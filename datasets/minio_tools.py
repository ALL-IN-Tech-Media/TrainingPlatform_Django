from minio import Minio
from minio.error import S3Error
import os
from .config import TEMP_ROOT_DIR, LOCAL_IP, BUCKET_NAME, MINIO_ACCESS_KEY, MINIO_SECRET_KEY
import sys
import mimetypes 
from .models import Dataset

# MinIO 客户端配置
minio_client = Minio(
    f"{LOCAL_IP}:9000",  # 替换为你的 MinIO 主机和端口
    access_key=MINIO_ACCESS_KEY,  # 替换为你的访问密钥
    secret_key=MINIO_SECRET_KEY,  # 替换为你的秘密密钥
    secure=False  # 如果使用 HTTPS，请设置为 True
)

def upload_to_minio(local_path, dataset):
    """上传文件夹到 MinIO并更新数据集上传状态"""
    bucket_name = "ai-data"  # 替换为你的桶名称

    # 检查桶是否存在
    try:
        if not minio_client.bucket_exists(bucket_name):
            minio_client.make_bucket(bucket_name)
            print("bucket创建成功")
            # 设置桶为公开
            import json
            policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"AWS": ["*"]},
                        "Action": ["s3:GetObject"],
                        "Resource": [f"arn:aws:s3:::{bucket_name}/*"]
                    }
                ]
            }
            minio_client.set_bucket_policy(bucket_name, json.dumps(policy))
    except S3Error as e:
        print(f"桶检查或创建失败: {e}")
        return
    print(f"开始上传 {local_path}")

    upload_success = True  # 用于跟踪上传是否成功

    ## 开始上传文件
    for root, dirs, files in os.walk(local_path):
        for file in files:
            file_path = os.path.join(root, file)
            object_name = os.path.relpath(file_path, TEMP_ROOT_DIR).replace("\\", "/")  # 替换反斜杠为斜杠以兼容 MinIO
            try:
                # 获取文件类型
                content_type, _ = mimetypes.guess_type(file_path)
                minio_client.fput_object(bucket_name, object_name, file_path, content_type=content_type)
                http_link = f"http://{LOCAL_IP}:9000/{BUCKET_NAME}/{object_name}"
            except S3Error as e:
                print(f"上传失败: {object_name}, 错误: {e}")
                upload_success = False  # 如果有任何文件上传失败，标记为失败
    
    if upload_success:
        # 如果所有文件上传成功，更新数据集的上传状态
        dataset.update_is_upload(True)
    print(f"{local_path}上传成功")

def delete_from_minio(object_name):
    num = 0
    while True:
        objects = minio_client.list_objects("ai-data", prefix=object_name, recursive=True)
        object_list = list(objects)  # 将生成器转换为列表以便多次使用
        if not object_list:  # 如果没有更多对象，退出循环
            break
        for obj in object_list:
            num += 1
            minio_client.remove_object("ai-data", obj.object_name)
            # print(f"成功删除: {obj.object_name}")
    print(f"{object_name}删除成功，删除总量为{num}")

def get_dataset_link(object_name, next_image, page_size=60):
    """生成 MinIO 对象的 HTTP 访问链接，支持分页"""

    # 假设每个页面有固定数量的对象，例如每页 10 个对象

    # 生成完整的对象路径
    full_object_name = f"{object_name}/"  # 以文件夹路径为基础

    # 列出指定文件夹下的所有对象
    http_links = []
    try:
        # 使用生成器逐步获取对象，不递归到子文件夹
        objects = minio_client.list_objects(BUCKET_NAME, prefix=full_object_name, recursive=True ,start_after=next_image)
        # objects = minio_client.list_objects(BUCKET_NAME, prefix=full_object_name, recursive=True ,start_after=next_image, max_keys=page_size)
        
        # 逐步处理对象以避免内存问题
        num = 0
        for obj in objects:
            num += 1
            http_link = f"http://{LOCAL_IP}:9000/{BUCKET_NAME}/{obj.object_name}"
            http_links.append(http_link)
    except S3Error as e:
        print(f"列出文件失败: {e}")
    return http_links

if __name__ == "__main__":
    upload_to_minio('/tmp/AIData_temp_dir/lzz/000/APEX_images')
    # get_minio_link("lzz/00000000/APEX_images/images/train", None)
    # get_dataset_link("lzz/0000/Detection/images", '')
    # delete_from_minio("lzz/9999")

