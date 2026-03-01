# -*- coding: utf-8 -*-
"""
应用流水线配置视图
"""
import re
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from utils.custom_model_viewSet import CustomModelViewSet
from ..models import (
    ApplicationPipelineConfig, ApplicationPipelineVersion,
    PipelineTemplate, PipelineTemplateVersion, Application
)
from ..serializers import (
    ApplicationPipelineConfigSerializer, ApplicationPipelineConfigCreateSerializer,
    ApplicationPipelineVersionSerializer, ValidateNamingSerializer, GenerateNamesSerializer
)
from ..filters import ApplicationPipelineConfigFilter, ApplicationPipelineVersionFilter


class ApplicationPipelineConfigViewSet(CustomModelViewSet):
    """应用流水线配置管理"""
    queryset = ApplicationPipelineConfig.objects.all()
    serializer_class = ApplicationPipelineConfigSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ApplicationPipelineConfigFilter
    search_fields = ["application__name", "application__code"]
    ordering_fields = ["create_time", "application__name"]
    enable_soft_delete = True

    action_serializers = {
        "create": ApplicationPipelineConfigCreateSerializer,
        "update": ApplicationPipelineConfigCreateSerializer,
    }

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.enable_soft_delete:
            queryset = queryset.filter(is_deleted=False)
        return queryset.select_related(
            'application', 'template', 'template_version'
        )

    def perform_create(self, serializer):
        """创建时自动设置创建人"""
        serializer.save(creator=self.request.user.username)

    def perform_update(self, serializer):
        """更新时自动设置修改人并创建新版本"""
        instance = serializer.instance
        # 增加版本号
        new_version = instance.current_version + 1
        serializer.save(
            modifier=self.request.user.username,
            current_version=new_version
        )

    @action(detail=True, methods=['get'])
    def versions(self, request, pk=None):
        """获取配置版本历史"""
        config = self.get_object()
        queryset = config.versions.all().order_by('-version')
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ApplicationPipelineVersionSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = ApplicationPipelineVersionSerializer(queryset, many=True)
        return Response({'code': 0, 'data': serializer.data})

    @action(detail=True, methods=['post'])
    def generate(self, request, pk=None):
        """生成 Jenkinsfile"""
        config = self.get_object()
        
        # 获取模板内容
        if config.template_version:
            template_content = config.template_version.content
            template_variables = config.template_version.variables
        elif config.template:
            latest_version = config.template.latest_version
            if latest_version:
                template_content = latest_version.content
                template_variables = latest_version.variables
            else:
                return Response({'code': 1, 'message': '模板没有可用版本'}, status=status.HTTP_400_BAD_REQUEST)
        elif config.custom_content:
            template_content = config.custom_content
            template_variables = {}
        else:
            return Response({'code': 1, 'message': '未配置模板或自定义内容'}, status=status.HTTP_400_BAD_REQUEST)
        
        # 合并变量：模板默认值 + 用户配置值
        final_variables = {}
        if template_variables and isinstance(template_variables, dict):
            for var in template_variables.get('variables', []):
                var_name = var.get('name')
                if var_name:
                    final_variables[var_name] = var.get('default', '')
        
        # 用户配置覆盖默认值
        if config.variables:
            final_variables.update(config.variables)
        
        # 替换变量
        content = template_content
        for key, value in final_variables.items():
            content = content.replace(f'${{{key}}}', str(value))
        
        # 创建配置版本
        new_version = config.current_version + 1
        app_version = ApplicationPipelineVersion.objects.create(
            config=config,
            version=new_version,
            content=content,
            variables_snapshot=final_variables,
            stages_snapshot=config.stages_config,
            generated_by=request.user.username
        )
        
        # 更新配置的当前版本号
        config.current_version = new_version
        config.save()
        
        return Response({
            'code': 0,
            'data': {
                'version': new_version,
                'version_id': app_version.id,
                'content': content
            }
        })

    @action(detail=True, methods=['post'])
    def rollback(self, request, pk=None):
        """回滚到历史版本"""
        config = self.get_object()
        target_version = request.data.get('target_version')

        if not target_version:
            return Response({'code': 1, 'message': '请指定目标版本'}, status=status.HTTP_400_BAD_REQUEST)

        # 查找目标版本
        try:
            version = config.versions.get(version=target_version)
        except ApplicationPipelineVersion.DoesNotExist:
            return Response({'code': 1, 'message': '目标版本不存在'}, status=status.HTTP_404_NOT_FOUND)

        # 恢复配置
        config.variables = version.variables_snapshot
        config.stages_config = version.stages_snapshot
        config.save(modifier=request.user.username)

        return Response({
            'code': 0,
            'message': f'已回滚到版本 v{target_version}'
        })

    @action(detail=True, methods=['post'])
    def sync_to_jenkins(self, request, pk=None):
        """
        同步配置到 Jenkins

        将当前配置的 Jenkinsfile 同步到 Jenkins Job
        """
        from ..tasks import sync_jenkins_config

        config = self.get_object()

        # 检查是否有可用版本
        latest_version = config.get_config_version()
        if not latest_version:
            return Response({
                'code': 1,
                'message': '请先生成 Jenkinsfile 版本'
            }, status=status.HTTP_400_BAD_REQUEST)

        # 触发异步同步任务
        task = sync_jenkins_config.delay(config.id)

        return Response({
            'code': 0,
            'data': {
                'task_id': task.id,
                'message': '同步任务已提交，请稍后查看状态'
            }
        })

    @action(detail=True, methods=['get'])
    def sync_status(self, request, pk=None):
        """获取同步状态"""
        config = self.get_object()

        return Response({
            'code': 0,
            'data': {
                'sync_status': config.jenkins_sync_status,
                'sync_status_display': config.get_jenkins_sync_status_display(),
                'sync_time': config.jenkins_sync_time,
                'sync_message': config.jenkins_sync_message,
                'jenkins_job_name': config.jenkins_job_name
            }
        })

    @action(detail=True, methods=['post'])
    def generate_and_sync(self, request, pk=None):
        """
        生成 Jenkinsfile 并同步到 Jenkins

        一键操作：生成新版本 + 触发同步
        """
        from ..tasks import sync_jenkins_config

        config = self.get_object()

        # 获取模板内容
        if config.template_version:
            template_content = config.template_version.content
            template_variables = config.template_version.variables
        elif config.template:
            latest_version = config.template.latest_version
            if latest_version:
                template_content = latest_version.content
                template_variables = latest_version.variables
            else:
                return Response({'code': 1, 'message': '模板没有可用版本'}, status=status.HTTP_400_BAD_REQUEST)
        elif config.custom_content:
            template_content = config.custom_content
            template_variables = {}
        else:
            return Response({'code': 1, 'message': '未配置模板或自定义内容'}, status=status.HTTP_400_BAD_REQUEST)

        # 合并变量
        final_variables = {}
        if template_variables and isinstance(template_variables, dict):
            for var in template_variables.get('variables', []):
                var_name = var.get('name')
                if var_name:
                    final_variables[var_name] = var.get('default', '')

        if config.variables:
            final_variables.update(config.variables)

        # 替换变量
        content = template_content
        for key, value in final_variables.items():
            content = content.replace(f'${{{key}}}', str(value))

        # 创建配置版本
        new_version = config.current_version + 1
        app_version = ApplicationPipelineVersion.objects.create(
            config=config,
            version=new_version,
            content=content,
            variables_snapshot=final_variables,
            stages_snapshot=config.stages_config,
            generated_by=request.user.username
        )

        # 更新配置的当前版本号
        config.current_version = new_version
        config.jenkins_sync_status = 0  # 待同步
        config.save(update_fields=['current_version', 'jenkins_sync_status'])

        # 触发同步任务
        task = sync_jenkins_config.delay(config.id)

        return Response({
            'code': 0,
            'data': {
                'version': new_version,
                'version_id': app_version.id,
                'content': content,
                'task_id': task.id,
                'message': 'Jenkinsfile 已生成，正在同步到 Jenkins...'
            }
        })


