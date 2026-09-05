#!/bin/sh
set -eu

script_directory=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repository_root=$(CDPATH= cd -- "$script_directory/../../.." && pwd)
environment_file=${ENV_FILE:-"$repository_root/.env"}

if [ ! -f "$environment_file" ]; then
	printf '%s\n' "missing local environment file: $environment_file" >&2
	exit 2
fi

# Usage: run-ingest-batch.sh <pairs-file> [parallelism] [max-videos]
# pairs-file: one "<match-natural-key> <video-id>" per line, space-separated
# (natural keys use ':' internally, never spaces, so this splits safely).
pairs_file=${1:?usage: run-ingest-batch.sh <pairs-file> [parallelism] [max-videos]}
parallelism=${2:-4}
max_videos=${3:-1}

# This wrapper is for local development only. CI and deployed environments
# should inject variables directly through their platform configuration.
set -a
# shellcheck disable=SC1090
. "$environment_file"
set +a

cd "$repository_root/services/importer"
# Each invocation is an independent process (own DB pool, own temp dir), so
# concurrent invocations across different matches are safe; -P bounds how
# many run at once to stay well under provider rate limits.
xargs -P "$parallelism" -n2 sh -c \
	'go run ./cmd/ingest-youtube --match-natural-key "$1" --video-id "$2" --max-videos '"$max_videos"'' _ \
	< "$pairs_file"
