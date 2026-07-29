from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.serializers import ModelSerializer

from ai.models import AIApiKey, AIModel, ChatConversation
from utils.serializers import CustomModelSerializer
from utils.custom_model_viewSet import CustomModelViewSet
from django_filters import rest_framework as filters

PLATFORM_MODEL_ALIAS = {
    'deepseek': 'deepseek-chat',
    'tongyi': 'qwen-plus',
}


class ChatConversationSerializer(CustomModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = ChatConversation
        fields = '__all__'
        read_only_fields = ['id', 'create_time', 'update_time']


class ChatConversationFilter(filters.FilterSet):

    class Meta:
        model = ChatConversation
        fields = ['id', 'remark', 'creator', 'modifier', 'is_deleted', 'title', 'pinned', 'model',
                  'system_message', 'max_tokens', 'max_contexts']


class ConversationsSerializer(ModelSerializer):

    class Meta:
        model = ChatConversation
        fields = ['id', 'title', 'update_time']


class ChatConversationViewSet(CustomModelViewSet):
    queryset = ChatConversation.objects.filter(is_deleted=False).order_by('-id')
    serializer_class = ChatConversationSerializer
    filterset_class = ChatConversationFilter
    search_fields = ['name']
    ordering_fields = ['create_time', 'id']
    ordering = ['-create_time']

    def create(self, request, *args, **kwargs):
        request.data['max_tokens'] = 2048
        request.data['max_contexts'] = 10
        request.data['temperature'] = 0.7
        platform = request.data.get('platform', 'deepseek')
        request.data['model'] = PLATFORM_MODEL_ALIAS.get(platform, 'deepseek-chat')
        response = super().create(request, *args, **kwargs)
        if response.data.get('id'):
            ai_model = AIModel.objects.filter(status=1).first()
            if ai_model:
                ChatConversation.objects.filter(pk=response.data['id']).update(model_id=ai_model)
        return response

    @action(methods=['get'], detail=False)
    def conversations(self):
        queryset = self.get_queryset().filter(creator=self.request.user.username).values('id', 'title', 'update_time')
        serializer = ConversationsSerializer(queryset, many=True)
        return self._build_response(
            data=serializer.data,
            message="ok"
        )
