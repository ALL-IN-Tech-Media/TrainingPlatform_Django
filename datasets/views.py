import requests
import os
import shutil
import glob
import zipfile
import duckdb
import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import FileSystemStorage
from .models import Dataset, Project, CreatorProfile, Product, CreatorProductMatch
from .tool import check_directory_structure_detect, delete_temp_dir, get_categories
from .minio_tools import upload_to_minio, delete_from_minio, get_dataset_link
from .config import TEMP_ROOT_DIR, LOCAL_IP, BUCKET_NAME, LOCAL_DATA_DIR
from concurrent.futures import ThreadPoolExecutor
from accounts.models import User
from django.forms import model_to_dict
from django.db.models.fields.files import ImageFieldFile
import pandas as pd
import numpy as np
from decimal import Decimal
from datetime import datetime

executor = ThreadPoolExecutor(max_workers=10)
task_type_map = {'Detect':'Detection', 'Classify':'Classification'}

# Create your views here.
@csrf_exempt
def create_dataset(request):
    """创建一个数据集的接口，包含参数校验、用户校验、名称唯一性校验，统一返回格式。保证本地文件和数据库原子性。"""
    if request.method == 'POST':
        import shutil
        from django.db import transaction
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            return JsonResponse({'code': 400, 'message': '请求体不是有效的JSON', 'data': {}}, status=400)
        name = data.get('name')
        user_id = data.get('user_id')
        task_type = data.get('task_type', '')
        size = data.get('size', '')
        description = data.get('description', '')
        categories = data.get('categories', [])
        # 参数完整性校验
        if not name or not user_id:
            return JsonResponse({'code': 400, 'message': '缺少必要参数: name 或 user_id', 'data': {}}, status=400)
        # 用户存在性校验
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return JsonResponse({'code': 400, 'message': '用户不存在', 'data': {}}, status=400)
        # 名称唯一性校验（同一用户下）
        if Dataset.objects.filter(name=name, user=user).exists():
            return JsonResponse({'code': 400, 'message': '该用户下数据集名称已存在', 'data': {}}, status=400)

        user_dir = os.path.join(LOCAL_DATA_DIR, str(user.id))
        try:
            with transaction.atomic():
                # 先插入数据库，获取id
                dataset = Dataset(
                    name=name,
                    user=user,
                    task_type=task_type,
                    size=size,
                    description=description,
                    categories=categories
                )
                dataset.save()
                # 再创建文件夹和parquet文件
                real_dataset_dir = os.path.join(user_dir, str(dataset.id), 'datasets')
                if not os.path.exists(user_dir):
                    os.makedirs(user_dir)
                if not os.path.exists(real_dataset_dir):
                    os.makedirs(real_dataset_dir)
                real_parquet_path = os.path.join(real_dataset_dir, f"{dataset.id}.parquet")
        except Exception as e:
            # 失败时清理本地文件夹
            if os.path.exists(real_dataset_dir):
                shutil.rmtree(real_dataset_dir, ignore_errors=True)
            return JsonResponse({'code': 500, 'message': f'创建数据集失败: {e}', 'data': {}}, status=500)

        return JsonResponse({'code': 200, 'message': '数据集创建成功', 'data': {'dataset_id': dataset.id}})
    return JsonResponse({'code': 400, 'message': '请求方法错误', 'data': {}}, status=400)

