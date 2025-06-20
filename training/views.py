from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from django.http import JsonResponse
from rest_framework.response import Response
from .models import TrainingModel, TrainingEpochModel
import requests
from .config import FLASK_API
# Create your views here.
@csrf_exempt  # 仅在开发时使用，生产环境中请使用更安全的方式
def create_training_task(request):
    if request.method == 'POST':
        user = request.POST.get('user')
        project_name = request.POST.get('projectName')
        pre_model_name = request.POST.get('preModelName')
        dataset_name = request.POST.get('datasetName')
        task_type = request.POST.get('taskType')
        epoch = request.POST.get('epochs')
        batch_size = request.POST.get('batchSize')
        image_size = request.POST.get('imageSize')
        id = -1


        training_task = TrainingModel(
            user=user,
            project_name=project_name,
            pre_model_name=pre_model_name,
            dataset_name=dataset_name,
            task_type=task_type,
            epoch=epoch,
            batch_size=batch_size,
            image_size=image_size,
            status="初始化",
            model_size="0MB"
        )

        try:
            training_task.save()
            id = training_task.id
            success = True
        except Exception as e:
            success = False
            error_message = "训练任务提交失败"

        # 调用Flask创建训练任务
        ####### 记得做一个连通性测试，防止卡死
        response = requests.post(f'{FLASK_API}/train_detect', json={
            'id': id,
            'user': user,
            'projectName': project_name,
            'preModelName': pre_model_name,
            'datasetName': dataset_name,
            'taskType': task_type,
            'epoch': epoch,
            'batchSize': batch_size,
            'imageSize': image_size
        })


        if success:
            return JsonResponse({'success': 'True', 'message': '训练任务提交成功'})
        else:
            return JsonResponse({'success': 'False', 'error': error_message}, status=500)
    else:
        return JsonResponse({'success': 'False', 'error': 'Invalid request method'}, status=405)
    
@csrf_exempt  # 仅在开发时使用，生产环境中请使用更安全的方式
def get_project_training_tasks(request):
    if request.method == 'GET':
        user = request.GET.get('user')
        project_name = request.GET.get('projectName')
        tasks = TrainingModel.objects.filter(user=user, project_name=project_name)

        return JsonResponse({'success': 'True', 'tasks': list(tasks.values())})
    else:
        return JsonResponse({'success': 'False', 'error': 'Invalid request method'}, status=405)    
    
@csrf_exempt  # 仅在开发时使用，生产环境中请使用更安全的方式
def delete_project_training_task(request):
    if request.method == 'GET':
        id = request.GET.get('id')
        user = request.GET.get('user')
        project_name = request.GET.get('projectName')

        # 调用Flask停止当前的ray进程
        ####### 记得做一个连通性测试，防止卡死(也就是前台点击了没有反应)
        response = requests.get(f'{FLASK_API}/stop_training_ray_task', json={
            'training_id': id
        })
        
        # 删除与训练任务相关的所有训练记录
        TrainingEpochModel.objects.filter(training_model__id=id).delete()
        
        task_deleted, _ = TrainingModel.objects.filter(id=id, user=user, project_name=project_name).delete()

        if task_deleted > 0:
            return JsonResponse({'success': True, 'message': '删除成功'})
        else:
            return JsonResponse({'success': False, 'message': '删除失败'})
    else:
        return JsonResponse({'success': False, 'message': '请求异常'})

@csrf_exempt  # 仅在开发时使用，生产环境中请使用更安全的方式
def update_training_status(request):
    if request.method == 'GET':
        training_id = request.GET.get('id')
        # 假设您还想更新 status 字段
        new_status = request.GET.get('status')  # 从请求中获取新的状态

        # 更新 TrainingModel 中的记录
        updated_count = TrainingModel.objects.filter(id=training_id).update(status=new_status)

        if updated_count > 0:
            return JsonResponse({'success': True, 'message': '更新成功'})
        else:
            return JsonResponse({'success': False, 'message': '未找到记录或更新失败'})
        
@csrf_exempt  # 仅在开发时使用，生产环境中请使用更安全的方式
@api_view(['POST'])
def insert_training_epoch_status(request):
    id = request.data.get('training_id')  # 获取 TrainingModel 的 ID
    epoch_number = request.data.get('epoch_number')
    map_50 = request.data.get('map_50')
    map_95 = request.data.get('map_95')
    precision = request.data.get('precision')
    recall = request.data.get('recall')

    # 查找对应的 TrainingModel 实例
    try:
        training_model = TrainingModel.objects.get(id=id)

        # 创建新的 TrainingEpochModel 实例
        new_epoch = TrainingEpochModel(
            training_model=training_model,  # 关联到 TrainingModel
            epoch_number=epoch_number,
            mAP50=map_50,
            mAP95=map_95,
            precision=precision,
            recall=recall
        )

        # 保存到数据库
        new_epoch.save()
        return JsonResponse({'success': True, 'message': '训练轮次数据插入成功'})

    except TrainingModel.DoesNotExist:
        return JsonResponse({'success': False, 'message': '指定的 TrainingModel 不存在'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)
    
@csrf_exempt  # 仅在开发时使用，生产环境中请使用更安全的方式
@api_view(['GET'])
def get_training_epoch_data(request):
    training_id = request.GET.get('training_id')  # 获取请求中的 training_id

    if not training_id:
        return JsonResponse({'success': False, 'message': '缺少 training_id'}, status=400)

    try:
        # 查找所有与 training_id 相关的 TrainingEpochModel 实例，并按 epoch_number 排序
        epochs = TrainingEpochModel.objects.filter(training_model__id=training_id).order_by('epoch_number')

        # 将查询结果转换为字典列表
        epoch_data = list(epochs.values('id', 'epoch_number', 'mAP50', 'mAP95', 'precision', 'recall', 'create_time'))
        print(epoch_data)

        return JsonResponse({'success': True, 'epochs': epoch_data})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)
    
@csrf_exempt  # 仅在开发时使用，生产环境中请使用更安全的方式
@api_view(['GET'])
def get_curr_epoch_data(request):
    training_id = request.GET.get('training_id')
    print(training_id)
    
    # 获取当前 training_id 最新的 epoch 数据
    latest_epoch_data = TrainingEpochModel.get_latest_epoch(training_id)
    
    if latest_epoch_data:
        # 将数据序列化为字典形式
        data = {
            'id': latest_epoch_data.id,
            'epoch_number': latest_epoch_data.epoch_number,
            'mAP50': latest_epoch_data.mAP50,
            'mAP95': latest_epoch_data.mAP95,
            'precision': latest_epoch_data.precision,
            'recall': latest_epoch_data.recall,
            'create_time': latest_epoch_data.create_time,
        }
        return Response({'success': True, 'data': data})
    else:
        return Response({'success': False, 'error': 'No data found for the given training_id.'}, status=404)
    