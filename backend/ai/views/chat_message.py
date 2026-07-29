import asyncio

from django.http import StreamingHttpResponse
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response

from ai.llm.enums import LLMProvider
from ai.llm.factory import get_adapter
from ai.models import ChatConversation, ChatMessage
from backend import settings
from ai.choices import MessageType
from utils.serializers import CustomModelSerializer
from utils.custom_model_viewSet import CustomModelViewSet
from django_filters import rest_framework as filters

PLATFORM_TO_PROVIDER = {
    'OpenAI': LLMProvider.OPENAI,
    'AzureOpenAI': LLMProvider.OPENAI,
    'Ollama': LLMProvider.OPENAI,
    'DeepSeek': LLMProvider.DEEPSEEK,
    'TongYi': LLMProvider.TONGYI,
    'SiliconFlow': LLMProvider.OPENAI,
    'ZhiPu': LLMProvider.OPENAI,
}


def _get_conversation_config(conversation_id):
    try:
        conversation = ChatConversation.objects.select_related(
            'model_id__key'
        ).get(pk=conversation_id)
    except ChatConversation.DoesNotExist:
        return None, None, None, None

    if not conversation.model_id:
        return None, None, None, None

    ai_model = conversation.model_id
    api_key_obj = ai_model.key
    provider = PLATFORM_TO_PROVIDER.get(api_key_obj.platform, LLMProvider.OPENAI)
    api_key = api_key_obj.api_key
    base_url = api_key_obj.url or None
    model = ai_model.model
    return provider, api_key, base_url, model


class ChatMessageSerializer(CustomModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    """
    AI 聊天消息 序列化器
    """
    class Meta:
        model = ChatMessage
        fields = '__all__'
        read_only_fields = ['id', 'create_time', 'update_time']


class ChatMessageFilter(filters.FilterSet):

    class Meta:
        model = ChatMessage
        fields = ['id', 'remark', 'creator', 'modifier', 'is_deleted', 'conversation_id',
                  'model', 'type', 'reply_id', 'content', 'use_context', 'segment_ids']


class ChatMessageViewSet(CustomModelViewSet):
    """
    AI 聊天消息 视图集
    """
    queryset = ChatMessage.objects.filter(is_deleted=False).order_by('-id')
    serializer_class = ChatMessageSerializer
    filterset_class = ChatMessageFilter
    search_fields = ['name']  # 根据实际字段调整
    ordering_fields = ['create_time', 'id']
    ordering = ['-create_time']

    @action(detail=False, methods=['post'], url_path='stream')
    def stream(self, request):
        """
        流式聊天接口
        """
        content = request.data.get('content')
        conversation_id = request.data.get('conversation_id')
        resume = request.data.get('resume', False)
        if isinstance(conversation_id, dict):
            conversation_id = conversation_id.get('id')

        user_id = request.user.id

        from ai.models import AIModel

        provider, api_key, base_url, model = _get_conversation_config(conversation_id)

        if provider is None:
            ai_model = AIModel.objects.filter(status=1).select_related('key').first()
            if ai_model and ai_model.key and ai_model.key.api_key:
                provider = PLATFORM_TO_PROVIDER.get(ai_model.key.platform, LLMProvider.OPENAI)
                api_key = ai_model.key.api_key
                base_url = ai_model.key.url or None
                model = ai_model.model
            else:
                platform = request.data.get('platform', 'deepseek')
                if platform == 'tongyi':
                    model = 'qwen-plus'
                    api_key = settings.DASHSCOPE_API_KEY
                    provider = LLMProvider.TONGYI
                else:
                    model = 'deepseek-chat'
                    api_key = settings.DEEPSEEK_API_KEY
                    provider = LLMProvider.DEEPSEEK

        try:
            conversation = ChatMessage.objects.filter(conversation_id=conversation_id).order_by('id')
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        if not resume:
            ChatMessage.objects.create(
                conversation_id=conversation_id,
                user_id=user_id,
                role_id=None,
                model=model,
                model_id=None,
                type=MessageType.USER,
                reply_id=None,
                content=content,
                use_context=True,
                segment_ids=None,
            )

        context = [("system", "You are a helpful assistant")]
        history = ChatMessage.objects.filter(conversation_id=conversation_id).order_by('id')

        for msg in history:
            context.append((msg.type, msg.content))

        llm = get_adapter(provider, api_key=api_key, model=model, base_url=base_url)

        def generate():
            ai_reply = ""
            loop = None
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                async def async_stream():
                    async for chunk in llm.stream_chat(context):
                        yield chunk

                async_gen = async_stream()
                while True:
                    try:
                        chunk = loop.run_until_complete(async_gen.__anext__())
                    except StopAsyncIteration:
                        break
                    except Exception as e:
                        yield f"data: 错误：{str(e)}\n\n"
                        break

                    if hasattr(chunk, 'content'):
                        chunk_content = chunk.content.strip()
                    elif isinstance(chunk, dict) and 'content' in chunk:
                        chunk_content = chunk['content'].strip()
                    else:
                        chunk_content = str(chunk).strip()

                    if chunk_content:
                        ai_reply += chunk_content
                        yield f"data: {chunk_content}\n\n"

            finally:
                if loop:
                    loop.close()
            if ai_reply.strip():
                ChatMessage.objects.create(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    role_id=None,
                    model=model,
                    model_id=None,
                    type=MessageType.ASSISTANT,
                    reply_id=None,
                    content=ai_reply,
                    use_context=True,
                    segment_ids=None,
                )

        return StreamingHttpResponse(generate(), content_type='text/event-stream')
