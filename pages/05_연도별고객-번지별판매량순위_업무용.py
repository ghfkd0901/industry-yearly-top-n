import streamlit as st
import pandas as pd
import os
import io

# 1. 페이지 설정 및 데이터 로드
st.set_page_config(page_title="업무용 사업장별 주요고객 순위 분석", layout="wide")

@st.cache_data
def load_commercial_data():
    file_path = 'data/commercial_heating_site_summary.csv' 
    if not os.path.exists(file_path):
        return None
    # 번지순번의 앞자리 0을 유지하기 위해 문자열로 로드
    return pd.read_csv(file_path, encoding='utf-8-sig', dtype={'번지순번': str})

df_comm = load_commercial_data()

if df_comm is not None:
    # 데이터 전처리
    df_comm['매출년도'] = df_comm['매출년월'].str[:4]
    df_comm['월'] = df_comm['매출년월'].str[5:]
    
    # --- 사이드바 설정 ---
    st.sidebar.markdown("### 📊 업무용 현황 요약")
    total_sites = len(df_comm.groupby(['고객명', '번지순번']))
    total_volume_all = df_comm['사용량'].sum()
    
    col_side1, col_side2 = st.sidebar.columns(2)
    col_side1.metric("총 사업장 수", f"{total_sites:,}개")
    col_side2.metric("총 판매량(㎥)", f"{total_volume_all/1000000:,.1f}M")
    st.sidebar.divider()

    st.sidebar.header("⚙️ 업무용 보고서 설정")
    selected_year = st.sidebar.selectbox("📅 분석 연도", sorted(df_comm['매출년도'].unique(), reverse=True))
    
    all_products = sorted(df_comm['상품'].unique().tolist())
    selected_products = st.sidebar.multiselect("🏷️ 용도 선택", all_products, default=all_products)

    unit_option = st.sidebar.radio("📊 분석 단위", ["㎥", "천㎥", "MJ", "GJ"], index=0, horizontal=True)

    if unit_option == "㎥":
        target_col, div_factor = "사용량", 1
    elif unit_option == "천㎥":
        target_col, div_factor = "사용량", 1000
    elif unit_option == "MJ":
        target_col, div_factor = "사용열량", 1
    else: # GJ
        target_col, div_factor = "사용열량", 1000

    min_value = st.sidebar.number_input(f"🔍 최소 연간 합계 ({unit_option})", min_value=0, value=100000)

    # --- 데이터 가공 ---
    df_filtered = df_comm[
        (df_comm['매출년도'] == selected_year) & 
        (df_comm['상품'].isin(selected_products))
    ].copy()
    
    df_filtered['display_value'] = df_filtered[target_col] / div_factor

    # 피벗 테이블 생성
    pivot = df_filtered.pivot_table(
        index=['고객명', '번지순번'], 
        columns='월', 
        values='display_value', 
        aggfunc='sum', 
        margins=True, 
        margins_name="연간 합계"
    ).fillna(0)

    if not pivot.empty:
        # 합계 제외 후 정렬 및 순위 부여
        main_data = pivot.drop("연간 합계", level=0, errors='ignore').sort_values('연간 합계', ascending=False)
        main_data.insert(0, '순위', range(1, len(main_data) + 1))
        max_rank = int(main_data['순위'].max())

        st.sidebar.subheader("🏆 순위 범위 및 UI 설정")
        col_r1, col_r2 = st.sidebar.columns(2)
        with col_r1:
            start_rank = st.number_input("시작 순위", min_value=1, max_value=max_rank, value=1)
        with col_r2:
            end_rank = st.number_input("종료 순위", min_value=1, max_value=max_rank, value=min(100, max_rank))

        font_size = st.sidebar.number_input("📏 표 글자 크기 (px)", min_value=10, max_value=50, value=14)

        # 필터링 적용
        final_filtered = main_data[
            (main_data['순위'] >= start_rank) & 
            (main_data['순위'] <= end_rank) &
            (main_data['연간 합계'] >= min_value)
        ]

        if not final_filtered.empty:
            total_sum = final_filtered.drop(columns='순위').sum()
            total_row = pd.DataFrame([total_sum], index=pd.MultiIndex.from_tuples([("선택범위 합계", "-")], names=['고객명', '번지순번']))
            total_row.insert(0, '순위', '∑')
            report_df = pd.concat([final_filtered, total_row])
        else:
            report_df = pd.DataFrame()

        # --- 엑셀 다운로드 (제목 및 양식 수정) ---
        st.sidebar.divider()
        if not report_df.empty:
            excel_df = report_df.reset_index()
            month_cols = [f"{str(i).zfill(2)}" for i in range(1, 13)]
            cols = ['순위', '고객명', '번지순번'] + month_cols + ['연간 합계']
            excel_df = excel_df[cols]
            
            month_rename = {f"{str(i).zfill(2)}": f"{i}월" for i in range(1, 13)}
            excel_df = excel_df.rename(columns=month_rename)

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                excel_df.to_excel(writer, sheet_name='업무용_실적보고', index=False)
                
                workbook = writer.book
                worksheet = writer.sheets['업무용_실적보고']
                header_fmt = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC', 'border': 1, 'align': 'center'})
                num_fmt = workbook.add_format({'num_format': '#,##0', 'border': 1})
                
                for col_num, value in enumerate(excel_df.columns.values):
                    worksheet.write(0, col_num, value, header_fmt)
                
                worksheet.set_column('A:A', 6)  # 순위
                worksheet.set_column('B:B', 25) # 고객명
                worksheet.set_column('C:C', 10) # 번지순번
                worksheet.set_column('D:P', 12, num_fmt)
                
            st.sidebar.download_button(
                label="📥 업무용 보고서 다운로드",
                data=output.getvalue(),
                file_name=f"{selected_year}_업무용_주요고객현황.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

        # --- 메인 화면 출력 ---
        st.markdown(f"""
        <style>
            .report-header {{ text-align: center; color: black; }}
            .report-table {{ width: 100%; border-collapse: collapse; font-size: {font_size}px; margin-top: 20px; }}
            .report-table th {{ background-color: #2c3e50; color: white; padding: 10px; border: 1px solid #ddd; text-align: center; position: sticky; top: 0; }}
            .report-table td {{ padding: 8px; border: 1px solid #ddd; text-align: right; }}
            .rank-col {{ text-align: center !important; background-color: #f8f9fa; font-weight: bold; }}
            .name-col {{ text-align: left !important; font-weight: bold; min-width: 150px; }}
            .addr-col {{ text-align: center !important; color: #666; width: 80px; }}
            .total-row {{ background-color: #f1c40f !important; font-weight: bold; }}
        </style>
        """, unsafe_allow_html=True)

        st.markdown(f"<h2 class='report-header'>🏢 {selected_year}년 업무용 주요고객 현황 보고서</h2>", unsafe_allow_html=True)
        st.markdown(f"<p class='report-header' style='font-size: 16px;'>분석 범위: {start_rank}위 ~ {end_rank}위 ({unit_option} 기준)</p>", unsafe_allow_html=True)

        if not report_df.empty:
            html_table = '<table class="report-table"><thead><tr><th>순위</th><th>고객명</th><th>번지순번</th>'
            months = [f"{str(m).zfill(2)}" for m in range(1, 13)]
            for m in months: html_table += f'<th>{m}월</th>'
            html_table += '<th>연간 합계</th></tr></thead><tbody>'

            for (name, addr), row in report_df.iterrows():
                row_class = "total-row" if name == "선택범위 합계" else ""
                html_table += f'<tr class="{row_class}">'
                html_table += f'<td class="rank-col">{row["순위"]}</td>'
                html_table += f'<td class="name-col">{name}</td>'
                html_table += f'<td class="addr-col">{addr}</td>'
                for m in months: html_table += f'<td>{row.get(m, 0):,.0f}</td>'
                html_table += f'<td>{row["연간 합계"]:,.0f}</td></tr>'
            
            html_table += '</tbody></table>'
            st.markdown(html_table, unsafe_allow_html=True)
            st.caption(f"※ 본 보고서는 {selected_year}년도 업무용 실적 데이터를 기반으로 작성되었습니다.")
        else:
            st.warning("조건에 맞는 데이터가 없습니다.")
    else:
        st.warning("분석할 데이터가 없습니다.")
else:
    st.error("데이터 파일을 찾을 수 없습니다.")