from django.db import models

# Create your models here.

class User(models.Model):
    id = models.AutoField(primary_key=True)  # 自增id为主键
    username = models.CharField(max_length=64, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)


    def get_username(self):
        return self.username
    

class UserToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # 关联用户
    token = models.CharField(max_length=64, unique=True)  # 存储 token
    created_at = models.DateTimeField(auto_now_add=True)  # 创建时间
    expires_at = models.DateTimeField()  # 过期时间
