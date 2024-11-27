From python:3.11

USER root

# 工作目录
WORKDIR /ragflow

# 安装Node.js Nginx和npm
RUN apt-get update && \
    apt-get install -y nodejs nginx npm && \
    npm install -g npm@latest

ADD ./web ./web    
ADD ./api ./api
ADD ./conf ./conf
ADD ./deepdoc ./deepdoc
ADD ./rag ./rag
ADD ./graph ./graph
ADD docker/entrypoint.sh ./entrypoint.sh
ADD docker/.env ./
ADD ./requirements_test.txt ./requirements.txt
COPY ./nltk_data /usr/local/nltk_data


# 安装Python依赖
RUN pip install --upgrade pip -i https://mirrors.aliyun.com/pypi/simple && \
    pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple


# 构建前端
RUN cd ./web && npm install --force && npm run build

# 设置环境变量
ENV PYTHONPATH=/ragflow/
ENV HF_ENDPOINT=https://hf-mirror.com


# 暴露端口
EXPOSE 80
EXPOSE 443

# 容器启动时运行 nginx
CMD ["nginx", "-g", "daemon off;"]

# 赋予入口点脚本执行权限
RUN chmod +x ./entrypoint.sh

# 设置入口点
ENTRYPOINT ["./entrypoint.sh"]