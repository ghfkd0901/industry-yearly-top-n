import streamlit as st
import pandas as pd
import os

# 1. 데이터 로드
@st.cache_data
def load_commercial_data():
    file_path = 'data/commercial_heating_monthly_summary.csv'
    if not os.path.exists(file_path):
        return None
    return pd.read_csv(file_path, encoding='utf-8-sig')

df_comm = load_commercial_data()

if df_comm is not None:
    df_comm['매출년도'] = df_comm['매출년월'].str[:4]
    df_comm['월'] = df_comm['매출년월'].str[5:]
    
    # --- 사이드바 설정 ---
    st.sidebar.markdown("### 📊 전체 현황 요약")
    total_customers_all = df_comm['고객명'].nunique()
    total_volume_all = df_comm['사용량'].sum()
    
    col_side1, col_side2 = st.sidebar.columns(2)
    col_side1.metric("총 고객 수", f"{total_customers_all:,}명")
    col_side2.metric("총 판매량(㎥)", f"{total_volume_all/1000000:,.1f}M")
    st.sidebar.divider()

    st.sidebar.header("⚙️ 보고서 필터 설정")
    selected_year = st.sidebar.selectbox("📅 분석 연도", sorted(df_comm['매출년도'].unique(), reverse=True))
    
    # [유지] 상품(용도) 필터링
    all_products = sorted(df_comm['상품'].unique().tolist())
    selected_products = st.sidebar.multiselect("🏷️ 용도 선택", all_products, default=all_products)

    unit_option = st.sidebar.radio("📊 분석 단위", ["㎥", "천㎥", "MJ", "GJ"], index=0, horizontal=True)

    # 최소 연간합계 기준 500,000 설정
    if unit_option == "㎥":
        target_col, div_factor, default_min = "사용량", 1, 500000
    elif unit_option == "천㎥":
        target_col, div_factor, default_min = "사용량", 1000, 500
    elif unit_option == "MJ":
        target_col, div_factor, default_min = "사용열량", 1, 20000000 
    else: # GJ
        target_col, div_factor, default_min = "사용열량", 1000, 20000

    min_value = st.sidebar.number_input(f"🔍 최소 연간 합계 ({unit_option})", min_value=0, value=default_min)

    # --- 데이터 가공 ---
    df_filtered = df_comm[
        (df_comm['매출년도'] == selected_year) & 
        (df_comm['상품'].isin(selected_products))
    ].copy()
    
    df_filtered['display_value'] = df_filtered[target_col] / div_factor

    # 피벗 테이블 생성
    pivot = df_filtered.pivot_table(
        index='고객명', columns='월', values='display_value', aggfunc='sum', margins=True, margins_name="연간 합계"
    ).fillna(0)

    if not pivot.empty:
        main_data = pivot.drop("연간 합계").sort_values('연간 합계', ascending=False)
        main_data.insert(0, '순위', range(1, len(main_data) + 1))
        max_rank = int(main_data['순위'].max())

        st.sidebar.subheader("🏆 순위 범위 및 UI 설정")
        col_r1, col_r2 = st.sidebar.columns(2)
        with col_r1:
            start_rank = st.number_input("시작 순위", min_value=1, max_value=max_rank, value=1)
        with col_r2:
            end_rank = st.number_input("종료 순위", min_value=1, max_value=max_rank, value=min(50, max_rank))

        font_size = st.sidebar.number_input("📏 표 글자 크기 (px)", min_value=10, max_value=50, value=15)

        # 필터링 적용
        final_filtered = main_data[
            (main_data['순위'] >= start_rank) & 
            (main_data['순위'] <= end_rank) &
            (main_data['연간 합계'] >= min_value)
        ]

        if not final_filtered.empty:
            total_sum = final_filtered.drop(columns='순위').sum()
            total_row = pd.DataFrame([total_sum], index=["선택범위 합계"])
            total_row.insert(0, '순위', '-')
            report_df = pd.concat([final_filtered, total_row])
        else:
            report_df = pd.DataFrame()

        # 스타일 및 출력
        st.markdown(f"""
        <style>
            .report-header {{ text-align: center; color: black; }}
            .report-table {{ width: 100%; border-collapse: collapse; font-size: {font_size}px; margin-top: 20px; }}
            .report-table th {{ background-color: #2c3e50; color: white; padding: 12px; border: 1px solid #ddd; text-align: center; }}
            .report-table td {{ padding: 10px; border: 1px solid #ddd; text-align: right; }}
            .rank-col {{ text-align: center !important; background-color: #f8f9fa; font-weight: bold; width: 60px; }}
            .name-col {{ text-align: left !important; font-weight: bold; min-width: 180px; }}
            .total-row {{ background-color: #f1c40f !important; font-weight: bold; }}
        </style>
        """, unsafe_allow_html=True)

        # --- 보고서 제목 및 상세 정보 (상품 정보 포함) ---
        st.markdown(f"<h2 class='report-header'>🏨 {selected_year}년 주요고객 현황 ({start_rank}위 ~ {end_rank}위)</h2>", unsafe_allow_html=True)
        
        # 💡 선택된 상품명을 리스트업하여 표시
        products_display = ", ".join(selected_products) if selected_products else "없음"
        st.markdown(f"""
            <div class='report-header' style='font-size: 16px; color: #333;'>
                <b>분석 단위:</b> {unit_option} | 
                <b>조회 기준:</b> 연간 합계 {min_value:,.0f} 이상 | 
                <b>선택 상품:</b> {products_display}
            </div>
        """, unsafe_allow_html=True)

        if not report_df.empty:
            html_table = '<table class="report-table"><thead><tr><th>순위</th><th>고객명</th>'
            months = [f"{str(m).zfill(2)}" for m in range(1, 13)]
            for m in months: html_table += f'<th>{m}월</th>'
            html_table += '<th>연간 합계</th></tr></thead><tbody>'

            for idx, row in report_df.iterrows():
                row_class = "total-row" if idx == "선택범위 합계" else ""
                html_table += f'<tr class="{row_class}">'
                html_table += f'<td class="rank-col">{row["순위"]}</td>'
                html_table += f'<td class="name-col">{idx}</td>'
                for m in months: html_table += f'<td>{row.get(m, 0):,.0f}</td>'
                html_table += f'<td>{row["연간 합계"]:,.0f}</td></tr>'
            html_table += '</tbody></table>'
            st.markdown(html_table, unsafe_allow_html=True)
            st.caption(f"※ 본 리포트는 {selected_year}년도 실적 데이터를 기준으로 자동 생성되었습니다.")
        else:
            st.warning("조건에 맞는 데이터가 없습니다.")
    else:
        st.warning("데이터가 비어있습니다.")
else:
    st.error("데이터 파일을 찾을 수 없습니다.")