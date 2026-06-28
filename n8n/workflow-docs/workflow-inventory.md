# Đối chiếu 14 workflow TKTL với n8n live

**Thời điểm chụp:** 2026-06-29 · **Chế độ:** chỉ đọc · **Phạm vi:** đúng TKTL WF-01…WF-14

JSON canonical trong `n8n/workflows/` đại diện cho **activeVersion đang chạy**, không phải draft chưa publish. Mỗi file đặt `active: false` để import không tự kích hoạt. So sánh graph bỏ qua trường `credentials` vì MCP sanitize trường này và chuẩn hóa đúng hai placeholder secret đã ghi trong manifest.

| WF | ID live | Published | Draft version | Active version | Node/cạnh | Webhook | JWT Cách B | Kết quả |
|---|---|---:|---|---|---:|---|---|---|
| 01 | `1VrdYDoQ8zqEnWdD` | Có | `025604bc-927b-4b2c-a473-74b79c5ce00b` | `025604bc-927b-4b2c-a473-74b79c5ce00b` | 20/20 | `POST ingest-document` | PASS | MATCHED_ACTIVE_GRAPH |
| 02 | `nZA5xAnubald5h5Q` | Có | `767e4afb-aad9-4019-ac86-befd3a91cdc5` | `767e4afb-aad9-4019-ac86-befd3a91cdc5` | 26/27 | `POST rag-query` | PASS | MATCHED_ACTIVE_GRAPH |
| 03 | `Nya2cM5pHbCvzr7Y` | Có | `66c5e44a-0859-44b9-a868-e5936aa0d13e` | `66c5e44a-0859-44b9-a868-e5936aa0d13e` | 14/14 | `POST draft-protocol` | PASS | MATCHED_ACTIVE_GRAPH |
| 04 | `lXWCvmXltec0RTgo` | Có | `fb751091-66e1-4324-ba60-9757a3283692` | `fb751091-66e1-4324-ba60-9757a3283692` | 14/14 | `POST check-protocol` | PASS | MATCHED_ACTIVE_GRAPH |
| 05 | `CPh7Z1g4EwyOrVo0` | Có | `1a3919c5-59cb-4127-a09e-6460084b991a` | `1a3919c5-59cb-4127-a09e-6460084b991a` | 14/14 | `POST calculate-report` | PASS | MATCHED_ACTIVE_GRAPH |
| 06 | `o4fuUanxRrD7qQoG` | Có | `f7b7ee5a-870b-446d-9a1e-e06ff1f4fe22` | `f7b7ee5a-870b-446d-9a1e-e06ff1f4fe22` | 9/9 | `POST search-docs` | PASS | MATCHED_ACTIVE_GRAPH |
| 07 | `KFvOoabtnptFghSy` | Có | `8f2d714c-48eb-4d00-8316-7fae6f40007f` | `8f2d714c-48eb-4d00-8316-7fae6f40007f` | 12/12 | `POST approve-document` | PASS | MATCHED_ACTIVE_GRAPH |
| 08 | `5wwaxP51FgeXuDi3` | Có | `821c2f84-221c-4bae-a6d3-c881c8b0aa20` | `821c2f84-221c-4bae-a6d3-c881c8b0aa20` | 5/4 | `GET health` | N/A (health public) | MATCHED_ACTIVE_GRAPH |
| 09 | `old58Th1kWOvMcTp` | Có | `c03ee46b-2ccb-49ae-b265-ba0dd284c5f5` | `c03ee46b-2ccb-49ae-b265-ba0dd284c5f5` | 20/21 | `POST ingest-web` | PASS | MATCHED_ACTIVE_GRAPH |
| 10 | `nFYb0JyZ6MZf5OVR` | Có | `f0e0de35-1577-4bd4-9468-fcde186016bc` | `f0e0de35-1577-4bd4-9468-fcde186016bc` | 15/18 | `POST gmp-upload` | PASS | MATCHED_ACTIVE_GRAPH |
| 11 | `yrLN2Y5tEC8jJwGR` | Có | `bad508fe-756e-42e5-b6e5-19786d97e6f8` | `bad508fe-756e-42e5-b6e5-19786d97e6f8` | 23/25 | `POST literature-search` | PASS | MATCHED_ACTIVE_GRAPH |
| 12 | `DMcZCeYXTFRUyufV` | Có | `8d6c7110-f951-49e7-a238-e81520aeaa57` | `8d6c7110-f951-49e7-a238-e81520aeaa57` | 16/16 | `POST assistant-query` | PASS | MATCHED_ACTIVE_GRAPH |
| 13 | `TcusASYdTTHaoygD` | Có | `ce4f4ce7-731e-4e95-8fc1-e0ba83816315` | `ce4f4ce7-731e-4e95-8fc1-e0ba83816315` | 18/23 | `POST copilot-query` | PASS | MATCHED_ACTIVE_GRAPH |
| 14 | `6USn5CYpK9VlyExu` | Có | `f432217d-c329-45cd-90a7-2a0055719549` | `70afe9fe-2325-4413-a1b1-860f0c05cb2f` | 15/14 | `POST web-search` | FAIL (thiếu onError) | KNOWN_LIVE_DRIFT |

## WF-01 — TKTL WF-01 Document Ingest

- File: `n8n/workflows/TKTL-WF-01-document-ingest.json`
- ID: `1VrdYDoQ8zqEnWdD`
- Version: draft `025604bc-927b-4b2c-a473-74b79c5ce00b`; active `025604bc-927b-4b2c-a473-74b79c5ce00b`
- Webhook: `POST /webhook/ingest-document`
- Credential binding trong export: `PG: Get User Roles → GMP-check`, `PG: Check Duplicate → GMP-check`, `PG: Create Document → GMP-check`, `OpenAI: Embedding → OpenAl`, `PG: Insert Chunks + Update + Audit → GMP-check`
- JWT: GET `/auth/v1/user`, token từ header, apikey=có (đã redaction), onError=continueErrorOutput

### Node graph active

