FROM nvidia/cuda:12.3.1-devel-ubuntu22.04
WORKDIR /app
COPY ./server/requirements.txt /app
RUN apt-get update && apt-get install -y python3 python3-pip curl \ 
    && pip install -r requirements.txt \ 
    && useradd -u 1000 app-user \
    && rm -rf /var/lib/apt/lists/*

RUN CMAKE_ARGS="-DLLAMA_CUBLAS=on" FORCE_CMAKE=1 pip install llama-cpp-python[server]==0.2.23

RUN curl https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF/resolve/main/llama-2-7b-chat.Q5_K_M.gguf -o /app/llama-2-7b-chat.Q5_K_M.gguf
COPY ./server/ .
RUN chown -R app-user:app-user /app/
USER app-user
CMD ["celery", "--app", "workers.gpu.celery", "worker", "--loglevel=info", "-c", "1", "-Q", "gpu"]