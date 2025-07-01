from django.db import models
import uuid
from accounts.models import User
from django.utils import timezone

class CreatorProfile(models.Model):
    """达人信息模型，用于筛选功能"""
    # 基本信息
    name = models.CharField(max_length=255, verbose_name="达人名称")
    # 修改为支持本地图片上传，同时保持URL兼容性
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name="头像图片")
    avatar_url = models.TextField(blank=True, null=True, verbose_name="头像URL")
    platform_id = models.CharField(max_length=255, blank=True, null=True, verbose_name="Platform ID")

    # 新增联系方式
    email = models.EmailField(max_length=255, blank=True, null=True, verbose_name="电子邮箱")
    instagram = models.CharField(max_length=255, blank=True, null=True, verbose_name="Instagram账号")
    location = models.CharField(max_length=100, blank=True, null=True, verbose_name="位置")
    live_schedule = models.CharField(max_length=255, blank=True, null=True, verbose_name="直播时间表")

    # 新增达人平台字段
    PROFILE_CHOICES = [
        ('tiktok', 'TikTok'),
        ('instagram', 'Instagram'),
        ('youtube', 'YouTube'),
        ('other', '其他平台'),
    ]
    profile = models.CharField(max_length=20, choices=PROFILE_CHOICES, default='tiktok', verbose_name="达人平台")

    # 新增hashtag和trend字段
    hashtags = models.TextField(blank=True, null=True, verbose_name="标签", help_text="以#分隔的标签，例如:#fashion#beauty#lifestyle")
    trends = models.TextField(blank=True, null=True, verbose_name="趋势", help_text="创作者相关的趋势关键词")

    # 新增地区字段
    region = models.CharField(max_length=100, blank=True, null=True, verbose_name="地区")

    # 新增主页链接字段
    tiktok_link = models.URLField(max_length=500, blank=True, null=True, verbose_name="主页链接")

    # 新增对标美区达人等级
    us_creator_level = models.CharField(max_length=50, blank=True, null=True, verbose_name="对标美区达人等级")

    # 新增报价字段
    price_gbp = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="报价(英镑)")
    price_usd = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="报价(美金)")

    # 新增GMV(英镑)字段
    gmv_gbp = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, verbose_name="GMV(英镑)")

    # 新增链接字段
    link = models.URLField(max_length=500, blank=True, null=True, verbose_name="链接")

    # 类别 - Category
    CATEGORY_CHOICES = [
        ('Phones & Electronics', '手机与电子产品'),
        ('Homes Supplies', '家居用品'),
        ('Kitchenware', '厨房用品'),
        ('Textiles & Soft Furnishings', '纺织品和软装'),
        ('Household Appliances', '家用电器'),
        ('Womenswear & Underwear', '女装和内衣'),
        ('Muslim Fashion', '穆斯林时尚'),
        ('Shoes', '鞋类'),
        ('Beauty & Personal Care', '美容和个人护理'),
        ('Computers & Office Equipment', '电脑和办公设备'),
        ('Pet Supplies', '宠物用品'),
        ('Baby & Maternity', '婴儿和孕妇用品'),
        ('Sports & Outdoor', '运动和户外'),
        ('Toys', '玩具'),
        ('Furniture', '家具'),
        ('Tools & Hardware', '工具和硬件'),
        ('Home Improvement', '家居装修'),
        ('Automotive & Motorcycle', '汽车和摩托车'),
        ('Fashion Accessories', '时尚配饰'),
        ('Food & Beverages', '食品和饮料'),
        ('Health', '健康'),
        ('Books, Magazines & Audio', '书籍、杂志和音频'),
        ('Kids Fashion', '儿童时尚'),
        ('Menswear & Underwear', '男装和内衣'),
        ('Luggage & Bags', '行李和包'),
        ('Pre-Owned Collections', '二手收藏'),
        ('Jewellery Accessories & Derivatives', '珠宝配饰及衍生品'),
    ]
    category = models.CharField(max_length=100, choices=CATEGORY_CHOICES, blank=True, null=True, verbose_name="类别")

    # 电商等级 - E-commerce Level (L1-L7)
    E_COMMERCE_LEVEL_CHOICES = [
        (1, 'L1'),
        (2, 'L2'),
        (3, 'L3'),
        (4, 'L4'),
        (5, 'L5'),
        (6, 'L6'),
        (7, 'L7'),
    ]
    e_commerce_level = models.IntegerField(choices=E_COMMERCE_LEVEL_CHOICES, blank=True, null=True,
                                           verbose_name="电商能力等级")

    # 曝光等级 - Exposure Level (KOC-1, KOC-2, KOL-1, KOL-2, KOL-3)
    EXPOSURE_LEVEL_CHOICES = [
        ('KOC-1', 'KOC-1'),
        ('KOC-2', 'KOC-2'),
        ('KOL-1', 'KOL-1'),
        ('KOL-2', 'KOL-2'),
        ('KOL-3', 'KOL-3'),
    ]
    exposure_level = models.CharField(max_length=10, choices=EXPOSURE_LEVEL_CHOICES, blank=True, null=True,
                                      verbose_name="曝光等级")

    # 粉丝数 - Followers
    followers = models.IntegerField(default=0, verbose_name="粉丝数")

    # GMV - Gross Merchandise Value (in thousands of dollars)
    gmv = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, verbose_name="GMV(千美元)")
    items_sold = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True,
                                     verbose_name="售出商品数量")

    # 视频数据 - Video Views
    avg_video_views = models.IntegerField(default=0, blank=True, null=True, verbose_name="平均视频浏览量")

    # 价格信息 - Pricing
    pricing = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="个人定价")
    pricing_package = models.CharField(max_length=100, blank=True, null=True, verbose_name="套餐定价")

    # 合作信息 - Collaboration
    collab_count = models.IntegerField(default=0, blank=True, null=True, verbose_name="合作次数")
    latest_collab = models.CharField(max_length=100, blank=True, null=True, verbose_name="最新合作")

    # 电商平台 - E-commerce platforms (存储为JSON数组，如["SUNLINK", "ARZOPA", "BELIFE"])
    e_commerce_platforms = models.JSONField(blank=True, null=True, verbose_name="电商平台")

    # 分析数据 - Analytics (JSON格式存储销售渠道和类别分布)
    gmv_by_channel = models.JSONField(blank=True, null=True, verbose_name="GMV按渠道分布")
    gmv_by_category = models.JSONField(blank=True, null=True, verbose_name="GMV按类别分布")

    # MCN机构
    mcn = models.CharField(max_length=255, blank=True, null=True, verbose_name="MCN机构")

    # 时间戳
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    update_time = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    def get_avatar_url(self):
        """获取头像URL，优先返回本地图片，其次返回外部URL"""
        if self.avatar:
            return self.avatar.url
        elif self.avatar_url:
            return self.avatar_url
        return None

    class Meta:
        verbose_name = "达人信息"
        verbose_name_plural = verbose_name
        db_table = "creator_profiles"

    def __str__(self):
        return f"{self.name}"