| # | Node | Type |
|---:|---|---|
| 1 | Webhook Ingest | `n8n-nodes-base.webhook` |
| 2 | 🔐 Verify JWT | `n8n-nodes-base.httpRequest` |
| 3 | Parse + Validate + Hash | `n8n-nodes-base.code` |
| 4 | Input OK? | `n8n-nodes-base.if` |
| 5 | Error Response | `n8n-nodes-base.respondToWebhook` |
| 6 | PG: Get User Roles | `n8n-nodes-base.postgres` |
| 7 | Check Upload Permission | `n8n-nodes-base.code` |
| 8 | Permission OK? | `n8n-nodes-base.if` |
| 9 | Permission Denied | `n8n-nodes-base.respondToWebhook` |
| 10 | PG: Check Duplicate | `n8n-nodes-base.postgres` |
| 11 | Process Dup Result | `n8n-nodes-base.code` |
| 12 | Duplicate? | `n8n-nodes-base.if` |
| 13 | Duplicate Response | `n8n-nodes-base.respondToWebhook` |
| 14 | PG: Create Document | `n8n-nodes-base.postgres` |
| 15 | Extract + Chunk | `n8n-nodes-base.code` |
| 16 | OpenAI: Embedding | `n8n-nodes-base.httpRequest` |
| 17 | Build Insert SQL | `n8n-nodes-base.code` |
| 18 | PG: Insert Chunks + Update + Audit | `n8n-nodes-base.postgres` |
| 19 | Success Response | `n8n-nodes-base.respondToWebhook` |
| 20 | Auth 401 | `n8n-nodes-base.code` |

### Connections active

- `Webhook Ingest` [main:0] → `🔐 Verify JWT` [input:0]
- `Parse + Validate + Hash` [main:0] → `Input OK?` [input:0]
- `Input OK?` [main:0] → `Error Response` [input:0]
- `Input OK?` [main:1] → `PG: Get User Roles` [input:0]
- `PG: Get User Roles` [main:0] → `Check Upload Permission` [input:0]
- `Check Upload Permission` [main:0] → `Permission OK?` [input:0]
- `Permission OK?` [main:0] → `Permission Denied` [input:0]
- `Permission OK?` [main:1] → `PG: Check Duplicate` [input:0]
- `PG: Check Duplicate` [main:0] → `Process Dup Result` [input:0]
- `Process Dup Result` [main:0] → `Duplicate?` [input:0]
- `Duplicate?` [main:0] → `Duplicate Response` [input:0]
- `Duplicate?` [main:1] → `PG: Create Document` [input:0]
- `PG: Create Document` [main:0] → `Extract + Chunk` [input:0]
- `Extract + Chunk` [main:0] → `OpenAI: Embedding` [input:0]
- `OpenAI: Embedding` [main:0] → `Build Insert SQL` [input:0]
- `Build Insert SQL` [main:0] → `PG: Insert Chunks + Update + Audit` [input:0]
- `PG: Insert Chunks + Update + Audit` [main:0] → `Success Response` [input:0]
- `🔐 Verify JWT` [main:0] → `Parse + Validate + Hash` [input:0]
- `🔐 Verify JWT` [main:1] → `Auth 401` [input:0]
- `Auth 401` [main:0] → `Error Response` [input:0]

## WF-02 — TKTL WF-02 RAG Query

- File: `n8n/workflows/TKTL-WF-02-rag-query.json`
- ID: `nZA5xAnubald5h5Q`
- Version: draft `767e4afb-aad9-4019-ac86-befd3a91cdc5`; active `767e4afb-aad9-4019-ac86-befd3a91cdc5`
- Webhook: `POST /webhook/rag-query`
- Credential binding trong export: `PG: Get User Info → GMP-check`, `OpenAI: Query Expansion → OpenAl`, `OpenAI: Embed Query → OpenAl`, `PG: Hybrid Search → GMP-check`, `OpenAI: Rerank → OpenAl`, `PG: Get System Prompt → GMP-check`, `OpenAI: Chat Answer → OpenAl`, `PG: Save Query + Audit → GMP-check`
- JWT: GET `/auth/v1/user`, token từ header, apikey=có (đã redaction), onError=continueErrorOutput

### Node graph active

| # | Node | Type |
|---:|---|---|
| 1 | Webhook RAG | `n8n-nodes-base.webhook` |
| 2 | Parse + JWT Decode | `n8n-nodes-base.code` |
| 3 | Input OK? | `n8n-nodes-base.if` |
| 4 | Error Response | `n8n-nodes-base.respondToWebhook` |
| 5 | PG: Get User Info | `n8n-nodes-base.postgres` |
| 6 | Check AI Permission | `n8n-nodes-base.code` |
| 7 | Permission OK? | `n8n-nodes-base.if` |
| 8 | Permission Denied | `n8n-nodes-base.respondToWebhook` |
| 9 | OpenAI: Query Expansion | `n8n-nodes-base.httpRequest` |
| 10 | Parse Expansion | `n8n-nodes-base.code` |
| 11 | OpenAI: Embed Query | `n8n-nodes-base.httpRequest` |
| 12 | Build Search SQL | `n8n-nodes-base.code` |
| 13 | PG: Hybrid Search | `n8n-nodes-base.postgres` |
| 14 | Prepare Rerank | `n8n-nodes-base.code` |
| 15 | Has Candidates? | `n8n-nodes-base.if` |
| 16 | OpenAI: Rerank | `n8n-nodes-base.httpRequest` |
| 17 | Apply Rerank | `n8n-nodes-base.code` |
| 18 | Process Search + Build Context | `n8n-nodes-base.code` |
| 19 | PG: Get System Prompt | `n8n-nodes-base.postgres` |
| 20 | Build AI Messages | `n8n-nodes-base.code` |
| 21 | OpenAI: Chat Answer | `n8n-nodes-base.httpRequest` |
| 22 | Format Response + Build Save SQL | `n8n-nodes-base.code` |
| 23 | PG: Save Query + Audit | `n8n-nodes-base.postgres` |
| 24 | RAG Response | `n8n-nodes-base.respondToWebhook` |
| 25 | 🔐 Verify JWT | `n8n-nodes-base.httpRequest` |
| 26 | Auth 401 | `n8n-nodes-base.code` |

### Connections active

