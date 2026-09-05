#!/bin/sh
set -eu

# Runs whisper-server natively (not in Docker) so local dev gets Metal
# acceleration on Apple Silicon -- Docker Desktop cannot pass that through
# to a Linux container, so docker/whisper/Dockerfile's image is CPU-only
# and meaningfully slower. Requires `brew install whisper-cpp`.
#
# Downloads to a temp file and renames atomically on success: a partial
# download left in place as the final filename loads "successfully" but
# produces silently hallucinated garbage transcriptions -- this happened
# once during development and cost real debugging time to diagnose.

model_name=${WHISPER_MODEL:-large-v3-turbo}
cache_directory=${WHISPER_MODEL_CACHE:-"$HOME/.cache/whisper.cpp"}
model_path="$cache_directory/ggml-$model_name.bin"

if ! command -v whisper-server >/dev/null 2>&1; then
	printf '%s\n' "whisper-server not found -- install with: brew install whisper-cpp" >&2
	exit 2
fi

mkdir -p "$cache_directory"
if [ ! -f "$model_path" ]; then
	printf '%s\n' "downloading $model_name model to $model_path ..." >&2
	curl -fL --retry 3 -o "$model_path.partial" \
		"https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-$model_name.bin"
	mv "$model_path.partial" "$model_path"
fi

exec whisper-server --host 127.0.0.1 --port "${WHISPER_SERVER_PORT:-8080}" --model "$model_path" --convert
