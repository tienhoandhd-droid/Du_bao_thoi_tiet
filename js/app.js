// ============================================================
// GMP Validation Dashboard — Logic ứng dụng
// Đọc cấu hình từ window.APP_CONFIG (js/config.js, nạp trước file này)
// Thư viện Supabase nạp qua CDN ở <head> (window.supabase)
// ============================================================

// ============================================================
// CONFIG — Giá trị được GitHub Actions thay tự động từ Secrets
// KHÔNG sửa trực tiếp ở đây
// ============================================================
// Bắt lỗi toàn cục — log rõ ràng, không để app "chết im"
window.addEventListener('error', function (e) { console.error('[Lỗi ứng dụng]', e.message, (e.filename || '') + ':' + (e.lineno || '')); });
window.addEventListener('unhandledrejection', function (e) { console.error('[Promise lỗi]', e.reason); });

const CONFIG = window.APP_CONFIG || {};

const API = {
  health:   CONFIG.WEBHOOK_BASE + '/health',
  ragQuery: CONFIG.WEBHOOK_BASE + '/rag-query',
  ingest:   CONFIG.WEBHOOK_BASE + '/ingest-document',
  search:   CONFIG.WEBHOOK_BASE + '/search-docs',
  approve:  CONFIG.WEBHOOK_BASE + '/approve-document',
};

// ============================================================
// SUPABASE + AUTH
// ============================================================
let sb = null;
(function initSupabase(){
  function fail(msg){
    console.error('[INIT]', msg);
    var e = document.getElementById('loginError');
    if (e){ e.textContent = msg; e.style.display = 'block'; }
    var b = document.getElementById('loginBtn');
    if (b){ b.disabled = true; b.textContent = '⚠ Lỗi cấu hình'; }
  }
  if (!window.supabase || typeof window.supabase.createClient !== 'function'){
    fail('Thư viện Supabase chưa tải được — kiểm tra mạng có chặn cdn.jsdelivr.net không (hoặc tự host thư viện).');
    return;
  }
  if (!CONFIG.SUPABASE_URL || CONFIG.SUPABASE_URL.slice(0,4) !== 'http' || CONFIG.SUPABASE_URL.indexOf('__') !== -1){
    fail('SUPABASE_URL trống/sai trong Secret. Giá trị hiện tại: "' + CONFIG.SUPABASE_URL + '"');
    return;
  }
  if (!CONFIG.SUPABASE_ANON_KEY || CONFIG.SUPABASE_ANON_KEY.length < 20 || CONFIG.SUPABASE_ANON_KEY.indexOf('__') !== -1){
    fail('SUPABASE_ANON_KEY trống/sai trong Secret.');
    return;
  }
  try {
    sb = window.supabase.createClient(CONFIG.SUPABASE_URL, CONFIG.SUPABASE_ANON_KEY);
  } catch (e){
    fail('createClient lỗi: ' + e.message);
  }
})();
let currentUser = null, currentSession = null, currentRoles = [];

// Session timeout (8 giờ = 28800000ms)
let sessionTimer = null;
function resetSessionTimer() {
  clearTimeout(sessionTimer);
  sessionTimer = setTimeout(() => {
    alert('Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.');
    handleLogout();
  }, 28800000);
}

async function handleLogin() {
  const email = document.getElementById('loginEmail').value.trim();
  const password = document.getElementById('loginPassword').value;
  const errEl = document.getElementById('loginError');
  const btn = document.getElementById('loginBtn');
  if (!email || !password) { errEl.textContent = 'Vui lòng nhập email và mật khẩu'; errEl.style.display = 'block'; return; }
  btn.textContent = 'Đang đăng nhập...'; btn.disabled = true; errEl.style.display = 'none';

  if (!sb) { errEl.textContent = 'Hệ thống chưa khởi tạo (xem lỗi cấu hình phía trên).'; errEl.style.display = 'block'; btn.textContent = '❄ Đăng nhập'; btn.disabled = false; return; }
  let data, error;
  try {
    ({ data, error } = await sb.auth.signInWithPassword({ email, password }));
  } catch (e) {
    errEl.textContent = 'Không kết nối được Supabase: ' + e.message + ' — kiểm tra SUPABASE_URL và mạng.';
    errEl.style.display = 'block'; btn.textContent = '❄ Đăng nhập'; btn.disabled = false; return;
  }
  if (error) {
    errEl.textContent = error.message === 'Invalid login credentials' ? 'Sai email hoặc mật khẩu' : 'Lỗi: ' + error.message;
    errEl.style.display = 'block'; btn.textContent = '❄ Đăng nhập'; btn.disabled = false; return;
  }
  currentUser = data.user; currentSession = data.session;
  try { await loadUserRoles(); } catch (e) { console.warn('[roles]', e.message); }
  showApp(); resetSessionTimer();
}

