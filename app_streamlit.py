import streamlit as st
import time
import os
import sys
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh

# 确保能导入同目录下的 utils
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from news_scanner_utils import (
    get_sina_724_dt_range, 
    filter_news, 
    transform_to_ui_text, 
    load_and_merge_news
)

# ==========================================
# 页面配置
# ==========================================
st.set_page_config(page_title="Jedi News Scanner", page_icon="🕵️‍♂️", layout="wide")

# 隐藏 Streamlit 默认菜单和水印
hide_st_style = """
            <style>
            footer {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

st.title("🕵️‍♂️ 新闻情报监控系统")
st.markdown("---")

# ==========================================
# 状态初始化
# ==========================================
if "news_memory" not in st.session_state:
    st.session_state.news_memory = []
if "last_fetch_time" not in st.session_state:
    # 实时监控恢复默认 30 分钟逻辑
    st.session_state.last_fetch_time = datetime.now() - timedelta(minutes=60)
if "last_refresh_success" not in st.session_state:
    st.session_state.last_refresh_success = "从未刷新"

# ==========================================
# 侧边栏：模式切换
# ==========================================
active_tab = st.sidebar.radio("📡 模式切换", ["🚀 实时监控模式", "📚 历史回溯搜索"])

# ==========================================
# Tab 1: 实时监控模式
# ==========================================
if active_tab == "🚀 实时监控模式":
    # 侧边栏控制
    st.sidebar.markdown("---")
    st.sidebar.header("⚙️ 实时监控参数")
    refresh_interval = st.sidebar.slider("自动刷新间隔 (分钟)", 0.5, 30.0, 3.0, step=0.5)
    memory_limit_mins = st.sidebar.slider("内存保留时长 (分钟)", 10, 120, 60)

    st.sidebar.markdown("---")
    rt_filter_keyword = st.sidebar.text_input("智能搜索关键词", value="", placeholder="输入关键词，如：伊朗战争局势", key="rt_filter")
    rt_filter_threshold = st.sidebar.slider(
        "搜索匹配阈值", 0.1, 0.9, 0.40, 0.025, 
        key="rt_threshold"
    )

    # 自动刷新逻辑移入 fragment 函数中
    @st.fragment(run_every=f"{refresh_interval}m")
    def realtime_news_container():
        def update_news():
            now = datetime.now()
            start_str = st.session_state.last_fetch_time.strftime("%Y-%m-%d %H:%M:%S")
            end_str = now.strftime("%Y-%m-%d %H:%M:%S")
            
            new_items = get_sina_724_dt_range(start_str, end_str, save=False)
            
            if new_items:
                all_news = new_items + st.session_state.news_memory
                unique_news = {item['id']: item for item in all_news}
                sorted_news = sorted(unique_news.values(), key=lambda x: x['timestamp'], reverse=True)
                
                cutoff_time = now - timedelta(minutes=memory_limit_mins)
                st.session_state.news_memory = [
                    item for item in sorted_news 
                    if datetime.strptime(item['timestamp'], "%Y-%m-%d %H:%M:%S") > cutoff_time
                ]
            st.session_state.last_fetch_time = now
            st.session_state.last_refresh_success = now.strftime("%H:%M:%S")

        update_news()

        col1, col2 = st.columns([1, 5])
        if col1.button("🔄 立即同步"):
            update_news()
            st.rerun()
        col2.markdown(f"**上次同步时间:** `{st.session_state.last_refresh_success}` (每 {refresh_interval} 分钟自动同步)")

        display_data = st.session_state.news_memory
        if rt_filter_keyword and display_data:
            display_data = filter_news(display_data, keyword=rt_filter_keyword, threshold=rt_filter_threshold)
            st.caption(f"🔍 实时过滤：匹配到 {len(display_data)} 条记录")

        if display_data:
            st.markdown(transform_to_ui_text(display_data))
        else:
            st.warning("暂无实时快讯。")

    realtime_news_container()

# ==========================================
# Tab 2: 历史回溯搜索
# ==========================================
else:
    st.header("🔍 历史新闻检索")

    # 1. 历史检索控制全部移动到侧边栏
    st.sidebar.markdown("---")
    st.sidebar.header("🔍 历史新闻检索配置")

    # 查询时间范围移至侧边栏最上方
    with st.sidebar.expander("📅 设置查询时间范围", expanded=True):
        st.subheader("开始时间")
        d_start = st.date_input("开始日期", datetime.now(), key="d_s")
        t_start_str = st.text_input("开始时刻", value="00:00:00", key="t_s_input", placeholder="HH:MM:SS")
        
        st.subheader("结束时间")
        d_end = st.date_input("结束日期", datetime.now(), key="d_e")
        t_end_str = st.text_input("结束时刻", value="23:59:59", key="t_e_input", placeholder="HH:MM:SS")

    st.sidebar.markdown("---")
    hist_keyword = st.sidebar.text_input("历史库语义搜索 (关键词)", placeholder="例如：半导体、美联储...", key="hist_k")
    hist_threshold = st.sidebar.slider("搜索匹配阈值", 0.1, 0.9, 0.40, 0.05, key="hist_t")
    
    run_hist = st.sidebar.button("🚀 开始检索历史库", use_container_width=True)

    # 侧边栏数据维护工具
    with st.sidebar.expander("🛠️ 数据库按天补全"):
        st.caption("选择日期，一键补全全天 (00:00-23:59) 数据至本地")
        target_day = st.date_input("选择补全日期", datetime.now(), key="fix_day")

        if st.button("开始同步当日数据", use_container_width=True):
            f_start = datetime.combine(target_day, datetime.min.time()).strftime("%Y-%m-%d %H:%M:%S")
            f_end = datetime.combine(target_day, datetime.max.time()).strftime("%Y-%m-%d %H:%M:%S")

            progress_bar = st.progress(0)
            status_text = st.empty()

            status_text.text(f"🚀 正在准备补全: {target_day}")
            progress_bar.progress(20)

            with st.spinner("同步中..."):
                try:
                    dumped_data = get_sina_724_dt_range(f_start, f_end, save=True)
                    progress_bar.progress(100)
                    status_text.text("✅ 同步完成！")
                    st.sidebar.success(f"成功存入 {len(dumped_data)} 条记录")
                    time.sleep(1.5)
                except Exception as e:
                    st.sidebar.error(f"同步失败: {e}")

            progress_bar.empty()
            status_text.empty()

    # 2. 页面主体仅保留检索结果展示
    if run_hist:
        try:
            t_start = datetime.strptime(t_start_str, "%H:%M:%S").time()
            t_end = datetime.strptime(t_end_str, "%H:%M:%S").time()
            start_dt = datetime.combine(d_start, t_start)
            end_dt = datetime.combine(d_end, t_end)

            start_str = start_dt.strftime("%Y-%m-%d %H:%M:%S")
            end_str = end_dt.strftime("%Y-%m-%d %H:%M:%S")

            with st.spinner(f"正在从本地库检索 {start_str} 至 {end_str}..."):
                # 获取数据和可能的警告信息
                result = load_and_merge_news("./news_data", start_str, end_str)
                hist_data = result["data"]
                hist_warnings = result["warnings"]

                if hist_data:
                    if hist_keyword:
                        hist_data = filter_news(hist_data, keyword=hist_keyword, threshold=hist_threshold)
                    else:
                        # 确保没有关键词时也是倒序排列
                        hist_data = sorted(hist_data, key=lambda x: x.get('timestamp', ''), reverse=True)

                    # 显示成功信息和警告
                    st.success(f"找到 {len(hist_data)} 条历史记录")
                    for warning_msg in hist_warnings:
                        st.warning(warning_msg)
                        
                    st.markdown(transform_to_ui_text(hist_data))
                else:
                    # 如果没有数据，显示 result 里的严重警告信息
                    for warning_msg in hist_warnings:
                        st.error(warning_msg)
                    st.error("该时间段内本地无数据，请尝试侧边栏的补全功能。")
        except ValueError:
            st.error("时间格式无效，请输入正确的 HH:MM:SS 格式")

st.sidebar.markdown("---")
st.sidebar.caption(f"💡 实时模式状态：缓存 {len(st.session_state.news_memory)} 条")
