# 应用发布功能 PRD 文档

## 一、需求概述

在应用管理页面增加发布功能，支持选择分支、环境、审批流程，触发 Jenkins 构建并记录发布日志，满足审计需求。

## 二、核心业务流程

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              发布流程时序图                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  用户 ──► 选择应用 ──► 点击发布 ──► 选择分支/环境/审批 ──► 确认发布信息        │
│                                                      │                      │
│                                                      ▼                      │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│  │ 创建发布  │───►│ 审批流程  │───►│ 触发构建  │───►│ 记录日志  │              │
│  │   记录    │    │  (可选)   │    │ Jenkins  │    │ 更新状态  │              │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘              │
│                                        │                                    │
│                                        ▼                                    │
│                               ┌──────────────┐                              │
│                               │ 轮询构建状态  │                              │
│                               │ 拉取构建日志  │                              │
│                               └──────────────┘                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 三、数据模型设计

### 3.1 新增模型：ReleaseRecord（发布记录）

```python
class ReleaseRecord(CoreModel):
    """发布记录"""
    
    # 发布状态
    STATUS_CHOICES = [
        ('pending', '待发布'),
        ('approval_pending', '待审批'),
        ('approved', '已审批'),
        ('rejected', '已拒绝'),
        ('building', '构建中'),
        ('build_success', '构建成功'),
        ('build_failed', '构建失败'),
        ('deploying', '部署中'),
        ('deployed', '已部署'),
        ('rollback', '已回滚'),
        ('cancelled', '已取消'),
    ]
    
    # 关联应用
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='releases')
    
    # 发布配置
    branch = models.CharField(max_length=128, verbose_name="代码分支")
    environment = models.CharField(max_length=32, choices=ApplicationPipelineConfig.ENVIRONMENT_CHOICES, verbose_name="目标环境")
    version = models.CharField(max_length=64, blank=True, null=True, verbose_name="发布版本")
    
    # 审批信息
    require_approval = models.BooleanField(default=False, verbose_name="需要审批")
    approval_type = models.CharField(max_length=32, blank=True, null=True, verbose_name="审批类型")
    approvers = models.JSONField(default=list, blank=True, verbose_name="审批人列表")
    approval_time = models.DateTimeField(null=True, blank=True, verbose_name="审批时间")
    approval_comment = models.TextField(blank=True, null=True, verbose_name="审批意见")
    
    # Jenkins 构建信息
    jenkins_job_name = models.CharField(max_length=256, blank=True, null=True, verbose_name="Jenkins Job 名称")
    jenkins_build_number = models.IntegerField(null=True, blank=True, verbose_name="Jenkins 构建号")
    jenkins_build_url = models.CharField(max_length=512, blank=True, null=True, verbose_name="Jenkins 构建地址")
    jenkins_build_status = models.CharField(max_length=32, blank=True, null=True, verbose_name="Jenkins 构建状态")
    jenkins_build_duration = models.IntegerField(null=True, blank=True, verbose_name="构建耗时(毫秒)")
    
    # 构建产物
    docker_image = models.CharField(max_length=256, blank=True, null=True, verbose_name="Docker 镜像")
    artifact_url = models.CharField(max_length=512, blank=True, null=True, verbose_name="构建产物地址")
    
    # 发布状态
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='pending', verbose_name="发布状态")
    status_message = models.TextField(blank=True, null=True, verbose_name="状态消息")
    
    # 发布人
    released_by = models.CharField(max_length=64, verbose_name="发布人")
    
    class Meta:
        db_table = "release_record"
        verbose_name = "发布记录"
        ordering = ["-create_time"]
```

### 3.2 新增模型：ReleaseBuildLog（构建日志）

```python
class ReleaseBuildLog(CoreModel):
    """构建日志"""
    
    release = models.ForeignKey(ReleaseRecord, on_delete=models.CASCADE, related_name='build_logs')
    
    # 日志内容
    log_content = models.TextField(verbose_name="日志内容")
    log_type = models.CharField(max_length=32, default='console', verbose_name="日志类型")
    
    # 阶段信息
    stage_name = models.CharField(max_length=64, blank=True, null=True, verbose_name="阶段名称")
    stage_status = models.CharField(max_length=32, blank=True, null=True, verbose_name="阶段状态")
    
    class Meta:
        db_table = "release_build_log"
        verbose_name = "构建日志"
        ordering = ["create_time"]
```

