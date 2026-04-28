"""
Simple Streamlit test app to verify data loading.
Run: streamlit run test_streamlit.py
"""

import streamlit as st
from database import init_db, get_available_dates, get_posts_with_analysis, get_all_subreddits
import pandas as pd

st.set_page_config(page_title="数据显示测试", layout="wide")

st.title("🧪 数据显示测试")

# Initialize DB
init_db()

st.markdown("### [1] 数据库状态")
dates = get_available_dates()
st.write(f"**可用日期:** {dates}")

st.markdown("### [2] 频道列表")
subreddits = get_all_subreddits()
st.write(f"**配置的频道:** {subreddits}")

st.markdown("### [3] 数据加载测试")

# Select date
selected_date = st.selectbox("选择日期", dates) if dates else "2026-04-24"
st.write(f"**选择的日期:** {selected_date}")

# Load data
st.write(f"正在从数据库加载数据...")
rows = get_posts_with_analysis(fetch_date=selected_date, subreddits=subreddits)

st.write(f"**加载结果:** {len(rows)} 条数据")

if rows:
    # Convert to DataFrame
    df = pd.DataFrame(rows)

    st.success(f"✅ 成功加载 {len(df)} 条数据!")

    st.markdown("### 数据样本")
    st.dataframe(
        df[["subreddit", "title", "score", "sentiment"]].head(10),
        use_container_width=True
    )

    st.markdown("### 数据统计")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("总帖数", len(df))
    with col2:
        analyzed = len(df[df["sentiment"].notna()])
        st.metric("已分析", analyzed)
    with col3:
        st.metric("待分析", len(df) - analyzed)
else:
    st.error("❌ 没有数据返回！")
    st.write("调试信息:")
    st.write(f"- 日期: {selected_date}")
    st.write(f"- 频道: {subreddits}")
