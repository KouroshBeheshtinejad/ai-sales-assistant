#!/usr/bin/env sh
set -eu

: "${PGDUMP_DATABASE_URL:?PGDUMP_DATABASE_URL is required}"
output="${1:-nava-$(date +%F).dump}"
pg_dump --format=custom --file="$output" "$PGDUMP_DATABASE_URL"
printf 'Created %s\n' "$output"