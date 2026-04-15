import json
import os
import tempfile
import unittest
from pathlib import Path

from petsc.evidence_service import EvidenceService
from petsc.fabric_client import InMemoryFabricStub


class TestEvidenceService(unittest.TestCase):
    def test_text_hash_stable(self):
        svc = EvidenceService()
        r1 = svc.hash_data("hello")
        r2 = svc.hash_data("hello")
        r3 = svc.hash_data("hello!")
        self.assertEqual(r1["hash"], r2["hash"])
        self.assertNotEqual(r1["hash"], r3["hash"])
        self.assertEqual(r1["data_type"], "text")

    def test_json_hash_stable(self):
        svc = EvidenceService()
        a = {"b": 1, "a": 2}
        b = {"a": 2, "b": 1}
        self.assertEqual(svc.hash_data(a)["hash"], svc.hash_data(b)["hash"])

    def test_file_hash_and_tamper(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "x.bin"
            p.write_bytes(b"ABC")
            svc = EvidenceService()
            h1 = svc.hash_data(str(p))["hash"]
            p.write_bytes(b"ABCD")
            h2 = svc.hash_data(str(p))["hash"]
            self.assertNotEqual(h1, h2)

    def test_batch_order(self):
        with tempfile.TemporaryDirectory() as td:
            p1 = Path(td) / "a.txt"
            p2 = Path(td) / "b.txt"
            p1.write_text("A", encoding="utf-8")
            p2.write_text("B", encoding="utf-8")
            svc = EvidenceService()
            res = svc.hash_data([str(p1), str(p2), "C"])
            self.assertEqual([r["index"] for r in res], [0, 1, 2])
            self.assertEqual(res[0]["data_type"], "file")
            self.assertEqual(res[2]["data_type"], "text")

    def test_anchor_and_verify_and_query(self):
        with tempfile.TemporaryDirectory() as td:
            record_path = Path(td) / "records.jsonl"
            p = Path(td) / "photo.jpg"
            p.write_bytes(b"\xff\xd8\xffDEMO\xff\xd9")

            fabric = InMemoryFabricStub()
            svc = EvidenceService(fabric_client=fabric, record_store_path=record_path, block_size=64)

            anchored = svc.anchor_hash(
                orderId="PET-TEST-000001",
                evidenceType="pet_photo",
                rawData=str(p),
                submitter="merchant",
            )
            self.assertEqual(anchored["status"], "success")
            self.assertTrue(anchored["txId"])

            ok = svc.verify_hash(
                orderId="PET-TEST-000001",
                evidenceType="pet_photo",
                rawData=str(p),
                chainHash=anchored["hash"],
            )
            self.assertTrue(ok["isValid"])

            p.write_bytes(p.read_bytes() + b"TAMPER")
            bad = svc.verify_hash(
                orderId="PET-TEST-000001",
                evidenceType="pet_photo",
                rawData=str(p),
                chainHash=anchored["hash"],
            )
            self.assertFalse(bad["isValid"])

            q = svc.query_records({"orderId": "PET-TEST-000001"}, page=1, pageSize=10)
            self.assertGreaterEqual(q["total"], 1)
            self.assertEqual(q["records"][0]["orderId"], "PET-TEST-000001")

            export_path = Path(td) / "export.json"
            exp = svc.export_records_json(export_path, {"orderId": "PET-TEST-000001"})
            self.assertEqual(exp["status"], "success")
            self.assertTrue(export_path.exists())
            exported = json.loads(export_path.read_text(encoding="utf-8"))
            self.assertIsInstance(exported, list)


if __name__ == "__main__":
    unittest.main()

