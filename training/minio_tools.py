import os
from minio import Minio
from minio.error import S3Error

minio_client = Minio(
    "192.168.0.126:9000",
    access_key="liuchang630.",
    secret_key="liuchang630.",
    secure=False
)

BUCKET_NAME = "ai-data"

# def download_minio_file(bucket_name, file_name):
#     minio_client = MinioClient()
#     minio_client.download_file(bucket_name, file_name)

def download_minio_folder(bucket_name, folder_name, local_path):
    # 列出文件夹中的所有对象
    objects = minio_client.list_objects(bucket_name, prefix=folder_name, recursive=True)
    print(list(objects))
    
    for obj in objects:
        print(obj)
        # 构建本地文件路径
        local_file_path = os.path.join(local_path, obj.object_name[len(folder_name):].lstrip('/'))
        
        # 确保本地目录存在
        os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
        
        # 下载文件
        minio_client.download_file(bucket_name, obj.object_name, local_file_path)

if __name__ == "__main__":
    download_minio_folder(BUCKET_NAME, "lzz/APEX测试数据集/Detection/images/", "/Users/liuzizhen/Projects/AIData/lzz/APEX测试数据集")
