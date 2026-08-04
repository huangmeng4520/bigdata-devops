from django.db import models

from ai.choices import PlatformChoices, MessageType
from backend import settings
from utils.models import CommonStatus, CoreModel

class AIApiKey(CoreModel):
    """ AI API 密钥表 """
    name = models.CharField(max_length=255, db_comment="名称", verbose_name="名称")
    platform = models.CharField(
        max_length=100,
        choices=PlatformChoices.choices,
        verbose_name="平台",
        db_comment="平台"
    )
    api_key = models.CharField(max_length=255, db_comment="密钥", verbose_name="密钥")
    url = models.CharField(max_length=255, null=True, blank=True, db_comment="自定义 API 地址", verbose_name="自定义 API 地址")
    status = models.SmallIntegerField(
        choices=CommonStatus.choices,
        default=CommonStatus.DISABLED,
        verbose_name="状态",
        db_comment="状态",
    )

    class Meta:
        db_table = "ai_api_key"
        verbose_name = "AI API 密钥"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class AIModel(CoreModel):
    """ AI 模型 """
    name = models.CharField(max_length=64, db_comment="模型名字", verbose_name="模型名字")
    sort = models.IntegerField(db_comment="排序", default=0, verbose_name="排序")
    status = models.SmallIntegerField(
        choices=CommonStatus.choices,
        default=CommonStatus.DISABLED,
        verbose_name="状态",
        db_comment="状态",
    )
    key = models.ForeignKey(
        'AIApiKey',
        on_delete=models.CASCADE,
        db_comment='API 秘钥编号', verbose_name="API 秘钥编号"
    )
    model_type = models.CharField(max_length=32, db_comment="模型类型", verbose_name="模型类型", blank=True, null=True)
    platform = models.CharField(max_length=32, db_comment="模型平台", verbose_name="模型平台")
    model = models.CharField(max_length=64, db_comment="模型标识", verbose_name="模型标识")

    temperature = models.FloatField(null=True, blank=True, db_comment="温度参数", verbose_name="温度参数")
    max_tokens = models.IntegerField(null=True, blank=True, db_comment="单条回复的最大 Token 数量", verbose_name="单条回复的最大 Token 数量")
    max_contexts = models.IntegerField(null=True, blank=True, db_comment="上下文的最大 Message 数量", verbose_name="上下文的最大 Message 数量")

    class Meta:
        db_table = "ai_model"
        verbose_name = "模型配置"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class Tool(CoreModel):
    """ AI 工具表 """
    name = models.CharField(max_length=128, verbose_name="工具名称", db_comment="工具名称")
    description = models.CharField(max_length=256, null=True, blank=True, verbose_name="工具描述", db_comment="工具描述")
    status = models.SmallIntegerField(verbose_name="状态", db_comment="状态", default=0)

    class Meta:
        db_table = "ai_tool"
        verbose_name = "AI 工具"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class Knowledge(CoreModel):
    """ AI 知识库表 """
    name = models.CharField(max_length=255, verbose_name="知识库名称", db_comment="知识库名称")
    description = models.TextField(null=True, blank=True, verbose_name="知识库描述", db_comment="知识库描述")
    embedding_model_id = models.ForeignKey(
        'AIModel',
        on_delete=models.CASCADE,
        db_column='embedding_model_id',
        db_comment='向量模型编号', verbose_name="向量模型编号"
    )
    embedding_model = models.CharField(max_length=32, verbose_name="向量模型标识", db_comment="向量模型标识")
    top_k = models.IntegerField(verbose_name="topK", db_comment="topK", default=0)
    similarity_threshold = models.FloatField(verbose_name="相似度阈值", db_comment="相似度阈值")
    status = models.SmallIntegerField(
        choices=CommonStatus.choices,
        default=CommonStatus.DISABLED,
        verbose_name="状态",
        db_comment="状态",
    )

    class Meta:
        db_table = "ai_knowledge"
        verbose_name = "AI 知识库"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class KnowledgeDocument(CoreModel):
    """  AI 知识库文档表  """
    knowledge = models.ForeignKey(
        Knowledge,
        on_delete=models.CASCADE,
        related_name="documents",
        verbose_name="知识库",
        db_comment="知识库"
    )
    name = models.CharField(max_length=255, verbose_name="文档名称", db_comment="文档名称")
    url = models.CharField(max_length=1024, verbose_name="文件 URL", db_comment="文件 URL")
    content = models.TextField(verbose_name="内容", db_comment="内容")
    content_length = models.IntegerField(verbose_name="字符数", db_comment="字符数")
    tokens = models.IntegerField(verbose_name="token 数量", db_comment="token 数量")
    segment_max_tokens = models.IntegerField(verbose_name="分片最大 Token 数", db_comment="分片最大 Token 数")
    retrieval_count = models.IntegerField(default=0, verbose_name="召回次数", db_comment="召回次数")
    status = models.SmallIntegerField(
        choices=CommonStatus.choices,
        default=CommonStatus.DISABLED,
        verbose_name="状态",
        db_comment="状态",
    )

    class Meta:
        db_table = "ai_knowledge_document"
        verbose_name = "AI 知识库文档"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class KnowledgeSegment(CoreModel):
    """ AI 知识库分段表 """
    knowledge = models.ForeignKey(
        Knowledge,
        on_delete=models.CASCADE,
        related_name="segments",
        verbose_name="知识库",
        db_comment="知识库"
    )
    document = models.ForeignKey(
        KnowledgeDocument,
        on_delete=models.CASCADE,
        related_name="segments",
        verbose_name="文档",
        db_comment="文档"
    )
    content = models.TextField(verbose_name="分段内容", db_comment="分段内容")
    content_length = models.IntegerField(verbose_name="字符数", db_comment="字符数")
    tokens = models.IntegerField(verbose_name="token 数量", db_comment="token 数量")
    vector_id = models.CharField(
        max_length=100,
        null=True, blank=True,
        verbose_name="向量库的编号",
        db_comment="向量库的编号"
    )
    retrieval_count = models.IntegerField(default=0, verbose_name="召回次数", db_comment="召回次数")
    status = models.SmallIntegerField(
        choices=CommonStatus.choices,
        default=CommonStatus.DISABLED,
        verbose_name="状态",
        db_comment="状态"
    )

    class Meta:
        db_table = "ai_knowledge_segment"
        verbose_name = "AI 知识库分段"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"Segment {self.id}"


