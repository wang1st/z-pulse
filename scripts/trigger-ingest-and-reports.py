#!/usr/bin/env python3
"""
触发 ingestion-worker 提取文章并重新生成报告
"""
import os
import sys
import time
try:
    import httpx
except ImportError:
    try:
        import requests
        httpx = None
    except ImportError:
        print("❌ 需要安装 httpx 或 requests: pip install httpx")
        sys.exit(1)
from datetime import date

# 配置
API_URL = os.getenv("API_URL", "http://localhost:8000")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin@123")

def get_token():
    """登录获取 token"""
    print("步骤 1: 登录 API 获取 token...")
    try:
        if httpx:
            with httpx.Client(timeout=20) as client:
                resp = client.post(
                    f"{API_URL}/api/auth/token",
                    data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                resp.raise_for_status()
                data = resp.json()
        else:
            resp = requests.post(
                f"{API_URL}/api/auth/token",
                data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=20,
            )
            resp.raise_for_status()
            data = resp.json()
        
        token = data.get("access_token")
        if not token:
            print("❌ 登录失败：未获取到 token")
            sys.exit(1)
        print("✅ 登录成功")
        return token
    except Exception as e:
        print(f"❌ 登录失败: {e}")
        sys.exit(1)

def trigger_collection(token):
    """触发文章采集"""
    print("\n步骤 2: 触发 ingestion-worker 提取文章...")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        if httpx:
            with httpx.Client(timeout=20) as client:
                resp = client.post(
                    f"{API_URL}/api/admin/articles/collect",
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()
        else:
            resp = requests.post(
                f"{API_URL}/api/admin/articles/collect",
                headers=headers,
                timeout=20,
            )
            resp.raise_for_status()
            data = resp.json()
        
        job_id = data.get("job_id")
        if not job_id:
            print("❌ 触发失败：未获取到 job_id")
            print(f"响应: {data}")
            sys.exit(1)
        print(f"✅ 已触发采集任务 (Job ID: {job_id})")
        return job_id
    except Exception as e:
        print(f"❌ 触发失败: {e}")
        sys.exit(1)

def wait_for_collection(token, job_id):
    """等待采集完成"""
    print("\n步骤 3: 等待 ingestion-worker 完成...")
    print("正在监控任务状态...")
    
    max_wait = 1800  # 30分钟
    elapsed = 0
    interval = 10
    
    while elapsed < max_wait:
        try:
            headers = {"Authorization": f"Bearer {token}"}
            params = {"job_id": job_id}
            if httpx:
                with httpx.Client(timeout=20) as client:
                    resp = client.get(
                        f"{API_URL}/api/admin/articles/collect/status",
                        params=params,
                        headers=headers,
                    )
                    resp.raise_for_status()
                    data = resp.json()
            else:
                resp = requests.get(
                    f"{API_URL}/api/admin/articles/collect/status",
                    params=params,
                    headers=headers,
                    timeout=20,
                )
                resp.raise_for_status()
                data = resp.json()
                status = data.get("status", "unknown")
                
                if status in ("success", "SUCCESS"):
                    new_articles = data.get("new_articles", 0)
                    print(f"✅ ingestion-worker 已完成")
                    print(f"  新提取文章数: {new_articles}")
                    return True
                elif status in ("failed", "FAILED"):
                    print(f"❌ ingestion-worker 失败")
                    return False
                else:
                    print(f"  状态: {status} (已等待 {elapsed} 秒)")
                    time.sleep(interval)
                    elapsed += interval
        except Exception as e:
            print(f"  检查状态时出错: {e}")
            time.sleep(interval)
            elapsed += interval
    
    print("⚠️  等待超时，但继续执行报告生成")
    return False

def regenerate_report(token, report_date: str):
    """重新生成指定日期的报告"""
    print(f"\n重新生成 {report_date} 的晨报...")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        params = {"force": "true"}
        if httpx:
            with httpx.Client(timeout=30) as client:
                resp = client.post(
                    f"{API_URL}/api/admin/reports/daily/{report_date}/regenerate",
                    params=params,
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()
        else:
            resp = requests.post(
                f"{API_URL}/api/admin/reports/daily/{report_date}/regenerate",
                params=params,
                headers=headers,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            job_id = data.get("job_id")
            if job_id:
                print(f"✅ 已触发 {report_date} 晨报重新生成 (Job ID: {job_id})")
                return True
            else:
                print(f"⚠️  触发 {report_date} 晨报重新生成失败或已存在")
                print(f"响应: {data}")
                return False
    except Exception as e:
        print(f"⚠️  触发 {report_date} 晨报重新生成失败: {e}")
        return False

def main():
    print("=" * 50)
    print("触发 ingestion-worker 并生成报告")
    print("=" * 50)
    print()
    
    # 1. 登录
    token = get_token()
    
    # 2. 触发采集
    job_id = trigger_collection(token)
    
    # 3. 等待采集完成
    collection_success = wait_for_collection(token, job_id)
    
    if not collection_success:
        print("\n⚠️  采集可能未完全完成，但继续生成报告...")
    
    # 4. 重新生成报告
    print("\n步骤 4: 重新生成晨报...")
    regenerate_report(token, "2026-01-02")
    regenerate_report(token, "2026-01-03")
    
    print("\n" + "=" * 50)
    print("完成！")
    print("=" * 50)
    print("\n注意：报告生成是异步任务，系统会自动发送给订阅用户")

if __name__ == "__main__":
    main()

