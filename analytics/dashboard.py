"""
dashboard.py — 주차장 입출차 데이터 분석 대시보드 (Streamlit)

실행:
    streamlit run dashboard.py

데이터: demo_parking.db (generate_sample_data.py로 생성한 합성 데이터,
        실제 카메라 배포 시 lpr_system/parking.db로 경로만 바꾸면 동일하게 동작)
"""
import os
import sqlite3

import pandas as pd
import plotly.express as px
import streamlit as st

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo_parking.db")

st.set_page_config(page_title="주차장 데이터 분석", layout="wide")


@st.cache_data
def load(query: str) -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


# ── 입출차 페어링 (LAG 윈도우 함수) + 요금 계산 ────────────────
VISITS_SQL = """
WITH paired AS (
    SELECT plate_text, event_type, timestamp,
           LAG(timestamp)  OVER (PARTITION BY plate_text ORDER BY timestamp) AS prev_ts,
           LAG(event_type) OVER (PARTITION BY plate_text ORDER BY timestamp) AS prev_type
    FROM entry_exit_log
)
SELECT
    plate_text,
    prev_ts AS entry_time,
    timestamp AS exit_time,
    CAST((JULIANDAY(timestamp) - JULIANDAY(prev_ts)) * 24 * 60 AS INTEGER) AS duration_min
FROM paired
WHERE event_type = 'EXIT' AND prev_type = 'ENTRY'
"""


def calc_fee(duration_min: int) -> int:
    if duration_min <= 10:
        return 0
    over = max(0, duration_min - 30)
    units = -(-over // 10)
    return min(15000, 1000 + units * 500)


visits = load(VISITS_SQL)
visits["entry_time"] = pd.to_datetime(visits["entry_time"])
visits["exit_time"] = pd.to_datetime(visits["exit_time"])
visits["fee"] = visits["duration_min"].apply(calc_fee)
visits["date"] = visits["entry_time"].dt.date
visits["hour"] = visits["entry_time"].dt.hour
WEEKDAY_KR = ["월", "화", "수", "목", "금", "토", "일"]
visits["weekday"] = visits["entry_time"].dt.dayofweek.map(lambda i: WEEKDAY_KR[i])

whitelist = load("SELECT plate_text FROM whitelist")
visits["visitor_type"] = visits["plate_text"].isin(whitelist["plate_text"]).map(
    {True: "정기(화이트리스트)", False: "일반 방문"}
)

# ── 헤더 & KPI ──────────────────────────────────────────────
st.title("주차장 입출차 데이터 분석")
st.caption(
    f"기간: {visits['date'].min()} ~ {visits['date'].max()}  ·  "
    "데이터: LPR 시스템 SQLite 로그 기반 (데모용 합성 데이터)"
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("총 방문 건수", f"{len(visits):,}건")
c2.metric("총 추정 매출", f"{visits['fee'].sum():,}원")
c3.metric("평균 체류시간", f"{visits['duration_min'].mean():.0f}분")
c4.metric("정기 이용 차량", f"{whitelist.shape[0]}대")

st.divider()

# ── 일별 방문·매출 추이 ────────────────────────────────────
daily = visits.groupby("date").agg(visit_count=("plate_text", "count"), revenue=("fee", "sum")).reset_index()
col1, col2 = st.columns(2)
with col1:
    st.subheader("일별 방문 대수 추이")
    st.plotly_chart(px.line(daily, x="date", y="visit_count", markers=True), use_container_width=True)
with col2:
    st.subheader("일별 추정 매출 추이")
    st.plotly_chart(px.bar(daily, x="date", y="revenue"), use_container_width=True)

# ── 시간대별 피크 / 요일별 비교 ──────────────────────────────
col3, col4 = st.columns(2)
with col3:
    st.subheader("시간대별 입차 패턴 (피크타임)")
    hourly = visits.groupby("hour").size().reindex(range(24), fill_value=0).reset_index(name="count")
    st.plotly_chart(px.bar(hourly, x="hour", y="count"), use_container_width=True)
with col4:
    st.subheader("요일별 평균 체류시간")
    wd = visits.groupby("weekday")["duration_min"].mean().reindex(WEEKDAY_KR).reset_index()
    st.plotly_chart(px.bar(wd, x="weekday", y="duration_min"), use_container_width=True)

# ── 체류시간 분포 / 정기 vs 일반 비중 ─────────────────────────
col5, col6 = st.columns(2)
with col5:
    st.subheader("체류시간 구간별 분포")
    bins = [0, 30, 120, 360, 10**6]
    labels = ["~30분", "30분~2시간", "2~6시간", "6시간~"]
    visits["bucket"] = pd.cut(visits["duration_min"], bins=bins, labels=labels)
    bucket_df = visits["bucket"].value_counts().reindex(labels).reset_index()
    bucket_df.columns = ["구간", "건수"]
    st.plotly_chart(px.bar(bucket_df, x="구간", y="건수"), use_container_width=True)
with col6:
    st.subheader("정기 이용 vs 일반 방문 비중")
    st.plotly_chart(px.pie(visits, names="visitor_type"), use_container_width=True)

# ── 재방문 TOP 10 ────────────────────────────────────────────
st.subheader("재방문(단골) 차량 TOP 10")
top10 = (
    visits.groupby("plate_text").size().reset_index(name="visits")
    .sort_values("visits", ascending=False).head(10)
)
st.dataframe(top10, use_container_width=True, hide_index=True)
