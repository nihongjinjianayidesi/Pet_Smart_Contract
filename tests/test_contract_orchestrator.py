from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from petsc.contract_orchestrator import ContractOrchestrator
from petsc.evidence_service import EvidenceService
from petsc.fabric_client import InMemoryFabricStub


class TestContractOrchestrator(unittest.TestCase):
    def _build(self) -> ContractOrchestrator:
        self._tmp = tempfile.TemporaryDirectory()
        base = Path(self._tmp.name)
        fabric = InMemoryFabricStub()
        evidence = EvidenceService(fabric_client=fabric, record_store_path=base / "evidence.jsonl")
        return ContractOrchestrator(
            fabric_client=fabric,
            evidence_service=evidence,
            record_store_path=base / "fulfillment.jsonl",
        )

    def tearDown(self) -> None:
        if hasattr(self, "_tmp"):
            self._tmp.cleanup()

    def test_normal_flow(self) -> None:
        orch = self._build()
        order = {
            "orderId": "PET-20260501-000001",
            "total_fee": 500.00,
            "total_distance_km": 900,
            "status": "CREATED",
            "create_time_ms": 1746220800000,
        }
        orch.register_order(order, ts=order["create_time_ms"])

        r1 = orch.advance_state(
            orderId=order["orderId"],
            current_status="CREATED",
            trigger_data={"signatures_complete": True},
            ts=1746220800000,
        )
        self.assertEqual(r1["trigger_node"], "合约生效")
        self.assertEqual(r1["new_status"], "CREATED")
        self.assertEqual(r1["settlements"][0]["status"], "success")

        r2 = orch.advance_state(
            orderId=order["orderId"],
            current_status="CREATED",
            trigger_data={"gps": {"at_pickup": True}, "user_confirm": True},
            ts=1746220801000,
        )
        self.assertEqual(r2["new_status"], "PICKED_UP")

        r3 = orch.advance_state(
            orderId=order["orderId"],
            current_status="PICKED_UP",
            trigger_data={"departed": True, "env_ok": True},
            ts=1746220802000,
        )
        self.assertEqual(r3["new_status"], "IN_TRANSIT")

        r4 = orch.advance_state(
            orderId=order["orderId"],
            current_status="IN_TRANSIT",
            trigger_data={"gps": {"distance": 300, "total_distance": 900}},
            ts=1746220803000,
        )
        self.assertEqual(r4["trigger_node"], "途中节点1")

        r5 = orch.advance_state(
            orderId=order["orderId"],
            current_status="IN_TRANSIT",
            trigger_data={"gps": {"distance": 600, "total_distance": 900}},
            ts=1746220804000,
        )
        self.assertEqual(r5["trigger_node"], "途中节点2")

        r6a = orch.advance_state(
            orderId=order["orderId"],
            current_status="IN_TRANSIT",
            trigger_data={"arrived": True, "signed": True, "user_confirm": True},
            ts=1746220805000,
        )
        self.assertEqual(r6a["new_status"], "DELIVERED")
        self.assertEqual(len(r6a["settlements"]), 0)

        r6b = orch.advance_state(
            orderId=order["orderId"],
            current_status="DELIVERED",
            trigger_data={},
            ts=1746220805000 + 2 * 60 * 60 * 1000,
        )
        self.assertEqual(r6b["trigger_node"], "到达确认")

        r7 = orch.advance_state(
            orderId=order["orderId"],
            current_status="DELIVERED",
            trigger_data={},
            ts=1746220805000 + 7 * 24 * 60 * 60 * 1000,
        )
        self.assertEqual(r7["new_status"], "COMPLETED")

        rt = orch.get_order_runtime(order["orderId"])
        self.assertAlmostEqual(rt["released_total"], 500.00, places=2)

    def test_dispute_flow(self) -> None:
        orch = self._build()
        order = {
            "orderId": "PET-20260501-000002",
            "total_fee": 500.00,
            "total_distance_km": 900,
            "status": "CREATED",
            "create_time_ms": 1746220800000,
        }
        orch.register_order(order, ts=order["create_time_ms"])
        order_id = order["orderId"]

        orch.advance_state(orderId=order_id, current_status="CREATED", trigger_data={"signatures_complete": True}, ts=1746220800000)
        orch.advance_state(orderId=order_id, current_status="CREATED", trigger_data={"gps": {"at_pickup": True}, "user_confirm": True}, ts=1746220801000)
        orch.advance_state(orderId=order_id, current_status="PICKED_UP", trigger_data={"departed": True, "env_ok": True}, ts=1746220802000)
        orch.advance_state(orderId=order_id, current_status="IN_TRANSIT", trigger_data={"gps": {"distance": 300, "total_distance": 900}}, ts=1746220803000)
        orch.advance_state(orderId=order_id, current_status="IN_TRANSIT", trigger_data={"gps": {"distance": 600, "total_distance": 900}}, ts=1746220804000)
        orch.advance_state(orderId=order_id, current_status="IN_TRANSIT", trigger_data={"arrived": True, "signed": True, "user_confirm": True}, ts=1746220805000)

        d1 = orch.open_dispute(orderId=order_id, reason="宠物状态异常", ts=1746220805000 + 60 * 60 * 1000, evidence={"photo": "tamper"})
        self.assertTrue(d1["dispute_flag"])

        d2 = orch.close_case(
            orderId=order_id,
            decision="承运方责任，按规则退款",
            ts=1746220805000 + 3 * 60 * 60 * 1000,
            basis={"report": "carrier_fault"},
        )
        self.assertFalse(d2["dispute_flag"])

        rt = orch.get_order_runtime(order_id)
        self.assertEqual(rt["status"], "COMPLETED")


if __name__ == "__main__":
    unittest.main()

