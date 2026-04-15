from __future__ import annotations

import json
from pathlib import Path

from .evidence_service import EvidenceService
from .fabric_client import InMemoryFabricStub


def _write_demo_files(base_dir: Path) -> dict:
    base_dir.mkdir(parents=True, exist_ok=True)

    text_path = base_dir / "demo_text.txt"
    text_path.write_text("宠物托运订单信息：PET-20260501-000001\n", encoding="utf-8")

    # 这里不需要是真正可打开的 JPG/MP4/PDF，只要是“固定的二进制内容文件”即可复现实验哈希与篡改校验。
    photo_path = base_dir / "pet_photo.jpg"
    photo_path.write_bytes(b"\xff\xd8\xff" + b"PETSC_DEMO_PHOTO" + b"\xff\xd9")

    doc_path = base_dir / "handover_certificate.pdf"
    doc_path.write_bytes(b"%PDF-1.4\n% PETSC DEMO PDF\n1 0 obj\n<<>>\nendobj\n%%EOF\n")

    return {
        "text_path": str(text_path),
        "photo_path": str(photo_path),
        "doc_path": str(doc_path),
    }


def main() -> None:
    data_dir = Path.cwd() / "offchain_data"
    record_path = data_dir / "evidence_records.jsonl"
    inputs_dir = data_dir / "demo_inputs"

    files = _write_demo_files(inputs_dir)

    fabric = InMemoryFabricStub()
    svc = EvidenceService(fabric_client=fabric, record_store_path=record_path)

    order_id = "PET-20260501-000001"
    evidence_type = "pet_photo"

    print("=== 1) 同一文件多次计算哈希一致（截图点 A） ===")
    h1 = svc.hash_data(files["photo_path"])
    h2 = svc.hash_data(files["photo_path"])
    print(json.dumps({"run1": h1, "run2": h2, "same": h1["hash"] == h2["hash"]}, ensure_ascii=False, indent=2))

    print("\n=== 2) 上链存证（本地 stub 模拟返回 txId） ===")
    anchored = svc.anchor_hash(
        orderId=order_id,
        evidenceType=evidence_type,
        rawData=files["photo_path"],
        submitter="merchant",
    )
    print(json.dumps(anchored, ensure_ascii=False, indent=2))

    print("\n=== 3) 未篡改：链上哈希 vs 本地哈希 一致（截图点 B-通过） ===")
    ok = svc.verify_hash(
        orderId=order_id,
        evidenceType=evidence_type,
        rawData=files["photo_path"],
        chainHash=anchored["hash"],
    )
    print(json.dumps(ok, ensure_ascii=False, indent=2))

    print("\n=== 4) 篡改文件后再校验：不一致（截图点 C-失败） ===")
    Path(files["photo_path"]).write_bytes(Path(files["photo_path"]).read_bytes() + b"TAMPER")
    bad = svc.verify_hash(
        orderId=order_id,
        evidenceType=evidence_type,
        rawData=files["photo_path"],
        chainHash=anchored["hash"],
    )
    print(json.dumps(bad, ensure_ascii=False, indent=2))

    print("\n=== 5) 查询与导出存证记录（截图点 D 可选） ===")
    q = svc.query_records({"orderId": order_id, "evidenceType": evidence_type}, page=1, pageSize=20)
    print(json.dumps(q, ensure_ascii=False, indent=2))

    exported = svc.export_records_json(data_dir / "evidence_records_export.json", {"orderId": order_id})
    print(json.dumps(exported, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

