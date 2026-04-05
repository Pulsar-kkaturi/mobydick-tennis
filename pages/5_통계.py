"""
통계 / 시각화 페이지
- 선수별 성적 차트 (총점, 승률, 득실차)
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import db
from logic.scoring import calculate_standings

st.title("통계 & 시각화")

tournament = db.render_tournament_selector()
if not tournament:
    st.stop()

selected_name = tournament["name"]
tid = tournament["id"]

players = db.get_tournament_players(tid)
matches = db.get_matches(tid)
config = db.get_scoring_config(tid)
extra_scores = db.get_extra_scores(tid)

if not players:
    st.info("선수가 없습니다.")
    st.stop()

standings = calculate_standings(players, matches, config, extra_scores)
df = pd.DataFrame(standings)

if df.empty:
    st.info("경기 데이터가 없습니다.")
    st.stop()

df["승률(%)"] = (df["wins"] / df["played"].replace(0, 1) * 100).round(1)

# ── 차트 1: 총점 막대 ─────────────────────────────────────────────────────────
st.subheader("총점 비교")
fig1 = px.bar(
    df.sort_values("total", ascending=True),
    x="total", y="name", orientation="h",
    labels={"total": "총점", "name": "선수"},
    color="total",
    color_continuous_scale="Greens",
    text="total",
)
fig1.update_traces(textposition="outside")
fig1.update_layout(showlegend=False, coloraxis_showscale=False)
st.plotly_chart(fig1, use_container_width=True)

# ── 차트 2: 승률 ──────────────────────────────────────────────────────────────
st.subheader("승률 (%)")
fig2 = px.bar(
    df.sort_values("승률(%)", ascending=True),
    x="승률(%)", y="name", orientation="h",
    labels={"승률(%)": "승률 (%)", "name": "선수"},
    color="승률(%)",
    color_continuous_scale="Blues",
    text="승률(%)",
)
fig2.update_traces(textposition="outside")
fig2.update_layout(showlegend=False, coloraxis_showscale=False)
st.plotly_chart(fig2, use_container_width=True)

# ── 차트 3: 득실차 ────────────────────────────────────────────────────────────
st.subheader("게임 득실차")
df_sorted = df.sort_values("score_diff", ascending=True)
colors = ["#2E7D32" if v >= 0 else "#C62828" for v in df_sorted["score_diff"]]
fig3 = go.Figure(go.Bar(
    x=df_sorted["score_diff"],
    y=df_sorted["name"],
    orientation="h",
    marker_color=colors,
    text=df_sorted["score_diff"],
    textposition="outside",
))
fig3.update_layout(xaxis_title="득실차", yaxis_title="선수")
st.plotly_chart(fig3, use_container_width=True)

# ── 차트 4: 레이더 차트 (상위 5명) ───────────────────────────────────────────
st.subheader("선수별 종합 비교 (상위 5명)")
top5 = df.nlargest(5, "total")

categories = ["승리수", "경기수", "득실차 (양수화)"]

fig4 = go.Figure()
for _, row in top5.iterrows():
    # 득실차는 음수가 있을 수 있어서 최솟값 기준으로 양수화
    min_diff = df["score_diff"].min()
    norm_diff = row["score_diff"] - min_diff
    fig4.add_trace(go.Scatterpolar(
        r=[row["wins"], row["played"], norm_diff],
        theta=categories,
        fill="toself",
        name=row["name"],
    ))

fig4.update_layout(polar=dict(radialaxis=dict(visible=True)), showlegend=True)
st.plotly_chart(fig4, use_container_width=True)
