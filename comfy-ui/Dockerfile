FROM base-ubuntu-caddy-24:latest

ENV PYENV_ROOT=/opt/pyenv
ENV PATH=$PYENV_ROOT/shims:$PYENV_ROOT/bin:$PATH

RUN apt-get update -y && \
	apt-get install -y --no-install-recommends \
		build-essential curl git ca-certificates libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev libffi-dev liblzma-dev make wget && \
	apt-get clean && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/pyenv/pyenv.git $PYENV_ROOT && \
	$PYENV_ROOT/bin/pyenv install -s 3.11.14 && \
	$PYENV_ROOT/bin/pyenv global 3.11.14 && \
	$PYENV_ROOT/bin/pyenv rehash

RUN pip install --upgrade pip setuptools wheel && \
	pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

RUN git clone https://github.com/comfyanonymous/ComfyUI.git /home/runuser/ComfyUI && \
	chown -R runuser:runuser /home/runuser/ComfyUI

COPY extra_model_paths.yaml /home/runuser/ComfyUI/extra_model_paths.yaml
RUN chown runuser:runuser /home/runuser/ComfyUI/extra_model_paths.yaml || true

RUN pip install -r /home/runuser/ComfyUI/requirements.txt || true

EXPOSE 8081

RUN echo \
'\n[program:comfyui]\n\
priority=1\n\
environment=DISPLAY=:0,\n\
            USER=runuser\n\
command=/opt/pyenv/shims/python /home/runuser/ComfyUI/main.py --listen --port 8080\n\
autorestart=true\n\
stdout_logfile=/dev/fd/1\n\
stdout_logfile_maxbytes=0\n\
redirect_stderr=true\n'\
>> /etc/supervisord.conf