- `Webhook RAG` [main:0] → `🔐 Verify JWT` [input:0]
- `Parse + JWT Decode` [main:0] → `Input OK?` [input:0]
- `Input OK?` [main:0] → `Error Response` [input:0]
- `Input OK?` [main:1] → `PG: Get User Info` [input:0]
- `PG: Get User Info` [main:0] → `Check AI Permission` [input:0]
- `Check AI Permission` [main:0] → `Permission OK?` [input:0]
- `Permission OK?` [main:0] → `Permission Denied` [input:0]
- `Permission OK?` [main:1] → `OpenAI: Query Expansion` [input:0]
- `OpenAI: Query Expansion` [main:0] → `Parse Expansion` [input:0]
- `Parse Expansion` [main:0] → `OpenAI: Embed Query` [input:0]
- `OpenAI: Embed Query` [main:0] → `Build Search SQL` [input:0]
- `Build Search SQL` [main:0] → `PG: Hybrid Search` [input:0]
- `PG: Hybrid Search` [main:0] → `Prepare Rerank` [input:0]
- `Prepare Rerank` [main:0] → `Has Candidates?` [input:0]
- `Has Candidates?` [main:0] → `OpenAI: Rerank` [input:0]
- `Has Candidates?` [main:1] → `Process Search + Build Context` [input:0]
- `OpenAI: Rerank` [main:0] → `Apply Rerank` [input:0]
- `Apply Rerank` [main:0] → `Process Search + Build Context` [input:0]
- `Process Search + Build Context` [main:0] → `PG: Get System Prompt` [input:0]
- `PG: Get System Prompt` [main:0] → `Build AI Messages` [input:0]
- `Build AI Messages` [main:0] → `OpenAI: Chat Answer` [input:0]
- `OpenAI: Chat Answer` [main:0] → `Format Response + Build Save SQL` [input:0]
- `Format Response + Build Save SQL` [main:0] → `PG: Save Query + Audit` [input:0]
- `PG: Save Query + Audit` [main:0] → `RAG Response` [input:0]
- `🔐 Verify JWT` [main:0] → `Parse + JWT Decode` [input:0]
- `🔐 Verify JWT` [main:1] → `Auth 401` [input:0]
- `Auth 401` [main:0] → `Error Response` [input:0]

## WF-03 — TKTL WF-03 Draft Protocol

- File: `n8n/workflows/TKTL-WF-03-draft-protocol.json`
- ID: `Nya2cM5pHbCvzr7Y`
- Version: draft `66c5e44a-0859-44b9-a868-e5936aa0d13e`; active `66c5e44a-0859-44b9-a868-e5936aa0d13e`
- Webhook: `POST /webhook/draft-protocol`
- Credential binding trong export: `PG: Load Template + Equipment + Prompt → GMP-check`, `OpenAI: Draft Protocol → OpenAl`, `PG: Save Protocol + Audit → GMP-check`
- JWT: GET `/auth/v1/user`, token từ header, apikey=có (đã redaction), onError=continueErrorOutput

### Node graph active

| # | Node | Type |
|---:|---|---|
| 1 | Webhook Draft | `n8n-nodes-base.webhook` |
| 2 | Parse + Auth | `n8n-nodes-base.code` |
| 3 | OK? | `n8n-nodes-base.if` |
| 4 | Error | `n8n-nodes-base.respondToWebhook` |
| 5 | PG: Load Template + Equipment + Prompt | `n8n-nodes-base.postgres` |
| 6 | Build AI Request | `n8n-nodes-base.code` |
| 7 | Role OK? | `n8n-nodes-base.if` |
| 8 | Role Denied | `n8n-nodes-base.respondToWebhook` |
| 9 | OpenAI: Draft Protocol | `n8n-nodes-base.httpRequest` |
| 10 | Format + Save SQL | `n8n-nodes-base.code` |
| 11 | PG: Save Protocol + Audit | `n8n-nodes-base.postgres` |
| 12 | Draft Response | `n8n-nodes-base.respondToWebhook` |
| 13 | 🔐 Verify JWT | `n8n-nodes-base.httpRequest` |
| 14 | Auth 401 | `n8n-nodes-base.code` |

### Connections active

- `Webhook Draft` [main:0] → `🔐 Verify JWT` [input:0]
- `Parse + Auth` [main:0] → `OK?` [input:0]
- `OK?` [main:0] → `Error` [input:0]
- `OK?` [main:1] → `PG: Load Template + Equipment + Prompt` [input:0]
- `PG: Load Template + Equipment + Prompt` [main:0] → `Build AI Request` [input:0]
- `Build AI Request` [main:0] → `Role OK?` [input:0]
- `Role OK?` [main:0] → `Role Denied` [input:0]
- `Role OK?` [main:1] → `OpenAI: Draft Protocol` [input:0]
- `OpenAI: Draft Protocol` [main:0] → `Format + Save SQL` [input:0]
- `Format + Save SQL` [main:0] → `PG: Save Protocol + Audit` [input:0]
- `PG: Save Protocol + Audit` [main:0] → `Draft Response` [input:0]
- `🔐 Verify JWT` [main:0] → `Parse + Auth` [input:0]
- `🔐 Verify JWT` [main:1] → `Auth 401` [input:0]
- `Auth 401` [main:0] → `Error` [input:0]

## WF-04 — TKTL WF-04 Check Protocol

- File: `n8n/workflows/TKTL-WF-04-check-protocol.json`
- ID: `lXWCvmXltec0RTgo`
- Version: draft `fb751091-66e1-4324-ba60-9757a3283692`; active `fb751091-66e1-4324-ba60-9757a3283692`
- Webhook: `POST /webhook/check-protocol`
- Credential binding trong export: `PG: Load Data → GMP-check`, `OpenAI: Semantic Review → OpenAl`, `PG: Save Review + Audit → GMP-check`
- JWT: GET `/auth/v1/user`, token từ header, apikey=có (đã redaction), onError=continueErrorOutput

### Node graph active

| # | Node | Type |
|---:|---|---|
| 1 | Webhook Check | `n8n-nodes-base.webhook` |
| 2 | Parse + Auth | `n8n-nodes-base.code` |
| 3 | OK? | `n8n-nodes-base.if` |
| 4 | Error | `n8n-nodes-base.respondToWebhook` |
| 5 | PG: Load Data | `n8n-nodes-base.postgres` |
| 6 | Layer 1-2 Check + Build AI | `n8n-nodes-base.code` |
| 7 | Role OK? | `n8n-nodes-base.if` |
| 8 | Denied | `n8n-nodes-base.respondToWebhook` |
| 9 | OpenAI: Semantic Review | `n8n-nodes-base.httpRequest` |
| 10 | Merge Findings + Save SQL | `n8n-nodes-base.code` |
| 11 | PG: Save Review + Audit | `n8n-nodes-base.postgres` |
| 12 | Check Response | `n8n-nodes-base.respondToWebhook` |
| 13 | 🔐 Verify JWT | `n8n-nodes-base.httpRequest` |
| 14 | Auth 401 | `n8n-nodes-base.code` |

