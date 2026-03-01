# -*- coding: utf-8 -*-
"""
发布模板视图
"""
from django_filters.rest_framework import DjangoFilterBackend
from utils.custom_model_viewSet import CustomModelViewSet
from ..models import Template
from ..serializers import TemplateSerializer, TemplateCreateSerializer
from ..filters import TemplateFilter


class TemplateViewSet(CustomModelViewSet):
    """发布模板管理"""
    queryset = Template.objects.all()
    serializer_class = TemplateSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = TemplateFilter
    search_fields = ["name", "code"]
    ordering_fields = ["create_time"]
    enable_soft_delete = True

    action_serializers = {
        "create": TemplateCreateSerializer,
        "update": TemplateCreateSerializer,
    }

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.enable_soft_delete:
            queryset = queryset.filter(is_deleted=False)
        return queryset

    def perform_create(self, serializer):
        """创建时自动设置创建人"""
        serializer.save(creator=self.request.user.username)

    def perform_update(self, serializer):
        """更新时自动设置修改人"""
        serializer.save(modifier=self.request.user.username)
