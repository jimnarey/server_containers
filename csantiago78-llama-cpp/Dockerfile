# Pinned csantiago78/llama.cpp source selected inside the image only.
# The host source checkout (/mnt/work/csantiago78-llama-cpp/source) stays on
# the branch tip and clean; only this copy, inside the build, is detached at
# the known-good commit. Mirrors the pattern used by
# generel-schwerz-llama-cpp/Dockerfile.
ARG UBUNTU_VERSION=24.04
ARG CUDA_VERSION=12.8.1
ARG GCC_VERSION=14
ARG CUDA_DOCKER_ARCH=120
# CUDA compilation is memory-hungry; keep rebuilds viable while a large model
# has recently occupied the host page cache.
ARG BUILD_JOBS=4
# csantiago78/llama.cpp's `moe-expert-cache` branch: a GPU-resident LRU cache
# for host-offloaded MoE expert weights (draft PR against ggml-org/llama.cpp
# #27861), independent of the GenerelSchwerz fork. Reported multi-GPU support
# (layer-split across devices) is what generel-schwerz-llama-cpp's own MoE
# cache lacks (see upstream issue GenerelSchwerz/llama.cpp#90). Keep this
# immutable: Docker checks out this copied source tree only.
ARG LLAMA_FORK_BRANCH=moe-expert-cache
ARG LLAMA_FORK_COMMIT=bccbacdb8945680f1cfc7e6bffd1e59014705750

ARG BASE_CUDA_DEV_CONTAINER=docker.io/nvidia/cuda:${CUDA_VERSION}-devel-ubuntu${UBUNTU_VERSION}
ARG BASE_CUDA_RUN_CONTAINER=docker.io/nvidia/cuda:${CUDA_VERSION}-runtime-ubuntu${UBUNTU_VERSION}

FROM ${BASE_CUDA_DEV_CONTAINER} AS build

ARG GCC_VERSION
ARG CUDA_DOCKER_ARCH
ARG BUILD_JOBS
ARG LLAMA_FORK_BRANCH
ARG LLAMA_FORK_COMMIT

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential cmake gcc-${GCC_VERSION} g++-${GCC_VERSION} git libgomp1 python3 && \
    rm -rf /var/lib/apt/lists/*

ENV CC=gcc-${GCC_VERSION} \
    CXX=g++-${GCC_VERSION} \
    CUDAHOSTCXX=g++-${GCC_VERSION}

WORKDIR /src

# The build context is the local checkout at
# /mnt/work/csantiago78-llama-cpp/source. This copy, not that checkout, is
# detached at the known-good revision.
COPY . .
RUN git rev-parse --verify "${LLAMA_FORK_COMMIT}^{commit}" && \
    git checkout --detach "${LLAMA_FORK_COMMIT}" && \
    test "$(git rev-parse HEAD)" = "${LLAMA_FORK_COMMIT}"

RUN cmake -S . -B build \
        -DGGML_NATIVE=OFF \
        -DGGML_CUDA=ON \
        -DGGML_BACKEND_DL=ON \
        -DGGML_CPU_ALL_VARIANTS=ON \
        -DLLAMA_BUILD_TESTS=OFF \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_CUDA_ARCHITECTURES=${CUDA_DOCKER_ARCH} \
        -DCMAKE_EXE_LINKER_FLAGS=-Wl,--allow-shlib-undefined && \
    cmake --build build --config Release --target llama-server --parallel "${BUILD_JOBS}"

RUN mkdir -p /app/lib && \
    find build -name '*.so*' -exec cp -P {} /app/lib \;

FROM ${BASE_CUDA_RUN_CONTAINER} AS server

ARG LLAMA_FORK_BRANCH
ARG LLAMA_FORK_COMMIT

LABEL org.opencontainers.image.source="https://github.com/csantiago78/llama.cpp" \
      org.opencontainers.image.revision="${LLAMA_FORK_COMMIT}" \
      org.opencontainers.image.version="${LLAMA_FORK_BRANCH}"

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl libgomp1 && \
    rm -rf /var/lib/apt/lists/*

COPY --from=build /app/lib/ /app/
COPY --from=build /src/build/bin/llama-server /app/llama-server

ENV LD_LIBRARY_PATH=/app \
    LLAMA_ARG_HOST=0.0.0.0

WORKDIR /app

HEALTHCHECK CMD ["curl", "--fail", "http://localhost:8080/health"]

ENTRYPOINT ["/app/llama-server"]