@csrf_exempt
def add_data_to_dataset(request):
    """根据传入的product_id和creator_id插入一条CreatorProductMatch记录，直接写入data.jsonl，统一返回格式"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            return JsonResponse({'code': 400, 'message': '请求体不是有效的JSON', 'data': {}}, status=400)
        product_id = data.get('product_id')
        creator_id = data.get('creator_id')
        is_matched = data.get('is_matched')
        prompt = data.get('prompt')
        dataset_id = data.get('dataset_id')
        user_id = data.get('user_id')
        if not product_id or not creator_id or not dataset_id or not user_id or prompt is None:
            return JsonResponse({'code': 400, 'message': '缺少product_id或creator_id或dataset_id或user_id或prompt参数', 'data': {}})
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return JsonResponse({'code': 400, 'message': '产品不存在', 'data': {}}, status=400)
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return JsonResponse({'code': 400, 'message': '用户不存在', 'data': {}}, status=400)
        try:
            creator = CreatorProfile.objects.get(id=creator_id)
        except CreatorProfile.DoesNotExist:
            return JsonResponse({'code': 400, 'message': '达人不存在', 'data': {}}, status=400)
        try:
            dataset = Dataset.objects.get(id=dataset_id, user_id=user_id)
        except Dataset.DoesNotExist:
            return JsonResponse({'code': 400, 'message': '数据集不存在', 'data': {}}, status=400)

        # 组装json数据
        def clean_filefields(d):
            for k, v in d.items():
                if isinstance(v, ImageFieldFile):
                    d[k] = None
            return d
        creator_dict = model_to_dict(creator)
        product_dict = model_to_dict(product)
        creator_dict = clean_filefields(creator_dict)
        product_dict = clean_filefields(product_dict)
        creator_dict['creator_id'] = creator_dict.pop('id')
        product_dict['product_id'] = product_dict.pop('id')
        creator_prefixed = {f'creator_{k}': v for k, v in creator_dict.items()}
        product_prefixed = {f'product_{k}': v for k, v in product_dict.items()}
        row = {**creator_prefixed, **product_prefixed, 'is_matched': is_matched, 'prompt': prompt, 'create_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

        # 组装user内容
        user_content = []
        for k, v in row.items():
            if k not in ['is_matched', 'prompt', 'create_time']:
                user_content.append(f"{k}:{v}")
        user_content_str = ','.join(user_content)
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_content_str},
            {"role": "assistant", "content": str(is_matched)}
        ]
        # 写入data.jsonl
        save_dir = os.path.join(LOCAL_DATA_DIR, str(user.id), str(dataset.id), 'datasets')
        os.makedirs(save_dir, exist_ok=True)
        jsonl_path = os.path.join(save_dir, "data.json")
        with open(jsonl_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps({"messages": messages}, ensure_ascii=False) + '\n')
        return JsonResponse({'code': 200, 'message': '数据添加成功', 'data': {}})
    return JsonResponse({'code': 400, 'message': '请求方法错误', 'data': {}})

@csrf_exempt
def get_dataset_list(request):
    """根据传入的用户id返回该用户所有数据集信息，统一返回格式"""
    if request.method == 'GET':
        user_id = request.GET.get('user_id')
        if not user_id:
            return JsonResponse({'code': 400, 'message': '缺少user_id参数', 'data': {}}, status=400)
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return JsonResponse({'code': 400, 'message': '用户不存在', 'data': {}}, status=400)
        datasets = Dataset.objects.filter(user=user)
        dataset_list = list(datasets.values())
        return JsonResponse({'code': 200, 'message': '查询成功', 'data': {'datasets': dataset_list}})
    return JsonResponse({'code': 400, 'message': '请求方法错误', 'data': {}}, status=400)

@csrf_exempt
def get_dataset_detail(request):
    """根据传入的dataset_id和user_id返回该数据集的信息，统一返回格式"""
    if request.method == 'GET':
        dataset_id = request.GET.get('dataset_id')
        user_id = request.GET.get('user_id')
        if not dataset_id or not user_id:
            return JsonResponse({'code': 400, 'message': '缺少dataset_id或user_id参数', 'data': {}}, status=400)
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return JsonResponse({'code': 400, 'message': '用户不存在', 'data': {}}, status=400)
        try:
            dataset = Dataset.objects.get(id=dataset_id, user=user)
        except Dataset.DoesNotExist:
            return JsonResponse({'code': 400, 'message': '数据集不存在', 'data': {}}, status=400)
        return JsonResponse({'code': 200, 'message': '查询成功', 'data': {'dataset': model_to_dict(dataset)}})
    return JsonResponse({'code': 400, 'message': '请求方法错误', 'data': {}}, status=400)

@csrf_exempt
def delete_dataset_api(request):
    """根据user_id和dataset_id删除数据集，统一返回格式"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            return JsonResponse({'code': 400, 'message': '请求体不是有效的JSON', 'data': {}}, status=400)
        user_id = data.get('user_id')
        dataset_id = data.get('dataset_id')
        if not user_id or not dataset_id:
            return JsonResponse({'code': 400, 'message': '缺少user_id或dataset_id参数', 'data': {}}, status=400)
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return JsonResponse({'code': 400, 'message': '用户不存在', 'data': {}}, status=400)
        try:
            dataset = Dataset.objects.get(id=dataset_id, user=user)
        except Dataset.DoesNotExist:
            return JsonResponse({'code': 400, 'message': '数据集不存在', 'data': {}}, status=400)
        
        # 删除本地磁盘数据集文件夹
        user_dir = os.path.join(LOCAL_DATA_DIR, str(user.id))
        dataset_dir = os.path.join(user_dir, str(dataset.id))
        if os.path.exists(dataset_dir):
            shutil.rmtree(dataset_dir)

        # 删除数据库中的数据集
        dataset.delete()
        return JsonResponse({'code': 200, 'message': '数据集删除成功', 'data': {}})
    return JsonResponse({'code': 400, 'message': '请求方法错误', 'data': {}}, status=400)

