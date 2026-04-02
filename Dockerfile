FROM nvidia/cuda:12.8.0-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV HF_HOME=/runpod-volume/cache/huggingface
ENV HF_HUB_CACHE=/runpod-volume/cache/huggingface/hub
ENV PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True,max_split_size_mb:128

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    build-essential \
    git \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --upgrade pip setuptools wheel

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    --extra-index-url https://download.pytorch.org/whl/cu128

COPY . .

CMD ["python3", "handler.py"]
