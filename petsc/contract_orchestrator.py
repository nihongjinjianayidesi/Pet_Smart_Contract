from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from .evidence_service import EvidenceService
from .fabric_client import FabricClient
from .hash_utils import sha256_hex_from_text, stable_json_dumps


def _money(v: Union[str, float, int, Decimal]) -> Decimal:
    return Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _now_ms_fallback(ts: Optional[int]) -> int:
    if ts is None:
        raise ValueError("ts 不能为空（毫秒级 Unix 时间戳）")
    t = int(ts)
    if t <= 0:
        raise ValueError("ts 必须为毫秒级Unix时间戳(>0)")
    return t


def _norm_status(s: Any) -> str:
    v = str(s or "").strip().upper()
    if v == "CONTRACT_EFFECTIVE":
        return "CREATED"
    return v


CONTRACT_STATUSES = {"CREATED", "PICKED_UP", "IN_TRANSIT", "DELIVERED", "DISPUTED", "COMPLETED"}

LEGAL_STATUS_TRANSITIONS: Dict[str, set] = {
    "CREATED": {"CREATED", "PICKED_UP"},
    "PICKED_UP": {"IN_TRANSIT"},
    "IN_TRANSIT": {"IN_TRANSIT", "DELIVERED"},
    "DELIVERED": {"DELIVERED", "COMPLETED", "DISPUTED"},
    "DISPUTED": {"COMPLETED"},
    "COMPLETED": {"COMPLETED"},
}


NODE_1 = "合约生效"
NODE_2 = "接宠确认"
NODE_3 = "运输启动"
NODE_4 = "途中节点1"
NODE_5 = "途中节点2"
NODE_6 = "到达确认"
NODE_7 = "合约完结"
NODE_CASE = "争议结案"

SETTLEMENT_NODE_RULES: List[Dict[str, Any]] = [
    {
        "nodeKey": "node1",
        "node": NODE_1,
        "fromStatus": "CREATED",
        "toStatus": "CREATED",
        "trigger": "三方电子签名完成",
        "action": "freeze",
        "rate": 1.00,
        "cumulativeReleaseRate": 0.00,
    },
    {
        "nodeKey": "node2",
        "node": NODE_2,
        "fromStatus": "CREATED",
        "toStatus": "PICKED_UP",
        "trigger": "GPS到达接宠点 + 饲主确认装笼",
        "action": "release",
        "rate": 0.20,
        "cumulativeReleaseRate": 0.20,
    },
    {
        "nodeKey": "node3",
        "node": NODE_3,
        "fromStatus": "PICKED_UP",
        "toStatus": "IN_TRANSIT",
        "trigger": "车辆出发/航班起飞 + 环境正常",
        "action": "release",
        "rate": 0.30,
        "cumulativeReleaseRate": 0.50,
    },
    {
        "nodeKey": "node4",
        "node": NODE_4,
        "fromStatus": "IN_TRANSIT",
        "toStatus": "IN_TRANSIT",
        "trigger": "完成1/3路程（GPS/里程计算）",
        "action": "release",
        "rate": 0.15,
        "cumulativeReleaseRate": 0.65,
    },
    {
        "nodeKey": "node5",
        "node": NODE_5,
        "fromStatus": "IN_TRANSIT",
        "toStatus": "IN_TRANSIT",
        "trigger": "完成2/3路程（GPS/里程计算）",
        "action": "release",
        "rate": 0.15,
        "cumulativeReleaseRate": 0.80,
    },
    {
        "nodeKey": "node6",
        "node": NODE_6,
        "fromStatus": "DELIVERED",
        "toStatus": "DELIVERED",
        "trigger": "到达 + 签收 + 2小时无异议",
        "action": "release",
        "rate": 0.10,
        "cumulativeReleaseRate": 0.90,
    },
    {
        "nodeKey": "node7",
        "node": NODE_7,
        "fromStatus": "DELIVERED",
        "toStatus": "COMPLETED",
        "trigger": "7天无申诉",
        "action": "release",
        "rate": 0.10,
        "cumulativeReleaseRate": 1.00,
    },
]


