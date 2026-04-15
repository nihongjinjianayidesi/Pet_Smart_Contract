package main

import (
	"encoding/json"
	"strconv"
	"strings"
	"time"

	"github.com/hyperledger/fabric-contract-api-go/v2/contractapi"
)

type SmartContract struct {
	contractapi.Contract
}

// CreateOrder 创建订单并写入初始状态（CREATED）。
// 入参：一个 JSON 字符串，字段为 orderId / petHash / quoteSummary / ts（毫秒）等。
// 存证策略：petHash 原样上链（要求为 SHA-256 64位hex）；quoteSummary 不上链明文，仅上链 quoteHash=sha256(quoteSummary)。
// 返回：成功返回 {status:"success", txId:"..."}；失败返回 error，其 errorMsg 为 JSON 格式 {status:"failed", errorMsg:"..."}。
func (s *SmartContract) CreateOrder(ctx contractapi.TransactionContextInterface, requestJSON string) (string, error) {
	var req CreateOrderRequest
	if err := parseJSON(requestJSON, &req); err != nil {
		return "", err
	}

	if err := mustNonEmpty("orderId", req.OrderID); err != nil {
		return "", err
	}
	if err := mustValidHash("petHash", req.PetHash); err != nil {
		return "", err
	}
	if err := mustNonEmpty("quoteSummary", req.QuoteSummary); err != nil {
		return "", err
	}
	if err := mustValidTs(req.Ts); err != nil {
		return "", err
	}

	ok, err := s.orderExists(ctx, req.OrderID)
	if err != nil {
		return "", err
	}
	if ok {
		return "", failedError("订单已存在: " + req.OrderID)
	}

	clientID, mspID, err := clientIdentity(ctx)
	if err != nil {
		return "", err
	}

	txID := ctx.GetStub().GetTxID()
	order := Order{
		OrderID: req.OrderID,

		PetHash:   strings.ToLower(req.PetHash),
		QuoteHash: sha256Hex(req.QuoteSummary),

		Status: StatusCreated,

		OwnerID:  clientID,
		OwnerMSP: mspID,

		CarrierID:  strings.TrimSpace(req.CarrierID),
		CarrierMSP: strings.TrimSpace(req.CarrierMSP),

		CreatedTs: req.Ts,
		UpdatedTs: req.Ts,

		LastSubmitter: clientID,
		LastTxID:      txID,
	}

	b, err := json.Marshal(order)
	if err != nil {
		return "", failedError("订单序列化失败: " + err.Error())
	}
	if err := ctx.GetStub().PutState(orderKey(req.OrderID), b); err != nil {
		return "", failedError("写入订单失败: " + err.Error())
	}

	return successTx(txID)
}

// UpdateStatus 更新订单状态（状态枚举见 model.go）。
// 入参：JSON 字符串，字段为 orderId / newStatus / reason / ts（毫秒）等。
// 说明：为保证 QueryHistory 能完整追溯，每次状态更新都会写回 Order 主键（order:<orderId>），因此历史记录天然包含状态变更轨迹。
func (s *SmartContract) UpdateStatus(ctx contractapi.TransactionContextInterface, requestJSON string) (string, error) {
	var req UpdateStatusRequest
	if err := parseJSON(requestJSON, &req); err != nil {
		return "", err
	}
	if err := mustNonEmpty("orderId", req.OrderID); err != nil {
		return "", err
	}
	status, err := mustValidStatus(req.NewStatus)
	if err != nil {
		return "", err
	}
	if err := mustValidTs(req.Ts); err != nil {
		return "", err
	}

	order, err := s.getOrder(ctx, req.OrderID)
	if err != nil {
		return "", err
	}

	clientID, _, err := clientIdentity(ctx)
	if err != nil {
		return "", err
	}

	order.Status = status
	order.UpdatedTs = req.Ts
	order.LastReason = strings.TrimSpace(req.Reason)
	order.LastSubmitter = clientID
	order.LastTxID = ctx.GetStub().GetTxID()

	if strings.TrimSpace(req.CarrierID) != "" {
		order.CarrierID = strings.TrimSpace(req.CarrierID)
	}
	if strings.TrimSpace(req.CarrierMSP) != "" {
		order.CarrierMSP = strings.TrimSpace(req.CarrierMSP)
	}

	if err := s.putOrder(ctx, order); err != nil {
		return "", err
	}

	return successTx(order.LastTxID)
}

