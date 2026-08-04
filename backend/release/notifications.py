# -*- coding: utf-8 -*-
"""
审批通知模块：按规则配置的渠道（站内信/邮件/飞书）发送通知
"""
import logging

logger = logging.getLogger(__name__)


def notify_approval_pending(release):
    """发布进入待审批时通知当前审批人"""
    if not release.approval_rule:
        return
    channels = release.approval_rule.notify_channels or ['site']
    approver_ids = release.current_approver_ids or []
    if not approver_ids:
        return

    context = _build_context(release)

    for ch in channels:
        try:
            if ch == 'site':
                _notify_site(release, approver_ids, context, 'pending')
            elif ch == 'email':
                _notify_email(release, approver_ids, context, 'pending')
            elif ch == 'feishu':
                _notify_feishu(release, approver_ids, context, 'pending')
        except Exception as e:
            logger.warning("发送 %s 审批待办通知失败: %s", ch, e)


def notify_approval_result(release, action_user, approved):
    """审批完成（通过/拒绝）时通知发布人"""
    from system.models import User
    try:
        publisher = User.objects.filter(username=release.released_by).first()
    except User.DoesNotExist:
        publisher = None

    channels = []
    if release.approval_rule:
        channels = release.approval_rule.notify_channels or ['site']

    context = _build_context(release)
    context['action_user'] = action_user.username
    context['result'] = '通过' if approved else '拒绝'

    recipient_ids = []
    if publisher:
        recipient_ids = [publisher.id]

    for ch in channels:
        try:
            if ch == 'site' and recipient_ids:
                _notify_site(release, recipient_ids, context, 'result')
            elif ch == 'email' and recipient_ids:
                _notify_email(release, recipient_ids, context, 'result')
            elif ch == 'feishu' and recipient_ids:
                _notify_feishu(release, recipient_ids, context, 'result')
        except Exception as e:
            logger.warning("发送 %s 审批结果通知失败: %s", ch, e)


def notify_approval_timeout(release):
    """审批超时通知"""
    if not release.approval_rule:
        return
    channels = release.approval_rule.notify_channels or ['site']
    context = _build_context(release)
    context['result'] = '超时'
    context['action_user'] = '系统'

    from system.models import User
    try:
        publisher = User.objects.filter(username=release.released_by).first()
    except User.DoesNotExist:
        publisher = None

    recipient_ids = [publisher.id] if publisher else []

    for ch in channels:
        try:
            if ch == 'site' and recipient_ids:
                _notify_site(release, recipient_ids, context, 'timeout')
            elif ch == 'email' and recipient_ids:
                _notify_email(release, recipient_ids, context, 'timeout')
            elif ch == 'feishu' and recipient_ids:
                _notify_feishu(release, recipient_ids, context, 'timeout')
        except Exception as e:
            logger.warning("发送 %s 超时通知失败: %s", ch, e)


def _build_context(release):
    app = release.application
    return {
        'release_id': release.id,
        'app_name': app.name if app else '-',
        'branch': release.branch,
        'environment': release.environment,
        'version': release.version or '-',
        'released_by': release.released_by,
        'rule_type': release.approval_type,
        'approved_count': release.approved_count,
        'required_count': release.required_count,
        'deadline': release.approval_deadline,
    }


def _notify_site(release, approver_ids, context, event_type):
    """站内信通知（写入 system_login_log 的类似机制，可扩展为消息表）

    此处为占位实现：实际可写入自建消息表或调用 vben Notification
    """
    logger.info(
        "[站内信] 事件=%s 接收人=%s 发布单 #%s %s -> %s",
        event_type, approver_ids, release.id, context.get('app_name'),
        context.get('result', '待审批'),
    )


def _notify_email(release, approver_ids, context, event_type):
    """邮件通知"""
    from django.core.mail import send_mail
    from system.models import User

    users = User.objects.filter(id__in=approver_ids, email__isnull=False).exclude(email='')
    if not users:
        return

    subject_map = {
        'pending': f"[发布审批] {context['app_name']} 等待您的审批",
        'result': f"[发布审批] {context['app_name']} 审批{context['result']}",
        'timeout': f"[发布审批] {context['app_name']} 审批超时",
    }
    body_map = {
        'pending': (
            f"发布单 #{release.id}\n"
            f"应用：{context['app_name']}\n"
            f"分支：{context['branch']} | 环境：{context['environment']} | 版本：{context['version']}\n"
            f"发布人：{context['released_by']}\n"
            f"请及时登录系统进行审批。"
        ),
        'result': (
            f"发布单 #{release.id}\n"
            f"应用：{context['app_name']}\n"
            f"审批人：{context['action_user']} | 结果：{context['result']}\n"
        ),
        'timeout': (
            f"发布单 #{release.id}\n"
            f"应用：{context['app_name']}\n"
            f"审批已超时，系统将按规则自动处理。"
        ),
    }

    subject = subject_map.get(event_type, '[发布审批]')
    body = body_map.get(event_type, '')

    for u in users:
        try:
            send_mail(
                subject=subject,
                message=body,
                from_email=None,
                recipient_list=[u.email],
                fail_silently=True,
            )
        except Exception as e:
            logger.warning("邮件发送失败 user=%s: %s", u.id, e)


def _notify_feishu(release, approver_ids, context, event_type):
    """飞书通知（占位）

    实际实现可通过 lark 插件 skill 发送交互卡片：
    1. 通过 RequestAuthorization 工具请求飞书授权
    2. 调用 lark-im skill 发送卡片消息
    """
    logger.info(
        "[飞书] 事件=%s 接收人=%s 发布单 #%s（占位实现，需对接 lark 插件）",
        event_type, approver_ids, release.id,
    )
