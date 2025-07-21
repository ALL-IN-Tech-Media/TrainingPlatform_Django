from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import ModelFactory
from rest_framework.decorators import api_view
import json
import os
import subprocess
from accounts.models import User
from concurrent.futures import ThreadPoolExecutor
import shutil

executor = ThreadPoolExecutor(max_workers=10)

# 全局字典保存 model_id -> Popen 对象
download_processes = {}

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

def download_and_save_model(model_id, model_name):
    import subprocess, os
    from .models import ModelFactory

    save_dir = os.path.join('/home/ooin/ooin_training/model_factory', model_name.split('/')[1])
    os.makedirs(save_dir, exist_ok=True)
    try:
        env = {"HF_ENDPOINT": "https://hf-mirror.com"}
        command = [
            "huggingface-cli",
            "download",
            f"{model_name}",
            "--local-dir",
            f"{save_dir}"
        ]
        proc = subprocess.Popen(command, env={**env, **dict(**os.environ)})
        download_processes[model_id] = proc
        exit_code = proc.wait()
        if exit_code == 0:
            # 只有正常完成才设为True
            ModelFactory.objects.filter(id=model_id).update(is_downloaded=True, status='下载成功')
        else:
            # 异常退出，删除数据库记录
            print(f"模型下载进程异常退出，exit code: {exit_code}")
            ModelFactory.objects.filter(id=model_id).update(status='下载失败，请联系管理员下载')
    except Exception as e:
        ModelFactory.objects.filter(id=model_id).update(status='下载失败，请联系管理员下载')
        print(f"模型下载失败: {e} (type: {type(e)})")
    finally:
        download_processes.pop(model_id, None)

@csrf_exempt
def add_new_model(request):
    if request.method != 'POST':
        return JsonResponse({'code': 405, 'message': '请求方法错误', 'data': {}}, status=405)
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'code': 400, 'message': '请求体不是有效的JSON', 'data': {}}, status=400)
    user_id = data.get('user_id')
    model_name = data.get('model_name')
    if not user_id or not model_name:
        return JsonResponse({'code': 400, 'message': '缺少user_id或model_name参数', 'data': {}}, status=400)
    # 校验格式
    if '/' not in model_name or model_name.count('/') != 1:
        return JsonResponse({'code': 400, 'message': 'model_name格式错误，必须为“组织/模型名”', 'data': {}}, status=400)
    # 校验用户
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({'code': 400, 'message': '用户不存在', 'data': {}}, status=400)

    # 检查是否已经存在模型
    model_obj = ModelFactory.objects.filter(model_name=model_name.split('/')[1], series=model_name.split('/')[0]).first()
    if model_obj:
        if model_obj.is_downloaded:
            return JsonResponse({'code': 400, 'message': '模型已存在', 'data': {}}, status=400)
        else:
            # 复用原有记录，重启下载任务
            executor.submit(download_and_save_model, model_obj.id, model_name)
            return JsonResponse({'code': 200, 'message': '模型下载任务已重新提交，下载完成后自动入库', 'data': {'model_id': model_obj.id}})
    else:
        # 先插入数据库，is_downloaded=False
        model_obj = ModelFactory.objects.create(
            category='LLM',  # 你可以补充
            series=model_name.split('/')[0],
            model_name=model_name.split('/')[1],
            config_info={},
            description='',
            is_downloaded=False,
            status='下载中'
        )
        executor.submit(download_and_save_model, model_obj.id, model_name)
        return JsonResponse({'code': 200, 'message': '模型下载任务已提交，下载完成后自动入库', 'data': {'model_id': model_obj.id}})
        
@csrf_exempt
def get_model_list(request):
    if request.method != 'GET':
        return JsonResponse({'code': 405, 'message': '请求方法错误', 'data': {}}, status=405)
    user_id = request.GET.get('user_id')
    if not user_id:
        return JsonResponse({'code': 400, 'message': '缺少user_id参数', 'data': {}}, status=400)
    # 校验用户
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({'code': 400, 'message': '用户不存在', 'data': {}}, status=400)

    # 获取所有模型列表（不再只筛选is_downloaded=True）
    models = ModelFactory.objects.all().values(
        'id', 'category', 'series', 'model_name', 'description', 'is_downloaded', 'status'
    )
    model_list = [
        {k: v for k, v in model.items() if k != 'config_info'}
        for model in models
    ]
    return JsonResponse({'code': 200, 'message': '模型列表', 'data': {'models': model_list}})

@csrf_exempt
def cancel_download(request):
    if request.method != 'POST':
        return JsonResponse({'code': 405, 'message': '请求方法错误', 'data': {}}, status=405)
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'code': 400, 'message': '请求体不是有效的JSON', 'data': {}}, status=400)
    model_id = data.get('model_id')
    if not model_id:
        return JsonResponse({'code': 400, 'message': '缺少model_id参数', 'data': {}}, status=400)
    try:
        model_id = int(model_id)
    except Exception:
        return JsonResponse({'code': 400, 'message': 'model_id必须为整数', 'data': {}}, status=400)
        
    proc = download_processes.get(model_id)
    if proc:
        proc.terminate()  # 或 proc.kill()
        # 查找数据库记录
        model_obj = ModelFactory.objects.filter(id=model_id).first()
        if model_obj:
            # 拼接本地路径
            save_dir = os.path.join('/home/ooin/ooin_training/model_factory', model_obj.model_name)
            # 删除本地文件夹
            if os.path.exists(save_dir):
                shutil.rmtree(save_dir)
            # 删除数据库记录
            model_obj.delete()
        return JsonResponse({'code': 200, 'message': '下载已取消，记录及本地文件已删除', 'data': {}})
    else:
        model_obj = ModelFactory.objects.filter(id=model_id).first()
        if model_obj:
            save_dir = os.path.join('/home/ooin/ooin_training/model_factory', model_obj.model_name)
            if os.path.exists(save_dir):
                shutil.rmtree(save_dir)
            model_obj.delete()
        return JsonResponse({'code': 404, 'message': '未找到下载进程', 'data': {}})