# Discovery Brief — mais-dd-workbench (T2 DD 自動化)

> Spec-Driven Workflow Stage 1 (Discovery)。 user gate 通過後 Stage 2 (Requirements EARS 形式) へ移行。
> 共通 doctrine は **[mais-deal-matching internal ADR](../../mais-deal-matching/(internal config)/internal_kb/decisionLog.md)** citation reference。

---

## 1. PJ goal (literal、 original proposal § T2 line 362-390 inherit)

中堅日本企業 M&A の DD (デューデリジェンス) 段階で:
- VDR / 共有ドライブ上の Excel / Word / PowerPoint / PDF を **直接 ingestion**
- DD 質問票数百項目に対し **source 文書 link back 付き** で **分単位** で回答
- 中堅日本企業固有 pattern (同族経営 / 名義株 / オーナー私的経費) を AI で surface
- 全 access が改ざん不能 audit log に記録、 「人が verify 可能」 architecture

期待効果: DD 工数 **-50%** ★★★ / DD サイクル **週 → 日** ★★★

---

## 2. user 像 (一次 / 二次)

| user | scope | use case |
|---|---|---|
| **MAIS 営業 / コンサル + (author) (FDE)** | 一次 | 担当 DDP に VDR 文書 upload、 質問票テンプレート選択、 AI 生成回答を review、 source link で chunk verify、 中堅 fit pattern hit を確認、 紹介 / 経営判断材料化 |
| **C&R 顧客 5 万社の事業承継検討企業** | 二次 (移植後) | DD 自己診断、 自社財務 / 法務 risk surface (移植段階の課題) |

---

## 3. core 機能 (original proposal § T2 line 369-374 literal 反映)

### 3.1 Document ingestion (Clarum 式)

- 対応 file 種別: PDF / DOCX / PPTX / XLSX / HTML / image (OCR) / audio (移植段階)
- 抽出単位: chunk (page / cell / bbox / paragraph offset metadata 付き)
- 採用 stack: **Docling (IBM MIT)** + 自前 chunk metadata schema (ADR-102)

### 3.2 財務 DD レポート draft 自動生成 (M's DD 式)

- input: 申告書 / 財務諸表 / 勘定科目内訳明細書 (PDF / Excel)
- output: 財務 DD レポート draft (PDF / Word output、 後で人が編集)
- decomposed stack: SEC filings RAG pattern + Equity Research multi-agent framework (7 financial data type + 11-metric eval) + Finance-LLMs (kennethleungty GitHub) reference + 自前 中堅日本企業 financial pattern detector

### 3.3 Contract clause extraction + DD 質問票自動回答

- 質問票テンプレート: 財務 / 法務 / 事業 の 3 category × 各 100 項目 = **300 項目 default** (M&A PMI 過去案件 + CUAD/ACORD 41 categories から literal 構成)
- 抽出対象 clause (CUAD/ACORD category 例):
  - Change of Control
  - Limitation of Liability
  - Indemnification
  - Most Favored Nation
  - Non-Compete / Non-Solicitation
  - Termination for Convenience
  - Governing Law / Jurisdiction
- 採用 stack: 5-stage hybrid pipeline (T1 ADR-005 literal reuse、 document chunk に適用) + LLMProvider Protocol (MockProvider 試作、 Gemini/Claude/Ollama 移植時 swap)

### 3.4 Citation link back (Clarum 仕様)

- 全 LLM 回答に citation array literal 付与: `[{citation_id, chunk_id, doc_id, page, section_header, snippet, confidence}, ...]`
- UI 上で citation click → chunk 元 doc PDF/Excel の literal 該当 page/cell を highlight 表示
- 採用 stack: **LlamaIndex CitationQueryEngine** + Docling chunk metadata (ADR-102 統合)

### 3.5 中堅日本企業 fit pattern detector (differentiation core)