// AnchorEvidence 写入证据材料的哈希摘要（不存原始材料）。
// 入参：JSON 字符串，字段为 orderId / evidenceType / hash / ts（毫秒）等。
// 链上存储：Evidence 使用 compositeKey: evidence~<orderId>~<evidenceId>；同时回写 Order.evidenceCount 以便快速展示。
func (s *SmartContract) AnchorEvidence(ctx contractapi.TransactionContextInterface, requestJSON string) (string, error) {
	var req AnchorEvidenceRequest
	if err := parseJSON(requestJSON, &req); err != nil {
		return "", err
	}
	if err := mustNonEmpty("orderId", req.OrderID); err != nil {
		return "", err
	}
	if err := mustNonEmpty("evidenceType", req.EvidenceType); err != nil {
		return "", err
	}
	if err := mustValidHash("hash", req.Hash); err != nil {
		return "", err
	}
	if err := mustValidTs(req.Ts); err != nil {
		return "", err
	}

	order, err := s.getOrder(ctx, req.OrderID)
	if err != nil {
		return "", err
	}

	clientID, mspID, err := clientIdentity(ctx)
	if err != nil {
		return "", err
	}

	txID := ctx.GetStub().GetTxID()
	evidenceID := txID
	eKey, err := ctx.GetStub().CreateCompositeKey("evidence", []string{req.OrderID, evidenceID})
	if err != nil {
		return "", failedError("生成evidenceKey失败: " + err.Error())
	}

	signer := strings.TrimSpace(req.Signer)
	if signer == "" {
		signer = clientID
	}

	ev := Evidence{
		OrderID:     req.OrderID,
		EvidenceID:  evidenceID,
		Type:        strings.TrimSpace(req.EvidenceType),
		Hash:        strings.ToLower(req.Hash),
		Ts:          req.Ts,
		SignerID:    signer,
		SignerMSP:   mspID,
		SubmitterID: clientID,
		TxID:        txID,
	}

	evBytes, err := json.Marshal(ev)
	if err != nil {
		return "", failedError("证据序列化失败: " + err.Error())
	}
	if err := ctx.GetStub().PutState(eKey, evBytes); err != nil {
		return "", failedError("写入证据失败: " + err.Error())
	}

	order.EvidenceCount++
	order.UpdatedTs = req.Ts
	order.LastSubmitter = clientID
	order.LastTxID = txID

	if err := s.putOrder(ctx, order); err != nil {
		return "", err
	}

	return successTx(txID)
}

