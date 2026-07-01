import { workflow, node, trigger, languageModel, outputParser, expr, newCredential } from '@n8n/workflow-sdk';

const craveWebhook = trigger({
  type: 'n8n-nodes-base.webhook',
  version: 2.1,
  config: { name: 'CRAVE Webhook', parameters: { httpMethod: 'POST', path: 'crave-verify', responseMode: 'responseNode' } },
  output: [{ body: { question: 'ISO 8573-2 quy định thời gian lấy mẫu dầu theo nồng độ dầu dự kiến?', user_id: '' } }]
});

const normalizeInput = node({
  type: 'n8n-nodes-base.set',
  version: 3.4,
  config: {
    name: 'Chuan hoa dau vao',
    parameters: {
      mode: 'manual',
      assignments: { assignments: [
        { id: 'q', name: 'question', value: expr('{{ $json.body?.question ?? $json.question ?? "" }}'), type: 'string' },
        { id: 'u', name: 'userId', value: expr('{{ $json.body?.user_id ?? $json.user_id ?? "" }}'), type: 'string' }
      ] }
    }
  },
  output: [{ question: 'ISO 8573-2 ...', userId: '' }]
});

const loadPrompts = node({
  type: 'n8n-nodes-base.postgres',
  version: 2.6,
  config: {
    name: 'Nap prompt CRAVE',
    parameters: {
      operation: 'executeQuery',
      query: "select prompt_name, prompt_text from public.prompt_versions where version = 'v1.0' and is_active = true and prompt_name in ('crave_claim_framing','crave_support_agent','crave_refute_agent','crave_judge')"
    },
    credentials: { postgres: newCredential('GMP-check') }
  },
  output: [{ prompt_name: 'crave_claim_framing', prompt_text: '...' }]
});

const collectPrompts = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Gom prompt CRAVE',
    parameters: {
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode: "const rows = $input.all().map(i => i.json);\nconst prompts = {};\nfor (const r of rows) { prompts[r.prompt_name] = r.prompt_text; }\nconst question = $('Chuan hoa dau vao').first().json.question;\nreturn [{ json: { question, prompts } }];"
    }
  },
  output: [{ question: '...', prompts: { crave_judge: '...' } }]
});

const framingModel = languageModel({
  type: '@n8n/n8n-nodes-langchain.lmChatGoogleGemini',
  version: 1.1,
  config: { name: 'Gemini Khung hoa', parameters: { modelName: 'models/gemini-2.5-flash', options: { temperature: 0.1 } }, credentials: { googlePalmApi: newCredential('Google Gemini(PaLM) Api account 87') } }
});
const framingParser = outputParser({
  type: '@n8n/n8n-nodes-langchain.outputParserStructured',
  version: 1.3,
  config: { name: 'Parser Khung', parameters: { schemaType: 'fromJson', jsonSchemaExample: '{"claim_text_vi":"...","claim_text_en":"...","frame_used":"pcc","facets":{"population":"","concept":"","context":"","comparison":"","exposure":"","outcome":"","threshold":"","doc_type":""},"retrieval_queries":{"vi":["..."],"en":["..."]}}' } }
});
const framingAgent = node({
  type: '@n8n/n8n-nodes-langchain.agent',
  version: 3.1,
  config: {
    name: 'Khung hoa menh de',
    parameters: { promptType: 'define', text: expr('Cau hoi cua nguoi dung (tieng Viet): {{ $json.question }}'), hasOutputParser: true, options: { systemMessage: expr('{{ $json.prompts.crave_claim_framing }}') } },
    subnodes: { model: framingModel, outputParser: framingParser }
  },
  output: [{ output: { claim_text_vi: '...', claim_text_en: '...', frame_used: 'pcc', facets: {}, retrieval_queries: { en: ['...'] } } }]
});

