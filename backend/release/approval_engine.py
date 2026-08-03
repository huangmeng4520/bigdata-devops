# -*- coding: utf-8 -*-
"""
审批引擎：三级作用域规则匹配 + 4 种流转策略（single/any/all/sequential）
"""
from datetime import timedelta

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from .models import ApprovalRule, ApprovalRecord


class ApprovalEngine:
    """审批流转引擎

    使用方式：
        # 发布创建时初始化
        engine = ApprovalEngine.init_for_release(release)

        # 审批时调用
        engine = ApprovalEngine(release)
        result = engine.apply_approval(user, approved=True, comment='同意')
    """

    def __init__(self, release):
        self.release = release
        self.rule = release.approval_rule

    # ========== 规则匹配（三级回退） ==========
    @classmethod
    def _match_rule(cls, release):
        """按 应用 → 项目 → 全局 优先级匹配审批规则

        返回 (rule, scope) 或 (None, None)
        """
        app = release.application
        env = release.environment

        # 1. 应用级（最优先）
        rule = ApprovalRule.objects.filter(
            application=app, environment=env,
            status=1, is_deleted=False,
        ).first()
        if rule:
            return rule, 'application'

        # 2. 项目级
        if app.project_id:
            rule = ApprovalRule.objects.filter(
                project=app.project, application__isnull=True,
                environment=env, status=1, is_deleted=False,
            ).first()
            if rule:
                return rule, 'project'

        # 3. 全局兜底
        rule = ApprovalRule.objects.filter(
            project__isnull=True, application__isnull=True,
            environment=env, status=1, is_deleted=False,
        ).first()
        return (rule, 'global') if rule else (None, None)

    @classmethod
    @transaction.atomic
    def init_for_release(cls, release):
        """发布创建时初始化审批单

        返回 ApprovalEngine 实例；若未匹配到规则返回 None（视为免审）
        """
        rule, scope = cls._match_rule(release)
        if not rule:
            return None

        release.approval_rule = rule
        release.approval_scope = scope
        release.approval_type = rule.rule_type
        release.approvers = rule.approvers
        release.required_count = cls._calc_required(rule)
        release.approved_count = 0
        release.current_approver_ids = cls._current_approvers(rule, [])
        release.status = 'approval_pending'
        if rule.timeout_hours:
            release.approval_deadline = timezone.now() + timedelta(hours=rule.timeout_hours)
        release.save()
        return cls(release)

    @staticmethod
    def _calc_required(rule):
        """根据规则类型计算需通过数"""
        return {
            'single': 1,
            'any': rule.min_approvers,
            'all': len(rule.approvers),
            'sequential': len(rule.approvers),
        }[rule.rule_type]

    @staticmethod
    def _current_approvers(rule, already_approved_ids):
        """计算当前可审批人 ID 列表"""
        if not rule:
            # 规则缺失（如历史数据 approval_rule=None），无法计算后续审批人，清空列表
            return []
        if rule.rule_type == 'sequential':
            # 顺序审批：只剩顺序最靠前未审批的人
            remaining = [
                a for a in rule.approvers
                if a.get('user_id') not in already_approved_ids
            ]
            return [remaining[0]['user_id']] if remaining else []
        # single / any / all：所有未审批的人都是当前审批人
        return [
            a['user_id'] for a in rule.approvers
            if a.get('user_id') not in already_approved_ids
        ]

    # ========== 流转判定 ==========
    def can_user_approve(self, user_id):
        """用户是否在当前审批人列表中"""
        return user_id in (self.release.current_approver_ids or [])

    def _approved_ids(self):
        """已通过审批人 ID 列表"""
        return list(
            self.release.approval_records
            .filter(action='approve')
            .values_list('approver_id', flat=True)
        )

    def _order_of(self, user_id):
        """获取审批人在顺序中的位置"""
        if not self.rule:
            return 0
        for a in self.rule.approvers:
            if a.get('user_id') == user_id:
                return a.get('order', 0)
        return 0

    @transaction.atomic
    def apply_approval(self, user, approved, comment=''):
        """处理一次审批动作

        返回 'approved' / 'rejected' / 'pending'
        """
        if not self.can_user_approve(user.id):
            raise PermissionDenied("您不在当前审批人列表中")

        # 写留痕
        ApprovalRecord.objects.create(
            release=self.release, rule=self.rule,
            approver_id=user.id, approver_name=user.username,
            order=self._order_of(user.id),
            action='approve' if approved else 'reject',
            comment=comment,
            acted_at=timezone.now(),
        )

        if not approved:
            self.release.status = 'rejected'
            self.release.approval_user = user.username
            self.release.approval_time = timezone.now()
            self.release.approval_comment = comment
            self.release.status_message = f'被 {user.username} 拒绝'
            self.release.save()
            return 'rejected'

        # 通过
        self.release.approved_count += 1
        approved_ids = self._approved_ids() + [user.id]
        self.release.current_approver_ids = self._current_approvers(self.rule, approved_ids)

        if self.release.approved_count >= self.release.required_count:
            # 审批完成
            self.release.status = 'approved'
            self.release.approval_time = timezone.now()
            self.release.approval_user = user.username
            self.release.approval_comment = comment
            self.release.status_message = '审批通过，自动触发构建'
            self.release.save()
            # 自动触发 Jenkins 构建
            from .tasks import trigger_jenkins_build
            trigger_jenkins_build.delay(self.release.id)
            return 'approved'

        # 等待其他审批人
        self.release.status_message = f'已通过 {self.release.approved_count}/{self.release.required_count}'
        self.release.save()
        return 'pending'