@csrf_exempt
def get_match_list(request):
    """获取CreatorProductMatch数据列表，支持分页和筛选（从Parquet文件读取）"""
    if request.method == 'GET':
        page = request.GET.get('page')
        page_size = request.GET.get('page_size')
        user_id = request.GET.get('user_id')
        dataset_id = request.GET.get('dataset_id')
        # 参数校验
        if not page or not page_size or not user_id or not dataset_id:
            return JsonResponse({'code': 400, 'message': '缺少参数: page, page_size, user_id, dataset_id', 'data': {}}, status=400)
        try:
            page = int(page)
            page_size = int(page_size)
            if page < 1 or page_size < 1:
                raise ValueError
        except ValueError:
            return JsonResponse({'code': 400, 'message': 'page和page_size必须为正整数', 'data': {}}, status=400)
        # 校验用户和数据集
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return JsonResponse({'code': 400, 'message': '用户不存在', 'data': {}}, status=400)
        try:
            dataset = Dataset.objects.get(id=dataset_id, user=user)
        except Dataset.DoesNotExist:
            return JsonResponse({'code': 400, 'message': '数据集不存在', 'data': {}}, status=400)
        # 拼接Parquet文件路径
        user_dir = os.path.join(LOCAL_DATA_DIR, str(user.id))
        dataset_dir = os.path.join(user_dir, str(dataset.id), 'datasets')
        parquet_path = os.path.join(dataset_dir, f"{dataset.id}.parquet")
        if not os.path.exists(parquet_path):
            return JsonResponse({'code': 200, 'message': '暂无数据', 'data': {'total': 0, 'matches': []}})
        try:
            df = pd.read_parquet(parquet_path)
        except Exception as e:
            return JsonResponse({'code': 500, 'message': f'Parquet文件读取失败: {str(e)}', 'data': {}})
        total = len(df)
        start = (page - 1) * page_size
        end = start + page_size
        # 分页
        page_df = df.iloc[start:end]
        # 转为dict
        matches = page_df.fillna('').to_dict(orient='records')

        def convert_obj(obj):
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            if isinstance(obj, Decimal):
                return float(obj)
            if isinstance(obj, dict):
                return {k: convert_obj(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [convert_obj(i) for i in obj]
            return obj
        matches = [convert_obj(item) for item in matches]
        return JsonResponse({'code': 200, 'message': '查询成功', 'data': {'total': total, 'matches': matches}})
    return JsonResponse({'code': 400, 'message': '请求方法错误', 'data': {}})

@csrf_exempt
def remove_data_from_dataset(request):
    """从数据集中删除指定的达人和产品匹配记录"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            return JsonResponse({'code': 400, 'message': '请求体不是有效的JSON', 'data': {}}, status=400)
        
        product_id = data.get('product_id')
        creator_id = data.get('creator_id')
        dataset_id = data.get('dataset_id')
        user_id = data.get('user_id')
        
        if not product_id or not creator_id or not dataset_id or not user_id:
            return JsonResponse({'code': 400, 'message': '缺少必要参数', 'data': {}}, status=400)
            
        try:
            dataset = Dataset.objects.get(id=dataset_id, user_id=user_id)
        except Dataset.DoesNotExist:
            return JsonResponse({'code': 400, 'message': '数据集不存在', 'data': {}}, status=400)
            
        dataset_dir = os.path.join(LOCAL_DATA_DIR, str(dataset.user.id), str(dataset.id), 'datasets')
        parquet_path = os.path.join(dataset_dir, f"{dataset.id}.parquet")
        
        if not os.path.exists(parquet_path):
            return JsonResponse({'code': 400, 'message': '数据文件不存在', 'data': {}}, status=400)
            
        try:
            # 使用 duckdb 删除指定记录
            con = duckdb.connect()
            # 创建临时表存储要保留的数据
            query = f"""
            CREATE TABLE temp_table AS 
            SELECT * FROM read_parquet('{parquet_path}')
            WHERE NOT (product_id = {product_id} AND creator_id = {creator_id})
            """
            con.execute(query)
            
            # 将临时表写回 parquet 文件
            con.execute(f"COPY temp_table TO '{parquet_path}' (FORMAT PARQUET)")
            con.close()
            
            return JsonResponse({'code': 200, 'message': '匹配关系删除成功', 'data': {}})
            
        except Exception as e:
            return JsonResponse({'code': 500, 'message': f'删除数据时发生错误: {str(e)}', 'data': {}}, status=500)
            
    return JsonResponse({'code': 400, 'message': '请求方法错误', 'data': {}}, status=400)

@csrf_exempt
def export_dataset_to_jsonl(request):
    """将parquet文件内容导出为指令微调所需的jsonl格式，并写入data.json文件"""
    if request.method == 'GET':
        user_id = request.GET.get('user_id')
        dataset_id = request.GET.get('dataset_id')
        if not user_id or not dataset_id:
            return JsonResponse({'code': 400, 'message': '缺少user_id或dataset_id参数', 'data': {}}, status=400)
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return JsonResponse({'code': 400, 'message': '用户不存在', 'data': {}}, status=400)
        try:
            dataset = Dataset.objects.get(id=dataset_id, user=user)
        except Dataset.DoesNotExist:
            return JsonResponse({'code': 400, 'message': '数据集不存在', 'data': {}}, status=400)
        user_dir = os.path.join(LOCAL_DATA_DIR, str(user.id))
        dataset_dir = os.path.join(user_dir, str(dataset.id), 'datasets')
        parquet_path = os.path.join(dataset_dir, f"{dataset.id}.parquet")
        json_path = os.path.join(dataset_dir, "data.json")
        if not os.path.exists(parquet_path):
            return JsonResponse({'code': 400, 'message': '数据文件不存在', 'data': {}}, status=400)
        try:
            df = pd.read_parquet(parquet_path)
        except Exception as e:
            return JsonResponse({'code': 500, 'message': f'Parquet文件读取失败: {str(e)}', 'data': {}})
        # 构造jsonl内容
        lines = []
        for _, row in df.iterrows():
            # prompt作为system内容
            prompt = row.get('prompt', '')
            # 组装user内容
            user_content = []
            for k, v in row.items():
                if k not in ['is_matched', 'prompt', 'create_time']:
                    user_content.append(f"{k}:{v}")
            user_content_str = ','.join(user_content)
            messages = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_content_str},
            ]
            assistant_content = str(row.get('is_matched', ''))
            messages.append({"role": "assistant", "content": assistant_content})
            lines.append(json.dumps({"messages": messages}, ensure_ascii=False))
        # 写入data.json文件
        with open(json_path, 'w', encoding='utf-8') as f:
            for line in lines:
                f.write(line + '\n')
        return JsonResponse({'code': 200, 'message': '导出成功', 'data': {'json_path': json_path}})
    return JsonResponse({'code': 400, 'message': '请求方法错误', 'data': {}}, status=400)

@csrf_exempt
def upload_dataset(request):
    """
    接收用户上传的json或jsonl文件并保存到指定目录，文件名为<dataset_id>.jsonl
    """
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        dataset_id = request.POST.get('dataset_id')
        if not user_id or not dataset_id:
            return JsonResponse({'code': 400, 'message': '缺少user_id或dataset_id参数', 'data': {}})
        # 校验用户是否存在
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return JsonResponse({'code': 400, 'message': '用户不存在', 'data': {}})
        # 校验数据集是否存在且属于该用户
        try:
            dataset = Dataset.objects.get(id=dataset_id, user=user)
        except Dataset.DoesNotExist:
            return JsonResponse({'code': 400, 'message': '数据集不存在或不属于该用户', 'data': {}})
        if 'file' not in request.FILES:
            return JsonResponse({'code': 400, 'message': '未检测到上传文件', 'data': {}})
        upload_file = request.FILES['file']
        # 检查文件类型
        if not (upload_file.name.endswith('.json') or upload_file.name.endswith('.jsonl')):
            return JsonResponse({'code': 400, 'message': '只支持json或jsonl文件上传', 'data': {}})
        # 构造保存路径，文件名为<dataset_id>.jsonl
        save_dir = os.path.join(LOCAL_DATA_DIR, str(user_id), str(dataset_id), 'datasets')
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, f"data.json")
        # 保存文件
        with open(save_path, 'wb') as f:
            for chunk in upload_file.chunks():
                f.write(chunk)
        # 上传成功后，设置is_upload为True
        dataset.update_is_upload(True)
        return JsonResponse({'code': 200, 'message': '文件上传成功', 'data': {'file_path': save_path}})
    return JsonResponse({'code': 400, 'message': '请求方法错误', 'data': {}})

@csrf_exempt
def json_to_parquet(request):
    """
    将指定数据集目录下的data.json内容转换为parquet文件，parquet文件名为<dataset_id>.parquet。
    每行存system、user、assistant三列，分别为对应role的content。
    需要参数：user_id, dataset_id
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            return JsonResponse({'code': 400, 'message': '请求体不是有效的JSON', 'data': {}}, status=400)
        user_id = data.get('user_id')
        dataset_id = data.get('dataset_id')
        if not user_id or not dataset_id:
            return JsonResponse({'code': 400, 'message': '缺少user_id或dataset_id参数', 'data': {}})
        # 构造路径
        save_dir = os.path.join(LOCAL_DATA_DIR, str(user_id), str(dataset_id), 'datasets')
        json_path = os.path.join(save_dir, 'data.json')
        if not os.path.exists(json_path):
            return JsonResponse({'code': 400, 'message': 'data.json文件不存在', 'data': {}})
        rows = []
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                for line in f:
                    obj = json.loads(line)
                    messages = obj.get('messages', [])
                    system = user = assistant = ""
                    for m in messages:
                        if m.get('role') == 'system':
                            system = m.get('content', '')
                        elif m.get('role') == 'user':
                            user = m.get('content', '')
                        elif m.get('role') == 'assistant':
                            assistant = m.get('content', '')
                    rows.append({'system': system, 'user': user, 'assistant': assistant})
        except Exception as e:
            return JsonResponse({'code': 500, 'message': f'解析data.json失败: {str(e)}', 'data': {}})
        if not rows:
            return JsonResponse({'code': 400, 'message': 'data.json无有效数据', 'data': {}})
        # 转为DataFrame并写入parquet
        df = pd.DataFrame(rows)
        parquet_path = os.path.join(save_dir, f"{dataset_id}.parquet")
        try:
            df.to_parquet(parquet_path)
        except Exception as e:
            return JsonResponse({'code': 500, 'message': f'写入parquet失败: {str(e)}', 'data': {}})
        return JsonResponse({'code': 200, 'message': '转换成功', 'data': {'parquet_path': parquet_path}})
    return JsonResponse({'code': 400, 'message': '请求方法错误', 'data': {}})









@csrf_exempt  # 仅在开发时使用，生产环境中请使用更安全的方式
def create_project(request):
    project_name = request.POST.get('name')
    username = request.POST.get('user')
    task_type = request.POST.get('taskType')
    description = request.POST.get('description')
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'message': '用户不存在'})
    project = Project(name=project_name, user=user.username, task_type=task_type, description=description)
    project.save()
    return JsonResponse({'success': True, 'message': '项目已创建'})