const embedQuery = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.4,
  config: {
    name: 'Nhung truy van OpenAI',
    parameters: {
      method: 'POST',
      url: 'https://api.openai.com/v1/embeddings',
      authentication: 'predefinedCredentialType',
      nodeCredentialType: 'openAiApi',
      sendBody: true,
      contentType: 'json',
      specifyBody: 'json',
      jsonBody: expr('{ "model": "text-embedding-3-small", "input": {{ JSON.stringify($("Khung hoa menh de").item.json.output.claim_text_en) }} }')
    },
    credentials: { openAiApi: newCredential('OpenAl') }
  },
  output: [{ data: [{ embedding: [0.01, 0.02] }] }]
});

const buildVector = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Dung vector truy van',
    parameters: {
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode: "const emb = $json.data[0].embedding;\nconst f = $('Khung hoa menh de').first().json.output;\nconst enq = (f.retrieval_queries && f.retrieval_queries.en && f.retrieval_queries.en.length) ? f.retrieval_queries.en.join(' ') : f.claim_text_en;\nreturn [{ json: { vectorLiteral: '[' + emb.join(',') + ']', query_text: enq } }];"
    }
  },
  output: [{ vectorLiteral: '[0.01,0.02]', query_text: 'oil sampling time ISO 8573-2' }]
});

const insertClaim = node({
  type: 'n8n-nodes-base.postgres',
  version: 2.6,
  config: {
    name: 'Luu claim',
    parameters: {
      operation: 'executeQuery',
      query: 'insert into public.claims (source_question_vi, claim_text_vi, claim_text_en, frame_used, facets) values ($1, $2, $3, $4, $5::jsonb) returning id',
      options: { queryReplacement: expr('{{ [$("Chuan hoa dau vao").item.json.question, $("Khung hoa menh de").item.json.output.claim_text_vi, $("Khung hoa menh de").item.json.output.claim_text_en, $("Khung hoa menh de").item.json.output.frame_used, JSON.stringify($("Khung hoa menh de").item.json.output.facets)] }}') }
    },
    credentials: { postgres: newCredential('GMP-check') }
  },
  output: [{ id: '00000000-0000-0000-0000-000000000000' }]
});

const hybridSearch = node({
  type: 'n8n-nodes-base.postgres',
  version: 2.6,
  config: {
    name: 'Tim kiem Hybrid V4',
    parameters: {
      operation: 'executeQuery',
      query: 'select chunk_id, document_id, content, document_code, document_title, document_version, page_number, section_title, combined_score from public.hybrid_search_v4($1::extensions.vector, $2, 0.4, 8)',
      options: { queryReplacement: expr('{{ [$("Dung vector truy van").item.json.vectorLiteral, $("Dung vector truy van").item.json.query_text] }}') }
    },
    credentials: { postgres: newCredential('GMP-check') }
  },
  output: [{ chunk_id: '11111111-1111-1111-1111-111111111111', content: 'ISO 8573-2 ...', document_code: 'ISO-8573-2', page_number: 3, combined_score: 0.8 }]
});

const buildContext = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Dung CONTEXT',
    parameters: {
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode: "const chunks = $input.all().map(i => i.json);\nconst f = $('Khung hoa menh de').first().json.output;\nconst claimId = $('Luu claim').first().json.id;\nconst question = $('Chuan hoa dau vao').first().json.question;\nconst context = chunks.map((c, idx) => '[#' + (idx+1) + ' chunk_id=' + c.chunk_id + '] (' + c.document_code + ' p.' + c.page_number + ') ' + c.content).join('\\n\\n');\nreturn [{ json: { claimId, claimVi: f.claim_text_vi, claimEn: f.claim_text_en, question, context, chunkCount: chunks.length } }];"
    }
  },
  output: [{ claimId: '0000', claimVi: '...', claimEn: '...', question: '...', context: '[#1 chunk_id=... ] ...', chunkCount: 3 }]
});

