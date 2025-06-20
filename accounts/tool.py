import secrets
from django.utils import timezone
from .models import UserToken

def generate_token():
    return secrets.token_urlsafe(32)  # 生成一个安全的随机 token

def validate_token(token):
    try:
        user_token = UserToken.objects.get(token=token)
        if user_token.expires_at > timezone.now():
            return user_token.user  # 返回关联的用户
        else:
            return None  # Token 已过期
    except UserToken.DoesNotExist:
        return None  # Token 不存在