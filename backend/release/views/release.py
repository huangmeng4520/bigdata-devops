# -*- coding: utf-8 -*-
"""
发布记录视图
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.shortcuts import get_object_or_404

from ..models import (
    ReleaseRecord, ReleaseBuildLog, ApprovalRule, ApprovalRecord, Application,
    ApplicationPipelineConfig, EnvironmentStrategy
)
from ..serializers import (
    ReleaseRecordSerializer, ReleaseCreateSerializer,
    ReleaseBuildLogSerializer,
    ApprovalRuleSerializer, ApprovalRuleCreateSerializer,
    ApprovalActionSerializer, ApprovalRecordSerializer
)
from ..filters import ReleaseRecordFilter, ReleaseBuildLogFilter, ApprovalRuleFilter
from ..approval_engine import ApprovalEngine
from ..notifications import notify_approval_pending, notify_approval_result
from utils.custom_model_viewSet import CustomModelViewSet
from utils.data_permission import (
    DataPermissionMixin, user_has_scope_access, user_has_button_perm
)
from utils.permissions import HasMutateButtonPermission

MAX_LOG_LENGTH = 200 * 1024
MAX_EXTRACT_LENGTH = 30 * 1024

# 构建日志中标识错误的关键字（小写匹配）
ERROR_KEYWORDS = (
    'error', 'failed', 'failure', 'exception', 'traceback',
    'caused by', 'fatal', 'build failed', 'undefined',
    'npm err', 'syntaxerror', 'modulenotfounderror',
    'filenotfounderror', 'attributeerror', 'keyerror',
    'indexerror', 'valueerror', 'typeerror', 'runtimeerror',
    'connectionerror', 'timeout', 'denied', 'not found',
    'cannot find', 'no such file', 'permission denied',
    'exited with', 'return code', 'non-zero',
)

# 每个错误关键行前后保留的上下文行数
ERROR_CONTEXT_LINES = 15


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


def _extract_error_context(log_text):
    """从构建日志中智能提取错误关键行及其上下文。

    策略：定位含错误关键字的行，前后各保留 ERROR_CONTEXT_LINES 行上下文，
    合并重叠区间；未匹配到关键字时回退为日志末尾 MAX_EXTRACT_LENGTH 字符。
    """
    if not log_text:
        return ''

    lines = log_text.split('\n')
    if not lines:
        return ''

    error_indices = [
        i for i, line in enumerate(lines)
        if any(kw in line.lower() for kw in ERROR_KEYWORDS)
    ]

    # 未匹配到关键字：返回末尾片段
    if not error_indices:
        if len(log_text) <= MAX_EXTRACT_LENGTH:
            return log_text
        return '...(前部省略)...\n' + log_text[-MAX_EXTRACT_LENGTH:]

    # 合并重叠的上下文区间
    intervals = []
    for idx in error_indices:
        start = max(0, idx - ERROR_CONTEXT_LINES)
        end = min(len(lines), idx + ERROR_CONTEXT_LINES + 1)
        if intervals and start <= intervals[-1][1]:
            intervals[-1][1] = max(intervals[-1][1], end)
        else:
            intervals.append([start, end])

    result_lines = []
    for i, (start, end) in enumerate(intervals):
        if i > 0:
            skipped = start - intervals[i - 1][1]
            if skipped > 0:
                result_lines.append(f'...(中间省略 {skipped} 行)...')
        result_lines.extend(lines[start:end])

    result = '\n'.join(result_lines)

    # 仍然超长则按字符截断
    if len(result) > MAX_EXTRACT_LENGTH:
        result = result[:MAX_EXTRACT_LENGTH] + '\n...(日志过长，已截断)...'
    return result


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
        """审批通过（走审批引擎，支持多人流转）"""
        release = self.get_object()

        if not release.can_approve():
            return Response(
                {"error": f"当前状态 [{release.get_status_display()}] 不允许审批"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = ApprovalActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        engine = ApprovalEngine(release)
        try:
            result = engine.apply_approval(
                user=request.user, approved=True,
                comment=serializer.validated_data.get('comment', ''),
            )
        except PermissionDenied as e:
            return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)

        # 通知发布人
        if result in ('approved', 'rejected'):
            notify_approval_result(release, request.user, approved=True)

        msg_map = {
            'approved': '审批通过，已自动触发构建',
            'pending': '已记录您的审批，等待其他审批人',
        }
        return Response({
            "code": 0,
            "message": msg_map.get(result, '审批完成'),
            "data": {
                "status": release.status,
                "result": result,
                "approved_count": release.approved_count,
                "required_count": release.required_count,
                "current_approver_ids": release.current_approver_ids,
            },
        })

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def reject(self, request, pk=None):
        """审批拒绝（任一审批人拒绝即终止）"""
        release = self.get_object()

        if not release.can_approve():
            return Response(
                {"error": f"当前状态 [{release.get_status_display()}] 不允许审批"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = ApprovalActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        engine = ApprovalEngine(release)
        try:
            result = engine.apply_approval(
                user=request.user, approved=False,
                comment=serializer.validated_data.get('comment', ''),
            )
        except PermissionDenied as e:
            return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)

        notify_approval_result(release, request.user, approved=False)

        return Response({
            "code": 0,
            "message": "审批已拒绝",
            "data": {
                "status": release.status,
                "result": result,
            },
        })

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def approval_progress(self, request, pk=None):
        """审批进度：规则、已通过/待审批人、当前节点、历史记录

        补充字段：
        - current_approver_names: 当前待审批人姓名列表（由 approvers 配置解析得到）
        - current_stage / total_stage: 当前节点序号 / 节点总数（顺序审批场景）
        - approved_approvers / pending_approvers: 已通过 / 待审批审批人明细，便于前端时间线展示
        """
        release = self.get_object()
        records = release.approval_records.order_by('order', 'acted_at')

        # 由 approvers 配置（[{"user_id", "username", "order"}]）解析当前待审批人姓名
        approver_cfg_map = {
            a.get('user_id'): a for a in (release.approvers or [])
        }
        current_approver_ids = release.current_approver_ids or []
        current_approver_names = [
            approver_cfg_map.get(uid, {}).get('username', f'用户{uid}')
            for uid in current_approver_ids
        ]

        # 已通过 / 待审批审批人明细（基于历史记录 + 配置）
        approved_ids = set(records.filter(action='approve').values_list('approver_id', flat=True))
        approved_approvers = [
            {'user_id': a.get('user_id'), 'username': a.get('username'), 'order': a.get('order', 0)}
            for a in (release.approvers or []) if a.get('user_id') in approved_ids
        ]
        pending_approvers = [
            {'user_id': a.get('user_id'), 'username': a.get('username'), 'order': a.get('order', 0)}
            for a in (release.approvers or []) if a.get('user_id') not in approved_ids
        ]

        # 节点信息：顺序审批时给出当前节点序号
        total_stage = len(release.approvers or []) if release.approvers else 0
        if release.approval_type == 'sequential' and total_stage:
            current_stage = len(approved_approvers) + 1
            if current_stage > total_stage:
                current_stage = total_stage
        else:
            current_stage = 1 if current_approver_ids else 0

        return Response({
            "code": 0,
            "data": {
                "status": release.status,
                "status_display": release.get_status_display(),
                "rule_type": release.approval_type,
                "scope": release.approval_scope,
                "rule_name": release.approval_rule.name if release.approval_rule else None,
                "rule_code": release.approval_rule.code if release.approval_rule else None,
                "approved_count": release.approved_count,
                "required_count": release.required_count,
                "current_approver_ids": current_approver_ids,
                "current_approver_names": current_approver_names,
                "current_stage": current_stage,
                "total_stage": total_stage,
                "approved_approvers": approved_approvers,
                "pending_approvers": pending_approvers,
                "deadline": release.approval_deadline,
                "approvers": release.approvers,
                "history": ApprovalRecordSerializer(records, many=True).data,
            }
        })

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_approval_tasks(self, request):
        """我的审批待办：当前用户是 current_approver_ids 之一的待审批单

        注意：此处直接使用基础 queryset，不经过 data_permission_filter，
        因为审批人应能看到分配给自己的待办，即使该应用不在其数据权限范围内。
        """
        from django.db.models import Q
        qs = ReleaseRecord.objects.select_related(
            'application', 'application__project', 'application__module'
        ).filter(
            status='approval_pending'
        ).filter(
            Q(current_approver_ids__contains=request.user.id)
        ).order_by('-create_time')
        page = self.paginate_queryset(qs)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

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
        """AI 分析：智能提取错误日志上下文，创建对话并返回预填内容供用户确认后发送"""
        from ai.models import ChatConversation, AIModel

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

        # 智能提取错误关键行及上下文，避免发送全量日志
        error_context = _extract_error_context(log_text)

        pipeline_content = _get_pipeline_content(app, release.environment)
        project_name = app.project.name if app.project else '-'
        module_name = app.module.name if app.module else '-'

        prompt_parts = [
            "你是一个 DevOps 构建失败分析专家。请分析以下构建失败原因并给出修复建议。",
            "",
            f"应用：{app.name} ({app.code})",
            f"项目：{project_name} / 模块：{module_name}",
            f"分支：{release.branch} | 环境：{release.environment} | 版本：{release.version or '-'}",
        ]
        if pipeline_content:
            prompt_parts.extend([
                "",
                "该应用的 Pipeline 配置（Jenkinsfile）：",
                "```",
                pipeline_content,
                "```",
            ])
        prompt_parts.extend([
            "",
            "以下是本次构建的日志（已智能提取错误相关片段）：",
            "```",
            error_context,
            "```",
            "",
            "请分析失败原因并给出修复建议。",
        ])
        full_prompt = '\n'.join(prompt_parts)

        ai_model = AIModel.objects.filter(status=1).select_related('key').first()
        model_name = ai_model.model if ai_model else 'deepseek-chat'

        now_str = timezone.now().strftime('%m-%d %H:%M')
        conversation = ChatConversation.objects.create(
            title=f"构建分析: {app.name} #{release.jenkins_build_number or ''} {now_str}",
            model=model_name,
            model_id=ai_model if ai_model else None,
            temperature=0.7,
            max_tokens=2048,
            max_contexts=10,
        )

        release.conversation_id = conversation.id
        release.save(update_fields=['conversation_id'])

        # 不再预存 user 消息：把完整 prompt 返回给前端，预填到输入框，
        # 由用户确认/编辑后手动发送，发送时按正常流程落库并调用 LLM
        return self._build_response(data={
            "conversation_id": conversation.id,
            "content": full_prompt,
        })


class ApprovalRuleViewSet(CustomModelViewSet):
    """审批规则视图集"""
    queryset = ApprovalRule.objects.filter(is_deleted=False)
    serializer_class = ApprovalRuleSerializer
    filterset_class = ApprovalRuleFilter
    permission_classes = [IsAuthenticated, HasMutateButtonPermission]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ApprovalRuleCreateSerializer
        return ApprovalRuleSerializer

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def by_scope(self, request):
        """按作用域查询规则（前端配置页合并视图用）

        GET /api/admin/release/approval-rules/by_scope/?project_id=1&application_id=2&environment=production
        返回：应用级 + 项目级 + 全局规则，前端可展示三级继承视图
        """
        from django.db.models import Q
        project_id = request.query_params.get('project_id')
        application_id = request.query_params.get('application_id')
        environment = request.query_params.get('environment')

        qs = ApprovalRule.objects.filter(is_deleted=False, status=1)
        if environment:
            qs = qs.filter(environment=environment)

        if application_id:
            qs = qs.filter(
                Q(application_id=application_id)
                | Q(project_id=project_id, application__isnull=True)
                | Q(project__isnull=True, application__isnull=True)
            )
        elif project_id:
            qs = qs.filter(
                Q(project_id=project_id, application__isnull=True)
                | Q(project__isnull=True, application__isnull=True)
            )

        qs = qs.order_by('application_id', 'project_id', '-create_time')
        serializer = self.get_serializer(qs, many=True)
        return Response({"code": 0, "data": serializer.data})

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def effective(self, request):
        """查询某应用某环境的生效规则（审批引擎匹配结果预览）

        GET /api/admin/release/approval-rules/effective/?application_id=2&environment=production
        """
        app_id = request.query_params.get('application_id')
        env = request.query_params.get('environment')
        if not app_id or not env:
            return Response(
                {"error": "application_id 和 environment 为必填"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        app = get_object_or_404(Application, pk=app_id)
        # 临时构造 release 用于匹配（不落库）
        tmp = ReleaseRecord(application=app, environment=env)
        rule, scope = ApprovalEngine._match_rule(tmp)

        return Response({
            "code": 0,
            "data": {
                "scope": scope,
                "rule": ApprovalRuleSerializer(rule).data if rule else None,
                "message": "匹配到规则" if rule else "无规则，将免审直发",
            }
        })


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
    if not user_has_scope_access(request.user, 'project', application.project_id):
        return Response(
            {"error": "无权限操作该应用"},
            status=status.HTTP_403_FORBIDDEN
        )

    serializer = ReleaseCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    data = serializer.validated_data
    branch = data['branch']
    environment = data['environment']

    # 获取环境策略：决定是否需要审批
    strategy = EnvironmentStrategy.objects.filter(
        environment=environment,
        status=1  # 启用状态
    ).first()
    require_approval = bool(strategy and strategy.requires_approval)

    # 创建发布记录
    release = ReleaseRecord.objects.create(
        application=application,
        branch=branch,
        environment=environment,
        version=data.get('version') or None,
        require_approval=require_approval,
        status='pending',
        released_by=request.user.username,
        remark=data.get('remark', '')
    )

    # 先尝试匹配审批规则（无论环境策略是否要求审批，配了规则就应走审批）
    engine = ApprovalEngine.init_for_release(release)
    if engine:
        # 匹配到规则，进入待审批
        if not release.require_approval:
            release.require_approval = True
            release.save(update_fields=['require_approval'])
        notify_approval_pending(release)
        return Response({
            "code": 0,
            "data": {
                "id": release.id,
                "status": "approval_pending",
                "status_display": release.get_status_display(),
                "scope": release.approval_scope,
                "rule": release.approval_rule.code if release.approval_rule else None,
                "rule_name": release.approval_rule.name if release.approval_rule else None,
                "current_approver_ids": release.current_approver_ids,
                "required_count": release.required_count,
                "message": "发布已创建，等待审批"
            }
        })
    # 未匹配到规则
    if require_approval:
        # 环境策略要求审批但无匹配规则 → 降级为免审直发
        release.require_approval = False
        release.save(update_fields=['require_approval'])

    # 免审 → 直接触发构建
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
        resp_status = 'building'
        message = '发布已创建，构建已触发'
    except Exception as e:
        # Jenkins/Celery 服务异常
        release.status = 'build_failed'
        release.status_message = f'触发构建失败: {str(e)}'
        release.save(update_fields=['status', 'status_message'])
        resp_status = 'build_failed'
        message = f'发布已创建，但触发构建失败: {str(e)}'

    return Response({
        "code": 0,
        "data": {
            "id": release.id,
            "status": resp_status,
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
    if not user_has_scope_access(request.user, 'project', application.project_id):
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
    if not user_has_scope_access(request.user, 'project', application.project_id):
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
