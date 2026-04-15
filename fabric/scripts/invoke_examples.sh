#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

TEST_NETWORK_DIR="${TEST_NETWORK_DIR:-"$HOME/fabric-samples/test-network"}"
CHANNEL_NAME="${CHANNEL_NAME:-mychannel}"
CC_NAME="${CC_NAME:-petsc}"

ORDER_ID="${ORDER_ID:-PET-20260411-000001}"
PET_HASH="${PET_HASH:-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa}"
EVID_HASH="${EVID_HASH:-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb}"
BASIS_HASH="${BASIS_HASH:-cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc}"
QUOTE_SUMMARY="${QUOTE_SUMMARY:-weight=3.2kg;distance=12km;price=49.90}"

if [[ ! -f "$TEST_NETWORK_DIR/network.sh" ]]; then
  echo "未找到 test-network: $TEST_NETWORK_DIR"
  exit 1
fi

pushd "$TEST_NETWORK_DIR" >/dev/null

export PATH="$PWD/../bin:$PATH"
export FABRIC_CFG_PATH="$PWD/../config"

source "$TEST_NETWORK_DIR/scripts/envVar.sh"
setGlobals 1

TS() { date +%s%3N; }

echo
echo "=== 1) CreateOrder (invoke) ==="
CREATE_JSON="$(printf '{"orderId":"%s","petHash":"%s","quoteSummary":"%s","ts":%s}' "$ORDER_ID" "$PET_HASH" "$QUOTE_SUMMARY" "$(TS)")"
peer chaincode invoke \
  -o localhost:7050 --ordererTLSHostnameOverride orderer.example.com \
  --tls --cafile "$ORDERER_CA" \
  -C "$CHANNEL_NAME" -n "$CC_NAME" \
  --peerAddresses localhost:7051 --tlsRootCertFiles "$PEER0_ORG1_CA" \
  -c '{"function":"CreateOrder","Args":["'"$CREATE_JSON"'"]}' \
  --waitForEvent

echo
echo "=== 2) QueryOrder (query) ==="
peer chaincode query \
  -C "$CHANNEL_NAME" -n "$CC_NAME" \
  -c '{"function":"QueryOrder","Args":["'"$ORDER_ID"'"]}'

echo
echo "=== 3) UpdateStatus (invoke) ==="
UPDATE_JSON="$(printf '{"orderId":"%s","newStatus":"%s","reason":"%s","ts":%s}' "$ORDER_ID" "IN_TRANSIT" "已揽收，开始运输" "$(TS)")"
peer chaincode invoke \
  -o localhost:7050 --ordererTLSHostnameOverride orderer.example.com \
  --tls --cafile "$ORDERER_CA" \
  -C "$CHANNEL_NAME" -n "$CC_NAME" \
  --peerAddresses localhost:7051 --tlsRootCertFiles "$PEER0_ORG1_CA" \
  -c '{"function":"UpdateStatus","Args":["'"$UPDATE_JSON"'"]}' \
  --waitForEvent

echo
echo "=== 4) AnchorEvidence (invoke) ==="
EVID_JSON="$(printf '{"orderId":"%s","evidenceType":"%s","hash":"%s","ts":%s}' "$ORDER_ID" "PHOTO_PICKUP" "$EVID_HASH" "$(TS)")"
peer chaincode invoke \
  -o localhost:7050 --ordererTLSHostnameOverride orderer.example.com \
  --tls --cafile "$ORDERER_CA" \
  -C "$CHANNEL_NAME" -n "$CC_NAME" \
  --peerAddresses localhost:7051 --tlsRootCertFiles "$PEER0_ORG1_CA" \
  -c '{"function":"AnchorEvidence","Args":["'"$EVID_JSON"'"]}' \
  --waitForEvent

echo
echo "=== 5) RecordSettlement (invoke) ==="
SETTLE_JSON="$(printf '{"orderId":"%s","action":"%s","amount":%s,"node":"%s","ts":%s}' "$ORDER_ID" "freeze" "49.90" "platform" "$(TS)")"
peer chaincode invoke \
  -o localhost:7050 --ordererTLSHostnameOverride orderer.example.com \
  --tls --cafile "$ORDERER_CA" \
  -C "$CHANNEL_NAME" -n "$CC_NAME" \
  --peerAddresses localhost:7051 --tlsRootCertFiles "$PEER0_ORG1_CA" \
  -c '{"function":"RecordSettlement","Args":["'"$SETTLE_JSON"'"]}' \
  --waitForEvent

echo
echo "=== 6) RecordDecision (invoke) ==="
DECISION_JSON="$(printf '{"orderId":"%s","decision":"%s","basisHash":"%s","ts":%s}' "$ORDER_ID" "carrier_responsible" "$BASIS_HASH" "$(TS)")"
peer chaincode invoke \
  -o localhost:7050 --ordererTLSHostnameOverride orderer.example.com \
  --tls --cafile "$ORDERER_CA" \
  -C "$CHANNEL_NAME" -n "$CC_NAME" \
  --peerAddresses localhost:7051 --tlsRootCertFiles "$PEER0_ORG1_CA" \
  -c '{"function":"RecordDecision","Args":["'"$DECISION_JSON"'"]}' \
  --waitForEvent

echo
echo "=== 7) QueryHistory (query) ==="
peer chaincode query \
  -C "$CHANNEL_NAME" -n "$CC_NAME" \
  -c '{"function":"QueryHistory","Args":["'"$ORDER_ID"'"]}'

popd >/dev/null

