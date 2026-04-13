import re
import json
import logging
import requests
import pandas as pd
from datetime import datetime, timedelta
from fastembed import TextEmbedding
from typing import List, Dict, Optional, Any, Union

# ==========================================
# 全局配置与日志系统
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("SinaScanner")


# ==========================================
# 核心引擎类
# ==========================================
class SinaNewsScanner:
    """
    新浪7x24快讯抓取与处理引擎
    封装了网络请求、数据解析及语义模型管理
    """
    def __init__(self, model_name: str = 'BAAI/bge-small-zh-v1.5', model_path = None) -> None:
        """
        初始化引擎
        :param model_name: 用于语义过滤的 sentence-transformers 模型名称
        """
        self.base_url = "https://zhibo.sina.com.cn/api/zhibo/feed"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        self.model_name = model_name
        self.model_path = model_path
        self._semantic_model = None  # 懒加载

    @property
    def semantic_model(self) -> Any:
        """
        获取语义模型实例（单例模式）
        :return: SentenceTransformer 模型对象
        """
        if self._semantic_model is None:
            logger.info(f"⏳ 正在加载语义模型: {self.model_name}...")
            self._semantic_model = TextEmbedding(model_name=self.model_name, 
                                                 specific_model_path=self.model_path
                                                 )
            logger.info("✅ 模型加载成功")
        return self._semantic_model

    def clean_html(self, html_text: str) -> str:
        """
        去除文本中的 HTML 标签及特殊转义字符
        :param html_text: 包含 HTML 的原始文本
        :return: 纯文本字符串
        """
        if not html_text: return ""
        clean = re.compile('<.*?>')
        text = re.sub(clean, '', html_text)
        text = text.replace('&nbsp;', ' ').replace('&quot;', '"').replace('&amp;', '&').strip()
        return text

    def parse_item_full(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        深度解析单条新闻，处理嵌套的 ext 逻辑
        :param item: API 返回的原始字典记录
        :return: 规范化后的新闻字典
        """
        ext_raw = item.get('ext', '{}')
        ext_data = {}
        try:
            ext_data = json.loads(ext_raw) if ext_raw else {}
        except Exception:
            pass

        ext_stocks = ext_data.get('stocks', [])
        stock_list = list(set([s.get('key') for s in ext_stocks if s.get('key')]))
        
        parsed = {
            "id": item.get('id'),
            "timestamp": item.get('create_time'),
            "content": self.clean_html(item.get('rich_text') or item.get('content') or ""),
            "importance": int(item.get('is_focus', 0)),
            "is_top": int(item.get('top_value', 0)),
            "is_repeat": int(item.get('is_repeat', 0)),
            "stocks": ext_stocks,
            "stock_keys": stock_list,
            "tags": [t.get('name') for t in item.get('tag', [])],
            "raw_ext": ext_data,
            "source": item.get('creator', 'sina'),
            "doc_url": item.get('docurl', "")
        }
        # 合并兜底字段
        for k, v in item.items():
            if k not in parsed and k not in ['rich_text', 'content', 'ext', 'tag']:
                parsed[k] = v
        return parsed

    def get_page_date(self, page: int, page_size: int = 100) -> Optional[datetime]:
        """
        获取指定页码的第一条新闻时间点
        :param page: 页码
        :param page_size: 每页条数
        :return: datetime 对象或 None
        """
        params = {"page": page, "page_size": page_size, "zhibo_id": 152, "type": "all"}
        try:
            resp = requests.get(self.base_url, params=params, timeout=10).json()
            data = resp.get('result', {}).get('data', {}).get('feed', {}).get('list', [])
            if not data: return None
            return datetime.strptime(data[0]['create_time'], "%Y-%m-%d %H:%M:%S")
        except Exception as e:
            logger.error(f"❌ 页面日期获取失败 (Page {page}): {e}")
            return None
        
    def get_page_id(self, page: int, page_size: int = 100) -> Optional[int]:
        """
        获取指定页码的第一条新闻 ID
        :param page: 页码
        :param page_size: 每页条数
        :return: 新闻 ID 列表
        """
        params = {"page": page, "page_size": page_size, "zhibo_id": 152, "type": "all"}
        try:
            resp = requests.get(self.base_url, params=params, timeout=10).json()
            data = resp.get('result', {}).get('data', {}).get('feed', {}).get('list', [])
            if not data: return None
            return data[0]['id']
        except Exception as e:
            logger.error(f"❌ 页面 ID 获取失败 (Page {page}): {e}")
            return []

    def find_start_page(self, target_dt: datetime, target_id: Optional[str] = None, page_size: int = 100) -> int:
        """
        采用倍增探测+二分法精确锁定起始页码
        :param target_dt: 想要抓取的结束时间点（即扫描的起点）
        :param target_id: 想要抓取的结束时间点对应的新闻 ID（可选，优先级高于时间）
        :param page_size: 每页条数
        :return: 精确的起始扫描页码
        """
        logger.info(f"🔍 开始利用二分法定位时间区间: {target_dt}")
        
        # 1. 倍增探测锁定右边界
        left = 1
        right = 1
        while True:
            page_id = self.get_page_id(right, page_size)
            page_dt = self.get_page_date(right, page_size)
            # 否则使用时间来判断边界
            if not page_dt: # 到底了
                break
            if page_dt <= target_dt: # 找到右边界
                break
            left = right
            right *= 2
            logger.debug(f"探测中... 页码 {right} 时间 {page_dt} id {page_id}")

        # 2. 在 [left, right] 区间内进行二分查找
        ans = right
        low = left
        high = right
        
        while low <= high:
            mid = (low + high) // 2
            mid_dt = self.get_page_date(mid, page_size)
            
            if not mid_dt: # 如果 mid 超过了总页数
                high = mid - 1
                continue
                
            if mid_dt <= target_dt:
                # 这一页的时间已经比目标早了（或相等），符合条件
                # 但我们需要找的是最靠近“现在”的那一页，所以继续往左搜
                ans = mid
                high = mid - 1
            else:
                # 这一页太新了，往后（大页码）搜
                low = mid + 1
        
        # 稳妥起见，回退一页以确保覆盖边界重叠的消息
        final_page = max(1, ans - 1)
        logger.info(f"📍 定位完成：目标页码约第 {ans} 页，安全起始页定为 {final_page}")
        return final_page