### 3.3 新增模型：ApprovalRule（审批规则）

```python
class ApprovalRule(CoreModel):
    """审批规则"""
    
    RULE_TYPE_CHOICES = [
        ('single', '单人审批'),
        ('any', '任意一人审批'),
        ('all', '全部审批'),
        ('sequential', '顺序审批'),
    ]
    
    name = models.CharField(max_length=64, verbose_name="规则名称")
    code = models.CharField(max_length=32, unique=True, verbose_name="规则编码")
    environment = models.CharField(max_length=32, verbose_name="适用环境")
    rule_type = models.CharField(max_length=32, choices=RULE_TYPE_CHOICES, verbose_name="规则类型")
    
    # 审批人配置
    approvers = models.JSONField(default=list, verbose_name="审批人列表")  # [{"id": 1, "name": "张三", "order": 1}]
    
    # 条件配置
    min_approvers = models.IntegerField(default=1, verbose_name="最少审批人数")
    
    # 状态
    status = models.IntegerField(choices=CommonStatus.choices, default=CommonStatus.ENABLED, verbose_name="状态")
    
    class Meta:
        db_table = "release_approval_rule"
        verbose_name = "审批规则"
```

## 四、前端实现方案

### 4.1 发布按钮位置

**应用列表页面** (`web/apps/web-antd/src/views/release/application/index.vue`)

```vue
<template>
  <!-- 操作列增加发布按钮 -->
  <a-table-column title="操作" width="200px">
    <template #default="{ record }">
      <a-button type="primary" size="small" @click="handleRelease(record)">
        发布
      </a-button>
      <a-dropdown>
        <!-- 更多操作：配置、同步、构建记录 -->
      </a-dropdown>
    </template>
  </a-table-column>
</template>
```

### 4.2 发布多模态框组件结构

```
web/apps/web-antd/src/views/release/application/modules/
├── ReleaseModal.vue          # 发布主弹窗
├── ReleaseConfirmModal.vue   # 发布确认弹窗
├── ReleaseLogModal.vue       # 构建日志弹窗
└── components/
    ├── BranchSelect.vue      # 分支选择组件
    ├── EnvironmentSelect.vue # 环境选择组件
    ├── ApprovalSelect.vue    # 审批选择组件
    └── ReleaseInfo.vue       # 发布信息展示组件
```

### 4.3 发布流程状态机

```typescript
// 发布状态流转
type ReleaseStatus = 
  | 'pending'          // 初始状态
  | 'approval_pending' // 等待审批
  | 'approved'         // 审批通过
  | 'rejected'         // 审批拒绝
  | 'building'         // 构建中
  | 'build_success'    // 构建成功
  | 'build_failed'     // 构建失败
  | 'deploying'        // 部署中
  | 'deployed'         // 已部署
  | 'cancelled';       // 已取消

// 状态流转规则
const statusTransitions = {
  'pending': ['approval_pending', 'building', 'cancelled'],
  'approval_pending': ['approved', 'rejected', 'cancelled'],
  'approved': ['building', 'cancelled'],
  'rejected': ['pending', 'cancelled'],
  'building': ['build_success', 'build_failed', 'cancelled'],
  'build_success': ['deploying', 'deployed'],
  'build_failed': ['pending', 'building'],  // 允许重新构建
  'deploying': ['deployed', 'build_failed'],
  'deployed': ['rollback'],
};
```

### 4.4 发布弹窗交互流程

