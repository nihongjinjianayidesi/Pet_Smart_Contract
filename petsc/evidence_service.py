from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

from .fabric_client import FabricClient


SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")


def _now_ms() -> int:
    return int(time.time() * 1000)


def _is_file_path(s: str) -> bool:
    try:
        return Path(s).exists() and Path(s).is_file()
    except Exception:
        return False


def _stable_json_dumps(obj: Any) -> str:
    """
    用于“JSON对象 → 字符串 → 哈希”的稳定序列化：
    - sort_keys=True：字段顺序固定
    - separators：去掉多余空格
    - ensure_ascii=False：中文不转义，便于论文展示
    """

    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_hex_from_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_hex_from_file(file_path: Union[str, Path], block_size: int) -> str:
    h = hashlib.sha256()
    p = Path(file_path)
    with p.open("rb") as f:
        while True:
            chunk = f.read(block_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


@dataclass
class VerifyRecord:
    ts: int
    isValid: bool
    localHash: str
    chainHash: str


@dataclass
class EvidenceRecord:
    recordId: str
    orderId: str
    evidenceType: str
    hash: str
    rawDataInfo: Dict[str, Any]
    submitter: str
    submitTime: int
    txId: Optional[str] = None
    verifyRecords: List[VerifyRecord] = field(default_factory=list)

    def to_jsonable(self) -> Dict[str, Any]:
        return {
            "recordId": self.recordId,
            "orderId": self.orderId,
            "evidenceType": self.evidenceType,
            "hash": self.hash,
            "rawDataInfo": self.rawDataInfo,
            "submitter": self.submitter,
            "submitTime": self.submitTime,
            "txId": self.txId,
            "verifyRecords": [vr.__dict__ for vr in self.verifyRecords],
        }


HashInput = Union[str, bytes, Dict[str, Any]]


class EvidenceService:
    """
    证据存证与哈希校验通用模块（链下，Python）。

    设计目标：
    - 统一哈希：文本/文件(图片/视频/文档等)均采用 SHA-256，输出 64 位小写 hex
    - 统一上链：封装 AnchorEvidence 入参，调用 FabricClient
    - 统一校验：本地重新计算哈希，并与链上 hash 对比
    - 统一记录：把每次存证与校验过程写入 JSONL 日志，便于追溯与导出
    """

    def __init__(
        self,
        *,
        fabric_client: Optional[FabricClient] = None,
        record_store_path: Optional[Union[str, Path]] = None,
        block_size: int = 4 * 1024 * 1024,
    ) -> None:
        self.fabric_client = fabric_client
        self.block_size = int(block_size)
        if self.block_size <= 0:
            raise ValueError("block_size 必须 > 0")

        self.record_store_path: Optional[Path]
        if record_store_path is None:
            self.record_store_path = None
        else:
            self.record_store_path = Path(record_store_path)
            self.record_store_path.parent.mkdir(parents=True, exist_ok=True)
            if not self.record_store_path.exists():
                self.record_store_path.write_text("", encoding="utf-8")

    def hash_data(self, raw: Union[HashInput, List[HashInput]], ts: Optional[int] = None) -> Any:
        """
        计算单条或批量数据的 SHA-256 哈希。

        输入支持：
        - 文本：str；或 dict（会做稳定 JSON 序列化）
        - 文件：文件路径 str；或 dict {"file_path": "..."}
        - 二进制：bytes
        - 批量：List[上述任意类型]
        """

        if isinstance(raw, list):
            out: List[Dict[str, Any]] = []
            for i, item in enumerate(raw):
                r = self._hash_one(item, ts=ts)
                r["index"] = i
                out.append(r)
            return out
        return self._hash_one(raw, ts=ts)

    def anchor_hash(
        self,
        *,
        orderId: str,
        evidenceType: str,
        rawData: HashInput,
        submitter: str,
        ts: Optional[int] = None,
        signer: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        计算哈希并调用链码 AnchorEvidence 完成上链存证。

        说明：
        - 本函数不上传原文，只上链 hash 与必要索引字段（orderId/evidenceType/ts）。
        - 若未提供 fabric_client，则返回 failed（便于业务模块显式处理）。
        """

        order_id = str(orderId).strip()
        evidence_type = str(evidenceType).strip()
        submitter_ = str(submitter).strip()
        if not order_id:
            return {"status": "failed", "errorMsg": "orderId 不能为空"}
        if not evidence_type:
            return {"status": "failed", "errorMsg": "evidenceType 不能为空"}
        if not submitter_:
            return {"status": "failed", "errorMsg": "submitter 不能为空"}

        submit_ts = int(ts) if ts is not None else _now_ms()
        if submit_ts <= 0:
            return {"status": "failed", "errorMsg": "ts 必须为毫秒级Unix时间戳(>0)"}

        hashed = self._hash_one(rawData, ts=submit_ts)
        h = hashed["hash"]

        chain_req: Dict[str, Any] = {
            "orderId": order_id,
            "evidenceType": evidence_type,
            "hash": h,
            "ts": submit_ts,
        }
        if signer is not None and str(signer).strip():
            chain_req["signer"] = str(signer).strip()

        if self.fabric_client is None:
            self._append_record(
                EvidenceRecord(
                    recordId=uuid.uuid4().hex,
                    orderId=order_id,
                    evidenceType=evidence_type,
                    hash=h,
                    rawDataInfo=hashed.get("rawDataInfo", {}),
                    submitter=submitter_,
                    submitTime=submit_ts,
                    txId=None,
                )
            )
            return {
                "status": "failed",
                "errorMsg": "fabric_client 未配置，无法执行链上存证",
                "hash": h,
                "orderId": order_id,
                "evidenceType": evidence_type,
                "ts": submit_ts,
            }

        resp = self.fabric_client.anchor_evidence(chain_req)
        status = str(resp.get("status", "")).strip() or "failed"
        tx_id = resp.get("txId")
        error_msg = resp.get("errorMsg")

        self._append_record(
            EvidenceRecord(
                recordId=uuid.uuid4().hex,
                orderId=order_id,
                evidenceType=evidence_type,
                hash=h,
                rawDataInfo=hashed.get("rawDataInfo", {}),
                submitter=submitter_,
                submitTime=submit_ts,
                txId=str(tx_id) if tx_id else None,
            )
        )

        out: Dict[str, Any] = {
            "status": status,
            "txId": str(tx_id) if tx_id else None,
            "hash": h,
            "orderId": order_id,
            "evidenceType": evidence_type,
            "ts": submit_ts,
        }
        if status != "success" and error_msg:
            out["errorMsg"] = str(error_msg)
        return out

    def verify_hash(
        self,
        *,
        orderId: str,
        evidenceType: str,
        rawData: HashInput,
        chainHash: str,
        ts: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        完整性校验：本地重新计算 hash，与链上 hash 对比。
        """

        order_id = str(orderId).strip()
        evidence_type = str(evidenceType).strip()
        if not order_id:
            return {"isValid": False, "errorMsg": "orderId 不能为空"}
        if not evidence_type:
            return {"isValid": False, "errorMsg": "evidenceType 不能为空"}

        chain_h = str(chainHash).strip().lower()
        if not SHA256_HEX_RE.match(chain_h):
            return {"isValid": False, "errorMsg": "chainHash 必须为64位小写十六进制SHA-256哈希"}

        check_ts = int(ts) if ts is not None else _now_ms()
        hashed = self._hash_one(rawData, ts=check_ts)
        local_h = hashed["hash"]

        ok = local_h == chain_h
        result = {
            "isValid": ok,
            "localHash": local_h,
            "chainHash": chain_h,
            "data_type": hashed["data_type"],
            "ts": check_ts,
        }

        self._append_verify_record(order_id, evidence_type, chain_h, VerifyRecord(ts=check_ts, isValid=ok, localHash=local_h, chainHash=chain_h))
        return result

    def query_records(
        self,
        query: Dict[str, Any],
        *,
        page: int = 1,
        pageSize: int = 50,
    ) -> Dict[str, Any]:
        """
        查询存证日志（JSONL）。

        query 示例：
        - {"orderId":"xxx","evidenceType":"pet_photo","startTime":..., "endTime":...}

        返回：
        - {"total":N,"page":1,"pageSize":50,"records":[...]}
        """

        if self.record_store_path is None:
            return {"total": 0, "page": page, "pageSize": pageSize, "records": []}

        order_id = str(query.get("orderId", "")).strip()
        evidence_type = str(query.get("evidenceType", "")).strip()
        h = str(query.get("hash", "")).strip().lower()
        start_time = query.get("startTime")
        end_time = query.get("endTime")

        try:
            start_ms = int(start_time) if start_time is not None else None
        except Exception:
            start_ms = None
        try:
            end_ms = int(end_time) if end_time is not None else None
        except Exception:
            end_ms = None

        matched: List[Dict[str, Any]] = []
        for rec in self._iter_records():
            if order_id and rec.get("orderId") != order_id:
                continue
            if evidence_type and rec.get("evidenceType") != evidence_type:
                continue
            if h and rec.get("hash") != h:
                continue
            submit_time = rec.get("submitTime")
            if start_ms is not None and isinstance(submit_time, int) and submit_time < start_ms:
                continue
            if end_ms is not None and isinstance(submit_time, int) and submit_time > end_ms:
                continue
            matched.append(rec)

        total = len(matched)
        p = max(1, int(page))
        ps = max(1, int(pageSize))
        start = (p - 1) * ps
        end = start + ps
        return {"total": total, "page": p, "pageSize": ps, "records": matched[start:end]}

    def export_records_json(self, out_path: Union[str, Path], query: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        导出查询结果为 JSON 文件（便于论文附录/追溯）。
        """

        q = query or {}
        res = self.query_records(q, page=1, pageSize=10_000_000)
        p = Path(out_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(res["records"], ensure_ascii=False, indent=2), encoding="utf-8")
        return {"status": "success", "path": str(p), "count": res["total"]}

    def _hash_one(self, raw: HashInput, ts: Optional[int]) -> Dict[str, Any]:
        if raw is None:
            raise ValueError("rawData 不能为空")

        if isinstance(raw, (bytes, bytearray)):
            h = _sha256_hex_from_bytes(bytes(raw))
            return {"hash": h, "data_type": "file", "ts": int(ts) if ts is not None else _now_ms(), "rawDataInfo": {"type": "bytes", "size": len(raw)}}

        if isinstance(raw, str):
            s = raw
            if _is_file_path(s):
                p = Path(s)
                h = _sha256_hex_from_file(p, block_size=self.block_size)
                return {
                    "hash": h,
                    "data_type": "file",
                    "ts": int(ts) if ts is not None else _now_ms(),
                    "rawDataInfo": {"type": "file", "fileName": p.name, "filePath": str(p), "size": p.stat().st_size, "ext": p.suffix.lower()},
                }
            b = s.encode("utf-8")
            h = _sha256_hex_from_bytes(b)
            return {"hash": h, "data_type": "text", "ts": int(ts) if ts is not None else _now_ms(), "rawDataInfo": {"type": "text", "encoding": "utf-8", "size": len(b)}}

        if isinstance(raw, dict):
            if "file_path" in raw:
                fp = str(raw.get("file_path", "")).strip()
                if not fp:
                    raise ValueError("file_path 不能为空")
                if not _is_file_path(fp):
                    raise FileNotFoundError(f"文件不存在: {fp}")
                p = Path(fp)
                h = _sha256_hex_from_file(p, block_size=self.block_size)
                return {
                    "hash": h,
                    "data_type": "file",
                    "ts": int(ts) if ts is not None else _now_ms(),
                    "rawDataInfo": {
                        "type": "file",
                        "fileName": p.name,
                        "filePath": str(p),
                        "size": p.stat().st_size,
                        "ext": p.suffix.lower(),
                        "fileType": raw.get("file_type"),
                    },
                }
            if "text" in raw:
                encoding = str(raw.get("encoding", "utf-8")).strip() or "utf-8"
                text = raw.get("text")
                if text is None:
                    raise ValueError("text 不能为空")
                b = str(text).encode(encoding)
                h = _sha256_hex_from_bytes(b)
                return {"hash": h, "data_type": "text", "ts": int(ts) if ts is not None else _now_ms(), "rawDataInfo": {"type": "text", "encoding": encoding, "size": len(b)}}

            # 其他 dict 默认按“JSON对象”处理：稳定序列化后做哈希
            s = _stable_json_dumps(raw)
            b = s.encode("utf-8")
            h = _sha256_hex_from_bytes(b)
            return {"hash": h, "data_type": "text", "ts": int(ts) if ts is not None else _now_ms(), "rawDataInfo": {"type": "json", "encoding": "utf-8", "size": len(b)}}

        raise TypeError(f"不支持的数据类型: {type(raw).__name__}")

    def _append_record(self, record: EvidenceRecord) -> None:
        if self.record_store_path is None:
            return
        line = json.dumps(record.to_jsonable(), ensure_ascii=False, separators=(",", ":"))
        with self.record_store_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def _append_verify_record(self, order_id: str, evidence_type: str, chain_hash: str, vr: VerifyRecord) -> None:
        """
        为简化实现，这里采用“追加型更新”：
        - 若找到匹配记录：追加一条 verifyRecords 事件（写为单独一行的 verify_event）
        - 查询时会把 verify_event 合并进对应 record（见 _iter_records）

        好处：JSONL 不需要随机写回/覆盖，避免并发与截断风险。
        """

        if self.record_store_path is None:
            return
        verify_event = {
            "_kind": "verify_event",
            "orderId": order_id,
            "evidenceType": evidence_type,
            "chainHash": chain_hash,
            "verify": vr.__dict__,
        }
        line = json.dumps(verify_event, ensure_ascii=False, separators=(",", ":"))
        with self.record_store_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def _iter_records(self) -> Iterable[Dict[str, Any]]:
        """
        读取 JSONL 并合并 verify_event 到对应 record。
        """

        if self.record_store_path is None or not self.record_store_path.exists():
            return []

        records: List[Dict[str, Any]] = []

        with self.record_store_path.open("r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s:
                    continue
                try:
                    obj = json.loads(s)
                except Exception:
                    continue

                if isinstance(obj, dict) and obj.get("_kind") == "verify_event":
                    o = obj.get("orderId")
                    t = obj.get("evidenceType")
                    ch = obj.get("chainHash")
                    v = obj.get("verify")
                    if not (isinstance(o, str) and isinstance(t, str) and isinstance(ch, str) and isinstance(v, dict)):
                        continue
                    ch = ch.lower()
                    # 合并策略：匹配同一 orderId/evidenceType/hash 的“最近一次存证记录”
                    # 由于 recordId 不在 verify_hash 入参里，这里用 (orderId,evidenceType,hash) 进行归并。
                    candidates = [r for r in records if r.get("orderId") == o and r.get("evidenceType") == t and r.get("hash") == ch]
                    if candidates:
                        candidates[-1].setdefault("verifyRecords", []).append(v)
                    continue

                if isinstance(obj, dict) and "recordId" in obj:
                    records.append(obj)
                    continue

        return records