const supportModel = languageModel({
  type: '@n8n/n8n-nodes-langchain.lmChatGoogleGemini',
  version: 1.1,
  config: { name: 'Gemini Ung ho', parameters: { modelName: 'models/gemini-2.5-flash', options: { temperature: 0.1 } }, credentials: { googlePalmApi: newCredential('Google Gemini(PaLM) Api account 87') } }
});
const supportParser = outputParser({
  type: '@n8n/n8n-nodes-langchain.outputParserStructured',
  version: 1.3,
  config: { name: 'Parser Ung ho', parameters: { schemaType: 'fromJson', jsonSchemaExample: '{"stance":"support","no_evidence":false,"evidence":[{"chunk_id":"...","quote_en":"...","stance_strength":0.8,"note_vi":"..."}]}' } }
});
const supportAgent = node({
  type: '@n8n/n8n-nodes-langchain.agent',
  version: 3.1,
  config: {
    name: 'Bang chung ung ho',
    parameters: { promptType: 'define', text: expr('MENH DE: {{ $json.claimEn }}\n\nCONTEXT (moi doan co chunk_id):\n{{ $json.context }}'), hasOutputParser: true, options: { systemMessage: expr('{{ $("Gom prompt CRAVE").first().json.prompts.crave_support_agent }}') } },
    subnodes: { model: supportModel, outputParser: supportParser }
  },
  output: [{ output: { stance: 'support', no_evidence: false, evidence: [] } }]
});

const refuteModel = languageModel({
  type: '@n8n/n8n-nodes-langchain.lmChatGroq',
  version: 1,
  config: { name: 'Groq Phan bac', parameters: { model: 'llama-3.3-70b-versatile', options: { temperature: 0.1 } }, credentials: { groqApi: newCredential('Tai khoan Groq') } }
});
const refuteParser = outputParser({
  type: '@n8n/n8n-nodes-langchain.outputParserStructured',
  version: 1.3,
  config: { name: 'Parser Phan bac', parameters: { schemaType: 'fromJson', jsonSchemaExample: '{"no_evidence":false,"evidence":[{"chunk_id":"...","quote_en":"...","stance":"refute","stance_strength":0.7,"note_vi":"..."}]}' } }
});
const refuteAgent = node({
  type: '@n8n/n8n-nodes-langchain.agent',
  version: 3.1,
  config: {
    name: 'Bang chung phan bac',
    parameters: { promptType: 'define', text: expr('MENH DE: {{ $("Dung CONTEXT").item.json.claimEn }}\n\nCONTEXT:\n{{ $("Dung CONTEXT").item.json.context }}'), hasOutputParser: true, options: { systemMessage: expr('{{ $("Gom prompt CRAVE").first().json.prompts.crave_refute_agent }}') } },
    subnodes: { model: refuteModel, outputParser: refuteParser }
  },
  output: [{ output: { no_evidence: false, evidence: [] } }]
});

const judgeModel = languageModel({
  type: '@n8n/n8n-nodes-langchain.lmChatGroq',
  version: 1,
  config: { name: 'Groq Trong tai', parameters: { model: 'llama-3.3-70b-versatile', options: { temperature: 0.1 } }, credentials: { groqApi: newCredential('Tai khoan Groq') } }
});
const judgeParser = outputParser({
  type: '@n8n/n8n-nodes-langchain.outputParserStructured',
  version: 1.3,
  config: { name: 'Parser Trong tai', parameters: { schemaType: 'fromJson', jsonSchemaExample: '{"verdict":"supported","confidence":0.8,"rationale_vi":"...","answer_vi":"...","support_count":2,"refute_count":0,"requires_human_signoff":false,"escalation_target":null,"citations":[{"chunk_id":"...","quote_en":"..."}]}' } }
});
const judgeAgent = node({
  type: '@n8n/n8n-nodes-langchain.agent',
  version: 3.1,
  config: {
    name: 'Trong tai CRAVE',
    parameters: { promptType: 'define', text: expr('MENH DE (VI): {{ $("Dung CONTEXT").item.json.claimVi }}\nMENH DE (EN): {{ $("Dung CONTEXT").item.json.claimEn }}\n\nBANG CHUNG UNG HO:\n{{ JSON.stringify($("Bang chung ung ho").item.json.output.evidence) }}\n\nBANG CHUNG PHAN BAC/GIOI HAN:\n{{ JSON.stringify($("Bang chung phan bac").item.json.output.evidence) }}'), hasOutputParser: true, options: { systemMessage: expr('{{ $("Gom prompt CRAVE").first().json.prompts.crave_judge }}') } },
    subnodes: { model: judgeModel, outputParser: judgeParser }
  },
  output: [{ output: { verdict: 'supported', confidence: 0.8, rationale_vi: '...', answer_vi: '...', support_count: 2, refute_count: 0, requires_human_signoff: false, escalation_target: null, citations: [] } }]
});

