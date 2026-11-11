#!/usr/bin/env bash
# ./scripts/push-images.sh 1.1.2
set -euo pipefail
cd "$(dirname "$0")/.."

TAG=${1:?укажите тег, например 1.0.1}
REPO=${REPO:-glavorn}

docker build -t "$REPO/labchecker-backend:$TAG" backend
docker build -t "$REPO/labchecker-frontend:$TAG" -f nginx/Dockerfile .
docker push "$REPO/labchecker-backend:$TAG"
docker push "$REPO/labchecker-frontend:$TAG"

echo "Готово. Обновите newTag в k8s/overlays/prod/kustomization.yaml на $TAG и выполните:"
echo "  kubectl apply -k k8s/overlays/prod"
