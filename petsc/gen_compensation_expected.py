from __future__ import annotations

import json
import tempfile
from pathlib import Path

from .compensation_engine import CompensationEngine, PaymentSimulator
from .evidence_service import EvidenceService
from .fabric_client import InMemoryFabricStub


def main() -> None:
    base = Path.cwd() / "offchain_data" / "demo_inputs"
    cases = json.loads((base / "compensation_cases.json").read_text(encoding="utf-8"))
    order = cases["order_context"]

    out = {"cases": []}
    for i, c in enumerate(cases["cases"]):
        fabric = InMemoryFabricStub()
        with tempfile.TemporaryDirectory() as td:
            ev_path = str(Path(td) / "evidence_records.jsonl")
            ex_path = str(Path(td) / "exception_records.jsonl")
            evidence = EvidenceService(fabric_client=fabric, record_store_path=ev_path)
            engine = CompensationEngine(
                fabric_client=fabric,
                evidence_service=evidence,
                payment=PaymentSimulator(),
                record_store_path=ex_path,
            )

            detect = {
                "orderId": order["orderId"],
                "exception_id": c["exception_id"],
                "exception_type": c["exception_type"],
                "detect_data": c["detect_data"],
                "detect_time": c["detect_time"],
            }
            engine.auto_detect(detect, order_context=order)

            decision_ts = 1710000002000 + i * 10000
            comp_ts = decision_ts + 1000
            settle_ts = comp_ts + 1000

            basis_data = {"orderId": order["orderId"], "exception_id": c["exception_id"], **(c.get("basis_data") or {}), "ts": decision_ts}
            basis_hash = evidence.hash_data(basis_data)["hash"]

            engine.record_decision(
                {"orderId": order["orderId"], "decision": c["decision"], "basisHash": basis_hash, "ts": decision_ts, "handler": "regulator"},
                basis_data=basis_data,
            )

            comp = engine.calc_compensation(
                order_context=order,
                exception_id=c["exception_id"],
                decision={"orderId": order["orderId"], "decision": c["decision"], "basisHash": basis_hash, "ts": decision_ts, "handler": "regulator"},
                ts_ms=comp_ts,
            )

            amount = comp["data"]["amount"]
            out["cases"].append(
                {
                    "case_id": c["case_id"],
                    "exception_id": c["exception_id"],
                    "decision": {"ts": decision_ts, "basisHash": basis_hash},
                    "compensation": {"ts": comp_ts, "amount": amount},
                    "settlement": {"ts": settle_ts, "amount": amount},
                }
            )

    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
