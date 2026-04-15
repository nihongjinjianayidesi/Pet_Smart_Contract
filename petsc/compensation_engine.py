from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from .evidence_service import EvidenceService
from .fabric_client import FabricClient
from .hash_utils import SHA256_HEX_RE, stable_json_dumps


def _now_ms() -> int:
    return int(time.time() * 1000)


def _money(x: Union[Decimal, float, int, str]) -> Decimal:
    try:
        d = x if isinstance(x, Decimal) else Decimal(str(x))
    except Exception:
        raise ValueError("金额必须为数字")
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _money_f(x: Union[Decimal, float, int, str]) -> float:
    return float(_money(x))


def _float_1dp(v: Any) -> float:
    try:
        d = Decimal(str(v))
    except Exception:
        raise ValueError("偏离距离必须为数字")
    return float(d.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def _norm_str(v: Any) -> str:
    return str(v).strip()


def _require_ms_ts(v: Any, *, field: str) -> int:
    try:
        ts = int(v)
    except Exception:
        raise ValueError(f"{field} 必须为毫秒级Unix时间戳")
    if ts <= 0:
        raise ValueError(f"{field} 必须为毫秒级Unix时间戳(>0)")
    return ts


def _is_sha256_hex(v: Any) -> bool:
    return bool(SHA256_HEX_RE.match(str(v).strip().lower()))


def _as_decimal(v: Any, *, field: str) -> Decimal:
    try:
        return Decimal(str(v))
    except Exception:
        raise ValueError(f"{field} 必须为数字")


def _append_jsonl(path: Path, record: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("", encoding="utf-8")
    with path.open("a", encoding="utf-8") as f:
        f.write(stable_json_dumps(record) + "\n")


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s:
            continue
        try:
            out.append(json.loads(s))
        except Exception:
            continue
    return out


@dataclass(frozen=True)
class PaymentResult:
    status: str
    txId: Optional[str]
    from_account: str
    to_account: str
    amount: float
    ts: int
    errorMsg: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "status": self.status,
            "txId": self.txId,
            "from": self.from_account,
            "to": self.to_account,
            "amount": float(self.amount),
            "ts": int(self.ts),
        }
        if self.errorMsg:
            d["errorMsg"] = self.errorMsg
        return d


class PaymentSimulator:
    """
    链下支付系统（模拟）。

    说明：
    - 论文语境里“赔付执行”通常发生在链下真实支付系统，此处用内存账本模拟。
    - 支持“商家保证金优先扣除”。
    """

    def __init__(self, *, merchant_deposit: float = 5000.0, owner_wallet: float = 0.0) -> None:
        self.balances: Dict[str, Decimal] = {
            "merchant_deposit": _money(merchant_deposit),
            "owner_wallet": _money(owner_wallet),
        }
        self.payments: List[Dict[str, Any]] = []

    def execute(self, instruction: Dict[str, Any]) -> Dict[str, Any]:
        try:
            from_acc = _norm_str(instruction.get("from", ""))
            to_acc = _norm_str(instruction.get("to", ""))
            amount = _money(instruction.get("amount", 0))
            ts = _require_ms_ts(instruction.get("ts") or _now_ms(), field="ts")

            if not from_acc or not to_acc:
                return {"status": "failed", "errorMsg": "from/to 不能为空"}
            if amount <= Decimal("0.00"):
                return {"status": "failed", "errorMsg": "amount 必须 > 0"}
            if from_acc not in self.balances:
                return {"status": "failed", "errorMsg": "from 账户不存在"}
            if to_acc not in self.balances:
                self.balances[to_acc] = Decimal("0.00")

            if self.balances[from_acc] < amount:
                return {"status": "failed", "errorMsg": "余额不足"}

            self.balances[from_acc] = _money(self.balances[from_acc] - amount)
            self.balances[to_acc] = _money(self.balances[to_acc] + amount)
            tx_id = uuid.uuid4().hex
            rec = {
                "txId": tx_id,
                "from": from_acc,
                "to": to_acc,
                "amount": float(amount),
                "ts": ts,
                "balances": {k: float(v) for k, v in self.balances.items()},
            }
            self.payments.append(rec)
            return {"status": "success", "txId": tx_id, "data": dict(rec)}
        except Exception as e:
            return {"status": "failed", "errorMsg": f"payment simulator 异常: {e}"}


class CompensationEngine:
    """
    异常检测与智能赔付引擎（链下，Python 标准库实现）。

    设计目标：
    - 异常发现/证据留痕/通知/时限管控（链下编排）
    - 责任认定（自动规则 + 人工/监管入口）与赔付执行解耦
    - 赔付计算结果、责任结论、关键证据 hash 通过 Fabric 链码接口写链（可注入真实网关或使用 Stub）
    """

    EXCEPTION_TYPE_ALIASES: Dict[str, str] = {
        "环境参数超标": "env_out_of_range",
        "环境超标": "env_out_of_range",
        "env_out_of_range": "env_out_of_range",
        "路线偏离": "route_deviation",
        "route_deviation": "route_deviation",
        "宠物状态异常": "pet_status_abnormal",
        "pet_status_abnormal": "pet_status_abnormal",
        "托运延误": "shipping_delay",
        "延误": "shipping_delay",
        "shipping_delay": "shipping_delay",
        "宠物受伤": "pet_injury",
        "受伤": "pet_injury",
        "pet_injury": "pet_injury",
        "宠物死亡/丢失": "pet_death_or_lost",
        "死亡/丢失": "pet_death_or_lost",
        "pet_death_or_lost": "pet_death_or_lost",
    }

    DEFAULT_CONFIG: Dict[str, Any] = {
        "deadlines": {
            "env_out_of_range": {"response_minutes": 0, "handle_minutes": 30},
            "route_deviation": {"response_minutes": 0, "handle_minutes": 15},
            "pet_status_abnormal": {"response_minutes": 15, "handle_minutes": 60},
            "shipping_delay": {"response_minutes": None, "handle_minutes": None},
            "pet_injury": {"response_minutes": 0, "handle_minutes": None},
            "pet_death_or_lost": {"response_minutes": 0, "handle_minutes": None},
        },
        "rules": {
            "env_out_of_range": {"refund_rate": 1.0},
            "route_deviation": {"refund_rate": 1.0},
            "pet_status_abnormal": {"medical_share_rate": 0.5, "extra_fee_rate": 0.2},
            "shipping_delay": {
                "tiers_hours": [12, 24, 72],
                "tier_payout": {
                    "12": {"refund_rate": 0.5, "extra_rate": 0.0},
                    "24": {"refund_rate": 1.0, "extra_rate": 0.2},
                    "72": {"refund_rate": 1.0, "extra_rate": 0.5},
                },
            },
            "pet_injury": {"minor_refund_rate": 0.5, "serious_refund_rate": 1.0},
            "pet_death_or_lost": {"default_multiplier": 3.0},
        },
        "accounts": {"from": "merchant_deposit", "to": "owner_wallet"},
        "record_store": {"exceptions_jsonl": "offchain_data/exception_records.jsonl"},
    }

    def __init__(
        self,
        *,
        fabric_client: Optional[FabricClient] = None,
        evidence_service: Optional[EvidenceService] = None,
        payment: Optional[PaymentSimulator] = None,
        config: Optional[Dict[str, Any]] = None,
        record_store_path: Optional[Union[str, Path]] = None,
    ) -> None:
        self.fabric_client = fabric_client
        self.evidence_service = evidence_service
        self.payment = payment or PaymentSimulator()
        self.config: Dict[str, Any] = dict(self.DEFAULT_CONFIG)
        if config:
            self._deep_merge(self.config, config)

        if record_store_path is None:
            record_store_path = self.config.get("record_store", {}).get("exceptions_jsonl") or "offchain_data/exception_records.jsonl"
        self.record_store_path = Path(record_store_path)

    def handle_exception(self, detect_input: Dict[str, Any], *, ts_ms: Optional[int] = None) -> Dict[str, Any]:
        """
        异常响应处置入口（检测/上报后调用）。

        输出对齐论文“异常响应输出”核心字段：
        - exception_id / orderId / exception_type / status / response_time / handle_time
        """

        order_id = _norm_str(detect_input.get("orderId", ""))
        if not order_id:
            return {"status": "failed", "errorMsg": "orderId 不能为空"}

        exc_type_raw = _norm_str(detect_input.get("exception_type", ""))
        exc_type = self._normalize_exception_type(exc_type_raw)
        if exc_type is None:
            return {"status": "failed", "errorMsg": "无效 exception_type"}

        detect_time = detect_input.get("detect_time")
        if detect_time is None:
            detect_time = ts_ms if ts_ms is not None else _now_ms()
        detect_ts = _require_ms_ts(detect_time, field="detect_time")

        detect_data = detect_input.get("detect_data")
        if detect_data is None:
            return {"status": "failed", "errorMsg": "detect_data 不能为空"}

        exception_id_in = detect_input.get("exception_id")
        exception_id = _norm_str(exception_id_in) if exception_id_in is not None else ""
        if not exception_id:
            exception_id = self._new_exception_id(detect_ts)
        deadlines = self._calc_deadlines(exc_type, detect_ts)

        record: Dict[str, Any] = {
            "exception_id": exception_id,
            "orderId": order_id,
            "exception_type": exc_type,
            "detect_time": detect_ts,
            "detect_data": detect_data,
            "status": "detected",
            "response_deadline": deadlines[0],
            "handle_deadline": deadlines[1],
            "evidence": [],
            "notifications": [],
            "decision": None,
            "compensation": None,
            "settlement": None,
            "payment": None,
            "audit": {"createdTs": detect_ts, "updatedTs": detect_ts},
        }

        evidence = self._collect_and_anchor_evidence(order_id, exc_type, detect_data, detect_ts)
        if evidence:
            record["evidence"] = evidence

        record["notifications"] = self._build_notifications(order_id, exc_type, exception_id, detect_ts)
        _append_jsonl(self.record_store_path, record)

        out = {
            "status": "success",
            "exception_id": exception_id,
            "orderId": order_id,
            "exception_type": exc_type,
            "status_code": record["status"],
            "response_time": detect_ts,
            "handle_time": None,
            "deadlines": {"response_deadline": deadlines[0], "handle_deadline": deadlines[1]},
        }
        return out

    def record_decision(self, decision_input: Dict[str, Any], *, basis_data: Optional[Any] = None) -> Dict[str, Any]:
        """
        责任认定对接入口（系统自动认定或人工/监管认定均可走这里）。

        输入规范：
        - {"orderId":"...","decision":"merchant|owner|force_majeure|none","basisHash":"...","ts":...,"handler":"admin/regulator"}

        解耦约束：
        - 仅记录/接收责任结论；赔付执行需要显式调用 calc_compensation / execute_settlement
        """

        order_id = _norm_str(decision_input.get("orderId", ""))
        if not order_id:
            return {"status": "failed", "errorMsg": "orderId 不能为空"}

        decision = _norm_str(decision_input.get("decision", ""))
        if not decision:
            return {"status": "failed", "errorMsg": "decision 不能为空"}

        handler = _norm_str(decision_input.get("handler", "")) or None
        ts = decision_input.get("ts")
        submit_ts = _require_ms_ts(ts if ts is not None else _now_ms(), field="ts")

        basis_hash = decision_input.get("basisHash")
        if basis_hash is None and basis_data is not None:
            basis_hash = self._hash_only(basis_data)
        if basis_hash is None or not _is_sha256_hex(basis_hash):
            return {"status": "failed", "errorMsg": "basisHash 非法（需64位小写SHA-256）"}
        basis_hash_norm = str(basis_hash).strip().lower()

        if basis_data is not None:
            self._anchor_payload(order_id, evidence_type="decision_basis", payload=basis_data, ts=submit_ts, submitter=handler or "regulator")

        req = {"orderId": order_id, "decision": decision, "basisHash": basis_hash_norm, "ts": submit_ts}
        if self.fabric_client is None:
            chain = {"status": "failed", "errorMsg": "fabric_client 未配置，无法写入责任认定", "request": req}
        else:
            chain = self.fabric_client.record_decision(req)

        self._update_latest_exception(order_id, update={"decision": {"orderId": order_id, "decision": decision, "basisHash": basis_hash_norm, "ts": submit_ts, "handler": handler, "chain": chain}})
        return {"status": "success", "data": {"orderId": order_id, "decision": decision, "basisHash": basis_hash_norm, "ts": submit_ts, "handler": handler}, "chain": chain}

    def calc_compensation(
        self,
        *,
        order_context: Dict[str, Any],
        exception_id: str,
        decision: Optional[Dict[str, Any]] = None,
        ts_ms: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        赔付金额计算入口（不直接执行支付）。
        """

        ts = _require_ms_ts(ts_ms if ts_ms is not None else _now_ms(), field="ts")
        order_id = _norm_str(order_context.get("orderId") or order_context.get("order_id") or "")
        if not order_id:
            return {"status": "failed", "errorMsg": "order_context.orderId 不能为空"}

        exc = self.get_exception_archive({"exception_id": exception_id}).get("records", [])
        if not exc:
            return {"status": "failed", "errorMsg": "exception_id 不存在"}
        ex = exc[0]
        if _norm_str(ex.get("orderId", "")) != order_id:
            return {"status": "failed", "errorMsg": "order_context.orderId 与异常记录不一致"}

        exc_type = _norm_str(ex.get("exception_type", ""))
        detect_data = ex.get("detect_data") or {}

        if decision is None:
            decision = ex.get("decision")
            if isinstance(decision, dict) and "decision" in decision:
                decision = decision
        decision_value, basis_hash = self._extract_decision(decision)

        total_fee = _as_decimal(order_context.get("total_fee") or order_context.get("totalFee") or 0, field="total_fee")
        segment_fee = order_context.get("segment_fee") or order_context.get("segmentFee")
        segment_fee_d = _as_decimal(segment_fee, field="segment_fee") if segment_fee is not None else total_fee

        if decision_value not in {"merchant", "owner", "force_majeure", "none"}:
            return {"status": "failed", "errorMsg": "decision 非法（merchant|owner|force_majeure|none）"}

        if decision_value != "merchant":
            comp = {"exception_id": exception_id, "orderId": order_id, "amount": 0.0, "compensation_type": exc_type, "basis": "非商家责任，不触发赔付", "ts": ts}
            self._update_exception_by_id(exception_id, update={"compensation": comp})
            return {"status": "success", "data": comp}

        amount, basis = self._calc_amount_by_type(exc_type, detect_data, total_fee, segment_fee_d)
        comp = {"exception_id": exception_id, "orderId": order_id, "amount": _money_f(amount), "compensation_type": exc_type, "basis": basis, "ts": ts}
        if basis_hash:
            comp["basisHash"] = basis_hash
        self._update_exception_by_id(exception_id, update={"compensation": comp})
        return {"status": "success", "data": comp}

    def execute_settlement(self, instruction: Dict[str, Any]) -> Dict[str, Any]:
        """
        赔付执行：生成/接收赔付指令 -> 链上记录 -> 链下支付模拟 -> 结果回写链上。
        """

        order_id = _norm_str(instruction.get("orderId", ""))
        if not order_id:
            return {"status": "failed", "errorMsg": "orderId 不能为空"}
        ts = _require_ms_ts(instruction.get("ts") or _now_ms(), field="ts")
        amount = _money(instruction.get("amount") or 0)
        if amount <= Decimal("0.00"):
            return {"status": "failed", "errorMsg": "amount 必须 > 0"}

        exception_id = instruction.get("exception_id")
        basis_hash = instruction.get("basisHash")

        chain_req = {"orderId": order_id, "action": "refund", "amount": float(amount), "node": "EXCEPTION_COMP", "ts": ts}
        if self.fabric_client is None:
            chain = {"status": "failed", "errorMsg": "fabric_client 未配置，无法写入赔付记录", "request": chain_req}
        else:
            chain = self.fabric_client.record_settlement(chain_req)

        pay = self.payment.execute(instruction)
        pay_result = PaymentResult(
            status=str(pay.get("status") or "failed"),
            txId=str(pay.get("txId")) if pay.get("txId") else None,
            from_account=_norm_str(instruction.get("from", "")),
            to_account=_norm_str(instruction.get("to", "")),
            amount=float(amount),
            ts=ts,
            errorMsg=str(pay.get("errorMsg")) if pay.get("status") != "success" and pay.get("errorMsg") else None,
        ).to_dict()

        settlement_rec: Dict[str, Any] = {
            "orderId": order_id,
            "action": _norm_str(instruction.get("action", "compensate")) or "compensate",
            "amount": float(amount),
            "from": _norm_str(instruction.get("from", "")),
            "to": _norm_str(instruction.get("to", "")),
            "basisHash": str(basis_hash).strip().lower() if basis_hash else None,
            "ts": ts,
            "chain": chain,
            "payment": pay_result,
        }

        if exception_id:
            self._update_exception_by_id(str(exception_id), update={"settlement": settlement_rec, "payment": pay_result})
        else:
            self._update_latest_exception(order_id, update={"settlement": settlement_rec, "payment": pay_result})

        return {"status": "success", "data": settlement_rec}

    def build_settlement_instruction(
        self,
        *,
        orderId: str,
        amount: float,
        basisHash: Optional[str],
        ts_ms: Optional[int] = None,
        exception_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        ts = _require_ms_ts(ts_ms if ts_ms is not None else _now_ms(), field="ts")
        cfg_acc = self.config.get("accounts", {}) or {}
        from_acc = _norm_str(cfg_acc.get("from") or "merchant_deposit")
        to_acc = _norm_str(cfg_acc.get("to") or "owner_wallet")
        inst: Dict[str, Any] = {
            "orderId": _norm_str(orderId),
            "action": "compensate",
            "amount": float(_money(amount)),
            "from": from_acc,
            "to": to_acc,
            "basisHash": str(basisHash).strip().lower() if basisHash else None,
            "ts": ts,
        }
        if exception_id:
            inst["exception_id"] = str(exception_id)
        return inst

    def get_exception_archive(self, query: Dict[str, Any], *, page: int = 1, pageSize: int = 50) -> Dict[str, Any]:
        """
        异常档案查询：支持按 orderId/exception_id/time_range 查询。
        """

        q_order = _norm_str(query.get("orderId", "")) if query.get("orderId") is not None else None
        q_exc = _norm_str(query.get("exception_id", "")) if query.get("exception_id") is not None else None
        start_time = query.get("startTime")
        end_time = query.get("endTime")
        st = int(start_time) if start_time is not None else None
        et = int(end_time) if end_time is not None else None

        records = _read_jsonl(self.record_store_path)
        filtered: List[Dict[str, Any]] = []
        for r in records:
            if q_order and _norm_str(r.get("orderId", "")) != q_order:
                continue
            if q_exc and _norm_str(r.get("exception_id", "")) != q_exc:
                continue
            dt = r.get("detect_time")
            if st is not None and isinstance(dt, int) and dt < st:
                continue
            if et is not None and isinstance(dt, int) and dt > et:
                continue
            filtered.append(r)

        total = len(filtered)
        if page <= 0:
            page = 1
        if pageSize <= 0:
            pageSize = 50
        start = (page - 1) * pageSize
        end = start + pageSize
        return {"total": total, "page": page, "pageSize": pageSize, "records": filtered[start:end]}

    def auto_detect(self, detect_input: Dict[str, Any], *, order_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        可选：对环境/GPS/延误等输入做“自动判定是否异常”。
        若判定为异常，则直接调用 handle_exception。
        """

        exc_type_raw = _norm_str(detect_input.get("exception_type", ""))
        exc_type = self._normalize_exception_type(exc_type_raw)
        if exc_type is None:
            return {"status": "failed", "errorMsg": "无效 exception_type"}

        detect_data = detect_input.get("detect_data") or {}
        ok, reason = self._judge_is_exception(exc_type, detect_data, order_context=order_context)
        if not ok:
            return {"status": "success", "is_exception": False, "reason": reason}
        resp = self.handle_exception(detect_input)
        resp["is_exception"] = True
        resp["reason"] = reason
        return resp

    def _normalize_exception_type(self, raw: str) -> Optional[str]:
        s = _norm_str(raw)
        if not s:
            return None
        return self.EXCEPTION_TYPE_ALIASES.get(s)

    def _new_exception_id(self, ts_ms: int) -> str:
        ymd = time.strftime("%Y%m%d", time.localtime(ts_ms / 1000))
        return f"EXP-{ymd}-{uuid.uuid4().hex[:6].upper()}"

    def _calc_deadlines(self, exc_type: str, detect_ts: int) -> Tuple[Optional[int], Optional[int]]:
        dcfg = (self.config.get("deadlines") or {}).get(exc_type) or {}
        resp_min = dcfg.get("response_minutes")
        handle_min = dcfg.get("handle_minutes")
        resp_deadline = detect_ts + int(resp_min) * 60 * 1000 if resp_min is not None else None
        handle_deadline = detect_ts + int(handle_min) * 60 * 1000 if handle_min is not None else None
        return resp_deadline, handle_deadline

    def _collect_and_anchor_evidence(self, order_id: str, exc_type: str, detect_data: Any, ts: int) -> List[Dict[str, Any]]:
        if self.evidence_service is None:
            return []
        try:
            evidence_type = f"exception_{exc_type}"
            payload = {"orderId": order_id, "exception_type": exc_type, "detect_data": detect_data, "ts": ts}
            r = self.evidence_service.anchor_hash(
                orderId=order_id,
                evidenceType=evidence_type,
                rawData=stable_json_dumps(payload),
                submitter="platform",
                ts=ts,
            )
            return [{"evidenceType": evidence_type, "hash": r.get("hash"), "txId": r.get("txId"), "status": r.get("status"), "ts": ts}]
        except Exception:
            return []

    def _build_notifications(self, order_id: str, exc_type: str, exception_id: str, ts: int) -> List[Dict[str, Any]]:
        return [
            {"to": "owner", "orderId": order_id, "exception_id": exception_id, "exception_type": exc_type, "ts": ts},
            {"to": "merchant", "orderId": order_id, "exception_id": exception_id, "exception_type": exc_type, "ts": ts},
        ]

    def _hash_only(self, payload: Any) -> str:
        if self.evidence_service is None:
            raise ValueError("evidence_service 未配置，无法计算 basisHash")
        h = self.evidence_service.hash_data(payload)
        if isinstance(h, dict) and h.get("hash"):
            return str(h["hash"])
        raise ValueError("basisHash 计算失败")

    def _anchor_payload(self, order_id: str, *, evidence_type: str, payload: Any, ts: int, submitter: str) -> None:
        if self.evidence_service is None:
            return
        try:
            self.evidence_service.anchor_hash(
                orderId=order_id,
                evidenceType=evidence_type,
                rawData=stable_json_dumps(payload) if isinstance(payload, (dict, list)) else payload,
                submitter=submitter,
                ts=ts,
            )
        except Exception:
            return

    def _extract_decision(self, decision_obj: Optional[Dict[str, Any]]) -> Tuple[Optional[str], Optional[str]]:
        if decision_obj is None:
            return None, None
        if "decision" in decision_obj and isinstance(decision_obj.get("decision"), str):
            d = _norm_str(decision_obj.get("decision"))
        else:
            d = _norm_str(decision_obj.get("decision", "")) if isinstance(decision_obj, dict) else ""
        if not d:
            return None, None
        bh = decision_obj.get("basisHash") if isinstance(decision_obj, dict) else None
        basis_hash = str(bh).strip().lower() if bh and _is_sha256_hex(bh) else None
        return d, basis_hash

    def _calc_amount_by_type(self, exc_type: str, detect_data: Dict[str, Any], total_fee: Decimal, segment_fee: Decimal) -> Tuple[Decimal, str]:
        rules = (self.config.get("rules") or {}).get(exc_type) or {}

        if exc_type in {"env_out_of_range", "route_deviation"}:
            refund_rate = Decimal(str(rules.get("refund_rate", 1.0)))
            affected_ratio = detect_data.get("affected_fee_ratio")
            if affected_ratio is None:
                affected_ratio = detect_data.get("segment_fee_ratio")
            ar = Decimal("1.0") if affected_ratio is None else _as_decimal(affected_ratio, field="affected_fee_ratio")
            if ar < Decimal("0"):
                ar = Decimal("0")
            if ar > Decimal("1"):
                ar = Decimal("1")
            amt = _money(segment_fee * ar * refund_rate)
            return amt, f"{exc_type} 退还受影响路段费用（比例{float(ar):.2f}，退费率{float(refund_rate):.2f}）"

        if exc_type == "shipping_delay":
            planned = detect_data.get("planned_arrival")
            actual = detect_data.get("actual_arrival")
            if planned is None or actual is None:
                raise ValueError("延误检测数据需包含 planned_arrival/actual_arrival")
            planned_ts = _require_ms_ts(planned, field="planned_arrival")
            actual_ts = _require_ms_ts(actual, field="actual_arrival")
            delay_ms = max(0, actual_ts - planned_ts)
            delay_hours = Decimal(str(delay_ms)) / Decimal(str(3600 * 1000))

            tiers = rules.get("tiers_hours") or [12, 24, 72]
            tiers_sorted = sorted([int(x) for x in tiers])
            tier = 0
            for t in tiers_sorted:
                if delay_hours >= Decimal(str(t)):
                    tier = t
            if tier == 0:
                return Decimal("0.00"), "未达到延误赔付阈值"

            payout = (rules.get("tier_payout") or {}).get(str(tier)) or {}
            refund_rate = Decimal(str(payout.get("refund_rate", 0)))
            extra_rate = Decimal(str(payout.get("extra_rate", 0)))
            amt = _money(segment_fee * (refund_rate + extra_rate))
            return amt, f"延误{float(delay_hours):.1f}小时，按{tier}h阶梯（退费{float(refund_rate):.2f}+补偿{float(extra_rate):.2f}）"

        if exc_type == "pet_injury":
            severity = _norm_str(detect_data.get("severity") or detect_data.get("injury_level") or "")
            sev = "serious" if ("重" in severity or severity.lower() in {"serious", "heavy"}) else "minor"
            if sev == "minor":
                rate = Decimal(str(rules.get("minor_refund_rate", 0.5)))
                amt = _money(total_fee * rate)
                return amt, "轻微伤：赔付总运费50%"
            med_fee = _as_decimal(detect_data.get("medical_fee") or 0, field="medical_fee")
            rate = Decimal(str(rules.get("serious_refund_rate", 1.0)))
            amt = _money(med_fee + total_fee * rate)
            return amt, "重伤：赔付实际医疗费+总运费100%"

        if exc_type == "pet_death_or_lost":
            market = detect_data.get("market_price")
            if market is not None:
                amt = _money(market)
                return amt, "死亡/丢失：按宠物市场价赔付"
            mul = detect_data.get("multiplier")
            mult = Decimal(str(mul)) if mul is not None else Decimal(str(rules.get("default_multiplier", 3.0)))
            if mult < Decimal("0"):
                mult = Decimal("0")
            amt = _money(total_fee * mult)
            return amt, f"死亡/丢失：按总运费{float(mult):.1f}倍赔付"

        if exc_type == "pet_status_abnormal":
            med_fee = _as_decimal(detect_data.get("medical_fee") or 0, field="medical_fee")
            share = Decimal(str(rules.get("medical_share_rate", 0.5)))
            extra = Decimal(str(rules.get("extra_fee_rate", 0.2)))
            amt = _money(med_fee * share + total_fee * extra)
            return amt, f"状态异常：医疗费分担{float(share):.2f}+运费补偿{float(extra):.2f}"

        raise ValueError("未知异常类型，无法计算赔付")

    def _judge_is_exception(self, exc_type: str, detect_data: Dict[str, Any], *, order_context: Optional[Dict[str, Any]]) -> Tuple[bool, str]:
        if exc_type == "env_out_of_range":
            temp = detect_data.get("temperature")
            hum = detect_data.get("humidity")
            if temp is None and hum is None:
                return True, "环境异常上报"
            try:
                t = Decimal(str(temp)) if temp is not None else None
                h = Decimal(str(hum)) if hum is not None else None
            except Exception:
                return True, "环境数据异常（格式错误）"
            if t is not None and (t < Decimal("10") or t > Decimal("30")):
                return True, "温度超出安全阈值"
            if h is not None and (h < Decimal("30") or h > Decimal("80")):
                return True, "湿度超出安全阈值"
            return False, "环境参数正常"

        if exc_type == "route_deviation":
            dev = detect_data.get("deviation")
            if dev is None:
                return True, "路线偏离上报"
            km = _float_1dp(dev)
            return (km > 10.0), f"偏离{km:.1f}km"

        if exc_type == "shipping_delay":
            planned = detect_data.get("planned_arrival")
            actual = detect_data.get("actual_arrival")
            if planned is None or actual is None:
                return True, "延误数据不完整"
            planned_ts = _require_ms_ts(planned, field="planned_arrival")
            actual_ts = _require_ms_ts(actual, field="actual_arrival")
            delay_ms = max(0, actual_ts - planned_ts)
            delay_hours = float(Decimal(str(delay_ms)) / Decimal(str(3600 * 1000)))
            return (delay_hours >= 12.0), f"延误{delay_hours:.1f}小时"

        return True, "人工上报异常"

    def _deep_merge(self, base: Dict[str, Any], patch: Dict[str, Any]) -> None:
        for k, v in patch.items():
            if isinstance(v, dict) and isinstance(base.get(k), dict):
                self._deep_merge(base[k], v)  # type: ignore[index]
            else:
                base[k] = v

    def _update_latest_exception(self, order_id: str, *, update: Dict[str, Any]) -> None:
        records = _read_jsonl(self.record_store_path)
        idx = None
        for i in range(len(records) - 1, -1, -1):
            if _norm_str(records[i].get("orderId", "")) == order_id:
                idx = i
                break
        if idx is None:
            return
        records[idx] = self._apply_update(records[idx], update)
        self._rewrite_records(records)

    def _update_exception_by_id(self, exception_id: str, *, update: Dict[str, Any]) -> None:
        records = _read_jsonl(self.record_store_path)
        idx = None
        for i, r in enumerate(records):
            if _norm_str(r.get("exception_id", "")) == exception_id:
                idx = i
                break
        if idx is None:
            return
        records[idx] = self._apply_update(records[idx], update)
        self._rewrite_records(records)

    def _apply_update(self, record: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
        out = dict(record)
        for k, v in update.items():
            out[k] = v
        audit = dict(out.get("audit") or {})
        audit["updatedTs"] = _now_ms()
        out["audit"] = audit
        return out

    def _rewrite_records(self, records: List[Dict[str, Any]]) -> None:
        self.record_store_path.parent.mkdir(parents=True, exist_ok=True)
        self.record_store_path.write_text("", encoding="utf-8")
        for r in records:
            _append_jsonl(self.record_store_path, r)