### Connections active

- `Webhook Check` [main:0] → `🔐 Verify JWT` [input:0]
- `Parse + Auth` [main:0] → `OK?` [input:0]
- `OK?` [main:0] → `Error` [input:0]
- `OK?` [main:1] → `PG: Load Data` [input:0]
- `PG: Load Data` [main:0] → `Layer 1-2 Check + Build AI` [input:0]
- `Layer 1-2 Check + Build AI` [main:0] → `Role OK?` [input:0]
- `Role OK?` [main:0] → `Denied` [input:0]
- `Role OK?` [main:1] → `OpenAI: Semantic Review` [input:0]
- `OpenAI: Semantic Review` [main:0] → `Merge Findings + Save SQL` [input:0]
- `Merge Findings + Save SQL` [main:0] → `PG: Save Review + Audit` [input:0]
- `PG: Save Review + Audit` [main:0] → `Check Response` [input:0]
- `🔐 Verify JWT` [main:0] → `Parse + Auth` [input:0]
- `🔐 Verify JWT` [main:1] → `Auth 401` [input:0]
- `Auth 401` [main:0] → `Error` [input:0]

## WF-05 — TKTL WF-05 Calculation Helper

- File: `n8n/workflows/TKTL-WF-05-calculation-helper.json`
- ID: `CPh7Z1g4EwyOrVo0`
- Version: draft `1a3919c5-59cb-4127-a09e-6460084b991a`; active `1a3919c5-59cb-4127-a09e-6460084b991a`
- Webhook: `POST /webhook/calculate-report`
- Credential binding trong export: `PG: Load Formula + Prompt → GMP-check`, `OpenAI: Interpret → OpenAl`, `PG: Save Job + Audit → GMP-check`
- JWT: GET `/auth/v1/user`, token từ header, apikey=có (đã redaction), onError=continueErrorOutput

### Node graph active

| # | Node | Type |
|---:|---|---|
| 1 | Webhook Calc | `n8n-nodes-base.webhook` |
| 2 | Parse + Auth | `n8n-nodes-base.code` |
| 3 | OK? | `n8n-nodes-base.if` |
| 4 | Error | `n8n-nodes-base.respondToWebhook` |
| 5 | PG: Load Formula + Prompt | `n8n-nodes-base.postgres` |
| 6 | Run Calculation + Build AI | `n8n-nodes-base.code` |
| 7 | Calc OK? | `n8n-nodes-base.if` |
| 8 | Calc Error | `n8n-nodes-base.respondToWebhook` |
| 9 | OpenAI: Interpret | `n8n-nodes-base.httpRequest` |
| 10 | Format Result | `n8n-nodes-base.code` |
| 11 | PG: Save Job + Audit | `n8n-nodes-base.postgres` |
| 12 | Calc Response | `n8n-nodes-base.respondToWebhook` |
| 13 | 🔐 Verify JWT | `n8n-nodes-base.httpRequest` |
| 14 | Auth 401 | `n8n-nodes-base.code` |

### Connections active

- `Webhook Calc` [main:0] → `🔐 Verify JWT` [input:0]
- `Parse + Auth` [main:0] → `OK?` [input:0]
- `OK?` [main:0] → `Error` [input:0]
- `OK?` [main:1] → `PG: Load Formula + Prompt` [input:0]
- `PG: Load Formula + Prompt` [main:0] → `Run Calculation + Build AI` [input:0]
- `Run Calculation + Build AI` [main:0] → `Calc OK?` [input:0]
- `Calc OK?` [main:0] → `Calc Error` [input:0]
- `Calc OK?` [main:1] → `OpenAI: Interpret` [input:0]
- `OpenAI: Interpret` [main:0] → `Format Result` [input:0]
- `Format Result` [main:0] → `PG: Save Job + Audit` [input:0]
- `PG: Save Job + Audit` [main:0] → `Calc Response` [input:0]
- `🔐 Verify JWT` [main:0] → `Parse + Auth` [input:0]
- `🔐 Verify JWT` [main:1] → `Auth 401` [input:0]
- `Auth 401` [main:0] → `Error` [input:0]

## WF-06 — TKTL WF-06 Document Search

- File: `n8n/workflows/TKTL-WF-06-document-search.json`
- ID: `o4fuUanxRrD7qQoG`
- Version: draft `f7b7ee5a-870b-446d-9a1e-e06ff1f4fe22`; active `f7b7ee5a-870b-446d-9a1e-e06ff1f4fe22`
- Webhook: `POST /webhook/search-docs`
- Credential binding trong export: `PG: Search Documents → GMP-check`
- JWT: GET `/auth/v1/user`, token từ header, apikey=có (đã redaction), onError=continueErrorOutput

### Node graph active

| # | Node | Type |
|---:|---|---|
| 1 | Webhook Search | `n8n-nodes-base.webhook` |
| 2 | Parse + Build SQL | `n8n-nodes-base.code` |
| 3 | OK? | `n8n-nodes-base.if` |
| 4 | Error | `n8n-nodes-base.respondToWebhook` |
| 5 | PG: Search Documents | `n8n-nodes-base.postgres` |
| 6 | Format Results | `n8n-nodes-base.code` |
| 7 | Search Response | `n8n-nodes-base.respondToWebhook` |
| 8 | 🔐 Verify JWT | `n8n-nodes-base.httpRequest` |
| 9 | Auth 401 | `n8n-nodes-base.code` |

### Connections active

- `Webhook Search` [main:0] → `🔐 Verify JWT` [input:0]
- `Parse + Build SQL` [main:0] → `OK?` [input:0]
- `OK?` [main:0] → `Error` [input:0]
- `OK?` [main:1] → `PG: Search Documents` [input:0]
- `PG: Search Documents` [main:0] → `Format Results` [input:0]
- `Format Results` [main:0] → `Search Response` [input:0]
- `🔐 Verify JWT` [main:0] → `Parse + Build SQL` [input:0]
- `🔐 Verify JWT` [main:1] → `Auth 401` [input:0]
- `Auth 401` [main:0] → `Error` [input:0]

## WF-07 — TKTL WF-07 Approve Document

