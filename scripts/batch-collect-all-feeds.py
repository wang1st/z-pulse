#!/usr/bin/env python3
"""
批量触发所有公众号的全量抓取（end_page=10）
"""
import sqlite3
import urllib.request
import urllib.parse
import json
import time
import os

WERSS_DB_PATH = "/app/data/werss.db"
WERSS_URL = "http://localhost:8001"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin@123"

def get_all_feeds():
    """获取所有活跃公众号"""
    if not os.path.exists(WERSS_DB_PATH):
        print(f"❌ weRSS 数据库不存在: {WERSS_DB_PATH}")
        return []
    
    conn = sqlite3.connect(WERSS_DB_PATH)
    cursor = conn.cursor()
    
    # 更新 max_page 配置为 10
    cursor.execute('UPDATE config_management SET config_value = "10" WHERE config_key = "max_page"')
    conn.commit()
    
    # 获取所有活跃公众号
    cursor.execute('SELECT id, mp_name FROM feeds WHERE status = 1 ORDER BY mp_name')
    feeds = cursor.fetchall()
    conn.close()
    
    return feeds

def login_werss():
    """登录 weRSS 获取 token"""
    url = f"{WERSS_URL}/api/v1/wx/auth/login"
    data = urllib.parse.urlencode({
        "username": ADMIN_USERNAME,
        "password": ADMIN_PASSWORD
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

def get_article_count(date_str="2026-01-01"):
    """获取指定日期的文章数量"""
    if not os.path.exists(WERSS_DB_PATH):
        return 0
    
    conn = sqlite3.connect(WERSS_DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(f'''
        SELECT COUNT(*) 
        FROM articles 
        WHERE DATE(datetime(publish_time, 'unixepoch')) = '{date_str}'
    ''')
    
    count = cursor.fetchone()[0]
    conn.close()
    
    return count

def main():
    print("=" * 70)
    print("批量触发所有公众号的全量抓取（end_page=10）")
    print("=" * 70)
    print()
    
    # 1. 记录当前文章数量
    print("步骤 1: 记录当前 1月1日的文章数量...")
    initial_count = get_article_count("2026-01-01")
    print(f"✅ 当前 1月1日的文章数量: {initial_count} 篇")
    print()
    
    # 2. 获取所有公众号
    print("步骤 2: 获取所有活跃公众号...")
    feeds = get_all_feeds()
    if not feeds:
        print("❌ 未找到活跃公众号")
        return
    
    print(f"✅ 找到 {len(feeds)} 个活跃公众号")
    print()
    
    # 3. 登录
    print("步骤 3: 登录 weRSS...")
    token = login_werss()
    if not token:
        print("❌ 登录失败，无法继续")
        return
    print("✅ 登录成功")
    print()
    
    # 4. 批量触发抓取
    print("步骤 4: 批量触发公众号抓取（end_page=10）...")
    print("⚠️  注意：每个公众号有 60 秒的防频繁更新限制")
    print("⚠️  由于有 96 个公众号，完整抓取可能需要很长时间")
    print()
    
    success_count = 0
    failed_count = 0
    skip_count = 0
    
    # 每10个公众号显示一次进度
    for i, (mp_id, mp_name) in enumerate(feeds, 1):
        if i % 10 == 0 or i == 1:
            print(f"[进度: {i}/{len(feeds)}] 触发 {mp_name} (ID: {mp_id})...")
        
        success, message = trigger_collect(mp_id, token, end_page=10)
        
        if success:
            success_count += 1
            if i % 10 == 0:
                print(f"  ✅ 成功")
        else:
            if "频繁更新" in message:
                skip_count += 1
                if i % 10 == 0:
                    print(f"  ⚠️  跳过（频繁更新限制）")
            else:
                failed_count += 1
                if i % 10 == 0:
                    print(f"  ❌ 失败: {message}")
        
        # 等待 2 秒，避免过快请求
        if i < len(feeds):
            time.sleep(2)
    
    print()
    print(f"完成: 成功 {success_count}, 跳过 {skip_count}, 失败 {failed_count}")
    print()
    
    # 5. 等待抓取完成
    print("步骤 5: 等待抓取完成...")
    print("建议等待 5-10 分钟后，再统计新增文章数量")
    print()
    
    # 6. 统计新增数量
    print("步骤 6: 统计新增文章数量...")
    print("等待 30 秒后开始统计...")
    time.sleep(30)
    
    final_count = get_article_count("2026-01-01")
    new_count = final_count - initial_count
    
    print()
    print("=" * 70)
    print("统计结果")
    print("=" * 70)
    print(f"初始数量: {initial_count} 篇")
    print(f"最终数量: {final_count} 篇")
    print(f"新增数量: {new_count} 篇")
    print("=" * 70)

if __name__ == "__main__":
    main()

