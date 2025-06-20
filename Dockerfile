# 使用 Ubuntu 20.04 作为基础镜像
FROM ubuntu:20.04

# 设置环境变量，避免一些交互提示
ENV DEBIAN_FRONTEND=noninteractive

# 更换为阿里云源
RUN sed -i 's|http://archive.ubuntu.com/ubuntu/|http://mirrors.aliyun.com/ubuntu/|g' /etc/apt/sources.list && \
    sed -i 's|http://security.ubuntu.com/ubuntu/|http://mirrors.aliyun.com/ubuntu/|g' /etc/apt/sources.list

# 更新 apt-get 并安装必要的依赖
RUN apt-get update && \
    apt-get install -y wget curl bzip2 ca-certificates git vim && \
    apt-get clean

# 将 Anaconda 安装包复制到容器中
RUN wget https://repo.anaconda.com/archive/Anaconda3-2024.10-1-Linux-x86_64.sh -O /tmp/Anaconda3.sh

# 创建 /home/lzz/aiflask 目录
RUN mkdir -p /home/lzz/AIData_temp_dir
RUN mkdir -p /home/lzz/aidjango

# 复制本地的文件或文件夹到容器的指定路径
COPY . /home/lzz/aidjango/

# 安装 Anaconda
RUN bash /tmp/Anaconda3.sh -b -p /opt/anaconda3

# 配置环境变量，添加 Anaconda 到 PATH 中
ENV PATH=/opt/anaconda3/bin:$PATH
ENV PYTHONPATH=/home/lzz/aidjango

# 初始化 Conda 并创建环境
RUN /opt/anaconda3/bin/conda init bash

# 创建 Conda 环境并安装 Python 3.11
RUN conda create -n aidjango python=3.11 -y

# 激活环境并将其设为默认环境
RUN echo "conda activate aidjango" >> ~/.bashrc

# 使用 conda run 安装 PyTorch（避免手动激活）
RUN /opt/anaconda3/bin/conda run -n aidjango pip3 install Django==4.2.17 -i https://pypi.tuna.tsinghua.edu.cn/simple
RUN /opt/anaconda3/bin/conda run -n aidjango pip3 install pymysql==1.1.1 -i https://pypi.tuna.tsinghua.edu.cn/simple
RUN /opt/anaconda3/bin/conda run -n aidjango pip3 install djangorestframework==3.15.2 -i https://pypi.tuna.tsinghua.edu.cn/simple
RUN /opt/anaconda3/bin/conda run -n aidjango pip3 install django-cors-headers==4.6.0 -i https://pypi.tuna.tsinghua.edu.cn/simple
RUN /opt/anaconda3/bin/conda run -n aidjango pip3 install requests==2.32.3 -i https://pypi.tuna.tsinghua.edu.cn/simple
RUN /opt/anaconda3/bin/conda run -n aidjango pip3 install pyyaml==6.0.2 -i https://pypi.tuna.tsinghua.edu.cn/simple
RUN /opt/anaconda3/bin/conda run -n aidjango pip3 install minio==7.2.13 -i https://pypi.tuna.tsinghua.edu.cn/simple
RUN /opt/anaconda3/bin/conda run -n aidjango pip3 install gitpython -i https://pypi.tuna.tsinghua.edu.cn/simple
RUN /opt/anaconda3/bin/conda run -n aidjango pip3 install gunicorn -i https://pypi.tuna.tsinghua.edu.cn/simple

# 删除安装包
RUN rm /tmp/Anaconda3.sh

RUN rm -rf /home/lzz/aidjango/DockerENV

# 设置默认启动命令
CMD ["bash"]