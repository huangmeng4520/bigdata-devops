from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, serializers, status
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.response import Response

from system.models import Menu, MenuMeta
from utils.custom_model_viewSet import CustomModelViewSet
from utils.serializers import CustomModelSerializer


class MenuMetaSerializer(serializers.ModelSerializer):

    """菜单元数据序列化器"""
    hideChildrenInMenu = serializers.SerializerMethodField()
    hideInMenu = serializers.SerializerMethodField()
    iframeSrc = serializers.SerializerMethodField()

    class Meta:
        model = MenuMeta
        fields = '__all__'

    def get_hideChildrenInMenu(self, obj):
        return getattr(obj, 'hide_children_in_menu', None)

    def get_hideInMenu(self, obj):
        return getattr(obj, 'hide_in_menu', None)

    def get_iframeSrc(self, obj):
        return getattr(obj, 'iframe_src', None)


class MenuSerializer(CustomModelSerializer):
    """菜单序列化器"""
    parent = serializers.CharField(source='pid.name', read_only=True)
    meta = MenuMetaSerializer()
    children = serializers.SerializerMethodField()
    status_text = serializers.SerializerMethodField()
    type_text = serializers.SerializerMethodField()

    class Meta:
        model = Menu
        fields = '__all__'
        read_only_fields = ['id', 'create_time', 'update_time']

    def get_children(self, obj):
        """获取子菜单（排除软删除）"""
        children = obj.children.filter(is_deleted=False).order_by('sort')
        if children:
            return MenuSerializer(children, many=True).data
        return []

    def get_status_text(self, obj):
        """获取状态文本"""
        return obj.get_status_display()

    def get_type_text(self, obj):
        """获取菜单类型文本"""
        return obj.get_type_display()

    def create(self, validated_data):
        """创建菜单及关联的元数据"""
        meta_data = validated_data.pop('meta')
        meta = MenuMeta.objects.create(**meta_data)
        self.set_audit_user_fields(validated_data, is_create=True)
        menu = Menu.objects.create(meta=meta, **validated_data)
        return menu

    def update(self, instance, validated_data):
        """更新菜单及关联的元数据"""
        self.set_audit_user_fields(validated_data, is_create=False)
        meta_data = validated_data.pop('meta', {})
        meta_serializer = self.fields['meta']
        meta_serializer.update(instance.meta, meta_data)
        return super().update(instance, validated_data)


class MenuUserSerializer(MenuSerializer):
    def get_children(self, obj):
        request = self.context.get('request')
        children_qs = obj.children.exclude(type='button').filter(is_deleted=False).order_by('sort')
        if request and hasattr(request, 'user') and request.user.is_authenticated and not request.user.is_superuser:
            role_ids = request.user.role.values_list('id', flat=True)
            children_qs = children_qs.filter(role__id__in=role_ids).distinct()
        if children_qs:
            return MenuUserSerializer(children_qs, many=True, context=self.context).data
        return []


class MenuMetaViewSet(viewsets.ModelViewSet):
    """菜单元数据视图集"""
    queryset = MenuMeta.objects.all()
    serializer_class = MenuMetaSerializer


class MenuViewSet(CustomModelViewSet):
    """菜单管理视图集"""
    queryset = Menu.objects.filter(pid__isnull=True, is_deleted=False).order_by('sort', 'id', 'status').prefetch_related('children')
    serializer_class = MenuSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'type', 'pid', 'name']
    search_fields = ['name', 'path', 'auth_code']
    ordering_fields = ['meta__sort', 'create_time']

    @action(detail=False, methods=['get'])
    def tree(self, request):
        """获取菜单树形结构"""
        queryset = self.get_queryset().filter(pid__isnull=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='name-exists')
    def name_exists(self, request):
        return self._build_response()

    @action(detail=False, methods=['get'], url_path='name-search')
    def name_search(self, request):
        name = request.GET.get('name')
        pk = request.GET.get('id', None)
        pid = request.GET.get('pid', None)
        queryset = Menu.objects.all()
        if pid:
            queryset = queryset.filter(pid=pid)
        if pk:
            queryset = queryset.exclude(pk=pk)
        if name:
            queryset = queryset.filter(name=name)
        has_menu_name = queryset.exists()
        return self._build_response(data=has_menu_name)

    @action(detail=False, methods=['get'], url_path='path-exists')
    def path_exists(self, request):
        return self._build_response()

    @action(detail=False, methods=['get'], url_path='user_menu')
    def user_menu(self, request):
        user = self.request.user
        if user.is_superuser:
            menus = Menu.objects.filter(pid__isnull=True, is_deleted=False).exclude(type='button').order_by('sort')
        else:
            role_ids = user.role.values_list('id', flat=True)
            menus = Menu.objects.filter(pid__isnull=True, is_deleted=False,
                                        role__id__in=role_ids
                                        ).exclude(type='button').order_by('sort').distinct()
        menus_data = MenuUserSerializer(menus, many=True, context={'request': request}).data
        return self._build_response(data=menus_data)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        pk = kwargs['pk']
        instance = Menu.objects.get(pk=pk)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}
        return self._build_response(
            data=serializer.data,
            message="ok",
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        pk = kwargs['pk']
        instance = Menu.objects.get(pk=pk)
        self.perform_destroy(instance)
        return self._build_response(
            message="ok",
            status=status.HTTP_200_OK,
        )