class Brand(models.Model):
    """品牌模型"""
    id = models.AutoField(primary_key=True)  # 改为int自增主键
    name = models.CharField(max_length=100, unique=True, verbose_name='品牌名称')
    description = models.TextField(blank=True, null=True, verbose_name='品牌描述')
    logo_url = models.CharField(max_length=255, blank=True, null=True, verbose_name='品牌Logo')
    category = models.CharField(max_length=100, blank=True, null=True, verbose_name='品牌分类')
    source = models.CharField(max_length=100, blank=True, null=True, verbose_name='来源')
    collab_count = models.IntegerField(default=0, verbose_name='合作数量')
    creators_count = models.IntegerField(default=0, verbose_name='创作者数量')
    campaign_id = models.CharField(max_length=100, blank=True, null=True, verbose_name='活动ID')
    
    # 添加数据统计字段
    total_gmv_achieved = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='总GMV')
    total_views_achieved = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='总浏览量')
    shop_overall_rating = models.DecimalField(max_digits=3, decimal_places=1, default=0.0, verbose_name='店铺评分')
    
    # 存储关联到此品牌的所有产品和活动知识库ID列表
    dataset_id_list = models.JSONField(default=list, blank=True, verbose_name='知识库ID列表',
                                      help_text='所有关联的知识库ID列表')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    is_active = models.BooleanField(default=True, verbose_name='是否激活')
    
    class Meta:
        verbose_name = '品牌'
        verbose_name_plural = '品牌'
    
    def __str__(self):
        return self.name