- File: `n8n/workflows/TKTL-WF-07-approve-document.json`
- ID: `KFvOoabtnptFghSy`
- Version: draft `8f2d714c-48eb-4d00-8316-7fae6f40007f`; active `8f2d714c-48eb-4d00-8316-7fae6f40007f`
- Webhook: `POST /webhook/approve-document`
- Credential binding trong export: `PG: Get Roles → GMP-check`, `PG: Update Status → GMP-check`
- JWT: GET `/auth/v1/user`, token từ header, apikey=có (đã redaction), onError=continueErrorOutput

### Node graph active

| # | Node | Type |
|---:|---|---|
| 1 | Webhook Approve | `n8n-nodes-base.webhook` |
| 2 | Parse + JWT | `n8n-nodes-base.code` |
| 3 | OK? | `n8n-nodes-base.if` |
| 4 | Error | `n8n-nodes-base.respondToWebhook` |
| 5 | PG: Get Roles | `n8n-nodes-base.postgres` |
| 6 | Check QA Permission | `n8n-nodes-base.code` |
| 7 | QA OK? | `n8n-nodes-base.if` |
| 8 | QA Denied | `n8n-nodes-base.respondToWebhook` |
| 9 | PG: Update Status | `n8n-nodes-base.postgres` |
| 10 | Approve Response | `n8n-nodes-base.respondToWebhook` |
| 11 | 🔐 Verify JWT | `n8n-nodes-base.httpRequest` |
| 12 | Auth 401 | `n8n-nodes-base.code` |

### Connections active

- `Webhook Approve` [main:0] → `🔐 Verify JWT` [input:0]
- `Parse + JWT` [main:0] → `OK?` [input:0]
- `OK?` [main:0] → `Error` [input:0]
- `OK?` [main:1] → `PG: Get Roles` [input:0]
- `PG: Get Roles` [main:0] → `Check QA Permission` [input:0]
- `Check QA Permission` [main:0] → `QA OK?` [input:0]
- `QA OK?` [main:0] → `QA Denied` [input:0]
- `QA OK?` [main:1] → `PG: Update Status` [input:0]
- `PG: Update Status` [main:0] → `Approve Response` [input:0]
- `🔐 Verify JWT` [main:0] → `Parse + JWT` [input:0]
- `🔐 Verify JWT` [main:1] → `Auth 401` [input:0]
- `Auth 401` [main:0] → `Error` [input:0]

## WF-08 — TKTL WF-08 Health Monitor

- File: `n8n/workflows/TKTL-WF-08-health-monitor.json`
- ID: `5wwaxP51FgeXuDi3`
- Version: draft `821c2f84-221c-4bae-a6d3-c881c8b0aa20`; active `821c2f84-221c-4bae-a6d3-c881c8b0aa20`
- Webhook: `GET /webhook/health`
- Credential binding trong export: `PG: Get Stats → GMP-check`, `OpenAI: Check API → OpenAl`
- JWT: không có (health endpoint công khai)

### Node graph active

| # | Node | Type |
|---:|---|---|
| 1 | Webhook Health | `n8n-nodes-base.webhook` |
| 2 | PG: Get Stats | `n8n-nodes-base.postgres` |
| 3 | OpenAI: Check API | `n8n-nodes-base.httpRequest` |
| 4 | Build Health Report | `n8n-nodes-base.code` |
| 5 | Health Response | `n8n-nodes-base.respondToWebhook` |

### Connections active

- `Webhook Health` [main:0] → `PG: Get Stats` [input:0]
- `PG: Get Stats` [main:0] → `OpenAI: Check API` [input:0]
- `OpenAI: Check API` [main:0] → `Build Health Report` [input:0]
- `Build Health Report` [main:0] → `Health Response` [input:0]

## WF-09 — TKTL WF-09 Web Source Ingest

- File: `n8n/workflows/TKTL-WF-09-web-source-ingest.json`
- ID: `old58Th1kWOvMcTp`
- Version: draft `c03ee46b-2ccb-49ae-b265-ba0dd284c5f5`; active `c03ee46b-2ccb-49ae-b265-ba0dd284c5f5`
- Webhook: `POST /webhook/ingest-web`
- Credential binding trong export: `PG: Check Role → GMP-check`, `OpenAI: Embedding → OpenAl`, `PG: Insert Document → GMP-check`, `PG: Insert Chunks + Audit → GMP-check`
- JWT: GET `/auth/v1/user`, token từ header, apikey=có (đã redaction), onError=continueErrorOutput

### Node graph active

| # | Node | Type |
|---:|---|---|
| 1 | Webhook Web Ingest | `n8n-nodes-base.webhook` |
| 2 | Parse + Auth | `n8n-nodes-base.code` |
| 3 | OK? | `n8n-nodes-base.if` |
| 4 | Error | `n8n-nodes-base.respondToWebhook` |
| 5 | PG: Check Role | `n8n-nodes-base.postgres` |
| 6 | Check Permission | `n8n-nodes-base.code` |
| 7 | Perm OK? | `n8n-nodes-base.if` |
| 8 | Denied | `n8n-nodes-base.respondToWebhook` |
| 9 | Fetch Web Content | `n8n-nodes-base.httpRequest` |
| 10 | Extract HTML + Chunk | `n8n-nodes-base.code` |
| 11 | Extract OK? | `n8n-nodes-base.if` |
| 12 | Extract Error | `n8n-nodes-base.respondToWebhook` |
| 13 | OpenAI: Embedding | `n8n-nodes-base.httpRequest` |
| 14 | Build Doc SQL | `n8n-nodes-base.code` |
| 15 | PG: Insert Document | `n8n-nodes-base.postgres` |
| 16 | Build Chunks SQL | `n8n-nodes-base.code` |
| 17 | PG: Insert Chunks + Audit | `n8n-nodes-base.postgres` |
| 18 | Success | `n8n-nodes-base.respondToWebhook` |
| 19 | 🔐 Verify JWT | `n8n-nodes-base.httpRequest` |
| 20 | Auth 401 | `n8n-nodes-base.code` |

### Connections active