```
┌─────────────────────────────────────────────────────────────────────┐
│  Step 1: 发布配置弹窗 (ReleaseModal.vue)                             │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ 应用: medicare/payment/service                               │   │
│  ├─────────────────────────────────────────────────────────────┤   │
│  │ 分支选择:                                                    │   │
│  │   ○ main (默认)                                             │   │
│  │   ○ develop                                                 │   │
│  │   ○ release/v1.2.0                                          │   │
│  │   ○ 自定义: [          ]                                     │   │
│  ├─────────────────────────────────────────────────────────────┤   │
│  │ 目标环境:                                                    │   │
│  │   ○ 测试环境 (test)                                          │   │
│  │   ○ 准生产环境 (staging)                                     │   │
│  │   ○ 生产环境 (production)                                    │   │
│  ├─────────────────────────────────────────────────────────────┤   │
│  │ 审批设置:                                                    │   │
│  │   □ 需要审批                                                 │   │
│  │   审批规则: [下拉选择]                                        │   │
│  │   审批人:   [多选用户]                                        │   │
│  ├─────────────────────────────────────────────────────────────┤   │
│  │ 发布版本: v1.2.3 (从分支读取或手动输入)                        │   │
│  │ 发布说明: [文本域]                                            │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                        [取消]  [下一步 →]                           │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Step 2: 发布确认弹窗 (ReleaseConfirmModal.vue)                      │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ ⚠️ 请确认以下发布信息                                         │   │
│  ├─────────────────────────────────────────────────────────────┤   │
│  │ 应用名称:  medicare/payment/service                          │   │
│  │ 代码分支:  release/v1.2.0                                    │   │
│  │ 目标环境:  准生产环境 (staging)                               │   │
│  │ 发布版本:  v1.2.3                                            │   │
│  │ 是否审批:  是 (张三 → 李四)                                   │   │
│  │ 构建类型:  CI/CD 分离模式                                     │   │
│  │ CI Jenkins: internet-jenkins                                │   │
│  │ CD Jenkins: intranet-jenkins (配置导出)                      │   │
│  ├─────────────────────────────────────────────────────────────┤   │
│  │ 发布说明:                                                    │   │
│  │   修复支付模块超时问题                                        │   │
│  │   新增订单状态同步功能                                        │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                      [返回修改]  [确认发布]                         │
└─────────────────────────────────────────────────────────────────────┘
```

## 五、后端实现方案

### 5.1 API 接口设计

```python
# backend/release/urls.py

# 发布记录管理
router.register(r'release-record', views.ReleaseRecordViewSet)

# 发布操作 API
urlpatterns = [
    # 触发发布
    path('application/<int:app_id>/release/', views.trigger_release, name='trigger-release'),
    
    # 获取应用分支列表
    path('application/<int:app_id>/branches/', views.get_app_branches, name='app-branches'),
    
    # 获取环境配置
    path('application/<int:app_id>/environments/', views.get_app_environments, name='app-environments'),
    
    # 获取审批规则
    path('approval-rules/', views.get_approval_rules, name='approval-rules'),
    
    # 构建日志
    path('release/<int:release_id>/logs/', views.get_build_logs, name='build-logs'),
    
    # 审批操作
    path('release/<int:release_id>/approve/', views.approve_release, name='approve-release'),
    path('release/<int:release_id>/reject/', views.reject_release, name='reject-release'),
]
```

### 5.2 核心视图实现

```python
# backend/release/views/release.py

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

class ReleaseRecordViewSet(viewsets.ModelViewSet):
    """发布记录视图集"""
    queryset = ReleaseRecord.objects.all()
    serializer_class = ReleaseRecordSerializer
    filterset_class = ReleaseRecordFilter
    permission_classes = [IsAuthenticated]
    
    @action(detail=True, methods=['post'])
    def trigger(self, request, pk=None):
        """触发构建（审批通过后调用）"""
        release = self.get_object()
        
        if release.status != 'approved':
            return Response(
                {"error": "当前状态不允许触发构建"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 异步触发 Jenkins 构建
        from release.tasks import trigger_jenkins_build
        trigger_jenkins_build.delay(release.id)
        
        release.status = 'building'
        release.save()
        
        return Response({"message": "构建已触发"})
    
    @action(detail=True, methods=['get'])
    def logs(self, request, pk=None):
        """获取构建日志"""
        release = self.get_object()
        logs = release.build_logs.all().order_by('create_time')
        serializer = ReleaseBuildLogSerializer(logs, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """取消发布"""
        release = self.get_object()
        if release.status in ['building', 'approval_pending']:
            # 取消 Jenkins 构建
            if release.jenkins_build_number:
                jenkins = JenkinsService()
                jenkins.stop_build(release.jenkins_job_name, release.jenkins_build_number)
            
            release.status = 'cancelled'
            release.save()
            return Response({"message": "已取消"})
        return Response({"error": "当前状态不可取消"}, status=400)


@api_view(['POST'])
def trigger_release(request, app_id):
    """触发发布（创建发布记录）"""
    application = Application.objects.get(pk=app_id)
    
    # 参数验证
    serializer = ReleaseCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    data = serializer.validated_data
    branch = data['branch']
    environment = data['environment']
    require_approval = data.get('require_approval', False)
    approvers = data.get('approvers', [])
    
    # 获取环境策略
    strategy = EnvironmentStrategy.objects.filter(
        environment=environment,
        status=CommonStatus.ENABLED
    ).first()
    
    # 创建发布记录
    release = ReleaseRecord.objects.create(
        application=application,
        branch=branch,
        environment=environment,
        version=data.get('version'),
        require_approval=require_approval,
        approval_type=data.get('approval_type'),
        approvers=approvers,
        status='approval_pending' if require_approval else 'pending',
        released_by=request.user.username,
        remark=data.get('remark')
    )
    
    # 如果不需要审批，直接触发构建
    if not require_approval:
        from release.tasks import trigger_jenkins_build
        trigger_jenkins_build.delay(release.id)
        release.status = 'building'
        release.save()
    
    return Response({
        "id": release.id,
        "status": release.status,
        "message": "发布已创建" + ("，等待审批" if require_approval else "，构建已触发")
    })
```

