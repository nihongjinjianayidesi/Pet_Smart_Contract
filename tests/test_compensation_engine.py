from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from petsc.compensation_engine import CompensationEngine, PaymentSimulator
from petsc.evidence_service import EvidenceService
from petsc.fabric_client import InMemoryFabricStub


class TestCompensationEngine(unittest.TestCase):
    def test_compensation_cases_reproducible(self) -> None:
        base = Path(__file__).resolve().parent.parent
        case_path = base / "offchain_data" / "demo_inputs" / "compensation_cases.json"
        expected_path = base / "offchain_data" / "demo_inputs" / "compensation_cases_expected.json"

        cases = json.loads(case_path.read_text(encoding="utf-8"))
        expected = json.loads(expected_path.read_text(encoding="utf-8"))
        expected_by_id = {c["case_id"]: c for c in expected["cases"]}

        order_context = dict(cases["order_context"])

        for c in cases["cases"]:
            with self.subTest(case_id=c["case_id"]):
                exp = expected_by_id[c["case_id"]]

                fabric = InMemoryFabricStub()
                with tempfile.TemporaryDirectory() as td:
                    ev_path = str(Path(td) / "evidence_records.jsonl")
                    ex_path = str(Path(td) / "exception_records.jsonl")
                    evidence = EvidenceService(fabric_client=fabric, record_store_path=ev_path)
                    engine = CompensationEngine(
                        fabric_client=fabric,
                        evidence_service=evidence,
                        payment=PaymentSimulator(merchant_deposit=5000.0, owner_wallet=0.0),
                        record_store_path=ex_path,
                    )

                    detect = {
                        "orderId": order_context["orderId"],
                        "exception_id": c["exception_id"],
                        "exception_type": c["exception_type"],
                        "detect_data": c["detect_data"],
                        "detect_time": c["detect_time"],
                    }
                    r = engine.auto_detect(detect, order_context=order_context)
                    self.assertEqual(r["status"], "success")
                    self.assertTrue(r["is_exception"])
                    self.assertEqual(r["exception_id"], c["exception_id"])

                    basis_data = {"orderId": order_context["orderId"], "exception_id": c["exception_id"], **(c.get("basis_data") or {}), "ts": exp["decision"]["ts"]}
                    basis_hash = evidence.hash_data(basis_data)["hash"]
                    decision_in = {
                        "orderId": order_context["orderId"],
                        "decision": c["decision"],
                        "basisHash": basis_hash,
                        "ts": exp["decision"]["ts"],
                        "handler": "regulator",
                    }
                    decision = engine.record_decision(decision_in, basis_data=basis_data)
                    self.assertEqual(decision["status"], "success")
                    self.assertEqual(decision["data"]["basisHash"], exp["decision"]["basisHash"])

                    comp = engine.calc_compensation(order_context=order_context, exception_id=c["exception_id"], decision=decision["data"], ts_ms=exp["compensation"]["ts"])
                    self.assertEqual(comp["status"], "success")
                    self.assertAlmostEqual(comp["data"]["amount"], exp["compensation"]["amount"], places=2)

                    inst = engine.build_settlement_instruction(
                        orderId=order_context["orderId"],
                        amount=float(comp["data"]["amount"]),
                        basisHash=decision["data"]["basisHash"],
                        ts_ms=exp["settlement"]["ts"],
                        exception_id=c["exception_id"],
                    )
                    res = engine.execute_settlement(inst)
                    self.assertEqual(res["status"], "success")
                    self.assertEqual(res["data"]["payment"]["status"], "success")

                    hist = fabric.query_history({"orderId": order_context["orderId"]})
                    self.assertEqual(hist["status"], "success")
                    kinds = [x.get("kind") for x in hist.get("data", [])]
                    self.assertIn("AnchorEvidence", kinds)
                    self.assertIn("RecordDecision", kinds)
                    self.assertIn("RecordSettlement", kinds)


if __name__ == "__main__":
    unittest.main()
