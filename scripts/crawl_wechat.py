#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信公众号路亚放鱼信息爬取脚本
通过搜狗微信搜索等渠道获取路亚钓场的放鱼信息
"""

import json
import os
import re
import time
import random
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

OUTPUT_FILE = "../fish-stock-data.json"

# 搜索关键词
SEARCH_QUERIES = [
    "上海路亚放鱼",
    "路亚钓场放鱼通知",
    "上海路亚基地放鱼",
    "路亚塘放鱼信息",
    "上海路亚本周放鱼"
]

# 已知上海路亚钓场公众号关键词
VENUE_ACCOUNTS = [
    "荷风路亚", "玫瑰仙境", "晴天路亚", "PE路亚营地",
    "火山路亚", "大乐路亚", "沪岩之星", "玲珑路亚",
    "星辰路亚", "君宴路亚", "BKB路亚", "青松路亚",
    "探野星空", "华亭路亚", "嘻哈钓场", "金鹿路亚",
    "嘉年华路亚", "小袁钓场", "澜山钓场", "春池路亚",
]

REQ_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}


def safe_get(url, timeout=15, retries=3):
    for i in range(retries):
        try:
            r = requests.get(url, headers=REQ_HEADERS, timeout=timeout)
            if r.status_code == 200:
                return r
            time.sleep(2)
        except Exception as e:
            print(f"  请求失败(尝试{i+1}): {e}")
            time.sleep(2)
    return None


def search_sogou_wechat(keyword):
    """搜狗微信搜索"""
    results = []
    url = f"https://weixin.sogou.com/weixin?type=2&query={keyword}&ie=utf8"
    resp = safe_get(url)
    if not resp:
        return results
    
    soup = BeautifulSoup(resp.text, 'html.parser')
    items = soup.select('.news-box .news-list2 li')
    
    for item in items[:10]:
        try:
            title_el = item.select_one('.txt-box h3 a')
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            link = title_el.get('href', '')
            if link and not link.startswith('http'):
                link = 'https://weixin.sogou.com' + link
            
            desc_el = item.select_one('.txt-box p')
            desc = desc_el.get_text(strip=True) if desc_el else ''
            
            date_el = item.select_one('.txt-box .s-p')
            date_text = date_el.get_text(strip=True) if date_el else ''
            
            results.append({
                'title': title,
                'desc': desc,
                'link': link,
                'date': date_text,
                'keyword': keyword,
            })
        except:
            continue
    
    return results


def parse_article_for_stock(text, pub_date):
    """从文章标题/摘要中解析放鱼信息"""
    full_text = text.strip()
    if not full_text or len(full_text) < 8:
        return []
    
    results = []
    found_venue = None
    
    # 匹配钓场名称
    for v in VENUE_ACCOUNTS:
        if v in full_text:
            found_venue = v
            break
    
    if not found_venue:
        patterns = [
            r'([\u4e00-\u9fff]{2,8}(?:路亚|钓场|鱼塘|基地|塘|园|庄))',
            r'([\u4e00-\u9fff]{2,6}(?:垂钓|休闲))[场园]',
        ]
        for p in patterns:
            m = re.search(p, full_text)
            if m:
                found_venue = m.group(1)
                break
    
    if not found_venue:
        return results
    
    # 提取鱼种
    FISH = ['鲈鱼','加州鲈','海鲈','金目鲈','鳜鱼','翘嘴','红尾',
            '黑鱼','鳡鱼','鳟鱼','罗非','鲶鱼','马口','军鱼',
            '太阳鱼','白条','青稍','美国红','鲳鱼']
    fish_found = [f for f in FISH if f in full_text]
    
    if not fish_found:
        return results
    
    # 提取数量和价格
    stock_count = ""
    for p in [r'(\d+)[斤千克]', r'放鱼\s*(\d+)\s*[斤千克]', r'(\d+)斤']:
        m = re.search(p, full_text)
        if m:
            stock_count = m.group(1) + "斤"
            break
    
    price = ""
    for p in [r'(\d+)\s*元/[天人场]', r'票价[：:]?\s*(\d+)', r'(\d+)\s*元\s']:
        m = re.search(p, full_text)
        if m:
            price = m.group(1) + "元/天"
            break
    
    # 提取日期
    specific_date = ""
    m = re.search(r'(\d{1,2})月(\d{1,2})[日号]', full_text)
    if m:
        mt, dy = int(m.group(1)), int(m.group(2))
        specific_date = f"{datetime.now().year}-{mt:02d}-{dy:02d}"
    
    desc = full_text[:150]
    results.append({
        'source': '微信公众号',
        'location': found_venue,
        'address': '',
        'fish_species': fish_found[:5],
        'stock_count': stock_count,
        'price': price,
        'date': specific_date or (datetime.now().strftime('%Y-%m-%d')),
        'type': 'stock_info',
        'note': desc
    })
    return results


def search_venue_direct(name):
    """直接搜索特定钓场公众号"""
    results = []
    url = f"https://weixin.sogou.com/weixin?type=2&query={name}+放鱼&ie=utf8"
    resp = safe_get(url, timeout=10, retries=2)
    if not resp:
        return results
    
    soup = BeautifulSoup(resp.text, 'html.parser')
    items = soup.select('.news-box .news-list2 li')
    
    for item in items[:5]:
        try:
            title_el = item.select_one('.txt-box h3 a')
            if not title_el:
                continue
            text = title_el.get_text(strip=True) + ' '
            desc_el = item.select_one('.txt-box p')
            if desc_el:
                text += desc_el.get_text(strip=True)
            
            stock = parse_article_for_stock(text, datetime.now().strftime('%Y-%m-%d'))
            results.extend(stock)
        except:
            continue
    
    return results


def main():
    print("=" * 50)
    print("[微信公众号] 路亚放鱼信息爬取")
    print(f"[时间] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    all_results = []
    seen_venues = set()
    
    # 策略1: 搜狗微信关键词搜索
    print("\n[策略1] 关键词搜索...")
    for kw in SEARCH_QUERIES[:4]:
        print(f"  搜索: {kw}")
        articles = search_sogou_wechat(kw)
        for a in articles:
            text = a['title'] + ' ' + a['desc']
            stock = parse_article_for_stock(text, a['date'])
            for s in stock:
                v = s['location']
                if v not in seen_venues:
                    all_results.append(s)
                    seen_venues.add(v)
        time.sleep(random.uniform(1, 2))
    
    # 策略2: 逐个搜索已知钓场
    print(f"\n[策略2] 逐个搜索已知钓场...")
    for v in VENUE_ACCOUNTS[:8]:
        print(f"  搜索: {v}")
        stock = search_venue_direct(v)
        for s in stock:
            vn = s['location']
            if vn not in seen_venues:
                all_results.append(s)
                seen_venues.add(vn)
        time.sleep(random.uniform(0.5, 1.5))
    
    print(f"\n[结果] 共获取到 {len(all_results)} 条")
    
    # 读取并合并现有数据
    output_path = os.path.join(os.path.dirname(__file__), OUTPUT_FILE)
    existing = {'reviews': [], 'stock_info': []}
    if os.path.exists(output_path):
        try:
            with open(output_path, 'r', encoding='utf-8') as f:
                existing = json.load(f)
        except:
            pass
    
    old_stock = existing.get('stock_info', [])
    cutoff = datetime.now() - timedelta(days=30)
    kept = []
    for item in old_stock:
        try:
            d = datetime.strptime(item.get('date','2000-01-01'), '%Y-%m-%d')
            src = item.get('source', '')
            if d > cutoff and '微信' not in src:
                kept.append(item)
        except:
            pass
    
    merged = all_results + kept
    dedup = {}
    for item in merged:
        dedup[item['location']] = item
    merged = list(dedup.values())[:50]
    
    existing['stock_info'] = merged
    existing['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
        print(f"[保存] {output_path} ({len(merged)}条)")
        if all_results:
            print("\n  新增:")
            for s in all_results:
                fish = '/'.join(s['fish_species'][:3])
                print(f"    {s['location']} | {fish} | {s.get('stock_count','')}")
    except Exception as e:
        print(f"[保存失败] {e}")
    
    return len(merged)


if __name__ == '__main__':
    main()
