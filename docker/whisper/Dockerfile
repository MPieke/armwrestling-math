# Builds whisper.cpp's HTTP inference server with a bundled model, so
# self-hosted transcription runs identically in local dev and CI: one
# container, one port, no host-installed toolchain either place.
#
# Model: large-v3-turbo -- OpenAI's whisper-1 API is documented as
# large-v2 under the hood; large-v3-turbo is the closest self-hostable
# match to that quality that's still fast enough to be practical on a
# CI runner's CPU (a distilled large-v3, ~4-6x faster, without the full
# large-v3 model's runtime cost).
FROM debian:bookworm-slim AS build

RUN apt-get update && apt-get install --yes --no-install-recommends \
    build-essential cmake git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src
RUN git clone --branch v1.9.2 --depth 1 https://github.com/ggml-org/whisper.cpp.git .
RUN cmake -B build -DCMAKE_BUILD_TYPE=Release -DGGML_METAL=OFF -DGGML_NATIVE=OFF \
    && cmake --build build --config Release --target whisper-server -j"$(nproc)"

FROM debian:bookworm-slim
RUN apt-get update && apt-get install --yes --no-install-recommends \
    ffmpeg ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=build /src/build/bin/ /usr/local/bin/
RUN mkdir -p /usr/local/lib \
    && mv /usr/local/bin/*.so* /usr/local/lib/ \
    && ldconfig

ARG WHISPER_MODEL=large-v3-turbo
RUN mkdir -p /models \
    && curl -fL -o "/models/ggml-${WHISPER_MODEL}.bin" \
       "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-${WHISPER_MODEL}.bin"
ENV WHISPER_MODEL=${WHISPER_MODEL}

EXPOSE 8080
ENTRYPOINT ["/bin/sh", "-c", "whisper-server --host 0.0.0.0 --port 8080 --model /models/ggml-${WHISPER_MODEL}.bin --convert"]
