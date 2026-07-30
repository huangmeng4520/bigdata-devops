# -*- coding: utf-8 -*-
"""
发布记录视图
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.shortcuts import get_object_or_404

from ..models import (
    ReleaseRecord, ReleaseBuildLog, ApprovalRule, Application,
    ApplicationPipelineConfig, EnvironmentStrategy
)
from ..serializers import (
    ReleaseRecordSerializer, ReleaseCreateSerializer,
    ReleaseBuildLogSerializer,
    ApprovalRuleSerializer, ApprovalRuleCreateSerializer,
    ApprovalActionSerializer
)
from ..filters import ReleaseRecordFilter, ReleaseBuildLogFilter, ApprovalRuleFilter
from utils.custom_model_viewSet import CustomModelViewSet
from utils.data_permission import (
    DataPermissionMixin, user_has_scope_access, user_has_button_perm
)
from utils.permissions import HasMutateButtonPermission

MAX_LOG_LENGTH = 200 * 1024


def _get_pipeline_content(app, environment):
    """获取应用的 Pipeline Jenkinsfile 内容"""
    config = ApplicationPipelineConfig.objects.filter(
        application=app, environment=environment, is_active=True
    ).select_related('template_version').first()
    if not config:
        return None
    if config.template_version and config.template_version.content:
        return config.template_version.content
    if config.custom_content:
        return config.custom_content
    return None


class ReleaseRecordViewSet(DataPermissionMixin, CustomModelViewSet):
    """发布记录视图集"""
    queryset = ReleaseRecord.objects.select_related(
        'application', 'application__project', 'application__module'
    ).all()
    serializer_class = ReleaseRecordSerializer
    filterset_class = ReleaseRecordFilter
    permission_classes = [IsAuthenticated, HasMutateButtonPermission]

    # 数据权限：按所属应用→项目级联隔离
    scope_type = 'project'
    scope_field = 'application__project_id'

    # 自定义动作（触发/取消/审批/拒绝/重试/AI分析）按按钮码校验
    RECORD_ACTION_PERMS = {
        'trigger': 'release:release_record:trigger',
        'cancel': 'release:release_record:cancel',
        'approve': 'release:release_record:approve',
        'reject': 'release:release_record:reject',
        'retry': 'release:release_record:retry',
        'ai_analysis': 'release:release_record:ai_analysis',
    }

    def get_permissions(self):
        if self.action in self.RECORD_ACTION_PERMS:
            self.required_permission = self.RECORD_ACTION_PERMS[self.action]
        return super().get_permissions()

    def get_queryset(self):
        queryset = super().get_queryset()
        return self.data_permission_filter(queryset)

    def perform_update(self, serializer):
        self.check_object_data_permission(serializer.instance)
        serializer.save(modifier=self.request.user.username)

    def perform_destroy(self, instance):
        self.check_object_data_permission(instance)
        super().perform_destroy(instance)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def trigger(self, request, pk=None):
        """触发构建"""
        release = self.get_object()

        if not release.can_trigger():
            return Response(
                {"error": f"当前状态 [{release.get_status_display()}] 不允许触发构建"},
                status=status.HTTP_400_BAD_REQUEST
            )

        release.status = 'building'
        release.status_message = "正在触发构建..."
        release.save(update_fields=['status', 'status_message'])

        from ..tasks import trigger_jenkins_build
        trigger_jenkins_build.delay(release.id)

        return Response({
            "message": "构建已触发",
            "release_id": release.id,
            "status": release.status
        })

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def cancel(self, request, pk=None):
        """取消发布"""
        release = self.get_object()

        if not release.can_cancel():
            return Response(
                {"error": f"当前状态 [{release.get_status_display()}] 不允许取消"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if release.jenkins_build_number:
            from ..services import JenkinsService
            jenkins = JenkinsService()
            job_full_name = release.jenkins_job_name
            parts = job_full_name.split('/')
            job_name = parts[-1]
            folder = '/'.join(parts[:-1]) if len(parts) > 1 else None
            jenkins.stop_build(
                name=job_name,
                build_number=release.jenkins_build_number,
                folder=folder
            )

        release.status = 'cancelled'
        release.status_message = "用户取消"
        release.save(update_fields=['status', 'status_message'])

        return Response({"message": "已取消"})

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def logs(self, request, pk=None):
        """获取构建日志"""
        release = self.get_object()
        logs = release.build_logs.all().order_by('create_time')
        serializer = ReleaseBuildLogSerializer(logs, many=True)
        return self._build_response(data=serializer.data, message="ok")

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def approve(self, request, pk=None):
        """审批通过"""
        release = self.get_object()

        if not release.can_approve():
            return Response(
                {"error": f"当前状态 [{release.get_status_display()}] 不允许审批"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = ApprovalActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        release.status = 'approved'
        release.approval_time = timezone.now()
        release.approval_user = request.user.username
        release.approval_comment = serializer.validated_data.get('comment', '')
        release.save(update_fields=['status', 'approval_time', 'approval_user', 'approval_comment'])

        return Response({
            "message": "审批通过",
            "status": release.status
        })

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def reject(self, request, pk=None):
        """审批拒绝"""
        release = self.get_object()

        if not release.can_approve():
            return Response(
                {"error": f"当前状态 [{release.get_status_display()}] 不允许审批"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = ApprovalActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        release.status = 'rejected'
        release.approval_time = timezone.now()
        release.approval_user = request.user.username
        release.approval_comment = serializer.validated_data.get('comment', '')
        release.save(update_fields=['status', 'approval_time', 'approval_user', 'approval_comment'])

        return Response({
            "message": "审批已拒绝",
            "status": release.status
        })

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def retry(self, request, pk=None):
        """重试构建"""
        release = self.get_object()

        if release.status not in ['build_failed', 'cancelled']:
            return Response(
                {"error": f"当前状态 [{release.get_status_display()}] 不允许重试"},
                status=status.HTTP_400_BAD_REQUEST
            )

        release.status = 'building'
        release.status_message = "正在重试构建..."
        release.save(update_fields=['status', 'status_message'])

        from ..tasks import trigger_jenkins_build
        trigger_jenkins_build.delay(release.id)

        return Response({
            "message": "重试构建已触发",
            "release_id": release.id
        })

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def ai_analysis(self, request, pk=None):
        """AI 分析：创建对话保存日志，调用 AI 并保存回复，返回 conversation_id"""
        from ai.models import ChatConversation, ChatMessage, AIModel

        release = self.get_object()
        if release.status != 'build_failed':
            return Response(
                {"error": "仅构建失败的发布记录可以分析"},
                status=status.HTTP_400_BAD_REQUEST
            )

        app = release.application
        logs_qs = release.build_logs.all().order_by('create_time')
        log_text = '\n'.join(l.log_content or '' for l in logs_qs)
        if len(log_text) > MAX_LOG_LENGTH:
            log_text = '...(前部省略)...\n' + log_text[-MAX_LOG_LENGTH:]

        pipeline_content = _get_pipeline_content(app, release.environment)
        project_name = app.project.name if app.project else '-'
        module_name = app.module.name if app.module else '-'

        system_parts = [
            "你是一个 DevOps 构建失败分析专家。请分析以下构建失败原因。",
            "",
            f"应用：{app.name} ({app.code})",
            f"项目：{project_name} / 模块：{module_name}",
            f"分支：{release.branch} | 环境：{release.environment} | 版本：{release.version or '-'}",
        ]
        if pipeline_content:
            system_parts.extend([
                "",
                "该应用的 Pipeline 配置（Jenkinsfile）：",
                "```",
                pipeline_content,
                "```",
            ])
        system_prompt = '\n'.join(system_parts)

        user_prompt = f"以下是本次构建的日志输出，请分析失败原因并给出修复建议：\n\n```\n{log_text}\n```"

        full_user_msg = system_prompt + '\n\n---\n\n' + user_prompt

        ai_model = AIModel.objects.filter(status=1).select_related('key').first()
        model_name = ai_model.model if ai_model else 'deepseek-chat'

        from django.utils import timezone
        now_str = timezone.now().strftime('%m-%d %H:%M')
        conversation = ChatConversation.objects.create(
            title=f"构建分析: {app.name} #{release.jenkins_build_number or ''} {now_str}",
            model=model_name,
            model_id=ai_model if ai_model else None,
            temperature=0.7,
            max_tokens=2048,
            max_contexts=10,
        )

        ChatMessage.objects.create(
            conversation_id=conversation.id, model=model_name,
            type='user', content=full_user_msg[:2000],
            use_context=False,
        )

        release.conversation_id = conversation.id
        release.save(update_fields=['conversation_id'])

        return self._build_response(data={"conversation_id": conversation.id})


class ApprovalRuleViewSet(CustomModelViewSet):
    """审批规则视图集"""
    queryset = ApprovalRule.objects.all()
    serializer_class = ApprovalRuleSerializer
    filterset_class = ApprovalRuleFilter
    permission_classes = [IsAuthenticated, HasMutateButtonPermission]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ApprovalRuleCreateSerializer
        return ApprovalRuleSerializer


# ============================================================
# 应用发布 API（触发发布入口）
# ============================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_release(request, app_id):
    """
    触发发布（创建发布记录）

    POST /api/admin/release/application/<app_id>/release/
    """
    try:
        application = Application.objects.select_related(
            'project', 'module'
        ).get(pk=app_id)
    except Application.DoesNotExist:
        return Response(
            {"error": "应用不存在"},
            status=status.HTTP_404_NOT_FOUND
        )

    # 数据权限 + 按钮权限校验
    if not user_has_button_perm(request.user, 'release:application:release'):
        return Response(
            {"error": "无权限触发发布"},
            status=status.HTTP_403_FORBIDDEN
        )
    if not user_has_scope_access(request.user, 'application', application.id):
        return Response(
            {"error": "无权限操作该应用"},
            status=status.HTTP_403_FORBIDDEN
        )

    serializer = ReleaseCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    data = serializer.validated_data
    branch = data['branch']
    environment = data['environment']
    require_approval = data.get('require_approval', False)

    # 获取环境策略
    strategy = EnvironmentStrategy.objects.filter(
        environment=environment,
        status=1  # 启用状态
    ).first()

    # 如果环境策略要求审批，自动设置
    if strategy and strategy.requires_approval:
        require_approval = True

    # 创建发布记录
    release = ReleaseRecord.objects.create(
        application=application,
        branch=branch,
        environment=environment,
        version=data.get('version') or None,
        require_approval=require_approval,
        approval_type=data.get('approval_type'),
        approvers=data.get('approvers', []),
        status='approval_pending' if require_approval else 'pending',
        released_by=request.user.username,
        remark=data.get('remark', '')
    )

    # 如果不需要审批，直接触发构建
    if not require_approval:
        from ..services import JenkinsService, DevOpsException

        # 先同步检查 Jenkins 是否可用
        try:
            jenkins = JenkinsService()
            if not jenkins.test_connection():
                release.status = 'build_failed'
                release.status_message = 'Jenkins 服务不可用，请检查配置'
                release.save(update_fields=['status', 'status_message'])
                return Response({
                    "code": 1,
                    "data": {
                        "id": release.id,
                        "status": "build_failed",
                        "status_display": release.get_status_display(),
                        "message": "Jenkins 服务不可用，请检查配置"
                    }
                })
        except DevOpsException as e:
            release.status = 'build_failed'
            release.status_message = f'Jenkins 连接失败: {e.message}'
            release.save(update_fields=['status', 'status_message'])
            return Response({
                "code": 1,
                "data": {
                    "id": release.id,
                    "status": "build_failed",
                    "status_display": release.get_status_display(),
                    "message": f"Jenkins 连接失败: {e.message}"
                }
            })

        # 触发异步构建
        from ..tasks import trigger_jenkins_build
        try:
            trigger_jenkins_build.delay(release.id)
            release.status = 'building'
            release.save(update_fields=['status'])
            status = 'building'
            message = '发布已创建，构建已触发'
        except Exception as e:
            # Jenkins/Celery 服务异常
            release.status = 'build_failed'
            release.status_message = f'触发构建失败: {str(e)}'
            release.save(update_fields=['status', 'status_message'])
            status = 'build_failed'
            message = f'发布已创建，但触发构建失败: {str(e)}'
    else:
        status = 'approval_pending'
        message = '发布已创建，等待审批'

    return Response({
        "code": 0,
        "data": {
            "id": release.id,
            "status": status,
            "status_display": release.get_status_display(),
            "message": message
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_app_branches(request, app_id):
    """
    获取应用分支列表

    GET /api/admin/release/application/<app_id>/branches/
    """
    try:
        application = Application.objects.get(pk=app_id)
    except Application.DoesNotExist:
        return Response(
            {"error": "应用不存在"},
            status=status.HTTP_404_NOT_FOUND
        )

    # 数据权限校验：仅可访问被分配的应用
    if not user_has_scope_access(request.user, 'application', application.id):
        return Response(
            {"error": "无权限操作该应用"},
            status=status.HTTP_403_FORBIDDEN
        )

    # 从 GitLab 获取分支列表
    from ..services import GitLabService
    try:
        gitlab = GitLabService()
        if application.gitlab_project_id:
            branches = gitlab.get_project_branches(application.gitlab_project_id)
            return Response({"branches": branches})
        else:
            # 返回默认分支
            return Response({
                "branches": [
                    {"name": application.build_branch or "main", "commit": None}
                ]
            })
    except Exception as e:
        # 失败时返回默认分支
        return Response({
            "branches": [
                {"name": application.build_branch or "main", "commit": None}
            ],
            "error": str(e)
        })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_app_environments(request, app_id):
    """
    获取应用环境配置

    GET /api/admin/release/application/<app_id>/environments/
    """
    try:
        application = Application.objects.get(pk=app_id)
    except Application.DoesNotExist:
        return Response(
            {"error": "应用不存在"},
            status=status.HTTP_404_NOT_FOUND
        )

    # 数据权限校验：仅可访问被分配的应用
    if not user_has_scope_access(request.user, 'application', application.id):
        return Response(
            {"error": "无权限操作该应用"},
            status=status.HTTP_403_FORBIDDEN
        )

    configs = ApplicationPipelineConfig.objects.filter(
        application=application,
        is_active=True
    ).values('environment', 'jenkins_job_name')

    strategies = {
        s.environment: s
        for s in EnvironmentStrategy.objects.filter(status=1)
    }

    environments = []
    env_choices = dict(ApplicationPipelineConfig.ENVIRONMENT_CHOICES)

    for env_code, env_name in env_choices.items():
        config = next((c for c in configs if c['environment'] == env_code), None)
        strategy = strategies.get(env_code)

        environments.append({
            "code": env_code,
            "name": env_name,
            "has_pipeline_config": config is not None,
            "requires_approval": strategy.requires_approval if strategy else False,
        })

    return Response({"code": 0, "data": environments})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_approval_rules(request):
    """
    获取审批规则列表

    GET /api/admin/release/approval-rules/
    """
    environment = request.query_params.get('environment')
    queryset = ApprovalRule.objects.filter(status=1)

    if environment:
        queryset = queryset.filter(environment=environment)

    serializer = ApprovalRuleSerializer(queryset, many=True)
    return Response(serializer.data)
