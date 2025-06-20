from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
import requests
from .models import User
from django.db import IntegrityError
from django.contrib.auth import authenticate
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.hashers import check_password
from .tool import generate_token
from .models import UserToken  # 确保导入你的 UserToken 模型
from django.utils import timezone

@csrf_exempt
@api_view(['POST'])
def login(request):
    email = request.data.get('email')
    password = request.data.get('password')

    print(f"Attempting to log in with email: {email} and password: {password}")

    # 检查用户是否存在
    user = User.objects.filter(email=email).first()
    
    if user is None:
        print("用户不存在")
        return Response({
            'success': False,
            'message': "用户不存在"
        }, status=status.HTTP_404_NOT_FOUND)

    print(f"找到用户: {user.username}")  # 这里打印找到的用户名

    # 直接比较明文密码
    if user.password == password:
        print("密码验证成功")
        
        # 生成 token
        token = generate_token()
        
        # 设置 token 过期时间（例如 1 小时后）
        expires_at = timezone.now() + timezone.timedelta(hours=1)

        # 检查是否已存在 token
        user_token, created = UserToken.objects.update_or_create(
            user=user,
            defaults={'token': token, 'expires_at': expires_at}
        )

        if created:
            print("创建新的 token")
        else:
            print("更新现有的 token")

        return Response({
            'success': True,
            'message': "登录成功",
            'token': token,
            'username': user.username,
            'email': user.email
        }, status=status.HTTP_200_OK)
    else:
        print("密码验证失败")
        return Response({
            'success': False,
            'message': "邮箱或密码错误"
        }, status=status.HTTP_401_UNAUTHORIZED)

@csrf_exempt
@api_view(['POST'])
def register(request):
    username = request.data.get('username')
    email = request.data.get('email')
    password = request.data.get('password')
    
    user = User(username=username, email=email, password=password)
    
    try:
        user.save()
        success = True
    except IntegrityError as e:
        success = False
        error_message = str(e)  # 获取异常信息

    if success:
        return JsonResponse({'success': True, 'message': "注册成功"})
    else:
        if "Duplicate entry" in error_message:
            return JsonResponse({'success': False, 'message': "邮箱已被注册"})
        return JsonResponse({'success': False, 'message': "注册失败"})

@csrf_exempt
@api_view(['GET'])
def get_user_info(request):
    # 从请求头中获取自定义 token
    token = request.headers.get('Authorization')
    print(token)
    
    if token is None:
        return Response({
            'success': False,
            'message': "未提供 token"
        }, status=401)

    # 验证 token
    try:
        user_token = UserToken.objects.get(token=token)
        
        # 检查 token 是否过期
        if user_token.expires_at < timezone.now():
            return Response({
                'success': False,
                'message': "Token 已过期"
            }, status=401)

        # 获取用户信息
        user = user_token.user  # 通过 token 获取用户对象

        return Response({
            'success': True,
            'username': user.username,
            'email': user.email
        }, status=200)

    except UserToken.DoesNotExist:
        return Response({
            'success': False,
            'message': "无效的 token"
        }, status=401)

    
