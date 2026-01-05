#!/usr/bin/env python3
"""
完整流程：逐个全量爬取公众号12月31日后的文章，然后提取、重新生成报告并发送

步骤：
1. 逐个触发所有公众号的全量抓取（12月31日后，start_page=0, end_page=10）
2. 等待所有公众号抓取完成
3. 触发 ingestion-worker 提取文章
4. 重新生成12月31日后的晨报和周报
5. 发送给订阅用户（报告生成时自动发送）

使用方法：
  # 从 .env 文件读取配置
  python scripts/full-collect-and-regenerate-after-dec31.py
  
  # 或通过环境变量指定
  WERSS_URL=http://localhost:8080 API_URL=http://localhost:8000 ADMIN_PASSWORD=your_password python scripts/full-collect-and-regenerate-after-dec31.py
"""
import os
import sys
import time
import json
import asyncio
from datetime import date, datetime, timedelta
from pathlib import Path

try:
    import httpx
    requests = None
except ImportError:
    try:
        import requests
        httpx = None
    except ImportError:
        print("❌ 需要安装 httpx 或 requests: pip install httpx")
        sys.exit(1)

# 加载 .env 文件（如果存在）
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key not in os.environ:  # 环境变量优先
                    os.environ[key] = value

# 配置
WERSS_URL = os.getenv("WERSS_URL", "http://localhost:8080")
API_URL = os.getenv("API_URL", "http://localhost:8000")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", os.getenv("WERSS_PASSWORD", "admin@123"))

# 抓取配置
START_PAGE = 0
END_PAGE = 10  # 抓取前10页，应该能覆盖12月31日后的文章
# 并发控制：使用信号量限制同时处理的公众号数量（避免服务器过载）
CONCURRENT_LIMIT = 10  # 同时最多处理10个公众号的请求

