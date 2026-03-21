import os
import sys
import subprocess
from datetime import datetime, timedelta

# ==========================================
# 路径兼容处理 (支持打包后的相对路径)
# ==========================================
if getattr(sys, 'frozen', False):
    # 如果是打包后的可执行文件
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # 如果是直接运行脚本
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 确保能导入同目录下的 utils
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

try:
    from news_scanner_utils import get_sina_724_dt_range, logger
except ImportError as e:
    print(f"ImportError: {e}")
    sys.exit(1)

def send_feishu_notification(message):
    """
    通过调用系统命令 openclaw 来发送飞书消息
    """
    chat_id = "chat:oc_de08a04b348dbb2d533930b6429b2b7c"
    try:
        # 使用 subprocess 调用 openclaw 命令行工具
        # 注意：打包后需要确保系统路径中有 openclaw
        cmd = ["openclaw", "message", "send", "--target", chat_id, "--message", message]
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"📡 飞书通知已发送: {message}")
    except Exception as e:
        print(f"⚠️ 无法发送飞书通知: {e}")

def auto_sync():
    now = datetime.now()
    # 如果是凌晨 00:30 左右运行，我们补全的是昨天的数据
    if now.hour == 0 and now.minute < 45:
        target_date = now - timedelta(days=1)
    else:
        target_date = now

    date_str = target_date.strftime("%Y-%m-%d")
    f_start = f"{date_str} 00:00:00"
    f_end = f"{date_str} 23:59:59"

    start_msg = f"🚀 [定时任务启动] 正在同步 {date_str} 的数据..."
    print(start_msg)
    
    try:
        # 核心逻辑：获取数据并保存，增加重试机制
        max_retries = 3
        retry_count = 0
        dumped_data = []
        
        while retry_count < max_retries:
            try:
                dumped_data = get_sina_724_dt_range(f_start, f_end, save=True)
                break  # 成功则跳出循环
            except Exception as e:
                retry_count += 1
                if retry_count < max_retries:
                    print(f"⚠️ [重试 {retry_count}/{max_retries}] 同步异常: {e}. 正在重试...")
                else:
                    raise e  # 超过重试次数，抛出异常
        
        count = len(dumped_data)
        success_msg = f"✅ [定时任务完成] 日期 {date_str} 同步成功，共计 {count} 条。"
        print(success_msg)
        
        # 任务成功后发送消息
        send_feishu_notification(success_msg)
        
        return date_str, count
    except Exception as e:
        error_msg = f"❌ [定时任务失败] 日期 {date_str} 同步异常: {e}"
        print(error_msg)
        
        # 任务失败也要发通知
        send_feishu_notification(error_msg)
        return date_str, -1

if __name__ == "__main__":
    auto_sync()
