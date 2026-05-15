"""PII Vault: 暗号化 at rest + access audit log (internal ADR inherit、 ADR-007 inherit)。

T2 適用: T1 vault pattern を DD document/担当者連絡先 vault に literal 適用。
試作 = Fernet (AES-128-CBC + HMAC-SHA256)、 移植 = SQLCipher / PostgreSQL + KMS。

vault tables (T2 PoC scope):
  - document_pii: DOC-XXXXXX → {raw_description, contact_email, contact_phone, contact_person}
  - chunk_pii_optional: CHK-XXXXXX → {raw_text_with_pii} (PII 高密度 chunk のみ)
  - ddp_contact: DDP-XXXXXX → {representative_name, contact_email, contact_phone}
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path(os.environ.get("DATA_DIR", "./data"))
VAULT_DIR = DATA_DIR / "vault"
AUDIT_DIR = DATA_DIR / "audit"
AUDIT_LOG_PATH = AUDIT_DIR / "access_log.jsonl"


def _get_key() -> bytes:
    """Vault encryption key を env から取得、 無ければ instructive error (試作のみ)."""
    key_str = os.environ.get("VAULT_KEY")
    if not key_str:
        key = Fernet.generate_key()
        raise RuntimeError(
            f"VAULT_KEY 未設定。 .env に下記を追記:\n"
            f"  VAULT_KEY={key.decode()}\n"
            f"(本 key は試作用、 移植時は AWS KMS / Cloud KMS に置換)"
        )
    return key_str.encode()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def emit_audit(action: str, item_id: str, requester: str = "system", reason: str = "") -> None:
    """全 vault access を audit log に append (ADR-007 layer 7)."""
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": _now_iso(),
        "action": action,
        "item_id": item_id,
        "requester": requester,
        "reason": reason,
    }
    with AUDIT_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _vault_file(table: str) -> Path:
    return VAULT_DIR / f"{table}.enc"


def _load_vault(table: str) -> dict[str, dict[str, Any]]:
    path = _vault_file(table)
    if not path.exists():
        return {}
    key = _get_key()
    f = Fernet(key)
    try:
        plaintext = f.decrypt(path.read_bytes()).decode("utf-8")
    except InvalidToken:
        raise RuntimeError(f"VAULT_KEY 不一致、 {path} を復号不能 (key rotate?)")
    records = {}
    for line in plaintext.splitlines():
        if line.strip():
            rec = json.loads(line)
            id_key = _id_key_for_table(table)
            records[rec[id_key]] = rec
    return records


def _save_vault(table: str, records: dict[str, dict[str, Any]]) -> None:
    path = _vault_file(table)
    path.parent.mkdir(parents=True, exist_ok=True)
    key = _get_key()
    f = Fernet(key)
    plaintext = "\n".join(json.dumps(rec, ensure_ascii=False) for rec in records.values())
    path.write_bytes(f.encrypt(plaintext.encode("utf-8")))


def _id_key_for_table(table: str) -> str:
    mapping = {
        "document_pii": "doc_id",
        "chunk_pii_optional": "chunk_id",
        "ddp_contact": "ddp_id",
    }
    return mapping.get(table, "id")


# ─── public API (全 access audit log emit) ──────────────────────


def put_vault(table: str, record: dict[str, Any], requester: str = "system", reason: str = "") -> None:
    id_key = _id_key_for_table(table)
    if id_key not in record:
        raise ValueError(f"record に {id_key} field 必要")
    records = _load_vault(table)
    records[record[id_key]] = record
    _save_vault(table, records)
    emit_audit("PUT", f"{table}:{record[id_key]}", requester, reason)


def get_vault(table: str, item_id: str, requester: str = "system", reason: str = "") -> dict[str, Any] | None:
    emit_audit("GET", f"{table}:{item_id}", requester, reason)
    return _load_vault(table).get(item_id)


def init_vault_from_jsonl(table: str, jsonl_path: Path, requester: str = "init") -> int:
    """合成 PII JSONL → vault 一括 import (初回 setup 用、 試作のみ)."""
    if not jsonl_path.exists():
        return 0
    id_key = _id_key_for_table(table)
    records = {}
    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rec = json.loads(line)
            records[rec[id_key]] = rec
    _save_vault(table, records)
    emit_audit("INIT", f"{table}:bulk", requester, f"loaded {len(records)} from {jsonl_path}")
    return len(records)
