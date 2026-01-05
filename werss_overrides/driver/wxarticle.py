import random
from socket import timeout as socket_timeout
from .playwright_driver import PlaywrightController
from typing import Dict
from core.print import print_error,print_info,print_success,print_warning
import time
import core.wait as Wait
import base64
import re
from bs4 import BeautifulSoup
import os
from datetime import datetime
from core.config import cfg

class WXArticleFetcher:
    """微信公众号文章获取器
    
    基于WX_API登录状态获取文章内容
    
    Attributes:
        wait_timeout: 显式等待超时时间(秒)
    """
    
    def __init__(self, wait_timeout: int = 10000):
        """初始化文章获取器"""
        self.wait_timeout = wait_timeout
        self.controller = PlaywrightController()
        if not self.controller:
            raise Exception("WebDriver未初始化或未登录")
    
    def convert_publish_time_to_timestamp(self, publish_time_str: str) -> int:
        """将发布时间字符串转换为时间戳
        
        Args:
            publish_time_str: 发布时间字符串，如 "2024-01-01" 或 "2024-01-01 12:30"
            
        Returns:
            时间戳（秒）
        """
        try:
            # 尝试解析不同的时间格式
            formats = [
                "%Y-%m-%d %H:%M:%S",  # 2024-01-01 12:30:45
                "%Y年%m月%d日 %H:%M",        # 2024年03月24日 17:14
                "%Y-%m-%d %H:%M",     # 2024-01-01 12:30
                "%Y-%m-%d",           # 2024-01-01
                "%Y年%m月%d日",        # 2024年01月01日
                "%m月%d日",            # 01月01日 (当年)
            ]
            
            for fmt in formats:
                try:
                    if fmt == "%m月%d日":
                        # 对于只有月日的格式，智能判断年份
                        current_date = datetime.now()
                        current_year = current_date.year
                        full_time_str = f"{current_year}年{publish_time_str}"
                        dt = datetime.strptime(full_time_str, "%Y年%m月%d日")
                        
                        # 如果解析出的日期在未来，使用上一年
                        if dt > current_date:
                            dt = dt.replace(year=current_year - 1)
                    else:
                        dt = datetime.strptime(publish_time_str, fmt)
                    return int(dt.timestamp())
                except ValueError:
                    continue
            
            # 如果所有格式都失败，返回当前时间戳
            print_warning(f"无法解析时间格式: {publish_time_str}，使用当前时间")
            return int(datetime.now().timestamp())
            
        except Exception as e:
            print_error(f"时间转换失败: {e}")
            return int(datetime.now().timestamp())
       
        
    def extract_biz_from_source(self, url: str, page=None) -> str:
        """从URL或页面源码中提取biz参数
        
        Args:
            url: 文章URL
            page: Playwright Page实例，可选
            
        Returns:
            biz参数值
        """
        # 尝试从URL中提取
        match = re.search(r'[?&]__biz=([^&]+)', url)
        if match:
            return match.group(1)
            
        # 从页面源码中提取（需要page参数）
        if page is None:
            if not hasattr(self, 'page') or self.page is None:
                return ""
            page = self.page
            
        try:
            # 检查页面是否已关闭
            if page.is_closed():
                return ""
            
            # 从页面源码中查找biz信息
            try:
                page_source = page.content()
            except Exception as e:
                error_msg = str(e)
                if "Event loop is closed" in error_msg or "Is Playwright already stopped" in error_msg:
                    return ""
                raise
            
            print_info(f'开始解析Biz')
            biz_match = re.search(r'var biz = "([^"]+)"', page_source)
            if biz_match:
                return biz_match.group(1)
                
            # 尝试其他可能的biz存储位置
            biz_match = re.search(r'window\.__biz=([^&]+)', page_source)
            if biz_match:
                return biz_match.group(1)
            
            # 尝试使用 evaluate 获取 window.biz（添加错误处理）
            try:
                evaluate_method = getattr(page, 'evaluate', None)
                if evaluate_method is not None and callable(evaluate_method):
                    biz = evaluate_method('() => window.biz || null')
                    if biz:
                        return biz
            except Exception as e:
                error_msg = str(e)
                if "Event loop is closed" in error_msg or "Is Playwright already stopped" in error_msg:
                    return ""
                # 其他错误继续
            
            return ""
            
        except Exception as e:
            error_msg = str(e)
            if "Event loop is closed" in error_msg or "Is Playwright already stopped" in error_msg:
                # 事件循环关闭，静默处理
                return ""
            else:
                print_error(f"从页面源码中提取biz参数失败: {e}")
                return ""
    def extract_id_from_url(self, url: str) -> str:
        """从微信文章URL中提取ID
        
        Args:
            url: 文章URL
            
        Returns:
            文章ID字符串，如果提取失败返回None
        """
        try:
            # 从URL中提取ID部分
            match = re.search(r'/s/([A-Za-z0-9_-]+)', url)
            if not match:
                return ""
                
            id_str = match.group(1)
            
            # 添加必要的填充
            padding = 4 - len(id_str) % 4
            if padding != 4:
                id_str += '=' * padding
                
            # 尝试解码base64
            try:
                id_number = base64.b64decode(id_str).decode("utf-8")
                return id_number
            except Exception as e:
                # 如果base64解码失败，返回原始ID字符串
                return id_str
                
        except Exception as e:
            print_error(f"提取文章ID失败: {e}")
            return ""  
    def FixArticle(self, urls: list = [], mp_id: str = "") -> bool:
        """批量修复文章内容
        
        Args:
            urls: 文章URL列表，默认为示例URL
            mp_id: 公众号ID，可选
            
        Returns:
            操作是否成功
        """
        try:
            from jobs.article import UpdateArticle
            
            # 设置默认URL列表
            if urls is []:
                urls = ["https://mp.weixin.qq.com/s/YTHUfxzWCjSRnfElEkL2Xg"]
                
            success_count = 0
            total_count = len(urls)
            
            for i, url in enumerate(urls, 1):
                if url=="":
                    continue
                print_info(f"正在处理第 {i}/{total_count} 篇文章: {url}")
                
                try:
                    article_data = self.get_article_content(url)
                    
                    # 构建文章数据
                    article = {
                        "id": article_data.get('id'), 
                        "title": article_data.get('title'),
                        "mp_id": article_data.get('mp_id') if mp_id is None else mp_id, 
                        "publish_time": article_data.get('publish_time'),
                        "pic_url": article_data.get('pic_url'),
                        "content": article_data.get('content'),
                        "url": url,
                    }
                    
                    # 删除content字段避免重复存储
                    content_backup = article_data.get('content', '')
                    del article_data['content']
                    
                    print_success(f"获取成功: {article_data}")
                    
                    # 更新文章
                    ok = UpdateArticle(article, check_exist=True)
                    if ok:
                        success_count += 1
                        print_info(f"已更新文章: {article_data.get('title', '未知标题')}")
                    else:
                        print_warning(f"更新失败: {article_data.get('title', '未知标题')}")
                        
                    # 恢复content字段
                    article_data['content'] = content_backup
                    
                    # 避免请求过快，但只在非最后一个请求时等待
                    Wait(1,2,tips=f"处理第 {i}/{total_count} 篇文章")
                        
                except Exception as e:
                    print_error(f"处理文章失败 {url}: {e}")
                    continue
                    
            print_success(f"批量处理完成: 成功 {success_count}/{total_count}")
            return success_count > 0
            
        except Exception as e:
            print_error(f"批量修复文章失败: {e}")
            return False
        finally:
            self.Close() 
    async def async_get_article_content(self,url:str)->Dict:
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        loop = asyncio.get_running_loop()
        with ThreadPoolExecutor() as pool:
            future = loop.run_in_executor(pool, self.get_article_content, url)
        return await future
    def get_article_content(self, url: str) -> Dict:
        """获取单篇文章详细内容
        
        Args:
            url: 文章URL (如: https://mp.weixin.qq.com/s/qfe2F6Dcw-uPXW_XW7UAIg)
            
        Returns:
            文章内容数据字典，包含:
            - title: 文章标题
            - author: 作者
            - publish_time: 发布时间
            - content: 正文HTML
            - images: 图片URL列表
            
        Raises:
            Exception: 如果未登录或获取内容失败
        """
        info={
                "id": self.extract_id_from_url(url),
                "title": "",
                "publish_time": "",
                "content": "",
                "images": "",
                "mp_info":{
                "mp_name":"",   
                "logo":"",
                "biz": "",
                }
            }
        # 确保浏览器已启动
        if self.controller.page is None or (hasattr(self.controller, 'page') and self.controller.page is not None and self.controller.page.is_closed()):
            # 页面不存在或已关闭，重新启动浏览器
            self.controller.start_browser()
        
        self.page = self.controller.page
        # 将 wait_timeout（秒）转换为毫秒，并设置合理的超时时间
        timeout_ms = min(self.wait_timeout * 1000, 60000)  # 最多60秒
        print_warning(f"Get:{url} Wait:{self.wait_timeout}s (timeout: {timeout_ms}ms)")
        try:
            self.controller.open_url(url, timeout=timeout_ms)
            # 更新 page 引用，因为 open_url 可能会重新启动浏览器
            self.page = self.controller.page
        except Exception as e:
            # 如果打开URL失败，尝试重新启动浏览器并重试一次
            error_msg = str(e)
            # 避免嵌套错误信息：如果已经是格式化的错误信息，直接抛出
            if "打开URL失败" in error_msg or "打开URL超时" in error_msg or "浏览器已关闭" in error_msg:
                raise
            if "页面已关闭" in error_msg or "closed" in error_msg.lower() or "无法重新启动浏览器" in error_msg:
                print_warning(f"页面已关闭，尝试重新启动浏览器: {url}")
                try:
                    self.controller.cleanup()
                    self.controller.start_browser()
                    self.page = self.controller.page
                    # 重试打开URL
                    self.controller.open_url(url, timeout=timeout_ms)
                    self.page = self.controller.page
                except Exception as retry_error:
                    retry_error_msg = str(retry_error)
                    # 避免嵌套错误信息：如果已经是格式化的错误信息，直接抛出
                    if "打开URL失败" in retry_error_msg or "打开URL超时" in retry_error_msg or "浏览器已关闭" in retry_error_msg:
                        raise
                    print_error(f"重新启动浏览器后仍无法打开URL: {url}，错误: {retry_error_msg}")
                    try:
                        self.controller.cleanup()
                    except:
                        pass
                    raise Exception(f"打开URL失败: {url}，错误: {retry_error_msg}")
            else:
                # 其他错误，清理资源并重新抛出异常
                print_error(f"打开URL失败: {url}，错误: {error_msg}")
                try:
                    self.controller.cleanup()
                except:
                    pass
                raise Exception(f"打开URL失败: {url}，错误: {error_msg}")
        page = self.page
        content=""
        
        try:
            # 检查页面是否已关闭
            if page.is_closed():
                raise Exception("页面已关闭，无法获取内容")
            
            # 等待页面加载完成，设置超时避免卡死
            try:
                page.wait_for_load_state("domcontentloaded", timeout=10000)  # 10秒超时
            except Exception as e:
                print_warning(f"等待页面加载超时，继续尝试获取内容: {str(e)}")
            
            # 获取页面内容，设置超时
            try:
                # Playwright 的 text_content() 方法不支持 timeout 参数，需要先等待元素
                body_element = page.locator("body")
                body_element.wait_for(state="attached", timeout=5000)  # 等待元素附加
                body = body_element.text_content().strip()  # text_content() 不支持 timeout 参数
            except Exception as e:
                # 如果 locator 超时，尝试使用 evaluate
                print_warning(f"使用 locator 获取内容失败，尝试使用 evaluate: {str(e)}")
                try:
                    # 检查页面是否已关闭
                    if page.is_closed():
                        raise Exception("页面已关闭，无法使用 evaluate")
                    # 检查 page 对象本身是否有效
                    if page is None:
                        raise Exception("page 对象为 None")
                    # 安全地获取 evaluate 方法
                    try:
                        evaluate_method = getattr(page, 'evaluate', None)
                    except AttributeError as ae:
                        raise Exception(f"无法获取 page.evaluate 属性: {str(ae)}")
                    if evaluate_method is None:
                        raise Exception("page.evaluate 方法不存在")
                    # 检查 evaluate_method 的类型，确保它不是模块
                    import types
                    if isinstance(evaluate_method, types.ModuleType):
                        raise Exception("page.evaluate 是模块对象，不是方法（事件循环可能已关闭）")
                    # 额外检查：确保 evaluate_method 是可调用的
                    if not callable(evaluate_method):
                        raise Exception(f"page.evaluate 不是可调用对象，类型: {type(evaluate_method)}")
                    # 尝试调用 evaluate
                    try:
                        body = evaluate_method("() => document.body.innerText")
                    except TypeError as te:
                        # 如果是 'module' object is not callable 错误
                        error_msg = str(te)
                        if "'module' object is not callable" in error_msg or "not callable" in error_msg:
                            # 这不应该发生，因为我们已经检查了类型
                            raise Exception(f"page.evaluate 调用失败（类型检查未捕获）: {error_msg}")
                        raise
                    if body:
                        body = body.strip()
                    else:
                        body = ""
                except Exception as e2:
                    # 捕获所有异常，包括 TypeError 和 AttributeError
                    error_msg = str(e2)
                    # 检查是否是 'module' object is not callable 错误
                    if "'module' object is not callable" in error_msg or "not callable" in error_msg:
                        # 这是一个已知问题，可能是事件循环关闭导致的
                        # 静默处理，不打印错误信息，直接返回空内容
                        try:
                            self.controller.cleanup()
                        except:
                            pass
                        body = ""
                    else:
                        # 其他错误才打印详细信息
                        import traceback
                        error_trace = traceback.format_exc()
                        print_warning(f"evaluate 调用异常详情: {error_msg}")
                        print_warning(f"错误堆栈: {error_trace}")
                        raise Exception(f"无法获取页面内容: {error_msg}")
            
            info["content"]=body
            if "当前环境异常，完成验证后即可继续访问" in body:
                info["content"]=""
                # try:
                #     page.locator("#js_verify").click()
                # except:
                self.controller.cleanup()
                Wait(tips="当前环境异常，完成验证后即可继续访问")
                raise Exception("当前环境异常，完成验证后即可继续访问")
            if "该内容已被发布者删除" in body or "The content has been deleted by the author." in body:
                info["content"]="DELETED"
                raise Exception("该内容已被发布者删除")
            if  "内容审核中" in body:
                info['content']="DELETED"
                raise Exception("内容审核中")
            if "该内容暂时无法查看" in body:
                info["content"]="DELETED"
                raise Exception("该内容暂时无法查看")
            if "违规无法查看" in body:
                info["content"]="DELETED"
                raise Exception("违规无法查看")
            if "发送失败无法查看" in body:
                info["content"]="DELETED"
                raise Exception("发送失败无法查看")
            if "Unable to view this content because it violates regulation" in body:     
                info["content"]="DELETED"
                raise Exception("违规无法查看")
            

            # 检查页面是否已关闭
            if page.is_closed():
                raise Exception("页面已关闭，无法获取元数据")
            
            # 获取标题（添加超时保护）
            try:
                title_locator = page.locator('meta[property="og:title"]')
                title_locator.wait_for(state="attached", timeout=5000)  # 5秒超时
                title = title_locator.get_attribute("content", timeout=5000)  # 5秒超时
            except Exception as e:
                error_msg = str(e)
                if "Timeout" in error_msg or "timeout" in error_msg:
                    # 超时错误静默处理
                    title = None
                else:
                    print_warning(f"获取标题失败: {str(e)}")
                    title = None
            
            #获取作者（添加超时保护）
            try:
                author_locator = page.locator('meta[property="og:article:author"]')
                author_locator.wait_for(state="attached", timeout=5000)  # 5秒超时
                author = author_locator.get_attribute("content", timeout=5000)  # 5秒超时
            except Exception as e:
                error_msg = str(e)
                if "Timeout" in error_msg or "timeout" in error_msg:
                    author = None
                else:
                    print_warning(f"获取作者失败: {str(e)}")
                    author = None
            
            #获取描述（添加超时保护）
            try:
                desc_locator = page.locator('meta[property="og:description"]')
                desc_locator.wait_for(state="attached", timeout=5000)  # 5秒超时
                description = desc_locator.get_attribute("content", timeout=5000)  # 5秒超时
            except Exception as e:
                error_msg = str(e)
                if "Timeout" in error_msg or "timeout" in error_msg:
                    description = None
                else:
                    print_warning(f"获取描述失败: {str(e)}")
                    description = None
            
            #获取题图（添加超时保护）
            try:
                image_locator = page.locator('meta[property="twitter:image"]')
                image_locator.wait_for(state="attached", timeout=5000)  # 5秒超时
                topic_image = image_locator.get_attribute("content", timeout=5000)  # 5秒超时
            except Exception as e:
                error_msg = str(e)
                if "Timeout" in error_msg or "timeout" in error_msg:
                    topic_image = None
                else:
                    print_warning(f"获取题图失败: {str(e)}")
                    topic_image = None

            self.export_to_pdf(f"./data/{title}.pdf")
            if title=="":
                try:
                    # 检查页面是否已关闭
                    if page.is_closed():
                        title = ""
                    else:
                        # 安全地调用 evaluate
                        evaluate_method = getattr(page, 'evaluate', None)
                        if evaluate_method is not None:
                            try:
                                title = evaluate_method('() => document.title')
                            except (TypeError, AttributeError) as e:
                                if "'module' object is not callable" in str(e) or "not callable" in str(e):
                                    print_warning(f"page.evaluate 不可调用: {str(e)}")
                                    title = ""
                                else:
                                    raise
                        else:
                            title = ""
                except Exception as e:
                    print_warning(f"使用 evaluate 获取标题失败: {str(e)}")
                    title = ""
            
          
         
            # 获取正文内容和图片（添加超时保护）
            content = ""
            try:
                content_element = page.locator("#js_content")
                content_element.wait_for(state="attached", timeout=10000)  # 10秒超时
                content = content_element.inner_html(timeout=10000)  # 10秒超时
            except Exception as e:
                error_msg = str(e)
                if "Timeout" in error_msg or "timeout" in error_msg:
                    # 超时，尝试使用 #js_article
                    try:
                        content_element = page.locator("#js_article")
                        content_element.wait_for(state="attached", timeout=5000)
                        content = content_element.inner_html(timeout=5000)
                    except:
                        content = ""
                else:
                    print_warning(f"获取正文内容失败: {str(e)}")
                    content = ""
            
            #获取图集内容 
            if content=="":
                try:
                    content_element = page.locator("#js_article")
                    content_element.wait_for(state="attached", timeout=5000)
                    content = content_element.inner_html(timeout=5000)
                except Exception as e:
                    error_msg = str(e)
                    if "Timeout" in error_msg or "timeout" in error_msg:
                        content = ""
                    else:
                        print_warning(f"获取图集内容失败: {str(e)}")
                        content = ""

            content=self.clean_article_content(str(content))
            #获取图像资源
            images = [
                img.get_attribute("data-src") or img.get_attribute("src")
                for img in content_element.locator("img").all()
                if img.get_attribute("data-src") or img.get_attribute("src")
            ]
            images=[]
            if images and len(images)>0:
                info["pic_url"]=images[0]


            try:
                # 检查页面是否已关闭
                if page.is_closed():
                    raise Exception("页面已关闭，无法获取发布时间")
                #获取发布时间（添加超时保护）
                publish_time_locator = page.locator("#publish_time")
                publish_time_locator.wait_for(state="attached", timeout=5000)  # 5秒超时
                publish_time_str = publish_time_locator.text_content(timeout=5000).strip()  # 5秒超时
                # 将发布时间转换为时间戳
                publish_time = self.convert_publish_time_to_timestamp(publish_time_str)
            except Exception as e:
                error_msg = str(e)
                if "Timeout" in error_msg or "timeout" in error_msg or "Event loop is closed" in error_msg:
                    # 超时或事件循环关闭，静默处理
                    publish_time = ""
                else:
                    print_warning(f"获取发布时间失败: {str(e)}")
                    publish_time = ""
            info["title"]=title
            info["publish_time"]=publish_time
            info["content"]=content
            info["images"]=images
            info["author"]=author
            info["description"]=description
            info["topic_image"]=topic_image
            
            # 输出文章信息到日志
            if title:
                # 格式化发布日期
                publish_date_str = ""
                if publish_time:
                    try:
                        # publish_time 是时间戳（秒），转换为日期字符串
                        publish_date = datetime.fromtimestamp(int(publish_time))
                        publish_date_str = publish_date.strftime("%Y-%m-%d %H:%M:%S")
                    except:
                        publish_date_str = str(publish_time) if publish_time else "未知"
                else:
                    publish_date_str = "未知"
                
                print_info(f"📰 文章信息 - 标题: {title}, 发布日期: {publish_date_str}")

        except Exception as e:
            error_msg = str(e)
            # 如果是 'module' object is not callable 错误，静默处理
            if "'module' object is not callable" in error_msg or "not callable" in error_msg:
                # 静默处理，不打印错误信息
                pass
            else:
                # 其他错误才打印
                print_error(f"文章内容获取失败: {error_msg}")
                print_warning(f"页面内容预览: {body[:50] if 'body' in locals() else 'N/A'}...")
            # 记录详细错误信息但继续执行

        try:
            if info["content"]!="DELETED":
                # 等待关键元素加载
                # 使用更精确的选择器避免匹配多个元素
                ele_logo = page.locator('#js_like_profile_bar .wx_follow_avatar img')
                # 获取<img>标签的src属性（添加超时保护）
                try:
                    ele_logo.wait_for(state="attached", timeout=5000)  # 5秒超时
                    logo_src = ele_logo.get_attribute('src', timeout=5000)  # 5秒超时
                except Exception as e:
                    error_msg = str(e)
                    if "Timeout" in error_msg or "timeout" in error_msg or "Event loop is closed" in error_msg or "Is Playwright already stopped" in error_msg:
                        # 超时或事件循环关闭，静默处理
                        logo_src = None
                    else:
                        print_warning(f"获取logo失败: {str(e)}")
                        logo_src = None

                # 获取公众号名称
                try:
                    # 检查页面是否已关闭
                    if page.is_closed():
                        title = None
                        biz = None
                    else:
                        # 安全地调用 evaluate（使用原生 JavaScript，不依赖 jQuery）
                        evaluate_method = getattr(page, 'evaluate', None)
                        if evaluate_method is not None:
                            try:
                                # 使用原生 JavaScript 而不是 jQuery
                                title = evaluate_method('() => { const el = document.querySelector("#js_wx_follow_nickname"); return el ? el.textContent : null; }')
                                biz = evaluate_method('() => window.biz || null')
                            except (TypeError, AttributeError) as e:
                                if "'module' object is not callable" in str(e) or "not callable" in str(e):
                                    print_warning(f"page.evaluate 不可调用: {str(e)}")
                                    title = None
                                    biz = None
                                else:
                                    raise
                            except Exception as e:
                                error_msg = str(e)
                                if "ReferenceError" in error_msg or "$ is not defined" in error_msg or "Event loop is closed" in error_msg or "Is Playwright already stopped" in error_msg:
                                    # jQuery 未定义或事件循环关闭，静默处理
                                    title = None
                                    biz = None
                                else:
                                    raise
                        else:
                            title = None
                            biz = None
                except Exception as e:
                    error_msg = str(e)
                    if "Event loop is closed" in error_msg or "Is Playwright already stopped" in error_msg or "ReferenceError" in error_msg:
                        # 事件循环关闭或引用错误，静默处理
                        title = None
                        biz = None
                    else:
                        print_warning(f"获取公众号信息失败: {str(e)}")
                        title = None
                        biz = None
                info["mp_info"]={
                    "mp_name":title,
                    "logo":logo_src,
                    "biz": biz or self.extract_biz_from_source(url, page), 
                }
                info["mp_id"]= "MP_WXS_"+base64.b64decode(info["mp_info"]["biz"]).decode("utf-8")
        except Exception as e:
            print_error(f"获取公众号信息失败: {str(e)}")   
            pass
        
        # 在返回前输出文章信息（如果标题存在）
        if info.get("title"):
            title = info.get("title", "未知标题")
            publish_time = info.get("publish_time", "")
            
            # 获取公众号信息
            mp_name = "未知公众号"
            if "mp_info" in info and info["mp_info"]:
                mp_name = info["mp_info"].get("mp_name", "未知公众号")
            elif "mp_id" in info and info["mp_id"]:
                # 如果只有 mp_id，尝试从 mp_id 中提取信息
                mp_id = info["mp_id"]
                mp_name = f"公众号({mp_id})"
            
            # 格式化发布日期
            publish_date_str = ""
            if publish_time:
                try:
                    # publish_time 是时间戳（秒），转换为日期字符串
                    publish_date = datetime.fromtimestamp(int(publish_time))
                    publish_date_str = publish_date.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    publish_date_str = str(publish_time) if publish_time else "未知"
            else:
                publish_date_str = "未知"
            
            print_info(f"📰 文章信息 - 公众号: {mp_name}, 标题: {title}, 发布日期: {publish_date_str}")
        
        self.Close()
        return info
    def Close(self):
        """关闭浏览器"""
        if hasattr(self, 'controller'):
            self.controller.Close()
        else:
            print("WXArticleFetcher未初始化或已销毁")
    def __del__(self):
        """销毁文章获取器"""
        try:
            if hasattr(self, 'controller') and self.controller is not None:
                self.controller.Close()
        except Exception as e:
            # 析构函数中避免抛出异常
            pass

    def export_to_pdf(self, title=None):
        """将文章内容导出为 PDF 文件
        
        Args:
            output_path: 输出 PDF 文件的路径（可选）
        """
        output_path=""
        try:
            if cfg.get("export.pdf.enable",False)==False:
                return
            # 使用浏览器打印功能生成 PDF
            if output_path:
                import os
                pdf_path=cfg.get("export.pdf.dir","./data/pdf")
                output_path=os.path.abspath(f"{pdf_path}/{title}.pdf")
            print_success(f"PDF 文件已生成{output_path}")
        except Exception as e:
            print_error(f"生成 PDF 失败: {str(e)}")
    
    def fix_images(self,content:str)->str:
        try:
            soup = BeautifulSoup(content, 'html.parser')
            # 找到内容
            js_content_div = soup
            # 移除style属性中的visibility: hidden;
            if js_content_div is None:
                return ""
            js_content_div.attrs.pop('style', None)
            # 找到所有的img标签
            img_tags = js_content_div.find_all('img')
            # 遍历每个img标签并修改属性，设置宽度为1080p
            for img_tag in img_tags:
                if 'data-src' in img_tag.attrs:
                    img_tag['src'] = img_tag['data-src']
                    del img_tag['data-src']
                if 'style' in img_tag.attrs:
                    style = img_tag['style']
                    # 使用正则表达式替换width属性
                    style = re.sub(r'width\s*:\s*\d+\s*px', 'width: 1080px', style)
                    img_tag['style'] = style
            return  js_content_div.prettify()
        except Exception as e:
            print_error(f"修复图片失败: {str(e)}")
        return content
    def get_image_url(self,url:str)->str:
        base_url=cfg.get("server.base_url","")
        return f"{base_url}/static/res/logo/{url}" 
    def get_description(self,content:str,length:int=200)->str:
        soup = BeautifulSoup(content, 'html.parser')
            # 找到内容
        js_content_div = soup
        if js_content_div is None:
            return ""
        content = js_content_div.get_text().strip().strip("\n").replace("\n"," ").replace("\r"," ")
        return content[:length]+"..." if len(content)>length else content

    def proxy_images(self,content:str)->str:
        try:
            soup = BeautifulSoup(content, 'html.parser')
            # 找到内容
            js_content_div = soup
            # 移除style属性中的visibility: hidden;
            if js_content_div is None:
                return ""
            js_content_div.attrs.pop('style', None)
            # 找到所有的img标签
            img_tags = js_content_div.find_all('img')
            # 遍历每个img标签并修改属性，设置宽度为1080p
            for img_tag in img_tags:
                if 'src' in img_tag.attrs:
                    img_tag['src'] = self.get_image_url(img_tag['src'])
                if 'style' in img_tag.attrs:
                    style = img_tag['style']
                    # 使用正则表达式替换width属性
                    style = re.sub(r'width\s*:\s*\d+\s*px', 'width: 100%', style)
                    img_tag['style'] = style
            return  js_content_div.prettify()
        except Exception as e:
            print_error(f"Proxy图片失败: {str(e)}")
        return content
   
    def clean_article_content(self,html_content: str):
        from tools.html import htmltools
        html_content=self.fix_images(html_content)
        if not cfg.get("gather.clean_html",False):
            return html_content
        return htmltools.clean_html(str(html_content).strip(),
                                 remove_selectors=[
                                     "link",
                                     "head",
                                     "script"
                                 ],
                                 remove_attributes=[
                                     {"name":"style","value":"display: none;"},
                                     {"name":"style","value":"display:none;"},
                                     {"name":"aria-hidden","value":"true"},
                                 ],
                                 remove_normal_tag=True
                                 )
   


Web=WXArticleFetcher()