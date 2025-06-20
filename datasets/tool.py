import os
import shutil
import yaml

def is_image_file(filename):
    # 检查文件扩展名是否为常见的图片格式
    valid_image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff'}
    _, ext = os.path.splitext(filename)
    return ext.lower() in valid_image_extensions

def is_xml_file(filename):
    # 检查文件扩展名是否为XML格式
    _, ext = os.path.splitext(filename)
    return ext.lower() == '.xml' or ext.lower() == '.txt'

def check_single_yaml_file(folder_path):
    # 列出目录中的所有文件
    files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
    
    # 过滤出后缀为.yaml的文件
    yaml_files = [f for f in files if f.lower().endswith('.yaml')]
    
    # 检查是否只有一个.yaml文件
    return len(yaml_files) == 1, yaml_files

def remove_ds_store_files(folder_path):
    # 遍历文件夹及其子文件夹，删除所有.DS_Store文件
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

# 使用示例
if __name__ == "__main__":
    yaml_path = "/Users/liuzizhen/AIData_temp_dir/lzz/APEX测试数据集/Detection/coco8.yaml"
    name = get_categories(yaml_path)
    print(name)
    
