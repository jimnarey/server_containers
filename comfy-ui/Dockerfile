FROM base-ubuntu-caddy-24:latest

ARG COMFYUI_VERSION=v0.29.2
ARG TORCH_VERSION=2.11.0
ARG TORCHVISION_VERSION=0.26.0
ARG TORCHAUDIO_VERSION=2.11.0
ARG PYTORCH_INDEX_URL=https://download.pytorch.org/whl/cu130

ENV VIRTUAL_ENV=/opt/comfyui-venv
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"
ENV PYTHONUNBUFFERED=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV HF_HUB_DISABLE_TELEMETRY=1
ENV DO_NOT_TRACK=1

RUN apt-get update -y && \
    apt-get install -y --no-install-recommends \
        ffmpeg \
        git \
        libgl1 \
        libglib2.0-0 \
        python3 \
        python3-pip \
        python3-venv && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN git clone --branch "${COMFYUI_VERSION}" --depth 1 \
        https://github.com/Comfy-Org/ComfyUI.git /opt/ComfyUI && \
    python3 -m venv "${VIRTUAL_ENV}" && \
    pip install --upgrade pip setuptools wheel && \
    pip install \
        "torch==${TORCH_VERSION}" \
        "torchvision==${TORCHVISION_VERSION}" \
        "torchaudio==${TORCHAUDIO_VERSION}" \
        --index-url "${PYTORCH_INDEX_URL}" && \
    pip install -r /opt/ComfyUI/requirements.txt && \
    pip install -r /opt/ComfyUI/manager_requirements.txt && \
    pip check && \
    mkdir -p \
        /models \
        /data/input \
        /data/output \
        /data/temp \
        /data/user \
        /opt/ComfyUI/custom_nodes && \
    chown -R runuser:runuser \
        "${VIRTUAL_ENV}" \
        /data \
        /opt/ComfyUI/custom_nodes

COPY --chown=runuser:runuser extra_model_paths.yaml /opt/ComfyUI/extra_model_paths.yaml
COPY --chown=runuser:runuser start-comfyui.sh /usr/local/bin/start-comfyui
RUN chmod 755 /usr/local/bin/start-comfyui

EXPOSE 8081

RUN printf '%s\n' \
    '' \
    '[program:comfyui]' \
    'priority=10' \
    'directory=/opt/ComfyUI' \
    'command=/usr/local/bin/start-comfyui' \
    'autorestart=true' \
    'startretries=10' \
    'stopasgroup=true' \
    'killasgroup=true' \
    'stdout_logfile=/dev/fd/1' \
    'stdout_logfile_maxbytes=0' \
    'redirect_stderr=true' \
    >> /etc/supervisord.conf