const insertVerdict = node({
  type: 'n8n-nodes-base.postgres',
  version: 2.6,
  config: {
    name: 'Luu verdict',
    parameters: {
      operation: 'executeQuery',
      query: "insert into public.claim_verdicts (claim_id, verdict, confidence, rationale_vi, support_count, refute_count, model_provider, model_name, escalated, escalation_target, requires_human_signoff, prompt_version_id) values ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,(select id from public.prompt_versions where prompt_name='crave_judge' and version='v1.0')) returning id, verdict, confidence, requires_human_signoff",
      options: { queryReplacement: expr('{{ [$("Dung CONTEXT").item.json.claimId, $("Trong tai CRAVE").item.json.output.verdict, $("Trong tai CRAVE").item.json.output.confidence, $("Trong tai CRAVE").item.json.output.rationale_vi, $("Trong tai CRAVE").item.json.output.support_count, $("Trong tai CRAVE").item.json.output.refute_count, "groq", "llama-3.3-70b-versatile", ($("Trong tai CRAVE").item.json.output.escalation_target ? true : false), $("Trong tai CRAVE").item.json.output.escalation_target, $("Trong tai CRAVE").item.json.output.requires_human_signoff] }}') }
    },
    credentials: { postgres: newCredential('GMP-check') }
  },
  output: [{ id: '2222', verdict: 'supported', confidence: 0.8, requires_human_signoff: false }]
});

const respond = node({
  type: 'n8n-nodes-base.respondToWebhook',
  version: 1.5,
  config: {
    name: 'Tra ket qua',
    parameters: {
      respondWith: 'json',
      responseBody: expr('{{ { "verdict": $("Trong tai CRAVE").item.json.output.verdict, "confidence": $("Trong tai CRAVE").item.json.output.confidence, "answer_vi": $("Trong tai CRAVE").item.json.output.answer_vi, "rationale_vi": $("Trong tai CRAVE").item.json.output.rationale_vi, "requires_human_signoff": $("Trong tai CRAVE").item.json.output.requires_human_signoff, "claim_id": $("Dung CONTEXT").item.json.claimId, "support": $("Bang chung ung ho").item.json.output.evidence, "refute": $("Bang chung phan bac").item.json.output.evidence, "citations": $("Trong tai CRAVE").item.json.output.citations, "disclaimer": "[AI-DRAFT] Can nguoi co chuyen mon GMP xem xet va phe duyet." } }}')
    }
  }
});

export default workflow('crave-claim-verification', 'TKTL CRAVE Claim Verification')
  .add(craveWebhook)
  .to(normalizeInput)
  .to(loadPrompts)
  .to(collectPrompts)
  .to(framingAgent)
  .to(embedQuery)
  .to(buildVector)
  .to(insertClaim)
  .to(hybridSearch)
  .to(buildContext)
  .to(supportAgent)
  .to(refuteAgent)
  .to(judgeAgent)
  .to(insertVerdict)
  .to(respond);
