import streamlit as st
import pandas as pd
import os
import io

# --- 1. 페이지 설정 및 데이터 로드 ---
st.set_page_config(page_title="산업용 YoY 순위 분석", layout="wide")

@st.cache_data
def load_industrial_data():
    file_path = 'data/industry_monthly_summary.csv'
    if not os.path.exists(file_path):
        return None
    return pd.read_csv(file_path, encoding='utf-8-sig')

df_ind = load_industrial_data()

if df_ind is not None:
    # 기본 전처리
    df_ind['매출년도'] = df_ind['매출년월'].str[:4]
    
    # --- 2. 사이드바 설정 ---
    st.sidebar.title("📈 YoY 분석 설정")
    
    years = sorted(df_ind['매출년도'].unique(), reverse=True)
    if len(years) < 2:
        st.error("🚨 분석을 위해 최소 2년 이상의 데이터가 필요합니다.")
        st.stop()

    selected_year = st.sidebar.selectbox("📅 대상 연도 선택", years, index=0)
    prev_year = str(int(selected_year) - 1)
    
    unit_option = st.sidebar.radio("📊 분석 단위", ["㎥", "MJ"], index=0, horizontal=True)
    target_col = "사용량" if unit_option == "㎥" else "사용열량"
    
    st.sidebar.divider()

    # --- 3. 순위 기준 설정 ---
    st.sidebar.subheader("🏆 순위 정렬 기준")
    sort_options = {
        f"{selected_year}년 실적": f"{selected_year}년 ({unit_option})",
        "증감량": "증감량",
        "증감률": "증감률(%)",
        f"{prev_year}년 실적": f"{prev_year}년 ({unit_option})"
    }
    selected_sort_label = st.sidebar.selectbox("정렬 기준 선택", list(sort_options.keys()), index=0)
    selected_sort_col = sort_options[selected_sort_label]
    
    # --- 4. 데이터 가공 (YoY) ---
    df_curr = df_ind[df_ind['매출년도'] == selected_year].groupby('고객명')[target_col].sum()
    df_prev = df_ind[df_ind['매출년도'] == prev_year].groupby('고객명')[target_col].sum()
    
    # 데이터 병합
    yoy_df = pd.DataFrame({
        f'{prev_year}년 ({unit_option})': df_prev,
        f'{selected_year}년 ({unit_option})': df_curr
    }).fillna(0)
    
    # 증감 계산
    yoy_df['증감량'] = yoy_df[f'{selected_year}년 ({unit_option})'] - yoy_df[f'{prev_year}년 ({unit_option})']
    yoy_df['증감률(%)'] = (yoy_df['증감량'] / yoy_df[f'{prev_year}년 ({unit_option})'] * 100).replace([float('inf'), -float('inf')], 0).fillna(0)
    
    # --- 5. 순위 부여 및 컬럼 재배치 (가장 중요) ---
    # 사용자가 선택한 기준에 따라 정렬
    yoy_df = yoy_df.sort_values(selected_sort_col, ascending=False)
    
    # 순위 부여 및 고객명(인덱스)을 컬럼으로 전환
    yoy_df.insert(0, '순위', range(1, len(yoy_df) + 1))
    final_df = yoy_df.reset_index().rename(columns={'고객명': '고객명'})
    
    # [순위, 고객명, 전년실적, 당년실적, 증감량, 증감률] 순서로 컬럼 강제 고정
    cols_order = ['순위', '고객명', f'{prev_year}년 ({unit_option})', f'{selected_year}년 ({unit_option})', '증감량', '증감률(%)']
    final_df = final_df[cols_order]

    # --- 6. 메인 화면 출력 ---
    st.markdown(f"## 🏭 {selected_year}년 vs {prev_year}년 산업용 실적 비교 보고서")
    
    # 상단 요약 지표
    total_curr = final_df[f'{selected_year}년 ({unit_option})'].sum()
    total_prev = final_df[f'{prev_year}년 ({unit_option})'].sum()
    total_diff = total_curr - total_prev
    total_rate = (total_diff / total_prev * 100) if total_prev != 0 else 0

    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric(f"{selected_year}년 총 실적", f"{total_curr:,.0f}", f"{total_diff:,.0f}")
    col_m2.metric("전체 평균 증감률", f"{total_rate:.1f}%")
    col_m3.metric("분석 대상 업체수", f"{len(final_df):,}개")

    st.divider()

    # --- 7. 테이블 스타일링 및 출력 (깨짐 방지 처리) ---
    st.subheader(f"🔍 고객별 {selected_sort_label} 순위 현황")
    
    def color_diff(val):
        if isinstance(val, (int, float)):
            if val > 0: return 'color: #e74c3c; font-weight: bold;'
            if val < 0: return 'color: #3498db; font-weight: bold;'
        return ''

    # 스타일 적용 (hide_index=True 필수)
    styled_df = final_df.style.format({
        f'{prev_year}년 ({unit_option})': '{:,.0f}',
        f'{selected_year}년 ({unit_option})': '{:,.0f}',
        '증감량': '{:,.0f}',
        '증감률(%)': '{:.1f}%'
    }).map(color_diff, subset=['증감량', '증감률(%)'])

    # hide_index=True를 사용하여 Pandas의 기본 인덱스를 숨기고 '순위' 열이 1열이 되게 함
    st.dataframe(styled_df, use_container_width=True, height=650, hide_index=True)

    # --- 8. 엑셀 다운로드 ---
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        final_df.to_excel(writer, sheet_name='YoY_순위_리포트', index=False)
        
        workbook = writer.book
        worksheet = writer.sheets['YoY_순위_리포트']
        
        # 서식
        header_fmt = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC', 'border': 1, 'align': 'center'})
        num_fmt = workbook.add_format({'num_format': '#,##0', 'border': 1})
        pct_fmt = workbook.add_format({'num_format': '0.0"%"', 'border': 1})
        
        for col_num, value in enumerate(final_df.columns.values):
            worksheet.write(0, col_num, value, header_fmt)
        
        worksheet.set_column('A:A', 8)  # 순위
        worksheet.set_column('B:B', 25) # 고객명
        worksheet.set_column('C:E', 18, num_fmt) # 실적
        worksheet.set_column('F:F', 12, pct_fmt) # 증감률

    st.sidebar.divider()
    st.sidebar.download_button(
        label="📥 현재 보고서 엑셀 다운로드",
        data=output.getvalue(),
        file_name=f"산업용_YoY_순위_{selected_year}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

else:
    st.error("❌ 데이터 파일(industry_monthly_summary.csv)을 찾을 수 없습니다.")