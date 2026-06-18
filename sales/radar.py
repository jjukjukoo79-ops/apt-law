"""
영업 레이더 — 분양공고 → 법률 영업 리드 변환 레이어

크롤러가 수집한 announcements 레코드를 읽어 다음을 산출한다.
  · 시공사 / 시행사 파싱 (공고문 전문 content 에서 추출)
  · 집단등기 영업창: 입주 3~6개월 전 선점 타이밍 + D-day
  · 하자담보소송 영업창: 차수별 책임기간(2·3·5·10년) 만료일 + D-day
  · 리드 점수 / 등급: 공급세대수 × 권역 가중

[변호사법 안전선]
이 레이어는 '내부 리드 선별·우선순위·타이밍 산출' 용도로만 설계됐다.
불특정 다수 세대 대상 직접 광고/접촉은 변호사법 광고규정·§34(알선·유인)
위험이 있으므로, 접촉은 입주자대표회의 등 정당한 채널을 경유해야 한다.
"""
import os
import re
import json
import calendar
from datetime import date, datetime

VERSION = "1.5"

# ── 하자담보책임기간(공동주택관리법 시행령 별표4 요지) 대표 차수 ──
# 실제 세부 항목은 더 잘게 나뉘나, 영업 타이밍 산출용 대표 차수만 사용.
DEFECT_PHASES = [
    (2, "2년차 (마감·미장·도배 등)"),
    (3, "3년차 (방수·창호·난방 등)"),
    (5, "5년차 (대지·옹벽·철골 등)"),
    (10, "10년차 (기둥·내력벽 등 주요구조부)"),
]

# 집단등기 영업창: 입주 N개월 전부터 OPEN
REG_WINDOW_MONTHS = 6

# 공고문 content 에서 시공사/시행사를 찾을 후보 키
BUILDER_KEYS = ["cnstrctEntrpsNm", "cnstrtnEntrpsNm", "시공사", "건설업체", "구성업체명"]
DEVELOPER_KEYS = ["bsnsMbyNm", "사업주체", "시행사", "사업주체명"]

# 권역 가중치 (리드 점수 = 세대수 × weight)
METRO = ("서울", "경기", "인천")
WIDE_CITY = ("부산", "대구", "광주", "대전", "울산", "세종")


# ──────────────────────────────────────────────
# 날짜 유틸
# ──────────────────────────────────────────────
def parse_ymd(s) -> date | None:
    """'20250612', '2025-06-12', '2025.06', '202506' 등을 date 로."""
    if not s:
        return None
    digits = re.sub(r"[^0-9]", "", str(s))
    try:
        if len(digits) >= 8:
            return date(int(digits[:4]), int(digits[4:6]), int(digits[6:8]))
        if len(digits) == 6:  # YYYYMM (입주예정 연월)
            return date(int(digits[:4]), int(digits[4:6]), 1)
    except ValueError:
        return None
    return None


def add_months(d: date, n: int) -> date:
    m = d.month - 1 + n
    y = d.year + m // 12
    m = m % 12 + 1
    day = min(d.day, calendar.monthrange(y, m)[1])
    return date(y, m, day)


def add_years(d: date, n: int) -> date:
    try:
        return d.replace(year=d.year + n)
    except ValueError:  # 2/29
        return d.replace(year=d.year + n, day=28)


def _iso(d: date | None) -> str:
    return d.isoformat() if d else ""


# ──────────────────────────────────────────────
# 파싱
# ──────────────────────────────────────────────
def parse_party(content: str | None, keys: list[str]) -> str:
    """공고문 전문(key: value 라인 묶음)에서 시공사/시행사 추출."""
    if not content:
        return ""
    for key in keys:
        m = re.search(rf"{re.escape(key)}\s*[:：]\s*(.+)", content)
        if m:
            val = m.group(1).strip().split("\n")[0].strip(" ,'\"")
            if val and val.lower() not in ("none", "null", "-"):
                return val[:60]
    return ""


def region_weight(sido: str | None) -> float:
    s = sido or ""
    if any(k in s for k in METRO):
        return 1.3
    if any(k in s for k in WIDE_CITY):
        return 1.1
    return 1.0


def lead_tier(score: float) -> str:
    if score >= 1000:
        return "S"
    if score >= 500:
        return "A"
    if score >= 200:
        return "B"
    return "C"


# ──────────────────────────────────────────────
# 영업창 산출
# ──────────────────────────────────────────────
def reg_window(move_in: date | None, today: date) -> dict:
    """집단등기 영업창 상태."""
    if not move_in:
        return {"status": "입주일미상", "dday": None, "window_open": ""}

    open_day = add_months(move_in, -REG_WINDOW_MONTHS)
    dday = (move_in - today).days  # 입주까지 남은 일수 (음수=경과)

    if today < open_day:
        status = "대기"
    elif today <= move_in:
        status = "OPEN"  # 🔥 선점 영업창
    else:
        status = "입주후"

    return {"status": status, "dday": dday, "window_open": _iso(open_day)}


