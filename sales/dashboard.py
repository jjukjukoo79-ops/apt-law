"""
영업 레이더 대시보드 생성기 — enrich된 리드를 단일 HTML 파일로 출력.
서버 불필요(파일 더블클릭으로 열림). 법무 올인원 네이비 테마.
"""
import os
import json
from datetime import datetime

THEME = {
    "navy": "#1E2761",
    "ice": "#CADCFC",
    "reg": "#534AB7",     # 집단등기 보라
    "defect": "#D85A30",  # 하자 테라코타
}


def build_html(leads: list[dict], generated_at: str) -> str:
    payload = json.dumps(leads, ensure_ascii=False)
    total = len(leads)
    reg_open = sum(1 for x in leads if x["reg_status"] == "OPEN")
    defect_hot = sum(1 for x in leads if x["defect_status"] == "적기")
    new_today = sum(1 for x in leads if x.get("is_new"))

    html = _TEMPLATE
    html = html.replace("__LEADS_JSON__", payload)
    html = html.replace("__GENERATED__", generated_at)
    html = html.replace("__VERSION__", "1.5")
    html = html.replace("__TOTAL__", str(total))
    html = html.replace("__REG_OPEN__", str(reg_open))
    html = html.replace("__DEFECT_HOT__", str(defect_hot))
    html = html.replace("__NEW__", str(new_today))
    return html


