# 使用 Python 3.13.3 作为基础镜像
FROM python:3.13.3-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
# 防止 Python 生成 .pyc 文件
ENV PYTHONDONTWRITEBYTECODE=1

# 防止 Python 缓存输出
ENV PYTHONUNBUFFERED=1

# 设置时区为 UTC
ENV TZ=UTC

# 允许不带认证的API访问
ENV FLOWER_UNAUTHENTICATED_API=1

# 创建证书目录
RUN mkdir -p /usr/local/share/ca-certificates/extra

# 复制 DigiCert 根证书到容器
COPY ../common/cert/EncryptionEverywhereDVTLSCA-G1.crt.pem /usr/local/share/ca-certificates/extra/EncryptionEverywhereDVTLSCA-G1.crt
COPY ../common/cert/EncryptionEverywhereDVTLSCA-G2.crt.pem /usr/local/share/ca-certificates/extra/EncryptionEverywhereDVTLSCA-G2.crt

# 确保文件权限正确
RUN chmod 644 /usr/local/share/ca-certificates/extra/EncryptionEverywhereDVTLSCA-G1.crt
RUN chmod 644 /usr/local/share/ca-certificates/extra/EncryptionEverywhereDVTLSCA-G2.crt

# 更新证书
RUN update-ca-certificates

# 为 Python 设置证书环境变量
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt

# 安装系统依赖
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libffi-dev \
    default-libmysqlclient-dev \
    curl \
    make \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && update-alternatives --install /usr/bin/cc cc /usr/bin/gcc 100 \
    && update-alternatives --install /usr/bin/c++ c++ /usr/bin/g++ 100

# 更新证书
RUN update-ca-certificates

# 安装 Poetry
RUN pip install --no-cache-dir poetry

# 复制整个项目到容器中
COPY . /app/

# 配置 Poetry - 不创建虚拟环境
RUN poetry config virtualenvs.create false

# 安装项目依赖
RUN poetry install --all-groups --no-interaction --no-ansi

# 添加执行权限
RUN chmod +x /app/gateway/entrypoint.sh

# 暴露应用端口
# 注意，修改端口的时候，要修改服务器workspace中的启动命令里的docker设置
EXPOSE 8080

# 设置入口脚本
ENTRYPOINT ["/app/gateway/entrypoint.sh"]