- `Webhook Web Ingest` [main:0] → `🔐 Verify JWT` [input:0]
- `Parse + Auth` [main:0] → `OK?` [input:0]
- `OK?` [main:0] → `Error` [input:0]
- `OK?` [main:1] → `PG: Check Role` [input:0]
- `PG: Check Role` [main:0] → `Check Permission` [input:0]
- `Check Permission` [main:0] → `Perm OK?` [input:0]
- `Perm OK?` [main:0] → `Denied` [input:0]
- `Perm OK?` [main:1] → `Fetch Web Content` [input:0]
- `Fetch Web Content` [main:0] → `Extract HTML + Chunk` [input:0]
- `Fetch Web Content` [main:1] → `Extract HTML + Chunk` [input:0]
- `Extract HTML + Chunk` [main:0] → `Extract OK?` [input:0]
- `Extract OK?` [main:0] → `Extract Error` [input:0]
- `Extract OK?` [main:1] → `OpenAI: Embedding` [input:0]
- `OpenAI: Embedding` [main:0] → `Build Doc SQL` [input:0]
- `Build Doc SQL` [main:0] → `PG: Insert Document` [input:0]
- `PG: Insert Document` [main:0] → `Build Chunks SQL` [input:0]
- `Build Chunks SQL` [main:0] → `PG: Insert Chunks + Audit` [input:0]
- `PG: Insert Chunks + Audit` [main:0] → `Success` [input:0]
- `🔐 Verify JWT` [main:0] → `Parse + Auth` [input:0]
- `🔐 Verify JWT` [main:1] → `Auth 401` [input:0]
- `Auth 401` [main:0] → `Error` [input:0]

## WF-10 — TKTL WF-10 Google Drive Sync

- File: `n8n/workflows/TKTL-WF-10-google-drive-sync.json`
- ID: `nFYb0JyZ6MZf5OVR`
- Version: draft `f0e0de35-1577-4bd4-9468-fcde186016bc`; active `f0e0de35-1577-4bd4-9468-fcde186016bc`
- Webhook: `POST /webhook/gmp-upload`
- Credential binding trong export: `Google Drive: Upload → CRAVE-Google-Workspace`
- JWT: GET `/auth/v1/user`, token từ query, apikey=có (đã redaction), onError=continueErrorOutput

### Node graph active

| # | Node | Type |
|---:|---|---|
| 1 | Webhook Drive Sync | `n8n-nodes-base.webhook` |
| 2 | 🔐 Verify JWT | `n8n-nodes-base.httpRequest` |
| 3 | CONFIG | `n8n-nodes-base.set` |
| 4 | Parse + Validate | `n8n-nodes-base.code` |
| 5 | Input Error? | `n8n-nodes-base.if` |
| 6 | Prepare Sync Log | `n8n-nodes-base.set` |
| 7 | REST: Insert Sync Log | `n8n-nodes-base.httpRequest` |
| 8 | Success Response | `n8n-nodes-base.respondToWebhook` |
| 9 | Auth 401 | `n8n-nodes-base.code` |
| 10 | Decode Error | `n8n-nodes-base.code` |
| 11 | Drive Error | `n8n-nodes-base.code` |
| 12 | Log Error | `n8n-nodes-base.code` |
| 13 | Error Response | `n8n-nodes-base.respondToWebhook` |
| 14 | Decode Base64 | `n8n-nodes-base.code` |
| 15 | Google Drive: Upload | `n8n-nodes-base.httpRequest` |

### Connections active

- `Webhook Drive Sync` [main:0] → `🔐 Verify JWT` [input:0]
- `🔐 Verify JWT` [main:0] → `CONFIG` [input:0]
- `🔐 Verify JWT` [main:1] → `Auth 401` [input:0]
- `CONFIG` [main:0] → `Parse + Validate` [input:0]
- `Parse + Validate` [main:0] → `Input Error?` [input:0]
- `Input Error?` [main:0] → `Error Response` [input:0]
- `Input Error?` [main:1] → `Decode Base64` [input:0]
- `Prepare Sync Log` [main:0] → `REST: Insert Sync Log` [input:0]
- `REST: Insert Sync Log` [main:0] → `Success Response` [input:0]
- `REST: Insert Sync Log` [main:1] → `Log Error` [input:0]
- `Auth 401` [main:0] → `Error Response` [input:0]
- `Drive Error` [main:0] → `Error Response` [input:0]
- `Log Error` [main:0] → `Error Response` [input:0]
- `Decode Error` [main:0] → `Error Response` [input:0]
- `Decode Base64` [main:0] → `Google Drive: Upload` [input:0]
- `Decode Base64` [main:1] → `Decode Error` [input:0]
- `Google Drive: Upload` [main:0] → `Prepare Sync Log` [input:0]
- `Google Drive: Upload` [main:0] → `Drive Error` [input:0]

## WF-11 — TKTL WF-11 Literature Search

- File: `n8n/workflows/TKTL-WF-11-literature-search.json`
- ID: `yrLN2Y5tEC8jJwGR`
- Version: draft `bad508fe-756e-42e5-b6e5-19786d97e6f8`; active `bad508fe-756e-42e5-b6e5-19786d97e6f8`
- Webhook: `POST /webhook/literature-search`
- Credential binding trong export: `PG: Check Role → GMP-check`, `OpenAI: Embedding → OpenAl`, `PG: Insert Document → GMP-check`, `PG: Insert Chunks + Audit → GMP-check`
- JWT: GET `/auth/v1/user`, token từ header, apikey=có (đã redaction), onError=continueErrorOutput

### Node graph active

| # | Node | Type |
|---:|---|---|
| 1 | Webhook Literature Search | `n8n-nodes-base.webhook` |
| 2 | 🔐 Verify JWT | `n8n-nodes-base.httpRequest` |
| 3 | Auth 401 | `n8n-nodes-base.code` |
| 4 | Parse + Auth | `n8n-nodes-base.code` |
| 5 | Input OK? | `n8n-nodes-base.if` |
| 6 | Error Response | `n8n-nodes-base.respondToWebhook` |
| 7 | Is Ingest? | `n8n-nodes-base.if` |
| 8 | Build Search URL | `n8n-nodes-base.code` |
| 9 | Europe PMC Search | `n8n-nodes-base.httpRequest` |
| 10 | Normalize Results | `n8n-nodes-base.code` |
| 11 | Search Response | `n8n-nodes-base.respondToWebhook` |
| 12 | PG: Check Role | `n8n-nodes-base.postgres` |
| 13 | Check Permission | `n8n-nodes-base.code` |
| 14 | Perm OK? | `n8n-nodes-base.if` |
| 15 | Fetch Article | `n8n-nodes-base.httpRequest` |
| 16 | Normalize Article | `n8n-nodes-base.code` |
| 17 | Article Found? | `n8n-nodes-base.if` |
| 18 | OpenAI: Embedding | `n8n-nodes-base.httpRequest` |
| 19 | Build Doc SQL | `n8n-nodes-base.code` |
| 20 | PG: Insert Document | `n8n-nodes-base.postgres` |
| 21 | Build Chunks SQL | `n8n-nodes-base.code` |
| 22 | PG: Insert Chunks + Audit | `n8n-nodes-base.postgres` |
| 23 | Ingest Response | `n8n-nodes-base.respondToWebhook` |

