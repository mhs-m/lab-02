from mcp.server.fastmcp import FastMCP
import httpx
from pypdf import PdfReader
import json
import re

# 创建 MCP 服务器实例
mcp = FastMCP("超级工具集")

# ========== 工具1：网页内容获取 ==========
@mcp.tool()
def fetch_webpage(url: str, max_chars: int = 5000) -> str:
    """获取指定 URL 的网页文本内容（去除 HTML 标签后返回纯文本）。
    
    Args:
        url: 完整的网页 URL，如 'https://example.com'。
        max_chars: 最大返回字符数，默认 5000，防止内容过长。
    """
    try:
        response = httpx.get(url, timeout=10)
        response.raise_for_status()
        # 简单去除 HTML 标签（用正则提取文本）
        text = re.sub(r'<[^>]+>', ' ', response.text)
        text = re.sub(r'\s+', ' ', text).strip()
        if len(text) > max_chars:
            text = text[:max_chars] + "...(内容已截断)"
        return text
    except Exception as e:
        return f"获取网页失败: {str(e)}"

# ========== 工具2：PDF 文件读取 ==========
@mcp.tool()
def read_pdf(file_path: str, max_pages: int = 10) -> str:
    """读取本地 PDF 文件，提取纯文本内容（最多前 max_pages 页）。
    
    Args:
        file_path: PDF 文件的绝对路径。
        max_pages: 最多读取的页数，默认 10 页，避免过长。
    """
    try:
        reader = PdfReader(file_path)
        total_pages = len(reader.pages)
        pages_to_read = min(max_pages, total_pages)
        text_parts = []
        for i in range(pages_to_read):
            page = reader.pages[i]
            page_text = page.extract_text()
            if page_text:
                text_parts.append(f"--- 第 {i+1} 页 ---\n{page_text}")
        if not text_parts:
            return "PDF 中未提取到文本内容（可能为扫描件）。"
        full_text = "\n\n".join(text_parts)
        # 限制总长度（避免超过上下文窗口）
        if len(full_text) > 20000:
            full_text = full_text[:20000] + "...(内容已截断)"
        return full_text
    except Exception as e:
        return f"读取 PDF 失败: {str(e)}"

# ========== 工具3：获取指定城市的当前天气状况 ==========
@mcp.tool()
def get_current_weather(city: str) -> str:
    """获取指定城市的当前实时天气（温度、风速、天气状况）。
    
    Args:
        city: 城市名称（中文或英文均可），如 '北京' 或 'Beijing'。
    """
    try:
        # 1. 通过城市名获取经纬度（使用 Open-Meteo Geocoding API，免费无key）
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=zh&format=json"
        geo_resp = httpx.get(geo_url, timeout=5)
        geo_data = geo_resp.json()
        if not geo_data.get("results"):
            return f"未找到城市 '{city}' 的地理信息，请检查名称。"
        
        result = geo_data["results"][0]
        lat = result["latitude"]
        lon = result["longitude"]
        name = result.get("name", city)
        country = result.get("country", "")
        
        # 2. 获取实时天气（Open-Meteo 当前天气 API）
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&timezone=auto"
        weather_resp = httpx.get(weather_url, timeout=5)
        weather_data = weather_resp.json()
        
        if "current_weather" not in weather_data:
            return "未能获取到天气数据。"
        
        current = weather_data["current_weather"]
        temperature = current["temperature"]
        windspeed = current["windspeed"]
        weathercode = current.get("weathercode", 0)
        
        # 天气代码映射（常用代码）
        code_map = {
            0: "晴朗",
            1: "大致晴朗",
            2: "局部多云",
            3: "多云",
            45: "雾",
            48: "霜雾",
            51: "小毛毛雨",
            53: "毛毛雨",
            55: "密集毛毛雨",
            61: "小雨",
            63: "中雨",
            65: "大雨",
            71: "小雪",
            73: "中雪",
            75: "大雪",
            80: "阵雨",
            81: "中阵雨",
            82: "大阵雨",
            95: "雷暴",
            96: "雷暴伴有小雪",
            99: "雷暴伴有大雪"
        }
        description = code_map.get(weathercode, f"未知代码 {weathercode}")
        
        return (f"{name}（{country}）当前天气：\n"
                f"🌡️ 温度：{temperature}°C\n"
                f"💨 风速：{windspeed} km/h\n"
                f"☁️ 天气状况：{description}")
    except Exception as e:
        return f"获取天气失败: {str(e)}"

# ========== 启动服务器 ==========
if __name__ == "__main__":
    mcp.run(transport="stdio")