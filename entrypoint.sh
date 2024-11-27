#!/bin/bash

/usr/sbin/nginx

export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu/

PY=/e/conda_envs/ragflow/bin/python
# PY=/home/dell/anaconda3/bin/python
export PYTHONPATH=/e/ragflow/ragflow-saic/ragflow-main
# 可选：添加Hugging Face镜像
export HF_ENDPOINT=https://hf-mirror.com

if [[ -z "$WS" || $WS -lt 1 ]]; then
  WS=1
fi

function task_exe(){
    while [ 1 -eq 1 ];do
      $PY rag/svr/task_executor.py ;
    done
}

for ((i=0;i<WS;i++))
do
  task_exe  &
done

while [ 1 -eq 1 ];do
    $PY api/ragflow_server.py
done

wait;