// RecordSettlement 写入费用托管/结算的指令或结果摘要。
// 入参：JSON 字符串，字段为 orderId / action(freeze|release|refund) / amount / node / ts（毫秒）。
// 链上存储：SettlementRecord 使用 compositeKey: settlement~<orderId>~<txId>；同时回写 Order.settlement 作为最新摘要。
func (s *SmartContract) RecordSettlement(ctx contractapi.TransactionContextInterface, requestJSON string) (string, error) {
	var req RecordSettlementRequest
	if err := parseJSON(requestJSON, &req); err != nil {
		return "", err
	}
	if err := mustNonEmpty("orderId", req.OrderID); err != nil {
		return "", err
	}
	action, err := mustValidSettlementAction(req.Action)
	if err != nil {
		return "", err
	}
	if err := mustNonEmpty("node", req.Node); err != nil {
		return "", err
	}
	if err := mustValidTs(req.Ts); err != nil {
		return "", err
	}
	if req.Amount < 0 {
		return "", failedError("amount 不能为负数")
	}
	amount := round2(req.Amount)

	order, err := s.getOrder(ctx, req.OrderID)
	if err != nil {
		return "", err
	}

	clientID, mspID, err := clientIdentity(ctx)
	if err != nil {
		return "", err
	}

	txID := ctx.GetStub().GetTxID()
	sKey, err := ctx.GetStub().CreateCompositeKey("settlement", []string{req.OrderID, txID})
	if err != nil {
		return "", failedError("生成settlementKey失败: " + err.Error())
	}

	rec := SettlementRecord{
		OrderID:      req.OrderID,
		Action:       action,
		Amount:       amount,
		Node:         strings.TrimSpace(req.Node),
		Ts:           req.Ts,
		SubmitterID:  clientID,
		SubmitterMSP: mspID,
		TxID:         txID,
	}

	recBytes, err := json.Marshal(rec)
	if err != nil {
		return "", failedError("结算记录序列化失败: " + err.Error())
	}
	if err := ctx.GetStub().PutState(sKey, recBytes); err != nil {
		return "", failedError("写入结算记录失败: " + err.Error())
	}

	order.Settlement = &SettlementSummary{
		Action: action,
		Amount: amount,
		Node:   strings.TrimSpace(req.Node),
		Ts:     req.Ts,
		TxID:   txID,
	}
	order.UpdatedTs = req.Ts
	order.LastSubmitter = clientID
	order.LastTxID = txID

	if err := s.putOrder(ctx, order); err != nil {
		return "", err
	}

	return successTx(txID)
}

// RecordDecision 写入责任认定结论摘要。
// 入参：JSON 字符串，字段为 orderId / decision / basisHash / ts（毫秒）。
// 链上存储：DecisionRecord 使用 compositeKey: decision~<orderId>~<txId>；同时回写 Order.decision 作为最新摘要。
func (s *SmartContract) RecordDecision(ctx contractapi.TransactionContextInterface, requestJSON string) (string, error) {
	var req RecordDecisionRequest
	if err := parseJSON(requestJSON, &req); err != nil {
		return "", err
	}
	if err := mustNonEmpty("orderId", req.OrderID); err != nil {
		return "", err
	}
	if err := mustNonEmpty("decision", req.Decision); err != nil {
		return "", err
	}
	if err := mustValidHash("basisHash", req.BasisHash); err != nil {
		return "", err
	}
	if err := mustValidTs(req.Ts); err != nil {
		return "", err
	}

	order, err := s.getOrder(ctx, req.OrderID)
	if err != nil {
		return "", err
	}

	clientID, mspID, err := clientIdentity(ctx)
	if err != nil {
		return "", err
	}

	txID := ctx.GetStub().GetTxID()
	dKey, err := ctx.GetStub().CreateCompositeKey("decision", []string{req.OrderID, txID})
	if err != nil {
		return "", failedError("生成decisionKey失败: " + err.Error())
	}

	rec := DecisionRecord{
		OrderID:      req.OrderID,
		Decision:     strings.TrimSpace(req.Decision),
		BasisHash:    strings.ToLower(req.BasisHash),
		Ts:           req.Ts,
		SubmitterID:  clientID,
		SubmitterMSP: mspID,
		TxID:         txID,
	}

	recBytes, err := json.Marshal(rec)
	if err != nil {
		return "", failedError("责任认定序列化失败: " + err.Error())
	}
	if err := ctx.GetStub().PutState(dKey, recBytes); err != nil {
		return "", failedError("写入责任认定失败: " + err.Error())
	}

	order.Decision = &DecisionSummary{
		Decision:  strings.TrimSpace(req.Decision),
		BasisHash: strings.ToLower(req.BasisHash),
		Ts:        req.Ts,
		TxID:      txID,
	}
	order.UpdatedTs = req.Ts
	order.LastSubmitter = clientID
	order.LastTxID = txID

	if err := s.putOrder(ctx, order); err != nil {
		return "", err
	}

	return successTx(txID)
}

