FROM node:24.19.0-bookworm-slim AS node-runtime

FROM base-ubuntu-24:latest

ARG GUARDED_FETCH_VERSION=0.1.4

COPY --from=node-runtime /usr/local/ /usr/local/

WORKDIR /opt/guarded-fetch

COPY package.json ./
RUN npm install --omit=dev --ignore-scripts "guarded-fetch@${GUARDED_FETCH_VERSION}" && \
    npm cache clean --force

COPY server.mjs ./
RUN chown -R runuser:runuser /opt/guarded-fetch

USER runuser

EXPOSE 8080

CMD ["node", "server.mjs"]