def defect_window(move_in: date | None, today: date) -> dict:
    """하자담보소송 영업창 — 다음 만료 차수와 D-day."""
    if not move_in:
        return {"status": "입주일미상", "phase": "", "expiry": "", "dday": None}

    expiries = [(yr, label, add_years(move_in, yr)) for yr, label in DEFECT_PHASES]
    upcoming = [(yr, label, exp) for yr, label, exp in expiries if exp >= today]

    if not upcoming:  # 10년차까지 모두 경과
        return {"status": "만료종료", "phase": "", "expiry": "", "dday": None}

    yr, label, exp = min(upcoming, key=lambda x: x[2])
    dday = (exp - today).days

    if today < move_in:
        status = "입주전"
    elif dday <= 365:
        status = "적기"  # 🔥 만료 1년 이내 → 감정·제소 준비 적기
    else:
        status = "모니터링"

    return {"status": status, "phase": label, "expiry": _iso(exp), "dday": dday}


# ──────────────────────────────────────────────
# 메인 enrich
# ──────────────────────────────────────────────
def enrich_row(row: dict, today: date | None = None) -> dict:
    """announcements 레코드 1건 → 영업 리드 dict."""
    today = today or datetime.now().date()

    supply = row.get("supply_count") or 0
    try:
        supply = int(supply)
    except (TypeError, ValueError):
        supply = 0

    sido = row.get("region_sido") or ""
    weight = region_weight(sido)
    score = round(supply * weight)

    move_in = parse_ymd(row.get("move_in_date"))
    content = row.get("content") or ""

    reg = reg_window(move_in, today)
    defect = defect_window(move_in, today)

    # 오늘의 레이더 알림 — 지금 움직여야 할 리드만 actionable
    if reg["status"] == "OPEN":
        actionable, alert_cat, alert_dday = True, "집단등기", reg["dday"]
    elif defect["status"] == "적기":
        actionable, alert_cat, alert_dday = True, "하자", defect["dday"]
    else:
        actionable, alert_cat, alert_dday = False, "", None

    source = row.get("source", "")
    title = row.get("title", "")
    move_in_raw = row.get("move_in_date", "")

    return {
        "key": f"{source}|{title}|{move_in_raw}",
        "source": source,
        "title": title,
        "housing_type": row.get("housing_type", ""),
        "sido": sido,
        "sigungu": row.get("region_sigungu", ""),
        "address": row.get("region_address", ""),
        "supply_count": supply,
        "builder": parse_party(content, BUILDER_KEYS),
        "developer": parse_party(content, DEVELOPER_KEYS),
        "announce_date": row.get("announce_date", ""),
        "recruit_end": row.get("recruitment_end", ""),
        "move_in": _iso(move_in),
        "move_in_raw": move_in_raw,
        "lead_score": score,
        "tier": lead_tier(score),
        # 집단등기
        "reg_status": reg["status"],
        "reg_dday": reg["dday"],
        "reg_window_open": reg["window_open"],
        # 하자
        "defect_status": defect["status"],
        "defect_phase": defect["phase"],
        "defect_expiry": defect["expiry"],
        "defect_dday": defect["dday"],
        # 오늘의 레이더 알림
        "actionable": actionable,
        "alert_cat": alert_cat,
        "alert_dday": alert_dday,
        "is_new": False,  # apply_snapshot 에서 전일 대비 신규면 True
        "url": row.get("url", ""),
    }


def enrich_all(rows: list[dict], today: date | None = None) -> list[dict]:
    """레코드 리스트 → 리드 리스트 (점수 내림차순)."""
    leads = [enrich_row(r, today) for r in rows]
    leads.sort(key=lambda x: x["lead_score"], reverse=True)
    return leads


# ──────────────────────────────────────────────
# 전일 대비 신규 감지 (매일 알려주는 레이더)
# ──────────────────────────────────────────────
def state_path_for(db_path: str) -> str:
    return os.path.join(os.path.dirname(db_path) or "data", "radar_state.json")


def _load_state(path: str) -> set[str]:
    try:
        with open(path, encoding="utf-8") as f:
            return set(json.load(f))
    except (OSError, ValueError):
        return set()


def apply_snapshot(leads: list[dict], path: str) -> tuple[int, bool]:
    """전일 스냅샷과 비교해 새로 actionable 이 된 리드를 is_new=True 로 표시.

    최초 실행(상태 파일 없음)은 기준선만 저장하고 신규 0으로 처리한다.
    반환: (신규 알림 건수, 최초실행 여부)
    """
    first_run = not os.path.exists(path)
    prev = _load_state(path)

    now_keys = []
    for lead in leads:
        if lead["actionable"]:
            lead["is_new"] = (not first_run) and (lead["key"] not in prev)
            now_keys.append(lead["key"])
        else:
            lead["is_new"] = False

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(now_keys, f, ensure_ascii=False)

    new_count = sum(1 for x in leads if x["is_new"])
    return new_count, first_run
