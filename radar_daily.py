"""
분양 영업 레이더 — 일일 자동 러너 (v1.5)

수집 → 리드 변환 → 전일 대비 신규 감지 → 대시보드 갱신을 하나로 묶는다.
대시보드 상단의 '🔔 오늘의 레이더' 패널에서 매일 알려주는 알림을
집단등기·하자 탭과 동시에 확인할 수 있다.

사용:
  python radar_daily.py                 # 1회: 수집 + 리드변환 + 대시보드 갱신
  python radar_daily.py --open          # 갱신 후 브라우저로 대시보드 열기
  python radar_daily.py --no-crawl      # 수집 생략(이미 쌓인 DB로 갱신만)
  python radar_daily.py --schedule           # 매일 08:00 자동 실행 (상주)
  python radar_daily.py --schedule --at 07:30  # 실행 시각 지정

선행: 최초 1회는 `python main.py` 또는 `--crawl` 으로 공고를 수집해야 한다.
크롤링 의존성(requests·bs4·fake_useragent 등)은 --no-crawl 시 불필요.
"""
import os
import sys
import argparse
import webbrowser
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from config import DB_PATH, OUTPUT_DIR, REGION_CODES
from sales.radar import enrich_all, apply_snapshot, state_path_for
from sales.dashboard import write_dashboard, write_share_copy
from sales_radar import load_rows_from_db, resolve_share_dir


def crawl_once() -> int:
    """전 출처 1회 수집. 신규 건수 반환. (크롤러 의존성 필요)"""
    from models.database import init_db, upsert_announcement
    from crawlers.applyhome import crawl_all_regions as crawl_applyhome
    from crawlers.lh import crawl_lh
    from crawlers.sh import crawl_sh
    from crawlers.public_data import crawl_public_data

    engine = init_db(DB_PATH)
    new = 0

    def save(items):
        nonlocal new
        for it in items:
            if upsert_announcement(engine, it):
                new += 1

    save(crawl_applyhome(REGION_CODES, fetch_detail=True))
    save(crawl_lh(REGION_CODES, fetch_detail=True))
    save(crawl_sh(fetch_detail=True))
    save(crawl_public_data(REGION_CODES))
    return new


def build(open_browser: bool = False, share_dir: str | None = None):
    """DB → 리드 변환 → 스냅샷 → 대시보드 (+ 공유 사본)."""
    rows = load_rows_from_db()
    if not rows:
        print("DB가 비어 있습니다. 먼저 수집하세요 (`python main.py`).")
        return None

    leads = enrich_all(rows)
    new_cnt, first = apply_snapshot(leads, state_path_for(DB_PATH))
    print(f"리드 {len(leads)}건 / 영업창 OPEN {sum(1 for x in leads if x['reg_status']=='OPEN')}건 "
          f"/ 하자 적기 {sum(1 for x in leads if x['defect_status']=='적기')}건 "
          f"/ 신규 {new_cnt}건" + ("  (최초 실행 — 기준선 저장)" if first else ""))

    path = write_dashboard(leads, OUTPUT_DIR)
    if share_dir is not None:
        write_share_copy(leads, share_dir)
    if open_browser:
        webbrowser.open("file://" + os.path.abspath(path))
    return path


def job(no_crawl: bool, open_browser: bool, share_dir: str | None = None):
    print(f"\n[{datetime.now():%Y-%m-%d %H:%M:%S}] 레이더 갱신 시작")
    if not no_crawl:
        try:
            print(f"  신규 수집: {crawl_once()}건")
        except Exception as e:
            print(f"  [수집 생략] {e}")
    build(open_browser, share_dir)
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] 완료")


def main():
    ap = argparse.ArgumentParser(description="분양 영업 레이더 — 일일 자동 러너")
    ap.add_argument("--no-crawl", action="store_true", help="수집 생략, DB로 갱신만")
    ap.add_argument("--open", action="store_true", help="갱신 후 브라우저로 열기")
    ap.add_argument("--schedule", action="store_true", help="매일 자동 실행(상주)")
    ap.add_argument("--at", default="08:00", help="자동 실행 시각 HH:MM (기본 08:00)")
    ap.add_argument("--share", nargs="?", const="DESKTOP", default=None,
                    help="직원 공유용 사본 생성 (기본: 바탕화면, 경로 지정 가능)")
    args = ap.parse_args()

    share_dir = resolve_share_dir(args.share) if args.share is not None else None

    if not args.schedule:
        job(args.no_crawl, args.open, share_dir)
        return

    import schedule
    import time
    print(f"스케줄러 시작 — 매일 {args.at} 레이더 갱신")
    job(args.no_crawl, args.open, share_dir)  # 시작 시 1회 즉시
    schedule.every().day.at(args.at).do(job, no_crawl=args.no_crawl, open_browser=False, share_dir=share_dir)
    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