### Connections active

- `Webhook Literature Search` [main:0] → `🔐 Verify JWT` [input:0]
- `🔐 Verify JWT` [main:0] → `Parse + Auth` [input:0]
- `🔐 Verify JWT` [main:1] → `Auth 401` [input:0]
- `Auth 401` [main:0] → `Error Response` [input:0]
- `Parse + Auth` [main:0] → `Input OK?` [input:0]
- `Input OK?` [main:0] → `Error Response` [input:0]
- `Input OK?` [main:1] → `Is Ingest?` [input:0]
- `Is Ingest?` [main:0] → `PG: Check Role` [input:0]
- `Is Ingest?` [main:1] → `Build Search URL` [input:0]
- `Build Search URL` [main:0] → `Europe PMC Search` [input:0]
- `Europe PMC Search` [main:0] → `Normalize Results` [input:0]
- `Normalize Results` [main:0] → `Search Response` [input:0]
- `PG: Check Role` [main:0] → `Check Permission` [input:0]
- `Check Permission` [main:0] → `Perm OK?` [input:0]
- `Perm OK?` [main:0] → `Error Response` [input:0]
- `Perm OK?` [main:1] → `Fetch Article` [input:0]
- `Fetch Article` [main:0] → `Normalize Article` [input:0]
- `Normalize Article` [main:0] → `Article Found?` [input:0]
- `Article Found?` [main:0] → `Error Response` [input:0]
- `Article Found?` [main:1] → `OpenAI: Embedding` [input:0]
- `OpenAI: Embedding` [main:0] → `Build Doc SQL` [input:0]
- `Build Doc SQL` [main:0] → `PG: Insert Document` [input:0]
- `PG: Insert Document` [main:0] → `Build Chunks SQL` [input:0]
- `Build Chunks SQL` [main:0] → `PG: Insert Chunks + Audit` [input:0]
- `PG: Insert Chunks + Audit` [main:0] → `Ingest Response` [input:0]

## WF-12 — TKTL WF-12 - Loi tro ly QA agentic

- File: `n8n/workflows/TKTL-WF-12-qa-assistant-agentic.json`
- ID: `DMcZCeYXTFRUyufV`
- Version: draft `8d6c7110-f951-49e7-a238-e81520aeaa57`; active `8d6c7110-f951-49e7-a238-e81520aeaa57`
- Webhook: `POST /webhook/assistant-query`
- Credential binding trong export: `Load Memory → GMP-check`, `Embed Query → OpenAl`, `OpenAI Chat Model → OpenAl`, `rag_search → GMP-check`, `literature_lookup → GMP-check`, `Save Memory User → GMP-check`, `Save Memory Assistant → GMP-check`, `Audit INSERT → GMP-check`
- JWT: GET `/auth/v1/user`, token từ body, apikey=có (đã redaction), onError=continueErrorOutput

### Node graph active

| # | Node | Type |
|---:|---|---|
| 1 | Webhook | `n8n-nodes-base.webhook` |
| 2 | Verify JWT | `n8n-nodes-base.httpRequest` |
| 3 | Auth Gate | `n8n-nodes-base.if` |
| 4 | Load Memory | `n8n-nodes-base.postgres` |
| 5 | Embed Query | `n8n-nodes-base.httpRequest` |
| 6 | AI Agent | `@n8n/n8n-nodes-langchain.agent` |
| 7 | OpenAI Chat Model | `@n8n/n8n-nodes-langchain.lmChatOpenAi` |
| 8 | rag_search | `n8n-nodes-base.postgresTool` |
| 9 | literature_lookup | `n8n-nodes-base.postgresTool` |
| 10 | calc | `@n8n/n8n-nodes-langchain.toolCode` |
| 11 | Prepare Response | `n8n-nodes-base.code` |
| 12 | Save Memory User | `n8n-nodes-base.postgres` |
| 13 | Save Memory Assistant | `n8n-nodes-base.postgres` |
| 14 | Audit INSERT | `n8n-nodes-base.postgres` |
| 15 | Respond 200 | `n8n-nodes-base.respondToWebhook` |
| 16 | Respond 401 | `n8n-nodes-base.respondToWebhook` |

### Connections active

- `Webhook` [main:0] → `Verify JWT` [input:0]
- `Verify JWT` [main:0] → `Auth Gate` [input:0]
- `Verify JWT` [main:1] → `Auth Gate` [input:0]
- `Auth Gate` [main:0] → `Load Memory` [input:0]
- `Auth Gate` [main:1] → `Respond 401` [input:0]
- `Load Memory` [main:0] → `Embed Query` [input:0]
- `Embed Query` [main:0] → `AI Agent` [input:0]
- `AI Agent` [main:0] → `Prepare Response` [input:0]
- `OpenAI Chat Model` [ai_languageModel:0] → `AI Agent` [input:0]
- `rag_search` [ai_tool:0] → `AI Agent` [input:0]
- `literature_lookup` [ai_tool:0] → `AI Agent` [input:0]
- `calc` [ai_tool:0] → `AI Agent` [input:0]
- `Prepare Response` [main:0] → `Save Memory User` [input:0]
- `Save Memory User` [main:0] → `Save Memory Assistant` [input:0]
- `Save Memory Assistant` [main:0] → `Audit INSERT` [input:0]
- `Audit INSERT` [main:0] → `Respond 200` [input:0]

## WF-13 — TKTL WF-13 Validation Copilot

- File: `n8n/workflows/TKTL-WF-13-validation-copilot.json`
- ID: `TcusASYdTTHaoygD`
- Version: draft `ce4f4ce7-731e-4e95-8fc1-e0ba83816315`; active `ce4f4ce7-731e-4e95-8fc1-e0ba83816315`
- Webhook: `POST /webhook/copilot-query`
- Credential binding trong export: `PG: Prepare Session + History → GMP-check`, `Embed Query → OpenAl`, `OpenAI Chat Model → OpenAl`, `rag_search → GMP-check`, `get_template → GMP-check`, `PG: Save Messages + Audit → GMP-check`
- JWT: GET `/auth/v1/user`, token từ query, apikey=có (đã redaction), onError=continueErrorOutput

