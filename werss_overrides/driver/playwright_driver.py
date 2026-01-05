from asyncio import futures
import os
import platform
import subprocess
import sys
import json
import random
import uuid
import asyncio
from socket import timeout as socket_timeout

# 设置环境变量
browsers_name = os.getenv("BROWSER_TYPE", "firefox")
browsers_path = os.getenv("PLAYWRIGHT_BROWSERS_PATH", "")
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = browsers_path

# 导入Playwright相关模块
from playwright.sync_api import sync_playwright
from playwright.async_api import async_playwright

class PlaywrightController:
    def __init__(self):
        self.system = platform.system().lower()
        self.driver = None
        self.browser = None
        self.context = None
        self.page = None
        self.isClose = True
        self._retry_count = 0  # 添加重试计数器，防止无限递归
    def _is_browser_installed(self, browser_name):
        """检查指定浏览器是否已安装"""
        try:
            
            # 遍历目录，查找包含浏览器名称的目录
            for item in os.listdir(browsers_path):
                item_path = os.path.join(browsers_path, item)
                if os.path.isdir(item_path) and browser_name.lower() in item.lower():
                    return True
            
            return False
        except (OSError, PermissionError):
            return False
    def is_async(self):
        try:
            # 尝试获取事件循环
                # 设置合适的事件循环策略
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return True
        except RuntimeError:
            # 如果没有正在运行的事件循环，则说明不是异步环境
            return False
    
    def is_browser_started(self):
        """检测浏览器是否已启动"""
        try:
            # 检查页面是否已关闭
            if self.page is not None and self.page.is_closed():
                return False
            return (not self.isClose and 
                    self.driver is not None and 
                    self.browser is not None and 
                    self.context is not None and 
                    self.page is not None)
        except Exception:
            # 如果检查过程中出现异常，认为浏览器未启动
            return False
    def start_browser(self, headless=True, mobile_mode=False, dis_image=True, browser_name=browsers_name, language="zh-CN", anti_crawler=True, _retry_count=0):
        """
        启动浏览器
        
        Args:
            _retry_count: 内部重试计数器，防止无限递归（最大重试2次）
        """
        # 限制最大重试次数，防止无限递归（增加到3次以提高成功率）
        MAX_RETRIES = 3
        if _retry_count >= MAX_RETRIES:
            self.cleanup()
            raise Exception(f"浏览器启动失败：达到最大重试次数（{MAX_RETRIES}次）")
        
        try:
            # 如果浏览器已经关闭，先清理资源（静默处理，忽略 greenlet 错误）
            try:
                if self.isClose and (self.driver is not None or self.browser is not None or self.context is not None):
                    self.cleanup()
            except Exception:
                # 忽略清理时的错误（包括 greenlet 错误），继续启动新浏览器
                pass
            if self.isClose and (self.driver is not None or self.browser is not None or self.context is not None):
                try:
                    self.cleanup()
                except:
                    pass
            
            # 使用线程锁确保线程安全
            if  str(os.getenv("NOT_HEADLESS",False))=="True":
                headless = False
            else:
                headless = True

            if self.system != "windows":
                headless = True
            if self.driver is None:
                if sys.platform == "win32" :
                    # 设置事件循环策略为WindowsSelectorEventLoopPolicy
                    # asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
                    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
                self.driver = sync_playwright().start()
        
            # 根据浏览器名称选择浏览器类型
            if browser_name.lower() == "firefox":
                browser_type = self.driver.firefox
            elif browser_name.lower() == "webkit":
                browser_type = self.driver.webkit
            else:
                browser_type = self.driver.chromium  # 默认使用chromium
            # 移除重复的日志信息
            # print(f"启动浏览器: {browser_name}, 无头模式: {headless}, 移动模式: {mobile_mode}, 反爬虫: {anti_crawler}")
            # 设置启动选项
            launch_options = {
                "headless": headless,
                # 优化内存使用：限制最大内存使用，避免 OOM
                "args": [
                    "--disable-dev-shm-usage",  # 使用 /tmp 而不是 /dev/shm，避免共享内存不足
                    "--disable-gpu",  # 禁用 GPU，减少资源使用
                    "--no-sandbox",  # 禁用沙盒模式（容器环境需要）
                    "--disable-setuid-sandbox",  # 禁用 setuid 沙盒
                    "--disable-web-security",  # 禁用 Web 安全（爬虫需要）
                    "--disable-features=IsolateOrigins,site-per-process",  # 禁用某些安全特性
                    "--disable-blink-features=AutomationControlled",  # 隐藏自动化特征
                    "--memory-pressure-off",  # 关闭内存压力检测
                ]
            }
            
            # 在Windows上添加额外的启动选项
            if self.system == "windows":
                launch_options["handle_sigint"] = False
                launch_options["handle_sigterm"] = False
                launch_options["handle_sighup"] = False
            
            self.browser = browser_type.launch(**launch_options)
            
            # 设置浏览器语言为中文
            context_options = {
                "locale": language
            }
            
            # 反爬虫配置
            if anti_crawler:
                context_options.update(self._get_anti_crawler_config(mobile_mode))
            
            self.context = self.browser.new_context(**context_options)
            self.page = self.context.new_page()
            
            if mobile_mode:
                self.page.set_viewport_size({"width": 375, "height": 812})
            # else:
            #     self.page.set_viewport_size({"width": 1920, "height": 1080})

            if dis_image:
                self.context.route("**/*.{png,jpg,jpeg}", lambda route: route.abort())

            # 应用反爬虫脚本
            if anti_crawler:
                self._apply_anti_crawler_scripts()

            self.isClose = False
            self._retry_count = 0  # 成功启动后重置计数器
            return self.page
        except Exception as e:
            error_msg = str(e)
            # 检查是否是 greenlet、事件循环或进程通信相关的错误
            greenlet_errors = (
                "Cannot switch to a different thread",
                "greenlet",
                "Event loop is closed",
                "Is Playwright already stopped",
                "EPIPE",
                "write EPIPE",
                "Broken pipe",
                "maximum recursion depth exceeded"  # 添加递归深度错误
            )
            
            is_greenlet_error = any(err in error_msg for err in greenlet_errors)
            
            if is_greenlet_error:
                # 静默处理 greenlet/事件循环错误，尝试重新启动浏览器
                try:
                    self.cleanup()
                except:
                    pass
                
                # 如果已达到最大重试次数，抛出异常而不是返回 None
                if _retry_count >= MAX_RETRIES:
                    self.cleanup()
                    raise Exception(f"浏览器启动失败：达到最大重试次数（{MAX_RETRIES}次），greenlet/事件循环错误: {error_msg}")
                
                # 等待一段时间后重试（逐渐增加延迟）
                import time
                sleep_time = 0.5 * (_retry_count + 1)  # 递增延迟：0.5s, 1s, 1.5s...
                time.sleep(sleep_time)
                
                # 递归重试启动浏览器（传递重试计数）
                try:
                    return self.start_browser(headless, mobile_mode, dis_image, browser_name, language, anti_crawler, _retry_count=_retry_count + 1)
                except RecursionError:
                    # 捕获递归错误，抛出异常
                    self.cleanup()
                    raise Exception(f"浏览器启动失败：递归深度超限，greenlet/事件循环错误: {error_msg}")
                except Exception as retry_error:
                    retry_error_msg = str(retry_error)
                    # 如果重试也失败，且仍然是 greenlet 错误，抛出异常
                    if any(err in retry_error_msg for err in greenlet_errors):
                        self.cleanup()
                        raise Exception(f"浏览器启动失败：重试后仍然失败，greenlet/事件循环错误: {retry_error_msg}")
                    # 其他错误才抛出
                    raise
            
            # 其他错误才打印详细信息（但 greenlet/事件循环错误已经在上面的 if 块中处理了）
            # 这里只处理真正的浏览器安装/配置错误
            if not is_greenlet_error:
                print(f"浏览器启动失败: {error_msg}")
                tips="Docker环境;您可以设置环境变量INSTALL=True并重启Docker自动安装浏览器环境;如需要切换浏览器可以设置环境变量BROWSER_TYPE=firefox 支持(firefox,webkit,chromium),开发环境请手工安装"
                print(tips)
                self.cleanup()
                raise Exception(tips)
            else:
                # greenlet/事件循环错误已经处理，但理论上不应该到这里（应该在 if is_greenlet_error 块中处理）
                self.cleanup()
                raise Exception(f"浏览器启动失败：greenlet/事件循环错误: {error_msg}")
        
    def string_to_json(self, json_string):
        try:
            json_obj = json.loads(json_string)
            return json_obj
        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {e}")
            return ""

    def parse_string_to_dict(self, kv_str: str):
        result = {}
        items = kv_str.strip().split(';')
        for item in items:
            try:
                key, value = item.strip().split('=')
                result[key.strip()] = value.strip()
            except Exception as e:
                pass
        return result

    def add_cookies(self, cookies):
        if self.context is None:
            raise Exception("浏览器未启动，请先调用 start_browser()")
        self.context.add_cookies(cookies)
    def get_cookies(self):
        if self.context is None:
            raise Exception("浏览器未启动，请先调用 start_browser()")
        return self.context.cookies()
    def add_cookie(self, cookie):
        self.add_cookies([cookie])


    def _get_anti_crawler_config(self, mobile_mode=False):
        """获取反爬虫配置"""
        
        # 生成随机指纹
        fingerprint = self._generate_uuid()
        
        # 基础配置
        config = {
            "user_agent": self._get_realistic_user_agent(mobile_mode),
            "viewport": {
                "width": random.randint(1200, 1920) if not mobile_mode else 375,
                "height": random.randint(800, 1080) if not mobile_mode else 812,
                "device_scale_factor": random.choice([1, 1.25, 1.5, 2])
            },
            "extra_http_headers": {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Cache-Control": "no-cache",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1"
            }
        }
        
        # 移动端特殊配置
        if mobile_mode:
            config["extra_http_headers"].update({
                "User-Agent": config["user_agent"],
                "X-Requested-With": "com.tencent.mm"
            })
        
        return config

    def _get_realistic_user_agent(self, mobile_mode=False):
        """获取更真实的User-Agent"""
        # 移除重复的日志信息
        # print(f"浏览器特征设置完成: {'移动端' if mobile_mode else '桌面端'}")
        if mobile_mode:
            # 移动端User-Agent
            mobile_agents = [
                "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
                "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36",
                "Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36",
                "Mozilla/5.0 (Windows Phone 10.0; Android 6.0.1; Microsoft; Lumia 950) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Mobile Safari/537.36 Edge/14.14393"
            ]
            return random.choice(mobile_agents)
        else:
            # 桌面端User-Agent（更新版本）
            desktop_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 OPR/106.0.0.0",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ]
            return random.choice(desktop_agents)

    def _generate_uuid(self):
        """生成UUID指纹"""
        return str(uuid.uuid4()).replace("-", "")

    def _apply_anti_crawler_scripts(self):
        # try:
        #     from playwright_stealth.stealth import Stealth
        #     stealth = Stealth()
        #     stealth.apply_stealth_sync(self.page)
        # except ImportError:
        #     print("检测到playwright_stealth未安装，正在自动安装...")
        #     subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright_stealth"])
        #     from playwright_stealth.stealth import Stealth
        #     stealth = Stealth()
        #     stealth.apply_stealth_sync(self.page)
        
        """应用反爬虫脚本"""
        # 隐藏自动化特征
        self.page.add_init_script("""
        // 隐藏webdriver属性
        Object.defineProperty(navigator, 'webdriver', {
            get: () => false,
        });
        
        // 隐藏chrome属性
        Object.defineProperty(window, 'chrome', {
            get: () => false,
        });
        
        // 修改plugins长度
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5],
        });
        
        // 修改languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['zh-CN', 'zh', 'en'],
        });
        
        // 隐藏自动化痕迹
        Object.defineProperty(navigator, 'webdriver', {
            get: () => false,
        });
        
        // 修改permissions
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
        """)
      
        # 设置更真实的浏览器行为
        try:
            # 安全地调用 evaluate
            evaluate_method = getattr(self.page, 'evaluate', None)
            if evaluate_method is not None:
                try:
                    evaluate_method("""
        // 随机延迟点击事件
        const originalAddEventListener = EventTarget.prototype.addEventListener;
        EventTarget.prototype.addEventListener = function(type, listener, options) {
            if (type === 'click') {
                const wrappedListener = function(...args) {
                    setTimeout(() => listener.apply(this, args), Math.random() * 100 + 50);
                };
                return originalAddEventListener.call(this, type, wrappedListener, options);
            }
            return originalAddEventListener.call(this, type, listener, options);
        };
        
        // 随机化鼠标移动
        document.addEventListener('mousemove', (e) => {
            if (Math.random() > 0.7) {
                e.stopImmediatePropagation();
            }
        }, true);
        """)
                except (TypeError, AttributeError) as e:
                    if "'module' object is not callable" not in str(e) and "not callable" not in str(e):
                        raise
                    # evaluate 不可调用，忽略错误继续执行
        except Exception as e:
            # 忽略 evaluate 相关的错误，不影响主要功能
            pass

       

   

    def __del__(self):
        # 避免在程序退出时调用Close()，防止"can't register atexit after shutdown"错误
        try:
            import atexit
            # 检查是否在atexit处理过程中
            if not atexit._exithandlers:
                self.Close()
        except:
            # 如果发生任何异常，直接跳过清理
            pass

    def open_url(self, url, wait_until="domcontentloaded", timeout=30000):
        """
        打开URL，带超时保护
        
        Args:
            url: 要打开的URL
            wait_until: 等待条件，默认 "domcontentloaded"
            timeout: 超时时间（毫秒），默认 30 秒
        """
        try:
            # 检查页面是否已关闭，如果关闭则重新启动浏览器
            if self.page is None or self.page.is_closed():
                # 页面已关闭，重新启动浏览器
                try:
                    self.cleanup()
                except:
                    pass
                # 重新启动浏览器（start_browser 现在会抛出异常而不是返回 None）
                self.start_browser()
                if self.page is None or self.page.is_closed():
                    raise Exception(f"无法重新启动浏览器，页面仍然关闭")
            
            # 设置超时时间，避免无限等待导致卡死
            self.page.goto(url, wait_until=wait_until, timeout=timeout)
        except Exception as e:
            error_msg = str(e)
            # 如果已经是我们自己的错误信息，直接抛出
            if "无法重新启动浏览器" in error_msg or "打开URL失败" in error_msg or "打开URL超时" in error_msg or "浏览器已关闭" in error_msg:
                raise
            # 如果是超时错误，提供更明确的提示
            if "timeout" in error_msg.lower() or "Timeout" in error_msg:
                raise Exception(f"打开URL超时（{timeout/1000}秒）: {url}")
            # 如果是页面关闭错误，尝试重新启动浏览器
            if "closed" in error_msg.lower() or "Target page, context or browser has been closed" in error_msg:
                # 尝试重新启动浏览器并重试一次
                try:
                    self.cleanup()
                    self.start_browser()  # start_browser 现在会抛出异常而不是返回 None
                    if self.page is None or self.page.is_closed():
                        raise Exception(f"浏览器启动失败，页面仍然关闭")
                    # 重试打开URL
                    self.page.goto(url, wait_until=wait_until, timeout=timeout)
                    return  # 成功，直接返回
                except Exception as retry_error:
                    retry_error_msg = str(retry_error)
                    # 如果已经是我们自己的错误信息，直接抛出
                    if "无法重新启动浏览器" in retry_error_msg or "浏览器启动失败" in retry_error_msg:
                        raise Exception(f"浏览器已关闭，重新启动后仍无法打开URL: {url}，错误: {retry_error_msg}")
                    raise Exception(f"浏览器已关闭，重新启动后仍无法打开URL: {url}，错误: {retry_error_msg}")
                raise Exception(f"浏览器已关闭，无法打开URL: {url}")
            raise Exception(f"打开URL失败: {url}，错误: {error_msg}")

    def Close(self):
        self.cleanup()

    def cleanup(self):
        """清理所有资源"""
        try:
            # 检查事件循环状态
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    # 事件循环已关闭，使用同步方式清理
                    pass
            except RuntimeError:
                # 没有事件循环，使用同步方式清理
                pass
            
            # 使用线程锁确保线程安全
            # 捕获 greenlet 和进程通信相关的错误关键词
            greenlet_errors = (
                "Cannot switch to a different thread",
                "greenlet.error",
                "Event loop is closed",
                "Is Playwright already stopped",
                "already stopped",
                "EPIPE",
                "write EPIPE",
                "Broken pipe"
            )
            
            if hasattr(self, 'page') and self.page:
                try:
                    # 检查页面是否已关闭
                    if not self.page.is_closed():
                        self.page.close()
                except Exception as e:
                    error_msg = str(e)
                    # 忽略 greenlet 和事件循环相关的错误
                    if not any(err in error_msg for err in greenlet_errors):
                        print(f"关闭页面失败: {str(e)}")
            
            if hasattr(self, 'context') and self.context:
                try:
                    # 检查上下文是否已关闭
                    if hasattr(self.context, 'pages') and len(self.context.pages) > 0:
                        self.context.close()
                except Exception as e:
                    error_msg = str(e)
                    # 忽略 greenlet 和事件循环相关的错误
                    if not any(err in error_msg for err in greenlet_errors):
                        print(f"关闭上下文失败: {str(e)}")
            
            if hasattr(self, 'browser') and self.browser:
                try:
                    # 检查浏览器是否已关闭
                    if hasattr(self.browser, 'contexts') and len(self.browser.contexts) > 0:
                        self.browser.close()
                except Exception as e:
                    error_msg = str(e)
                    # 忽略 greenlet 和事件循环相关的错误
                    if not any(err in error_msg for err in greenlet_errors):
                        print(f"关闭浏览器失败: {str(e)}")
            
            if hasattr(self, 'driver') and self.driver:
                try:
                    self.driver.stop()
                except Exception as e:
                    error_msg = str(e)
                    # 忽略 greenlet 和事件循环相关的错误
                    if not any(err in error_msg for err in greenlet_errors):
                        print(f"停止 Playwright 驱动失败: {str(e)}")
            
            self.isClose = True
        except Exception as e:
            error_msg = str(e)
            # 忽略 greenlet、事件循环和进程通信相关的错误
            greenlet_errors = (
                "Cannot switch to a different thread",
                "greenlet.error",
                "Event loop is closed",
                "already stopped",
                "EPIPE",
                "write EPIPE",
                "Broken pipe"
            )
            if not any(err in error_msg for err in greenlet_errors):
                print(f"资源清理失败: {error_msg}")

    def dict_to_json(self, data_dict):
        try:
            return json.dumps(data_dict, ensure_ascii=False, indent=2)
        except (TypeError, ValueError) as e:
            print(f"字典转JSON失败: {e}")
            return ""

ControlDriver=PlaywrightController()
# 示例用法
if __name__ == "__main__":
    controller = PlaywrightController()
    try:
        controller.start_browser()
        controller.open_url("https://mp.weixin.qq.com/")
    finally:
        # controller.Close()
        pass