- 検出 pattern (literal):
  1. **同族経営** (家族親族による役員兼任、 株式集中、 議事録上の議論欠如)
  2. **名義株** (実質所有者と名義人の乖離、 連続性ある譲渡履歴)
  3. **オーナー私的経費** (役員報酬の異常値、 役員貸付金、 私的支出が経費計上)
  4. (他、 ADR-104 で literal 列挙予定 = 関連会社循環取引 / 不明朗な資本取引 / 株主間契約不在 等)
- 採用 stack: regex (高速 first pass) + LLM (確信度判定 + reasoning) hybrid、 past PMI 16 社案件の知見を prompt に literal 反映

---

## 4. data model (Ontology Object Type 7 件、 ADR-105 で literal 確定予定)

| Object Type | scope | DB |
|---|---|---|
| **DDProject** | M&A 案件 1 件 (DDP-XXXXXX) | operational |
| **Document** | source file 1 件 (DOC-XXXXXX、 PDF/Word/PPT/Excel) | operational + DocumentPII (vault) |
| **Chunk** | Docling 抽出 chunk 1 件 (CHK-XXXXXX、 page/bbox/cell/paragraph offset 付き) | operational + ChunkPII (vault、 必要時のみ) |
| **Question** | DD 質問票項目 1 件 (Q-XXXXXX) | operational |
| **Answer** | LLM 生成回答 1 件 (A-XXXXXX、 citation array 付き) | operational |
| **Citation** | Chunk への link back 1 件 (CIT-XXXXXX) | operational |
| **JPPattern** | 中堅日本企業 fit pattern hit 1 件 (JPP-XXXXXX) | operational |

Link Type (literal):
- DDProject 1:N Document
- Document 1:N Chunk
- DDProject 1:N Question (質問票項目 instance)
- Question 1:1 Answer
- Answer 1:N Citation
- Citation N:1 Chunk
- Chunk 1:N JPPattern (1 chunk に複数 pattern hit 可)

---

## 5. 非 scope (本 PoC 期間で扱わない)

- 実 M&A 案件 VDR 連携 (Datasite API / Intralinks API、 移植段階)
- RBAC + IAM + MFA (移植段階)
- multi-tenant (移植段階)
- 自走 outreach / 案件 sourcing agent (T1 / T3 scope)
- 本番 KMS (移植段階、 試作 = .env + Fernet self-managed key)
- 法務 DD の判決 / 判例検索 (T5 PMI knowledge base scope)
- DD 後の Day-1 / 100 日 plan 生成 (T3 scope)
- KPI alert / 月次 PMI monitoring (T4 scope)
- 文書 OCR で複雑な手書き帳票対応 (移植段階、 Docling default は印字対応)

---

## 6. 採用 stack 詳細 (doctrine: prior-art-first、 doctrine: external-source-audit audit 待ち)

| 層 | ひな形 | license | source citation |
|---|---|---|---|
| Document ingestion | Docling (IBM) | MIT | https://www.docling.ai/ , arxiv 2501.17887 (docling>=2.0 で CVE-2026-24009 fix 込み) |
| Citation infra | LlamaIndex CitationQueryEngine | MIT | https://docs.llamaindex.ai/ |
| Contract clause | CUAD (Atticus Project) | CC BY 4.0 | https://www.atticusprojectai.org/cuad |
| Contract clause complex | ACORD dataset | (academic open) | arxiv 2501.06582 |
| Contract benchmark | ContractEval 2026 | (academic) | arxiv 2508.03080 |
| BM25 (Stage 1) | rank_bm25 | Apache-2.0 | https://github.com/dorianbrown/rank_bm25 |
| Dense (Stage 2) | sentence-transformers + multilingual-e5-large | Apache-2.0 | T1 ADR-005 inherit |
| Cross-encoder (Stage 4) | sentence-transformers cross-encoder/ms-marco-MiniLM-L-12-v2 | Apache-2.0 | T1 ADR-005 inherit |
| LLM listwise (Stage 5) | castorini/rank_llm pattern + MockProvider | Apache-2.0 | T1 ADR-005 inherit |
| FAISS index | faiss-cpu | MIT | https://github.com/facebookresearch/faiss |
| Web UI | FastAPI + uvicorn + Jinja2 | MIT | T1 ADR-007 inherit |
| Vault | cryptography (Fernet) | Apache-2.0 | T1 ADR-007 inherit |
| PII redact | regex 高速 first pass + Presidio (移植時 active) | MIT | T1 ADR-007 inherit |
| Financial DD draft | decomposed: SEC filings RAG pattern + Equity Research framework + Finance-LLMs reference | mixed | (ADR-106 で literal 起草) |
| 中堅 fit pattern | MAIS literal 自作 (regex + LLM hybrid) | MAIS 内部 | (ADR-104 で literal 起草) |
| 動画 pipeline | scripts/produce_video.py (T1 完成) literal copy + SCENES edit | (T1 既存) | T1 internal ADR inherit |

