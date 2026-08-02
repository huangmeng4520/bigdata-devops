# -*- coding: utf-8 -*-
"""
代码仓库管理视图
"""
import logging
from django.db import IntegrityError
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from utils.custom_model_viewSet import CustomModelViewSet
from utils.data_permission import DataPermissionMixin, get_allowed_scope_ids
from utils.permissions import HasMutateButtonPermission
from ..models import CodeRepository
from ..serializers import CodeRepositorySerializer, CodeRepositoryCreateSerializer
from ..filters import CodeRepositoryFilter
from ..services import GitLabService, DevOpsException
from ..tasks import sync_code_repository_gitlab, import_gitlab_projects_batch

logger = logging.getLogger(__name__)


class CodeRepositoryViewSet(DataPermissionMixin, CustomModelViewSet):
    """代码仓库管理"""
    queryset = CodeRepository.objects.all()
    serializer_class = CodeRepositorySerializer
    permission_classes = [HasMutateButtonPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_class = CodeRepositoryFilter
    enable_soft_delete = True

    # 数据权限：代码库归属项目（或模块），按 project 级联隔离
    scope_type = 'project'
    scope_field = 'project_id'

    def data_permission_filter(self, queryset):
        allowed = get_allowed_scope_ids(self.get_user(), self.scope_type)
        if allowed is None:
            return queryset
        if not allowed:
            return queryset.none()
        from django.db.models import Q
        return queryset.filter(
            Q(project_id__in=allowed) | Q(module__project_id__in=allowed)
        )

    def check_object_data_permission(self, instance):
        allowed = get_allowed_scope_ids(self.get_user(), self.scope_type)
        if allowed is None:
            return
        project_id = instance.project_id
        module_project_id = instance.module.project_id if instance.module_id else None
        if project_id in allowed or module_project_id in allowed:
            return
        from rest_framework.exceptions import PermissionDenied
        raise PermissionDenied('无权限操作该数据：不在您的数据范围内')

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.enable_soft_delete:
            queryset = queryset.filter(is_deleted=False)
        return self.data_permission_filter(queryset)

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CodeRepositoryCreateSerializer
        return CodeRepositorySerializer

    def _sync_to_gitlab(self, repo):
        """同步代码仓库到 GitLab（同步执行）"""
        if repo.repository_type != 'gitlab':
            return

        from ..services import ConfigService
        config = ConfigService.get_gitlab_config()
        if not config.get('gitlab_url') or not config.get('gitlab_token'):
            logger.warning(f"GitLab 配置不完整，跳过同步")
            return

        gitlab = GitLabService()
        try:
            namespace_id = None
            if repo.module and repo.module.gitlab_subgroup_id:
                namespace_id = repo.module.gitlab_subgroup_id
            elif repo.project and repo.project.gitlab_group_id:
                namespace_id = repo.project.gitlab_group_id

            if not namespace_id:
                logger.warning(f"缺少 GitLab Group/Subgroup 配置，跳过同步")
                return

            project = gitlab.create_project(
                name=repo.name,
                path=repo.code,
                namespace_id=namespace_id,
                description=repo.description or '',
                default_branch=repo.default_branch or 'main'
            )

            repo.gitlab_project_id = project.get("id")
            repo.git_url = project.get("ssh_url_to_repo", "")
            repo.git_http_url = project.get("http_url_to_repo", "")
            repo.save(update_fields=['gitlab_project_id', 'git_url', 'git_http_url'])
        except DevOpsException as e:
            logger.error(f"同步代码仓库到 GitLab 失败: {e.message}")

    def perform_create(self, serializer):
        """创建代码仓库时同步到 GitLab"""
        repo = serializer.save()
        self._sync_to_gitlab(repo)

    def perform_update(self, serializer):
        """更新代码仓库时同步到 GitLab"""
        self.check_object_data_permission(serializer.instance)
        repo = serializer.save()
        self._sync_to_gitlab(repo)

    def perform_destroy(self, instance):
        """软删除"""
        self.check_object_data_permission(instance)
        instance.is_deleted = True
        instance.save()

    @action(detail=True, methods=['post'])
    def sync_gitlab(self, request, pk=None):
        """手动同步 GitLab 仓库"""
        repo = self.get_object()
        
        if repo.repository_type != 'gitlab':
            return Response({
                'code': 1,
                'message': '只有 GitLab 类型的仓库才能同步'
            })
        
        sync_code_repository_gitlab.delay(repo.id)
        
        return Response({
            'code': 0,
            'message': 'GitLab 同步任务已提交'
        })

    # ==================== 从 GitLab 导入 ====================

    @action(detail=False, methods=["get"])
    def list_gitlab_projects(self, request):
        """
        列出 GitLab 上的 Projects（用于导入）
        返回所有项目 + 已导入ID集合，由前端负责显示/过滤
        """
        group_id = request.query_params.get("group_id")
        search = request.query_params.get("search", "")
        page = int(request.query_params.get("page", 1))
        per_page = int(request.query_params.get("per_page", 50))

        try:
            gitlab = GitLabService()
            if group_id:
                projects, total = gitlab.list_projects(int(group_id), page=page, per_page=per_page, with_total=True)
            elif search:
                projects, total = gitlab.search_projects(search, page=page, per_page=per_page, with_total=True)
            else:
                projects, total = gitlab.list_projects(page=page, per_page=per_page, with_total=True)
            
            # 获取已导入的 GitLab Project IDs
            imported_ids = set(CodeRepository.objects.filter(
                is_deleted=False
            ).values_list('gitlab_project_id', flat=True))
            
            # 返回所有项目（不过滤），让前端根据 imported_ids 区分已导入和未导入
            return Response({
                "code": 0,
                "data": {
                    "projects": projects,        # 当前页所有项目
                    "total": total,               # GitLab 原始总数
                    "imported_ids": list(imported_ids),  # 已导入的 ID 集合
                },
            })
        except DevOpsException as e:
            return Response({"code": 1, "message": e.message})

    @action(detail=False, methods=["post"])
    def import_gitlab_projects(self, request):
        """
        批量从 GitLab 导入 Projects 到本系统（异步任务）
        改为提交 Celery 异步任务，避免前端超时
        """
        import_data = request.data.get("data", [])
        
        if not import_data:
            return Response({"code": 1, "message": "请选择要导入的 Projects"})

        # 过滤掉没有 gitlab_project_id 的项，提取纯数据
        valid_items = []
        invalid_count = 0
        for item in import_data:
            gitlab_project_id = item.get("gitlab_project_id")
            if not gitlab_project_id:
                invalid_count += 1
                continue
            valid_items.append({
                "gitlab_project_id": int(gitlab_project_id),
                "project_id": item.get("project_id"),
                "module_id": item.get("module_id"),
            })

        if not valid_items:
            return Response({"code": 1, "message": "没有有效的 Project 可导入"})

        # 过滤已导入的（未删除）
        imported_ids = set(CodeRepository.objects.filter(
            is_deleted=False
        ).values_list('gitlab_project_id', flat=True))
        
        items_to_import = [it for it in valid_items if it["gitlab_project_id"] not in imported_ids]
        skipped_count = len(valid_items) - len(items_to_import)

        if not items_to_import:
            return Response({
                "code": 0,
                "message": f"全部 {len(valid_items)} 个项目已导入，无需重复导入",
                "data": {"success_count": 0, "fail_count": 0, "skipped_count": skipped_count, "results": []}
            })

        # 提交 Celery 异步任务
        task = import_gitlab_projects_batch.delay(
            items=items_to_import,
            username=request.user.username
        )

        return Response({
            "code": 0,
            "message": f"批量导入任务已提交（{len(items_to_import)} 个项目），正在后台处理。已跳过 {skipped_count} 个已导入项目" + (f"，{invalid_count} 个参数无效" if invalid_count else ""),
            "data": {
                "task_id": task.id,
                "total": len(items_to_import),
                "skipped_count": skipped_count,
                "invalid_count": invalid_count,
            }
        })

    @action(detail=False, methods=["post"])
    def import_gitlab_project(self, request):
        """
        从 GitLab 导入单个 Project 到本系统
        """
        gitlab_project_id = request.data.get("gitlab_project_id")
        project_id = request.data.get("project_id")
        module_id = request.data.get("module_id")
        
        if not gitlab_project_id:
            return Response({"code": 1, "message": "请提供 gitlab_project_id"})

        try:
            gitlab = GitLabService()
            project_info = gitlab.get_project(gitlab_project_id, raise_on_error=True)
            
            if not project_info:
                return Response({"code": 1, "message": "GitLab Project 不存在"})

            # 先解析项目/模块：优先显式参数，否则按 GitLab namespace 路径自动匹配
            from ..models import Project, Module

            project_obj = None
            module_obj = None

            if project_id:
                try:
                    project_obj = Project.objects.get(id=project_id, is_deleted=False)
                except Project.DoesNotExist:
                    return Response({"code": 1, "message": "项目不存在"})

            if module_id:
                try:
                    module_obj = Module.objects.get(id=module_id, is_deleted=False)
                except Module.DoesNotExist:
                    return Response({"code": 1, "message": "模块不存在"})

            # 未显式指定时，按 GitLab namespace 路径自动匹配项目/模块
            if project_obj is None:
                namespace = project_info.get("namespace", {}) or {}
                full_path = namespace.get("full_path", "")
                if full_path:
                    path_parts = full_path.split("/")
                    try:
                        project_obj = Project.objects.get(code=path_parts[0], is_deleted=False)
                    except Project.DoesNotExist:
                        project_obj = None
                    if project_obj and len(path_parts) >= 2:
                        try:
                            module_obj = Module.objects.get(
                                project=project_obj, code=path_parts[1], is_deleted=False
                            )
                        except Module.DoesNotExist:
                            module_obj = None

            # 已存在且未删除
            if CodeRepository.objects.filter(gitlab_project_id=gitlab_project_id, is_deleted=False).exists():
                return Response({"code": 1, "message": "该 GitLab Project 已导入"})

            # 若曾被软删除，恢复之（取消删除并校正项目/模块关联）
            deleted_repo = CodeRepository.objects.filter(
                gitlab_project_id=gitlab_project_id, is_deleted=True
            ).first()
            if deleted_repo:
                deleted_repo.is_deleted = False
                deleted_repo.name = project_info.get("name", deleted_repo.name)
                deleted_repo.code = project_info.get("path", deleted_repo.code)
                deleted_repo.git_url = project_info.get("ssh_url_to_repo", deleted_repo.git_url)
                deleted_repo.git_http_url = project_info.get("http_url_to_repo", deleted_repo.git_http_url)
                deleted_repo.project = project_obj
                deleted_repo.module = module_obj
                deleted_repo.repository_type = 'gitlab'
                try:
                    deleted_repo.save()
                except IntegrityError:
                    return Response({
                        "code": 1,
                        "message": f"恢复失败：项目下已存在同名代码仓库（{deleted_repo.code}），请先清理重复数据"
                    })
                return Response({
                    "code": 0,
                    "message": "恢复成功",
                    "data": {
                        "id": deleted_repo.id,
                        "name": deleted_repo.name,
                        "gitlab_project_id": deleted_repo.gitlab_project_id,
                        "project_id": deleted_repo.project_id,
                        "module_id": deleted_repo.module_id,
                    }
                })

            repo = CodeRepository.objects.create(
                name=project_info.get("name", ""),
                code=project_info.get("path", ""),
                gitlab_project_id=project_info["id"],
                git_url=project_info.get("ssh_url_to_repo", ""),
                git_http_url=project_info.get("http_url_to_repo", ""),
                project=project_obj,
                module=module_obj,
                repository_type='gitlab',
                creator=request.user.username
            )

            return Response({
                "code": 0,
                "message": "导入成功",
                "data": {
                    "id": repo.id,
                    "name": repo.name,
                    "gitlab_project_id": repo.gitlab_project_id
                }
            })
        except DevOpsException as e:
            return Response({"code": 1, "message": e.message})
        except Exception as e:
            logger.error(f"导入 GitLab Project 失败: {str(e)}")
            return Response({"code": 1, "message": f"导入失败: {str(e)}"})
