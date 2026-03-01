# -*- coding: utf-8 -*-
"""
同步日志视图
"""
from django_filters.rest_framework import DjangoFilterBackend
from utils.custom_model_viewSet import CustomModelViewSet
from ..models import SyncLog
from ..serializers import SyncLogSerializer
from ..filters import SyncLogFilter


class SyncLogViewSet(CustomModelViewSet):
    """同步日志管理"""
    queryset = SyncLog.objects.all()
    serializer_class = SyncLogSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = SyncLogFilter
    search_fields = ["resource_name"]
    ordering_fields = ["create_time"]

    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            "config_package", "project", "module", "app"
        )
        return queryset

    # 同步日志只读
    http_method_names = ['get', 'head', 'options']
