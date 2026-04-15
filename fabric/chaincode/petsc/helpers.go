package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"math"
	"regexp"
	"strings"
	"time"

	"github.com/hyperledger/fabric-contract-api-go/v2/contractapi"
)

var sha256HexRe = regexp.MustCompile(`^[0-9a-fA-F]{64}$`)

// sha256Hex 对输入字符串做 SHA-256 并输出 64 位十六进制字符串。
func sha256Hex(s string) string {
	sum := sha256.Sum256([]byte(s))
	return hex.EncodeToString(sum[:])
}

func isSHA256Hex(s string) bool {
	return sha256HexRe.MatchString(strings.TrimSpace(s))
}

func round2(v float64) float64 {
	return math.Round(v*100) / 100
}

// successTx / successData 用于把“成功返回结构”统一为 JSON。
func successTx(txID string) (string, error) {
	return TxResponse{Status: "success", TxID: txID}.JSON()
}

func successData(data any) (string, error) {
	return TxResponse{Status: "success", Data: data}.JSON()
}

// failedError 用于把“失败返回结构”统一为 JSON，并作为 error 返回。
// Fabric 里只要返回 error，该交易就会失败回滚；调用侧可直接解析 error 字符串为 JSON。
func failedError(msg string) error {
	s, err := TxResponse{Status: "failed", ErrorMsg: msg}.JSON()
	if err != nil {
		return fmt.Errorf("failed to marshal error: %v", err)
	}
	return fmt.Errorf(s)
}

func parseJSON(input string, out any) error {
	if strings.TrimSpace(input) == "" {
		return failedError("参数不能为空(JSON字符串)")
	}
	dec := json.NewDecoder(strings.NewReader(input))
	dec.DisallowUnknownFields()
	if err := dec.Decode(out); err != nil {
		return failedError("JSON解析失败: " + err.Error())
	}
	return nil
}

func mustNonEmpty(name, v string) error {
	if strings.TrimSpace(v) == "" {
		return failedError(name + " 不能为空")
	}
	return nil
}

func mustValidTs(ts int64) error {
	if ts <= 0 {
		return failedError("ts 必须为毫秒级Unix时间戳(>0)")
	}
	return nil
}

func mustValidHash(name, h string) error {
	if !isSHA256Hex(h) {
		return failedError(name + " 必须为SHA-256的64位十六进制字符串")
	}
	return nil
}

func mustValidStatus(s string) (OrderStatus, error) {
	switch OrderStatus(strings.TrimSpace(s)) {
	case StatusCreated, StatusPickedUp, StatusInTransit, StatusDelivered, StatusDisputed, StatusCompleted:
		return OrderStatus(strings.TrimSpace(s)), nil
	default:
		return "", failedError("newStatus 非法，必须是 CREATED、PICKED_UP、IN_TRANSIT、DELIVERED、DISPUTED、COMPLETED 之一")
	}
}

func mustValidSettlementAction(a string) (string, error) {
	a = strings.ToLower(strings.TrimSpace(a))
	switch a {
	case "freeze", "release", "refund":
		return a, nil
	default:
		return "", failedError("action 非法，必须是 freeze/release/refund 之一")
	}
}

func clientIdentity(ctx contractapi.TransactionContextInterface) (clientID, mspID string, err error) {
	cid := ctx.GetClientIdentity()
	id, err := cid.GetID()
	if err != nil {
		return "", "", failedError("获取提交方ID失败: " + err.Error())
	}
	msp, err := cid.GetMSPID()
	if err != nil {
		return "", "", failedError("获取提交方MSPID失败: " + err.Error())
	}
	return id, msp, nil
}

func orderKey(orderID string) string {
	return "order:" + orderID
}

func formatRFC3339(t time.Time) string {
	if t.IsZero() {
		return ""
	}
	return t.UTC().Format(time.RFC3339Nano)
}
