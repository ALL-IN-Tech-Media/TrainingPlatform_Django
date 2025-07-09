from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from django.http import JsonResponse
from rest_framework.response import Response
from .models import TrainingModel, TrainingEpochModel
import requests
from .config import FLASK_API, Monitoring_platform_api
import json
from accounts.models import User
from datasets.models import Dataset
from django.db import transaction
import os
import shutil
from datasets.config import LOCAL_DATA_DIR
import docker
from urllib.parse import urlparse

status_dict = {
    1: '训练中',
    2: '训练完成'
}

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

# Create your views here.
@csrf_exempt  # 仅在开发时使用，生产环境中请使用更安全的方式
def create_TextGeneration_task(request):
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
                response = requests.post(f'{FLASK_API}/text_generation_fine_tuning', json={
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
def create_Embedding_task(request):
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
                response = requests.post(f'{FLASK_API}/embedding_fine_tuning', json={
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
@api_view(['GET'])
def get_training_pid(request):
    if request.method == 'GET':
        training_id = request.GET.get('training_id')
        if not training_id:
            return JsonResponse({'code': 400, 'message': '缺少training_id参数', 'data': {}}, status=400)
        
        try:
            training = TrainingModel.objects.get(id=training_id)
        except TrainingModel.DoesNotExist:
            return JsonResponse({'code': 400, 'message': '训练任务不存在', 'data': {}}, status=400)
        
        response = requests.get(f'{FLASK_API}/get_training_pid', json={
                    'training_id': training_id
                })
        if response.json().get('code') != 200:
            raise Exception(f"获取pid失败: {response.json().get('message')}")
        
        pid = response.json().get('data').get('pid')
        
        return JsonResponse({'code': 200, 'message': '获取训练任务pid成功', 'data': {'pid': pid}})
    else:
        return JsonResponse({'code': 405, 'message': 'Invalid request method', 'data': {}}, status=405)

@csrf_exempt  # 仅在开发时使用，生产环境中请使用更安全的方式
def get_datasets_training_tasks(request):
    if request.method == 'GET':
        user_id = request.GET.get('user_id')
        dataset_id = request.GET.get('dataset_id')
        current_status = request.GET.get('current_status')

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
        
        # 判断 current_status 是否传递
        if current_status is None:
            tasks = TrainingModel.objects.filter(user=user, dataset=dataset)
        else:
            try:
                current_status = int(current_status)
            except ValueError:
                return JsonResponse({'code': 400, 'message': 'current_status 必须为整数', 'data': {}}, status=400)
            if current_status not in status_dict.keys():
                return JsonResponse({'code': 400, 'message': 'current_status 参数不合法', 'data': {}}, status=400)
            tasks = TrainingModel.objects.filter(user=user, dataset=dataset, status=status_dict[current_status])

        task_list = list(tasks.values())

        # 为每个任务附加最新的 epoch loss 信息
        for task in task_list:
            latest_epoch = TrainingEpochModel.objects.filter(training_model_id=task['id']).order_by('-epoch_number').first()
            if latest_epoch:
                task['latest_epoch'] = {
                    'id': latest_epoch.id,
                    'current_epoch': latest_epoch.epoch_number,
                    'train_loss': latest_epoch.train_loss,
                    'val_loss': latest_epoch.val_loss,
                    'create_time': latest_epoch.create_time,
                }
            else:
                task['latest_epoch'] = None

        return JsonResponse({'code': 200, 'message': '获取训练任务成功', 'data': {'tasks': task_list}})
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

    # 先判断训练任务是否存在
    try:
        training = TrainingModel.objects.get(id=training_id)
    except TrainingModel.DoesNotExist:
        return JsonResponse({'code': 404, 'message': '训练任务不存在', 'data': {}}, status=404)

    try:
        # 查找所有与 training_id 相关的 TrainingEpochModel 实例，并按 epoch_number 排序
        epochs = TrainingEpochModel.objects.filter(training_model=training).order_by('epoch_number')

        # 将查询结果转换为字典列表
        epoch_data = list(epochs.values('id', 'epoch_number', 'train_loss', 'val_loss', 'create_time'))

        return JsonResponse({'code': 200, 'message': '获取训练轮次数据成功', 'data': {'epochs': epoch_data}})
    except Exception as e:
        return JsonResponse({'code': 500, 'message': str(e), 'data': {}}, status=500)
    
@csrf_exempt  # 仅在开发时使用，生产环境中请使用更安全的方式
@api_view(['GET'])
def get_curr_epoch_loss(request):
    training_id = request.GET.get('training_id')
    
    # 先判断训练任务是否存在
    try:
        training = TrainingModel.objects.get(id=training_id)
    except TrainingModel.DoesNotExist:
        return JsonResponse({'code': 404, 'message': '训练任务不存在', 'data': {}}, status=404)

    try:
        # 获取当前 training_id 最新的 epoch 数据
        latest_epoch_data = TrainingEpochModel.objects.filter(training_model=training).order_by('-epoch_number').first()

        if latest_epoch_data:
            # 将数据序列化为字典形式
            data = {
                'id': latest_epoch_data.id,
                'current_epoch': latest_epoch_data.epoch_number,
                'train_loss': latest_epoch_data.train_loss,
                'val_loss': latest_epoch_data.val_loss,
                'create_time': latest_epoch_data.create_time,
            }
            return JsonResponse({'code': 200, 'message': '获取当前训练轮次数据成功', 'data': data})
        else:
            return JsonResponse({'code': 404, 'message': 'No data found for the given training_id.', 'data': {}}, status=404)
    except Exception as e:
        return JsonResponse({'code': 500, 'message': str(e), 'data': {}}, status=500)
    
@csrf_exempt  # 仅在开发时使用，生产环境中请使用更安全的方式
@api_view(['GET'])
def start_resource_monitor(request):
    training_id = request.GET.get('training_id')
    if not training_id:
        return JsonResponse({'code': 400, 'message': '缺少training_id参数', 'data': {}}, status=400)
    
    try:
        training = TrainingModel.objects.get(id=training_id)
    except TrainingModel.DoesNotExist:
        return JsonResponse({'code': 404, 'message': '训练任务不存在', 'data': {}}, status=404)
    
    # 1. 获取训练进程的pid
    try:
        response = requests.get(f'{FLASK_API}/get_training_pid', json={
            'training_id': training_id
        })
        if response.json().get('code') != 200:
            return JsonResponse({'code': 500, 'message': f"获取pid失败: {response.json().get('message')}", 'data': {}}, status=500)
        pid = response.json().get('data').get('pid')
        if not pid:
            return JsonResponse({'code': 500, 'message': '未获取到有效的pid', 'data': {}}, status=500)
    except Exception as e:
        return JsonResponse({'code': 500, 'message': f'获取pid异常: {e}', 'data': {}}, status=500)

    # 2. 调用监控平台API
    try:
        monitor_response = requests.post(f'{Monitoring_platform_api}/api/process/pid/add/', json={
            'pid': int(pid),
            'interval': 5,
        })
        if monitor_response.json().get('code') != "success":
            return JsonResponse({'code': 500, 'message': '启动资源监控失败,' + monitor_response.json().get('message'), 'data': {}}, status=500)
    except Exception as e:
        return JsonResponse({'code': 500, 'message': f'调用监控平台异常: {e}', 'data': {}}, status=500)
    
    training.is_monitor = True
    training.save()
    
    return JsonResponse({'code': 200, 'message': '启动资源监控成功,' + monitor_response.json().get('message'), 'data': {}})

@csrf_exempt  # 仅在开发时使用，生产环境中请使用更安全的方式
@api_view(['GET'])
def stop_resource_monitor(request):
    training_id = request.GET.get('training_id')
    if not training_id:
        return JsonResponse({'code': 400, 'message': '缺少training_id参数', 'data': {}}, status=400)
    
    try:
        training = TrainingModel.objects.get(id=training_id)
    except TrainingModel.DoesNotExist:
        return JsonResponse({'code': 404, 'message': '训练任务不存在', 'data': {}}, status=404)
    
    # 1. 获取训练进程的pid
    try:
        response = requests.get(f'{FLASK_API}/get_training_pid', json={
            'training_id': training_id
        })
        if response.json().get('code') != 200:
            return JsonResponse({'code': 500, 'message': f"获取pid失败: {response.json().get('message')}", 'data': {}}, status=500)
        pid = response.json().get('data').get('pid')
        if not pid:
            return JsonResponse({'code': 500, 'message': '未获取到有效的pid', 'data': {}}, status=500)
    except Exception as e:
        return JsonResponse({'code': 500, 'message': f'获取pid异常: {e}', 'data': {}}, status=500)

    # 2. 调用监控平台API
    try:
        monitor_response = requests.post(f'{Monitoring_platform_api}/api/process/pid/remove/', json={
            'pid': int(pid),
        })
        if monitor_response.json().get('code') != "success":
            return JsonResponse({'code': 500, 'message': '停止资源监控失败,' + monitor_response.json().get('message'), 'data': {}}, status=500)
    except Exception as e:
        return JsonResponse({'code': 500, 'message': f'调用监控平台异常: {e}', 'data': {}}, status=500)
    
    training.is_monitor = False
    training.save()
    
    return JsonResponse({'code': 200, 'message': '停止资源监控成功,' + monitor_response.json().get('message'), 'data': {}})

@csrf_exempt  # 仅在开发时使用，生产环境中请使用更安全的方式
@api_view(['POST'])
def deploy_model(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'code': 400, 'message': '请求体不是有效的JSON', 'data': {}}, status=400)
    
    user_id = data.get('user_id')
    dataset_id = data.get('dataset_id')
    training_id = data.get('training_id')
    # deploy_epoch = data.get('deploy_epoch')
    gpu = data.get('gpu')
    max_num_seqs = data.get('max_num_seqs')
    max_model_len = data.get('max_model_len')
    max_num_batched_tokens = data.get('max_num_batched_tokens')
    container_name = data.get('container_name')  # 可选


    if not all([user_id, dataset_id, training_id, gpu, max_num_seqs, max_model_len, max_num_batched_tokens]):
        return JsonResponse({'code': 400, 'message': '缺少参数', 'data': {}}, status=400)

    try:
        training = TrainingModel.objects.get(id=training_id)
    except TrainingModel.DoesNotExist:
        return JsonResponse({'code': 404, 'message': '训练任务不存在', 'data': {}}, status=404)

    # 组装请求体
    payload = {
        "user_id": user_id,
        "dataset_id": dataset_id,
        "training_id": training_id,
        "gpu": gpu,
        "max_num_seqs": max_num_seqs,
        "max_model_len": max_model_len,
        "max_num_batched_tokens": max_num_batched_tokens,
    }
    if container_name:
        payload["container_name"] = container_name

    flask_url = f"{FLASK_API}/deploy_model"

    try:
        flask_response = requests.post(flask_url, json=payload, timeout=60)
        flask_data = flask_response.json()
        if flask_response.status_code == 200 and flask_data.get("code") == 200:
            training.is_deploy = True
            training.save()
            return JsonResponse({'code': 200, 'message': '容器已启动', 'data': {'host_port': flask_data.get('data').get('host_port'), 'deploy_ip': urlparse(FLASK_API).hostname + ':'+ str(flask_data.get('data').get('host_port'))}})
        else:
            return JsonResponse({'code': 500, 'message': f"Flask部署失败: {flask_data.get('message')}", 'data': {}}, status=500)
    except Exception as e:
        return JsonResponse({'code': 500, 'message': f'调用Flask部署接口异常: {e}', 'data': {}}, status=500)

@csrf_exempt  # 仅在开发时使用，生产环境中请使用更安全的方式
@api_view(['POST'])
def embedding_deploy_model(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'code': 400, 'message': '请求体不是有效的JSON', 'data': {}}, status=400)
    
    user_id = data.get('user_id')
    dataset_id = data.get('dataset_id')
    training_id = data.get('training_id')
    gpu = data.get('gpu')
    max_length = data.get('max_length')
    container_name = data.get('container_name')  # 可选


    if not all([user_id, dataset_id, training_id, gpu, max_length]):
        return JsonResponse({'code': 400, 'message': '缺少参数', 'data': {}}, status=400)

    try:
        training = TrainingModel.objects.get(id=training_id)
    except TrainingModel.DoesNotExist:
        return JsonResponse({'code': 404, 'message': '训练任务不存在', 'data': {}}, status=404)

    # 组装请求体
    payload = {
        "user_id": user_id,
        "dataset_id": dataset_id,
        "training_id": training_id,
        "gpu": gpu,
        "max_length": max_length,
    }
    if container_name:
        payload["container_name"] = container_name

    flask_url = f"{FLASK_API}/embedding_deploy_model"

    try:
        flask_response = requests.post(flask_url, json=payload, timeout=60)
        flask_data = flask_response.json()
        if flask_response.status_code == 200 and flask_data.get("code") == 200:
            training.is_deploy = True
            training.save()
            return JsonResponse({'code': 200, 'message': '容器已启动', 'data': {'host_port': flask_data.get('data').get('host_port'), 'deploy_ip': urlparse(FLASK_API).hostname + ':'+ str(flask_data.get('data').get('host_port'))}})
        else:
            return JsonResponse({'code': 500, 'message': f"Flask部署失败: {flask_data.get('message')}", 'data': {}}, status=500)
    except Exception as e:
        return JsonResponse({'code': 500, 'message': f'调用Flask部署接口异常: {e}', 'data': {}}, status=500)    

@csrf_exempt  # 仅在开发时使用，生产环境中请使用更安全的方式
@api_view(['POST'])
def stop_deploy_model(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'code': 400, 'message': '请求体不是有效的JSON', 'data': {}}, status=400)
    
    user_id = data.get('user_id')
    dataset_id = data.get('dataset_id')
    training_id = data.get('training_id')

    if not all([user_id, dataset_id, training_id]):
        return JsonResponse({'code': 400, 'message': '缺少参数', 'data': {}}, status=400)
    
    try:
        training = TrainingModel.objects.get(id=training_id)
    except TrainingModel.DoesNotExist:
        return JsonResponse({'code': 404, 'message': '训练任务不存在', 'data': {}}, status=404)
    
    try:
        response = requests.post(f'{FLASK_API}/stop_deploy_model', json={
            'user_id': user_id,
            'dataset_id': dataset_id,
            'training_id': training_id
        })
        if response.json().get('code') != 200:
            return JsonResponse({'code': 500, 'message': f"停止部署失败: {response.json().get('message')}", 'data': {}}, status=500)
    except Exception as e:
        return JsonResponse({'code': 500, 'message': f'调用Flask停止部署接口异常: {e}', 'data': {}}, status=500)
    
    training.is_deploy = False
    training.save()
    
    return JsonResponse({'code': 200, 'message': '成功停止部署', 'data': {}})