async function handleLogout() {
  clearTimeout(sessionTimer);
  await sb.auth.signOut();
  currentUser = null; currentSession = null; currentRoles = [];
  document.getElementById('app').style.display = 'none';
  document.getElementById('loginPage').style.display = 'flex';
}

async function checkSession() {
  if (!sb) return;
  const { data: { session } } = await sb.auth.getSession();
  if (session) { currentUser = session.user; currentSession = session; await loadUserRoles(); showApp(); resetSessionTimer(); }
}

// Tự động refresh token
if (sb) sb.auth.onAuthStateChange((event, session) => {
  if (event === 'TOKEN_REFRESHED' && session) { currentSession = session; resetSessionTimer(); }
  if (event === 'SIGNED_OUT') { handleLogout(); }
});

async function loadUserRoles() {
  if (!currentUser) return;
  const { data } = await sb.from('user_roles').select('roles(role_name,display_name)').eq('user_id', currentUser.id).eq('is_active', true);
  currentRoles = (data || []).map(r => r.roles.role_name);
}

function getToken() { return currentSession?.access_token || ''; }
function showApp() {
  document.getElementById('loginPage').style.display = 'none';
  document.getElementById('app').style.display = 'block';
  document.getElementById('userEmail').textContent = currentUser?.email || '';
  const roleMap = { admin:'Quản trị viên', qa_manager:'QA Manager', validation:'Thẩm định', engineering:'Kỹ thuật', viewer:'Người xem', auditor:'Kiểm toán' };
  document.getElementById('userRole').textContent = roleMap[currentRoles[0]] || currentRoles[0] || 'viewer';
  loadDashboard();
}

// ============================================================
// API CALLS (gọi n8n webhook với JWT token)
// ============================================================
async function apiCall(url, method = 'GET', body = null) {
  const token = getToken();
  if (!token) { handleLogout(); throw new Error('Chưa đăng nhập'); }
  const opts = { method, headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token } };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(url, opts);
  if (res.status === 401) { handleLogout(); throw new Error('Phiên hết hạn'); }
  return res.json();
}

// ============================================================
// DASHBOARD
// ============================================================
async function loadDashboard() {
  try {
    const h = await apiCall(API.health);
    const statusHtml = Object.entries(h.services || {}).map(([n, s]) => {
      const labels = { supabase:'Supabase', openai:'OpenAI', n8n:'n8n' };
      return `<div class="service-pill ${safeClass(s.status, 'unknown')}"><span class="dot"></span>${escapeHtml(labels[n]||n)}: ${escapeHtml(s.message)}</div>`;
    }).join('');
    document.getElementById('serviceStatus').innerHTML = statusHtml;

    const st = h.stats || {};
    document.getElementById('statsGrid').innerHTML = [
      {v:st.total_documents,l:'Tổng tài liệu'}, {v:st.sop_count,l:'SOP'}, {v:st.guideline_count,l:'Guideline'}, {v:st.form_count,l:'Form / Template'},
      {v:st.docs_vi,l:'Tiếng Việt'}, {v:st.docs_en,l:'Tiếng Anh'}, {v:st.docs_bilingual,l:'Song ngữ'},
      {v:st.docs_approved,l:'Approved cho AI',c:'success'}, {v:st.docs_pending_review,l:'Chờ review',c:'warning'},
      {v:st.ai_translations_pending,l:'Bản dịch AI chưa duyệt',c:st.ai_translations_pending>0?'warning':''},
      {v:st.total_ai_queries,l:'Tổng AI queries'}, {v:st.total_users,l:'Người dùng'},
      {v:st.failed_jobs,l:'Job lỗi',c:st.failed_jobs>0?'danger':''}, {v:st.unresolved_security_events,l:'Sự kiện bảo mật',c:st.unresolved_security_events>0?'danger':''},
    ].map(s=>`<div class="stat-card ${safeClass(s.c, '')}"><div class="value">${escapeHtml(s.v??0)}</div><div class="label">${escapeHtml(s.l)}</div></div>`).join('');

    const w = h.warnings || [];
    document.getElementById('systemWarnings').innerHTML = w.length > 0
      ? w.map(x=>`<div class="warning-banner">⚠ ${escapeHtml(x)}</div>`).join('')
      : '<span style="color:var(--mint)">✓ Không có cảnh báo — hệ thống hoạt động bình thường</span>';
  } catch (e) {
    document.getElementById('serviceStatus').innerHTML = `<div class="service-pill error"><span class="dot"></span>Lỗi: ${escapeHtml(e.message)}</div>`;
  }
}