// QueryOrder 查询订单当前快照。
// 入参：支持直接传 orderId，或传 {"orderId":"..."}（便于统一用 JSON 方式调用）。
func (s *SmartContract) QueryOrder(ctx contractapi.TransactionContextInterface, orderIDOrJSON string) (string, error) {
	orderID, err := parseQueryOrderID(orderIDOrJSON)
	if err != nil {
		return "", err
	}

	order, err := s.getOrder(ctx, orderID)
	if err != nil {
		return "", err
	}
	return successData(order)
}

// QueryHistory 查询订单主键的历史变更记录（状态变更、证据写入、结算/认定写入都会触发 Order 回写）。
// 返回：[{txId,isDelete,timestamp,value}] 列表，其中 value 为当时的 Order JSON 快照。
func (s *SmartContract) QueryHistory(ctx contractapi.TransactionContextInterface, orderIDOrJSON string) (string, error) {
	orderID, err := parseQueryOrderID(orderIDOrJSON)
	if err != nil {
		return "", err
	}

	ok, err := s.orderExists(ctx, orderID)
	if err != nil {
		return "", err
	}
	if !ok {
		return "", failedError("订单不存在: " + orderID)
	}

	iter, err := ctx.GetStub().GetHistoryForKey(orderKey(orderID))
	if err != nil {
		return "", failedError("查询历史失败: " + err.Error())
	}
	defer iter.Close()

	out := make([]HistoryEntry, 0)
	for iter.HasNext() {
		mod, err := iter.Next()
		if err != nil {
			return "", failedError("遍历历史失败: " + err.Error())
		}

		ts := ""
		if mod.Timestamp != nil {
			t := time.Unix(mod.Timestamp.Seconds, int64(mod.Timestamp.Nanos))
			ts = formatRFC3339(t)
		}

		entry := HistoryEntry{
			TxID:      mod.TxId,
			IsDelete:  mod.IsDelete,
			Timestamp: ts,
		}
		if len(mod.Value) > 0 && !mod.IsDelete {
			entry.Value = json.RawMessage(mod.Value)
		}

		out = append(out, entry)
	}

	return successData(out)
}

func (s *SmartContract) orderExists(ctx contractapi.TransactionContextInterface, orderID string) (bool, error) {
	b, err := ctx.GetStub().GetState(orderKey(orderID))
	if err != nil {
		return false, failedError("读取订单失败: " + err.Error())
	}
	return b != nil, nil
}

func (s *SmartContract) getOrder(ctx contractapi.TransactionContextInterface, orderID string) (*Order, error) {
	b, err := ctx.GetStub().GetState(orderKey(orderID))
	if err != nil {
		return nil, failedError("读取订单失败: " + err.Error())
	}
	if b == nil {
		return nil, failedError("订单不存在: " + orderID)
	}

	var order Order
	if err := json.Unmarshal(b, &order); err != nil {
		return nil, failedError("订单反序列化失败: " + err.Error())
	}
	return &order, nil
}

func (s *SmartContract) putOrder(ctx contractapi.TransactionContextInterface, order *Order) error {
	b, err := json.Marshal(order)
	if err != nil {
		return failedError("订单序列化失败: " + err.Error())
	}
	if err := ctx.GetStub().PutState(orderKey(order.OrderID), b); err != nil {
		return failedError("写入订单失败: " + err.Error())
	}
	return nil
}

func parseQueryOrderID(orderIDOrJSON string) (string, error) {
	v := strings.TrimSpace(orderIDOrJSON)
	if v == "" {
		return "", failedError("orderId 不能为空")
	}
	if strings.HasPrefix(v, "{") {
		var req QueryRequest
		if err := parseJSON(v, &req); err != nil {
			return "", err
		}
		if err := mustNonEmpty("orderId", req.OrderID); err != nil {
			return "", err
		}
		return req.OrderID, nil
	}
	return v, nil
}

// Ping 便于部署后快速验证链码已能被调用（非论文表 4-7 必需接口）。
func (s *SmartContract) Ping(ctx contractapi.TransactionContextInterface) (string, error) {
	return successData(map[string]string{
		"status": "ok",
		"txId":   ctx.GetStub().GetTxID(),
		"ts":     strconv.FormatInt(time.Now().UnixMilli(), 10),
	})
}