def get_user_projects(request):
    username = request.GET.get('user')
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return JsonResponse({'projects': []})
    projects = Project.objects.filter(user=user.username)
    return JsonResponse({'projects': list(projects.values())})

@csrf_exempt  # 仅在开发时使用，生产环境中请使用更安全的方式
def delete_project(request):
    username = request.GET.get('user')
    project_name = request.GET.get('projectName')
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return JsonResponse({'success': False})
    project_deleted, _ = Project.objects.filter(user=user.username, name=project_name).delete()
    if project_deleted > 0:
        return JsonResponse({'success': True})
    else:
        return JsonResponse({'success': False})
    
@csrf_exempt  # 仅在开发时使用，生产环境中请使用更安全的方式
def delete_dataset(request):
    username = request.GET.get('user')
    dataset_name = request.GET.get('datasetName')
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return JsonResponse({'success': False})
    project_deleted, _ = Dataset.objects.filter(user=user, name=dataset_name).delete()

    delete_object_name = user.username + '/' + dataset_name

    ## 删除minio中的所有数据
    future1 = executor.submit(delete_from_minio, delete_object_name)

    ## 删除临时文件夹的所有数据
    curr_temp_dir = os.path.join(os.path.join(TEMP_ROOT_DIR, user.username), dataset_name)

    future2 = executor.submit(delete_temp_dir, curr_temp_dir)
    if project_deleted > 0:
        return JsonResponse({'success': True})
    else:
        return JsonResponse({'success': False})
    
