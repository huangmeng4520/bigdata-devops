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


class ReleaseRecordViewSet(CustomModelViewSet):
    """发布记录视图集"""
    queryset = ReleaseRecord.objects.select_related(
        'application', 'application__project', 'application__module'
    ).all()
    serializer_class = ReleaseRecordSerializer
    filterset_class = ReleaseRecordFilter
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        # 非管理员只能看到自己发布的记录
        user = self.request.user
        if not user.is_superuser:
            # 可以在这里添加更复杂的权限逻辑
            pass
        return queryset

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def trigger(self, request, pk=None):
        """触发构建"""
        release = self.get_object()

        if not release.can_trigger():
            return Response(
                {"error": f"当前状态 [{release.get_status_display()}] 不允许触发构建"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 更新状态
        release.status = 'building'
        release.status_message = "正在触发构建..."
        release.save(update_fields=['status', 'status_message'])

        # 异步触发 Jenkins 构建
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

        # 取消 Jenkins 构建
        if release.jenkins_build_number:
            from ..services import JenkinsService
            jenkins = JenkinsService()

            # 解析 Job 名称和 Folder
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

        # 更新状态
        release.status = 'building'
        release.status_message = "正在重试构建..."
        release.save(update_fields=['status', 'status_message'])

        # 异步触发 Jenkins 构建
        from ..tasks import trigger_jenkins_build
        trigger_jenkins_build.delay(release.id)

        return Response({
            "message": "重试构建已触发",
            "release_id": release.id
        })


class ApprovalRuleViewSet(CustomModelViewSet):
    """审批规则视图集"""
    queryset = ApprovalRule.objects.all()
    serializer_class = ApprovalRuleSerializer
    filterset_class = ApprovalRuleFilter
    permission_classes = [IsAuthenticated]

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
        version=data.get('version'),
        require_approval=require_approval,
        approval_type=data.get('approval_type'),
        approvers=data.get('approvers', []),
        status='approval_pending' if require_approval else 'pending',
        released_by=request.user.username,
        remark=data.get('remark', '')
    )

    # 如果不需要审批，直接触发构建
    if not require_approval:
        from ..tasks import trigger_jenkins_build
        trigger_jenkins_build.delay(release.id)
        release.status = 'building'
        release.save(update_fields=['status'])

    return Response({
        "id": release.id,
        "status": release.status,
        "status_display": release.get_status_display(),
        "message": "发布已创建" + ("，等待审批" if require_approval else "，构建已触发")
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
        application = Application.objects.select_related('ci_template', 'cd_template').get(pk=app_id)
    except Application.DoesNotExist:
        return Response(
            {"error": "应用不存在"},
            status=status.HTTP_404_NOT_FOUND
        )

    # 检查应用是否直接关联了 CI/CD 模板
    has_ci_template = application.ci_template_id is not None
    has_cd_template = application.cd_template_id is not None

    # 获取应用的流水线配置（针对每个环境的详细配置）
    configs = ApplicationPipelineConfig.objects.filter(
        application=application,
        is_active=True
    ).values('environment', 'config_type', 'jenkins_job_name')

    # 获取环境策略
    strategies = {
        s.environment: s
        for s in EnvironmentStrategy.objects.filter(status=1)
    }

    environments = []
    env_choices = dict(ApplicationPipelineConfig.ENVIRONMENT_CHOICES)

    for env_code, env_name in env_choices.items():
        config = next((c for c in configs if c['environment'] == env_code), None)
        strategy = strategies.get(env_code)

        # 判断是否有 CI 配置：
        # 1. 应用直接关联了 CI 模板，或
        # 2. 该环境有具体的 CI 流水线配置
        has_ci_config = has_ci_template or (config and config['config_type'] == 'ci')
        has_cd_config = has_cd_template or (config and config['config_type'] == 'cd')

        environments.append({
            "code": env_code,
            "name": env_name,
            "has_ci_config": has_ci_config,
            "has_cd_config": has_cd_config,
            "requires_approval": strategy.requires_approval if strategy else False,
            "pipeline_mode": strategy.pipeline_mode if strategy else 'integrated',
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