def write_dashboard(leads: list[dict], output_dir: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    generated = datetime.now().strftime("%Y-%m-%d %H:%M")
    html = build_html(leads, generated)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(output_dir, f"영업레이더_{ts}.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

    # 올인원 대시보드 링크용 고정 경로 — 항상 최신본으로 덮어쓰기
    latest = os.path.join(output_dir, "영업레이더_최신.html")
    with open(latest, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"대시보드 저장: {path} ({len(leads)}건)")
    print(f"  최신본(대시보드 링크용): {latest}")
    return path


def write_share_copy(leads: list[dict], share_dir: str) -> str:
    """직원 공유용 사본 — 날짜가 붙은 자기완결 HTML 1개. 그대로 전달하면 됨."""
    os.makedirs(share_dir, exist_ok=True)
    html = build_html(leads, datetime.now().strftime("%Y-%m-%d %H:%M"))
    fname = f"영업레이더_공유_{datetime.now():%Y%m%d}.html"
    dest = os.path.join(share_dir, fname)
    with open(dest, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[공유] 공유용 사본 생성: {dest}")
    print("   → 이 파일 1개를 카톡·이메일·공유폴더로 전달하면 직원이 더블클릭으로 엽니다.")
    return dest


_TEMPLATE = r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>분양 영업 레이더 — 법무 올인원</title>
<style>
  :root{--navy:#1E2761;--ice:#CADCFC;--reg:#534AB7;--defect:#D85A30;--bg:#f4f5f9;--line:#e4e6ef;--muted:#6b7280;}
  *{box-sizing:border-box;margin:0;padding:0;}
  body{font-family:'Pretendard','Malgun Gothic',system-ui,sans-serif;background:var(--bg);color:#1f2333;padding:24px;}
  .wrap{max-width:1280px;margin:0 auto;}
  header h1{font-size:22px;color:var(--navy);}
  header p{color:var(--muted);font-size:13px;margin-top:4px;}
  .ver{font-size:12px;background:var(--ice);color:var(--navy);border-radius:6px;padding:2px 8px;vertical-align:middle;font-weight:700;}
  .radar{background:linear-gradient(180deg,#fff,#fbfcff);border:1.5px solid var(--reg);border-radius:14px;padding:14px 16px;margin:14px 0;}
  .radar-head{font-size:15px;font-weight:800;color:var(--navy);margin-bottom:10px;}
  .radar-head .sub{font-weight:500;}
  .newpill{float:right;background:#E1F5EE;color:#0F6E56;border-radius:20px;padding:3px 12px;font-size:12.5px;font-weight:700;}
  .digest{display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:8px;}
  .dcard{display:flex;align-items:center;gap:10px;background:#fff;border:1px solid var(--line);border-radius:10px;padding:8px 11px;}
  .dot{width:9px;height:9px;border-radius:50%;flex-shrink:0;}
  .dot.now{background:#D85A30;} .dot.soon{background:#E0A030;} .dot.later{background:#9FB0C8;}
  .dcard .di{flex:1;min-width:0;}
  .dcard .dt{font-weight:700;color:var(--navy);font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
  .dcard .dm{font-size:11.5px;color:var(--muted);}
  .dcard .dd{font-weight:800;font-size:13px;white-space:nowrap;}
  .catreg{color:var(--reg);} .catdef{color:var(--defect);}
  .new{background:#1D9E75;color:#fff;border-radius:5px;font-size:10px;padding:1px 5px;margin-left:4px;}
  .digest .empty{grid-column:1/-1;}
  .safe{background:#FBEAF0;border:1px solid #ED93B1;color:#72243E;font-size:12.5px;
        border-radius:10px;padding:10px 14px;margin:14px 0;}
  .kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:16px 0;}
  .kpi{background:#fff;border:1px solid var(--line);border-radius:12px;padding:14px 16px;}
  .kpi .n{font-size:26px;font-weight:800;color:var(--navy);}
  .kpi .l{font-size:12px;color:var(--muted);margin-top:2px;}
  .tabs{display:flex;gap:8px;margin:8px 0 14px;}
  .tab{padding:10px 18px;border-radius:10px 10px 0 0;border:1px solid var(--line);
       border-bottom:none;background:#eceeffa0;cursor:pointer;font-weight:700;font-size:14px;color:var(--muted);}
  .tab.active{background:#fff;color:var(--navy);box-shadow:0 -2px 0 var(--reg) inset;}
  .tab.defect.active{box-shadow:0 -2px 0 var(--defect) inset;}
  .controls{display:flex;gap:10px;margin-bottom:10px;flex-wrap:wrap;}
  input,select{padding:8px 12px;border:1px solid var(--line);border-radius:8px;font-size:13px;}
  input{flex:1;min-width:200px;}
  table{width:100%;border-collapse:collapse;background:#fff;border-radius:12px;overflow:hidden;
        border:1px solid var(--line);font-size:13px;}
  th{background:var(--navy);color:#fff;padding:10px 12px;text-align:left;font-weight:600;cursor:pointer;white-space:nowrap;}
  th:hover{background:#2a3580;}
  td{padding:9px 12px;border-top:1px solid var(--line);vertical-align:middle;}
  tr:hover td{background:#f8f9ff;}
  .title{font-weight:700;color:var(--navy);}
  .sub{color:var(--muted);font-size:11.5px;}
  .badge{display:inline-block;padding:2px 9px;border-radius:20px;font-size:11.5px;font-weight:700;}
  .t-S{background:#26215C;color:#fff;} .t-A{background:#534AB7;color:#fff;}
  .t-B{background:#AFA9EC;color:#26215C;} .t-C{background:#e4e6ef;color:#555;}
  .st-OPEN,.st-적기{background:#D85A30;color:#fff;}
  .st-대기,.st-모니터링{background:#E6F1FB;color:#1c4e80;}
  .st-입주후,.st-입주전,.st-만료종료,.st-입주일미상{background:#eef0f5;color:#777;}
  .dday{font-weight:800;}
  .empty{padding:40px;text-align:center;color:var(--muted);}
  a.lnk{color:var(--reg);text-decoration:none;font-size:11.5px;}
  footer{margin-top:18px;color:var(--muted);font-size:11.5px;text-align:center;}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>🛰 분양 영업 레이더 <span class="ver">v__VERSION__</span></h1>
    <p>크롤러 수집 분양공고 → 집단등기·하자소송 영업 타이밍 자동 산출 · 생성 __GENERATED__</p>
  </header>

  <section class="radar">
    <div class="radar-head">🔔 오늘의 레이더 <span class="sub">— 지금 움직여야 할 리드 (긴급순)</span>
      <span class="newpill" id="newpill">🆕 신규 __NEW__</span></div>
    <div id="digest" class="digest"></div>
  </section>

  <div class="safe">⚖ <b>변호사법 안전선</b> — 본 레이더는 내부 리드 선별·우선순위·타이밍 산출용입니다.
    불특정 다수 직접 접촉은 광고규정·§34 위험이 있으니, 접촉은 입주자대표회의 등 정당한 채널을 경유하세요.</div>

  <div class="kpis">
    <div class="kpi"><div class="n">__TOTAL__</div><div class="l">전체 리드</div></div>
    <div class="kpi"><div class="n" style="color:var(--reg)">__REG_OPEN__</div><div class="l">집단등기 영업창 OPEN</div></div>
    <div class="kpi"><div class="n" style="color:var(--defect)">__DEFECT_HOT__</div><div class="l">하자 만료 적기(1년내)</div></div>
    <div class="kpi"><div class="n" style="color:#1D9E75">__NEW__</div><div class="l">🆕 오늘 신규 알림</div></div>
  </div>

  <div class="tabs">
    <div class="tab active" id="tab-reg" onclick="switchTab('reg')">① 집단등기 (입주 임박순)</div>
    <div class="tab defect" id="tab-defect" onclick="switchTab('defect')">② 하자소송 (만료 임박순)</div>
  </div>

  <div class="controls">
    <input id="q" placeholder="단지명·지역·시공사 검색…" oninput="render()">
    <select id="tier" onchange="render()">
      <option value="">전체 등급</option><option>S</option><option>A</option><option>B</option><option>C</option>
    </select>
    <select id="onlyhot" onchange="render()">
      <option value="">전체 상태</option>
      <option value="hot">영업창/적기만</option>
    </select>
  </div>

  <div id="grid"></div>
  <footer>🔒 <b>사내 공유 전용 · 외부 유출 금지</b> &nbsp;·&nbsp; 법무 올인원 · 분양 영업 레이더 &nbsp;·&nbsp; 출처: 청약홈·LH·SH·공공데이터포털</footer>
</div>

<script>
const LEADS = __LEADS_JSON__;
let mode = 'reg';
let sortKey = null, sortDir = -1;

function switchTab(m){
  mode = m;
  document.getElementById('tab-reg').classList.toggle('active', m==='reg');
  document.getElementById('tab-defect').classList.toggle('active', m==='defect');
  sortKey = null;
  render();
}
function dlabel(d){ if(d===null) return '—'; return d>=0 ? 'D-'+d : 'D+'+Math.abs(d); }
function esc(s){ return (s||'').toString().replace(/[<>&]/g,c=>({'<':'&lt;','>':'&gt;','&':'&amp;'}[c])); }

function filtered(){
  const q = document.getElementById('q').value.trim().toLowerCase();
  const tier = document.getElementById('tier').value;
  const hot = document.getElementById('onlyhot').value;
  let rows = LEADS.filter(r=>{
    if(tier && r.tier!==tier) return false;
    if(q){
      const hay=(r.title+' '+r.sido+' '+r.sigungu+' '+r.builder+' '+r.developer).toLowerCase();
      if(!hay.includes(q)) return false;
    }
    if(mode==='reg'){
      if(r.reg_status==='입주일미상') return false;
      if(hot==='hot' && r.reg_status!=='OPEN') return false;
    }else{
      if(r.defect_status==='입주일미상') return false;
      if(hot==='hot' && r.defect_status!=='적기') return false;
    }
    return true;
  });
  const dk = mode==='reg' ? 'reg_dday' : 'defect_dday';
  if(sortKey){
    rows.sort((a,b)=>{ let x=a[sortKey],y=b[sortKey];
      if(typeof x==='string'){x=x||'';y=y||'';return (x>y?1:x<y?-1:0)*sortDir;}
      return ((x??1e9)-(y??1e9))*sortDir; });
  }else{
    rows.sort((a,b)=>(a[dk]??1e9)-(b[dk]??1e9)); // 임박순
  }
  return rows;
}

function render(){
  const rows = filtered();
  const grid = document.getElementById('grid');
  if(!rows.length){ grid.innerHTML='<div class="empty">조건에 맞는 리드가 없습니다. (DB가 비어있다면 <code>--demo</code>로 미리보기)</div>'; return; }

  let head, body;
  if(mode==='reg'){
    head = ['단지','지역','세대수','등급','시행사','입주예정','영업창 OPEN','상태'];
    body = rows.map(r=>`<tr>
      <td><span class="title">${esc(r.title)}</span><br><span class="sub">${esc(r.housing_type)} · ${esc(r.source)}</span></td>
      <td>${esc(r.sido)} ${esc(r.sigungu)}</td>
      <td>${r.supply_count.toLocaleString()}</td>
      <td><span class="badge t-${r.tier}">${r.tier}</span></td>
      <td>${esc(r.developer)||'<span class="sub">미상</span>'}</td>
      <td>${esc(r.move_in)||esc(r.move_in_raw)}</td>
      <td class="sub">${esc(r.reg_window_open)}</td>
      <td><span class="badge st-${r.reg_status}">${r.reg_status}</span> <span class="dday">${dlabel(r.reg_dday)}</span>
          ${r.url?`<br><a class="lnk" href="${esc(r.url)}" target="_blank">공고 ↗</a>`:''}</td>
    </tr>`).join('');
  }else{
    head = ['단지','지역','세대수','등급','시공사','입주일','다음 만료차수','만료일','상태'];
    body = rows.map(r=>`<tr>
      <td><span class="title">${esc(r.title)}</span><br><span class="sub">${esc(r.housing_type)} · ${esc(r.source)}</span></td>
      <td>${esc(r.sido)} ${esc(r.sigungu)}</td>
      <td>${r.supply_count.toLocaleString()}</td>
      <td><span class="badge t-${r.tier}">${r.tier}</span></td>
      <td>${esc(r.builder)||'<span class="sub">미상</span>'}</td>
      <td>${esc(r.move_in)||esc(r.move_in_raw)}</td>
      <td class="sub">${esc(r.defect_phase)}</td>
      <td>${esc(r.defect_expiry)}</td>
      <td><span class="badge st-${r.defect_status}">${r.defect_status}</span> <span class="dday">${dlabel(r.defect_dday)}</span></td>
    </tr>`).join('');
  }
  grid.innerHTML = `<table><thead><tr>${head.map((h,i)=>`<th onclick="sortBy(${i})">${h}</th>`).join('')}</tr></thead><tbody>${body}</tbody></table>`;
}

function sortBy(i){
  const regKeys=['title','sido','supply_count','tier','developer','move_in','reg_window_open','reg_dday'];
  const defKeys=['title','sido','supply_count','tier','builder','move_in','defect_phase','defect_expiry','defect_dday'];
  const k=(mode==='reg'?regKeys:defKeys)[i];
  if(sortKey===k){ sortDir*=-1; } else { sortKey=k; sortDir=1; }
  render();
}

// 🔔 오늘의 레이더 — 두 카테고리 통합, 긴급순. 두 탭과 동시에 항상 노출.
function urgency(d){ if(d===null) return 'later'; if(d<=30) return 'now'; if(d<=90) return 'soon'; return 'later'; }
function renderDigest(){
  const el=document.getElementById('digest');
  const hot=LEADS.filter(r=>r.actionable).sort((a,b)=>(a.alert_dday??1e9)-(b.alert_dday??1e9)).slice(0,12);
  if(!hot.length){ el.innerHTML='<div class="empty" style="padding:14px;color:var(--muted)">오늘 즉시 움직일 리드가 없습니다. (집단등기 영업창 OPEN·하자 만료 적기 발생 시 표시)</div>'; return; }
  el.innerHTML=hot.map(r=>{
    const cat=r.alert_cat==='집단등기'?'<span class="catreg">집단등기</span>':'<span class="catdef">하자</span>';
    const nb=r.is_new?'<span class="new">NEW</span>':'';
    return `<div class="dcard"><span class="dot ${urgency(r.alert_dday)}"></span>
      <div class="di"><div class="dt">${esc(r.title)}${nb}</div>
      <div class="dm">${cat} · ${esc(r.sido)} ${esc(r.sigungu)} · ${r.supply_count.toLocaleString()}세대 · <span class="badge t-${r.tier}" style="padding:0 6px">${r.tier}</span></div></div>
      <div class="dd">${dlabel(r.alert_dday)}</div></div>`;
  }).join('');
}

renderDigest();
render();
</script>
</body>
</html>"""