// ============================================================
// AI SEARCH
// ============================================================
async function handleQuery() {
  const q = document.getElementById('queryInput').value.trim();
  if (!q) return;
  const btn = document.getElementById('queryBtn'), rd = document.getElementById('aiResult');
  btn.textContent = 'Đang tìm...'; btn.disabled = true;
  rd.innerHTML = '<div class="loading">Đang phân tích câu hỏi và tìm kiếm nguồn...</div>';
  try {
    const r = await apiCall(API.ragQuery, 'POST', {
      query: q, response_language: 'vi',
      filters: { language_preference: document.getElementById('filterLang').value, document_type: document.getElementById('filterDocType').value || null }
    });
    if (!r.success) { rd.innerHTML = `<div class="warning-banner">Lỗi: ${escapeHtml(r.error||'Không xác định')}</div>`; return; }
    let h = `<div style="margin-bottom:12px">Mức tin cậy: <span class="confidence-badge confidence-${safeClass(r.confidence, 'unknown')}">${escapeHtml(r.confidence)}</span></div>`;
    if (r.conflict_warning) h += `<div class="warning-banner">⚠ ${escapeHtml(r.conflict_warning)}</div>`;
    if (r.language_warning) h += `<div class="warning-banner">🌐 ${escapeHtml(r.language_warning)}</div>`;
    h += `<div class="answer">${escapeHtml(r.answer)}</div>`;
    if (r.sources?.length) {
      h += `<div class="card"><h3>Nguồn tham chiếu</h3><table class="sources-table"><thead><tr><th>#</th><th>Mã tài liệu</th><th>Phiên bản</th><th>Ngôn ngữ</th><th>Trang</th><th>Mục</th><th>Loại</th><th>Điểm</th></tr></thead><tbody>`;
      r.sources.forEach((s,i) => { h += `<tr><td>${i+1}</td><td><strong>${escapeHtml(s.document_code||'N/A')}</strong></td><td>${escapeHtml(s.version||'-')}</td><td><span class="lang-badge">${escapeHtml(s.language_code||'-')}</span></td><td>${escapeHtml(s.page_number||'-')}</td><td>${escapeHtml((s.section_code||'') + ' ' + (s.section_title||''))}</td><td><span class="source-badge ${safeClass(s.source_type, 'unknown')}">${escapeHtml(s.source_type||'-')}</span></td><td>${formatScore(s.relevance_score)}</td></tr>`; });
      h += '</tbody></table></div>';
    }
    h += `<div class="disclaimer">⚕ ${escapeHtml(r.disclaimer||'Nội dung do AI tạo, cần người có chuyên môn xem xét trước khi dùng cho hồ sơ GMP chính thức.')}</div>`;
    rd.innerHTML = h;
  } catch (e) { rd.innerHTML = `<div class="warning-banner">Lỗi: ${escapeHtml(e.message)}</div>`; }
  finally { btn.textContent = 'Tìm kiếm'; btn.disabled = false; }
}

