# -*- coding: utf-8 -*-
__all__ = [
    'ProjectViewSet',
    'ModuleViewSet',
    'ApplicationViewSet',
    'ConfigPackageViewSet',
    'SyncLogViewSet',
    'TemplateViewSet',
    # CI/CD 模板系统
    'PipelineTemplateViewSet',
    'PipelineTemplateVersionViewSet',
    'ApplicationPipelineConfigViewSet',
    'ApplicationPipelineVersionViewSet',
    'EnvironmentStrategyViewSet',
    'CDConfigExportViewSet',
    # 发布管理
    'ReleaseRecordViewSet',
    'ApprovalRuleViewSet',
    # 发布 API
    'trigger_release',
    'get_app_branches',
    'get_app_environments',
    'get_approval_rules',
    # 发布统计
    'get_statistics',
    'get_trend',
    'get_app_rank',
]

from .project import ProjectViewSet
from .module import ModuleViewSet
from .application import ApplicationViewSet
from .config_package import ConfigPackageViewSet
from .sync_log import SyncLogViewSet
from .template import TemplateViewSet
# CI/CD 模板系统
from .pipeline_template import PipelineTemplateViewSet, PipelineTemplateVersionViewSet
from .application_pipeline import ApplicationPipelineConfigViewSet, ApplicationPipelineVersionViewSet
from .environment_strategy import EnvironmentStrategyViewSet
from .cd_config_export import CDConfigExportViewSet
# 发布管理
from .release import (
    ReleaseRecordViewSet, ApprovalRuleViewSet,
    trigger_release, get_app_branches, get_app_environments, get_approval_rules
)
# 发布统计
from .statistics import get_statistics, get_trend, get_app_rank
