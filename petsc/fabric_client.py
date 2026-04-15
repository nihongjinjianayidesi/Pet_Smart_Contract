from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol


class FabricClient(Protocol):
    """
    Fabric 调用抽象层。

    说明：
    - 论文与毕设实现里，Python 侧通常通过 Gateway SDK 或 peer CLI 调用链码。
    - 本仓库为“纯标准库”要求，这里只定义最小接口，便于 EvidenceService 解耦。
    """

    def anchor_evidence(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用链码 AnchorEvidence。

        request 字段对齐链码 AnchorEvidenceRequest：
        - orderId / evidenceType / hash / ts（毫秒）/ signer(可选)

        返回建议对齐链码 TxResponse：
        - { "status": "success", "txId": "..." }
        - 或 { "status": "failed", "errorMsg": "..." }
        """

    def update_status(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用链码 UpdateStatus。

        request 字段对齐链码 UpdateStatusRequest：
        - orderId / newStatus / reason(可选) / ts（毫秒）
        """

    def record_settlement(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用链码 RecordSettlement。

        request 字段对齐链码 RecordSettlementRequest：
        - orderId / action(freeze|release|refund) / amount / node / ts（毫秒）
        """

    def record_decision(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用链码 RecordDecision。

        request 字段对齐链码 RecordDecisionRequest：
        - orderId / decision / basisHash / ts（毫秒）
        """


@dataclass
class AnchoredEvidence:
    orderId: str
    evidenceType: str
    hash: str
    ts: int
    signer: Optional[str] = None
    txId: str = field(default_factory=lambda: uuid.uuid4().hex)


class InMemoryFabricStub:
    """
    本地演示/测试用 Fabric Stub：
    - 不依赖任何 Fabric 组件
    - 模拟返回 txId，并把存证记录保存在内存中
    """

    def __init__(self) -> None:
        self.anchored: List[AnchoredEvidence] = []
        self.orders: Dict[str, Dict[str, Any]] = {}
        self.settlements: List[Dict[str, Any]] = []
        self.decisions: List[Dict[str, Any]] = []
        self.history: Dict[str, List[Dict[str, Any]]] = {}

    def anchor_evidence(self, request: Dict[str, Any]) -> Dict[str, Any]:
        try:
            order_id = str(request.get("orderId", "")).strip()
            evidence_type = str(request.get("evidenceType", "")).strip()
            h = str(request.get("hash", "")).strip().lower()
            ts = int(request.get("ts"))
            signer = request.get("signer")

            if not order_id:
                return {"status": "failed", "errorMsg": "orderId 不能为空"}
            if not evidence_type:
                return {"status": "failed", "errorMsg": "evidenceType 不能为空"}
            if len(h) != 64:
                return {"status": "failed", "errorMsg": "hash 非法"}
            if ts <= 0:
                return {"status": "failed", "errorMsg": "ts 必须为毫秒级Unix时间戳(>0)"}

            ev = AnchoredEvidence(
                orderId=order_id,
                evidenceType=evidence_type,
                hash=h,
                ts=ts,
                signer=str(signer).strip() if signer is not None else None,
            )
            self.anchored.append(ev)
            self._append_history(
                order_id,
                {
                    "txId": ev.txId,
                    "ts": ts,
                    "kind": "AnchorEvidence",
                    "request": {"orderId": order_id, "evidenceType": evidence_type, "hash": h, "ts": ts, "signer": ev.signer},
                },
            )
            return {"status": "success", "txId": ev.txId}
        except Exception as e:
            return {"status": "failed", "errorMsg": f"stub 调用异常: {e}"}

    def update_status(self, request: Dict[str, Any]) -> Dict[str, Any]:
        try:
            order_id = str(request.get("orderId", "")).strip()
            new_status = str(request.get("newStatus", "")).strip().upper()
            reason = str(request.get("reason", "")).strip()
            ts = int(request.get("ts"))
            if not order_id:
                return {"status": "failed", "errorMsg": "orderId 不能为空"}
            if not new_status:
                return {"status": "failed", "errorMsg": "newStatus 不能为空"}
            if ts <= 0:
                return {"status": "failed", "errorMsg": "ts 必须为毫秒级Unix时间戳(>0)"}

            tx_id = uuid.uuid4().hex
            cur = self.orders.get(order_id) or {"orderId": order_id}
            cur["status"] = new_status
            cur["updatedTs"] = ts
            if reason:
                cur["lastReason"] = reason
            cur["lastTxId"] = tx_id
            self.orders[order_id] = cur

            self._append_history(
                order_id,
                {"txId": tx_id, "ts": ts, "kind": "UpdateStatus", "value": dict(cur), "request": dict(request)},
            )
            return {"status": "success", "txId": tx_id}
        except Exception as e:
            return {"status": "failed", "errorMsg": f"stub 调用异常: {e}"}

    def record_settlement(self, request: Dict[str, Any]) -> Dict[str, Any]:
        try:
            order_id = str(request.get("orderId", "")).strip()
            action = str(request.get("action", "")).strip()
            amount = float(request.get("amount"))
            node = str(request.get("node", "")).strip()
            ts = int(request.get("ts"))
            if not order_id:
                return {"status": "failed", "errorMsg": "orderId 不能为空"}
            if action not in {"freeze", "release", "refund"}:
                return {"status": "failed", "errorMsg": "action 非法，必须为 freeze|release|refund"}
            if not node:
                return {"status": "failed", "errorMsg": "node 不能为空"}
            if ts <= 0:
                return {"status": "failed", "errorMsg": "ts 必须为毫秒级Unix时间戳(>0)"}
            if amount < 0:
                return {"status": "failed", "errorMsg": "amount 不能为负数"}

            tx_id = uuid.uuid4().hex
            rec = {
                "orderId": order_id,
                "action": action,
                "amount": round(amount, 2),
                "node": node,
                "ts": ts,
                "txId": tx_id,
            }
            self.settlements.append(rec)

            cur = self.orders.get(order_id) or {"orderId": order_id}
            cur["settlement"] = {"action": action, "amount": rec["amount"], "node": node, "ts": ts, "txId": tx_id}
            cur["updatedTs"] = ts
            cur["lastTxId"] = tx_id
            self.orders[order_id] = cur

            self._append_history(
                order_id,
                {"txId": tx_id, "ts": ts, "kind": "RecordSettlement", "value": dict(cur), "request": dict(request)},
            )
            return {"status": "success", "txId": tx_id}
        except Exception as e:
            return {"status": "failed", "errorMsg": f"stub 调用异常: {e}"}

    def record_decision(self, request: Dict[str, Any]) -> Dict[str, Any]:
        try:
            order_id = str(request.get("orderId", "")).strip()
            decision = str(request.get("decision", "")).strip()
            basis_hash = str(request.get("basisHash", "")).strip().lower()
            ts = int(request.get("ts"))
            if not order_id:
                return {"status": "failed", "errorMsg": "orderId 不能为空"}
            if not decision:
                return {"status": "failed", "errorMsg": "decision 不能为空"}
            if len(basis_hash) != 64:
                return {"status": "failed", "errorMsg": "basisHash 非法"}
            if ts <= 0:
                return {"status": "failed", "errorMsg": "ts 必须为毫秒级Unix时间戳(>0)"}

            tx_id = uuid.uuid4().hex
            rec = {"orderId": order_id, "decision": decision, "basisHash": basis_hash, "ts": ts, "txId": tx_id}
            self.decisions.append(rec)

            cur = self.orders.get(order_id) or {"orderId": order_id}
            cur["decision"] = {"decision": decision, "basisHash": basis_hash, "ts": ts, "txId": tx_id}
            cur["updatedTs"] = ts
            cur["lastTxId"] = tx_id
            self.orders[order_id] = cur

            self._append_history(
                order_id,
                {"txId": tx_id, "ts": ts, "kind": "RecordDecision", "value": dict(cur), "request": dict(request)},
            )
            return {"status": "success", "txId": tx_id}
        except Exception as e:
            return {"status": "failed", "errorMsg": f"stub 调用异常: {e}"}

    def query_order(self, request: Dict[str, Any]) -> Dict[str, Any]:
        order_id = str(request.get("orderId", "")).strip()
        if not order_id:
            return {"status": "failed", "errorMsg": "orderId 不能为空"}
        cur = self.orders.get(order_id)
        if cur is None:
            return {"status": "failed", "errorMsg": "订单不存在"}
        return {"status": "success", "data": dict(cur)}

    def query_history(self, request: Dict[str, Any]) -> Dict[str, Any]:
        order_id = str(request.get("orderId", "")).strip()
        if not order_id:
            return {"status": "failed", "errorMsg": "orderId 不能为空"}
        return {"status": "success", "data": list(self.history.get(order_id, []))}

    def _append_history(self, order_id: str, entry: Dict[str, Any]) -> None:
        self.history.setdefault(order_id, []).append(entry)

    def dump_json(self) -> str:
        return json.dumps([e.__dict__ for e in self.anchored], ensure_ascii=False, indent=2)
