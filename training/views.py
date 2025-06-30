from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from django.http import JsonResponse
from rest_framework.response import Response
from .models import TrainingModel, TrainingEpochModel
import requests
from .config import FLASK_API
import json
from accounts.models import User
from datasets.models import Dataset
from django.db import transaction
import os
import shutil
from datasets.config import LOCAL_DATA_DIR

# Create your views here.
@csrf_exempt  # 仅在开发时使用，生产环境中请使用更安全的方式
def create_training_task(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            return JsonResponse({'code': 400, 'message': '请求体不是有效的JSON', 'data': {}}, status=400)
        
        user_id = data.get('user_id')
        dataset_id = data.get('dataset_id')
        model_name = data.get('model_name')
        training_type = data.get('training_type')
        epochs = data.get('epochs')
        batch_size = data.get('batch_size')
        max_length = data.get('max_length')
        save_epoch = data.get('save_epoch')
        gpu_machine_ip = data.get('gpu_machine_ip')
        gpu = data.get('gpu')

        # 检查参数是否传递（None），而不是值为0
        if any(x is None for x in [model_name, user_id, dataset_id, training_type, epochs, batch_size, max_length]):
            return JsonResponse({'code': 400, 'message': '缺少必要参数', 'data': {}}, status=400)

        # 类型和范围校验
        try:
            user_id = int(user_id)
            dataset_id = int(dataset_id)
            epochs = int(epochs)
            batch_size = int(batch_size)
            max_length = int(max_length)
            save_batch = int(save_epoch)
        except (ValueError, TypeError):
            return JsonResponse({'code': 400, 'message': 'user_id、dataset_id、epochs、batch_size、max_length 必须为整数', 'data': {}}, status=400)

        if user_id <= 0 or dataset_id <= 0 or epochs <= 0 or batch_size <= 0 or max_length <= 0:
            return JsonResponse({'code': 400, 'message': 'user_id、dataset_id、epochs、batch_size、max_length 必须为正整数', 'data': {}}, status=400)

        # 用户存在性校验
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return JsonResponse({'code': 400, 'message': '用户不存在', 'data': {}}, status=400)
        # 数据集存在性及归属校验
        try:
            dataset = Dataset.objects.get(id=dataset_id, user=user)
        except Dataset.DoesNotExist:
            return JsonResponse({'code': 400, 'message': '该用户下不存在此数据集', 'data': {}}, status=400)

        training_task = TrainingModel(
            user=user,
            dataset=dataset,
            model_name=model_name,
            training_type=training_type,
            epochs=epochs,
            batch_size=batch_size,
            max_length=max_length,
            status="初始化"
        )

        try:
            with transaction.atomic():
                training_task.save()
                training_id = training_task.id

                # 调用Flask创建训练任务
                response = requests.post(f'{FLASK_API}/train_fine_tuning', json={
                    'training_id': training_id,
                    'user_id': user_id,  # 注意这里要传id或序列化
                    'dataset_id': dataset_id,
                    'model_name': model_name,
                    'training_type': training_type,
                    'epochs': epochs,
                    'batch_size': batch_size,
                    'max_length': max_length,
                    'save_epoch': save_epoch,
                    'gpu': gpu
                })
                # 可以根据 response 判断 Flask 是否成功
                if response.json().get('code') != 200:
                    raise Exception(f"Flask任务创建失败: {response.json().get('message')}")

            # 只有数据库和Flask都成功才会走到这里
            return JsonResponse({'code': 200, 'message': '训练任务提交成功', 'data': {'training_id': training_id}})

        except Exception as e:
            # 只要有异常，数据库操作会回滚
            return JsonResponse({'code': 500, 'message': f'训练任务提交失败: {e}', 'data': {}}, status=500)
    else:
        return JsonResponse({'code': 405, 'message': 'Invalid request method', 'data': {}}, status=405)
    
@csrf_exempt  # 仅在开发时使用，生产环境中请使用更安全的方式
def get_datasets_training_tasks(request):
    if request.method == 'GET':
        user_id = request.GET.get('user_id')
        dataset_id = request.GET.get('dataset_id')

        # 用户存在性校验
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return JsonResponse({'code': 400, 'message': '用户不存在', 'data': {}}, status=400)
        # 数据集存在性及归属校验
        try:
            dataset = Dataset.objects.get(id=dataset_id, user=user)
        except Dataset.DoesNotExist:
            return JsonResponse({'code': 400, 'message': '该用户下不存在此数据集', 'data': {}}, status=400)

        tasks = TrainingModel.objects.filter(user=user, dataset=dataset)

        return JsonResponse({'code': 200, 'message': '获取训练任务成功', 'data': {'tasks': list(tasks.values())}})
    else:
        return JsonResponse({'code': 405, 'message': 'Invalid request method', 'data': {}}, status=405)    
    
@csrf_exempt  # 仅在开发时使用，生产环境中请使用更安全的方式
def delete_training_task(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            return JsonResponse({'code': 400, 'message': '请求体不是有效的JSON', 'data': {}}, status=400)
        
        training_id = data.get('training_id')
        user_id = data.get('user_id')
        dataset_id = data.get('dataset_id')

        try:
            training = TrainingModel.objects.get(id=training_id)
        except TrainingModel.DoesNotExist:
            return JsonResponse({'code': 404, 'message': '训练任务不存在', 'data': {}}, status=404)
        
        if training.dataset_id != int(dataset_id):
            return JsonResponse({'code': 400, 'message': '该训练任务未使用此数据集', 'data': {}}, status=400)

        # 调用Flask停止当前的ray进程
        ####### 记得做一个连通性测试，防止卡死(也就是前台点击了没有反应)
        response = requests.get(f'{FLASK_API}/stop_training_ray_task', json={
            'training_id': training_id
        })

        # 删除本地磁盘数据集文件夹
        save_model_dir = os.path.join(LOCAL_DATA_DIR, str(user_id), str(dataset_id), 'save_models', str(training_id))
        if os.path.exists(save_model_dir):
            shutil.rmtree(save_model_dir)
        
        # 删除与训练任务相关的所有训练记录
        TrainingEpochModel.objects.filter(training_model__id=training_id).delete()
        
        task_deleted, _ = TrainingModel.objects.filter(id=training_id).delete()

        if task_deleted > 0:
            return JsonResponse({'code': 200, 'message': '删除成功', 'data': {}})
        else:
            return JsonResponse({'code': 500, 'message': '删除失败', 'data': {}})
    else:
        return JsonResponse({'code': 405, 'message': 'Invalid request method', 'data': {}}, status=405)

@csrf_exempt  # 仅在开发时使用，生产环境中请使用更安全的方式
@api_view(['POST'])
def update_training_status(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            return JsonResponse({'code': 400, 'message': '请求体不是有效的JSON', 'data': {}}, status=400)
        
        training_id = data.get('training_id')
        # 假设您还想更新 status 字段
        new_status = data.get('status')  # 从请求中获取新的状态

        # 更新 TrainingModel 中的记录
        model = TrainingModel.objects.filter(id=training_id)
        updated_count = TrainingModel.objects.filter(id=training_id).update(status=new_status)

        if updated_count > 0:
            return JsonResponse({'code': 200, 'message': '更新成功', 'data': {}})
        else:
            return JsonResponse({'code': 500, 'message': '未找到记录或更新失败', 'data': {}})
        
@csrf_exempt  # 仅在开发时使用，生产环境中请使用更安全的方式
@api_view(['POST'])
def insert_training_epoch_loss(request):
    id = request.data.get('training_id')  # 获取 TrainingModel 的 ID
    epoch_number = request.data.get('epoch_number')
    train_loss = request.data.get('train_loss')
    val_loss = request.data.get('val_loss')

    # 查找对应的 TrainingModel 实例
    try:
        training_model = TrainingModel.objects.get(id=id)

        # 创建新的 TrainingEpochModel 实例
        new_epoch = TrainingEpochModel(
            training_model=training_model,  # 关联到 TrainingModel
            epoch_number=epoch_number,
            train_loss=train_loss,
            val_loss=val_loss
        )

        # 保存到数据库
        new_epoch.save()
        return JsonResponse({'code': 200, 'message': '训练轮次数据插入成功', 'data': {}})

    except TrainingModel.DoesNotExist:
        return JsonResponse({'code': 404, 'message': '指定的 TrainingModel 不存在', 'data': {}}, status=404)
    except Exception as e:
        return JsonResponse({'code': 500, 'message': str(e), 'data': {}}, status=500)
    
@csrf_exempt  # 仅在开发时使用，生产环境中请使用更安全的方式
@api_view(['GET'])
def get_training_epoch_loss(request):
    training_id = request.GET.get('training_id')  # 获取请求中的 training_id

    if not training_id:
        return JsonResponse({'code': 400, 'message': '缺少 training_id', 'data': {}}, status=400)

    try:
        # 查找所有与 training_id 相关的 TrainingEpochModel 实例，并按 epoch_number 排序
        epochs = TrainingEpochModel.objects.filter(training_model__id=training_id).order_by('epoch_number')

        # 将查询结果转换为字典列表
        epoch_data = list(epochs.values('id', 'epoch_number', 'train_loss', 'val_loss', 'create_time'))
        print(epoch_data)

        return JsonResponse({'code': 200, 'message': '获取训练轮次数据成功', 'data': {'epochs': epoch_data}})
    except Exception as e:
        return JsonResponse({'code': 500, 'message': str(e), 'data': {}}, status=500)
    
@csrf_exempt  # 仅在开发时使用，生产环境中请使用更安全的方式
@api_view(['GET'])
def get_curr_epoch_loss(request):
    training_id = request.GET.get('training_id')
    print(training_id)
    
    # 获取当前 training_id 最新的 epoch 数据
    latest_epoch_data = TrainingEpochModel.get_latest_epoch(training_id)
    
    if latest_epoch_data:
        # 将数据序列化为字典形式
        data = {
            'id': latest_epoch_data.id,
            'epoch_number': latest_epoch_data.epoch_number,
            'train_loss': latest_epoch_data.train_loss,
            'val_loss': latest_epoch_data.val_loss,
            'create_time': latest_epoch_data.create_time,
        }
        return JsonResponse({'code': 200, 'message': '获取当前训练轮次数据成功', 'data': data})
    else:
        return JsonResponse({'code': 404, 'message': 'No data found for the given training_id.', 'data': {}}, status=404)
