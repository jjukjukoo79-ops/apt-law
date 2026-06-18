"""
분양 영업 레이더 — CLI 엔트리

크롤러 DB(announcements)를 읽어 법률 영업 리드로 변환하고
Excel + 단독 HTML 대시보드로 내보낸다.

사용:
  python sales_radar.py                # DB 읽어 리드 변환 → output/영업레이더_*.xlsx + .html
  python sales_radar.py --open         # 생성 후 브라우저로 대시보드 열기
  python sales_radar.py --demo         # 샘플 데이터로 대시보드 미리보기 (DB 불필요)
  python sales_radar.py --html-only    # 엑셀 생략, HTML만

선행: python main.py 로 분양공고를 먼저 수집해두면 실제 데이터로 동작.
"""
import os
import sys
import argparse
import webbrowser

sys.path.insert(0, os.path.dirname(__file__))

from config import DB_PATH, OUTPUT_DIR
from sales.radar import enrich_all, apply_snapshot, state_path_for
from sales.dashboard import write_dashboard, write_share_copy


def resolve_share_dir(arg) -> str:
    """--share 값 → 공유 폴더 경로. 값 생략 시 바탕화면."""
    if arg in (None, "", "DESKTOP"):
        return os.path.join(os.path.expanduser("~"), "Desktop")
    return arg


def load_rows_from_db() -> list[dict]:
    """DB 에서 announcements 전체를 dict 리스트로."""
    if not os.path.exists(DB_PATH):
        return []

    from sqlalchemy.orm import Session
    from models.database import Announcement, get_engine

    engine = get_engine(DB_PATH)
    with Session(engine) as session:
        rows = session.query(Announcement).all()
        return [
            {c.name: getattr(r, c.name) for c in Announcement.__table__.columns}
            for r in rows
        ]


def demo_rows() -> list[dict]:
    """대시보드 미리보기용 샘플 (실제 데이터 아님)."""
    def c(builder, dev):
        return f"cnstrctEntrpsNm: {builder}\nbsnsMbyNm: {dev}"

    return [
        {"source": "청약홈", "title": "[샘플]별내자이더스타", "housing_type": "아파트",
         "region_sido": "경기", "region_sigungu": "남양주시", "supply_count": 1500,
         "move_in_date": "202609", "content": c("GS건설", "별내지구도시개발조합"), "url": ""},
        {"source": "청약홈", "title": "[샘플]송도더샵센트럴", "housing_type": "아파트",
         "region_sido": "인천", "region_sigungu": "연수구", "supply_count": 980,
         "move_in_date": "202612", "content": c("포스코이앤씨", "송도국제도시개발"), "url": ""},
        {"source": "청약홈", "title": "[샘플]동탄레이크파크", "housing_type": "아파트",
         "region_sido": "경기", "region_sigungu": "화성시", "supply_count": 540,
         "move_in_date": "202706", "content": c("DL이앤씨", "동탄2지역주택조합"), "url": ""},
        {"source": "청약홈", "title": "[샘플]래미안원펜타스", "housing_type": "아파트",
         "region_sido": "서울", "region_sigungu": "서초구", "supply_count": 1200,
         "move_in_date": "202403", "content": c("삼성물산", "신반포15차재건축조합"), "url": ""},
        {"source": "LH청약센터", "title": "[샘플]청주테크노폴리스B2", "housing_type": "공공분양",
         "region_sido": "충북", "region_sigungu": "청주시", "supply_count": 760,
         "move_in_date": "202109", "content": c("계룡건설", "한국토지주택공사"), "url": ""},
        {"source": "청약홈", "title": "[샘플]해운대비스타동원", "housing_type": "아파트",
         "region_sido": "부산", "region_sigungu": "해운대구", "supply_count": 320,
         "move_in_date": "201609", "content": c("동원개발", "동원건설산업"), "url": ""},
        {"source": "청약홈", "title": "[샘플]구도심리버뷰(만료)", "housing_type": "아파트",
         "region_sido": "대구", "region_sigungu": "북구", "supply_count": 410,
         "move_in_date": "201401", "content": c("중흥토건", "중흥주택"), "url": ""},
        {"source": "청약홈", "title": "[샘플]오피스텔더스카이", "housing_type": "오피스텔",
         "region_sido": "서울", "region_sigungu": "영등포구", "supply_count": 150,
         "move_in_date": "202611", "content": c("현대건설", "여의도PFV"), "url": ""},
        {"source": "공공데이터포털", "title": "[샘플]입주일미상단지", "housing_type": "아파트",
         "region_sido": "전남", "region_sigungu": "여수시", "supply_count": 600,
         "move_in_date": "", "content": c("한양", "여수개발"), "url": ""},
    ]