### 5.3 异步任务实现

```python
# backend/release/tasks.py

from celery import shared_task
from .services.jenkins_service import JenkinsService
from .models import ReleaseRecord, ReleaseBuildLog

@shared_task(bind=True)
def trigger_jenkins_build(self, release_id):
    """触发 Jenkins 构建"""
    release = ReleaseRecord.objects.get(pk=release_id)
    application = release.application
    
    try:
        # 获取对应环境的流水线配置
        pipeline_config = application.pipeline_configs.filter(
            config_type='ci',
            environment=release.environment,
            is_active=True
        ).first()
        
        if not pipeline_config:
            raise Exception(f"未找到 {release.environment} 环境的 CI 配置")
        
        # 获取 Jenkins 实例
        strategy = EnvironmentStrategy.objects.filter(
            environment=release.environment
        ).first()
        
        jenkins = JenkinsService(instance_code=strategy.ci_jenkins)
        
        # 触发构建
        build_info = jenkins.build_job(
            job_name=pipeline_config.jenkins_job_name,
            parameters={
                'BRANCH': release.branch,
                'VERSION': release.version or '',
                'ENVIRONMENT': release.environment,
            }
        )
        
        # 更新发布记录
        release.jenkins_job_name = pipeline_config.jenkins_job_name
        release.jenkins_build_number = build_info['number']
        release.jenkins_build_url = build_info['url']
        release.status = 'building'
        release.save()
        
        # 异步轮询构建状态
        poll_build_status.delay(release.id)
        
    except Exception as e:
        release.status = 'build_failed'
        release.status_message = str(e)
        release.save()
        raise


@shared_task(bind=True)
def poll_build_status(self, release_id):
    """轮询构建状态"""
    release = ReleaseRecord.objects.get(pk=release_id)
    
    jenkins = JenkinsService()
    
    while release.status == 'building':
        build_info = jenkins.get_build_info(
            release.jenkins_job_name,
            release.jenkins_build_number
        )
        
        if build_info['building']:
            # 拉取日志
            fetch_build_log.delay(release.id)
            # 30秒后继续轮询
            poll_build_status.apply_async(args=[release_id], countdown=30)
            return
        else:
            # 构建完成
            release.jenkins_build_status = build_info['result']
            release.jenkins_build_duration = build_info['duration']
            
            if build_info['result'] == 'SUCCESS':
                release.status = 'build_success'
                # 触发 CD 部署（如果需要）
            else:
                release.status = 'build_failed'
            
            release.save()
            
            # 最终拉取完整日志
            fetch_build_log.delay(release.id)
            return


@shared_task
def fetch_build_log(release_id):
    """拉取构建日志"""
    release = ReleaseRecord.objects.get(pk=release_id)
    
    jenkins = JenkinsService()
    log_content = jenkins.get_build_console_output(
        release.jenkins_job_name,
        release.jenkins_build_number
    )
    
    # 保存或更新日志
    ReleaseBuildLog.objects.update_or_create(
        release=release,
        log_type='console',
        defaults={'log_content': log_content}
    )
```