class ChatRole(CoreModel):
    """ AI 聊天角色表 """
    name = models.CharField(max_length=128, verbose_name="角色名称", db_comment="角色名称")
    avatar = models.CharField(max_length=256, verbose_name="头像", db_comment="头像")
    description = models.CharField(max_length=256, verbose_name="角色描述", db_comment="角色描述")
    status = models.SmallIntegerField(
        choices=CommonStatus.choices,
        default=CommonStatus.DISABLED,
        verbose_name="状态",
        db_comment="状态"
    )
    sort = models.IntegerField(default=0, verbose_name="角色排序", db_comment="角色排序")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        verbose_name="用户",
        db_comment="用户编号"
    )
    public_status = models.BooleanField(default=False, verbose_name="是否公开", db_comment="是否公开")
    category = models.CharField(max_length=32, null=True, blank=True, verbose_name="角色类别", db_comment="角色类别")
    model_id = models.ForeignKey(
        'AIModel',
        on_delete=models.CASCADE,
        db_column='model_id',
        verbose_name="向量模型编号",
        db_comment='向量模型编号'
    )
    system_message = models.CharField(
        max_length=1024, null=True, blank=True,
        verbose_name="角色上下文",
        db_comment="角色上下文"
    )
    knowledge = models.ManyToManyField(
        'Knowledge',
        blank=True,
        related_name="roles",
        verbose_name="关联的知识库",
    )
    tools = models.ManyToManyField(
        'Tool',
        blank=True,
        related_name="roles",
        verbose_name="关联的工具",
    )

    class Meta:
        db_table = "ai_chat_role"
        verbose_name = "AI 聊天角色"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class ChatConversation(CoreModel):
    """ AI 聊天对话表 """
    title = models.CharField(max_length=256, verbose_name="对话标题", db_comment="对话标题")
    pinned = models.BooleanField(default=False, verbose_name="是否置顶", db_comment="是否置顶")
    pinned_time = models.DateTimeField(null=True, blank=True, verbose_name="置顶时间", db_comment="置顶时间")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        verbose_name="用户",
        db_comment="用户编号"
    )
    role = models.ForeignKey(
        'ChatRole',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        verbose_name="聊天角色",
        db_comment="聊天角色"
    )
    model_id = models.ForeignKey(
        'AIModel',
        on_delete=models.CASCADE,
        null=True, blank=True,
        db_column='model_id',
        verbose_name="向量模型编号",
        db_comment='向量模型编号'
    )
    model = models.CharField(max_length=32, verbose_name="模型标识", db_comment="模型标识")
    system_message = models.CharField(
        max_length=1024, null=True, blank=True,
        verbose_name="角色设定",
        db_comment="角色设定"
    )
    temperature = models.FloatField(verbose_name="温度参数", db_comment="温度参数")
    max_tokens = models.IntegerField(verbose_name="单条回复的最大 Token 数量", db_comment="单条回复的最大 Token 数量")
    max_contexts = models.IntegerField(verbose_name="上下文的最大 Message 数量", db_comment="上下文的最大 Message 数量")

    class Meta:
        db_table = "ai_chat_conversation"
        verbose_name = "AI 聊天对话"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.title


