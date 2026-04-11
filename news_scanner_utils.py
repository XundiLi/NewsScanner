import os
import time
import random
import re
import json
import glob
import logging
import requests
import torch
import sys
import pandas as pd
from datetime import datetime, timedelta
from sentence_transformers import SentenceTransformer, util
from typing import List, Dict, Optional, Any, Union
from news_scanner_engine import SinaNewsScanner

# ==========================================
# 相对路径逻辑支持
# ==========================================
if getattr(sys, 'frozen', False):
    # 打包后的可执行文件所在目录
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # 脚本所在目录
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ==========================================
# 全局配置与日志系统
# ==========================================
log_path = os.path.join(BASE_DIR, 'sync.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(log_path, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("SinaScanner")

# ==========================================
# 模块级功能函数
# ==========================================
LOCAL_MODEL_PATH = os.path.join(BASE_DIR, "transformer_models", "paraphrase-multilingual-MiniLM-L12-v2")
_engine = SinaNewsScanner(model_name = LOCAL_MODEL_PATH)

def get_sina_724_dt_range(start_time_str: str, end_time_str: str, save: bool = True, file_format: str = "jsonl") -> List[Dict[str, Any]]:
    """
    抓取指定时间范围的新浪快讯
    :param start_time_str: 起始时间字符串 (YYYY-MM-DD HH:MM:SS)
    :param end_time_str: 结束时间字符串 (YYYY-MM-DD HH:MM:SS)
    :param save: 是否保存到本地
    :param file_format: 保存格式 (jsonl 或 xlsx)
    :return: 抓取到的解析后数据列表
    """
    start_dt = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
    end_dt = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")
    current_page = _engine.find_start_page(end_dt)
    
    all_news = []
    logger.info(f"🚀 扫描启动，起始页码: {current_page}")

    while True:
        params = {"page": current_page, "page_size": 100, "zhibo_id": 152, "type": "all"}
        try:
            time.sleep(random.uniform(0.4, 0.7))
            resp = requests.get(_engine.base_url, params=params, headers=_engine.headers, timeout=20).json()
            feed_list = resp.get('result', {}).get('data', {}).get('feed', {}).get('list', [])
            if not feed_list: break

            for item in feed_list:
                item_dt = datetime.strptime(item.get('create_time'), "%Y-%m-%d %H:%M:%S")
                if start_dt <= item_dt <= end_dt:
                    all_news.append(_engine.parse_item_full(item))
                elif item_dt < start_dt:
                    logger.info(f"🏁 抓取完成：已到达设定起始时间。")
                    return export_range_data(all_news, start_time_str, end_time_str, save=save, file_format=file_format)
            
            logger.info(f"📦 正在扫描第 {current_page} 页 | 最新条目: {feed_list[0]['create_time']}")
            current_page += 1
        except Exception as e:
            logger.error(f"❌ 抓取过程异常: {e}")
            break
    return all_news

def export_range_data(data: List[Dict[str, Any]], start_str: str, end_str: str, output_dir: str = None, save: bool = True, file_format: str = "jsonl") -> List[Dict[str, Any]]:
    """
    导出新闻数据到指定目录
    :param data: 新闻列表
    :param start_str: 时间段开始标识
    :param end_str: 时间段结束标识
    :param output_dir: 输出文件夹路径
    :param save: 是否执行保存
    :param file_format: 文件后缀名
    :return: 原始数据列表
    """
    if not data or not save: return data
    if output_dir is None:
        output_dir = os.path.join(BASE_DIR, "news_data")
        
    if not os.path.exists(output_dir): os.makedirs(output_dir)
    
    fn_start = start_str.replace("-", "").replace(":", "").replace(" ", "_")
    fn_end = end_str.replace("-", "").replace(":", "").replace(" ", "_")
    full_path = os.path.join(output_dir, f"Sina_724_{fn_start}_to_{fn_end}.{file_format}")
    
    if file_format == "jsonl":
        with open(full_path, 'w', encoding='utf-8') as f:
            for entry in data: f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    else:
        pd.DataFrame(data).to_excel(full_path, index=False)
    
    logger.info(f"💾 数据已成功持久化至: {full_path}")
    return data

def load_and_merge_news(input_dir: str = None, start_time: str = None, end_time: str = None, file_format: str = "jsonl") -> Dict[str, Any]:
    """
    从本地目录加载并合并特定时间段的数据
    :param input_dir: 数据存放目录
    :param start_time: 检索起始时间
    :param end_time: 检索结束时间
    :param file_format: 文件格式
    :return: 包含数据列表和警告信息的字典
    """
    if input_dir is None:
        input_dir = os.path.join(BASE_DIR, "news_data")
        
    warnings = []
    q_start = start_time.replace("-", "").replace(":", "").replace(" ", "_")
    q_end = end_time.replace("-", "").replace(":", "").replace(" ", "_")
    
    all_merged_data = []
    file_pattern = os.path.join(input_dir, f"*.{file_format}")
    all_files = glob.glob(file_pattern)
    
    target_files = []
    for f_path in all_files:
        f_name = os.path.basename(f_path)
        try:
            parts = f_name.rsplit('.', 1)[0].split("_")
            f_start = f"{parts[2]}_{parts[3]}"
            f_end = f"{parts[5]}_{parts[6]}"
            if f_end >= q_start and f_start <= q_end:
                target_files.append(f_path)
        except (IndexError, ValueError):
            target_files.append(f_path)

    logger.info(f"📂 筛选出 {len(target_files)}/{len(all_files)} 个相关文件。")

    for file_path in target_files:
        try:
            if file_format == "jsonl":
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_data = [json.loads(line) for line in f]
            else:
                file_data = pd.read_excel(file_path).to_dict(orient='records')
            all_merged_data.extend(file_data)
        except Exception as e:
            logger.error(f"❌ 读取失败 {file_path}: {e}")

    if not all_merged_data:
        msg = f"🚨 严重警告：在 {start_time} 至 {end_time} 范围内未读到任何数据！"
        logger.warning(msg)
        return {"data": [], "warnings": [msg]}

    # 1. 精准时间过滤
    final_data = filter_news(all_merged_data, start_time=start_time, end_time=end_time)

    # 2. 排序 (修改为倒序排列)
    final_data.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

    # 3. 基于 id + timestamp 去重并输出重复项
    seen_ids = set()
    unique_list = []
    duplicate_ids = []
    
    for item in final_data:
        news_id = item.get('id', 'no_id')
        ts = item.get('timestamp', '')
        unique_key = f"{news_id}_{ts}"
        
        if unique_key not in seen_ids:
            unique_list.append(item)
            seen_ids.add(unique_key)
        else:
            duplicate_ids.append(f"{news_id} ({ts})")

    if duplicate_ids:
        msg = f"⚠️ 发现 {len(duplicate_ids)} 条重复 ID 记录"
        logger.warning(msg)
        warnings.append(msg)

    # 4. 数据缺失校验 (10分钟阈值)
    if unique_list:
        fmt = '%Y-%m-%d %H:%M:%S'
        target_start_dt = datetime.strptime(start_time, fmt)
        target_end_dt = datetime.strptime(end_time, fmt)
        
        actual_last_dt = datetime.strptime(unique_list[0]['timestamp'], fmt)
        actual_first_dt = datetime.strptime(unique_list[-1]['timestamp'], fmt)
        
        threshold = timedelta(minutes=10)

        if (actual_first_dt - target_start_dt) > threshold:
            msg = f"⚠️ [数据空洞] 起始点 {start_time} 后超过 10 分钟才有数据 (首条: {actual_first_dt})"
            logger.warning(msg)
            warnings.append(msg)

        if (target_end_dt - actual_last_dt) > threshold:
            msg = f"⚠️ [数据空洞] 结束点 {end_time} 前超过 10 分钟数据中断 (末条: {actual_last_dt})"
            logger.warning(msg)
            warnings.append(msg)

    logger.info(f"✅ 合并完成！最终数据量: {len(unique_list)} 条。")
    return {"data": unique_list, "warnings": warnings}

def filter_news(news_list: List[Dict[str, Any]], keyword: Optional[str] = None, start_time: Optional[str] = None, end_time: Optional[str] = None, threshold: float = 0.35) -> List[Dict[str, Any]]:
    """
    结合时间与语义相似度的新闻过滤器
    :param news_list: 待过滤的数据源
    :param keyword: 搜索关键词
    :param start_time: 过滤起始时间
    :param end_time: 过滤结束时间
    :param threshold: 语义匹配阈值
    :return: 满足条件的过滤结果
    """
    # 1. 物理时间过滤
    st = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S") if start_time else None
    ed = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S") if end_time else None
    
    pre = []
    for it in news_list:
        dt = datetime.strptime(it['timestamp'], "%Y-%m-%d %H:%M:%S")
        if st and dt < st: continue
        if ed and dt > ed: continue
        pre.append(it)
        
    if not keyword or not pre:
        return sorted(pre, key=lambda x: x['timestamp'], reverse=True)

    # 2. 语义搜索
    model = _engine.semantic_model
    corpus = [it.get('content', '') for it in pre]
    corpus_emb = model.encode(corpus, convert_to_tensor=True)
    query_emb = model.encode(keyword, convert_to_tensor=True)
    scores = util.cos_sim(query_emb, corpus_emb)[0]
    
    res = []
    for i, score in enumerate(scores):
        if score >= threshold:
            it = pre[i].copy()
            it['score'] = round(float(score), 4)
            res.append(it)
            
    return sorted(res, key=lambda x: x['timestamp'], reverse=True)

def transform_to_ai_text(raw_data_list: List[Dict[str, Any]], chunk_size: int = 30) -> List[str]:
    """
    将快讯转化为 AI 提示词块 (内部强制正序处理，方便 Wiki 模式增量摄取)
    :param raw_data_list: 清洗后的列表 (不论输入顺序，此处会克隆并排序)
    :param chunk_size: 每块条数
    :return: 文本块列表
    """
    # 克隆并进行正序排序，确保 AI 摄取是按时间线进行的
    sorted_data = sorted(raw_data_list, key=lambda x: x.get('timestamp', ''), reverse=False)
    
    chunks = []
    total = len(sorted_data)
    
    for i in range(0, total, chunk_size):
        chunk_items = sorted_data[i : i + chunk_size]
        chunk_index = (i // chunk_size) + 1
        
        start_t = chunk_items[0].get('timestamp', '')
        end_t = chunk_items[-1].get('timestamp', '')
        
        header = (
            f"--- [NEWS CHUNK ID: {chunk_index}] ---\n"
            f"时间范围: {start_t} TO {end_t}\n"
            f"条数: {len(chunk_items)}\n"
            "------------------------------------------\n"
        )
        
        formatted_lines = []
        for item in chunk_items:
            news_id = item.get('id', 'N/A')
            full_time = item.get('timestamp', '') 
            content = item.get('content', '').replace('\n', ' ')
            
            stocks = [s.get('symbol') for s in item.get('stocks', [])]
            stock_label = f"【{'/'.join(stocks)}】" if stocks else ""
            
            icon = "🔥" if item.get('importance', 0) > 0 or item.get('is_top', 0) > 0 else "·"
            icon = "🔁" if item.get('is_repeat', 0) > 0 else icon
            
            formatted_lines.append(f"[{news_id}] {icon} {full_time} {content} {stock_label}")
        
        full_chunk_text = header + "\n".join(formatted_lines) + "\n\n"
        chunks.append(full_chunk_text)
        
    return chunks

def transform_to_ui_text(raw_data_list: List[Dict[str, Any]]) -> str:
    """
    将快讯转化为适合 UI 展示的 Markdown 文本
    :param raw_data_list: 清洗后的列表
    :return: Markdown 格式的字符串
    """
    if not raw_data_list:
        return ""
        
    formatted_lines = []
    for item in raw_data_list:
        full_time = item.get('timestamp', '') 
        content = item.get('content', '')
        
        # 使用 Streamlit 支持的 Markdown 颜色语法 :blue[text]
        colored_time = f":blue[{full_time}]"
        
        # 处理品种标签
        stocks = [s.get('symbol') for s in item.get('stocks', [])]
        stock_label = f" **[{'/'.join(stocks)}]**" if stocks else ""
        
        # 重要性视觉权重
        icon = "🔥" if item.get('importance', 0) > 0 or item.get('is_top', 0) > 0 else "•"
        icon = "🔁" if item.get('is_repeat', 0) > 0 else icon
        
        # 使用 Markdown 列表格式，利于自动换行
        formatted_lines.append(f"{icon} **{colored_time}** {content}{stock_label}")
    
    return "\n\n".join(formatted_lines)

def save_text_file(content: str, output_path: str) -> None:
    """
    保存 AI 提示词文本至磁盘
    :param content: 文本内容
    :param output_path: 目标文件路径
    """
    if not content: return
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
    logger.info(f"✅ AI 文本已保存: {output_path}")

def get_lastest_news_id(news_list: List[Dict[str, Any]]) -> Optional[str]:
    """
    获取新闻列表中最新的 ID
    :param news_list: 新闻数据列表
    :return: 最新新闻的 ID 或 None
    """
    if not news_list:
        return None
    lastest_news_id =  max(set(news['id'] for news in news_list))
    return lastest_news_id
