# -*- coding: utf-8 -*-
"""
发布统计视图
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta

from ..models import ReleaseRecord


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_statistics(request):
    """
    获取发布统计数据
    
    GET /api/admin/release/statistics/
    """
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')
    
    # 默认最近30天
    if not end_date:
        end_date = timezone.now().date()
    else:
        end_date = timezone.datetime.strptime(end_date, '%Y-%m-%d').date()
    
    if not start_date:
        start_date = end_date - timedelta(days=30)
    else:
        start_date = timezone.datetime.strptime(start_date, '%Y-%m-%d').date()
    
    # 基础查询集
    queryset = ReleaseRecord.objects.filter(
        create_time__date__gte=start_date,
        create_time__date__lte=end_date
    )
    
    # 总体统计
    total_count = queryset.count()
    success_count = queryset.filter(status='build_success').count()
    failed_count = queryset.filter(status='build_failed').count()
    pending_count = queryset.filter(status__in=['pending', 'approval_pending', 'building']).count()
    
    # 环境统计
    env_stats = queryset.values('environment').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # 状态统计
    status_stats = queryset.values('status').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # 今日发布数
    today = timezone.now().date()
    today_count = ReleaseRecord.objects.filter(
        create_time__date=today
    ).count()
    
    # 本周发布数
    week_start = today - timedelta(days=today.weekday())
    week_count = ReleaseRecord.objects.filter(
        create_time__date__gte=week_start
    ).count()
    
    return Response({
        'code': 0,
        'data': {
            'total': total_count,
            'success': success_count,
            'failed': failed_count,
            'pending': pending_count,
            'today': today_count,
            'week': week_count,
            'success_rate': round(success_count / total_count * 100, 2) if total_count > 0 else 0,
            'environment_stats': list(env_stats),
            'status_stats': list(status_stats),
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_trend(request):
    """
    获取发布趋势数据
    
    GET /api/admin/release/statistics/trend/
    """
    days = int(request.query_params.get('days', 30))
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)
    
    # 按日期分组统计
    trend_data = ReleaseRecord.objects.filter(
        create_time__date__gte=start_date,
        create_time__date__lte=end_date
    ).annotate(
        date=TruncDate('create_time')
    ).values('date').annotate(
        total=Count('id'),
        success=Count('id', filter=Q(status='build_success')),
        failed=Count('id', filter=Q(status='build_failed')),
    ).order_by('date')
    
    # 填充没有数据的日期
    date_list = []
    current_date = start_date
    trend_dict = {item['date']: item for item in trend_data}
    
    while current_date <= end_date:
        if current_date in trend_dict:
            date_list.append(trend_dict[current_date])
        else:
            date_list.append({
                'date': current_date,
                'total': 0,
                'success': 0,
                'failed': 0,
            })
        current_date += timedelta(days=1)

    # 按最近时间倒序排列，便于在表格中优先查看最新数据
    date_list.reverse()

    return Response({
        'code': 0,
        'data': date_list,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_app_rank(request):
    """
    获取应用发布排行
    
    GET /api/admin/release/statistics/app-rank/
    """
    limit = int(request.query_params.get('limit', 10))
    days = int(request.query_params.get('days', 30))
    
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)
    
    # 按应用分组统计
    app_stats = ReleaseRecord.objects.filter(
        create_time__date__gte=start_date,
        create_time__date__lte=end_date
    ).values(
        'application__id',
        'application__name',
        'application__code',
        'application__project__name',
        'application__module__name',
    ).annotate(
        total=Count('id'),
        success=Count('id', filter=Q(status='build_success')),
        failed=Count('id', filter=Q(status='build_failed')),
    ).order_by('-total')[:limit]
    
    return Response({
        'code': 0,
        'data': list(app_stats),
    })
