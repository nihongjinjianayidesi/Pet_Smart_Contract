# PetSC 基础链码（模块1）

本目录提供毕业设计“宠物托运智能合约系统”模块1的最小可用 Go 链码：只上链关键摘要/状态变化/证据哈希，支持订单查询与历史追溯。

## 1. 数据模型（链上存证）

- Order：orderId、petHash、quoteHash、status、ownerId、carrierId、createdTs/updatedTs、lastTxId 等
- Evidence：orderId、evidenceId、type、hash、ts、submitterId 等（仅存哈希，不存原文材料）
- SettlementRecord：orderId、action(freeze/release/refund)、amount(保留2位)、node、ts 等（摘要/指令记录）
- DecisionRecord：orderId、decision、basisHash、ts 等（摘要/结论记录）

## 2. 7 个核心接口（参数均为 JSON 字符串）

Fabric v2 的调用一般是：`peer chaincode invoke/query -c '{"function":"XXX","Args":["<JSON>"]}'`

### 写入类（invoke）

- CreateOrder(requestJSON) → `{status:"success", txId:"xxx"}`
- UpdateStatus(requestJSON) → `{status:"success", txId:"xxx"}`
- AnchorEvidence(requestJSON) → `{status:"success", txId:"xxx"}`
- RecordSettlement(requestJSON) → `{status:"success", txId:"xxx"}`
- RecordDecision(requestJSON) → `{status:"success", txId:"xxx"}`

### 查询类（query）

- QueryOrder(orderId 或 `{"orderId":"..."}`) → `{status:"success", data:{...}}`
- QueryHistory(orderId 或 `{"orderId":"..."}`) → `{status:"success", data:[...]}`

## 3. JSON 入参示例

### CreateOrder

```json
{
  "orderId": "PET-20260411-000001",
  "petHash": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "quoteSummary": "weight=3.2kg;distance=12km;price=49.90",
  "ts": 1710000000000
}
```

### UpdateStatus

```json
{
  "orderId": "PET-20260411-000001",
  "newStatus": "IN_TRANSIT",
  "reason": "已揽收，开始运输",
  "ts": 1710000001000
}
```

### AnchorEvidence

```json
{
  "orderId": "PET-20260411-000001",
  "evidenceType": "PHOTO_PICKUP",
  "hash": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  "ts": 1710000002000
}
```

### RecordSettlement

```json
{
  "orderId": "PET-20260411-000001",
  "action": "freeze",
  "amount": 49.9,
  "node": "platform",
  "ts": 1710000003000
}
```

### RecordDecision

```json
{
  "orderId": "PET-20260411-000001",
  "decision": "carrier_responsible",
  "basisHash": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
  "ts": 1710000004000
}
```

## 4. 部署与测试（test-network）

本仓库根目录下提供了脚本，适配 `fabric-samples/test-network`：

- `fabric/scripts/deploy_petsc_cc.sh`
- `fabric/scripts/invoke_examples.sh`
- `fabric/scripts/smoke_test.sh`

