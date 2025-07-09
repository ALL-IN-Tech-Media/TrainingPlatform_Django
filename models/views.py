from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import ModelFactory
from rest_framework.decorators import api_view
import json

# Create your views here.
@csrf_exempt  # 仅在开发时使用，生产环境中请使用更安全的方式
@api_view(['GET'])
def get_task_model_list(request):
    if request.method == 'GET':
        user_id = request.GET.get('user_id')
        datasets_id = request.GET.get('datasets_id')
        training_id = request.GET.get('training_id')
        if not user_id or not datasets_id or not training_id:
            return JsonResponse({'code': 400, 'message': 'user_id, datasets_id, training_id is required', 'data': {}}, status=400)
    return JsonResponse({'code': 200, 'message': 'get_task_model_list', 'data': {}}, status=200)

@csrf_exempt  # 仅在开发时使用，生产环境中请使用更安全的方式
@api_view(['POST'])
def add_new_model(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            return JsonResponse({'code': 400, 'message': '请求体不是有效的JSON', 'data': {}}, status=400)
        category = data.get('category')
        series = data.get('series')
        model_name = data.get('model_name')
        config_info = data.get('config_info')
        description = data.get('description')
        if not category or not series or not model_name:
            return JsonResponse({'code': 400, 'message': 'category, series, model_name is required', 'data': {}}, status=400)
        
        # 检查是否已存在
        if ModelFactory.objects.filter(category=category, series=series, model_name=model_name).exists():
            return JsonResponse({'code': 409, 'message': '该模型已存在', 'data': {}}, status=409)
        
        model = ModelFactory(category=category, series=series, model_name=model_name, config_info=config_info, description=description)
        model.save()
        return JsonResponse({'code': 200, 'message': '添加新模型成功', 'data': {}}, status=200)
    return JsonResponse({'code': 405, 'message': '请求方式错误', 'data': {}}, status=405)

