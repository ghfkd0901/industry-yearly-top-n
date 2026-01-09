import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import os

st.set_page_config(page_title="산업용 순위 변동 레이스", layout="wide")

@st.cache_data
def load_summary_data():
    file_path = r'D:\project2\산업용주요고객판매량분석_차성윤\data\industry_yearly_summary.csv'
    if not os.path.exists(file_path):
        return None
    return pd.read_csv(file_path, encoding='utf-8-sig')

df = load_summary_data()

if df is not None:
    st.title("🏎️ 산업용 주요고객 순위 변동 레이스")
    
    # --- 사이드바 설정 ---
    st.sidebar.header("⚙️ 레이스 설정")
    target_col = st.sidebar.selectbox("분석 지표 선택", ["사용량", "사용열량"], index=0)
    top_n = st.sidebar.slider("표시할 상위 업체 수", min_value=5, max_value=30, value=15)
    
    # --- 데이터 가공 ---
    all_years = sorted(df['매출년도'].unique())
    x_max = df[target_col].max() * 1.1
    
    # 업체별 고유 색상 매핑 (레이스 중 업체 식별을 위해 고정)
    all_customers = df['고객명'].unique()
    color_map = {customer: px.colors.qualitative.Plotly[i % len(px.colors.qualitative.Plotly)] 
                 for i, customer in enumerate(all_customers)}

    # 💡 프레임 생성 (순위 변동을 위한 핵심 로직)
    frames = []
    for year in all_years:
        # 해당 연도의 TOP N 추출 (순위대로 정렬)
        year_data = df[df['매출년도'] == year].nlargest(top_n, target_col).sort_values(target_col, ascending=True)
        
        frames.append(go.Frame(
            data=[go.Bar(
                x=year_data[target_col],
                y=year_data['고객명'],
                orientation='h',
                text=[f" {v:,.0f}" for v in year_data[target_col]],
                textposition='outside',
                marker=dict(color=[color_map[c] for c in year_data['고객명']]),
                cliponaxis=False
            )],
            # 💡 매 프레임마다 y축 카테고리 순서를 해당 연도 순위로 강제 재정렬
            layout=go.Layout(yaxis=dict(categoryarray=year_data['고객명'].tolist(), categoryorder="array")),
            name=str(year)
        ))

    # 초기 화면 (첫 번째 연도) 설정
    initial_year_data = df[df['매출년도'] == all_years[0]].nlargest(top_n, target_col).sort_values(target_col, ascending=True)

    fig = go.Figure(
        data=[go.Bar(
            x=initial_year_data[target_col],
            y=initial_year_data['고객명'],
            orientation='h',
            text=[f" {v:,.0f}" for v in initial_year_data[target_col]],
            textposition='outside',
            marker=dict(color=[color_map[c] for c in initial_year_data['고객명']]),
            cliponaxis=False
        )],
        layout=go.Layout(
            height=700,
            xaxis=dict(range=[0, x_max], autorange=False, title=target_col, tickformat=",.0f"),
            yaxis=dict(title="", showticklabels=True, automargin=True, 
                       categoryarray=initial_year_data['고객명'].tolist(), categoryorder="array"),
            title=f"연도별 {target_col} 순위 변동",
            template="plotly_white",
            margin=dict(l=200, r=100, t=100, b=50),
            updatemenus=[{
                "buttons": [
                    {
                        "args": [None, {"frame": {"duration": 1500, "redraw": True}, "fromcurrent": True, "transition": {"duration": 1200, "easing": "quad-in-out"}}],
                        "label": "▶️ 재생", "method": "animate"
                    },
                    {
                        "args": [[None], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate", "transition": {"duration": 0}}],
                        "label": "⏸️ 일시정지", "method": "animate"
                    }
                ],
                "direction": "left", "pad": {"r": 10, "t": 87}, "showactive": False, "type": "buttons", "x": 0.1, "xanchor": "right", "y": 0, "yanchor": "top"
            }],
            sliders=[{
                "active": 0,
                "yanchor": "top", "xanchor": "left",
                "currentvalue": {"font": {"size": 20}, "prefix": "분석 연도: ", "visible": True, "xanchor": "right"},
                "transition": {"duration": 1200, "easing": "quad-in-out"}, # 💡 quad-in-out으로 수정
                "pad": {"b": 10, "t": 50}, "len": 0.9, "x": 0.1, "y": 0,
                "steps": [{"args": [[f.name], {"frame": {"duration": 1500, "redraw": True}, "mode": "immediate", "transition": {"duration": 1200}}],
                           "label": f.name, "method": "animate"} for f in frames]
            }]
        ),
        frames=frames
    )

    st.plotly_chart(fig, use_container_width=True)

else:
    st.error("데이터 파일을 찾을 수 없습니다.")