def export_excel(leads: list[dict], output_dir: str) -> str:
    import pandas as pd
    from datetime import datetime

    os.makedirs(output_dir, exist_ok=True)
    cols = {
        "tier": "등급", "lead_score": "리드점수", "title": "단지명", "housing_type": "유형",
        "source": "출처", "sido": "시도", "sigungu": "시군구", "supply_count": "세대수",
        "developer": "시행사", "builder": "시공사", "move_in": "입주예정",
        "reg_status": "집단등기상태", "reg_dday": "집단등기D-day", "reg_window_open": "영업창OPEN",
        "defect_status": "하자상태", "defect_phase": "다음만료차수", "defect_expiry": "하자만료일",
        "defect_dday": "하자D-day", "url": "공고URL",
    }
    df = pd.DataFrame(leads)
    df = df[[k for k in cols if k in df.columns]].rename(columns=cols)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(output_dir, f"영업레이더_{ts}.xlsx")

    with pd.ExcelWriter(path, engine="openpyxl") as w:
        df.to_excel(w, sheet_name="전체리드", index=False)
        reg = df[df["집단등기상태"].isin(["OPEN", "대기"])].sort_values("집단등기D-day")
        reg.to_excel(w, sheet_name="집단등기_타겟", index=False)
        defect = df[df["하자상태"].isin(["적기", "모니터링"])].sort_values("하자D-day")
        defect.to_excel(w, sheet_name="하자소송_타겟", index=False)

    print(f"Excel 저장: {path} ({len(df)}건)")
    return path


def main():
    ap = argparse.ArgumentParser(description="분양 영업 레이더")
    ap.add_argument("--demo", action="store_true", help="샘플 데이터로 미리보기 (DB 불필요)")
    ap.add_argument("--open", action="store_true", help="생성 후 브라우저로 열기")
    ap.add_argument("--html-only", action="store_true", help="엑셀 생략, HTML 대시보드만")
    ap.add_argument("--share", nargs="?", const="DESKTOP", default=None,
                    help="직원 공유용 사본 생성 (기본: 바탕화면, 경로 지정 가능)")
    args = ap.parse_args()

    rows = demo_rows() if args.demo else load_rows_from_db()
    if not rows:
        print("수집된 공고가 없습니다. 먼저 `python main.py` 로 수집하거나 `--demo` 로 미리보세요.")
        return

    leads = enrich_all(rows)
    print(f"\n리드 변환: {len(leads)}건")
    print(f"  집단등기 영업창 OPEN: {sum(1 for x in leads if x['reg_status']=='OPEN')}건")
    print(f"  하자 만료 적기(1년내): {sum(1 for x in leads if x['defect_status']=='적기')}건")

    # 전일 대비 신규 알림 (데모는 기준선 오염 방지로 제외)
    if not args.demo:
        new_cnt, first = apply_snapshot(leads, state_path_for(DB_PATH))
        print(f"  [신규] 오늘 신규 알림: {new_cnt}건" + ("  (최초 실행 — 기준선 저장)" if first else ""))

    if not args.html_only:
        try:
            export_excel(leads, OUTPUT_DIR)
        except Exception as e:
            print(f"[엑셀 생략] {e}")

    html_path = write_dashboard(leads, OUTPUT_DIR)

    if args.share is not None:
        write_share_copy(leads, resolve_share_dir(args.share))

    if args.open:
        webbrowser.open("file://" + os.path.abspath(html_path))


if __name__ == "__main__":
    main()
