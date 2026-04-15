from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple


def _now_ms() -> int:
    return int(time.time() * 1000)


def _stable_json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _money(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _money_f(x: Decimal) -> float:
    return float(_money(x))


def _weight_1dp(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def _to_decimal(v: Any, field_name: str) -> Decimal:
    try:
        return Decimal(str(v))
    except Exception:
        raise ValueError(f"{field_name} 必须为数字")


def _norm_str(v: Any) -> str:
    return str(v).strip()


@dataclass(frozen=True)
class RiskResult:
    risk_flag: bool
    risk_type: Optional[str] = None
    suggestion: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        if not self.risk_flag:
            return {"risk_flag": False}
        return {"risk_flag": True, "risk_type": self.risk_type, "suggestion": self.suggestion}


class PricingEngine:
    """
    宠物托运自动报价引擎（链下，Python 标准库实现）。

    核心流程：
    输入托运需求 → 风险识别 → 基础运费计算 → 附加费用计算 → 违约金预留 → 费用明细表 → 报价摘要(hash)
    """

    DEFAULT_CONFIG: Dict[str, Any] = {
        "transport_types": ["航空", "铁路", "陆运专车", "顺风车"],
        "route_distance_km": {
            "北京-上海": 1213,
            "北京-天津": 130,
            "上海-杭州": 180,
            "广州-深圳": 140,
            "成都-重庆": 300,
        },
        "base_fare": {
            "航空": {"base": 80, "per_kg": 6.0, "per_km": 0.80},
            "铁路": {"tiers": [(300, 120), (800, 220), (1500, 350), (10**9, 500)]},
            "陆运专车": {"tiers": [(50, 150), (200, 260), (500, 480), (1000, 800), (10**9, 1200)]},
            "顺风车": {"tiers": [(50, 80), (200, 160), (500, 320), (1000, 520), (10**9, 800)]},
        },
        "pickup_fee": {"free_upto_km": 50, "tier_50_100": 50, "over_100_default": 120},
        "cage_fee": {"1": 30, "2": 50, "3": 80},
        "insurance": {"base_coverage": 2000, "step_premium": 10, "step_coverage": 100},
        "delivery_fee_by_city": {"北京": 30, "上海": 40, "广州": 35, "深圳": 35, "default": 30},
        "addons_fee": {"夏季凉垫": 20, "喂食服务": 30, "视频加频": 15},
        "breach_reserve_rate": 0.10,
        "breach_reserve_min": 1.00,
    }

    SHORT_NOSE_BREEDS = {"法斗", "法国斗牛犬", "英斗", "英国斗牛犬", "巴哥", "加菲猫", "波斯猫"}
    HIGH_STRESS_BREEDS = {"柴犬", "哈士奇", "阿拉斯加", "萨摩耶", "边牧"}

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = self._merge_config(self.DEFAULT_CONFIG, config or {})

    def generate_quote(
        self,
        request: Dict[str, Any],
        *,
        ts_ms: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        生成报价（不包含“上链调用”，只输出标准化 JSON 结果）。
        """

        ts = int(ts_ms) if ts_ms is not None else _now_ms()
        if ts <= 0:
            raise ValueError("ts_ms 必须为毫秒级Unix时间戳(>0)")

        req = self._validate_and_normalize_request(request)
        risk = self.identify_risk(req["pet_type"], transport_type=req["transport_type"])

        base_fee, base_std = self.calc_base_fare(
            transport_type=req["transport_type"],
            weight=req["weight"],
            distance_km=req["distance_km"],
            start=req["start"],
            end=req["end"],
        )

        pickup_fee, pickup_std = self.calc_pickup_fee(req.get("pickup_distance_km"))
        cage_fee, cage_std = self.calc_cage_fee(req.get("cage"))
        insurance_fee, insurance_std, insurance_coverage = self.calc_insurance(req.get("insurance_premium"))
        delivery_fee, delivery_std = self.calc_delivery_fee(
            transport_type=req["transport_type"], end=req["end"], delivery_node=req.get("delivery_node")
        )
        addons_fee, addons_std, addons_chosen = self.calc_addons(req.get("value_added") or [])

        addon_total = _money(pickup_fee + cage_fee + insurance_fee + delivery_fee + addons_fee)
        subtotal = _money(base_fee + addon_total)
        breach_reserve = self.calc_breach_reserve(subtotal)
        total = _money(subtotal + breach_reserve)

        fee_detail = self.build_fee_detail(
            base=(base_fee, base_std),
            pickup=(pickup_fee, pickup_std),
            cage=(cage_fee, cage_std),
            insurance=(insurance_fee, insurance_std),
            delivery=(delivery_fee, delivery_std),
            addons=(addons_fee, addons_std),
            breach=(breach_reserve, f"按总运费的{int(self.config['breach_reserve_rate']*100)}%预留，不足1元按1元"),
        )

        quote_hash, quote_hash_payload = self.compute_quote_hash(
            req=req,
            risk=risk,
            fee_detail=fee_detail,
            totals={
                "base_fee": base_fee,
                "addon_total": addon_total,
                "subtotal": subtotal,
                "breach_reserve": breach_reserve,
                "total": total,
            },
            ts_ms=ts,
            insurance_coverage=insurance_coverage,
            addons_chosen=addons_chosen,
        )

        out = {
            "ts_ms": ts,
            "input": {
                **req,
                "weight": float(req["weight"]),
                "distance_km": int(req["distance_km"]),
            },
            "risk": risk.to_dict(),
            "fees": {
                "base_fee": _money_f(base_fee),
                "addon_total": _money_f(addon_total),
                "breach_reserve": _money_f(breach_reserve),
                "total_fee": _money_f(total),
            },
            "fee_detail": fee_detail,
            "quote_hash": quote_hash,
            "quote_hash_payload": quote_hash_payload,
            "text_detail": self.render_text_detail(
                order_id=None,
                risk=risk,
                fee_detail=fee_detail,
                total_fee=total,
                base_fee=base_fee,
                addon_total=addon_total,
                breach_reserve=breach_reserve,
                insurance_coverage=insurance_coverage,
            ),
        }
        return out

    def generate_order_id(self, *, date_yyyymmdd: Optional[str] = None, seq: Optional[int] = None) -> str:
        """
        订单号格式：PET-YYYYMMDD-XXXXXX
        - seq 提供时可复现实验；不提供则用 sha256 时间戳截断生成 6 位
        """

        if date_yyyymmdd is None:
            t = time.localtime()
            date_yyyymmdd = f"{t.tm_year:04d}{t.tm_mon:02d}{t.tm_mday:02d}"
        s = str(date_yyyymmdd).strip()
        if len(s) != 8 or not s.isdigit():
            raise ValueError("date_yyyymmdd 必须为 YYYYMMDD")

        if seq is not None:
            n = int(seq)
            if n < 0:
                raise ValueError("seq 不能为负数")
            return f"PET-{s}-{n:06d}"

        digest = hashlib.sha256(f"{s}:{_now_ms()}".encode("utf-8")).hexdigest()
        num = int(digest[:12], 16) % 1000000
        return f"PET-{s}-{num:06d}"

    def create_order(
        self,
        *,
        quote: Dict[str, Any],
        order_id: Optional[str] = None,
        ts_ms: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        用户确认后生成“订单对象”（用于对接模块3/链码 CreateOrder）。
        """

        ts = int(ts_ms) if ts_ms is not None else _now_ms()
        if ts <= 0:
            raise ValueError("ts_ms 必须为毫秒级Unix时间戳(>0)")

        if order_id is None:
            order_id = self.generate_order_id()
        order_id = str(order_id).strip()
        if not order_id:
            raise ValueError("order_id 不能为空")

        total_fee = quote.get("fees", {}).get("total_fee")
        quote_hash = quote.get("quote_hash")
        if total_fee is None or quote_hash is None:
            raise ValueError("quote 缺少必要字段：fees.total_fee / quote_hash")

        q = quote.get("input", {})
        summary = (
            f"type={q.get('pet_type')};weight={q.get('weight')}kg;"
            f"distance={q.get('distance_km')}km;transport={q.get('transport_type')};"
            f"total={float(total_fee):.2f};quoteHash={quote_hash}"
        )

        return {
            "orderId": order_id,
            "status": "CONTRACT_EFFECTIVE",
            "quote_summary": summary,
            "total_fee": float(total_fee),
            "quote_hash": str(quote_hash),
            "fee_detail": quote.get("fee_detail", []),
            "create_time_ms": ts,
        }

    def identify_risk(self, pet_type: str, *, transport_type: Optional[str] = None) -> RiskResult:
        name = _norm_str(pet_type)
        risk_types: List[str] = []
        if name in self.SHORT_NOSE_BREEDS:
            risk_types.append("短鼻腔")
        if name in self.HIGH_STRESS_BREEDS:
            risk_types.append("高应激")

        if not risk_types:
            return RiskResult(risk_flag=False)

        suggestion = "建议购买双倍保险"
        if transport_type is not None and str(transport_type).strip() == "航空":
            suggestion = "推荐陆运专车，购买双倍保险"
        return RiskResult(risk_flag=True, risk_type="+".join(risk_types), suggestion=suggestion)

    def calc_base_fare(
        self, *, transport_type: str, weight: Decimal, distance_km: int, start: str, end: str
    ) -> Tuple[Decimal, str]:
        t = _norm_str(transport_type)
        if t not in self.config["transport_types"]:
            raise ValueError(f"transport_type 非法，支持：{self.config['transport_types']}")

        d = int(distance_km)
        if d <= 0:
            raise ValueError("distance_km 必须为正整数")

        if t == "航空":
            rule = self.config["base_fare"]["航空"]
            base = _to_decimal(rule["base"], "航空.base")
            per_kg = _to_decimal(rule["per_kg"], "航空.per_kg")
            per_km = _to_decimal(rule["per_km"], "航空.per_km")
            fee = _money(base + (weight * per_kg) + (Decimal(d) * per_km))
            std = f"航空-按重量+距离计费（{start}→{end} {d}km，{float(weight)}kg）"
            return fee, std

        tiers = list(self.config["base_fare"][t]["tiers"])
        for upper, price in tiers:
            if d <= int(upper):
                fee = _money(_to_decimal(price, "tier_price"))
                std = f"{t}-按里程档位计费（{start}→{end} {d}km）"
                return fee, std
        raise ValueError("基础运费规则表配置错误")

    def calc_pickup_fee(self, pickup_distance_km: Optional[Any]) -> Tuple[Decimal, str]:
        if pickup_distance_km is None:
            return Decimal("0.00"), "未选择接宠"
        d = int(_to_decimal(pickup_distance_km, "pickup_distance_km"))
        if d < 0:
            raise ValueError("pickup_distance_km 不能为负数")

        rule = self.config["pickup_fee"]
        free_upto = int(rule["free_upto_km"])
        if d <= free_upto:
            return Decimal("0.00"), f"接宠费：0-{free_upto}km 免费"
        if d <= 100:
            fee = _money(_to_decimal(rule["tier_50_100"], "pickup_fee.tier_50_100"))
            return fee, "接宠费：50-100km 50元"
        default_fee = _money(_to_decimal(rule["over_100_default"], "pickup_fee.over_100_default"))
        return default_fee, "接宠费：100km以上 协商价（默认值）"

    def calc_cage_fee(self, cage: Optional[Any]) -> Tuple[Decimal, str]:
        if cage is None:
            return Decimal("0.00"), "笼具：未选择（默认自备）"

        if isinstance(cage, dict):
            if bool(cage.get("self_provided")):
                return Decimal("0.00"), "笼具：自备"
            cage_type = _norm_str(cage.get("type"))
        else:
            cage_type = _norm_str(cage)
            if cage_type in {"自备", "自备笼具", "self"}:
                return Decimal("0.00"), "笼具：自备"

        m = self.config["cage_fee"]
        if cage_type not in m:
            raise ValueError("笼具规格非法，支持：1/2/3 或 自备")
        fee = _money(_to_decimal(m[cage_type], "cage_fee"))
        return fee, f"笼具费：{cage_type}号箱"

    def calc_insurance(self, insurance_premium: Optional[Any]) -> Tuple[Decimal, str, int]:
        premium = Decimal("0.00") if insurance_premium is None else _money(_to_decimal(insurance_premium, "insurance_premium"))
        if premium < 0:
            raise ValueError("insurance_premium 不能为负数")

        rule = self.config["insurance"]
        base_cov = int(rule["base_coverage"])
        step_prem = _to_decimal(rule["step_premium"], "insurance.step_premium")
        step_cov = int(rule["step_coverage"])

        extra_steps = int((premium / step_prem).to_integral_value(rounding="ROUND_FLOOR")) if step_prem > 0 else 0
        coverage = base_cov + extra_steps * step_cov
        std = f"保险：基础保额{base_cov}元（含），每加{float(step_prem)}元加保{step_cov}元，当前保额{coverage}元"
        return _money(premium), std, coverage

    def calc_delivery_fee(self, *, transport_type: str, end: str, delivery_node: Optional[Any]) -> Tuple[Decimal, str]:
        t = _norm_str(transport_type)
        node = _norm_str(delivery_node) if delivery_node is not None else ("机场" if t == "航空" else "车站" if t == "铁路" else "上门")

        if node in {"上门", "无", "none"}:
            return Decimal("0.00"), "提货费：无"

        city = _norm_str(end)
        m = self.config["delivery_fee_by_city"]
        fee = _to_decimal(m.get(city, m.get("default", 0)), "delivery_fee_by_city")
        return _money(fee), f"提货费：按{node}实际收费（{city}）"

    def calc_addons(self, value_added: List[Any]) -> Tuple[Decimal, str, List[str]]:
        chosen: List[str] = []
        total = Decimal("0.00")
        m = self.config["addons_fee"]
        for item in value_added:
            s = _norm_str(item)
            if not s:
                continue
            if s not in m:
                raise ValueError(f"增值服务非法：{s}，支持：{list(m.keys())}")
            chosen.append(s)
            total += _to_decimal(m[s], f"addons_fee.{s}")
        total = _money(total)
        if not chosen:
            return total, "增值服务：无", []
        std = "增值服务：" + "、".join([f"{x}{m[x]}元" for x in chosen])
        return total, std, chosen

    def calc_breach_reserve(self, subtotal: Decimal) -> Decimal:
        rate = _to_decimal(self.config["breach_reserve_rate"], "breach_reserve_rate")
        raw = _money(subtotal * rate)
        min_v = _money(_to_decimal(self.config["breach_reserve_min"], "breach_reserve_min"))
        if raw < min_v:
            return min_v
        return raw

    def build_fee_detail(
        self,
        *,
        base: Tuple[Decimal, str],
        pickup: Tuple[Decimal, str],
        cage: Tuple[Decimal, str],
        insurance: Tuple[Decimal, str],
        delivery: Tuple[Decimal, str],
        addons: Tuple[Decimal, str],
        breach: Tuple[Decimal, str],
    ) -> List[Dict[str, Any]]:
        items: List[Tuple[str, str, Decimal, str]] = [
            ("基础运费", base[1], base[0], "合约签订"),
            ("接宠费", pickup[1], pickup[0], "下单后-揽收前"),
            ("笼具费", cage[1], cage[0], "揽收时"),
            ("保险费", insurance[1], insurance[0], "合约签订"),
            ("提货费", delivery[1], delivery[0], "到达后-交付前"),
            ("增值服务费", addons[1], addons[0], "运输中/交付前"),
            ("违约金预留", breach[1], breach[0], "合约签订-冻结"),
        ]
        out: List[Dict[str, Any]] = []
        for item, standard, amount, trigger in items:
            out.append(
                {
                    "item": item,
                    "standard": standard,
                    "amount": _money_f(amount),
                    "trigger_node": trigger,
                }
            )
        return out

    def compute_quote_hash(
        self,
        *,
        req: Dict[str, Any],
        risk: RiskResult,
        fee_detail: List[Dict[str, Any]],
        totals: Dict[str, Decimal],
        ts_ms: int,
        insurance_coverage: int,
        addons_chosen: List[str],
    ) -> Tuple[str, Dict[str, Any]]:
        prem = _money(_to_decimal(req.get("insurance_premium") or 0, "insurance_premium"))
        payload = {
            "ts_ms": int(ts_ms),
            "input": {
                "pet_type": req["pet_type"],
                "weight": f"{_weight_1dp(req['weight']):f}",
                "start": req["start"],
                "end": req["end"],
                "distance_km": int(req["distance_km"]),
                "transport_type": req["transport_type"],
                "pickup_distance_km": req.get("pickup_distance_km"),
                "cage": req.get("cage"),
                "insurance_premium": f"{prem:f}",
                "insurance_coverage": int(insurance_coverage),
                "value_added": list(addons_chosen),
            },
            "risk": risk.to_dict(),
            "fee_detail": [
                {
                    "item": x["item"],
                    "standard": x["standard"],
                    "amount": f"{Decimal(str(x['amount'])).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):f}",
                    "trigger_node": x["trigger_node"],
                }
                for x in fee_detail
            ],
            "total_fee": f"{_money(totals['total']):f}",
        }
        raw = _stable_json_dumps(payload).encode("utf-8")
        return hashlib.sha256(raw).hexdigest(), payload

    def render_text_detail(
        self,
        *,
        order_id: Optional[str],
        risk: RiskResult,
        fee_detail: List[Dict[str, Any]],
        total_fee: Decimal,
        base_fee: Decimal,
        addon_total: Decimal,
        breach_reserve: Decimal,
        insurance_coverage: int,
    ) -> str:
        lines: List[str] = []
        if order_id:
            lines.append(f"订单号：{order_id}")
        if risk.risk_flag:
            lines.append(f"风险提示：{risk.risk_type}；建议：{risk.suggestion}")
        else:
            lines.append("风险提示：无")
        lines.append("")
        lines.append("费用明细表：")
        lines.append("-" * 72)
        lines.append(f"{'项目':<12}{'金额(元)':>12}  {'计费标准':<40}  {'触发节点'}")
        lines.append("-" * 72)
        for x in fee_detail:
            lines.append(f"{x['item']:<12}{x['amount']:>12.2f}  {x['standard']:<40}  {x['trigger_node']}")
        lines.append("-" * 72)
        lines.append(f"基础运费：{_money_f(base_fee):.2f}  附加费用合计：{_money_f(addon_total):.2f}  违约金预留：{_money_f(breach_reserve):.2f}")
        lines.append(f"保险保额：{insurance_coverage} 元")
        lines.append(f"报价总额：{_money_f(total_fee):.2f} 元")
        return "\n".join(lines)

    def _validate_and_normalize_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(request, dict):
            raise ValueError("输入必须为 dict")

        pet_type = _norm_str(request.get("pet_type"))
        if not pet_type:
            raise ValueError("pet_type 不能为空")

        start = _norm_str(request.get("start"))
        end = _norm_str(request.get("end"))
        if not start:
            raise ValueError("start 不能为空")
        if not end:
            raise ValueError("end 不能为空")

        transport_type = _norm_str(request.get("transport_type"))
        if transport_type not in self.config["transport_types"]:
            raise ValueError(f"transport_type 非法，支持：{self.config['transport_types']}")

        weight = _weight_1dp(_to_decimal(request.get("weight"), "weight"))
        if weight <= 0:
            raise ValueError("weight 必须为正数")

        distance_raw = request.get("distance_km")
        if distance_raw is None:
            distance_km = self._lookup_distance_km(start, end)
        else:
            distance_km = int(_to_decimal(distance_raw, "distance_km"))
        if distance_km <= 0:
            raise ValueError("distance_km 必须为正整数")

        pickup_distance_km = request.get("pickup_distance_km")
        if pickup_distance_km is not None:
            pickup_distance_km = int(_to_decimal(pickup_distance_km, "pickup_distance_km"))
            if pickup_distance_km < 0:
                raise ValueError("pickup_distance_km 不能为负数")

        cage = request.get("cage")
        insurance_premium = request.get("insurance_premium")
        if insurance_premium is not None:
            insurance_premium = float(_money(_to_decimal(insurance_premium, "insurance_premium")))
            if insurance_premium < 0:
                raise ValueError("insurance_premium 不能为负数")

        value_added = request.get("value_added")
        if value_added is None:
            value_added_list: List[str] = []
        elif isinstance(value_added, list):
            value_added_list = [_norm_str(x) for x in value_added if _norm_str(x)]
        else:
            raise ValueError("value_added 必须为列表")

        delivery_node = request.get("delivery_node")
        if delivery_node is not None and not _norm_str(delivery_node):
            delivery_node = None

        return {
            "pet_type": pet_type,
            "weight": weight,
            "start": start,
            "end": end,
            "distance_km": distance_km,
            "transport_type": transport_type,
            "pickup_distance_km": pickup_distance_km,
            "cage": cage,
            "insurance_premium": insurance_premium,
            "value_added": value_added_list,
            "delivery_node": delivery_node,
        }

    def _lookup_distance_km(self, start: str, end: str) -> int:
        key = f"{start}-{end}"
        rev = f"{end}-{start}"
        m = self.config.get("route_distance_km") or {}
        if key in m:
            return int(m[key])
        if rev in m:
            return int(m[rev])
        raise ValueError("distance_km 缺失，且未命中内置起终点里程表；请在输入中补充 distance_km")

    def _merge_config(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for k, v in base.items():
            if isinstance(v, dict):
                out[k] = dict(v)
            else:
                out[k] = v
        for k, v in override.items():
            if k in out and isinstance(out[k], dict) and isinstance(v, dict):
                out[k].update(v)
            else:
                out[k] = v
        return out