class ChatMessage(CoreModel):
    """ AI 聊天消息表 """
    conversation_id = models.BigIntegerField(verbose_name="对话编号", db_comment="对话编号")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        verbose_name="用户",
        db_comment="用户编号"
    )
    role = models.ForeignKey(
        'ChatRole',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        verbose_name="聊天角色",
        db_comment="聊天角色"
    )
    model = models.CharField(max_length=32, verbose_name="模型标识", db_comment="模型标识")
    model_id = models.ForeignKey(
        'AIModel',
        on_delete=models.CASCADE,
        null=True, blank=True,
        db_column='model_id',
        verbose_name="向量模型编号",
        db_comment='向量模型编号'
    )
    type = models.CharField(
        max_length=16,
        choices=MessageType.choices,
        verbose_name="消息类型",
        db_comment="消息类型",
    )
    reply_id = models.BigIntegerField(null=True, blank=True, verbose_name="回复编号", db_comment="回复编号")
    content = models.TextField(verbose_name="消息内容", db_comment="消息内容")
    use_context = models.BooleanField(default=False, verbose_name="是否携带上下文", db_comment="是否携带上下文")
    segment_ids = models.CharField(
        max_length=2048, null=True, blank=True,
        verbose_name="段落编号数组",
        db_comment="段落编号数组"
    )

    class Meta:
        db_table = "ai_chat_message"
        verbose_name = "AI 聊天消息"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.content[:30]


class Drawing(CoreModel):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        verbose_name="用户",
        db_comment="用户编号"
    )
    public_status = models.BooleanField(default=False, verbose_name='是否发布')

    platform = models.CharField(max_length=64, verbose_name='平台')
    model = models.CharField(max_length=64, verbose_name='模型')

    prompt = models.TextField(max_length=2000, verbose_name='提示词')
    width = models.IntegerField(verbose_name='图片宽度')
    height = models.IntegerField(verbose_name='图片高度')
    options = models.JSONField(null=True, verbose_name='绘制参数')

    status = models.CharField(max_length=20, verbose_name='绘画状态')
    pic_url = models.URLField(max_length=2048, null=True, verbose_name='图片地址')
    error_message = models.CharField(max_length=1024, null=True, verbose_name='错误信息')

    task_id = models.CharField(max_length=1024, null=True, verbose_name='任务编号')
    buttons = models.CharField(max_length=2048, null=True, verbose_name='mj buttons 按钮')

    class Meta:
        db_table = 'ai_drawing'
        verbose_name = 'AI 绘画表'
        verbose_name_plural = verbose_name