---

## 7. 制約 (literal、 doctrine: client-no-recovery 順守)

- **無料 + クレカ不要範囲** literal 順守 (pip OSS + GitHub PRIVATE + Cloudflare quick tunnel + VOICEVOX free + Anthropic API は MockProvider で試作期間中 defer)
- **consumer laptop** で完走 (doctrine: consumer-hw)、 GPU 必須にしない
- **合成 VDR data only**、 実 M&A 契約書 / 実財務諸表 一切扱わない (host PC OK、 移植時 sandbox 化必須)
- **vendor lock-in ZERO** (Anthropic API + OSS only、 Gemini / Claude / Ollama 1 file swap path)
- **個人情報保護法 2026 改正方針 適合** (暗号化 + 仮名加工で漏洩報告義務 ZERO、 internal ADR inherit)

---

## 8. 4-week roadmap (literal)

| Week | scope | deliverable | acceptance |
|---|---|---|---|
| **Week 0** | Spec-Driven Discovery → Requirements (EARS) → Design → Tasks、 GitHub PRIVATE repo + drift CI install、 採用 OSS 5 件 audit gate | internal knowledge base 5 file + scaffold + ADR-100-106 + Tasks | CI 全 green + ADR 7 件 accepted |
| **Week 1** | 合成 VDR data 生成 (PDF/Word/Excel/PPT 各 2 件 × DDP 5 案件 = 計 40 docs、 中堅 fit pattern inject) + Docling ingestion smoke + chunk metadata schema 確立 | 1 commandlet で VDR → chunked text + page/cell/bbox metadata 抽出 | 40 docs ingestion < 10 分、 chunk 抽出率 > 95% (PoC scope、 本番では 500+ docs / 案件) |
| **Week 2** | DD 質問票テンプレート 300 項目 + RAG citation pipeline + 5-stage hybrid retrieval を chunk に literal 適用 | 質問 → 回答 + source 文書 link back smoke | 4 dogfood query で正解 chunk top-5 命中率 > 80% |
| **Week 3** | Contract clause extraction (CUAD/ACORD 41 cat) + 中堅日本企業 fit pattern detector (regex+LLM hybrid) | clause 抽出 + JPPattern surface pipeline | CUAD test set F1 > 0.7 + 中堅 pattern dogfood で 3+ 件 hit |
| **Week 4** | FastAPI/Jinja UI 5 page + Vault Pattern + e2e_smoke + 動画 pipeline (SCENES T2 版) | 配布版 MP4 + 実機 demo (Cloudflare quick tunnel) | 全 endpoint 200 OK、 e2e_smoke 20+ step PASS、 動画 1:30+ 配布 ready |

---

## 9. risk + 対策

