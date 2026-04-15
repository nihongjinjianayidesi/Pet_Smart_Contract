package main

import "encoding/json"

type OrderStatus string

const (
	// 订单核心状态枚举（论文/接口要求固定为 6 种）
	StatusCreated   OrderStatus = "CREATED"
	StatusPickedUp  OrderStatus = "PICKED_UP"
	StatusInTransit OrderStatus = "IN_TRANSIT"
	StatusDelivered OrderStatus = "DELIVERED"
	StatusDisputed  OrderStatus = "DISPUTED"
	StatusCompleted OrderStatus = "COMPLETED"
)

type Order struct {
	// 订单唯一ID（建议格式：PET-YYYYMMDD-XXXXXX）
	OrderID string `json:"orderId"`

	// 敏感数据只上链哈希摘要：petHash、quoteHash 均为 SHA-256 64位hex
	PetHash   string `json:"petHash"`
	QuoteHash string `json:"quoteHash"`

	Status OrderStatus `json:"status"`

	// 提交方标识：使用 Fabric ClientIdentity（包含证书DN等信息的字符串）
	OwnerID  string `json:"ownerId"`
	OwnerMSP string `json:"ownerMsp"`

	CarrierID  string `json:"carrierId,omitempty"`
	CarrierMSP string `json:"carrierMsp,omitempty"`

	// 时间戳统一为 Unix 毫秒级（由调用方传入，便于业务层统一时间线）
	CreatedTs int64 `json:"createdTs"`
	UpdatedTs int64 `json:"updatedTs"`

	LastReason    string `json:"lastReason,omitempty"`
	LastSubmitter string `json:"lastSubmitter"`
	LastTxID      string `json:"lastTxId"`

	EvidenceCount int `json:"evidenceCount"`

	Settlement *SettlementSummary `json:"settlement,omitempty"`
	Decision   *DecisionSummary   `json:"decision,omitempty"`
}

type Evidence struct {
	OrderID     string `json:"orderId"`
	EvidenceID  string `json:"evidenceId"`
	Type        string `json:"type"`
	Hash        string `json:"hash"`
	Ts          int64  `json:"ts"`
	SignerID    string `json:"signerId"`
	SignerMSP   string `json:"signerMsp"`
	SubmitterID string `json:"submitterId"`
	TxID        string `json:"txId"`
}

type SettlementRecord struct {
	OrderID     string  `json:"orderId"`
	Action      string  `json:"action"`
	Amount      float64 `json:"amount"`
	Node        string  `json:"node"`
	Ts          int64   `json:"ts"`
	SubmitterID string  `json:"submitterId"`
	SubmitterMSP string `json:"submitterMsp"`
	TxID        string  `json:"txId"`
}

type SettlementSummary struct {
	Action string  `json:"action"`
	Amount float64 `json:"amount"`
	Node   string  `json:"node"`
	Ts     int64   `json:"ts"`
	TxID   string  `json:"txId"`
}

type DecisionRecord struct {
	OrderID      string `json:"orderId"`
	Decision     string `json:"decision"`
	BasisHash    string `json:"basisHash"`
	Ts           int64  `json:"ts"`
	SubmitterID  string `json:"submitterId"`
	SubmitterMSP string `json:"submitterMsp"`
	TxID         string `json:"txId"`
}

type DecisionSummary struct {
	Decision  string `json:"decision"`
	BasisHash string `json:"basisHash"`
	Ts        int64  `json:"ts"`
	TxID      string `json:"txId"`
}

type TxResponse struct {
	Status   string `json:"status"`
	TxID     string `json:"txId,omitempty"`
	ErrorMsg string `json:"errorMsg,omitempty"`
	Data     any    `json:"data,omitempty"`
}

func (r TxResponse) JSON() (string, error) {
	b, err := json.Marshal(r)
	if err != nil {
		return "", err
	}
	return string(b), nil
}

type CreateOrderRequest struct {
	OrderID      string `json:"orderId"`
	PetHash      string `json:"petHash"`
	QuoteSummary string `json:"quoteSummary"`
	Ts           int64  `json:"ts"`
	CarrierID    string `json:"carrierId,omitempty"`
	CarrierMSP   string `json:"carrierMsp,omitempty"`
}

type UpdateStatusRequest struct {
	OrderID    string `json:"orderId"`
	NewStatus  string `json:"newStatus"`
	Reason     string `json:"reason,omitempty"`
	Ts         int64  `json:"ts"`
	CarrierID  string `json:"carrierId,omitempty"`
	CarrierMSP string `json:"carrierMsp,omitempty"`
}

type AnchorEvidenceRequest struct {
	OrderID       string `json:"orderId"`
	EvidenceType  string `json:"evidenceType"`
	Hash          string `json:"hash"`
	Ts            int64  `json:"ts"`
	Signer        string `json:"signer,omitempty"`
}

type RecordSettlementRequest struct {
	OrderID string  `json:"orderId"`
	Action  string  `json:"action"`
	Amount  float64 `json:"amount"`
	Node    string  `json:"node"`
	Ts      int64   `json:"ts"`
}

type RecordDecisionRequest struct {
	OrderID    string `json:"orderId"`
	Decision   string `json:"decision"`
	BasisHash  string `json:"basisHash"`
	Ts         int64  `json:"ts"`
}

type QueryRequest struct {
	OrderID string `json:"orderId"`
}

type HistoryEntry struct {
	TxID      string          `json:"txId"`
	IsDelete  bool            `json:"isDelete"`
	Timestamp string          `json:"timestamp"`
	Value     json.RawMessage `json:"value,omitempty"`
}