class ApplicationPipelineVersionViewSet(CustomModelViewSet):
    """应用配置版本管理"""
    queryset = ApplicationPipelineVersion.objects.all()
    serializer_class = ApplicationPipelineVersionSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ApplicationPipelineVersionFilter
    ordering_fields = ["create_time", "version"]
    enable_soft_delete = True

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.enable_soft_delete:
            queryset = queryset.filter(is_deleted=False)
        return queryset.select_related('config', 'config__application')

    @action(detail=True, methods=['get'])
    def content(self, request, pk=None):
        """获取版本内容"""
        version = self.get_object()
        return Response({
            'code': 0,
            'data': {
                'content': version.content,
                'variables': version.variables_snapshot,
                'stages': version.stages_snapshot
            }
        })


# ============================================================
# 命名验证 API
# ============================================================

# 命名规则配置
PROJECT_NAME_RULES = {
    "pattern": r"^[a-z][a-z0-9_]*$",
    "forbidden_chars": ["-"],
    "min_length": 2,
    "max_length": 32,
}

MODULE_NAME_RULES = {
    "pattern": r"^[a-z][a-z0-9_]*$",
    "forbidden_chars": ["-"],
    "min_length": 2,
    "max_length": 32,
}

APP_NAME_RULES = {
    "pattern": r"^[a-z][a-z0-9_-]*$",
    "min_length": 2,
    "max_length": 64,
}


