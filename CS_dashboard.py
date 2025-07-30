import streamlit as st
import pandas as pd
import numpy as np
import json
import datetime
import matplotlib.pyplot as plt
import matplotlib as mpl
import altair as alt
import re
import plotly.express as px


@st.cache_data
def load_data(path):
    data = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            item = json.loads(line)
            def extract_level(tags, type_name, level):
                for t in (tags or []):
                    if t.startswith(f"{type_name}/"):
                        parts = t.split("/")
                        if len(parts) > level:
                            return parts[level]
                return None
            item["서비스유형"] = extract_level(item.get("tags"), "서비스유형", 1)
            item["서비스유형_2차"] = extract_level(item.get("tags"), "서비스유형", 2)
            item["고객유형"] = extract_level(item.get("tags"), "고객유형", 1)
            item["문의유형"] = extract_level(item.get("tags"), "문의유형", 1)
            item["문의유형_2차"] = extract_level(item.get("tags"), "문의유형", 2)
            item["firstAskedAt"] = pd.to_datetime(item.get("firstAskedAt"), errors='coerce')
            item["month"] = item["firstAskedAt"].strftime('%Y-%m') if pd.notnull(item["firstAskedAt"]) else None
            # cs_satisfaction 펼치기
            if "cs_satisfaction" in item and isinstance(item["cs_satisfaction"], dict):
                for k, v in item["cs_satisfaction"].items():
                    item[k] = v
            data.append(item)
    return pd.DataFrame(data)

def hms_to_seconds(hms_str):
    if not hms_str or pd.isna(hms_str):
        return None
    try:
        h, m, s = map(int, str(hms_str).split(":"))
        return h * 3600 + m * 60 + s
    except:
        return None

def extract_name(label):
    if label == "전체":
        return label
    return label.rsplit(" (", 1)[0]

stopwords = [
    "안녕하세요", "감사합니다", "네", "고맙습니다", "수고하세요", "수고하셨습니다",
    "감사", "문의", "확인", "예", "잘 부탁드립니다", "넵", "혹시", "제가", "맞습니다",
    "수 있을까요", "지금"
]




DATA_PATH = "cs_chat_4-7.jsonl"
df = load_data(DATA_PATH)
# mediumType 컬럼이 있는 경우에만 필터링
if "mediumType" in df.columns:
    df = df[df["mediumType"] != "phone"].reset_index(drop=True)

st.title("CS 대시보드")

# ===================== 1. 필터 UI: 한 줄에 모두 =========================
# 4월 1일부터로 고정
min_date = datetime.date(2024, 4, 1)
if not df['firstAskedAt'].isna().all():
    max_date = df['firstAskedAt'].max().date()
else:
    max_date = datetime.date.today()

# 1줄(6칸)로 기간, 유형 선택 배치
col1, col2, col3, col4, col5, col6 = st.columns([2, 1, 1, 1, 1, 1])

with col1:
    기간 = st.date_input("기간", (min_date, max_date), min_value=min_date, max_value=max_date, format="YYYY-MM-DD")
with col2:
    고객유형 = st.selectbox("고객유형", ["전체"] + sorted(df["고객유형"].dropna().unique()))
with col3:
    문의유형 = st.selectbox("문의유형", ["전체"] + sorted(df["문의유형"].dropna().unique()))
with col4:
    temp_filtered_2차 = df
    if 고객유형 != "전체":
        temp_filtered_2차 = temp_filtered_2차[temp_filtered_2차["고객유형"] == 고객유형]
    if 문의유형 != "전체":
        temp_filtered_2차 = temp_filtered_2차[temp_filtered_2차["문의유형"] == 문의유형]
    문의2_counts = temp_filtered_2차["문의유형_2차"].value_counts().sort_values(ascending=False)
    문의유형2_options = [f"{k} ({v})" for k, v in 문의2_counts.items() if v > 0 and pd.notnull(k)]
    문의유형_2차_label = st.selectbox("문의유형 2차", ["전체"] + 문의유형2_options)
    문의유형_2차 = extract_name(문의유형_2차_label)
with col5:
    서비스유형 = st.selectbox("서비스유형", ["전체"] + sorted(df["서비스유형"].dropna().unique()))
with col6:
    temp_filtered_서비스2 = df
    if 고객유형 != "전체":
        temp_filtered_서비스2 = temp_filtered_서비스2[temp_filtered_서비스2["고객유형"] == 고객유형]
    if 문의유형 != "전체":
        temp_filtered_서비스2 = temp_filtered_서비스2[temp_filtered_서비스2["문의유형"] == 문의유형]
    if 서비스유형 != "전체":
        temp_filtered_서비스2 = temp_filtered_서비스2[temp_filtered_서비스2["서비스유형"] == 서비스유형]
    서비스2_counts = temp_filtered_서비스2["서비스유형_2차"].value_counts().sort_values(ascending=False)
    서비스유형2_options = [f"{k} ({v})" for k, v in 서비스2_counts.items() if v > 0 and pd.notnull(k)]
    서비스유형_2차_label = st.selectbox("서비스유형 2차", ["전체"] + 서비스유형2_options)
    서비스유형_2차 = extract_name(서비스유형_2차_label)

