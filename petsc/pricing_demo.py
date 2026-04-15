from __future__ import annotations

import json
from pathlib import Path

from .evidence_service import EvidenceService
from .fabric_client import InMemoryFabricStub
from .pricing_engine import PricingEngine


def _demo_case_fixed() -> dict:
    return {
        "pet_type": "法斗",
        "weight": 9.6,
        "start": "北京",
        "end": "上海",
        "transport_type": "航空",
        "distance_km": 1213,
        "pickup_distance_km": 80,
        "cage": {"type": "2", "self_provided": False},
        "insurance_premium": 30,
        "value_added": ["喂食服务", "视频加频"],
    }


def main() -> None:
    data_dir = Path.cwd() / "offchain_data"
    data_dir.mkdir(parents=True, exist_ok=True)
    record_path = data_dir / "evidence_records.jsonl"

    engine = PricingEngine()
    fabric = InMemoryFabricStub()
    evidence = EvidenceService(fabric_client=fabric, record_store_path=record_path)

    print("=== 自动报价演示（模块2）- 固定样例（截图点：终端费用明细） ===")
    req = _demo_case_fixed()
    quote = engine.generate_quote(req, ts_ms=1710000000000)
    print(quote["text_detail"])
    print("\n报价JSON（可选截图点：结构化输出）")
    print(json.dumps({k: quote[k] for k in ["risk", "fees", "quote_hash"]}, ensure_ascii=False, indent=2))

    print("\n=== 报价摘要 hash 复现校验（模块2 vs 模块5） ===")
    h = evidence.hash_data(quote["quote_hash_payload"])
    print(json.dumps({"engine_quote_hash": quote["quote_hash"], "evidence_hash": h["hash"], "same": h["hash"] == quote["quote_hash"]}, ensure_ascii=False, indent=2))

    print("\n=== 模拟用户确认：生成订单并“上链存证 quoteHash”（截图点：上链返回 txId） ===")
    order_id = engine.generate_order_id(date_yyyymmdd="20260412", seq=1)
    order = engine.create_order(quote=quote, order_id=order_id, ts_ms=1710000001000)
    pet_h = evidence.hash_data(
        {
            "pet_type": quote["input"]["pet_type"],
            "weight": quote["input"]["weight"],
            "start": quote["input"]["start"],
            "end": quote["input"]["end"],
        }
    )["hash"]
    create_order_req = {
        "orderId": order_id,
        "petHash": pet_h,
        "quoteSummary": order["quote_summary"],
        "ts": order["create_time_ms"],
    }
    anchored = evidence.anchor_hash(
        orderId=order_id,
        evidenceType="quote_detail",
        rawData=quote["quote_hash_payload"],
        submitter="user",
        ts=1710000001000,
    )
    print(json.dumps({"order": order, "anchor": anchored, "createOrderRequestJSON": create_order_req}, ensure_ascii=False, indent=2))

    print("\n=== 模拟用户修改后重新报价：把航空改为陆运专车（截图点：对比两次 quoteHash） ===")
    req2 = dict(req)
    req2["transport_type"] = "陆运专车"
    quote2 = engine.generate_quote(req2, ts_ms=1710000002000)
    print(json.dumps({"before": quote["quote_hash"], "after": quote2["quote_hash"], "changed": quote["quote_hash"] != quote2["quote_hash"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
