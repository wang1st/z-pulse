#!/usr/bin/env python3
"""
测试 weRSS 抓取：随机选择 5 个公众号，设置 end_page=10 进行抓取
"""
import os
import sys
import time
import sqlite3
import subprocess

WERSS_DB_PATH = "/app/data/werss.db"
WERSS_URL = "http://localhost:8080"

def get_random_feeds(count=5):
    """获取随机公众号列表"""
    if not os.path.exists(WERSS_DB_PATH):
        print(f"❌ weRSS 数据库不存在: {WERSS_DB_PATH}")
        return []
    
    conn = sqlite3.connect(WERSS_DB_PATH)
    cursor = conn.cursor()
    
    # 更新 max_page 配置为 10
    cursor.execute('UPDATE config_management SET config_value = "10" WHERE config_key = "max_page"')
    conn.commit()
    
    # 获取随机公众号
    cursor.execute(f'''
        SELECT id, mp_name 
        FROM feeds 
        WHERE status = 1 
        ORDER BY RANDOM() 
        LIMIT {count}
    ''')
    
    feeds = cursor.fetchall()
    conn.close()
    
    return feeds

def login_werss():
    """登录 weRSS 获取 token"""
    import urllib.request
    import urllib.parse
    import json
    
    url = f"{WERSS_URL}/api/v1/wx/auth/login"
    data = urllib.parse.urlencode({
        "username": "admin",
        "password": "admin@123"
    }).encode()
    
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode())
            token = result.get("data", {}).get("access_token")
            if token:
                return token
            else:
                print(f"❌ 登录失败: {result}")
                return None
    except Exception as e:
        print(f"❌ 登录失败: {e}")
        return None

def trigger_collect(mp_id, token, start_page=0, end_page=10):
    """触发公众号抓取"""
    import urllib.request
    import urllib.parse
    import json
    
    url = f"{WERSS_URL}/api/v1/wx/mps/update/{mp_id}?start_page={start_page}&end_page={end_page}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode())
            code = result.get("code", 0)
            if code == 0:
                return True, "成功"
            elif code == 40402:
                return False, "频繁更新限制（需要等待60秒）"
            else:
                return False, result.get("message", "未知错误")
    except Exception as e:
        return False, str(e)

def main():
    print("=" * 60)
    print("测试 weRSS 抓取（end_page=10）")
    print("=" * 60)
    print()
    
    # 1. 获取随机公众号
    print("步骤 1: 获取随机公众号...")
    feeds = get_random_feeds(5)
    if not feeds:
        print("❌ 未找到活跃公众号")
        return
    
    print(f"✅ 找到 {len(feeds)} 个测试公众号：")
    for feed in feeds:
        print(f"  - {feed[1]} (ID: {feed[0]})")
    print()
    
    # 2. 登录
    print("步骤 2: 登录 weRSS...")
    token = login_werss()
    if not token:
        print("❌ 登录失败，无法继续")
        return
    print("✅ 登录成功")
    print()
    
    # 3. 触发抓取
    print("步骤 3: 触发公众号抓取（end_page=10）...")
    print("注意：每个公众号有 60 秒的防频繁更新限制")
    print()
    
    success_count = 0
    failed_count = 0
    
    for i, (mp_id, mp_name) in enumerate(feeds, 1):
        print(f"[{i}/{len(feeds)}] 触发 {mp_name} (ID: {mp_id})...")
        success, message = trigger_collect(mp_id, token, end_page=10)
        
        if success:
            print(f"  ✅ 成功")
            success_count += 1
        else:
            print(f"  ⚠️  {message}")
            failed_count += 1
        
        # 等待 2 秒，避免过快请求
        if i < len(feeds):
            time.sleep(2)
    
    print()
    print(f"完成: 成功 {success_count}, 失败/跳过 {failed_count}")
    print()
    print("步骤 4: 等待抓取完成...")
    print("建议等待 2-3 分钟后，再触发 ingestion-worker 提取文章")
    print()
    print("=" * 60)

if __name__ == "__main__":
    main()