@csrf_exempt  # 仅在开发时使用，生产环境中请使用更安全的方式
def get_project(request):
    username = request.GET.get('user')
    project_name = request.GET.get('projectName')
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'project': None})
    project = Project.objects.filter(user=user.username, name=project_name)
    if project.exists():
        return JsonResponse({'success': True, 'project': list(project.values())[0]})
    else:
        return JsonResponse({'success': False, 'project': None})

@csrf_exempt  # 仅在开发时使用，生产环境中请使用更安全的方式
def get_dataset(request):
    username = request.GET.get('user')
    dataset_name = request.GET.get('datasetName')
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'dataset': None})
    dataset = Dataset.objects.filter(user=user, name=dataset_name)
    if dataset.exists():
        return JsonResponse({'success': True, 'dataset': list(dataset.values())[0]})
    else:
        return JsonResponse({'success': False, 'dataset': None})

@csrf_exempt  # 仅在开发时使用，生产环境中请使用更安全的方式
def get_minio_links(request):
    username = request.GET.get('user')
    dataset_name = request.GET.get('datasetName')
    next_image = request.GET.get('nextImage')
    page_size = request.GET.get('pageSize')
    if next_image != '':
        next_image = os.path.relpath(next_image, f"http://{LOCAL_IP}:9000/{BUCKET_NAME}")
    task_type = request.GET.get('taskType')
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'links': []})
    ## 生成object_name路径，用于访问minio
    object_name = user.username + '/' + dataset_name + '/' + task_type + '/images' 
    http_links = get_dataset_link(object_name, next_image, page_size)
    return JsonResponse({'success': True, 'links': http_links})

