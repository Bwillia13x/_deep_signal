#!/usr/bin/env sh
set -e
host="$1"
port="$2"
until nc -z "$host" "$port"; do
  echo "Waiting for $host:$port..."
  sleep 1
done
echo "DB is up"