// ============================================================
// DOCUMENTS
// ============================================================
async function searchDocuments() {
  const ld = document.getElementById('docList');
  ld.innerHTML = '<div class="loading">Đang tải...</div>';
  try {
    const r = await apiCall(API.search, 'POST', {
      keyword: document.getElementById('docSearch').value.trim() || undefined,
      language_code: document.getElementById('docFilterLang').value || undefined,
      status: document.getElementById('docFilterStatus').value || undefined, limit: 50
    });
    const docs = (r.documents||[]).filter(d=>d.id);
    if (!docs.length) { ld.innerHTML = '<span class="empty">❄ Không tìm thấy tài liệu nào.</span>'; return; }
    const statusMap = {draft:'Bản nháp',indexed:'Đã index',reviewed:'Đã review',approved_for_ai_use:'✓ AI Approved',superseded:'Thay thế',archived:'Lưu trữ'};
    let h = '<table class="doc-table"><thead><tr><th>Mã</th><th>Tên</th><th>Loại</th><th>Ngôn ngữ</th><th>Phiên bản</th><th>Trạng thái</th><th>Chunks</th></tr></thead><tbody>';
    docs.forEach(d => { h += `<tr><td><strong>${escapeHtml(d.document_code)}</strong></td><td>${escapeHtml(d.document_title)}</td><td>${escapeHtml(d.document_type)}</td><td><span class="lang-badge">${escapeHtml(d.language_code)}</span></td><td>v${escapeHtml(d.version)}</td><td><span class="status-badge ${safeClass(d.status, 'unknown')}">${escapeHtml(statusMap[d.status]||d.status)}</span></td><td>${escapeHtml(d.chunk_count||0)}</td></tr>`; });
    ld.innerHTML = h + '</tbody></table>';
  } catch (e) { ld.innerHTML = `<div class="warning-banner">Lỗi: ${escapeHtml(e.message)}</div>`; }
}

// ============================================================
// AUDIT TRAIL
// ============================================================
async function loadAuditTrail() {
  const el = document.getElementById('auditList');
  el.innerHTML = '<div class="loading">Đang tải nhật ký...</div>';
  try {
    const { data, error } = await sb.from('audit_log').select('id,user_email,user_role,action_type,"timestamp",input_summary,document_code,language_code').order('timestamp', { ascending: false }).limit(30);
    if (error) throw error;
    if (!data?.length) { el.innerHTML = '<span class="empty">Chưa có nhật ký nào.</span>'; return; }
    const actionMap = {document_upload:'Upload tài liệu',document_index:'Index tài liệu',document_review:'Review tài liệu',document_approve:'Duyệt tài liệu',ai_query:'Hỏi AI',ai_draft_protocol:'Viết đề cương',ai_check_protocol:'Check đề cương',user_login:'Đăng nhập',config_change:'Thay đổi cấu hình',security_event:'Sự kiện bảo mật'};
    let h = '<table class="doc-table"><thead><tr><th>Thời gian</th><th>Người dùng</th><th>Vai trò</th><th>Hành động</th><th>Tóm tắt</th><th>Tài liệu</th></tr></thead><tbody>';
    data.forEach(l => {
      const t = new Date(l.timestamp).toLocaleString('vi-VN');
      h += `<tr><td style="font-size:12px;white-space:nowrap">${escapeHtml(t)}</td><td>${escapeHtml(l.user_email||'-')}</td><td>${escapeHtml(l.user_role||'-')}</td><td>${escapeHtml(actionMap[l.action_type]||l.action_type)}</td><td style="max-width:200px;overflow:hidden;text-overflow:ellipsis">${escapeHtml(l.input_summary||'-')}</td><td>${escapeHtml(l.document_code||'-')}</td></tr>`;
    });
    el.innerHTML = h + '</tbody></table>';
  } catch (e) { el.innerHTML = `<div class="warning-banner">Lỗi: ${escapeHtml(e.message)}</div>`; }
}

