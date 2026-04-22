"""
Streamlit dashboard for Reddit content monitoring & analysis.
Run:  streamlit run app.py
"""

import json
import os
from datetime import datetime
from typing import List, Optional

import pandas as pd
import plotly.express as px
import streamlit as st

from database import get_available_dates, get_posts_with_analysis, init_db
from reddit_fetcher import fetch_all
from analyzer import analyze_all
from scheduler import create_scheduler


# ── Auto-start scheduler (once per Streamlit process) ────────────────────────
@st.cache_resource
def _start_scheduler():
    """Start APScheduler in background so daily 10:00 trigger works even when
    running `streamlit run app.py` directly (without run.py)."""
    import atexit
    scheduler = create_scheduler()
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown(wait=False))
    return scheduler

_start_scheduler()

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Reddit 内容监控",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS for modern design ──────────────────────────────────────────────
st.markdown("""
<style>
    /* Main container styling */
    .main {
        background-color: #FAF8F3;
    }

    /* Cards and sections */
    [data-testid="stMetricValue"] {
        color: #8B9DC3;
        font-weight: 700;
    }

    /* Buttons */
    .stButton > button,
    .stButton button {
        background-color: #1F2937 !important;
        background: #1F2937 !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(31, 41, 55, 0.3) !important;
        padding: 10px 20px !important;
    }

    button {
        background-color: #1F2937 !important;
        color: white !important;
    }

    .stButton > button:hover,
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(31, 41, 55, 0.4) !important;
        background-color: #111827 !important;
        background: #111827 !important;
    }

    /* Headers */
    h1, h2, h3 {
        color: #2D3748;
        font-weight: 700;
    }

    /* Dividers */
    hr {
        border-color: #E2E8F0;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] button {
        border-radius: 6px;
        color: #718096;
        font-weight: 600;
    }

    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
        color: #8B9DC3;
        border-bottom: 3px solid #8B9DC3;
    }

    /* Multiselect tags */
    [data-baseweb="tag"] {
        background-color: #1F2937 !important;
        color: white !important;
    }

    [data-baseweb="tag"] span {
        color: white !important;
    }

    /* Info boxes */
    .stInfo {
        background: linear-gradient(135deg, rgba(139, 157, 195, 0.1) 0%, rgba(155, 157, 212, 0.05) 100%);
        border-left: 4px solid #8B9DC3;
        border-radius: 8px;
    }

    /* Metric cards */
    [data-testid="metric-container"] {
        background: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
        border: 1px solid #E2E8F0;
    }

    /* Equal height columns for filter section */
    [data-testid="column"] {
        display: flex;
        flex-direction: column;
    }

    [data-testid="column"] > div {
        flex: 1;
        display: flex;
        flex-direction: column;
    }

    [data-baseweb="select"] {
        flex: 1 !important;
        display: flex !important;
        flex-direction: column !important;
    }

    /* Mobile responsive design */
    @media (max-width: 800px) {
        /* Main container */
        .main {
            padding: 12px 8px !important;
            max-width: 100% !important;
        }

        /* Metric cards */
        [data-testid="metric-container"] {
            padding: 16px !important;
            margin-bottom: 12px !important;
        }

        /* Buttons */
        .stButton > button {
            padding: 12px !important;
            font-size: 14px !important;
        }

        /* Headers */
        h1 {
            font-size: 22px !important;
            margin-bottom: 16px !important;
        }

        h2 {
            font-size: 16px !important;
        }

        /* Charts - make them responsive */
        .plotly-graph-div {
            height: auto !important;
        }

        /* Table - reduce font size and padding */
        table {
            font-size: 11px !important;
        }

        table td, table th {
            padding: 8px 4px !important;
        }

        /* Tags */
        [data-baseweb="tag"] {
            font-size: 12px !important;
            padding: 4px 6px !important;
        }

        /* Dividers */
        hr {
            margin: 12px 0 !important;
        }

        /* Multiselect - single column */
        [data-testid="column"] {
            width: 100% !important;
            min-width: 100% !important;
        }
    }

    @media (max-width: 480px) {
        .main {
            padding: 8px 4px !important;
        }

        h1 {
            font-size: 18px !important;
        }

        h2 {
            font-size: 14px !important;
        }

        [data-testid="metric-container"] {
            padding: 12px !important;
        }

        table {
            font-size: 10px !important;
        }

        table td, table th {
            padding: 6px 2px !important;
        }
    }

    /* Plotly chart toolbar styling - remove dark background */
    .modebar {
        background: transparent !important;
    }

    .modebar-group {
        background: transparent !important;
    }

    .modebar-btn {
        background: transparent !important;
        color: #2D3748 !important;
    }

    .modebar-btn:hover {
        background: #F0F3FF !important;
        color: #2D3748 !important;
    }

    .plotly-graph-div .modebar {
        background: transparent !important;
    }

    .plotly-graph-div .modebar-btn {
        color: #2D3748 !important;
    }

    .plotly-graph-div .modebar-btn:hover {
        background: #F0F3FF !important;
    }

    /* Table responsive design */
    .table-wrapper {
        border-radius: 12px;
        overflow: hidden;
    }

    /* Desktop: show all columns */
    @media (min-width: 1024px) {
        .hide-mobile {
            display: table-cell !important;
        }
    }

    /* Tablet and Mobile: hide certain columns */
    @media (max-width: 1023px) {
        .hide-mobile {
            display: none !important;
        }

        table {
            font-size: 12px !important;
        }

        table td {
            padding: 10px !important;
        }

        table th {
            padding: 10px !important;
        }
    }

    /* Small mobile: further optimize */
    @media (max-width: 640px) {
        table {
            font-size: 11px !important;
            min-width: 600px !important;
        }

        table td {
            padding: 8px !important;
        }

        table th {
            padding: 8px !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# ── Label maps ───────────────────────────────────────────────────────────────
SENTIMENT_MAP = {"positive": "正面", "negative": "负面", "neutral": "中性"}
USER_TYPE_MAP = {
    "official": "官方",
    "hobbyist": "爱好者",
    "artist_creator": "艺术创作者",
    "maker": "创客",
    "reviewer_influencer": "评测人",
    "small_business": "小商家",
    "print_farm": "印刷工厂",
    "unknown": "未知",
}
CONTENT_TYPE_MAP = {
    "bug_report": "问题反馈",
    "feature_request": "功能需求",
    "showcase": "作品展示",
    "help": "求助",
    "discussion": "讨论",
    "other": "其他",
}
ALL_SUBREDDITS = ["bambulab", "EufyMakeOfficial", "snapmaker"]

# ── Subreddit management ──────────────────────────────────────────────────────
SUBREDDIT_CONFIG_FILE = "subreddit_config.json"

def _load_subreddits() -> List[str]:
    """Load subreddit list from config file or use defaults."""
    if os.path.exists(SUBREDDIT_CONFIG_FILE):
        try:
            with open(SUBREDDIT_CONFIG_FILE, "r") as f:
                data = json.load(f)
                return data.get("subreddits", ALL_SUBREDDITS)
        except Exception:
            return ALL_SUBREDDITS
    return ALL_SUBREDDITS

def _save_subreddits(subreddits: List[str]):
    """Save subreddit list to config file."""
    with open(SUBREDDIT_CONFIG_FILE, "w") as f:
        json.dump({"subreddits": subreddits}, f, indent=2)

# Load subreddits from config
ALL_SUBREDDITS = _load_subreddits()

# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_topics(val) -> list:
    if isinstance(val, list):
        return val
    if isinstance(val, str) and val:
        try:
            return json.loads(val)
        except Exception:
            return []
    return []


def _load_data(fetch_date: Optional[str], subreddits: List[str]) -> pd.DataFrame:
    rows = get_posts_with_analysis(fetch_date=fetch_date, subreddits=subreddits)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    # Fill nulls for posts without analysis
    df["sentiment"] = df["sentiment"].fillna("neutral")
    df["content_type"] = df["content_type"].fillna("other")
    df["user_type"] = df["user_type"].fillna("unknown")
    df["summary"] = df["summary"].fillna("")
    df["key_topics"] = df["key_topics"].apply(_parse_topics)
    df["score"] = pd.to_numeric(df["score"], errors="coerce").fillna(0).astype(int)
    return df


# ── Main app ──────────────────────────────────────────────────────────────────

def main():
    init_db()

    # ── Header row: title + action button ────────────────────────────────────
    title_col, btn_col = st.columns([7, 1])
    with title_col:
        st.title("Reddit 内容分析仪表盘")
    with btn_col:
        st.markdown("<br>", unsafe_allow_html=True)
        trigger = st.button(
            "开始爬取",
            use_container_width=True,
            help="手动触发一次抓取 + AI 分析，方便调试",
        )

    if trigger:
        # Reload subreddit list to pick up newly added channels
        ALL_SUBREDDITS = _load_subreddits()

        with st.status("正在执行抓取与分析 ...", expanded=True) as status:
            st.write("⏳ 正在抓取 Reddit 帖子 ...")
            try:
                fetched = fetch_all()
                st.write(f"✅ 抓取完成：新增 **{fetched}** 条帖子")
            except Exception as exc:
                st.write(f"❌ 抓取出错：{exc}")

            st.write("⏳ 正在 AI 分析 ...")
            try:
                analysed = analyze_all()
                st.write(f"✅ 分析完成：共处理 **{analysed}** 条")
            except Exception as exc:
                st.write(f"❌ 分析出错：{exc}")

            status.update(label="全部完成！", state="complete")
        st.rerun()

    st.divider()

    # ── Subreddit management ──────────────────────────────────────────────────
    with st.expander("➕ 管理频道（添加新频道）"):
        col1, col2 = st.columns([3, 1])
        with col1:
            new_subreddit = st.text_input(
                "输入新频道名称",
                placeholder="例如：Ender3 或 3Dprinting",
                label_visibility="collapsed",
            )
        with col2:
            add_btn = st.button("添加频道", use_container_width=True)

        if add_btn and new_subreddit:
            subreddit_name = new_subreddit.strip().lower()
            if subreddit_name not in ALL_SUBREDDITS:
                updated_list = ALL_SUBREDDITS + [subreddit_name]
                _save_subreddits(updated_list)
                st.success(f"✅ 成功添加频道: **{subreddit_name}**")
                st.rerun()
            else:
                st.warning(f"⚠️ 频道 **{subreddit_name}** 已存在")

        st.caption(f"当前频道数: {len(ALL_SUBREDDITS)}")
        st.write("**已有频道：**", ", ".join(ALL_SUBREDDITS))

    # ── Filter row ───────────────────────────────────────────────────────────
    dates = get_available_dates()

    fc1, fc2 = st.columns([1, 2])
    with fc1:
        if dates:
            selected_date = st.selectbox("选择日期", options=dates, index=0)
        else:
            selected_date = datetime.now().strftime("%Y-%m-%d")
            st.info("暂无数据，请点击右上角【立即抓取并分析】")
    with fc2:
        selected_subreddits = st.multiselect(
            "选择频道",
            options=ALL_SUBREDDITS,
            default=ALL_SUBREDDITS,
        )

    if not selected_subreddits:
        st.warning("请至少选择一个频道。")
        return

    df = _load_data(fetch_date=selected_date if dates else None, subreddits=selected_subreddits)

    if df.empty:
        st.info(
            "📭 当前筛选条件下暂无数据。\n\n"
            "请点击右上角 **【立即抓取并分析】** 按钮获取数据，或更换日期 / 频道筛选。"
        )
        return

    # ── Metric cards ─────────────────────────────────────────────────────────
    total = len(df)
    pos_pct = round((df["sentiment"] == "positive").sum() / total * 100, 1)
    neg_pct = round((df["sentiment"] == "negative").sum() / total * 100, 1)
    neu_pct = round((df["sentiment"] == "neutral").sum() / total * 100, 1)

    hobbyist_pct = round((df["user_type"] == "hobbyist").sum() / total * 100, 1)
    maker_pct = round((df["user_type"] == "maker").sum() / total * 100, 1)
    commercial_pct = round((df["user_type"] == "small_business").sum() / total * 100, 1)

    avg_score = round(df["score"].mean(), 0)
    max_score = df["score"].max()

    # 第一行：整体数据
    st.markdown("### 核心指标")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown("""
        <div style="background: #8B9DC3; padding: 24px; border-radius: 12px; color: white; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.06);">
            <div style="font-size: 36px; font-weight: 700; margin: 8px 0;">""" + str(total) + """</div>
            <div style="font-size: 13px; opacity: 0.95;">今日总帖数</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div style="background: #7BC67B; padding: 24px; border-radius: 12px; color: white; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.06);">
            <div style="font-size: 36px; font-weight: 700; margin: 8px 0;">{avg_score:.0f}</div>
            <div style="font-size: 13px; opacity: 0.95;">平均热度分</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div style="background: #D4859B; padding: 24px; border-radius: 12px; color: white; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.06);">
            <div style="font-size: 36px; font-weight: 700; margin: 8px 0;">{max_score}</div>
            <div style="font-size: 13px; opacity: 0.95;">最高热度分</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        high_conf_count = len(df[df.get("user_type_confidence", "") == "high"])
        st.markdown(f"""
        <div style="background: #F3D96F; padding: 24px; border-radius: 12px; color: #5A4A2A; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.06);">
            <div style="font-size: 36px; font-weight: 700; margin: 8px 0;">{high_conf_count}</div>
            <div style="font-size: 13px; opacity: 0.95;">高置信度分类</div>
        </div>
        """, unsafe_allow_html=True)

    # 第二行：情感分析
    st.markdown("### 情感分布")
    sent_col1, sent_col2, sent_col3 = st.columns(3)

    with sent_col1:
        st.markdown(f"""
        <div style="background: rgba(123, 198, 123, 0.15); padding: 20px; border-radius: 12px; border-left: 4px solid #7BC67B;">
            <div style="font-size: 28px; font-weight: 700; color: #7BC67B;">{pos_pct}%</div>
            <div style="font-size: 13px; color: #4B5563; margin-top: 6px;">正面情感帖子</div>
        </div>
        """, unsafe_allow_html=True)

    with sent_col2:
        st.markdown(f"""
        <div style="background: rgba(139, 157, 195, 0.15); padding: 20px; border-radius: 12px; border-left: 4px solid #8B9DC3;">
            <div style="font-size: 28px; font-weight: 700; color: #8B9DC3;">{neu_pct}%</div>
            <div style="font-size: 13px; color: #4B5563; margin-top: 6px;">中立情感帖子</div>
        </div>
        """, unsafe_allow_html=True)

    with sent_col3:
        st.markdown(f"""
        <div style="background: rgba(212, 133, 155, 0.15); padding: 20px; border-radius: 12px; border-left: 4px solid #D4859B;">
            <div style="font-size: 28px; font-weight: 700; color: #D4859B;">{neg_pct}%</div>
            <div style="font-size: 13px; color: #4B5563; margin-top: 6px;">负面情感帖子</div>
        </div>
        """, unsafe_allow_html=True)

    # 第三行：用户类型分布
    st.markdown("### 用户类型分布")
    user_col1, user_col2, user_col3 = st.columns(3)

    with user_col1:
        st.markdown(f"""
        <div style="background: rgba(155, 157, 212, 0.15); padding: 20px; border-radius: 12px; border-left: 4px solid #9B9DD4;">
            <div style="font-size: 28px; font-weight: 700; color: #9B9DD4;">{hobbyist_pct}%</div>
            <div style="font-size: 13px; color: #4B5563; margin-top: 6px;">爱好者</div>
        </div>
        """, unsafe_allow_html=True)

    with user_col2:
        st.markdown(f"""
        <div style="background: rgba(243, 217, 111, 0.15); padding: 20px; border-radius: 12px; border-left: 4px solid #F3D96F;">
            <div style="font-size: 28px; font-weight: 700; color: #F3D96F;">{maker_pct}%</div>
            <div style="font-size: 13px; color: #4B5563; margin-top: 6px;">创客</div>
        </div>
        """, unsafe_allow_html=True)

    with user_col3:
        st.markdown(f"""
        <div style="background: rgba(232, 180, 212, 0.15); padding: 20px; border-radius: 12px; border-left: 4px solid #E8B4D4;">
            <div style="font-size: 28px; font-weight: 700; color: #E8B4D4;">{commercial_pct}%</div>
            <div style="font-size: 13px; color: #4B5563; margin-top: 6px;">小商家</div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # ── Charts ────────────────────────────────────────────────────────────────
    left, right = st.columns(2)

    with left:
        # Bar chart: posts per subreddit split by hot/new
        st.subheader("各频道帖子数量")
        bar_df = (
            df.groupby(["subreddit", "category"])
            .size()
            .reset_index(name="数量")
        )
        if not bar_df.empty:
            fig_bar = px.bar(
                bar_df,
                x="subreddit",
                y="数量",
                color="category",
                barmode="group",
                color_discrete_map={"hot": "#8B9DC3", "new": "#D4C5E2"},
                labels={"subreddit": "频道", "category": "类型", "数量": "帖子数"},
            )
            fig_bar.update_layout(
                height=300,
                margin=dict(t=10, b=10),
                plot_bgcolor="rgba(248,249,251,1)",
                paper_bgcolor="rgba(248,249,251,1)",
                font=dict(color="#2D3748")
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        # Pie: content type
        st.subheader("内容类型分布")
        ct_series = df["content_type"].map(CONTENT_TYPE_MAP).value_counts()
        if not ct_series.empty:
            ct_df = ct_series.reset_index()
            ct_df.columns = ["类型", "数量"]
            colors = ["#8B9DC3", "#9B9DD4", "#D4C5E2", "#9B95FF", "#7A77FF", "#8A87FF"]
            fig_ct = px.pie(
                ct_df,
                names="类型",
                values="数量",
                hole=0.38,
                color_discrete_sequence=colors
            )
            fig_ct.update_traces(textposition="inside", textinfo="percent+label")
            fig_ct.update_layout(
                height=300,
                margin=dict(t=10, b=10),
                showlegend=False,
                paper_bgcolor="rgba(248,249,251,1)",
                font=dict(color="#2D3748")
            )
            st.plotly_chart(fig_ct, use_container_width=True)

    with right:
        # Pie: user type
        st.subheader("用户类型分布")
        ut_series = df["user_type"].map(USER_TYPE_MAP).value_counts()
        if not ut_series.empty:
            ut_df = ut_series.reset_index()
            ut_df.columns = ["类型", "数量"]
            fig_ut = px.pie(
                ut_df,
                names="类型",
                values="数量",
                hole=0.38,
                color="类型",
                color_discrete_map={
                    "官方": "#8B9DC3",
                    "爱好者": "#9B9DD4",
                    "艺术创作者": "#9B95FF",
                    "创客": "#F39C12",
                    "评测人": "#1ABC9C",
                    "小商家": "#E67E22",
                    "印刷工厂": "#2ECC71",
                    "未知": "#D4C5E2",
                },
            )
            fig_ut.update_traces(textposition="inside", textinfo="percent+label")
            fig_ut.update_layout(
                height=300,
                margin=dict(t=10, b=10),
                showlegend=False,
                paper_bgcolor="rgba(248,249,251,1)",
                font=dict(color="#2D3748")
            )
            st.plotly_chart(fig_ut, use_container_width=True)

        # Horizontal bar: sentiment distribution
        st.subheader("情感分布")
        s_series = df["sentiment"].map(SENTIMENT_MAP).value_counts()
        if not s_series.empty:
            s_df = s_series.reset_index()
            s_df.columns = ["情感", "数量"]
            fig_s = px.bar(
                s_df,
                x="数量",
                y="情感",
                orientation="h",
                color="情感",
                color_discrete_map={
                    "正面": "#10B981",
                    "负面": "#F87171",
                    "中性": "#D4C5E2",
                },
                text="数量",
            )
            fig_s.update_layout(
                height=300,
                margin=dict(t=10, b=10),
                showlegend=False,
                plot_bgcolor="rgba(248,249,251,1)",
                paper_bgcolor="rgba(248,249,251,1)",
                font=dict(color="#2D3748")
            )
            fig_s.update_traces(textposition="outside")
            st.plotly_chart(fig_s, use_container_width=True)

    st.divider()

    # ── Post list ─────────────────────────────────────────────────────────────
    st.subheader("帖子列表")

    lf1, lf2, lf3 = st.columns(3)
    with lf1:
        s_filter = st.multiselect(
            "情感筛选",
            options=list(SENTIMENT_MAP.keys()),
            default=list(SENTIMENT_MAP.keys()),
            format_func=lambda x: SENTIMENT_MAP.get(x, x),
        )
    with lf2:
        ut_filter = st.multiselect(
            "用户类型",
            options=list(USER_TYPE_MAP.keys()),
            default=list(USER_TYPE_MAP.keys()),
            format_func=lambda x: USER_TYPE_MAP.get(x, x),
        )
    with lf3:
        ct_filter = st.multiselect(
            "内容类型",
            options=list(CONTENT_TYPE_MAP.keys()),
            default=list(CONTENT_TYPE_MAP.keys()),
            format_func=lambda x: CONTENT_TYPE_MAP.get(x, x),
        )

    filtered = df[
        df["sentiment"].isin(s_filter)
        & df["user_type"].isin(ut_filter)
        & df["content_type"].isin(ct_filter)
    ].sort_values("score", ascending=False)

    if filtered.empty:
        st.info("无匹配帖子，请调整上方筛选条件。")
        return

    # Build modern styled HTML table with responsive design
    table_html = '<div class="table-wrapper" style="overflow-x: auto; width: 100%;">'
    table_html += '<table style="width:100%; border-collapse: collapse; font-size: 13px; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.06); border: 1px solid #E2E8F0; min-width: 800px;">'
    table_html += '<thead style="position: sticky; top: 0; background: #1F2937; z-index: 10;"><tr>'
    table_html += '<th style="padding: 14px; text-align: left; min-width: 80px; color: white; font-weight: 600;">频道</th>'
    table_html += '<th style="padding: 14px; text-align: left; min-width: 200px; color: white; font-weight: 600;">标题</th>'
    table_html += '<th style="padding: 14px; text-align: center; min-width: 40px; color: white; font-weight: 600;">链接</th>'
    table_html += '<th style="padding: 14px; text-align: center; min-width: 60px; color: white; font-weight: 600;">热度分</th>'
    table_html += '<th style="padding: 14px; text-align: center; min-width: 60px; color: white; font-weight: 600;">情感</th>'
    table_html += '<th style="padding: 14px; text-align: center; min-width: 80px; color: white; font-weight: 600;">用户类型</th>'
    table_html += '<th style="padding: 14px; text-align: left; min-width: 300px; color: white; font-weight: 600;">摘要</th>'
    table_html += '</tr></thead><tbody>'

    for idx, (_, r) in enumerate(filtered.iterrows()):
        url = f"https://www.reddit.com/r/{r['subreddit']}/comments/{r['post_id']}/"
        title = str(r.get("title") or "").replace('"', '&quot;')
        summary = str(r.get("summary") or "-").replace('"', '&quot;')
        subreddit = r["subreddit"]
        score = int(r["score"])
        sentiment = SENTIMENT_MAP.get(r.get("sentiment", ""), "-")
        user_type = USER_TYPE_MAP.get(r.get("user_type", ""), "-")

        # Sentiment color coding
        sentiment_color = {"正面": "#22C55E", "负面": "#EF4444", "中性": "#94A3B8"}.get(sentiment, "#94A3B8")
        bg_color = "#FAF8F3" if idx % 2 == 0 else "white"

        table_html += f'<tr style="height: auto; vertical-align: top; background: {bg_color}; border-bottom: 1px solid #E2E8F0; transition: background 0.2s ease;" onmouseover="this.style.background=\'#F0F3FF\'" onmouseout="this.style.background=\'{bg_color}\'">'
        table_html += f'<td style="padding: 14px; color: #4B5563; font-weight: 500;">{subreddit}</td>'
        table_html += f'<td style="padding: 14px; word-break: break-word; line-height: 1.4; color: #2D3748;">{title}</td>'
        table_html += f'<td style="padding: 14px; text-align: center;"><a href="{url}" target="_blank" style="color: #8B9DC3; text-decoration: none; font-weight: 600; transition: color 0.2s;" onmouseover="this.style.color=\'#9B9DD4\'" onmouseout="this.style.color=\'#8B9DC3\'">🔗</a></td>'
        table_html += f'<td style="padding: 14px; text-align: center; color: #8B9DC3; font-weight: 600;">{score}</td>'
        table_html += f'<td style="padding: 14px; text-align: center; color: {sentiment_color}; font-weight: 600;">{sentiment}</td>'
        table_html += f'<td style="padding: 14px; text-align: center; color: #4B5563; font-weight: 500;">{user_type}</td>'
        table_html += f'<td style="padding: 14px; word-break: break-word; line-height: 1.5; white-space: normal; overflow-wrap: break-word; color: #4B5563;">{summary}</td>'
        table_html += '</tr>'

    table_html += '</tbody></table>'
    table_html += '</div>'

    st.write(table_html, unsafe_allow_html=True)
    st.caption(f"共显示 {len(filtered)} 条帖子，按热度分降序排列")


if __name__ == "__main__":
    main()