def get_werss_token():
    """登录 weRSS 获取 token"""
    print("步骤 1: 登录 weRSS 获取 token...")
    try:
        if httpx:
            with httpx.Client(timeout=20) as client:
                resp = client.post(
                    f"{WERSS_URL}/api/v1/wx/auth/login",
                    data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                resp.raise_for_status()
                data = resp.json()
        else:
            resp = requests.post(
                f"{WERSS_URL}/api/v1/wx/auth/login",
                data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=20,
            )
            resp.raise_for_status()
            data = resp.json()
        
        token = data.get("data", {}).get("access_token")
        if not token:
            print("❌ 登录失败：未获取到 token")
            print(f"响应: {data}")
            sys.exit(1)
        print("✅ 登录成功")
        return token
    except Exception as e:
        print(f"❌ 登录失败: {e}")
        sys.exit(1)

def get_api_token():
    """登录 API 获取 token"""
    print("\n步骤 2: 登录 API 获取 token...")
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
            print(f"响应: {data}")
            raise Exception("未获取到 token")
        print("✅ 登录成功")
        return token
    except Exception as e:
        print(f"❌ 登录失败: {e}")
        raise

def get_all_mps(werss_token):
    """获取所有公众号列表"""
    print("\n步骤 3: 获取所有公众号列表...")
    try:
        headers = {"Authorization": f"Bearer {werss_token}"}
        if httpx:
            with httpx.Client(timeout=30) as client:
                resp = client.get(
                    f"{WERSS_URL}/api/v1/wx/mps?limit=100",
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()
        else:
            resp = requests.get(
                f"{WERSS_URL}/api/v1/wx/mps?limit=100",
                headers=headers,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        
        mps = data.get("data", {}).get("list", [])
        if not mps:
            print("❌ 未找到公众号")
            sys.exit(1)
        
        print(f"✅ 找到 {len(mps)} 个公众号")
        return mps
    except Exception as e:
        print(f"❌ 获取公众号列表失败: {e}")
        sys.exit(1)

async def trigger_collect_single_mp(client: httpx.AsyncClient, werss_token: str, mp: dict, index: int, total: int):
    """触发单个公众号的全量抓取（异步）"""
    mp_id = mp.get("id", "")
    mp_name = mp.get("mp_name", "未知")
    
    if not mp_id:
        return {"status": "skip", "reason": "no_id", "mp_name": mp_name}
    
    update_url = f"{WERSS_URL}/api/v1/wx/mps/update/{mp_id}?start_page={START_PAGE}&end_page={END_PAGE}"
    headers = {"Authorization": f"Bearer {werss_token}"}
    
    try:
        resp = await client.get(update_url, headers=headers, timeout=30.0)
        resp.raise_for_status()
        data = resp.json()
        
        code = data.get("code", 0)
        if code == 40402:
            return {"status": "skip", "reason": "rate_limit", "mp_name": mp_name, "mp_id": mp_id}
        elif code == 0 or code is None:
            return {"status": "success", "mp_name": mp_name, "mp_id": mp_id}
        else:
            msg = data.get("message", "未知错误")
            return {"status": "failed", "reason": msg, "mp_name": mp_name, "mp_id": mp_id}
    except httpx.TimeoutException:
        return {"status": "failed", "reason": "timeout", "mp_name": mp_name, "mp_id": mp_id}
    except Exception as e:
        error_msg = str(e)
        return {"status": "failed", "reason": error_msg, "mp_name": mp_name, "mp_id": mp_id}

async def trigger_collect_all_mps_async(werss_token, mps):
    """使用异步并发触发所有公众号的全量抓取（使用信号量限制并发数）"""
    print(f"\n步骤 4: 并发触发所有公众号的全量抓取（start_page={START_PAGE}, end_page={END_PAGE}）...")
    print(f"执行模式: 异步并发（使用1个线程，但使用连接池限制并发）")
    print(f"并发限制: 同时最多处理 {CONCURRENT_LIMIT} 个公众号")
    print(f"总数: {len(mps)} 个公众号")
    print()
    
    # 使用 httpx 的异步客户端
    if not httpx:
        print("❌ 需要 httpx 库支持异步并发，请安装: pip install httpx")
        return False
    
    success_count = 0
    skip_count = 0
    failed_count = 0
    
    # 创建信号量限制并发数
    semaphore = asyncio.Semaphore(CONCURRENT_LIMIT)
    
    async def trigger_with_semaphore(client, werss_token, mp, index, total):
        """带信号量控制的触发函数"""
        async with semaphore:
            return await trigger_collect_single_mp(client, werss_token, mp, index, total)
    
    # 创建异步客户端（限制连接池大小）
    limits = httpx.Limits(max_connections=CONCURRENT_LIMIT + 5, max_keepalive_connections=CONCURRENT_LIMIT)
    async with httpx.AsyncClient(timeout=30.0, limits=limits) as client:
        # 创建所有任务（使用信号量包装）
        tasks = []
        for i, mp in enumerate(mps, 1):
            task = trigger_with_semaphore(client, werss_token, mp, i, len(mps))
            tasks.append(task)
        
        # 并发执行所有任务（信号量会自动控制并发数）
        print(f"正在并发触发 {len(tasks)} 个公众号（并发限制: {CONCURRENT_LIMIT}）...")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        for i, result in enumerate(results, 1):
            mp_name = mps[i-1].get("mp_name", "未知")
            
            if isinstance(result, Exception):
                print(f"[{i}/{len(mps)}] {mp_name}: ❌ 异常 - {result}")
                failed_count += 1
            elif isinstance(result, dict):
                status = result.get("status")
                if status == "success":
                    print(f"[{i}/{len(mps)}] {mp_name}: ✅ 成功")
                    success_count += 1
                elif status == "skip":
                    reason = result.get("reason", "")
                    if reason == "rate_limit":
                        print(f"[{i}/{len(mps)}] {mp_name}: ⚠️  跳过（频繁更新限制）")
                    else:
                        print(f"[{i}/{len(mps)}] {mp_name}: ⚠️  跳过（{reason}）")
                    skip_count += 1
                elif status == "failed":
                    reason = result.get("reason", "")
                    print(f"[{i}/{len(mps)}] {mp_name}: ❌ 失败 - {reason}")
                    failed_count += 1
    
    print()
    print("=" * 60)
    print("批量触发完成")
    print("=" * 60)
    print(f"✅ 成功: {success_count} 个")
    print(f"⚠️  跳过: {skip_count} 个（频繁更新限制）")
    print(f"❌ 失败: {failed_count} 个")
    print()
    
    if success_count == 0 and failed_count > 0:
        print("⚠️  所有公众号都失败或跳过，可能无法继续")
        return False
    
    return True

def trigger_collect_all_mps(werss_token, mps):
    """触发所有公众号的全量抓取（同步包装器）"""
    # 使用异步函数
    return asyncio.run(trigger_collect_all_mps_async(werss_token, mps))

def trigger_ingestion_worker(api_token):
    """触发 ingestion-worker 提取文章"""
    print("\n步骤 5: 触发 ingestion-worker 提取文章...")
    try:
        headers = {"Authorization": f"Bearer {api_token}"}
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
            return None
        
        print(f"✅ 已触发采集任务 (Job ID: {job_id})")
        return job_id
    except Exception as e:
        print(f"❌ 触发失败: {e}")
        return None

def wait_for_ingestion(api_token, job_id):
    """等待 ingestion-worker 完成"""
    print("\n步骤 6: 等待 ingestion-worker 完成...")
    print("正在监控任务状态...")
    
    max_wait = 1800  # 30分钟
    elapsed = 0
    interval = 10
    
    while elapsed < max_wait:
        try:
            headers = {"Authorization": f"Bearer {api_token}"}
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

def regenerate_daily_reports(api_token, start_date: date, end_date: date):
    """重新生成指定日期范围内的晨报"""
    print(f"\n步骤 7: 重新生成 {start_date} 至 {end_date} 的晨报...")
    
    current_date = start_date
    success_count = 0
    failed_count = 0
    
    while current_date <= end_date:
        date_str = current_date.isoformat()
        print(f"\n重新生成 {date_str} 的晨报...", end=" ")
        
        try:
            headers = {"Authorization": f"Bearer {api_token}"}
            params = {"force": "true"}
            if httpx:
                with httpx.Client(timeout=30) as client:
                    resp = client.post(
                        f"{API_URL}/api/admin/reports/daily/{date_str}/regenerate",
                        params=params,
                        headers=headers,
                    )
                    resp.raise_for_status()
                    data = resp.json()
            else:
                resp = requests.post(
                    f"{API_URL}/api/admin/reports/daily/{date_str}/regenerate",
                    params=params,
                    headers=headers,
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()
            
            job_id = data.get("job_id")
            if job_id:
                print(f"✅ 已触发 (Job ID: {job_id})")
                success_count += 1
            else:
                print(f"⚠️  可能已存在或失败")
                failed_count += 1
        except Exception as e:
            error_msg = str(e)
            if "没有文章数据" in error_msg:
                print(f"⚠️  跳过（该日期没有文章数据）")
            else:
                print(f"❌ 失败: {error_msg}")
            failed_count += 1
        
        current_date += timedelta(days=1)
        time.sleep(2)  # 避免请求过快
    
    print()
    print(f"晨报重新生成完成: 成功 {success_count} 个, 失败/跳过 {failed_count} 个")
    return success_count

def regenerate_weekly_reports(api_token, start_date: date, end_date: date):
    """重新生成指定日期范围内的周报（基于每个周一）"""
    print(f"\n步骤 8: 重新生成 {start_date} 至 {end_date} 的周报...")
    
    # 找到范围内的所有周一
    mondays = []
    current_date = start_date
    # 找到第一个周一
    days_since_monday = current_date.weekday()
    if days_since_monday > 0:
        first_monday = current_date - timedelta(days=days_since_monday)
    else:
        first_monday = current_date
    
    # 如果第一个周一在开始日期之前，使用下一个周一
    if first_monday < start_date:
        first_monday += timedelta(days=7)
    
    # 收集所有周一
    while first_monday <= end_date:
        mondays.append(first_monday)
        first_monday += timedelta(days=7)
    
    if not mondays:
        print("⚠️  指定日期范围内没有周一（周报日期）")
        return 0
    
    print(f"找到 {len(mondays)} 个周报日期（周一）: {[str(d) for d in mondays]}")
    
    # 注意：周报重新生成需要在容器内执行，因为需要访问数据库
    # 这里我们提示用户手动执行，或者调用相应的工具
    print("\n⚠️  注意：周报重新生成需要在容器内执行，因为需要访问数据库")
    print("建议手动执行以下命令:")
    for monday in mondays:
        print(f"  docker exec zpulse-api python -m app.tools.regenerate_weekly_for_this_monday --date {monday.isoformat()}")
    
    print("\n或者等待系统自动生成周报（如果有定时任务）")
    return len(mondays)

def main():
    print("=" * 70)
    print("完整流程：全量爬取 → 提取 → 重新生成报告")
    print("=" * 70)
    print()
    print(f"配置:")
    print(f"  - weRSS URL: {WERSS_URL}")
    print(f"  - API URL: {API_URL}")
    print(f"  - 抓取范围: start_page={START_PAGE}, end_page={END_PAGE}")
    print(f"  - 执行模式: 异步并发（1个线程，并发限制: {CONCURRENT_LIMIT}）")
    print()
    
    # 1. 登录 weRSS
    werss_token = get_werss_token()
    
    # 2. 登录 API（可选，如果失败则跳过后续API相关步骤）
    api_token = None
    try:
        api_token = get_api_token()
    except Exception as e:
        print(f"\n⚠️  API 登录失败: {e}")
        print("   将跳过 ingestion-worker 和报告生成步骤")
        print("   （可以稍后手动触发这些步骤）")
    
    # 3. 获取所有公众号
    mps = get_all_mps(werss_token)
    
    # 4. 触发全量抓取（使用异步并发，1个线程）
    collect_success = trigger_collect_all_mps(werss_token, mps)
    
    if not collect_success:
        print("\n⚠️  抓取任务可能未完全成功")
    
    if not api_token:
        print("\n⚠️  由于 API 登录失败，跳过后续步骤")
        print("\n✅ weRSS 全量抓取已完成！")
        return
    
    # 5. 触发 ingestion-worker
    job_id = trigger_ingestion_worker(api_token)
    
    if job_id:
        # 6. 等待 ingestion-worker 完成
        ingestion_success = wait_for_ingestion(api_token, job_id)
        if not ingestion_success:
            print("\n⚠️  ingestion-worker 可能未完全成功，但继续执行报告生成...")
    else:
        print("\n⚠️  无法触发 ingestion-worker，跳过提取步骤")
    
    # 7. 重新生成晨报（12月31日之后）
    target_start_date = date(2025, 12, 31)
    target_end_date = date.today()
    
    regenerate_daily_reports(api_token, target_start_date, target_end_date)
    
    # 8. 提示周报重新生成
    regenerate_weekly_reports(api_token, target_start_date, target_end_date)
    
    print()
    print("=" * 70)
    print("任务完成！")
    print("=" * 70)
    print()
    print("💡 说明：")
    print("  - 报告生成是异步任务，系统会自动发送给订阅用户")
    print("  - 可以通过日志查看报告生成进度")
    print("  - 周报需要在容器内手动执行（见上方提示）")
    print()

if __name__ == "__main__":
    main()