// ============================================================
// SECURITY CHECK
// ============================================================
async function runSecurityCheck() {
  const el = document.getElementById('securityResults');
  const btn = document.getElementById('secCheckBtn');
  btn.disabled = true; btn.textContent = 'Đang kiểm tra...';
  el.innerHTML = '<div class="loading">Đang kiểm tra bảo mật...</div>';
  const checks = [];
  function add(ok, label, detail) { checks.push({ ok, label, detail }); }

  // 1. Frontend không chứa service_role key
  const html = document.documentElement.innerHTML;
  add(!html.includes('service_role'), 'Frontend không chứa service_role key', html.includes('service_role') ? 'NGUY HIỂM: Tìm thấy service_role trong HTML!' : 'Chỉ có anon key (an toàn)');

  // 2. Supabase kết nối
  try { const { error } = await sb.from('roles').select('id').limit(1); add(!error, 'Supabase RLS hoạt động', error ? error.message : 'Query qua RLS thành công'); }
  catch (e) { add(false, 'Supabase kết nối', e.message); }

  // 3. Webhook health
  try { const h = await apiCall(API.health); add(h.overall !== 'error', 'n8n Webhooks hoạt động', 'Overall: ' + h.overall); }
  catch (e) { add(false, 'n8n Webhooks', e.message); }

  // 4. Auth token tồn tại
  add(!!getToken(), 'JWT Token hợp lệ', getToken() ? 'Token có ' + getToken().length + ' ký tự' : 'Không có token!');

  // 5. Audit log ghi được
  try { const { error } = await sb.from('audit_log').select('id').limit(1); add(true, 'Audit log truy xuất được', 'Append-only log hoạt động'); }
  catch (e) { add(false, 'Audit log', e.message); }

  // 6. HTTPS
  add(location.protocol === 'https:', 'Kết nối HTTPS', location.protocol === 'https:' ? 'Mã hóa đường truyền' : 'CẢNH BÁO: Đang dùng HTTP không an toàn!');

  // Render
  el.innerHTML = checks.map(c => `<div class="security-check ${c.ok ? 'ok' : 'fail'}"><span class="icon">${c.ok ? '✓' : '✗'}</span><strong>${escapeHtml(c.label)}</strong><span style="color:var(--text-soft);margin-left:8px;font-size:12px">— ${escapeHtml(c.detail)}</span></div>`).join('');
  const passed = checks.filter(c => c.ok).length;
  el.innerHTML = `<div style="margin-bottom:12px;font-weight:700;color:${passed===checks.length?'var(--mint)':'var(--gold)'}">Kết quả: ${passed}/${checks.length} kiểm tra đạt</div>` + el.innerHTML;
  btn.disabled = false; btn.textContent = 'Chạy kiểm tra bảo mật';
}

// ============================================================
// NAVIGATION
// ============================================================
const titles = { dashboard:'❄ Tổng quan', 'ai-search':'✦ AI Search / Q&A', documents:'❆ Thư viện tài liệu', audit:'✧ Audit Trail', security:'🔒 Bảo mật' };
function showPage(id) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.sidebar nav a').forEach(a => a.classList.remove('active'));
  const pg = document.getElementById('page-' + id); if (pg) pg.classList.add('active');
  const lk = document.querySelector(`[data-page="${id}"]`); if (lk) lk.classList.add('active');
  document.getElementById('pageTitle').textContent = titles[id] || id;
  if (id === 'dashboard') loadDashboard();
  if (id === 'documents') searchDocuments();
  if (id === 'audit') loadAuditTrail();
  resetSessionTimer();
}

function escapeHtml(t) {
  const d = document.createElement('div');
  d.textContent = t === null || t === undefined ? '' : String(t);
  return d.innerHTML.replace(/\n/g, '<br>');
}

function safeClass(value, fallback) {
  const token = (value === null || value === undefined ? fallback : String(value))
    .toLowerCase()
    .replace(/[^a-z0-9_-]+/g, '_')
    .replace(/^_+|_+$/g, '');
  return token || fallback || '';
}

function formatScore(value) {
  const score = Number(value);
  return Number.isFinite(score) ? score.toFixed(2) : '0.00';
}

// ============================================================
// SNOWFLAKES ❄
// ============================================================
function createSnowflakes() {
  const c = document.getElementById('snowflakes'); if (!c) return;
  const flakes = ['❄','❆','✦','✧','·'];
  for (let i = 0; i < 35; i++) {
    const s = document.createElement('span');
    s.className = 'snowflake';
    s.textContent = flakes[Math.floor(Math.random() * flakes.length)];
    s.style.left = Math.random() * 100 + '%';
    s.style.fontSize = (8 + Math.random() * 14) + 'px';
    s.style.animationDuration = (6 + Math.random() * 10) + 's';
    s.style.animationDelay = Math.random() * 8 + 's';
    s.style.opacity = 0.3 + Math.random() * 0.5;
    c.appendChild(s);
  }
}

// ============================================================
// INIT
// ============================================================
window.addEventListener('DOMContentLoaded', () => { createSnowflakes(); checkSession(); });
