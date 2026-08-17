FROM ghcr.io/openhands/agent-canvas:1.7.0

USER root

# The upstream image reserves 1000:1000 for a legacy "pn" account and runs
# OpenHands as 10001:10001. Reassign the real account so a numeric Compose user
# still has a meaningful passwd/group identity and the documented home.
RUN userdel pn && \
    groupmod --gid 1000 openhands && \
    usermod --uid 1000 --gid 1000 openhands && \
    chown -R 1000:1000 /home/openhands

# Let the agent install system packages non-interactively while retaining the
# meaningful `openhands` identity used by the numeric Compose user mapping.
RUN echo 'openhands ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/openhands && \
    chmod 0440 /etc/sudoers.d/openhands && \
    visudo -cf /etc/sudoers.d/openhands

USER openhands
