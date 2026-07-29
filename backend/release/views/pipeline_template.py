# -*- coding: utf-8 -*-
"""
流水线模板视图
"""
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from utils.custom_model_viewSet import CustomModelViewSet
from utils.permissions import HasMutateButtonPermission
from ..models import PipelineTemplate, PipelineTemplateVersion
from ..serializers import (
    PipelineTemplateSerializer, PipelineTemplateCreateSerializer,
    PipelineTemplateDetailSerializer, PipelineTemplateVersionSerializer,
    PipelineTemplateVersionCreateSerializer
)
from ..filters import PipelineTemplateFilter, PipelineTemplateVersionFilter


class PipelineTemplateViewSet(CustomModelViewSet):
    """流水线模板管理"""
    queryset = PipelineTemplate.objects.all()
    serializer_class = PipelineTemplateSerializer
    permission_classes = [HasMutateButtonPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_class = PipelineTemplateFilter
    search_fields = ["name", "code", "language", "framework"]
    ordering_fields = ["create_time", "name"]
    enable_soft_delete = True

    action_serializers = {
        "create": PipelineTemplateCreateSerializer,
        "update": PipelineTemplateCreateSerializer,
        "retrieve": PipelineTemplateDetailSerializer,
    }

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.enable_soft_delete:
            queryset = queryset.filter(is_deleted=False)
        return queryset.prefetch_related('versions')

    def perform_create(self, serializer):
        """创建时自动设置创建人"""
        serializer.save(creator=self.request.user.username)

    def perform_update(self, serializer):
        """更新时自动设置修改人"""
        serializer.save(modifier=self.request.user.username)

    @action(detail=True, methods=['get'])
    def versions(self, request, pk=None):
        """获取模板版本列表"""
        template = self.get_object()
        queryset = template.versions.filter(is_deleted=False).order_by('-create_time')
        
        serializer = PipelineTemplateVersionSerializer(queryset, many=True)
        return Response({'code': 0, 'data': {'items': serializer.data, 'total': queryset.count()}})

    @action(detail=True, methods=['post'])
    def create_version(self, request, pk=None):
        """创建模板新版本"""
        template = self.get_object()
        
        # 检查版本号是否已存在
        version = request.data.get('version')
        if PipelineTemplateVersion.objects.filter(template=template, version=version).exists():
            return Response({'code': 1, 'message': f'版本 {version} 已存在'}, status=status.HTTP_400_BAD_REQUEST)
        
        # 如果设置为最新版本，先取消其他版本的最新标记
        is_latest = request.data.get('is_latest', False)
        if is_latest:
            PipelineTemplateVersion.objects.filter(template=template).update(is_latest=False)
        
        # 复制请求数据并添加 template
        data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
        data['template'] = template.id
        
        serializer = PipelineTemplateVersionCreateSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save(creator=request.user.username)
        
        return Response({'code': 0, 'message': '版本创建成功', 'data': serializer.data})

    @action(detail=True, methods=['post'])
    def preview(self, request, pk=None):
        """预览生成的 Jenkinsfile"""
        template = self.get_object()
        variables = request.data.get('variables', {})
        stages_config = request.data.get('stages_config', [])
        
        # 获取最新版本或指定版本
        version_id = request.data.get('version_id')
        if version_id:
            template_version = PipelineTemplateVersion.objects.filter(
                id=version_id, template=template
            ).first()
        else:
            template_version = template.latest_version
        
        if not template_version:
            return Response({'code': 1, 'message': '未找到模板版本'}, status=status.HTTP_404_NOT_FOUND)
        
        # 替换变量生成预览内容
        content = template_version.content
        for key, value in variables.items():
            content = content.replace(f'${{{key}}}', str(value))
        
        return Response({
            'code': 0,
            'data': {
                'content': content,
                'variables': variables,
                'stages': template_version.stages
            }
        })

    @action(detail=True, methods=['post'])
    def copy(self, request, pk=None):
        """复制模板"""
        template = self.get_object()
        new_name = request.data.get('name', f"{template.name}_copy")
        new_code = request.data.get('code', f"{template.code}_copy")
        
        # 检查编码是否已存在
        if PipelineTemplate.objects.filter(code=new_code, is_deleted=False).exists():
            return Response({'code': 1, 'message': f'模板编码 {new_code} 已存在'}, status=status.HTTP_400_BAD_REQUEST)
        
        # 复制模板
        new_template = PipelineTemplate.objects.create(
            name=new_name,
            code=new_code,
            language=template.language,
            language_version=template.language_version,
            framework=template.framework,
            description=template.description,
            is_official=False,
            status=template.status,
            creator=request.user.username
        )
        
        # 复制最新版本
        latest_version = template.latest_version
        if latest_version:
            PipelineTemplateVersion.objects.create(
                template=new_template,
                version="1.0.0",
                content=latest_version.content,
                variables=latest_version.variables,
                stages=latest_version.stages,
                stages_content=latest_version.stages_content,
                change_log="从模板复制",
                is_latest=True,
                status=latest_version.status,
                creator=request.user.username
            )
        
        return Response({'code': 0, 'message': '复制成功', 'data': {'id': new_template.id}})

    @action(detail=True, methods=['get'])
    def export_config(self, request, pk=None):
        """导出模板配置"""
        template = self.get_object()
        latest_version = template.latest_version
        
        export_data = {
            'template': {
                'name': template.name,
                'code': template.code,
                'language': template.language,
                'language_version': template.language_version,
                'framework': template.framework,
                'description': template.description,
            },
            'version': {
                'version': latest_version.version if latest_version else '1.0.0',
                'content': latest_version.content if latest_version else '',
                'variables': latest_version.variables if latest_version else {},
                'stages': latest_version.stages if latest_version else [],
                'stages_content': latest_version.stages_content if latest_version else {},
            } if latest_version else None
        }
        
        return Response({'code': 0, 'data': export_data})

    @action(detail=False, methods=['post'])
    def import_config(self, request):
        """导入模板配置"""
        import_data = request.data
        template_data = import_data.get('template', {})
        version_data = import_data.get('version')
        
        # 检查编码是否已存在
        code = template_data.get('code')
        if PipelineTemplate.objects.filter(code=code, is_deleted=False).exists():
            return Response({'code': 1, 'message': f'模板编码 {code} 已存在'}, status=status.HTTP_400_BAD_REQUEST)
        
        # 创建模板
        template = PipelineTemplate.objects.create(
            name=template_data.get('name'),
            code=code,
            language=template_data.get('language'),
            language_version=template_data.get('language_version', ''),
            framework=template_data.get('framework', ''),
            description=template_data.get('description', ''),
            is_official=False,
            creator=request.user.username
        )
        
        # 创建版本
        if version_data:
            PipelineTemplateVersion.objects.create(
                template=template,
                version=version_data.get('version', '1.0.0'),
                content=version_data.get('content', ''),
                variables=version_data.get('variables', {}),
                stages=version_data.get('stages', []),
                stages_content=version_data.get('stages_content', {}),
                change_log='导入',
                is_latest=True,
                creator=request.user.username
            )
        
        return Response({'code': 0, 'message': '导入成功', 'data': {'id': template.id}})


class PipelineTemplateVersionViewSet(CustomModelViewSet):
    """模板版本管理"""
    queryset = PipelineTemplateVersion.objects.all()
    serializer_class = PipelineTemplateVersionSerializer
    permission_classes = [HasMutateButtonPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_class = PipelineTemplateVersionFilter
    search_fields = ["version", "change_log"]
    ordering_fields = ["create_time", "version"]
    enable_soft_delete = True

    action_serializers = {
        "create": PipelineTemplateVersionCreateSerializer,
        "update": PipelineTemplateVersionCreateSerializer,
    }

    def retrieve(self, request, *args, **kwargs):
        """获取版本详情 - 返回统一格式"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({'code': 0, 'data': serializer.data})

    def update(self, request, *args, **kwargs):
        """更新版本 - 返回统一格式"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({'code': 0, 'message': '更新成功', 'data': serializer.data})

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.enable_soft_delete:
            queryset = queryset.filter(is_deleted=False)
        return queryset.select_related('template')

    def perform_create(self, serializer):
        """创建时自动设置创建人"""
        template = serializer.validated_data.get('template')
        is_latest = serializer.validated_data.get('is_latest', False)
        
        # 如果设置为最新版本，先取消其他版本的最新标记
        if is_latest:
            PipelineTemplateVersion.objects.filter(template=template).update(is_latest=False)
        
        serializer.save(creator=self.request.user.username)

    def perform_update(self, serializer):
        """更新时自动设置修改人"""
        instance = serializer.instance
        is_latest = serializer.validated_data.get('is_latest', False)
        
        # 如果设置为最新版本，先取消其他版本的最新标记
        if is_latest:
            PipelineTemplateVersion.objects.filter(
                template=instance.template
            ).exclude(id=instance.id).update(is_latest=False)
        
        serializer.save(modifier=self.request.user.username)

    @action(detail=True, methods=['post'])
    def set_latest(self, request, pk=None):
        """设置为最新版本"""
        version = self.get_object()
        
        # 取消同模板其他版本的最新标记
        PipelineTemplateVersion.objects.filter(
            template=version.template
        ).update(is_latest=False)
        
        # 设置当前版本为最新
        version.is_latest = True
        version.save()
        
        return Response({'code': 0, 'message': '已设置为最新版本'})

    @action(detail=True, methods=['post'])
    def auto_version(self, request, pk=None):
        """自动创建新版本（版本号自动递增）"""
        version = self.get_object()
        template = version.template
        
        # 自动递增版本号
        new_version_number = version.auto_increment_version()
        
        # 检查版本号是否已存在
        if PipelineTemplateVersion.objects.filter(template=template, version=new_version_number).exists():
            return Response({'code': 1, 'message': f'版本 {new_version_number} 已存在'}, status=status.HTTP_400_BAD_REQUEST)
        
        # 取消其他版本的最新标记
        PipelineTemplateVersion.objects.filter(template=template).update(is_latest=False)
        
        # 创建新版本
        new_version = PipelineTemplateVersion.objects.create(
            template=template,
            version=new_version_number,
            content=version.content,
            variables=version.variables,
            stages=version.stages,
            stages_content=version.stages_content,
            change_log=request.data.get('change_log', '自动版本迭代'),
            is_latest=True,
            status=version.status,
            creator=request.user.username
        )
        
        serializer = PipelineTemplateVersionSerializer(new_version)
        return Response({'code': 0, 'message': '新版本创建成功', 'data': serializer.data})

    @action(detail=True, methods=['put'])
    def update_stage(self, request, pk=None):
        """更新单个阶段的脚本"""
        version = self.get_object()
        stage_name = request.data.get('stage_name')
        stage_script = request.data.get('stage_script')
        
        if not stage_name:
            return Response({'code': 1, 'message': '阶段名称不能为空'}, status=status.HTTP_400_BAD_REQUEST)
        
        # 更新阶段脚本
        stages_content = version.stages_content or {}
        stages_content[stage_name] = stage_script
        version.stages_content = stages_content
        version.modifier = request.user.username
        version.save()
        
        return Response({'code': 0, 'message': '阶段脚本更新成功'})
