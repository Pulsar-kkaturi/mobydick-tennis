"""
통계 / 시각화 페이지
- 선수별 성적 차트 (총점, 승률, 득실차)
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import db
from logic.scoring import calculate_standings, get_season_ranking

st.title("통계 & 시각화")

tournaments = db.get_tournaments()
if tournaments:
    st.subheader("시즌별 랭킹포인트 추이")
    approved_tournaments = [t for t in tournaments if t.get("is_approved")]
    if not approved_tournaments:
        st.info("승인된 대회가 없어 시즌 랭킹포인트 추이를 계산할 수 없습니다.")
    else:
        standings_map = {}
        for t in approved_tournaments:
            tid = t["id"]
            if t.get("is_legacy"):
                legacy = db.get_legacy_results(tid)
                standings_map[tid] = [
                    {"name": r["player_name"], "rank": r["rank"]}
                    for r in legacy
                ]
            else:
                players_for_t = db.get_tournament_players(tid)
                if players_for_t:
                    standings_map[tid] = calculate_standings(
                        players_for_t,
                        db.get_matches(tid),
                        db.get_scoring_config(tid),
                        db.get_extra_scores(tid),
                    )

        years = sorted({
            int(str(t["date"])[:4])
            for t in approved_tournaments
            if t.get("date")
        })

        yearly_rows = []
        for year in years:
            year_tournaments = [
                t for t in approved_tournaments
                if t.get("date") and str(t["date"]).startswith(str(year))
            ]
            season_ranking = get_season_ranking(year_tournaments, standings_map)
            for r in season_ranking:
                yearly_rows.append({
                    "연도": year,
                    "선수": r["name"],
                    "연도포인트": r["points"],
                })

        if not yearly_rows:
            st.info("연도별 랭킹포인트 데이터가 없습니다.")
        else:
            df_yearly = pd.DataFrame(yearly_rows)
            all_players = sorted(df_yearly["선수"].unique().tolist())
            full_index = pd.MultiIndex.from_product([all_players, years], names=["선수", "연도"])
            df_trend = (
                df_yearly.set_index(["선수", "연도"])
                .reindex(full_index, fill_value=0)
                .reset_index()
            )
            df_trend["랭킹포인트"] = df_trend.groupby("선수")["연도포인트"].cumsum()

            # 모든 연도에서 포인트 합계가 0인 선수는 제외
            point_sum = df_trend.groupby("선수")["랭킹포인트"].sum()
            valid_players = point_sum[point_sum > 0].index.tolist()
            df_trend = df_trend[df_trend["선수"].isin(valid_players)]

            if df_trend.empty:
                st.info("포인트가 있는 선수가 없습니다.")
            else:
                # 연도별 누적 포인트 순위(1~3위 라벨 표시용)
                df_trend["순위"] = (
                    df_trend.groupby("연도")["랭킹포인트"]
                    .rank(method="dense", ascending=False)
                    .astype(int)
                )
                latest_year = max(years)
                final_rank_df = (
                    df_trend[df_trend["연도"] == latest_year][["선수", "랭킹포인트"]]
                    .sort_values(["랭킹포인트", "선수"], ascending=[False, True])
                )
                legend_order = final_rank_df["선수"].tolist()

                fig_trend = px.line(
                    df_trend.sort_values(["선수", "연도"]),
                    x="연도",
                    y="랭킹포인트",
                    color="선수",
                    markers=True,
                    labels={"연도": "연도", "랭킹포인트": "랭킹포인트", "선수": "선수"},
                    category_orders={"선수": legend_order},
                )
                fig_trend.update_layout(hovermode="x unified")
                fig_trend.update_xaxes(
                    type="category",
                    categoryorder="array",
                    categoryarray=years,
                )
                top3 = df_trend[df_trend["순위"].isin([1, 2, 3])].copy()
                if not top3.empty:
                    top3 = (
                        top3.groupby(["연도", "순위", "랭킹포인트"], as_index=False)
                        .agg({"선수": lambda s: ",".join(sorted(set(s)))})
                    )
                    top3["라벨"] = top3.apply(lambda r: f"{int(r['순위'])}위 {r['선수']}", axis=1)
                    fig_trend.add_trace(
                        go.Scatter(
                            x=top3["연도"],
                            y=top3["랭킹포인트"],
                            mode="text",
                            text=top3["라벨"],
                            textposition="top center",
                            showlegend=False,
                            hoverinfo="skip",
                        )
                    )
                st.plotly_chart(fig_trend, use_container_width=True)
                st.caption("시즌 랭킹포인트 기준: 승인된 대회만 집계하며, 연도별 누적 포인트로 표시합니다.")

st.divider()
st.subheader("대회별 통계")

tournament = db.render_tournament_selector(show_divider=False)
if not tournament:
    st.stop()

selected_name = tournament["name"]
tid = tournament["id"]
selected_date = tournament.get("date")

if selected_date:
    st.caption(f"선택 대회 날짜: {selected_date}")
else:
    st.caption("선택 대회 날짜: 미설정")

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

df["세트 승률(%)"] = (df["wins"] / df["played"].replace(0, 1) * 100).round(1)


def build_game_wins_map(match_rows: list[dict]) -> dict[str, int]:
    """선수별 게임 승리수(획득 게임 합계) 계산."""
    game_wins: dict[str, int] = {}
    for m in match_rows:
        s1 = m.get("team1_score")
        s2 = m.get("team2_score")
        if s1 is None or s2 is None:
            continue
        t1_players = [m.get("team1_player1"), m.get("team1_player2")]
        t2_players = [m.get("team2_player1"), m.get("team2_player2")]
        for p in [name for name in t1_players if name]:
            game_wins[p] = game_wins.get(p, 0) + int(s1)
        for p in [name for name in t2_players if name]:
            game_wins[p] = game_wins.get(p, 0) + int(s2)
    return game_wins


game_wins_map = build_game_wins_map(matches)
df["게임 승리수"] = df["name"].map(game_wins_map).fillna(0).astype(int)

# ── 차트 1: 승점 막대 ─────────────────────────────────────────────────────────
st.subheader("승점 비교")
fig1 = px.bar(
    df.sort_values("total", ascending=True),
    x="total", y="name", orientation="h",
    labels={"total": "승점", "name": "선수"},
    color="total",
    color_continuous_scale="Greens",
    text="total",
)
fig1.update_traces(textposition="outside")
fig1.update_layout(showlegend=False, coloraxis_showscale=False)
st.plotly_chart(fig1, use_container_width=True)

st.markdown("**승점 계산 방식**")
active_rules = [row for row in config.values() if row.get("is_active")]
if active_rules:
    for row in active_rules:
        st.caption(f"- {row['label']}: {row['score_value']}점")
else:
    st.caption("- 활성화된 승점 항목이 없습니다.")

# ── 차트 2: 승률 ──────────────────────────────────────────────────────────────
st.subheader("세트 승률 (%)")
fig2 = px.bar(
    df.sort_values("세트 승률(%)", ascending=True),
    x="세트 승률(%)", y="name", orientation="h",
    labels={"세트 승률(%)": "세트 승률 (%)", "name": "선수"},
    color="세트 승률(%)",
    color_continuous_scale="Blues",
    text="세트 승률(%)",
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

categories = ["승점", "세트 승률", "게임 득실차", "세트 승리수", "게임 승리수"]


def normalize_to_100(series: pd.Series) -> pd.Series:
    """지표를 0~100으로 정규화. 값이 모두 같으면 100으로 고정."""
    min_v = series.min()
    max_v = series.max()
    if max_v == min_v:
        return pd.Series([100.0] * len(series), index=series.index)
    return (series - min_v) / (max_v - min_v) * 100.0


radar_df = df.copy()
radar_df["norm_total"] = normalize_to_100(radar_df["total"])
radar_df["norm_win_rate"] = normalize_to_100(radar_df["세트 승률(%)"])
radar_df["norm_score_diff"] = normalize_to_100(radar_df["score_diff"])
radar_df["norm_wins"] = normalize_to_100(radar_df["wins"])
radar_df["norm_game_wins"] = normalize_to_100(radar_df["게임 승리수"])

fig4 = go.Figure()
top5_radar = radar_df[radar_df["name"].isin(top5["name"])].copy()
top5_radar = top5_radar.merge(top5[["name", "total"]], on="name", how="left").sort_values("total", ascending=False)
line_colors = ["#1E88E5", "#D81B60", "#43A047", "#FB8C00", "#8E24AA"]
for i, (_, row) in enumerate(top5_radar.iterrows()):
    fig4.add_trace(go.Scatterpolar(
        r=[
            row["norm_total"],
            row["norm_win_rate"],
            row["norm_score_diff"],
            row["norm_wins"],
            row["norm_game_wins"],
        ],
        theta=categories,
        fill="toself",
        name=row["name"],
        line=dict(color=line_colors[i % len(line_colors)], width=2),
        marker=dict(color=line_colors[i % len(line_colors)]),
        fillcolor=line_colors[i % len(line_colors)],
        opacity=0.28,
    ))

fig4.update_layout(
    polar=dict(
        radialaxis=dict(visible=True, range=[0, 100]),
        angularaxis=dict(rotation=90, direction="clockwise"),
    ),
    showlegend=True,
)
st.caption("레이더 차트는 지표별 단위 차이를 줄이기 위해 0~100 정규화 기준으로 표시합니다.")
st.plotly_chart(fig4, use_container_width=True)
