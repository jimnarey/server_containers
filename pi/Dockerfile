FROM agent-base:latest

ARG PI_VERSION=1.0.1

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN npm install --global --ignore-scripts \
        "@earendil-works/pi-coding-agent@${PI_VERSION}" && \
    npm cache clean --force

# Keep the trusted global extension in the image, rather than PI_HOME, so a
# fresh persistent Pi home still receives the same guarded web_fetch tool.
RUN mv /usr/local/bin/pi /usr/local/bin/pi-real
COPY extensions/ /opt/pi-extensions/
COPY bin/pi /usr/local/bin/pi
RUN cd /opt/pi-extensions && \
    npm install --omit=dev --ignore-scripts && \
    npm cache clean --force && \
    chmod -R a-w /opt/pi-extensions && \
    chmod 0755 /usr/local/bin/pi