| risk | impact | 対策 |
|---|---|---|
| Docling 採用 OSS が pip-audit で CVE 検出 | scaffold 後の install block | doctrine: external-source-audit gate で literal 検証、 fail 時 unstructured.io / pypdf にfallback (適合度 80% 維持で literal 採用可なものに限る、 doctrine: prior-art-first 順守) |
| 合成 VDR data の realism 不足で dogfood が意味なくなる | Week 2-3 で evaluation 不能 | original proposal § T2 line 389 「中堅日本企業の財務・法務には固有のパターン」 を Faker template + LLM 生成で literal 再現、 実 M&A 案件 reference (公開 IR resource) を pattern として参照 |
| 中堅 fit pattern detector の false positive 多発 | MAIS 営業 review の信頼性低下 | regex (高速 first pass、 precision 重視) + LLM (recall 補完 + reasoning) hybrid、 confidence threshold UI 調整 |
| LLM provider 試作期間中 = MockProvider のみで quality 検証不能 | DD 質問 200+ 項目の回答 quality を ★★★ で主張不能 | MockProvider = template + heuristic + 既存 cross-encoder score 流用で `★★` tier、 Week 4 ぎりぎりで Gemini free tier (CC 不要) を user 承認の上 swap 検討 (T1 carryover candidate A と同じ path) |
| internal ADR 修正が全 sibling repo に伝搬不能 | cross-repo SSoT drift | internal ADR 修正時は全 sibling internal knowledge base に carryover entry append (doctrine: handoff-duty)、 cross-repo citation rule literal 順守 |

---

## 10. 次 stage (Requirements、 user gate 通過後)

Discovery brief literal accept 後、 EARS 形式 (`The system shall ... when ...`) で Requirements を起草、 ADR-100 → ADR-101-106 として decisionLog に literal 記録。 主要 Requirements 候補:

1. **R1 (ingestion)**: The system shall ingest PDF/DOCX/PPTX/XLSX files via Docling when uploaded to a DDProject.
2. **R2 (chunk metadata)**: The system shall extract chunk-level metadata (page/cell/bbox/paragraph offset) for every chunk.
3. **R3 (citation)**: The system shall attach a citation array to every LLM-generated answer, linking back to the source chunk.
4. **R4 (clause extraction)**: The system shall extract CUAD/ACORD 41 clause categories from ingested contracts.
5. **R5 (JP pattern)**: The system shall detect JP-specific patterns (family governance / nominee shareholder / owner private expense) with regex + LLM hybrid.
6. **R6 (PII separation)**: The system shall not expose PII fields to embedding/retrieval/LLM layers (path separation, internal ADR inherit).
7. **R7 (audit log)**: The system shall log every PII vault access to append-only audit log.
8. **R8 (5-stage retrieval)**: The system shall retrieve top-K chunks using BM25 + dense + RRF + cross-encoder + LLM listwise (T1 ADR-005 reuse).
9. **R9 (UI)**: The system shall provide FastAPI/Jinja UI for DDP management, question review, answer verification, audit log inspection.
10. **R10 (drift prevention)**: The system shall maintain internal knowledge base 5 file + drift CI + pip-audit + Dependabot from Day 1 (doctrine: drift-prevention).

---

## 11. user gate (本 Discovery brief literal accept 判断)

下記 11 項目に user 承認:
1. ✅ PJ goal (§ 1)
2. ✅ user 像 (§ 2)
3. ✅ core 機能 5 件 (§ 3.1-3.5)
4. ✅ data model 7 Object Type (§ 4)
5. ✅ 非 scope (§ 5)
6. ✅ 採用 stack 17 件 (§ 6、 audit gate 通過済前提)
7. ✅ 制約 (§ 7)
8. ✅ 4-week roadmap + acceptance (§ 8)
9. ✅ risk + 対策 (§ 9)
10. ✅ Requirements 候補 10 件 (§ 10)
11. ✅ Discovery brief literal accept → Requirements stage 移行

不同意 / 追加 / 修正点あれば本 brief を update 後 user 再確認、 OK で Requirements stage 移行。