def make_settlement_record(*, orderId: str, node: str, action: str, amount: Union[Decimal, float, int, str], ts: int) -> Dict[str, Any]:
    order_id = str(orderId).strip()
    if not order_id:
        raise ValueError("orderId 不能为空")
    node_ = str(node).strip()
    if not node_:
        raise ValueError("node 不能为空")
    action_ = str(action).strip()
    if action_ not in {"freeze", "release", "refund"}:
        raise ValueError("action 非法，必须为 freeze|release|refund")
    t = _now_ms_fallback(ts)
    amt = float(_money(amount))
    payload: Dict[str, Any] = {"orderId": order_id, "node": node_, "action": action_, "amount": amt, "ts": t}
    payload["hash"] = sha256_hex_from_text(stable_json_dumps(payload))
    return payload


@dataclass
class OrderRuntime:
    orderId: str
    total_fee: Decimal
    total_distance_km: Optional[Decimal] = None
    status: str = "CREATED"

    created_ts: Optional[int] = None
    delivered_ts: Optional[int] = None

    nodes_done: Dict[str, bool] = field(
        default_factory=lambda: {
            "node1": False,
            "node2": False,
            "node3": False,
            "node4": False,
            "node5": False,
            "node6": False,
            "node7": False,
            "case": False,
        }
    )
    released_total: Decimal = field(default_factory=lambda: Decimal("0.00"))


