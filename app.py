import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# 1. 페이지 설정
st.set_page_config(page_title="산업용 주요고객 분석 리포트", layout="wide")

@st.cache_data
def load_summary_data():
    file_path = 'data/industry_yearly_summary.csv'
    if not os.path.exists(file_path):
        return None
    return pd.read_csv(file_path, encoding='utf-8-sig')

df_raw = load_summary_data()

if df_raw is not None:
    # --- 사이드바 설정 ---
    st.sidebar.header("⚙️ 분석 및 시각화 설정")
    
    unit_option = st.sidebar.radio("📊 단위 선택", ["㎥", "천㎥", "MJ", "GJ"], index=0, horizontal=True)
    conversion = {"㎥": ("사용량", 1), "천㎥": ("사용량", 1000), "MJ": ("사용열량", 1), "GJ": ("사용열량", 1000)}
    target_col, div_factor = conversion[unit_option]
    unit_label = unit_option

    df = df_raw.copy()
    df[target_col] = df[target_col] / div_factor
    
    st.sidebar.subheader("🏆 순위 분석 설정")
    all_years = sorted(df['매출년도'].unique())
    base_year = st.sidebar.selectbox("🔝 순위 결정 기준 연도", options=all_years, index=len(all_years)-1)
    
    max_available_rank = int(df[df['매출년도'] == base_year]['고객명'].count())
    rank_range = st.sidebar.slider("분석 순위 범위", 1, min(max_available_rank, 100), (1, 10))
    start_rank, end_rank = rank_range

    selected_years = st.sidebar.select_slider("표시 연도 범위", options=all_years, value=(min(all_years), max(all_years)))
    chart_height = st.sidebar.slider("그래프 높이", 400, 1200, 600, 100)

    # --- 데이터 가공 ---
    df_filtered = df[(df['매출년도'] >= selected_years[0]) & (df['매출년도'] <= selected_years[1])].copy()
    
    # 랭킹 데이터 산출 (전체 연도 대상)
    df_filtered['순위'] = df_filtered.groupby('매출년도')[target_col].rank(ascending=False, method='min')
    df_filtered['표시텍스트'] = df_filtered.apply(lambda x: f"{x['고객명']} ({x[target_col]:,.0f})", axis=1)

    # 기준 연도별 타겟 리스트
    df_base_year = df[df['매출년도'] == base_year].copy()
    df_base_year['순위'] = df_base_year[target_col].rank(ascending=False, method='min')
    
    target_customers = df_base_year[
        (df_base_year['순위'] >= start_rank) & (df_base_year['순위'] <= end_rank)
    ].sort_values('순위')['고객명'].tolist()
    
    df_plot = df_filtered[df_filtered['고객명'].isin(target_customers)].copy()
    df_plot['매출년도'] = df_plot['매출년도'].astype(str)
    display_years = sorted(df_plot['매출년도'].unique())

    # --- 🎨 컬러 로직 설정 ---
    customer_colors = px.colors.qualitative.Plotly 
    color_map = {customer: customer_colors[i % len(customer_colors)] for i, customer in enumerate(target_customers)}
    opacity_map = {year: 0.3 + (i / len(display_years)) * 0.7 for i, year in enumerate(display_years)}

    # --- 메인 화면 출력 ---
    st.title("🏭 산업용 주요고객 분석 대시보드")
    st.info(f"💡 **{base_year}년** 실적 기준 분석 (단위: {unit_label})")

    if not df_plot.empty:
        # 1. 꺾은선 그래프
        st.subheader("📈 연도별 추이 분석")
        fig_line = px.line(
            df_plot, x='매출년도', y=target_col, color='고객명', markers=True,
            color_discrete_map=color_map,
            template='plotly_white',
            category_orders={"고객명": target_customers}
        )
        fig_line.update_traces(line=dict(width=4))
        st.plotly_chart(fig_line, use_container_width=True)

        st.divider()

        # 2. 클러스터 막대 그래프
        st.subheader("📊 고객별 실적 비교 (연도별 톤 조절)")
        fig_bar = go.Figure()

        for year in display_years:
            year_data = df_plot[df_plot['매출년도'] == year]
            bar_colors = [color_map.get(cust, '#D3D3D3') for cust in year_data['고객명']]
            
            fig_bar.add_trace(go.Bar(
                name=year,
                x=year_data['고객명'],
                y=year_data[target_col],
                marker_color=bar_colors,
                opacity=opacity_map[year],
                text=year_data[target_col].apply(lambda x: f"{x:,.0f}"),
                textposition='outside'
            ))

        fig_bar.update_layout(
            barmode='group', template='plotly_white', height=chart_height,
            xaxis_title="고객사명", yaxis_title=f"판매량 ({unit_label})",
            legend_title_text="연도 (진할수록 최신)",
            xaxis={'categoryorder':'array', 'categoryarray':target_customers}
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        st.divider()

        # --- [추가] 3. 연도별 순위표 (TOP N 순위 데이터 표) ---
        st.subheader(f"🏆 연도별 {start_rank}위~{end_rank}위 순위 현황")
        # 해당 순위 범위에 드는 업체들만 피벗팅
        rank_pivot = df_filtered[
            (df_filtered['순위'] >= start_rank) & (df_filtered['순위'] <= end_rank)
        ].pivot(index='순위', columns='매출년도', values='표시텍스트').fillna("-")
        
        st.dataframe(rank_pivot.sort_index(), use_container_width=True)

        st.divider()

        # 4. 상세 실적 테이블
        st.subheader(f"📊 {base_year}년 주요 고객 연도별 상세 실적")
        customer_pivot = df_plot.pivot_table(
            index='고객명', columns='매출년도', values=target_col, aggfunc='sum',
            margins=True, margins_name="총계"
        ).fillna(0).reindex(target_customers + ["총계"])
        
        st.dataframe(customer_pivot.style.format("{:,.0f}"), use_container_width=True)

        # 엑셀 다운로드 버튼
        csv_raw = df_plot.to_csv(index=False, encoding='utf-8-sig')
        st.sidebar.download_button(
            label="📥 현재 분석 데이터 다운로드",
            data=csv_raw,
            file_name=f"산업용_주요고객_분석_{base_year}년기준.csv",
            mime="text/csv",
            use_container_width=True
        )

    else:
        st.warning("데이터가 없습니다. 범위를 조절해 주세요.")

else:
    st.error("데이터 요약 파일을 확인해 주세요.")