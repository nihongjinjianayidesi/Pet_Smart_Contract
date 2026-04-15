from __future__ import annotations

import json
from pathlib import Path

from .contract_orchestrator import ContractOrchestrator
from .evidence_service import EvidenceService
from .fabric_client import InMemoryFabricStub


def _fixed_order() -> dict:
    return {
        "orderId": "PET-20260501-000001",
        "total_fee": 500.00,
        "total_distance_km": 900,
        "status": "CREATED",
        "create_time_ms": 1746220800000,
    }


def main() -> None:
    data_dir = Path.cwd() / "offchain_data"
    data_dir.mkdir(parents=True, exist_ok=True)
    evidence_record_path = data_dir / "evidence_records.jsonl"
    fulfill_record_path = data_dir / "fulfillment_records.jsonl"

    fabric = InMemoryFabricStub()
    evidence = EvidenceService(fabric_client=fabric, record_store_path=evidence_record_path)
    orch = ContractOrchestrator(fabric_client=fabric, evidence_service=evidence, record_store_path=fulfill_record_path)

    order = _fixed_order()
    orch.register_order(order, ts=order["create_time_ms"])
    order_id = order["orderId"]

    print("=== 自动履约结算演示（模块3）- 固定样例（建议截图点：每一步输出） ===")
    print("订单运行时状态：")
    print(json.dumps(orch.get_order_runtime(order_id), ensure_ascii=False, indent=2))

    print("\n=== 1) 节点1-合约生效：三方签名完成 -> 冻结100%（截图点 1） ===")
    r1 = orch.advance_state(
        orderId=order_id,
        current_status="CREATED",
        trigger_data={"signatures_complete": True},
        ts=1746220800000,
    )
    print(json.dumps(r1, ensure_ascii=False, indent=2))

    print("\n=== 2) 节点2-接宠确认：到达接宠点+饲主确认 -> 释放20% 并进入 PICKED_UP（截图点 2） ===")
    r2 = orch.advance_state(
        orderId=order_id,
        current_status="CREATED",
        trigger_data={"gps": {"at_pickup": True}, "user_confirm": True},
        ts=1746220801000,
    )
    print(json.dumps(r2, ensure_ascii=False, indent=2))

    print("\n=== 3) 节点3-运输启动：出发+环境正常 -> 释放30% 并进入 IN_TRANSIT（截图点 3） ===")
    r3 = orch.advance_state(
        orderId=order_id,
        current_status="PICKED_UP",
        trigger_data={"departed": True, "env_ok": True},
        ts=1746220802000,
    )
    print(json.dumps(r3, ensure_ascii=False, indent=2))

    print("\n=== 4) 节点4-途中1：完成1/3路程 -> 释放15%（截图点 4） ===")
    r4 = orch.advance_state(
        orderId=order_id,
        current_status="IN_TRANSIT",
        trigger_data={"gps": {"distance": 300, "total_distance": 900}},
        ts=1746220803000,
    )
    print(json.dumps(r4, ensure_ascii=False, indent=2))

    print("\n=== 5) 节点5-途中2：完成2/3路程 -> 释放15%（截图点 5） ===")
    r5 = orch.advance_state(
        orderId=order_id,
        current_status="IN_TRANSIT",
        trigger_data={"gps": {"distance": 600, "total_distance": 900}},
        ts=1746220804000,
    )
    print(json.dumps(r5, ensure_ascii=False, indent=2))

    print("\n=== 6) 到达签收：到达+签收确认 -> 进入 DELIVERED（截图点 6） ===")
    r6a = orch.advance_state(
        orderId=order_id,
        current_status="IN_TRANSIT",
        trigger_data={"arrived": True, "signed": True, "user_confirm": True},
        ts=1746220805000,
    )
    print(json.dumps(r6a, ensure_ascii=False, indent=2))

    print("\n=== 7) 节点6-到达确认：2小时无异议 -> 释放10%（截图点 7） ===")
    r6b = orch.advance_state(
        orderId=order_id,
        current_status="DELIVERED",
        trigger_data={},
        ts=1746220805000 + 2 * 60 * 60 * 1000,
    )
    print(json.dumps(r6b, ensure_ascii=False, indent=2))

    print("\n=== 8) 节点7-合约完结：7天无申诉 -> 释放10%预留 并进入 COMPLETED（截图点 8） ===")
    r7 = orch.advance_state(
        orderId=order_id,
        current_status="DELIVERED",
        trigger_data={},
        ts=1746220805000 + 7 * 24 * 60 * 60 * 1000,
    )
    print(json.dumps(r7, ensure_ascii=False, indent=2))

    print("\n=== 9) 模拟链上查询：QueryOrder / QueryHistory（截图点 9） ===")
    print(json.dumps(fabric.query_order({"orderId": order_id}), ensure_ascii=False, indent=2))
    print(json.dumps(fabric.query_history({"orderId": order_id}), ensure_ascii=False, indent=2))

    print("\n=== 10) 查询链下履约记录（截图点 10 可选） ===")
    print(json.dumps(orch.query_fulfillment_records(orderId=order_id), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

