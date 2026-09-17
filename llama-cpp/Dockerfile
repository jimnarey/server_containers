# One reproducible llama.cpp build definition for every router service. Docker
# build layers retain three neutral source clones; each service copies its
# selected clone beside it, then checks out and builds its pinned revision.
ARG UBUNTU_VERSION=24.04
ARG CUDA_VERSION=12.8.1
ARG GCC_VERSION=14
ARG CUDA_DOCKER_ARCH=120
ARG BUILD_JOBS=4

ARG BASE_CUDA_DEV_CONTAINER=docker.io/nvidia/cuda:${CUDA_VERSION}-devel-ubuntu${UBUNTU_VERSION}
ARG BASE_CUDA_RUN_CONTAINER=docker.io/nvidia/cuda:${CUDA_VERSION}-runtime-ubuntu${UBUNTU_VERSION}

FROM ${BASE_CUDA_DEV_CONTAINER} AS source

ARG LLAMA_REPOSITORY
ARG LLAMA_SOURCE_NAME

# This is deliberately a build-image workspace, not a host bind mount:
# Dockerfiles cannot persistently write a source checkout to the host.
ENV LLAMA_SOURCES=/mnt/work/llama-cpp/sources

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN test -n "${LLAMA_REPOSITORY}" && test -n "${LLAMA_SOURCE_NAME}" && \
    apt-get update && \
    apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/* && \
    mkdir -p "${LLAMA_SOURCES}" && \
    source_dir="${LLAMA_SOURCES}/${LLAMA_SOURCE_NAME}" && \
    if [ -d "${source_dir}/.git" ]; then \
        git -C "${source_dir}" remote set-url origin "${LLAMA_REPOSITORY}"; \
    else \
        git clone --no-checkout "${LLAMA_REPOSITORY}" "${source_dir}"; \
    fi

FROM source AS build

ARG GCC_VERSION
ARG CUDA_DOCKER_ARCH
ARG BUILD_JOBS
ARG LLAMA_REPOSITORY
ARG LLAMA_SOURCE_NAME
ARG LLAMA_SERVICE_NAME
ARG LLAMA_BRANCH
ARG LLAMA_COMMIT
ARG LLAMA_CUDA=ON

RUN test -n "${LLAMA_SERVICE_NAME}" && \
    test -n "${LLAMA_BRANCH}" && \
    test -n "${LLAMA_COMMIT}" && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential cmake gcc-${GCC_VERSION} g++-${GCC_VERSION} libgomp1 python3 && \
    rm -rf /var/lib/apt/lists/*

ENV CC=gcc-${GCC_VERSION} \
    CXX=g++-${GCC_VERSION} \
    CUDAHOSTCXX=g++-${GCC_VERSION}

# Fetch the pinned commit directly. A human-readable branch may later be
# renamed or deleted, but it must never determine a reproducible build.
RUN source_dir="${LLAMA_SOURCES}/${LLAMA_SOURCE_NAME}" && \
    build_dir="${LLAMA_SOURCES}/${LLAMA_SOURCE_NAME}-${LLAMA_SERVICE_NAME}" && \
    test ! -e "${build_dir}" && \
    cp -a "${source_dir}" "${build_dir}" && \
    git -C "${build_dir}" fetch --tags origin "${LLAMA_COMMIT}" && \
    git -C "${build_dir}" rev-parse --verify "${LLAMA_COMMIT}^{commit}" && \
    git -C "${build_dir}" checkout --detach "${LLAMA_COMMIT}" && \
    test "$(git -C "${build_dir}" rev-parse HEAD)" = "${LLAMA_COMMIT}" && \
    cmake_args=( \
        -DGGML_NATIVE=OFF \
        -DGGML_CUDA="${LLAMA_CUDA}" \
        -DGGML_BACKEND_DL=ON \
        -DGGML_CPU_ALL_VARIANTS=ON \
        -DLLAMA_BUILD_TESTS=OFF \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_EXE_LINKER_FLAGS=-Wl,--allow-shlib-undefined \
    ) && \
    if [ "${LLAMA_CUDA}" = ON ]; then \
        cmake_args+=("-DCMAKE_CUDA_ARCHITECTURES=${CUDA_DOCKER_ARCH}"); \
    fi && \
    cmake -S "${build_dir}" -B "${build_dir}/build" "${cmake_args[@]}" && \
    cmake --build "${build_dir}/build" --config Release --target llama-server --parallel "${BUILD_JOBS}" && \
    mkdir -p /output/lib && \
    find "${build_dir}/build" -name '*.so*' -exec cp -P {} /output/lib/ \; && \
    cp "${build_dir}/build/bin/llama-server" /output/llama-server

FROM ${BASE_CUDA_RUN_CONTAINER} AS server

ARG LLAMA_REPOSITORY
ARG LLAMA_BRANCH
ARG LLAMA_COMMIT

LABEL org.opencontainers.image.source="${LLAMA_REPOSITORY}" \
      org.opencontainers.image.revision="${LLAMA_COMMIT}" \
      org.opencontainers.image.version="${LLAMA_BRANCH}"

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl libgomp1 && \
    rm -rf /var/lib/apt/lists/*

COPY --from=build /output/lib/ /app/
COPY --from=build /output/llama-server /app/llama-server

ENV LD_LIBRARY_PATH=/app \
    LLAMA_ARG_HOST=0.0.0.0

WORKDIR /app

HEALTHCHECK CMD ["curl", "--fail", "http://localhost:8080/health"]

ENTRYPOINT ["/app/llama-server"]
