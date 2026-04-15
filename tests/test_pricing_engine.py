from __future__ import annotations

import json
import unittest
from pathlib import Path

from petsc.evidence_service import EvidenceService
from petsc.fabric_client import InMemoryFabricStub
from petsc.pricing_engine import PricingEngine


class TestPricingEngine(unittest.TestCase):
    def test_quote_case_1_reproducible(self) -> None:
        base = Path(__file__).resolve().parent.parent
        case_path = base / "offchain_data" / "demo_inputs" / "quote_case_1.json"
        expected_path = base / "offchain_data" / "demo_inputs" / "quote_case_1_expected.json"

        case = json.loads(case_path.read_text(encoding="utf-8"))
        expected = json.loads(expected_path.read_text(encoding="utf-8"))

        engine = PricingEngine()
        quote = engine.generate_quote(case["request"], ts_ms=case["ts_ms"])

        self.assertEqual(quote["risk"], expected["risk"])
        self.assertEqual(quote["fees"], expected["fees"])
        self.assertEqual(quote["fee_detail"], expected["fee_detail"])
        self.assertEqual(quote["quote_hash"], expected["quote_hash"])

        evidence = EvidenceService(fabric_client=InMemoryFabricStub())
        h = evidence.hash_data(quote["quote_hash_payload"])
        self.assertEqual(h["hash"], quote["quote_hash"])

    def test_invalid_transport_type(self) -> None:
        engine = PricingEngine()
        with self.assertRaises(ValueError):
            engine.generate_quote(
                {
                    "pet_type": "柯基",
                    "weight": 10,
                    "start": "北京",
                    "end": "天津",
                    "distance_km": 130,
                    "transport_type": "火箭",
                    "value_added": [],
                }
            )


if __name__ == "__main__":
    unittest.main()

