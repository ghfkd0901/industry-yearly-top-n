import streamlit as st
import pandas as pd
import os

# 1. 데이터 로드
@st.cache_data
def load_monthly_data():
    file_path = 'data/industry_monthly_summary.csv'
    if not os.path.exists(file_path):
        return None
    return pd.read_csv(file_path, encoding='utf-8-sig')

df_monthly = load_monthly_data()

if df_monthly is not None:
    # 데이터 기본 전처리
    df_monthly['매출년도'] = df_monthly['매출년월'].str[:4]
    df_monthly['월'] = df_monthly['매출년월'].str[5:]
    
    # --- 사이드바 설정 ---
    st.sidebar.header("⚙️ 보고서 설정")
    
    # 분석 연도 선택
    selected_year = st.sidebar.selectbox("📅 분석 연도", sorted(df_monthly['매출년도'].unique(), reverse=True))

    # 1. 분석 단위 선택 (라디오 버튼 + 직관적인 이름)
    unit_option = st.sidebar.radio(
        "📊 분석 단위 선택", 
        ["㎥", "천㎥", "MJ", "GJ"],
        index=0,
        horizontal=True # 가로로 배치하여 공간 절약
    )

    # 2. 단위에 따른 변환 계수 및 기본 필터값 설정 (핵심 로직)
    if unit_option == "㎥":
        target_col, div_factor, default_min = "사용량", 1, 1000000
    elif unit_option == "천㎥":
        target_col, div_factor, default_min = "사용량", 1000, 1000
    elif unit_option == "MJ":
        target_col, div_factor, default_min = "사용열량", 1, 40000000 # MJ 기준 (㎥ 대비 약 40배 가정)
    else: # GJ
        target_col, div_factor, default_min = "사용열량", 1000, 40000
    
    # 3. 최소 연간 합계 입력 (단위에 따라 default_min이 자동으로 바뀜)
    min_value = st.sidebar.number_input(
        f"🔍 최소 연간 합계 ({unit_option})", 
        min_value=0, 
        value=default_min, 
        step=default_min // 10 if default_min > 0 else 100
    )

    font_size = st.sidebar.slider("📏 표 글자 크기 (px)", 10, 30, 15)

    # --- 데이터 가공 ---
    df_year = df_monthly[df_monthly['매출년도'] == selected_year].copy()
    
    # 단위 변환 적용
    df_year[target_col] = df_year[target_col] / div_factor

    # 피벗 테이블 생성
    pivot = df_year.pivot_table(
        index='고객명', columns='월', values=target_col, aggfunc='sum', margins=True, margins_name="연간 합계"
    ).fillna(0)

    # 필터링 적용
    pivot_filtered = pivot[pivot['연간 합계'] >= min_value].sort_values('연간 합계', ascending=False)
    
    # 순위 데이터 구성
    report_df = pivot_filtered.copy()
    if "연간 합계" in report_df.index:
        actual_customers = report_df.drop("연간 합계")
        actual_customers.insert(0, '순위', range(1, len(actual_customers) + 1))
        total_row = report_df.loc[["연간 합계"]]
        total_row.insert(0, '순위', '')
        report_df = pd.concat([actual_customers, total_row])

    # --- CSS 및 스타일링 ---
    st.markdown(f"""
    <style>
        .report-header {{ text-align: center; color: black; font-family: 'Malgun Gothic', sans-serif; }}
        .report-table {{ width: 100%; border-collapse: collapse; font-size: {font_size}px; margin-top: 20px; }}
        .report-table th {{ background-color: #2c3e50; color: white; padding: 12px; border: 1px solid #ddd; text-align: center; }}
        .report-table td {{ padding: 10px; border: 1px solid #ddd; text-align: right; }}
        .rank-col {{ text-align: center !important; background-color: #f8f9fa; font-weight: bold; width: 60px; }}
        .name-col {{ text-align: left !important; font-weight: bold; min-width: 180px; }}
        .total-row {{ background-color: #f1c40f !important; color: black; font-weight: bold; }}
    </style>
    """, unsafe_allow_html=True)

    # --- 보고서 본문 ---
    st.markdown(f"<h2 class='report-header'>🏭 {selected_year}년 산업용 주요고객 월별 현황 보고서</h2>", unsafe_allow_html=True)
    st.markdown(f"<p class='report-header' style='font-size: 16px;'>조회 기준: 연간 합계 {min_value:,.0f} {unit_option} 이상 (단위: {unit_option})</p>", unsafe_allow_html=True)

    # HTML 테이블 생성
    html_table = '<table class="report-table"><thead><tr><th>순위</th><th>고객명</th>'
    months = [f"{str(m).zfill(2)}" for m in range(1, 13)]
    for m in months: html_table += f'<th>{m}월</th>'
    html_table += '<th>연간 합계</th></tr></thead><tbody>'

    for idx, row in report_df.iterrows():
        row_class = "total-row" if idx == "연간 합계" else ""
        html_table += f'<tr class="{row_class}">'
        html_table += f'<td class="rank-col">{row["순위"]}</td>'
        html_table += f'<td class="name-col">{idx}</td>'
        for m in months:
            html_table += f'<td>{row.get(m, 0):,.0f}</td>'
        html_table += f'<td>{row["연간 합계"]:,.0f}</td></tr>'
    html_table += '</tbody></table>'

    st.markdown(html_table, unsafe_allow_html=True)
    st.caption(f"※ 본 리포트는 {selected_year}년도 실적 데이터를 기준으로 자동 생성되었습니다.")

else:
    st.error("데이터 파일을 찾을 수 없습니다. 경로를 확인해주세요.")