### Node graph active

| # | Node | Type |
|---:|---|---|
| 1 | Webhook Copilot Query | `n8n-nodes-base.webhook` |
| 2 | 🔐 Verify JWT | `n8n-nodes-base.httpRequest` |
| 3 | CONFIG | `n8n-nodes-base.set` |
| 4 | Parse + Validate | `n8n-nodes-base.code` |
| 5 | Input Error? | `n8n-nodes-base.if` |
| 6 | PG: Prepare Session + History | `n8n-nodes-base.postgres` |
| 7 | Session Error? | `n8n-nodes-base.if` |
| 8 | Embed Query | `n8n-nodes-base.httpRequest` |
| 9 | AI Agent | `@n8n/n8n-nodes-langchain.agent` |
| 10 | OpenAI Chat Model | `@n8n/n8n-nodes-langchain.lmChatOpenAi` |
| 11 | rag_search | `n8n-nodes-base.postgresTool` |
| 12 | get_template | `n8n-nodes-base.postgresTool` |
| 13 | Prepare Response | `n8n-nodes-base.code` |
| 14 | PG: Save Messages + Audit | `n8n-nodes-base.postgres` |
| 15 | Respond 200 | `n8n-nodes-base.respondToWebhook` |
| 16 | Auth 401 | `n8n-nodes-base.code` |
| 17 | Backend Error | `n8n-nodes-base.code` |
| 18 | Error Response | `n8n-nodes-base.respondToWebhook` |

### Connections active

- `Webhook Copilot Query` [main:0] → `🔐 Verify JWT` [input:0]
- `🔐 Verify JWT` [main:0] → `CONFIG` [input:0]
- `🔐 Verify JWT` [main:1] → `Auth 401` [input:0]
- `CONFIG` [main:0] → `Parse + Validate` [input:0]
- `Parse + Validate` [main:0] → `Input Error?` [input:0]
- `Input Error?` [main:0] → `Error Response` [input:0]
- `Input Error?` [main:1] → `PG: Prepare Session + History` [input:0]
- `PG: Prepare Session + History` [main:0] → `Session Error?` [input:0]
- `PG: Prepare Session + History` [main:1] → `Backend Error` [input:0]
- `Session Error?` [main:0] → `Error Response` [input:0]
- `Session Error?` [main:1] → `Embed Query` [input:0]
- `Embed Query` [main:0] → `AI Agent` [input:0]
- `Embed Query` [main:1] → `Backend Error` [input:0]
- `AI Agent` [main:0] → `Prepare Response` [input:0]
- `AI Agent` [main:1] → `Backend Error` [input:0]
- `OpenAI Chat Model` [ai_languageModel:0] → `AI Agent` [input:0]
- `rag_search` [ai_tool:0] → `AI Agent` [input:0]
- `get_template` [ai_tool:0] → `AI Agent` [input:0]
- `Prepare Response` [main:0] → `PG: Save Messages + Audit` [input:0]
- `PG: Save Messages + Audit` [main:0] → `Respond 200` [input:0]
- `PG: Save Messages + Audit` [main:1] → `Backend Error` [input:0]
- `Auth 401` [main:0] → `Error Response` [input:0]
- `Backend Error` [main:0] → `Error Response` [input:0]

## WF-14 — TKTL WF-14 Web Document Search

- File: `n8n/workflows/TKTL-WF-14-web-document-search.json`
- ID: `6USn5CYpK9VlyExu`
- Version: draft `f432217d-c329-45cd-90a7-2a0055719549`; active `70afe9fe-2325-4413-a1b1-860f0c05cb2f`
- Webhook: `POST /webhook/web-search`
- Credential binding trong export: `PG: Audit INSERT → GMP-check`
- JWT: GET `/auth/v1/user`, token từ header, apikey=có (đã redaction), onError=thiếu

### Node graph active

| # | Node | Type |
|---:|---|---|
| 1 | 🔍 Webhook Web Search | `n8n-nodes-base.webhook` |
| 2 | 🔐 Verify JWT | `n8n-nodes-base.httpRequest` |
| 3 | Auth OK? | `n8n-nodes-base.if` |
| 4 | CONFIG | `n8n-nodes-base.set` |
| 5 | Parse + Validate | `n8n-nodes-base.code` |
| 6 | Input Error? | `n8n-nodes-base.if` |
| 7 | Error Response | `n8n-nodes-base.respondToWebhook` |
| 8 | Prepare Tavily Body | `n8n-nodes-base.code` |
| 9 | 🌐 Tavily Search | `n8n-nodes-base.httpRequest` |
| 10 | Search OK? | `n8n-nodes-base.if` |
| 11 | ⚡ Process Results | `n8n-nodes-base.code` |
| 12 | PG: Audit INSERT | `n8n-nodes-base.postgres` |
| 13 | Respond 200 | `n8n-nodes-base.respondToWebhook` |
| 14 | Backend Error | `n8n-nodes-base.respondToWebhook` |
| 15 | Auth 401 | `n8n-nodes-base.respondToWebhook` |

### Connections active

- `🔍 Webhook Web Search` [main:0] → `🔐 Verify JWT` [input:0]
- `🔐 Verify JWT` [main:0] → `Auth OK?` [input:0]
- `Auth OK?` [main:0] → `CONFIG` [input:0]
- `Auth OK?` [main:1] → `Auth 401` [input:0]
- `CONFIG` [main:0] → `Parse + Validate` [input:0]
- `Parse + Validate` [main:0] → `Input Error?` [input:0]
- `Input Error?` [main:0] → `Error Response` [input:0]
- `Input Error?` [main:1] → `Prepare Tavily Body` [input:0]
- `Prepare Tavily Body` [main:0] → `🌐 Tavily Search` [input:0]
- `🌐 Tavily Search` [main:0] → `Search OK?` [input:0]
- `Search OK?` [main:0] → `⚡ Process Results` [input:0]
- `Search OK?` [main:1] → `Backend Error` [input:0]
- `⚡ Process Results` [main:0] → `PG: Audit INSERT` [input:0]
- `PG: Audit INSERT` [main:0] → `Respond 200` [input:0]
