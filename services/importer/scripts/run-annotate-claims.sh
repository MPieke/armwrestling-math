#!/bin/sh
set -eu

script_directory=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repository_root=$(CDPATH= cd -- "$script_directory/../../.." && pwd)
environment_file=${ENV_FILE:-"$repository_root/.env"}

if [ ! -f "$environment_file" ]; then
	printf '%s\n' "missing local environment file: $environment_file" >&2
	exit 2
fi

# This wrapper is for local development only. CI and deployed environments
# should inject variables directly through their platform configuration.
set -a
# shellcheck disable=SC1090
. "$environment_file"
set +a

cd "$repository_root/services/importer"
exec go run ./cmd/annotate-claims "$@"
