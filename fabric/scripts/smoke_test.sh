#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_NETWORK_DIR="${TEST_NETWORK_DIR:-"$HOME/fabric-samples/test-network"}"

SKIP_NETWORK_UP="${SKIP_NETWORK_UP:-0}"

if [[ ! -f "$TEST_NETWORK_DIR/network.sh" ]]; then
  echo "未找到 test-network: $TEST_NETWORK_DIR"
  exit 1
fi

pushd "$TEST_NETWORK_DIR" >/dev/null

if [[ "$SKIP_NETWORK_UP" != "1" ]]; then
  echo "[smoke] 启动网络并创建通道（如已启动可设置 SKIP_NETWORK_UP=1）"
  ./network.sh down
  ./network.sh up createChannel -ca
fi

popd >/dev/null

echo "[smoke] 部署链码"
bash "$SCRIPT_DIR/deploy_petsc_cc.sh"

echo
echo "[smoke] 调用示例接口"
bash "$SCRIPT_DIR/invoke_examples.sh"

echo
echo "[smoke] 完成"

