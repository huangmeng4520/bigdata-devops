# -*- coding: utf-8 -*-
"""
CD配置导出视图
"""
import json
import re
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from utils.custom_model_viewSet import CustomModelViewSet
from utils.data_permission import DataPermissionMixin
from utils.permissions import HasMutateButtonPermission
from ..models import CDConfigExport, ApplicationPipelineConfig, ApplicationPipelineVersion, Application
from ..serializers import CDConfigExportSerializer, CDConfigExportCreateSerializer
from ..filters import CDConfigExportFilter


class CDConfigExportViewSet(DataPermissionMixin, CustomModelViewSet):
    """CD配置导出管理"""
    queryset = CDConfigExport.objects.all()
    serializer_class = CDConfigExportSerializer
    permission_classes = [HasMutateButtonPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_class = CDConfigExportFilter
    search_fields = ["application__name", "application__code"]
    ordering_fields = ["create_time"]
    enable_soft_delete = True

    # 数据权限：按所属应用→项目级联隔离
    scope_type = 'project'
    scope_field = 'application__project_id'

    action_serializers = {
        "create": CDConfigExportCreateSerializer,
    }

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.enable_soft_delete:
            queryset = queryset.filter(is_deleted=False)
        queryset = queryset.select_related('application')
        return self.data_permission_filter(queryset)

    def perform_create(self, serializer):
        """创建时自动设置创建人"""
        serializer.save(exported_by=self.request.user.username)

    def perform_update(self, serializer):
        self.check_object_data_permission(serializer.instance)
        serializer.save()

    def perform_destroy(self, instance):
        self.check_object_data_permission(instance)
        super().perform_destroy(instance)

    @action(detail=True, methods=['post'])
    def download(self, request, pk=None):
        """下载导出文件并增加下载次数"""
        export = self.get_object()
        export.download_count += 1
        export.save()
        
        return Response({
            'code': 0,
            'data': {
                'content': export.content,
                'format': export.export_format,
                'filename': self._generate_filename(export)
            }
        })

    @action(detail=True, methods=['get'])
    def jenkinsfile(self, request, pk=None):
        """获取 Jenkinsfile 内容"""
        export = self.get_object()
        return Response({
            'code': 0,
            'data': {
                'content': export.content
            }
        })

    @action(detail=True, methods=['get'])
    def json_config(self, request, pk=None):
        """获取 JSON 配置"""
        export = self.get_object()
        return Response({
            'code': 0,
            'data': {
                'content': export.content
            }
        })

    def _generate_filename(self, export: CDConfigExport) -> str:
        """生成文件名"""
        app = export.application
        ext_map = {
            'jenkinsfile': 'groovy',
            'json': 'json',
            'yaml': 'yaml',
            'zip': 'zip'
        }
        ext = ext_map.get(export.export_format, 'txt')
        return f"{app.code}-{export.environment}-v{export.config_version}.{ext}"


def generate_jenkinsfile_cd(application: Application, environment: str, config_version: int = None) -> str:
    """生成 CD Jenkinsfile"""
    
    # 获取应用配置
    try:
        config = ApplicationPipelineConfig.objects.get(
            application=application,
            environment=environment
        )
    except ApplicationPipelineConfig.DoesNotExist:
        raise ValueError(f"应用 {application.name} 未配置 {environment} 环境的 Pipeline 配置")
    
    # 获取版本
    if config_version:
        version = config.versions.filter(version=config_version).first()
    else:
        version = config.versions.order_by('-version').first()
    
    if not version:
        raise ValueError(f"应用 {application.name} 没有可用的配置版本")
    
    # 获取项目信息
    project = application.project
    module = application.module
    
    # 生成标准名称
    harbor_project = f"{project.code}-{module.code}"
    image_tag = f"{harbor_project}/{application.code}"
    inventory_path = f"inventory/{project.code}/{module.code}/{application.code}/{environment}"
    
    # 生成 Jenkinsfile 内容（使用字符串拼接避免缩进问题）
    jenkinsfile = f"""// 自动生成的 CD 流水线
// 应用: {application.name}
// 环境: {environment}
// 版本: v{version.version}
// 生成时间: {version.create_time.strftime("%Y-%m-%d %H:%M:%S")}

pipeline {{
    agent {{
        label 'ansible'
    }}

    environment {{
        APP_NAME = '{application.code}'
        ENVIRONMENT = '{environment}'
        HARBOR_PROJECT = '{harbor_project}'
        IMAGE_NAME = '{image_tag}'
        ANSIBLE_INVENTORY = '{inventory_path}'
        PLAYBOOK_PATH = 'playbooks/deploy-docker.yml'
    }}

    stages {{
        stage('镜像确认') {{
            steps {{
                script {{
                    echo "确认镜像: ${{IMAGE_NAME}}:${{IMAGE_TAG}}"
                }}
            }}
        }}

        stage('部署前检查') {{
            steps {{
                sh '''
ansible --version
ansible all -i ${{ANSIBLE_INVENTORY}} -m ping || true
'''
            }}
        }}

        stage('部署容器') {{
            steps {{
                sh '''
ansible-playbook -i ${{ANSIBLE_INVENTORY}} ${{PLAYBOOK_PATH}} \\
    -e "app_name=${{APP_NAME}}" \\
    -e "environment=${{ENVIRONMENT}}" \\
    -e "image_name=${{IMAGE_NAME}}" \\
    -e "image_tag=${{IMAGE_TAG}}" \\
    -v
'''
            }}
        }}

        stage('健康检查') {{
            steps {{
                sh '''
ansible all -i ${{ANSIBLE_INVENTORY}} -m shell \\
    -a "docker ps --filter name=${{APP_NAME}} --format '{{{{.Status}}}}'"
'''
            }}
        }}
    }}

    post {{
        success {{
            echo '部署成功'
        }}
        failure {{
            echo '部署失败'
        }}
    }}
}}
"""
    return jenkinsfile, version.version


def generate_deploy_config(application: Application, environment: str, config_version: int = None) -> dict:
    """生成部署配置 JSON"""
    
    project = application.project
    module = application.module
    
    # 获取配置
    try:
        config = ApplicationPipelineConfig.objects.get(
            application=application,
            environment=environment
        )
    except ApplicationPipelineConfig.DoesNotExist:
        raise ValueError(f"应用未配置 {environment} 环境的 Pipeline 配置")
    
    # 合并变量
    variables = config.variables or {}
    stages_config = config.stages_config or []
    
    deploy_config = {
        "application": {
            "name": application.name,
            "code": application.code,
            "type": application.app_type,
            "description": application.description
        },
        "project": {
            "name": project.name,
            "code": project.code
        },
        "module": {
            "name": module.name,
            "code": module.code
        },
        "environment": environment,
        "git": {
            "url": application.git_url,
            "branch": application.build_branch
        },
        "docker": {
            "dockerfile_path": application.dockerfile_path,
            "harbor_project": f"{project.code}-{module.code}",
            "image_name": application.code
        },
        "jenkins": {
            "folder": f"{project.code}/{module.code}/{application.code}"
        },
        "variables": variables,
        "stages_config": stages_config
    }
    
    return deploy_config
