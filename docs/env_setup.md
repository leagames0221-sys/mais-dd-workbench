# env_setup — mais-dd-workbench

> Security Master Layer 1 (.env block) のため `.env.example` ファイル commit 不可。
> 本 doc を .env template として参照、 user が `.env` を手動作成。

---

## .env template (本 file を copy → `.env` 作成、 git commit 禁止)

```
# Vault encryption key (Fernet AES-256、 試作 = dev key、 移植時 KMS)
# 生成 commandlet: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
VAULT_KEY=<here>

# Session secret (Starlette SessionMiddleware HS256、 試作 = dev key、 移植時 RS256+KMS)
# 生成 commandlet: python -c "import secrets; print(secrets.token_urlsafe(32))"
SESSION_SECRET=<here>

# Synthetic VDR data seed (reproducibility 確保)
SYNTHETIC_SEED=20260512

# LLM provider (試作 = mock、 移植時 = gemini / claude / ollama に swap)
LLM_PROVIDER=mock

# Anthropic API key (Stage 5 LLM listwise rerank、 試作期間中 unused、 移植時 active)
# ANTHROPIC_API_KEY=
```

---

## 設定手順

```powershell
# 1. venv 作成 + activate
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Week 0 deps install
pip install -r requirements-week0.txt

# 3. .env 作成 (上記 template を notepad で literal copy → 値生成 → 保存)
notepad .env

# 4. 起動 smoke (Week 1+ で実装)
# python -m src.api.app
```

---

## 注意

- `.env` は `.gitignore` で literal block 済 (Security Master Layer 1)
- VAULT_KEY 紛失 = vault DB 復号不能 (試作 = data/vault/*.enc literal 再生成、 移植時 KMS rotation 設計必要)
- 移植時の VAULT_KEY rotation path = internal ADR inherit (KMS envelope key)、 ADR-100+ で T2 固有部分起草
