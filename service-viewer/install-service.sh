#!/bin/bash
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE_FILE="$DIR/service-viewer.service"

echo "=================================================="
echo "🚀 Service Viewer systemd 서비스 설치 및 기동"
echo "=================================================="

if [ ! -f "$SERVICE_FILE" ]; then
    echo "❌ $SERVICE_FILE 파일을 찾을 수 없습니다."
    exit 1
fi

echo "1. /etc/systemd/system/ 에 유닛 파일 복사..."
sudo cp "$SERVICE_FILE" /etc/systemd/system/service-viewer.service

echo "2. systemd 데몬 리로드..."
sudo systemctl daemon-reload

echo "3. 부팅 시 자동실행 등록 및 즉시 시작..."
sudo systemctl enable --now service-viewer.service

echo ""
echo "✅ 설치 및 기동이 완료되었습니다!"
echo "👉 브라우저 접속: http://localhost:8082"
echo ""
sudo systemctl status service-viewer.service --no-pager
