---
title: 아파트 공고 수집기
emoji: 🏢
colorFrom: green
colorTo: teal
sdk: streamlit
sdk_version: 1.40.0
app_file: app.py
pinned: false
---

# 🏢 아파트 분양공고 자동 수집기 (Streamlit Web UI)

전국 아파트·오피스텔·도시형생활주택 등 모든 분양공고를 자동 수집합니다.

## 수집 출처
| 출처 | 유형 | 비고 |
|------|------|------|
| 청약홈 (applyhome.co.kr) | 아파트, 오피스텔, 도시형생활주택 | 공고문 전문 포함 |
| LH청약센터 (apply.lh.or.kr) | 공공임대, 공공분양 | |
| SH공사 (i-sh.co.kr) | 서울 공공임대/분양 | |
| 공공데이터포털 API | 아파트 청약공고 | API 키 필요 |

## 설치

```bash
pip install -r requirements.txt
```

## 설정

```bash
cp .env.example .env
# .env 편집 → PUBLIC_DATA_API_KEY 입력 (선택)
```

공공데이터포털 API 키: https://www.data.go.kr → 회원가입 → "주택청약" 검색 → 활용신청

## 사용법

### 1회 수집
```bash
# 전국 전체 수집 (공고문 전문 포함)
python main.py

# 특정 지역만
python main.py --regions 서울 경기 부산

# 공고문 전문 생략 (빠른 목록만)
python main.py --no-detail

# 특정 출처만
python main.py --sources applyhome lh

# CSV로 내보내기 (지역별 분리)
python main.py --export csv

# 모든 형식 내보내기
python main.py --export all
```

### 자동 스케줄러 (60분 주기)
```bash
python scheduler.py
```

### 현황 요약만 확인
```bash
python main.py --summary
```

## 🛰 영업 레이더 v1.5 (법률 영업 활용)

수집한 분양공고를 **법률 영업 리드**로 변환합니다 — 집단등기·하자담보소송 타이밍 자동 산출.
대시보드 상단 **🔔 오늘의 레이더** 패널에서 "지금 움직여야 할 리드"(전일 대비 🆕 신규 포함)를
집단등기·하자 탭과 **동시에** 확인할 수 있습니다.

### 기본 자동화 — 매일 알려주는 레이더 (권장)
```bash
# 수집 → 리드변환 → 신규 감지 → 대시보드 갱신을 한 번에
python radar_daily.py --open

# 매일 08:00 자동 실행 (상주). 시각 변경은 --at 07:30
python radar_daily.py --schedule --at 08:00

# 이미 쌓인 DB로 갱신만 (수집 생략)
python radar_daily.py --no-crawl --open
```

### 단발 변환 / 미리보기
```bash
# DB 읽어 리드 변환 → output/영업레이더_*.xlsx + .html
python sales_radar.py

# 샘플 데이터로 미리보기 (DB·수집 불필요)
python sales_radar.py --demo --open

# 엑셀 생략, HTML 대시보드만 (pandas 미설치 환경)
python sales_radar.py --demo --html-only
```

> 🆕 **신규 감지**: `data/radar_state.json` 에 전일 actionable 리드를 저장해, 다음 실행 때
> 새로 영업창 OPEN·하자 적기가 된 리드만 🆕로 표시합니다. 최초 실행은 기준선만 저장(신규 0).

### 직원 공유 (파일 그대로 전달)
대시보드는 데이터가 내장된 **자기완결 HTML 1개**라, 그 파일만 보내면 직원이 더블클릭으로 엽니다.

```bash
# 바탕화면에 공유용 사본 생성 → 영업레이더_공유_YYYYMMDD.html
python radar_daily.py --share
python sales_radar.py --demo --share          # 데모로 미리 만들어 보기

# 사내 공유폴더/특정 경로로 바로 떨구기
python radar_daily.py --share "D:\공유\영업"
```

- 생성된 `영업레이더_공유_YYYYMMDD.html` 1개를 **카톡·이메일·공유폴더**로 전달.
- 모든 사본 하단에 **🔒 사내 공유 전용 · 외부 유출 금지** 표시가 박혀 있습니다.
- ⚠️ 리드 데이터가 들어있으므로 **공개 웹(GitHub Pages 등)에는 올리지 마세요** — 변호사법 안전선·개인정보.

**산출 항목** (`sales/radar.py`)
- 시공사/시행사: 공고문 전문에서 파싱
- **집단등기 영업창**: 입주 6개월 전 OPEN + 입주까지 D-day
- **하자소송 영업창**: 담보책임기간 차수별(2·3·5·10년) 만료일 + D-day
- 리드 점수/등급: 공급세대수 × 권역 가중(수도권 ×1.3, 광역시 ×1.1) → S/A/B/C

> ⚖ **변호사법 안전선**: 내부 리드 선별·우선순위·타이밍 산출 전용. 불특정 다수 직접 접촉은
> 광고규정·§34(알선·유인) 위험이 있으므로 입주자대표회의 등 정당한 채널을 경유할 것.

## 출력 파일 구조

```
data/
├── apt_crawler.db          # SQLite DB (전체 데이터)
└── output/
    ├── 분양공고_20240612_100000.xlsx   # Excel (지역별 시트)
    ├── 서울_20240612_100000.csv
    ├── 경기_20240612_100000.csv
    └── 전국_20240612_100000.csv
```

## DB 스키마

| 컬럼 | 설명 |
|------|------|
| source | 출처 (청약홈/LH/SH 등) |
| announce_id | 원본 공고 ID |
| title | 공고명 |
| housing_type | 주택유형 |
| region_sido | 시도 |
| region_sigungu | 시군구 |
| region_address | 전체 주소 |
| supply_count | 공급세대수 |
| recruitment_start/end | 청약접수 기간 |
| announce_date | 공고일 |
| winner_date | 당첨자 발표일 |
| move_in_date | 입주예정일 |
| min_price / max_price | 분양가 (만원) |
| url | 공고문 URL |
| content | 공고문 전문 |
