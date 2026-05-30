#!/bin/sh
set -eu

# 部署時以 BASE_PATH env 注入路徑前綴；本地/未設時退回根路徑 "/"。
# 必須以 / 開頭、/ 結尾，例如 /meal-staging/。
BASE_PATH="${BASE_PATH:-/}"
case "$BASE_PATH" in
  /*) : ;;
  *) BASE_PATH="/$BASE_PATH" ;;
esac
case "$BASE_PATH" in
  */) : ;;
  *) BASE_PATH="$BASE_PATH/" ;;
esac

ROOT=/usr/share/nginx/html
echo "injecting BASE_PATH=$BASE_PATH into static assets"
find "$ROOT" -type f \( -name '*.js' -o -name '*.html' -o -name '*.css' \) \
  -exec sed -i "s|/__BASE_PATH__/|${BASE_PATH}|g" {} +

exec nginx -g 'daemon off;'
