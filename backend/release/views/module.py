# -*- coding: utf-8 -*-
"""
模块管理视图
"""
import logging
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from utils.custom_model_viewSet import CustomModelViewSet
from utils.data_permission import DataPermissionMixin, user_has_scope_access
from utils.permissions import HasMutateButtonPermission
from ..models import Module, Application, SyncLog
from ..serializers import ModuleSerializer, ModuleCreateSerializer, ApplicationSerializer
from ..filters import ModuleFilter
from ..services import GitLabService, DevOpsException

logger = logging.getLogger(__name__)


class ModuleViewSet(DataPermissionMixin, CustomModelViewSet):
    """模块管理"""
    queryset = Module.objects.all()
    serializer_class = ModuleSerializer

    # 按钮权限：写操作（create/edit/destroy）需在角色中拥有对应按钮权限，
    # 读操作放行，避免影响列表/下拉等查询路径。
    permission_classes = [HasMutateButtonPermission]

    # 数据权限：模块归属项目，按 project 级联隔离
    scope_type = 'project'
    scope_field = 'project_id'
    filter_backends = [DjangoFilterBackend]
    filterset_class = ModuleFilter
    search_fields = ["name", "code"]
    ordering_fields = ["sort", "create_time"]
    enable_soft_delete = True

    action_serializers = {
        "create": ModuleCreateSerializer,
        "update": ModuleCreateSerializer,
    }

    def get_queryset(self):
        queryset = super().get_queryset().select_related("project")
        if self.enable_soft_delete:
            queryset = queryset.filter(is_deleted=False)
        return self.data_permission_filter(queryset)

    def perform_create(self, serializer):
        """创建模块并自动创建 GitLab Subgroup，需校验目标项目数据权限"""
        # 创建前校验：当前用户必须对目标项目拥有数据权限
        project = serializer.validated_data.get('project')
        project_id = project.id if hasattr(project, 'id') else project
        if not user_has_scope_access(self.request.user, 'project', project_id):
            raise PermissionDenied('无权限在该项目下创建模块：目标项目不在您的数据范围内')
        instance = serializer.save(creator=self.request.user.username)
        self._create_gitlab_subgroup(instance)

    def _create_gitlab_subgroup(self, module: Module):
        """
        创建 GitLab Subgroup

        Args:
            module: Module 实例
        """
        # 检查项目是否有 GitLab Group ID
        if not module.project.gitlab_group_id:
            logger.warning(f"模块 {module.name} 所属项目没有 GitLab Group ID，跳过 Subgroup 创建")
            # 记录日志
            SyncLog.objects.create(
                project=module.project,
                module=module,
                sync_type="gitlab",
                resource_name=module.code,
                action="create",
                status=0,
                message="所属项目没有 GitLab Group ID"
            )
            return

        try:
            gitlab = GitLabService()
            result = gitlab.create_group(
                name=module.name,
                path=module.code,
                parent_id=module.project.gitlab_group_id,
                description=module.description
            )

            # 更新 GitLab Subgroup ID
            module.gitlab_subgroup_id = result.get("id")
            module.save(update_fields=["gitlab_subgroup_id"])

            # 记录同步日志
            SyncLog.objects.create(
                project=module.project,
                module=module,
                sync_type="gitlab",
                resource_name=f"{module.project.code}/{module.code}",
                action="create",
                status=1,
                message=f"创建 GitLab Subgroup 成功: {result.get('web_url', '')}"
            )

            logger.info(f"模块 {module.name} GitLab Subgroup 创建成功: {result.get('id')}")

        except DevOpsException as e:
            logger.error(f"模块 {module.name} GitLab Subgroup 创建失败: {e.message}")
            SyncLog.objects.create(
                project=module.project,
                module=module,
                sync_type="gitlab",
                resource_name=module.code,
                action="create",
                status=0,
                message=e.message
            )
        except Exception as e:
            logger.exception(f"模块 {module.name} GitLab Subgroup 创建异常: {e}")

    def perform_update(self, serializer):
        """更新时自动设置修改人"""
        self.check_object_data_permission(serializer.instance)
        serializer.save(modifier=self.request.user.username)

    def perform_destroy(self, instance):
        """软删除，不删除 GitLab Subgroup"""
        self.check_object_data_permission(instance)
        instance.is_deleted = True
        instance.save()

    @action(detail=True, methods=["get"])
    def applications(self, request, pk=None):
        """获取模块下的应用列表"""
        module = self.get_object()
        applications = Application.objects.filter(
            module=module, is_deleted=False
        ).select_related("project")
        serializer = ApplicationSerializer(applications, many=True)
        return Response({"code": 0, "data": serializer.data})

    @action(detail=False, methods=["get"])
    def by_project(self, request):
        """按项目分组获取模块列表"""
        project_id = request.query_params.get("project_id")
        if not project_id:
            return Response({"code": 1, "message": "缺少project_id参数"})

        modules = Module.objects.filter(
            project_id=project_id, is_deleted=False, status=1
        )
        serializer = ModuleSerializer(modules, many=True)
        return Response({"code": 0, "data": serializer.data})

    @action(detail=True, methods=["post"])
    def sync_gitlab(self, request, pk=None):
        """手动同步 GitLab Subgroup"""
        module = self.get_object()

        if module.gitlab_subgroup_id:
            return Response({
                "code": 1,
                "message": "GitLab Subgroup 已存在，请使用更新功能"
            })

        if not module.project.gitlab_group_id:
            return Response({
                "code": 1,
                "message": "所属项目没有 GitLab Group ID，请先同步项目"
            })

        self._create_gitlab_subgroup(module)
        module.refresh_from_db()

        return Response({
            "code": 0,
            "message": "同步成功" if module.gitlab_subgroup_id else "同步失败，请查看日志",
            "data": {"gitlab_subgroup_id": module.gitlab_subgroup_id}
        })

    @action(detail=True, methods=["get"])
    def sync_logs(self, request, pk=None):
        """获取模块的同步日志"""
        module = self.get_object()
        from ..serializers import SyncLogSerializer

        logs = SyncLog.objects.filter(module=module).order_by("-create_time")[:50]
        serializer = SyncLogSerializer(logs, many=True)
        return Response({"code": 0, "data": serializer.data})

    # ==================== 从 GitLab 导入 ====================

    @action(detail=False, methods=["get"])
    def list_gitlab_subgroups(self, request):
        """
        列出 GitLab 上的 Subgroups（用于导入）
        """
        parent_id = request.query_params.get("parent_id")
        if not parent_id:
            return Response({"code": 1, "message": "请提供 parent_id（父 Group ID）"})

        page = int(request.query_params.get("page", 1))
        per_page = int(request.query_params.get("per_page", 50))

        try:
            gitlab = GitLabService()
            subgroups = gitlab.list_subgroups(int(parent_id), page, per_page)
            
            # 获取已导入的 GitLab Subgroup IDs
            imported_ids = set(Module.objects.filter(
                is_deleted=False
            ).values_list('gitlab_subgroup_id', flat=True))
            
            # 过滤已存在的
            filtered_subgroups = [
                s for s in subgroups 
                if s.get('id') not in imported_ids and s.get('id') is not None
            ]
            
            return Response({
                "code": 0,
                "data": filtered_subgroups,
                "total": len(filtered_subgroups)
            })
        except DevOpsException as e:
            return Response({"code": 1, "message": e.message})

    @action(detail=False, methods=["post"])
    def import_gitlab_subgroups(self, request):
        """
        批量从 GitLab 导入 Subgroups 到本系统
        """
        import_data = request.data.get("data", [])
        
        if not import_data:
            return Response({"code": 1, "message": "请选择要导入的 Subgroups"})

        # 获取已导入的 IDs
        imported_ids = set(Module.objects.filter(
            is_deleted=False
        ).values_list('gitlab_subgroup_id', flat=True))

        success_count = 0
        fail_count = 0
        results = []

        try:
            gitlab = GitLabService()
            
            for item in import_data:
                gitlab_subgroup_id = item.get("gitlab_subgroup_id")
                project_id = item.get("project_id")
                
                if not gitlab_subgroup_id or not project_id:
                    fail_count += 1
                    results.append({
                        "gitlab_subgroup_id": gitlab_subgroup_id,
                        "status": "failed",
                        "message": "参数不完整"
                    })
                    continue
                
                if gitlab_subgroup_id in imported_ids:
                    fail_count += 1
                    results.append({
                        "gitlab_subgroup_id": gitlab_subgroup_id,
                        "status": "skipped",
                        "message": "已存在"
                    })
                    continue
                
                try:
                    from ..models import Project
                    project = Project.objects.get(id=project_id, is_deleted=False)
                    if not project.gitlab_group_id:
                        fail_count += 1
                        results.append({
                            "gitlab_subgroup_id": gitlab_subgroup_id,
                            "status": "failed",
                            "message": "项目未关联 GitLab Group"
                        })
                        continue
                    
                    subgroup_info = gitlab.get_group_by_id(gitlab_subgroup_id)
                    if not subgroup_info:
                        fail_count += 1
                        results.append({
                            "gitlab_subgroup_id": gitlab_subgroup_id,
                            "status": "failed",
                            "message": "GitLab Subgroup 不存在"
                        })
                        continue

                    module = Module.objects.create(
                        name=subgroup_info.get("name", ""),
                        code=subgroup_info.get("path", ""),
                        project=project,
                        gitlab_subgroup_id=subgroup_info["id"],
                        gitlab_sync_status="success",
                        gitlab_sync_message="从 GitLab 导入",
                        creator=request.user.username
                    )
                    success_count += 1
                    results.append({
                        "gitlab_subgroup_id": gitlab_subgroup_id,
                        "status": "success",
                        "id": module.id,
                        "name": module.name
                    })
                except Exception as e:
                    fail_count += 1
                    results.append({
                        "gitlab_subgroup_id": gitlab_subgroup_id,
                        "status": "failed",
                        "message": str(e)
                    })

            return Response({
                "code": 0,
                "message": f"导入完成: 成功 {success_count} 个, 跳过/失败 {fail_count} 个",
                "data": {
                    "success_count": success_count,
                    "fail_count": fail_count,
                    "results": results
                }
            })
        except Exception as e:
            logger.error(f"批量导入 GitLab Subgroups 失败: {str(e)}")
            return Response({"code": 1, "message": f"导入失败: {str(e)}"})

    @action(detail=False, methods=["post"])
    def import_gitlab_subgroup(self, request):
        """
        从 GitLab 导入单个 Subgroup 到本系统
        """
        gitlab_subgroup_id = request.data.get("gitlab_subgroup_id")
        project_id = request.data.get("project_id")
        
        if not gitlab_subgroup_id:
            return Response({"code": 1, "message": "请提供 gitlab_subgroup_id"})
        if not project_id:
            return Response({"code": 1, "message": "请提供 project_id"})

        try:
            gitlab = GitLabService()
            subgroup_info = gitlab.get_group_by_id(gitlab_subgroup_id)
            
            if not subgroup_info:
                return Response({"code": 1, "message": "GitLab Subgroup 不存在"})

            if Module.objects.filter(gitlab_subgroup_id=gitlab_subgroup_id, is_deleted=False).exists():
                return Response({"code": 1, "message": "该 GitLab Subgroup 已导入"})

            from ..models import Project
            try:
                project = Project.objects.get(id=project_id, is_deleted=False)
            except Project.DoesNotExist:
                return Response({"code": 1, "message": "项目不存在"})

            if not project.gitlab_group_id:
                return Response({"code": 1, "message": "项目未关联 GitLab Group，无法导入 Subgroup"})

            module = Module.objects.create(
                name=subgroup_info.get("name", ""),
                code=subgroup_info.get("path", ""),
                project=project,
                gitlab_subgroup_id=subgroup_info["id"],
                gitlab_sync_status="success",
                gitlab_sync_message="从 GitLab 导入",
                creator=request.user.username
            )

            return Response({
                "code": 0,
                "message": "导入成功",
                "data": {
                    "id": module.id,
                    "name": module.name,
                    "gitlab_subgroup_id": module.gitlab_subgroup_id
                }
            })
        except DevOpsException as e:
            return Response({"code": 1, "message": e.message})
        except Exception as e:
            logger.error(f"导入 GitLab Subgroup 失败: {str(e)}")
            return Response({"code": 1, "message": f"导入失败: {str(e)}"})