# 기간 필터 적용
start_date, end_date = 기간
기간필터 = (df['firstAskedAt'].dt.date >= start_date) & (df['firstAskedAt'].dt.date <= end_date)
df = df[기간필터].reset_index(drop=True)

# 4월 1일 이전 데이터 제거 (2월, 3월 데이터 제외)
df = df[df['firstAskedAt'].dt.date >= datetime.date(2024, 4, 1)].reset_index(drop=True)

# 필터 적용
cond = pd.Series([True] * len(df))
if 고객유형 != "전체":
    cond &= (df["고객유형"] == 고객유형)
if 문의유형 != "전체":
    cond &= (df["문의유형"] == 문의유형)
if 문의유형_2차 != "전체":
    cond &= (df["문의유형_2차"] == 문의유형_2차)
if 서비스유형 != "전체":
    cond &= (df["서비스유형"] == 서비스유형)
if 서비스유형_2차 != "전체":
    cond &= (df["서비스유형_2차"] == 서비스유형_2차)

filtered = df[cond].reset_index(drop=True)
st.write(f"필터링 결과: {len(filtered)}건")

# ---- 월별 문의량 추이 ----
if not filtered.empty:
    st.subheader("CS 문의량 추이")
    date_group = st.selectbox("단위 선택", ["월간", "주간"], key="period_select")

    filtered = filtered.copy()
    filtered["month"] = filtered["firstAskedAt"].dt.to_period('M').astype(str)
    filtered["week"] = filtered["firstAskedAt"].dt.to_period('W').astype(str)

    if date_group == "월간":
        period_counts = filtered.groupby('month').size().reset_index(name="문의량")
        period_counts["월"] = period_counts["month"].apply(lambda x: str(x)[-2:])
        chart = alt.Chart(period_counts).mark_line(point=True).encode(
            x=alt.X("월:N", axis=alt.Axis(labelAngle=0, title="월")),
            y=alt.Y("문의량:Q", title="CS 문의량"),
            tooltip=["월", "문의량"]
        ).properties(width=650, height=300)
        st.altair_chart(chart, use_container_width=True)
    else:
        # 주차별 집계
        period_counts = filtered.groupby('week').size().reset_index(name="문의량")
        period_counts["월"] = period_counts["week"].apply(lambda x: x[5:7])

        # 월 바뀔 때만 월레이블 표시, 나머지는 빈칸
        month_label = []
        prev_month = ""
        for m in period_counts["월"]:
            if m != prev_month:
                month_label.append(m)
                prev_month = m
            else:
                month_label.append("")
        period_counts["월레이블"] = month_label

        # 라인 그래프(x축 주차), 월레이블은 아래 텍스트로 오버레이
        line = alt.Chart(period_counts).mark_line(point=True).encode(
            x=alt.X("week:N", axis=alt.Axis(title="월", labels=False)),  # x축 라벨 안보이게!
            y=alt.Y("문의량:Q", title="CS 문의량"),
            tooltip=["week", "문의량"]
        )
        labels = alt.Chart(period_counts).mark_text(
            dy=260, fontSize=13, fontWeight="bold", color="white"
        ).encode(
            x=alt.X("week:N"),
            y=alt.value(0),  # 그래프 아래로
            text=alt.Text("월레이블:N")
        )
        chart = (line + labels).properties(width=650, height=300)
        st.altair_chart(chart, use_container_width=True)
    # ------- 2. 월별 평균 시간 (분 단위) -------
    st.subheader("월간 응답/해결 시간")
    st.caption("y축 단위: 분(min)")

    time_keys = ["operationWaitingTime", "operationAvgReplyTime", "operationTotalReplyTime", "operationResolutionTime"]
    time_keys_kr = {
        "operationWaitingTime": "첫응답시간",
        "operationAvgReplyTime": "평균응답시간",
        "operationTotalReplyTime": "총응답시간",
        "operationResolutionTime": "해결시간"
    }

    # 월 컬럼 추가
    filtered["month"] = filtered["firstAskedAt"].dt.to_period('M').astype(str)

    # 시간컬럼별 월별 평균 계산 (분 단위)
    avg_time_df = pd.DataFrame()
    avg_time_df["month"] = sorted(filtered["month"].dropna().unique())
    for eng_key in time_keys:
        col_minutes = filtered.groupby('month')[eng_key].apply(lambda s: s.dropna().map(hms_to_seconds).mean() / 60 if not s.dropna().empty else None)
        avg_time_df[time_keys_kr[eng_key]] = avg_time_df["month"].map(col_minutes)

    avg_time_df["월"] = avg_time_df["month"].apply(lambda x: str(x)[-2:])

    # long 포맷
    ordered_keys = ["첫응답시간", "평균응답시간", "총응답시간", "해결시간"]
    avg_long = avg_time_df.melt(id_vars=['월'], value_vars=ordered_keys, var_name='시간종류', value_name='분')

    avg_time_chart = alt.Chart(avg_long).mark_line(point=True).encode(
        x=alt.X('월:N', axis=alt.Axis(labelAngle=0, title="월")),
        y=alt.Y('분:Q', title="평균 시간(분)"),
        color=alt.Color('시간종류:N', legend=alt.Legend(title="시간 종류")),
        tooltip=['월', '시간종류', '분']
    ).properties(width=650, height=300)
 
    st.altair_chart(avg_time_chart, use_container_width=True)

    # ===================== 문의유형별 변화 트리맵 =====================
    단위 = st.selectbox("단위 선택", ["월간", "주간", "일간"], key="change_period3")
    if 단위 == "월간":
        filtered["period"] = filtered["firstAskedAt"].dt.to_period('M').astype(str)
    elif 단위 == "주간":
        filtered["period"] = filtered["firstAskedAt"].dt.to_period('W').astype(str)
    else:
        filtered["period"] = filtered["firstAskedAt"].dt.date.astype(str)

    periods = sorted(filtered["period"].unique())
    if len(periods) >= 2:
        latest, prev = periods[-1], periods[-2]
    else:
        st.warning("비교할 기간이 2개 이상 필요합니다.")
        st.stop()

    now_df = filtered[filtered["period"] == latest].groupby("문의유형").size().rename("이번")
    prev_df = filtered[filtered["period"] == prev].groupby("문의유형").size().rename("이전")
    comp_df = pd.concat([now_df, prev_df], axis=1).fillna(0)
    comp_df["변화량"] = comp_df["이번"] - comp_df["이전"]
    comp_df["넓이"] = comp_df["변화량"].abs()
    comp_df["색"] = comp_df["변화량"]

    # 트리맵 표시용 텍스트
    comp_df["표시"] = comp_df["변화량"].apply(lambda x: f"{int(x):+d}")

    comp_df = comp_df.reset_index()

    if comp_df["넓이"].sum() == 0:
        st.info("문의량 변화가 없습니다.")
    else:
        fig = px.treemap(
            comp_df,
            path=["문의유형"],
            values="넓이",
            color="색",
            color_continuous_scale=["blue", "white", "red"],
            color_continuous_midpoint=0,
            hover_data={"변화량": True, "넓이": False, "색": False},
            custom_data=["표시"],  # 이거!
        )
        fig.update_traces(
            texttemplate="<b>%{label}</b><br>%{customdata[0]}",  # ← 여기!
            textposition="middle center"
        )
        fig.update_layout(margin=dict(t=30, l=0, r=0, b=0))
        st.subheader(f"문의유형별 {단위} 문의량 변화")
        st.plotly_chart(fig, use_container_width=True)

    # 고객유형별 CS 문의량 집계
    top_n = 5
    고객유형_counts = df["고객유형"].value_counts().dropna()
    if len(고객유형_counts) > top_n:
        top = 고객유형_counts.iloc[:top_n]
        others = 고객유형_counts.iloc[top_n:].sum()
        plot_counts = pd.concat([top, pd.Series({"기타": others})])
    else:
        plot_counts = 고객유형_counts

    if not plot_counts.empty:
        st.subheader("고객유형별 CS 문의량")
        plot_counts_df = plot_counts.reset_index()
        plot_counts_df.columns = ["고객유형", "문의량"]
        plot_counts_df["퍼센트"] = plot_counts_df["문의량"] / plot_counts_df["문의량"].sum() * 100
        # 범례에 퍼센트까지 합친 새 컬럼
        plot_counts_df["라벨"] = plot_counts_df.apply(
            lambda x: f"{x['고객유형']} ({x['퍼센트']:.1f}%)", axis=1
        )

        donut = alt.Chart(plot_counts_df).mark_arc(innerRadius=60, outerRadius=120).encode(
            theta=alt.Theta("문의량:Q", stack=True),
            color=alt.Color(
                "라벨:N",
                sort=plot_counts_df["라벨"].tolist(),  # ▶ 수동 정렬 (높은 순)
                legend=alt.Legend(title="고객유형(비율)")
            ),
            tooltip=[
                alt.Tooltip("고객유형:N", title="고객유형"),
                alt.Tooltip("문의량:Q", title="문의량"),
                alt.Tooltip("퍼센트:Q", format=".1f", title="비율(%)")
            ]
        ).properties(
            width=400,
            height=400
        )
        st.altair_chart(donut, use_container_width=True)
    else:
        st.info("고객유형 데이터가 없습니다.")
    


    # ------------------ CSat 분석 (비활성화) ------------------
    # csat_score_cols = ["A-1", "A-2", "A-4", "A-5"]
    # csat_text_cols = ["A-3", "A-6"]

    # st.header("CSat(고객만족도) 분석")
    # csat_avg = filtered[csat_score_cols].mean().reset_index()
    # csat_avg.columns = ["문항", "평균점수"]
    # chart3 = alt.Chart(csat_avg).mark_bar().encode(
    #     x=alt.X("평균점수:Q",
    #     title="평균 점수",
    #     scale=alt.Scale(domain=[0, 5], nice=False),     # 1~5로 고정, 소수점 없이
    #     axis=alt.Axis(values=[0, 1, 2, 3, 4, 5], format='.0f') # 눈금 값 직접 지정, 정수로 표기)
    #     ),
    #     y=alt.Y("문항:N", sort='-x', title="문항"),
    #     tooltip=["문항", "평균점수"]
    # )
    # st.subheader("1. CSat 문항별 평균 점수")
    # st.altair_chart(chart3, use_container_width=True)

    # st.subheader("2. 유형별 CSat 교차분석")
    # groupby_options = {
    #     "고객유형": "고객유형",
    #     "문의유형": "문의유형"
    # }
    # group_col = st.selectbox("분석할 분류(유형) 선택", list(groupby_options.keys()), key="cross_group")
    # group_col_df = groupby_options[group_col]
    # if group_col_df in filtered.columns:
    #     selected_csat = st.selectbox("비교할 CSat 항목 선택", csat_score_cols, key="csat_cross")
    #     gb = filtered.groupby(group_col_df)[selected_csat].mean().reset_index()
    #     gb.columns = [group_col_df, "평균점수"]
    #     gb = gb[gb["평균점수"].notna() & (gb["평균점수"] > 0)]
    #     chart4 = alt.Chart(gb).mark_bar().encode(
    #         x=alt.X("평균점수:Q", title="평균 점수",
    #                 scale=alt.Scale(domain=[0, 5], nice=False),     # 1~5로 고정, 소수점 없이
    #                 axis=alt.Axis(values=[0, 1, 2, 3, 4, 5], format='.0f') # 눈금 값 직접 지정, 정수로 표기)
    #         ),
    #         y=alt.Y(f"{group_col_df}:N", sort='-x', title=group_col_df),
    #         tooltip=[group_col_df, "평균점수"]
    #         )
    #         st.altair_chart(chart4, use_container_width=True)

    # st.header("3. CSat 점수 분포")
    # selected_hist = st.selectbox("점수 분포 볼 항목 선택", csat_score_cols, key="csat_hist2")
    # filtered_scores = filtered[selected_hist].dropna().astype(int)

    # score_bins = pd.Series([1, 2, 3, 4, 5], name="점수")
    # score_counts = filtered_scores.value_counts().reindex(score_bins, fill_value=0).sort_index()

    # # DataFrame으로 변환 후 컬럼명 지정
    # score_counts_df = score_counts.reset_index()
    # score_counts_df.columns = ["점수", "건수"]

    # import altair as alt

    # chart = alt.Chart(score_counts_df).mark_bar().encode(
    #     x=alt.X("점수:O", axis=alt.Axis(title="점수")),
    #     y=alt.Y("건수:Q", axis=alt.Axis(title="건수")),
    #     tooltip=["점수", "건수"]
    # ).properties(width=400, height=300)

    # st.altair_chart(chart, use_container_width=True)

    # st.subheader("4. 월별 CSat 점수")
    # trend_csat = st.selectbox("CSat 항목 선택", csat_score_cols, key="csat_trend")

    # # 'month'에서 월만 추출
    # trend_df = filtered.groupby("month")[trend_csat].mean().reset_index()
    # trend_df["월"] = trend_df["month"].apply(lambda x: str(x)[-2:])  # 마지막 두자리만

    # import altair as alt

    # trend_chart = alt.Chart(trend_df).mark_line(point=True).encode(
    #     x=alt.X("월:N", axis=alt.Axis(title="월", labelAngle=0)),
    #     y=alt.Y(f"{trend_csat}:Q", axis=alt.Axis(title="평균 점수")),
    #     tooltip=["월", trend_csat]
    # ).properties(width=500, height=300)

    # st.altair_chart(trend_chart, use_container_width=True)



else:
    st.warning("선택한 조건에 해당하는 데이터가 없습니다.")

if st.checkbox("원본 데이터 보기"):
    st.dataframe(filtered)
