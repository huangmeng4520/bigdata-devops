# -*- coding: utf-8 -*-
"""
项目管理视图
"""
import logging
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from utils.custom_model_viewSet import CustomModelViewSet
from utils.data_permission import DataPermissionMixin, get_allowed_scope_ids
from utils.permissions import HasMutateButtonPermission
from ..models import Project, Module, Application, SyncLog
from ..serializers import ProjectSerializer, ProjectCreateSerializer, ModuleSerializer, ApplicationSerializer
from ..filters import ProjectFilter
from ..services import GitLabService, DevOpsException

logger = logging.getLogger(__name__)


class ProjectViewSet(DataPermissionMixin, CustomModelViewSet):
    """项目管理"""
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [HasMutateButtonPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_class = ProjectFilter
    search_fields = ["name", "code"]
    ordering_fields = ["sort", "create_time"]
    enable_soft_delete = True

    # 数据权限：项目为范围根节点，按 project 隔离
    scope_type = 'project'
    scope_field = 'id'

    action_serializers = {
        "create": ProjectCreateSerializer,
        "update": ProjectCreateSerializer,
    }

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.enable_soft_delete:
            queryset = queryset.filter(is_deleted=False)
        return self.data_permission_filter(queryset)

    def perform_create(self, serializer):
        """创建项目并自动创建 GitLab Group，创建人自动获得该项目数据权限"""
        instance = serializer.save(creator=self.request.user.username)
        from system.models import DataPermissionRule
        DataPermissionRule.objects.get_or_create(
            scope_type='project',
            scope_id=instance.id,
            user=self.request.user,
            defaults={'creator': self.request.user.username, 'level': 'owner'},
        )
        self._create_gitlab_group(instance)

    def _create_gitlab_group(self, project: Project):
        """
        创建 GitLab Group

        Args:
            project: Project 实例
        """
        try:
            gitlab = GitLabService()
            result = gitlab.create_group(
                name=project.name,
                path=project.code,
                description=project.description
            )

            # 更新 GitLab Group ID
            project.gitlab_group_id = result.get("id")
            project.save(update_fields=["gitlab_group_id"])

            # 记录同步日志
            SyncLog.objects.create(
                project=project,
                sync_type="gitlab",
                resource_name=project.code,
                action="create",
                status=1,
                message=f"创建 GitLab Group 成功: {result.get('web_url', '')}"
            )

            logger.info(f"项目 {project.name} GitLab Group 创建成功: {result.get('id')}")

        except DevOpsException as e:
            logger.error(f"项目 {project.name} GitLab Group 创建失败: {e.message}")
            # 记录失败日志，但不阻塞主流程
            SyncLog.objects.create(
                project=project,
                sync_type="gitlab",
                resource_name=project.code,
                action="create",
                status=0,
                message=e.message
            )
        except Exception as e:
            logger.exception(f"项目 {project.name} GitLab Group 创建异常: {e}")

    def perform_update(self, serializer):
        """更新时自动设置修改人"""
        self.check_object_data_permission(serializer.instance)
        serializer.save(modifier=self.request.user.username)

    def perform_destroy(self, instance):
        """软删除，不删除 GitLab Group"""
        self.check_object_data_permission(instance)
        # 检查是否有关联的应用
        app_count = Application.objects.filter(project=instance, is_deleted=False).count()
        if app_count > 0:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"detail": f"该项目下存在 {app_count} 个应用，无法删除"})
        
        # 检查是否存在未删除的模块
        module_count = Module.objects.filter(project=instance, is_deleted=False).count()
        if module_count > 0:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"detail": f"该项目下存在 {module_count} 个模块，无法删除"})
        
        instance.is_deleted = True
        instance.save()

    @action(detail=True, methods=["get"])
    def modules(self, request, pk=None):
        """获取项目下的模块列表"""
        project = self.get_object()
        modules = Module.objects.filter(project=project, is_deleted=False)
        serializer = ModuleSerializer(modules, many=True)
        return Response({"code": 0, "data": serializer.data})

    @action(detail=True, methods=["get"])
    def applications(self, request, pk=None):
        """获取项目下的应用列表"""
        project = self.get_object()
        applications = Application.objects.filter(
            project=project, is_deleted=False
        ).select_related("module")
        serializer = ApplicationSerializer(applications, many=True)
        return Response({"code": 0, "data": serializer.data})

    @action(detail=False, methods=["get"])
    def tree(self, request):
        """获取项目-模块-应用树形结构（受数据权限过滤）"""
        projects = Project.objects.filter(is_deleted=False, status=1)
        allowed = get_allowed_scope_ids(self.request.user, 'project')
        if allowed is not None:
            projects = projects.filter(id__in=allowed)
        result = []
        for project in projects:
            modules = Module.objects.filter(project=project, is_deleted=False, status=1)
            module_list = []
            for module in modules:
                applications = Application.objects.filter(
                    module=module, is_deleted=False, status=1
                ).values("id", "name", "code", "app_type")
                module_list.append({
                    "id": module.id,
                    "name": module.name,
                    "code": module.code,
                    "applications": list(applications)
                })
            result.append({
                "id": project.id,
                "name": project.name,
                "code": project.code,
                "gitlab_group_id": project.gitlab_group_id,
                "modules": module_list
            })
        return Response({"code": 0, "data": result})

    @action(detail=True, methods=["post"])
    def sync_gitlab(self, request, pk=None):
        """手动同步 GitLab Group"""
        project = self.get_object()

        if project.gitlab_group_id:
            return Response({
                "code": 1,
                "message": "GitLab Group 已存在，请使用更新功能"
            })

        self._create_gitlab_group(project)
        project.refresh_from_db()

        return Response({
            "code": 0,
            "message": "同步成功" if project.gitlab_group_id else "同步失败，请查看日志",
            "data": {"gitlab_group_id": project.gitlab_group_id}
        })

    @action(detail=True, methods=["get"])
    def sync_logs(self, request, pk=None):
        """获取项目的同步日志"""
        project = self.get_object()
        from ..serializers import SyncLogSerializer

        logs = SyncLog.objects.filter(project=project).order_by("-create_time")[:50]
        serializer = SyncLogSerializer(logs, many=True)
        return Response({"code": 0, "data": serializer.data})

    # ==================== 从 GitLab 导入 ====================

    @action(detail=False, methods=["get"])
    def list_gitlab_groups(self, request):
        """
        列出 GitLab 上的 Groups（用于导入）
        """
        search = request.query_params.get("search", "")
        page = int(request.query_params.get("page", 1))
        per_page = int(request.query_params.get("per_page", 20))

        try:
            gitlab = GitLabService()
            logger.info(f"Fetching GitLab groups: search={search}, page={page}, per_page={per_page}")
            if search:
                groups = gitlab.search_groups(search, page, per_page)
            else:
                groups = gitlab.list_groups(page, per_page)
            
            # 获取已导入的 GitLab Group IDs
            imported_ids = set(Project.objects.filter(
                is_deleted=False
            ).values_list('gitlab_group_id', flat=True))
            
            # 过滤：只返回顶层 Groups（parent_id 为空），排除已导入的
            filtered_groups = [
                g for g in groups 
                if g.get('id') not in imported_ids 
                and g.get('id') is not None
                and g.get('parent_id') is None
            ]
            
            return Response({
                "code": 0,
                "data": filtered_groups,
                "total": len(filtered_groups)
            })
        except DevOpsException as e:
            logger.error(f"GitLab DevOpsException error: {e.message}")
            return Response({"code": 1, "message": e.message})
        except Exception as e:
            logger.error(f"GitLab error: {str(e)}")
            return Response({"code": 1, "message": str(e)})

    @action(detail=False, methods=["post"])
    def import_gitlab_groups(self, request):
        """
        批量从 GitLab 导入 Groups 到本系统
        """
        gitlab_group_ids = request.data.get("gitlab_group_ids", [])
        if not gitlab_group_ids:
            return Response({"code": 1, "message": "请选择要导入的 Groups"})

        # 获取已导入的 IDs
        imported_ids = set(Project.objects.filter(
            is_deleted=False
        ).values_list('gitlab_group_id', flat=True))

        success_count = 0
        fail_count = 0
        results = []

        try:
            gitlab = GitLabService()
            
            for gitlab_group_id in gitlab_group_ids:
                if gitlab_group_id in imported_ids:
                    fail_count += 1
                    results.append({
                        "gitlab_group_id": gitlab_group_id,
                        "status": "skipped",
                        "message": "已存在"
                    })
                    continue
                
                try:
                    group_info = gitlab.get_group_by_id(gitlab_group_id)
                    if not group_info:
                        fail_count += 1
                        results.append({
                            "gitlab_group_id": gitlab_group_id,
                            "status": "failed",
                            "message": "GitLab Group 不存在"
                        })
                        continue

                    project = Project.objects.create(
                        name=group_info.get("name", ""),
                        code=group_info.get("path", ""),
                        gitlab_group_id=group_info["id"],
                        gitlab_sync_status="success",
                        gitlab_sync_message="从 GitLab 导入",
                        creator=request.user.username
                    )
                    success_count += 1
                    results.append({
                        "gitlab_group_id": gitlab_group_id,
                        "status": "success",
                        "id": project.id,
                        "name": project.name
                    })
                except Exception as e:
                    fail_count += 1
                    results.append({
                        "gitlab_group_id": gitlab_group_id,
                        "status": "failed",
                        "message": str(e)
                    })

            return Response({
                "code": 0,
                "message": f"导入完成: 成功 {success_count} 个, 跳过 {fail_count} 个",
                "data": {
                    "success_count": success_count,
                    "fail_count": fail_count,
                    "results": results
                }
            })
        except Exception as e:
            logger.error(f"批量导入 GitLab Groups 失败: {str(e)}")
            return Response({"code": 1, "message": f"导入失败: {str(e)}"})

    @action(detail=False, methods=["post"])
    def import_gitlab_group(self, request):
        """
        从 GitLab 导入单个 Group 到本系统
        """
        gitlab_group_id = request.data.get("gitlab_group_id")
        if not gitlab_group_id:
            return Response({"code": 1, "message": "请提供 gitlab_group_id"})

        try:
            gitlab = GitLabService()
            group_info = gitlab.get_group_by_id(gitlab_group_id)
            
            if not group_info:
                return Response({"code": 1, "message": "GitLab Group 不存在"})

            if Project.objects.filter(gitlab_group_id=gitlab_group_id, is_deleted=False).exists():
                return Response({"code": 1, "message": "该 GitLab Group 已导入"})

            project = Project.objects.create(
                name=group_info.get("name", ""),
                code=group_info.get("path", ""),
                gitlab_group_id=group_info["id"],
                gitlab_sync_status="success",
                gitlab_sync_message="从 GitLab 导入",
                creator=request.user.username
            )

            return Response({
                "code": 0,
                "message": "导入成功",
                "data": {
                    "id": project.id,
                    "name": project.name,
                    "gitlab_group_id": project.gitlab_group_id
                }
            })
        except DevOpsException as e:
            return Response({"code": 1, "message": e.message})
        except Exception as e:
            logger.error(f"导入 GitLab Group 失败: {str(e)}")
            return Response({"code": 1, "message": f"导入失败: {str(e)}"})

    @action(detail=False, methods=["get"])
    def list_gitlab_projects(self, request):
        """
        列出 GitLab 上的 Projects（用于导入）
        """
        group_id = request.query_params.get("group_id")
        search = request.query_params.get("search", "")
        page = int(request.query_params.get("page", 1))
        per_page = int(request.query_params.get("per_page", 20))

        try:
            gitlab = GitLabService()
            if group_id:
                projects = gitlab.list_projects(int(group_id), page, per_page)
            elif search:
                projects = gitlab.search_projects(search, page, per_page)
            else:
                projects = gitlab.list_projects(page=page, per_page=per_page)
            
            return Response({
                "code": 0,
                "data": projects
            })
        except DevOpsException as e:
            return Response({"code": 1, "message": e.message})
