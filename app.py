import streamlit as st
import pandas as pd
import plotly.express as px
import os

# 1. 페이지 설정
st.set_page_config(page_title="산업용 주요고객 분석 리포트", layout="wide")

@st.cache_data
def load_summary_data():
    # 파일 경로 설정
    file_path = r'D:\project2\산업용주요고객판매량분석_차성윤\data\industry_yearly_summary.csv'
    if not os.path.exists(file_path):
        return None
    return pd.read_csv(file_path, encoding='utf-8-sig')

df = load_summary_data()

if df is not None:
    # --- 사이드바 설정 ---
    st.sidebar.header("⚙️ 분석 및 시각화 설정")
    
    top_n = st.sidebar.slider("표시할 상위 순위(N)", min_value=5, max_value=50, value=20)
    target_col = st.sidebar.selectbox("분석 지표 선택", ["사용량", "사용열량"], index=0)
    
    all_years = sorted(df['매출년도'].unique())
    selected_years = st.sidebar.select_slider("분석 연도 범위", options=all_years, value=(min(all_years), max(all_years)))

    chart_height = st.sidebar.slider("그래프 세로 크기 조절", min_value=600, max_value=2000, value=1000, step=100)

    # 데이터 레이블 표시 옵션
    show_labels = st.sidebar.checkbox("그래프 위에 데이터 수치 표시", value=True)

    # --- 데이터 가공 ---
    # 연도 필터링
    df_filtered = df[(df['매출년도'] >= selected_years[0]) & (df['매출년도'] <= selected_years[1])].copy()
    
    # 순위 계산
    df_filtered['순위'] = df_filtered.groupby('매출년도')[target_col].rank(ascending=False, method='min')
    df_filtered['표시텍스트'] = df_filtered.apply(lambda x: f"{x['고객명']}\n({x[target_col]:,.0f})", axis=1)

    # 시각화용 데이터 필터링 (마지막 연도 TOP N 기준)
    base_year = selected_years[1]
    top_n_list = df_filtered[(df_filtered['매출년도'] == base_year) & (df_filtered['순위'] <= top_n)]['고객명'].tolist()
    df_plot = df_filtered[df_filtered['고객명'].isin(top_n_list)].copy()

    # --- 시각화 (그래프) ---
    st.title("🏭 산업용 주요고객 분석 대시보드")
    
    fig = px.line(
        df_plot, x='매출년도', y=target_col, color='고객명', markers=True,
        text=target_col if show_labels else None,
        title=f"연도별 {target_col} 추이 (상위 {top_n}개 업체 기준)",
        template='plotly_white'
    )

    # 선 끝에 이름 및 지시선 표시
    for i, customer in enumerate(top_n_list):
        c_data = df_plot[df_plot['고객명'] == customer].sort_values('매출년도')
        if not c_data.empty:
            last_point = c_data.iloc[-1]
            
            fig.add_annotation(
                x=last_point['매출년도'], 
                y=last_point[target_col],
                text=f"<b>{customer}</b>",
                showarrow=True,
                arrowhead=0,
                arrowcolor=fig.data[i].line.color,
                ax=60, 
                ay=0,
                xanchor="left",
                font=dict(size=12, color=fig.data[i].line.color)
            )

    fig.update_traces(
        textposition="top center", 
        texttemplate='%{y:,.0f}',
        line=dict(width=3),
        showlegend=False 
    )

    fig.update_layout(
        height=chart_height,
        margin=dict(r=200, t=100), 
        hovermode="x unified",
        xaxis=dict(tickmode='linear', dtick=1),
        yaxis=dict(tickformat=",.0f", gridcolor='lightgrey')
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- 데이터 테이블 섹션 ---
    st.divider()
    
    st.subheader(f"🏆 1. 연도별 TOP {top_n} 순위표")
    rank_pivot = df_filtered[df_filtered['순위'] <= top_n].pivot(
        index='순위', columns='매출년도', values='표시텍스트'
    ).fillna("-")
    st.dataframe(rank_pivot.sort_index(), use_container_width=True)

    st.subheader(f"📊 2. 고객명별 연도별 {target_col} 현황")
    customer_pivot = df_plot.pivot_table(
        index='고객명', columns='매출년도', values=target_col, aggfunc='sum',
        margins=True, margins_name="총계"
    ).fillna(0).sort_values('총계', ascending=False)
    st.dataframe(customer_pivot.style.format("{:,.0f}"), use_container_width=True)

    # --- 📥 원본(Raw) 데이터 다운로드 섹션 ---
    st.divider()
    st.subheader("📥 원본 데이터 내보내기")
    
    # 사용자가 선택한 상위 고객의 [고객명, 매출년도, 사용량, 사용열량] 로우 데이터
    raw_download_df = df_plot[['고객명', '매출년도', '사용량', '사용열량']].sort_values(['고객명', '매출년도'])
    
    # CSV 변환 (BOM 포함 utf-8-sig로 한글 깨짐 방지)
    csv_raw = raw_download_df.to_csv(index=False, encoding='utf-8-sig')
    
    st.download_button(
        label="📄 원본 로우 데이터(CSV) 다운로드",
        data=csv_raw,
        file_name=f"산업용_상위고객_원본데이터.csv",
        mime="text/csv",
    )
    st.caption("※ 상위 순위 및 연도 범위가 적용된 [고객명, 매출년도, 사용량, 사용열량] 원본 데이터를 다운로드합니다.")

else:
    st.error("데이터 요약 파일을 확인해 주세요.")