class ContractOrchestrator:
    RELEASE_RATES = {
        "node2": Decimal("0.20"),
        "node3": Decimal("0.30"),
        "node4": Decimal("0.15"),
        "node5": Decimal("0.15"),
        "node6": Decimal("0.10"),
    }

    def __init__(
        self,
        *,
        fabric_client: Optional[FabricClient] = None,
        evidence_service: Optional[EvidenceService] = None,
        record_store_path: Optional[Union[str, Path]] = None,
    ) -> None:
        self.fabric_client = fabric_client
        self.evidence_service = evidence_service
        self._orders: Dict[str, OrderRuntime] = {}

        self.record_store_path: Optional[Path]
        if record_store_path is None:
            self.record_store_path = None
        else:
            self.record_store_path = Path(record_store_path)
            self.record_store_path.parent.mkdir(parents=True, exist_ok=True)
            if not self.record_store_path.exists():
                self.record_store_path.write_text("", encoding="utf-8")

    def register_order(self, order: Dict[str, Any], *, ts: Optional[int] = None) -> Dict[str, Any]:
        order_id = str(order.get("orderId", "")).strip()
        if not order_id:
            raise ValueError("order.orderId 不能为空")

        total_fee = order.get("total_fee", order.get("totalFee"))
        if total_fee is None:
            raise ValueError("order.total_fee 不能为空")
        total_fee_d = _money(total_fee)
        if total_fee_d <= 0:
            raise ValueError("total_fee 必须 > 0")

        total_distance = order.get("total_distance_km", order.get("distance_km", order.get("distanceKm")))
        total_distance_d: Optional[Decimal]
        if total_distance is None or str(total_distance).strip() == "":
            total_distance_d = None
        else:
            total_distance_d = Decimal(str(total_distance))
            if total_distance_d <= 0:
                raise ValueError("total_distance_km 必须 > 0")

        t = _now_ms_fallback(ts) if ts is not None else int(order.get("create_time_ms") or order.get("ts_ms") or 0) or None
        if t is not None and int(t) <= 0:
            raise ValueError("ts 必须为毫秒级Unix时间戳(>0)")

        init_status = _norm_status(order.get("status", "CREATED"))
        if init_status not in CONTRACT_STATUSES:
            init_status = "CREATED"

        rt = OrderRuntime(
            orderId=order_id,
            total_fee=total_fee_d,
            total_distance_km=total_distance_d,
            status=init_status,
            created_ts=int(t) if t is not None else None,
        )
        self._orders[order_id] = rt
        self._append_record(
            {
                "recordId": uuid.uuid4().hex,
                "eventType": "register_order",
                "orderId": order_id,
                "ts": int(t) if t is not None else None,
                "status": rt.status,
                "order": {"orderId": order_id, "total_fee": float(rt.total_fee), "total_distance_km": float(rt.total_distance_km) if rt.total_distance_km else None},
            }
        )
        return {"orderId": order_id, "status": rt.status}

    def get_order_runtime(self, orderId: str) -> Dict[str, Any]:
        rt = self._get_rt(orderId)
        return {
            "orderId": rt.orderId,
            "status": rt.status,
            "total_fee": float(rt.total_fee),
            "total_distance_km": float(rt.total_distance_km) if rt.total_distance_km else None,
            "created_ts": rt.created_ts,
            "delivered_ts": rt.delivered_ts,
            "released_total": float(rt.released_total),
            "nodes_done": dict(rt.nodes_done),
        }

    def advance_state(
        self,
        *,
        orderId: str,
        current_status: str,
        trigger_data: Dict[str, Any],
        ts: int,
    ) -> Dict[str, Any]:
        order_id = str(orderId).strip()
        if not order_id:
            raise ValueError("orderId 不能为空")

        rt = self._get_rt(order_id)
        t = _now_ms_fallback(ts)

        cur = _norm_status(current_status)
        if cur not in CONTRACT_STATUSES:
            raise ValueError("current_status 非法")
        if cur != rt.status:
            raise ValueError(f"current_status 与本地记录不一致：本地={rt.status} 传入={cur}")

        td = dict(trigger_data or {})

        if cur == "CREATED":
            if (not rt.nodes_done["node1"]) and bool(td.get("signatures_complete")):
                settlements = [self._freeze(rt, ts=t, node=NODE_1)]
                rt.nodes_done["node1"] = True
                self._append_fulfillment_event(order_id, old_status=cur, new_status=cur, trigger_node=NODE_1, ts=t, trigger_data=td, settlements=settlements)
                return self._result(order_id, old_status=cur, new_status=cur, trigger_node=NODE_1, ts=t, settlements=settlements)

            if rt.nodes_done["node1"] and (not rt.nodes_done["node2"]) and self._can_pickup(td):
                settlements = [self._release(rt, key="node2", ts=t, node=NODE_2)]
                old = rt.status
                new = "PICKED_UP"
                self._update_status(order_id, new_status=new, reason=NODE_2, ts=t)
                rt.status = new
                rt.nodes_done["node2"] = True
                self._append_fulfillment_event(order_id, old_status=old, new_status=new, trigger_node=NODE_2, ts=t, trigger_data=td, settlements=settlements)
                return self._result(order_id, old_status=old, new_status=new, trigger_node=NODE_2, ts=t, settlements=settlements)

            raise ValueError("当前状态=CREATED，触发条件不足：需要先 signatures_complete 冻结，再满足 接宠确认 条件推进")

        if cur == "PICKED_UP":
            if (not rt.nodes_done["node3"]) and self._can_depart(td):
                settlements = [self._release(rt, key="node3", ts=t, node=NODE_3)]
                old = rt.status
                new = "IN_TRANSIT"
                self._update_status(order_id, new_status=new, reason=NODE_3, ts=t)
                rt.status = new
                rt.nodes_done["node3"] = True
                self._append_fulfillment_event(order_id, old_status=old, new_status=new, trigger_node=NODE_3, ts=t, trigger_data=td, settlements=settlements)
                return self._result(order_id, old_status=old, new_status=new, trigger_node=NODE_3, ts=t, settlements=settlements)
            raise ValueError("当前状态=PICKED_UP，触发条件不足：需要 departed=true 且 env_ok=true")

        if cur == "IN_TRANSIT":
            progress = self._progress_ratio(rt, td)
            if (not rt.nodes_done["node4"]) and progress is not None and progress >= Decimal("0.333333"):
                settlements = [self._release(rt, key="node4", ts=t, node=NODE_4)]
                rt.nodes_done["node4"] = True
                self._append_fulfillment_event(order_id, old_status=cur, new_status=cur, trigger_node=NODE_4, ts=t, trigger_data=td, settlements=settlements)
                return self._result(order_id, old_status=cur, new_status=cur, trigger_node=NODE_4, ts=t, settlements=settlements)

            if (not rt.nodes_done["node5"]) and progress is not None and progress >= Decimal("0.666666"):
                settlements = [self._release(rt, key="node5", ts=t, node=NODE_5)]
                rt.nodes_done["node5"] = True
                self._append_fulfillment_event(order_id, old_status=cur, new_status=cur, trigger_node=NODE_5, ts=t, trigger_data=td, settlements=settlements)
                return self._result(order_id, old_status=cur, new_status=cur, trigger_node=NODE_5, ts=t, settlements=settlements)

            if self._can_arrive(td):
                old = rt.status
                new = "DELIVERED"
                self._update_status(order_id, new_status=new, reason="到达签收", ts=t)
                rt.status = new
                rt.delivered_ts = t
                self._append_fulfillment_event(order_id, old_status=old, new_status=new, trigger_node="到达签收", ts=t, trigger_data=td, settlements=[])
                return self._result(order_id, old_status=old, new_status=new, trigger_node="到达签收", ts=t, settlements=[])

            raise ValueError("当前状态=IN_TRANSIT，触发条件不足：需要里程进度(1/3,2/3)或 arrived+signed+user_confirm")

        if cur == "DELIVERED":
            if rt.delivered_ts is None:
                raise ValueError("DELIVERED 状态缺少 delivered_ts，无法判断异议期与完结条件")

            if (not rt.nodes_done["node6"]) and (t - int(rt.delivered_ts) >= 2 * 60 * 60 * 1000):
                settlements = [self._release(rt, key="node6", ts=t, node=NODE_6)]
                rt.nodes_done["node6"] = True
                self._append_fulfillment_event(order_id, old_status=cur, new_status=cur, trigger_node=NODE_6, ts=t, trigger_data=td, settlements=settlements)
                return self._result(order_id, old_status=cur, new_status=cur, trigger_node=NODE_6, ts=t, settlements=settlements)

            if rt.nodes_done["node6"] and (not rt.nodes_done["node7"]) and (t - int(rt.delivered_ts) >= 7 * 24 * 60 * 60 * 1000):
                settlements = [self._release_final(rt, ts=t, node=NODE_7)]
                old = rt.status
                new = "COMPLETED"
                self._update_status(order_id, new_status=new, reason=NODE_7, ts=t)
                rt.status = new
                rt.nodes_done["node7"] = True
                self._append_fulfillment_event(order_id, old_status=old, new_status=new, trigger_node=NODE_7, ts=t, trigger_data=td, settlements=settlements)
                return self._result(order_id, old_status=old, new_status=new, trigger_node=NODE_7, ts=t, settlements=settlements)

            raise ValueError("当前状态=DELIVERED，触发条件不足：需要2小时无异议释放，或7天无申诉完结")

        if cur == "DISPUTED":
            raise ValueError("当前状态=DISPUTED，请使用 close_case() 完成结案并生成结算指令")

        if cur == "COMPLETED":
            return self._result(order_id, old_status=cur, new_status=cur, trigger_node="noop", ts=t, settlements=[])

        raise ValueError("未知状态")

    def open_dispute(self, *, orderId: str, reason: str, ts: int, evidence: Optional[Any] = None) -> Dict[str, Any]:
        order_id = str(orderId).strip()
        if not order_id:
            raise ValueError("orderId 不能为空")
        rt = self._get_rt(order_id)
        t = _now_ms_fallback(ts)
        if rt.status != "DELIVERED":
            raise ValueError("仅允许在 DELIVERED 状态发起争议")
        if rt.delivered_ts is None:
            raise ValueError("缺少 delivered_ts，无法判断异议期")

        if t - int(rt.delivered_ts) >= 2 * 60 * 60 * 1000:
            raise ValueError("已超过 2 小时异议期，无法发起争议")

        r = str(reason).strip()
        if not r:
            raise ValueError("reason 不能为空")

        old = rt.status
        new = "DISPUTED"
        self._update_status(order_id, new_status=new, reason=f"争议发起:{r}", ts=t)
        rt.status = new

        if evidence is not None:
            self._anchor_hash(order_id, evidence_type="dispute_evidence", payload={"reason": r, "evidence": evidence, "ts": t})

        self._append_fulfillment_event(order_id, old_status=old, new_status=new, trigger_node="争议发起", ts=t, trigger_data={"reason": r}, settlements=[])
        return {"orderId": order_id, "dispute_flag": True, "reason": r}

    def close_case(self, *, orderId: str, decision: str, ts: int, basis: Any) -> Dict[str, Any]:
        order_id = str(orderId).strip()
        if not order_id:
            raise ValueError("orderId 不能为空")
        rt = self._get_rt(order_id)
        t = _now_ms_fallback(ts)
        if rt.status != "DISPUTED":
            raise ValueError("仅允许在 DISPUTED 状态结案")

        d = str(decision).strip()
        if not d:
            raise ValueError("decision 不能为空")

        basis_hash = self._hash_only(payload=basis)
        self._record_decision(order_id, decision=d, basis_hash=basis_hash, ts=t)
        self._anchor_hash(order_id, evidence_type="decision_basis", payload={"decision": d, "basis": basis, "basisHash": basis_hash, "ts": t})

        remaining = _money(rt.total_fee - rt.released_total)
        settlements: List[Dict[str, Any]] = []
        if remaining > Decimal("0.00"):
            action = self._decision_to_settlement_action(d)
            settlements.append(self._record_settlement(order_id, action=action, amount=remaining, node=NODE_CASE, ts=t))
            if action == "release":
                rt.released_total = _money(rt.released_total + remaining)

        old = rt.status
        new = "COMPLETED"
        self._update_status(order_id, new_status=new, reason=NODE_CASE, ts=t)
        rt.status = new
        rt.nodes_done["case"] = True
        rt.nodes_done["node7"] = True
        self._append_fulfillment_event(order_id, old_status=old, new_status=new, trigger_node=NODE_CASE, ts=t, trigger_data={"decision": d, "basisHash": basis_hash}, settlements=settlements)
        return {"orderId": order_id, "dispute_flag": False, "decision": d}

    def query_fulfillment_records(self, *, orderId: str) -> Dict[str, Any]:
        if self.record_store_path is None:
            return {"total": 0, "records": []}
        order_id = str(orderId).strip()
        if not order_id:
            raise ValueError("orderId 不能为空")
        matched: List[Dict[str, Any]] = []
        for rec in self._iter_records():
            if rec.get("orderId") == order_id:
                matched.append(rec)
        return {"total": len(matched), "records": matched}

    def _get_rt(self, order_id: str) -> OrderRuntime:
        rt = self._orders.get(order_id)
        if rt is None:
            raise ValueError(f"订单未注册: {order_id}（请先 register_order）")
        return rt

    def _append_record(self, rec: Dict[str, Any]) -> None:
        if self.record_store_path is None:
            return
        line = json.dumps(rec, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        with self.record_store_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def _iter_records(self) -> List[Dict[str, Any]]:
        if self.record_store_path is None:
            return []
        out: List[Dict[str, Any]] = []
        for line in self.record_store_path.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if not s:
                continue
            try:
                out.append(json.loads(s))
            except Exception:
                continue
        return out

    def _append_fulfillment_event(
        self,
        order_id: str,
        *,
        old_status: str,
        new_status: str,
        trigger_node: str,
        ts: int,
        trigger_data: Dict[str, Any],
        settlements: List[Dict[str, Any]],
    ) -> None:
        self._append_record(
            {
                "recordId": uuid.uuid4().hex,
                "eventType": "advance",
                "orderId": order_id,
                "old_status": old_status,
                "new_status": new_status,
                "trigger_node": trigger_node,
                "ts": ts,
                "trigger_data": trigger_data,
                "settlements": settlements,
            }
        )

    def _result(
        self,
        order_id: str,
        *,
        old_status: str,
        new_status: str,
        trigger_node: str,
        ts: int,
        settlements: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        return {
            "orderId": order_id,
            "old_status": old_status,
            "new_status": new_status,
            "trigger_node": trigger_node,
            "ts": ts,
            "status": "success",
            "settlements": settlements,
        }

    def _can_pickup(self, td: Dict[str, Any]) -> bool:
        gps = td.get("gps") or {}
        if bool(gps.get("at_pickup")) and bool(td.get("user_confirm")):
            return True
        if bool(td.get("at_pickup")) and bool(td.get("user_confirm")):
            return True
        return False

    def _can_depart(self, td: Dict[str, Any]) -> bool:
        return bool(td.get("departed")) and bool(td.get("env_ok"))

    def _progress_ratio(self, rt: OrderRuntime, td: Dict[str, Any]) -> Optional[Decimal]:
        gps = td.get("gps") or {}
        dist = gps.get("distance", gps.get("distance_km", td.get("distance")))
        total = gps.get("total_distance", gps.get("total_distance_km", td.get("total_distance")))
        if total is None:
            total = rt.total_distance_km
        if dist is None or total is None:
            return None
        try:
            d = Decimal(str(dist))
            tot = Decimal(str(total))
        except Exception:
            return None
        if tot <= 0:
            return None
        if d < 0:
            return None
        return d / tot

    def _can_arrive(self, td: Dict[str, Any]) -> bool:
        return bool(td.get("arrived")) and bool(td.get("signed")) and bool(td.get("user_confirm"))

    def _freeze(self, rt: OrderRuntime, *, ts: int, node: str) -> Dict[str, Any]:
        inst = make_settlement_record(orderId=rt.orderId, action="freeze", amount=rt.total_fee, node=node, ts=ts)
        self._anchor_hash(rt.orderId, evidence_type="settlement_instruction", payload=inst)
        return self._record_settlement(rt.orderId, action="freeze", amount=rt.total_fee, node=node, ts=ts)

    def _release(self, rt: OrderRuntime, *, key: str, ts: int, node: str) -> Dict[str, Any]:
        amount = self._calc_release_amount(rt, key=key)
        if amount <= Decimal("0.00"):
            raise ValueError("释放金额计算结果非法")
        inst = make_settlement_record(orderId=rt.orderId, action="release", amount=amount, node=node, ts=ts)
        self._anchor_hash(rt.orderId, evidence_type="settlement_instruction", payload=inst)
        rec = self._record_settlement(rt.orderId, action="release", amount=amount, node=node, ts=ts)
        rt.released_total = _money(rt.released_total + amount)
        return rec

    def _release_final(self, rt: OrderRuntime, *, ts: int, node: str) -> Dict[str, Any]:
        amount = _money(rt.total_fee - rt.released_total)
        if amount <= Decimal("0.00"):
            raise ValueError("剩余金额为0，无需完结释放")
        inst = make_settlement_record(orderId=rt.orderId, action="release", amount=amount, node=node, ts=ts)
        self._anchor_hash(rt.orderId, evidence_type="settlement_instruction", payload=inst)
        rec = self._record_settlement(rt.orderId, action="release", amount=amount, node=node, ts=ts)
        rt.released_total = _money(rt.released_total + amount)
        return rec

    def _calc_release_amount(self, rt: OrderRuntime, *, key: str) -> Decimal:
        rate = self.RELEASE_RATES.get(key)
        if rate is None:
            raise ValueError("未知释放节点")
        return _money(rt.total_fee * rate)

    def _update_status(self, order_id: str, *, new_status: str, reason: str, ts: int) -> Dict[str, Any]:
        payload = {"orderId": order_id, "newStatus": new_status, "reason": reason, "ts": ts}
        self._anchor_hash(order_id, evidence_type="status_update", payload=payload)
        if self.fabric_client is None:
            return {"status": "failed", "errorMsg": "fabric_client 未配置，无法执行链上状态更新"}
        return self.fabric_client.update_status(payload)

    def _record_settlement(self, order_id: str, *, action: str, amount: Union[Decimal, float], node: str, ts: int) -> Dict[str, Any]:
        req = {"orderId": order_id, "action": str(action), "amount": float(_money(amount)), "node": str(node), "ts": int(ts)}
        if self.fabric_client is None:
            return {"status": "failed", "errorMsg": "fabric_client 未配置，无法写入结算记录", "request": req}
        return self.fabric_client.record_settlement(req)

    def _record_decision(self, order_id: str, *, decision: str, basis_hash: str, ts: int) -> Dict[str, Any]:
        req = {"orderId": order_id, "decision": decision, "basisHash": basis_hash, "ts": int(ts)}
        if self.fabric_client is None:
            return {"status": "failed", "errorMsg": "fabric_client 未配置，无法写入责任认定", "request": req}
        return self.fabric_client.record_decision(req)

    def _hash_only(self, *, payload: Any) -> str:
        if self.evidence_service is None:
            raise ValueError("evidence_service 未配置，无法计算 basisHash")
        h = self.evidence_service.hash_data(payload)
        if isinstance(h, dict) and h.get("hash"):
            return str(h["hash"])
        raise ValueError("basisHash 计算失败")

    def _anchor_hash(self, order_id: str, *, evidence_type: str, payload: Any) -> None:
        if self.evidence_service is None:
            return
        try:
            ts: Optional[int] = None
            if isinstance(payload, dict) and payload.get("ts") is not None:
                try:
                    ts = int(payload.get("ts"))
                except Exception:
                    ts = None
            self.evidence_service.anchor_hash(
                orderId=order_id,
                evidenceType=evidence_type,
                rawData=stable_json_dumps(payload) if isinstance(payload, (dict, list)) else payload,
                submitter="orchestrator",
                ts=ts,
            )
        except Exception:
            return

    def _decision_to_settlement_action(self, decision: str) -> str:
        d = str(decision).strip()
        if "承运" in d and "责任" in d:
            return "refund"
        if "饲主" in d and "责任" in d:
            return "release"
        return "refund"
