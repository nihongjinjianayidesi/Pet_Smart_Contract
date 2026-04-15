from __future__ import annotations

import json
from pathlib import Path

from .compensation_engine import CompensationEngine, PaymentSimulator
from .evidence_service import EvidenceService
from .fabric_client import InMemoryFabricStub


def main() -> None:
    data_dir = Path.cwd() / "offchain_data"
    data_dir.mkdir(parents=True, exist_ok=True)
    record_path = data_dir / "evidence_records.jsonl"
    case_path = data_dir / "demo_inputs" / "compensation_cases.json"

    fabric = InMemoryFabricStub()
    evidence = EvidenceService(fabric_client=fabric, record_store_path=record_path)
    engine = CompensationEngine(fabric_client=fabric, evidence_service=evidence, payment=PaymentSimulator(merchant_deposit=5000.0, owner_wallet=0.0))

    print("=== 异常赔付演示（模块4）- 固定样例（截图点：终端全流程输出） ===")

    case_data = json.loads(case_path.read_text(encoding="utf-8"))
    order_context = dict(case_data["order_context"])
    case = case_data["cases"][0]
    detect = {
        "orderId": order_context["orderId"],
        "exception_id": case["exception_id"],
        "exception_type": case["exception_type"],
        "detect_data": case["detect_data"],
        "detect_time": case["detect_time"],
    }

    resp = engine.auto_detect(detect, order_context=order_context)
    print("\n1) 异常检测/响应（截图点：异常ID + 证据摘要上链 txId）")
    print(json.dumps(resp, ensure_ascii=False, indent=2))

    exception_id = resp.get("exception_id")
    basis_data = {
        "orderId": order_context["orderId"],
        "exception_id": exception_id,
        **(case.get("basis_data") or {}),
        "ts": 1710000002000,
    }
    basis_hash = evidence.hash_data(basis_data)["hash"]
    decision_in = {"orderId": order_context["orderId"], "decision": "merchant", "basisHash": basis_hash, "ts": 1710000002000, "handler": "regulator"}

    decision = engine.record_decision(decision_in, basis_data=basis_data)
    print("\n2) 责任认定（截图点：RecordDecision 上链 txId + basisHash）")
    print(json.dumps(decision, ensure_ascii=False, indent=2))

    comp = engine.calc_compensation(order_context=order_context, exception_id=str(exception_id), decision=decision.get("data"), ts_ms=1710000003000)
    print("\n3) 赔付计算（截图点：金额 2 位小数 + 规则说明）")
    print(json.dumps(comp, ensure_ascii=False, indent=2))

    amount = comp.get("data", {}).get("amount") or 0
    inst = engine.build_settlement_instruction(orderId=order_context["orderId"], amount=float(amount), basisHash=basis_hash, ts_ms=1710000004000, exception_id=str(exception_id))
    result = engine.execute_settlement(inst)
    print("\n4) 赔付执行（截图点：RecordSettlement 上链 txId + 支付模拟 txId + 余额变化）")
    print(json.dumps({"instruction": inst, "result": result, "balances": {k: float(v) for k, v in engine.payment.balances.items()}}, ensure_ascii=False, indent=2))

    print("\n5) 链上（Stub）查询：订单历史（截图点：history 里能看到 AnchorEvidence/RecordDecision/RecordSettlement）")
    print(json.dumps(fabric.query_history({"orderId": order_context["orderId"]}), ensure_ascii=False, indent=2))

    print("\n6) 异常档案查询（截图点：异常档案 JSON 结构）")
    print(json.dumps(engine.get_exception_archive({"orderId": order_context["orderId"]}), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
