from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Union


SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")


def now_ms() -> int:
    return int(time.time() * 1000)


def normalize_sha256_hex(h: str) -> str:
    s = str(h).strip().lower()
    if not SHA256_HEX_RE.match(s):
        raise ValueError("hash 必须为 SHA-256 的 64 位小写十六进制字符串")
    return s


def sha256_hex_from_text(text: Union[str, bytes], *, encoding: str = "utf-8") -> str:
    if isinstance(text, bytes):
        b = text
    else:
        b = str(text).encode(encoding)
    return hashlib.sha256(b).hexdigest()


def sha256_hex_from_file(file_path: Union[str, Path], *, block_size: int = 4 * 1024 * 1024) -> str:
    p = Path(file_path)
    if not p.exists() or not p.is_file():
        raise FileNotFoundError(f"文件不存在: {p}")
    if block_size <= 0:
        raise ValueError("block_size 必须 > 0")

    h = hashlib.sha256()
    with p.open("rb") as f:
        while True:
            chunk = f.read(block_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def stable_json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class EvidenceSummary:
    type: str
    hash: str
    ts: int
    uri: str
    signer: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"type": self.type, "hash": self.hash, "ts": self.ts, "uri": self.uri}
        if self.signer:
            d["signer"] = self.signer
        return d


def make_evidence_summary(
    *,
    evidence_type: str,
    h: str,
    ts: Optional[int] = None,
    uri: str = "",
    signer: Optional[str] = None,
) -> EvidenceSummary:
    t = str(evidence_type).strip()
    if not t:
        raise ValueError("evidence_type 不能为空")
    hh = normalize_sha256_hex(h)
    tss = int(ts) if ts is not None else now_ms()
    if tss <= 0:
        raise ValueError("ts 必须为毫秒级 Unix 时间戳(>0)")
    u = str(uri).strip()
    s = str(signer).strip() if signer is not None else None
    return EvidenceSummary(type=t, hash=hh, ts=tss, uri=u, signer=s or None)


def verify_evidence(
    *,
    raw: Union[str, bytes, Dict[str, Any]],
    chain_hash: str,
    encoding: str = "utf-8",
    block_size: int = 4 * 1024 * 1024,
    ts: Optional[int] = None,
) -> Dict[str, Any]:
    ch = normalize_sha256_hex(chain_hash)
    tss = int(ts) if ts is not None else now_ms()

    if isinstance(raw, (bytes, bytearray)):
        local = hashlib.sha256(bytes(raw)).hexdigest()
        data_type = "bytes"
    elif isinstance(raw, str) and Path(raw).exists() and Path(raw).is_file():
        local = sha256_hex_from_file(raw, block_size=block_size)
        data_type = "file"
    elif isinstance(raw, str):
        local = sha256_hex_from_text(raw, encoding=encoding)
        data_type = "text"
    elif isinstance(raw, dict):
        s = stable_json_dumps(raw)
        local = sha256_hex_from_text(s, encoding="utf-8")
        data_type = "json"
    else:
        return {"isValid": False, "reason": "unsupported_raw_type", "ts": tss}

    ok = local == ch
    return {
        "isValid": ok,
        "reason": "ok" if ok else "hash_mismatch",
        "localHash": local,
        "chainHash": ch,
        "data_type": data_type,
        "ts": tss,
    }

