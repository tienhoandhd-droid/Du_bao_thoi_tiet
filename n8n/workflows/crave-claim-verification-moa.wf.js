// TKTL CRAVE Claim Verification v2 MoA — workflow id: Dq7aO1y1RNGuILxn (inactive)
// Mixture-of-Agents: 3 proposer free song song (Gemini gemini-2.5-flash + Groq llama-3.3-70b
// + Groq openai/gpt-oss-120b) phân tích 2 chiều độc lập -> merge -> aggregator OpenAI gpt-5-mini
// (Chain-of-Verification + self-consistency) -> verdict GMP + answer_vi chi tiết.
// Prompt: crave_moa_proposer / crave_moa_aggregator (prompt_versions, migration 034).
// Retrieval interim zero-vector (chờ R06 embedding). Test PASS 2026-07-01 (mock ISO 8573-2):
//   3/3 proposer 'conditional' -> aggregator verdict conditional 0.82, CoV rõ, answer_vi chi tiết.
// Source SDK canonical: xem lịch sử tạo qua create_workflow_from_code; chỉnh live qua update_workflow.
// Node chính: CRAVE Webhook -> Chuan hoa -> Nap/Gom prompt -> Khung hoa (Gemini) -> Dung vector
//   -> Luu claim -> Tim kiem Hybrid V4 -> Dung CONTEXT
//   -> [Proposer A Gemini | Proposer B Groq Llama | Proposer C Groq OSS] -> Gop de xuat
//   -> Gom de xuat MoA -> Aggregator CRAVE (OpenAI) -> Luu verdict -> Tra ket qua
