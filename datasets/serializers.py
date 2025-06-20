from rest_framework import serializers
from .models import CreatorProfile, Brand, Product


class CreatorProfileSerializer(serializers.ModelSerializer):
    """创作者资料序列化器，包含头像处理"""
    avatar_display_url = serializers.SerializerMethodField()
    
    class Meta:
        model = CreatorProfile
        fields = [
            'id', 'name', 'avatar', 'avatar_url', 'avatar_display_url',
            'email', 'instagram', 'tiktok_link', 'location', 'live_schedule',
            'category', 'e_commerce_level', 'exposure_level', 'followers',
            'gmv', 'items_sold', 'avg_video_views', 'pricing', 'pricing_package',
            'collab_count', 'latest_collab', 'e_commerce_platforms',
            'gmv_by_channel', 'gmv_by_category', 'mcn',
            'create_time', 'update_time'
        ]
        extra_kwargs = {
            'avatar': {'write_only': False},  # 允许读写
            'avatar_url': {'write_only': False}  # 允许读写
        }
    
    def get_avatar_display_url(self, obj):
        """获取头像显示URL，优先使用本地图片"""
        request = self.context.get('request')
        avatar_url = obj.get_avatar_url()
        
        if avatar_url and request:
            # 如果是本地图片，返回完整的URL
            if obj.avatar:
                return request.build_absolute_uri(avatar_url)
            # 如果是外部URL，直接返回
            else:
                return avatar_url
        return avatar_url


class CreatorProfileListSerializer(serializers.ModelSerializer):
    """创作者资料列表序列化器，用于列表显示，字段较少"""
    avatar_display_url = serializers.SerializerMethodField()
    
    class Meta:
        model = CreatorProfile
        fields = [
            'id', 'name', 'avatar_display_url', 'category', 
            'exposure_level', 'followers', 'gmv', 'mcn'
        ]
    
    def get_avatar_display_url(self, obj):
        """获取头像显示URL"""
        request = self.context.get('request')
        avatar_url = obj.get_avatar_url()
        
        if avatar_url and request:
            if obj.avatar:
                return request.build_absolute_uri(avatar_url)
            else:
                return avatar_url
        return avatar_url 

class BrandSerializer(serializers.ModelSerializer):
    """品牌序列化器"""
    class Meta:
        model = Brand
        fields = ['id', 'name', 'description', 'logo_url', 'category', 'source', 
                  'collab_count', 'creators_count', 'campaign_id', 'total_gmv_achieved',
                  'total_views_achieved', 'shop_overall_rating', 'dataset_id_list', 
                  'created_at', 'updated_at', 'is_active']
        read_only_fields = ['id', 'created_at', 'updated_at', 'dataset_id_list']


class ProductSerializer(serializers.ModelSerializer):
    """产品序列化器"""
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    
    class Meta:
        model = Product
        fields = ['id', 'brand', 'brand_name', 'name', 'description', 'image_url', 
                  'pid', 'commission_rate', 'open_collab', 'available_samples',
                  'sales_price_min', 'sales_price_max', 'stock', 'items_sold',
                  'product_rating', 'reviews_count', 'collab_creators', 'tiktok_shop',
                  'dataset_id', 'external_id', 'created_at', 'updated_at', 'is_active']
        read_only_fields = ['id', 'created_at', 'updated_at']