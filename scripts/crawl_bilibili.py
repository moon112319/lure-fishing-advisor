#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
香蕉路亚视频信息爬取脚本
从B站爬取香蕉路亚（香蕉不拿拿）的视频信息，提取钓场、鱼种等数据
"""

import json
import os
import re
import requests
import time
from datetime import datetime

# 香蕉路亚的B站用户ID（需要从实际页面获取）
# 可以通过搜索用户名获取用户ID
BILIBILI_USER = "香蕉路亚香蕉不拿拿"
BILIBILI_UID = None  # 需要先获取用户ID

# 输出文件
OUTPUT_FILE = "../fish-stock-data.json"

def get_bilibili_uid(username):
    """通过用户名搜索获取B站用户ID"""
    search_url = f"https://api.bilibili.com/x/web-interface/search/type?search_type=bili_user&keyword={username}"
    try:
        response = requests.get(search_url, timeout=10)
        data = response.json()
        if data['code'] == 0 and data['data']['result']:
            return data['data']['result'][0]['mid']
    except Exception as e:
        print(f"获取用户ID失败: {e}")
    return None

def get_user_videos(uid, pn=1):
    """获取用户的视频列表"""
    url = f"https://api.bilibili.com/x/space/wbi/arc/search?mid={uid}&ps=20&pn={pn}"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        if data['code'] == 0:
            return data['data']['list']['vlist']
    except Exception as e:
        print(f"获取视频列表失败: {e}")
    return []

def parse_video_info(video):
    """从视频标题和描述中提取钓场信息"""
    title = video.get('title', '')
    description = video.get('description', '')
    pubdate = video.get('created', 0)
    
    # 转换时间戳
    pub_date = datetime.fromtimestamp(pubdate).strftime('%Y-%m-%d') if pubdate else ''
    
    # 尝试从标题中提取钓场名称
    # 常见的钓场名称模式：| 分隔，或者包含"钓场"、"路亚"、"塘"等关键词
    location = ""
    
    # 模式1: 标题中包含地名+路亚/钓场
    location_patterns = [
        r'\|([^|]+?(?:路亚|钓场|鱼塘|基地))',
        r'探钓([^|]+?)[|\s]',
        r'([^|]+?(?:路亚|钓场|鱼塘|基地))[^|]*$',
    ]
    
    for pattern in location_patterns:
        match = re.search(pattern, title)
        if match:
            location = match.group(1).strip()
            break
    
    # 尝试提取鱼种
    fish_species = []
    known_fish = ['鲈鱼', '鳜鱼', '翘嘴', '黑鱼', '马口', '红尾', '鳡鱼', '罗非', '鲶鱼', '海鲈', 
                   '溪哥', '军鱼', '鳟鱼', '白条', '青稍', '太阳鱼', '金目鲈', '美国红']
    
    for fish in known_fish:
        if fish in title or fish in description:
            fish_species.append(fish)
    
    # 尝试提取价格信息
    price = ""
    price_pattern = r'(\d+)\s*元|(\d+)\s*块|票价\s*(\d+)'
    price_match = re.search(price_pattern, title + description)
    if price_match:
        price = price_match.group(0)
    
    return {
        'source': '香蕉路亚',
        'video_title': title,
        'video_url': f"https://www.bilibili.com/video/{video.get('bvid', '')}",
        'location': location,
        'fish_species': fish_species,
        'price': price,
        'date': pub_date,
        'description': description[:200] if description else '',
        'type': 'review'  # 评测类型
    }

def main():
    """主函数"""
    print("开始爬取香蕉路亚的B站视频...")
    
    # 获取用户ID
    uid = get_bilibili_uid(BILIBILI_USER)
    if not uid:
        print("无法获取用户ID，请手动设置 BILIBILI_UID")
        # 使用已知的UID（需要通过网页获取）
        return
    
    print(f"获取到用户ID: {uid}")
    
    # 获取最新视频（前3页，每页20个）
    all_videos = []
    for page in range(1, 4):
        videos = get_user_videos(uid, page)
        if not videos:
            break
        all_videos.extend(videos)
        time.sleep(1)  # 避免请求过快
    
    print(f"获取到 {len(all_videos)} 个视频")
    
    # 解析视频信息
    results = []
    for video in all_videos:
        info = parse_video_info(video)
        if info['location'] or info['fish_species']:  # 只保存有信息的视频
            results.append(info)
    
    print(f"提取到 {len(results)} 条有效信息")
    
    # 读取现有数据
    output_path = os.path.join(os.path.dirname(__file__), OUTPUT_FILE)
    existing_data = {'reviews': [], 'stock_info': []}
    
    if os.path.exists(output_path):
        try:
            with open(output_path, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
        except:
            pass
    
    # 更新评测数据
    existing_data['reviews'] = results
    existing_data['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 保存数据
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(existing_data, f, ensure_ascii=False, indent=2)
    
    print(f"数据已保存到: {output_path}")
    print(f"共保存 {len(results)} 条评测信息")

if __name__ == "__main__":
    main()