@csrf_exempt 
def get_dataset_is_upload(request):
    if request.method == 'GET':
        username = request.GET.get('user')
        dataset_name = request.GET.get('datasetName')

        # 检查用户和数据集名称是否提供
        if not username or not dataset_name:
            return JsonResponse({'success': False, 'message': '用户或数据集名称未提供'})

        # 查询数据库获取数据集
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'message': '用户未找到'})
        dataset = Dataset.objects.filter(user=user, name=dataset_name).first()

        if dataset is not None:
            return JsonResponse({'success': True, 'is_upload': dataset.is_upload})
        else:
            return JsonResponse({'success': False, 'message': '数据集未找到'})

    return JsonResponse({'success': False, 'message': '请求方法错误'})

@csrf_exempt
def upload(request):
    if request.method == 'POST':
        # 检查文件是否存在
        if 'file' in request.FILES:
            dataset_name = request.POST.get('name')
            username = request.POST.get('user')
            task_type = request.POST.get('taskType')
            size = request.POST.get('size')
            description = request.POST.get('description')
            uploaded_file = request.FILES.get('file')

            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                return JsonResponse({'success': False, 'message': f'用户 {username} 不存在'})

            ## 检查数据库判断该数据集名称是否重复
            if Dataset.objects.filter(name=dataset_name, user=user).exists():
                return JsonResponse({'success': False, 'message': f'数据集 {dataset_name} 名称已存在'})

            ## 创建解压数据集的临时目录
            temp_dir = TEMP_ROOT_DIR + '/' + user.username + '/' + dataset_name
            
            # 如果目录已存在且不为空，则删除该目录
            if os.path.exists(temp_dir) and os.listdir(temp_dir):
                shutil.rmtree(temp_dir)

            os.makedirs(temp_dir, exist_ok=True)

            file_path = os.path.join(temp_dir, uploaded_file.name)
            with open(file_path, 'wb') as f:
                for chunk in uploaded_file.chunks():
                    f.write(chunk)
            
            print(f"数据集 {dataset_name} 保存到临时目录成功")

            ## 开始解压数据集
            try:
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                print(f"数据集 {dataset_name} 解压到临时目录成功")

                # 重命名解压后的文件夹
                extracted_folder_name = os.path.splitext(uploaded_file.name)[0]
                extracted_folder_path = os.path.join(temp_dir, extracted_folder_name)
                new_folder_path = os.path.join(temp_dir, 'Detection')
                os.rename(extracted_folder_path, new_folder_path)
            except Exception as e:
                print(f"数据集{dataset_name}解压失败", e)
                return JsonResponse({'success': False, 'message': f'数据集 {dataset_name} 解压失败'})
            
            # 根据 task_type 设置 data_path
            if task_type == "Detect":
                data_path = os.path.join(temp_dir, 'Detection')
            elif task_type == "Classify":
                data_path = os.path.join(temp_dir, 'Classification')
            else:
                data_path = os.path.join(temp_dir, 'Detection')  # 默认值

            # 根据 task_type 检查相应数据集的文件结构是否正确
            flag = False
            if task_type == "Detect":
                flag, message = check_directory_structure_detect(data_path)
            elif task_type == "Classify":
                flag, message = check_directory_structure_detect(data_path)
            else:
                flag, message = check_directory_structure_detect(data_path)

            if flag:
                yaml_files = glob.glob(os.path.join(data_path, "*.yaml"))
                yaml_path = yaml_files[0]
                categories = get_categories(yaml_path)
                print(f"数据集 {dataset_name} 结构检查成功")
            else:
                print(f"数据集 {dataset_name} 结构检查失败")

                ## 删除临时文件夹的所有数据
                curr_temp_dir = os.path.join(os.path.join(TEMP_ROOT_DIR, user.username), dataset_name)
                delete_temp_dir(curr_temp_dir)
                return JsonResponse({'success': False, 'message': f'数据集 {dataset_name} 结构不符合要求: {message}'})

            # 创建 Dataset 对象
            dataset = Dataset(
                name=dataset_name,
                user=user,  # 这里需要替换为实际的用户信息
                task_type=task_type,
                size=size,
                # number=0,
                description=description,
                categories = categories
            )

            future = executor.submit(upload_to_minio, data_path, dataset)

            dataset.save()

            if uploaded_file:
                return JsonResponse({'success': True, 'message': '文件已成功上传'})
            else:
                return JsonResponse({'success': False, 'message': '没有文件上传'})
    
    return JsonResponse({'success': False, 'message': '请求错误'})

@csrf_exempt
def get_user_datasets(request):
    username = request.GET.get('user')
    if not username:
        return JsonResponse({'code': 400, 'message': '缺少user参数', 'data': {}})
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return JsonResponse({'code': 400, 'message': '用户不存在', 'data': {}})
    datasets = Dataset.objects.filter(user=user)
    return JsonResponse({'datasets': list(datasets.values())})