def validate_naming(type: str, name: str) -> dict:
    """验证命名是否符合规范"""
    errors = []
    suggestion = None
    
    if type == "project":
        rules = PROJECT_NAME_RULES
        type_name = "项目"
    elif type == "module":
        rules = MODULE_NAME_RULES
        type_name = "模块"
    else:
        rules = APP_NAME_RULES
        type_name = "应用"
    
    # 长度检查
    if len(name) < rules["min_length"]:
        errors.append({
            "field": "name",
            "message": f"{type_name}名称长度不能小于 {rules['min_length']} 个字符",
            "rule": "min_length"
        })
    if len(name) > rules["max_length"]:
        errors.append({
            "field": "name",
            "message": f"{type_name}名称长度不能超过 {rules['max_length']} 个字符",
            "rule": "max_length"
        })
    
    # 禁止字符检查
    if "forbidden_chars" in rules:
        for char in rules["forbidden_chars"]:
            if char in name:
                errors.append({
                    "field": "name",
                    "message": f"{type_name}名称不能包含 '{char}' 字符",
                    "rule": "forbidden_chars"
                })
                # 生成建议
                if suggestion is None:
                    suggestion = name.replace(char, "_")
    
    # 正则匹配
    if not re.match(rules["pattern"], name):
        errors.append({
            "field": "name",
            "message": f"{type_name}名称格式不正确，只能包含小写字母、数字和下划线" + ("和连字符" if type == "app" else ""),
            "rule": "pattern"
        })
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "suggestion": suggestion
    }


def generate_standard_names(project: str, module: str, app: str, version: str = "latest", environment: str = "dev") -> dict:
    """生成标准化资源名称"""
    env_tag = environment
    if version != "latest":
        tag = f"{version}-{env_tag}"
    else:
        tag = env_tag
    
    return {
        "gitlab": {
            "group": project,
            "subgroup": f"{project}/{module}",
            "repository": f"{project}/{module}/{app}"
        },
        "harbor": {
            "project": f"{project}-{module}",
            "image": f"{project}-{module}/{app}",
            "tag": tag
        },
        "jenkins": {
            "folder": f"{project}/{module}",
            "job": f"{project}/{module}/{app}/{env_tag}"
        },
        "ansible": {
            "inventory": f"inventory/{project}/{module}/{app}/{env_tag}"
        }
    }