## 六、环境与 Jenkins 映射关系

```
┌────────────────────────────────────────────────────────────────────┐
│                      环境 CI/CD 模式配置                            │
├──────────┬─────────────┬──────────────┬───────────────────────────┤
│  环境    │  流水线模式  │  CI Jenkins  │  CD Jenkins               │
├──────────┼─────────────┼──────────────┼───────────────────────────┤
│  test    │  integrated │  互联网       │  互联网 (合并到 CI)        │
│  staging │  separated  │  互联网       │  政务网 (配置导出)         │
│  prod    │  separated  │  互联网       │  政务网 (配置导出)         │
└──────────┴─────────────┴──────────────┴───────────────────────────┘
```

### 发布流程差异

1. **测试环境**：CI/CD 合并，一键构建部署
2. **准生产/生产**：
   - CI：互联网 Jenkins 构建，推送镜像到 Harbor
   - CD：导出配置文件，手动导入政务网 Jenkins 执行部署

## 七、数据库表关系

```
┌─────────────────┐     ┌─────────────────────┐     ┌────────────────────┐
│   Application   │────►│ ApplicationPipeline │────►│ PipelineTemplate   │
│                 │     │     Config          │     │                    │
└────────┬────────┘     └─────────────────────┘     └────────────────────┘
         │
         │ 1:N
         ▼
┌─────────────────┐     ┌─────────────────────┐     ┌────────────────────┐
│  ReleaseRecord  │────►│  ReleaseBuildLog    │     │  ApprovalRule      │
│                 │     │                     │     │                    │
└─────────────────┘     └─────────────────────┘     └────────────────────┘
```

## 八、权限控制

```python
# 权限码定义
RELEASE_PERMISSIONS = {
    'release:trigger': '触发发布',
    'release:approve': '审批发布',
    'release:cancel': '取消发布',
    'release:view_log': '查看构建日志',
    'release:export': '导出发布配置',
}

# 按钮权限
- 发布按钮: release:trigger
- 审批按钮: release:approve
- 取消按钮: release:cancel
- 查看日志: release:view_log
```

## 九、前端 API 接口

```typescript
// web/apps/web-antd/src/api/release/deployment.ts

import { request } from '#/utils/request';

// 触发发布
export function triggerRelease(appId: number, data: ReleaseParams) {
  return request.post(`/api/admin/release/application/${appId}/release/`, data);
}

// 获取应用分支
export function getAppBranches(appId: number) {
  return request.get(`/api/admin/release/application/${appId}/branches/`);
}

// 获取环境配置
export function getAppEnvironments(appId: number) {
  return request.get(`/api/admin/release/application/${appId}/environments/`);
}

// 获取发布记录列表
export function getReleaseList(params: any) {
  return request.get('/api/admin/release/release-record/', { params });
}

// 获取构建日志
export function getBuildLogs(releaseId: number) {
  return request.get(`/api/admin/release/release-record/${releaseId}/logs/`);
}

// 审批发布
export function approveRelease(releaseId: number, data: { comment: string }) {
  return request.post(`/api/admin/release/release-record/${releaseId}/approve/`, data);
}

// 拒绝发布
export function rejectRelease(releaseId: number, data: { comment: string }) {
  return request.post(`/api/admin/release/release-record/${releaseId}/reject/`, data);
}

// 取消发布
export function cancelRelease(releaseId: number) {
  return request.post(`/api/admin/release/release-record/${releaseId}/cancel/`);
}
```

## 十、实现优先级

| 优先级 | 功能模块 | 预估工时 |
|--------|----------|----------|
| P0 | 数据模型创建 + 迁移 | 2h |
| P0 | 发布记录 CRUD API | 4h |
| P0 | 触发发布 API + 任务 | 4h |
| P1 | 前端发布弹窗组件 | 6h |
| P1 | 构建日志拉取 + 展示 | 4h |
| P2 | 审批流程实现 | 8h |
| P2 | 发布确认弹窗 | 2h |
| P3 | 发布统计报表 | 4h |
