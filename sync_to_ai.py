import os
import sys
from datetime import datetime
from news_scanner_utils import load_and_merge_news, transform_to_ai_text, save_text_file, get_sina_724_dt_range

def sync_news_to_ai_text(target_date_str: str, mode: str = "jsonl", output_dir: str = "./news_text", news_data_dir: str = "./news_data"):
    """
    将新闻数据转换为 AI 格式并保存
    :param target_date_str: 日期字符串，格式为 YYYY-MM-DD
    :param mode: 数据源模式
                 - "jsonl": 从本地 news_data 目录读取 jsonl 文件
                 - "live":  直接从新浪快讯接口抓取（不保存，仅内存处理）
    :param output_dir: 输出文件夹路径
    :param news_data_dir: jsonl 数据源目录（仅 mode=jsonl 时使用）
    """
    # 1. 构造时间范围
    start_time = f"{target_date_str} 00:00:00"
    end_time = f"{target_date_str} 23:59:59"
    
    print(f"🚀 正在处理日期: {target_date_str} (mode={mode})")
    
    # 2. 获取新闻数据
    if mode == "live":
        print(f"📡 [live] 从新浪快讯接口抓取数据...")
        max_retries = 3
        retry_count = 0
        data = []
        
        while retry_count < max_retries:
            try:
                data = get_sina_724_dt_range(start_time, end_time, save=False)
                break  # 成功则跳出循环
            except Exception as e:
                retry_count += 1
                if retry_count < max_retries:
                    print(f"⚠️ [重试 {retry_count}/{max_retries}] 抓取异常: {e}. 正在重试...")
                else:
                    raise e  # 超过重试次数，抛出异常
        
        if not data:
            print(f"⚠️ [live] 未抓取到 {target_date_str} 的新闻数据。")
            return
        
        print(f"✅ [live] 已抓取 {len(data)} 条新闻。")
        
    elif mode == "jsonl":
        print(f"📂 [jsonl] 从 {news_data_dir} 加载本地数据...")
        result = load_and_merge_news(news_data_dir, start_time, end_time)
        data = result.get("data", [])
        
        if not data:
            print(f"⚠️ [jsonl] 未找到 {target_date_str} 的新闻数据，请检查 {news_data_dir} 目录。")
            return
        
        print(f"✅ [jsonl] 已加载 {len(data)} 条新闻。")
    
    else:
        print(f"❌ 未知的 mode: {mode}，请使用 'jsonl' 或 'live'。")
        return

    # 3. 转换为 AI 提示词块 (已在 utils 内部实现正序 + Chunk ID)
    news_text_list = transform_to_ai_text(data)
    
    # 4. 合并所有块并保存
    # 保存路径: ./news_text/{YYYY-MM-DD}/news_ai_{YYYY-MM-DD}.txt
    date_subdir = os.path.join(output_dir, target_date_str)
    os.makedirs(date_subdir, exist_ok=True)
    
    file_name = f"news_ai_{target_date_str}.txt"
    output_path = os.path.join(date_subdir, file_name)
    
    full_content = "".join(news_text_list)
    save_text_file(full_content, output_path)
    
    print(f"💾 转换完成！AI 文本已保存至: {output_path}")

if __name__ == "__main__":
    # 默认处理今天，或者通过参数传入日期
    if len(sys.argv) > 1:
        date_to_process = sys.argv[1]
    else:
        date_to_process = datetime.now().strftime("%Y-%m-%d")
    
    # 默认使用 jsonl 模式
    mode = "jsonl"
    if len(sys.argv) > 2:
        mode = sys.argv[2]
    
    # 示例:
    #   python sync_to_ai.py                    # jsonl 模式，处理今天
    #   python sync_to_ai.py 2026-04-18          # jsonl 模式，处理指定日期
    #   python sync_to_ai.py 2026-04-18 live     # live 模式，处理指定日期
    
    sync_news_to_ai_text(date_to_process, mode=mode)
