# 주차장 입출차 데이터 분석

LPR 시스템(`lpr_system/`)이 SQLite에 쌓는 입출차 로그를 SQL로 분석하고
Streamlit 대시보드로 시각화한다. 검출·인식 파이프라인이 만든 데이터를
비즈니스 인사이트로 바꾸는 것이 목적.

> **데이터 안내**: 실 카메라 배포 전이라 `demo_parking.db`는 합성 데이터다.
> 스키마는 `lpr_system/database.py`와 완전히 동일하므로, 실제 데이터가
> 쌓이면 `DB_PATH`만 `lpr_system/parking.db`로 바꿔 그대로 사용 가능하다.

## 구성

| 파일 | 설명 |
|---|---|
| `generate_sample_data.py` | 오피스 주차장 4주치 합성 데이터 생성 (정기 출퇴근 40대 + 방문 차량) |
| `queries.sql` | 분석 쿼리 모음 — LAG 윈도우 함수로 입/출차 페어링, CTE, RANK 등 |
| `dashboard.py` | Streamlit 대시보드 |
| `demo_parking.db` | 생성된 샘플 DB (재실행 시 자동 갱신) |

## 실행

```bash
python -m venv dash_env
dash_env\Scripts\pip install -r requirements.txt

# (선택) 데이터 재생성
dash_env\Scripts\python generate_sample_data.py

# 대시보드 실행
dash_env\Scripts\python -m streamlit run dashboard.py
```

> `dash_env`는 `lpr_system`의 가상환경(`lpr_env`)과 **완전히 분리**되어 있다.
> streamlit이 요구하는 최신 protobuf가 paddlepaddle(`<=3.20.2` 고정)과
> 충돌하기 때문에, 메인 앱 환경을 건드리지 않도록 독립 venv로 격리했다.

## 분석 내용

- 일별 방문 대수 · 추정 매출 추이
- 시간대별 입차 패턴 (피크타임)
- 요일별 평균 체류시간 (평일 vs 주말)
- 체류시간 구간별 분포
- 정기(화이트리스트) vs 일반 방문 비중
- 재방문(단골) 차량 TOP 10

## SQL 포인트

`entry_exit_log`는 ENTRY/EXIT이 각각 별도 행이라, `LAG() OVER (PARTITION BY plate_text ORDER BY timestamp)`
로 같은 번호판의 직전 이벤트를 끌어와 방문 1건(입차~출차)으로 재구성한다.
요금 계산 로직(`parking_fee.py`)도 CASE 문으로 SQL에 동일하게 이식해
매출을 직접 집계한다. 자세한 쿼리는 `queries.sql` 참고.

---

## 데이터 도구 탐색

같은 데이터셋(`plate_logs`, `entry_exit_log`, `whitelist`)을 SQL 실행 환경에만
머물지 않고 여러 데이터 도구로 직접 다뤄봤다. CSV로 내보낸 뒤 각 도구에
맞는 방식으로 적재·탐색·시각화하는 과정을 연습했다.

**DB Browser for SQLite** — 원본 쿼리 검증
<img src="https://raw.githubusercontent.com/seo941024/LPR_System/master/analytics/assets/sqlite_browser.png" width="700">

**Power Query** — CSV 3개(plate_logs / entry_exit_log / whitelist) 적재 후
테이블 간 관계 구성
<img src="https://raw.githubusercontent.com/seo941024/LPR_System/master/analytics/assets/power_query_model.png" width="700">

**Power BI** — `plate_text` 필터, `event_type`별 집계 시각화
<img src="https://raw.githubusercontent.com/seo941024/LPR_System/master/analytics/assets/power_bi.png" width="700">

**Databricks (PySpark · Spark SQL)** — `spark.table()`로 Delta 테이블 로드,
DataFrame API와 `%sql` 매직 양쪽으로 동일 집계(`plate_color`별 건수) 수행.
JOIN 시 컬럼명 충돌(`AMBIGUOUS_REFERENCE`) 등 실제 디버깅 과정도 거쳤다.
<img src="https://raw.githubusercontent.com/seo941024/LPR_System/master/analytics/assets/databricks_spark.png" width="700">

> 목적은 "같은 질문(색상별 분포, 이벤트별 집계)에 도구별로 어떻게 접근하는가"를
> 비교하는 것 — SQL 엔진(SQLite/Spark SQL), ETL 도구(Power Query),
> BI 시각화(Power BI), 분산처리 프레임워크(PySpark)를 한 데이터셋 기준으로 훑었다.