class Product(models.Model):
    """产品模型 - 作为一个知识库"""
    id = models.AutoField(primary_key=True)  # 改为int自增主键
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='products', verbose_name='所属品牌')
    name = models.CharField(max_length=100, verbose_name='产品名称')
    description = models.TextField(blank=True, null=True, verbose_name='产品描述')
    image_url = models.CharField(max_length=255, blank=True, null=True, verbose_name='产品图片')
    
    # 添加产品详情字段
    pid = models.CharField(max_length=100, blank=True, null=True, verbose_name='产品ID')
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='佣金率')
    open_collab = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='开放合作率')
    available_samples = models.IntegerField(default=0, verbose_name='可用样品数')
    sales_price_min = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='最低销售价')
    sales_price_max = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='最高销售价')
    stock = models.IntegerField(default=0, verbose_name='库存')
    items_sold = models.IntegerField(default=0, verbose_name='已售数量')
    product_rating = models.DecimalField(max_digits=3, decimal_places=1, default=0, verbose_name='产品评分')
    reviews_count = models.IntegerField(default=0, verbose_name='评价数量')
    collab_creators = models.IntegerField(default=0, verbose_name='合作创作者数')
    tiktok_shop = models.BooleanField(default=False, verbose_name='是否TikTok商店')
    
    dataset_id = models.CharField(max_length=100, blank=True, null=True, verbose_name='知识库ID', 
                                help_text='外部知识库系统中的ID')
    external_id = models.CharField(max_length=100, blank=True, null=True, verbose_name='外部ID',
                                 help_text='外部系统中的唯一标识')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    is_active = models.BooleanField(default=True, verbose_name='是否激活')
    
    creators = models.ManyToManyField(
        'CreatorProfile',
        through='CreatorProductMatch',
        related_name='matched_products',
        verbose_name='匹配达人'
    )
    
    class Meta:
        verbose_name = '产品'
        verbose_name_plural = '产品'
        unique_together = ['brand', 'name']
        indexes = [
            models.Index(fields=['brand']),
            models.Index(fields=['dataset_id']),
            models.Index(fields=['is_active']),
            models.Index(fields=['pid']),
        ]
    
    def __str__(self):
        return f"{self.brand.name} - {self.name}"
    
    def save(self, *args, **kwargs):
        """重写save方法，更新品牌的dataset_id_list"""
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # 刷新品牌的dataset_id_list
        if is_new and self.is_active and self.dataset_id:
            brand = self.brand
            if self.dataset_id not in brand.dataset_id_list:
                brand.dataset_id_list.append(self.dataset_id)
                brand.save(update_fields=['dataset_id_list', 'updated_at'])

class CreatorProductMatch(models.Model):
    creator = models.ForeignKey('CreatorProfile', on_delete=models.CASCADE, verbose_name='达人')
    product = models.ForeignKey('Product', on_delete=models.CASCADE, verbose_name='产品')
    is_matched = models.BooleanField(default=False, verbose_name='是否匹配')
    match_score = models.FloatField(blank=True, null=True, verbose_name='匹配度分数')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        unique_together = ('creator', 'product')
        verbose_name = '达人-产品匹配'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.creator} - {self.product} 匹配: {self.is_matched} 分数: {self.match_score}"








class Dataset(models.Model):
    # 自增主键字段，Django 默认为每个模型提供一个 id 字段
    # 但是如果你需要自定义主键字段，可以用 `primary_key=True` 显式声明
    id = models.AutoField(primary_key=True)  # 自增主键

    # 数据集名称，最长255个字符，不能为空
    name = models.CharField(max_length=255)

    # 创建该数据集的用户，最长100个字符，不能为空
    # user = models.CharField(max_length=100)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    # 任务类型，最长50个字符，不能为空
    task_type = models.CharField(max_length=16)

    # 数据集大小，使用BigIntegerField来表示较大的整数
    size = models.CharField(max_length=64)

    # # 数据集的总图片数
    # number = models.IntegerField()

    #数据集的描述
    description = models.TextField(default="")

    # 创建时间，默认为当前时间戳
    create_time = models.DateTimeField(auto_now_add=True)  # 自动设置为当前时间（只在创建时）

    # 数据集的类别，使用 JSONField 存储类别信息
    categories = models.JSONField(default=list)  # 默认值为一个空列表

    # 该数据集是否已经有数据
    is_upload = models.BooleanField(default=False)  # 表示数据集是否已上传，默认为 False

    def update_is_upload(self, upload_status):
        """更新数据集的上传状态"""
        self.is_upload = upload_status
        self.save()  # 保存更改到数据库

    def __str__(self):
        return self.name  # 返回数据集名称作为对象的字符串表示
    

class Project(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    user = models.CharField(max_length=100)
    task_type = models.CharField(max_length=16)
    description = models.TextField(default="")
    create_time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
