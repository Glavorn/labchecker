#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

OVERLAY=k8s/overlays/local
KUBECTL="sudo k3s kubectl"

if ! command -v k3s >/dev/null; then
  echo "k3s не установлен. Установка: curl -sfL https://get.k3s.io | sh -" >&2
  exit 1
fi

if [ ! -f "$OVERLAY/secret.env" ]; then
  cp "$OVERLAY/secret.env.example" "$OVERLAY/secret.env"
  echo "Создан $OVERLAY/secret.env из шаблона"
fi

if [ ! -f "$OVERLAY/teacher.env" ]; then
  echo "TEACHER_TOKEN=$(head -c 24 /dev/urandom | base64 | tr -d '/+=')" > "$OVERLAY/teacher.env"
  echo "Создан $OVERLAY/teacher.env со случайным токеном"
fi

echo "==> Собираю образы"
docker build -t labchecker-backend:local backend
docker build -t labchecker-frontend:local -f nginx/Dockerfile .

# k3s не видит образы docker, импортируем в его containerd
echo "==> Импортирую образы в containerd k3s"
docker save labchecker-backend:local labchecker-frontend:local | sudo k3s ctr images import -

echo "==> Применяю манифесты"
$KUBECTL apply -k "$OVERLAY"

$KUBECTL -n labchecker rollout restart deployment/backend deployment/frontend

echo "==> Жду готовности"
$KUBECTL -n labchecker rollout status statefulset/db --timeout=180s
$KUBECTL -n labchecker rollout status deployment/backend --timeout=180s
$KUBECTL -n labchecker rollout status deployment/frontend --timeout=120s

$KUBECTL -n labchecker get pods,svc,ingress
echo
echo "Готово: http://localhost/ (Ingress через Traefik на 80 порту)"
