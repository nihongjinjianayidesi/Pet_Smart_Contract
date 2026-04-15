#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

TEST_NETWORK_DIR="${TEST_NETWORK_DIR:-"$HOME/fabric-samples/test-network"}"
CHANNEL_NAME="${CHANNEL_NAME:-mychannel}"
CC_NAME="${CC_NAME:-petsc}"
CC_VERSION="${CC_VERSION:-1.0}"
CC_SEQUENCE="${CC_SEQUENCE:-1}"
CC_SRC_PATH="${CC_SRC_PATH:-"$SCRIPT_DIR/../chaincode/petsc"}"

if [[ ! -f "$TEST_NETWORK_DIR/network.sh" ]]; then
  echo "未找到 test-network: $TEST_NETWORK_DIR"
  echo "请设置环境变量 TEST_NETWORK_DIR，例如："
  echo "  export TEST_NETWORK_DIR=\$HOME/fabric-samples/test-network"
  exit 1
fi

pushd "$TEST_NETWORK_DIR" >/dev/null

echo "[deploy] test-network: $TEST_NETWORK_DIR"
echo "[deploy] chaincode path: $CC_SRC_PATH"
echo "[deploy] name=$CC_NAME version=$CC_VERSION sequence=$CC_SEQUENCE channel=$CHANNEL_NAME"

./network.sh deployCC \
  -c "$CHANNEL_NAME" \
  -ccn "$CC_NAME" \
  -ccp "$CC_SRC_PATH" \
  -ccl go \
  -ccv "$CC_VERSION" \
  -ccs "$CC_SEQUENCE"

popd >/dev/null

