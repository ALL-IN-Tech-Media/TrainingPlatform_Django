import os
import shutil
import yaml
import json

def is_image_file(filename):
    
    valid_image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff'}
    _, ext = os.path.splitext(filename)
    return ext.lower() in valid_image_extensions

# 检查文件扩展名是否为XML格式
def is_xml_file(filename):
    
    _, ext = os.path.splitext(filename)
    return ext.lower() == '.xml' or ext.lower() == '.txt'

def check_single_yaml_file(folder_path):
    # 列出目录中的所有文件
    files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
    
    # 过滤出后缀为.yaml的文件
    yaml_files = [f for f in files if f.lower().endswith('.yaml')]
    
    # 检查是否只有一个.yaml文件
    return len(yaml_files) == 1, yaml_files

# 遍历文件夹及其子文件夹，删除所有.DS_Store文件
def remove_ds_store_files(folder_path):
    
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file == '.DS_Store':
                os.remove(os.path.join(root, file))

def check_directory_structure_detect(folder_path):
    results = {}

    # 检查是否存在且只有一个xxx.yaml文件
    # yaml_file_exists: True 或者 False
    # yaml_files: 文件名列表   yaml_files=['xxx.yaml']
    yaml_file_exists, yaml_files = check_single_yaml_file(folder_path)
    if not yaml_file_exists:
        return False, "不存在yaml文件"

    results['yaml_file'] = {'exists': yaml_file_exists, 'files': yaml_files}

    # 检查labels和images文件夹下的train和val文件夹
    labels_folder = os.path.join(folder_path, 'labels')
    images_folder = os.path.join(folder_path, 'images')
    
    labels_train_exists = os.path.isdir(os.path.join(labels_folder, 'train'))
    labels_val_exists = os.path.isdir(os.path.join(labels_folder, 'val'))
    images_train_exists = os.path.isdir(os.path.join(images_folder, 'train'))
    images_val_exists = os.path.isdir(os.path.join(images_folder, 'val'))

    if not labels_train_exists or not labels_val_exists or not images_train_exists or not images_val_exists:
        return False, "labels和images文件夹下的train和val文件夹不存在"
    
    results['labels_train_folder'] = labels_train_exists
    results['labels_val_folder'] = labels_val_exists
    results['images_train_folder'] = images_train_exists
    results['images_val_folder'] = images_val_exists

    # 删除可能存在的.DS_Store文件
    remove_ds_store_files(folder_path)

    # 检查images/train和images/val文件夹下是否全部都是图片
    train_images_path = os.path.join(images_folder, 'train')
    val_images_path = os.path.join(images_folder, 'val')

    all_images_train = all(is_image_file(f) for f in os.listdir(train_images_path))
    all_images_val = all(is_image_file(f) for f in os.listdir(val_images_path))
    results['all_images_train'] = all_images_train
    results['all_images_val'] = all_images_val

    # 检查labels/train和labels/val文件夹下是否全部都是xml文件
    all_labels_train = all(is_xml_file(f) for f in os.listdir(os.path.join(labels_folder, 'train')))
    all_labels_val = all(is_xml_file(f) for f in os.listdir(os.path.join(labels_folder, 'val')))
    results['all_labels_train'] = all_labels_train
    results['all_labels_val'] = all_labels_val

    # 检查结果
    all_checks_passed = all(results.values())
    return all_checks_passed, f"results: {results}"

def delete_temp_dir(dir_path):
    if os.path.exists(dir_path):
        shutil.rmtree(dir_path)
        return True
    return False

def get_categories(yaml_path):
    result = []
    with open(yaml_path, 'r', encoding='utf-8') as file:
        data = yaml.safe_load(file)
        names = data['names']
    if names is not None:
        result = list(names.values())
        return result
    else: return []

# 从本地检查json文件是否是chat格式
def validate_chat_format(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                obj = json.loads(line)
                if 'messages' not in obj or not isinstance(obj['messages'], list):
                    return False, '每行必须包含messages字段且为list'
                for msg in obj['messages']:
                    if 'role' not in msg or 'content' not in msg:
                        return False, 'messages中的每个元素必须有role和content'
            except Exception as e:
                return False, f'JSON解析失败: {e}'
    return True, ''

# 从本地检查json文件是否是instruct格式
def validate_instruct_format(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, list):
            return False, 'Instruct格式必须是一个数组'
        for item in data:
            if not all(k in item for k in ['instruction', 'input', 'output']):
                return False, '每个元素必须有instruction、input、output字段'
    except Exception as e:
        return False, f'JSON解析失败: {e}'
    return True, ''

# 在线检查json文件是否是chat格式
def validate_chat_format_fileobj(fileobj):
    fileobj.seek(0)
    for line in fileobj:
        try:
            obj = json.loads(line)
            if 'messages' not in obj or not isinstance(obj['messages'], list):
                return False, '每行必须包含messages字段且为list'
            for msg in obj['messages']:
                if 'role' not in msg or 'content' not in msg:
                    return False, 'messages中的每个元素必须有role和content'
        except Exception as e:
            return False, f'JSON解析失败: {e}'
    fileobj.seek(0)
    return True, ''

# 在线检查json文件是否是instruct格式
def validate_instruct_format_fileobj(fileobj):
    """
    校验上传文件对象是否为Instruct格式（JSON数组，每个元素有instruction、input、output字段）
    :param fileobj: Django上传的文件对象
    :return: (bool, str) 校验结果和错误信息
    """
    try:
        fileobj.seek(0)
        data = json.load(fileobj)
        if not isinstance(data, list):
            return False, 'Instruct格式必须是一个数组'
        for item in data:
            if not all(k in item for k in ['instruction', 'input', 'output']):
                return False, '每个元素必须有instruction、input、output字段'
    except Exception as e:
        return False, f'JSON解析失败: {e}'
    finally:
        fileobj.seek(0)  # 复位，便于后续保存
    return True, ''


# 从本地检查json文件是否是scored_pair格式
def validate_scored_pair_format(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                obj = json.loads(line)
                if 'sentence1' not in obj or 'sentence2' not in obj or 'score' not in obj:
                    return False, '每行必须包含sentence1、sentence2和score字段'
            except Exception as e:
                return False, f'JSON解析失败: {e}'
    return True, ''

# 在线检查json文件是否是scored_pair格式
def validate_scored_pair_format_fileobj(fileobj):
    fileobj.seek(0)
    for line in fileobj:
        try:
            obj = json.loads(line)
            if 'sentence1' not in obj or 'sentence2' not in obj or 'score' not in obj:
                return False, '每行必须包含sentence1、sentence2和score字段'
        except Exception as e:
            return False, f'JSON解析失败: {e}'
    fileobj.seek(0)
    return True, ''

# 从本地检查json文件是否是contrastive_triplet格式
def validate_contrastive_triplet_format(file_path):
    return False, '暂时不支持该数据格式的训练'

# 在线检查json文件是否是contrastive_triplet格式
def validate_contrastive_triplet_format_fileobj(fileobj):
    return False, '暂时不支持该数据格式的训练'

# 从本地检查json文件是否是labeled_sentence格式
def validate_labeled_sentence_format(file_path):
    return False, '暂时不支持该数据格式的训练'

# 在线检查json文件是否是labeled_sentence格式
def validate_labeled_sentence_format_fileobj(fileobj):
    return False, '暂时不支持该数据格式的训练'

# 使用示例
if __name__ == "__main__":
    yaml_path = "/Users/liuzizhen/AIData_temp_dir/lzz/APEX测试数据集/Detection/coco8.yaml"
    name = get_categories(yaml_path)
    print(name)
    
