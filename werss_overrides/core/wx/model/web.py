# Override for weRSS web.py to fix pagination issue
# This file fixes the issue where only the first page is crawled

import json
import time
import random
import requests
from datetime import datetime
from core.wx.base import WxGather
from core.print import print_info

class MpsWeb(WxGather):
    """Override MpsWeb class to fix pagination"""
    
    def get_Articles(self, faker_id: str = None, Mps_id: str = None, Mps_title: str = "", 
                     CallBack=None, start_page: int = 0, MaxPage: int = 1, interval: int = 10, 
                     Gather_Content: bool = False, Item_Over_CallBack=None, Over_CallBack=None):
        """重写 get_Articles 方法，修复分页问题"""
        super().Start(mp_id=Mps_id)
        if self.Gather_Content:
            Gather_Content = True
        print(f"Web浏览器模式,是否采集[{Mps_title}]内容：{Gather_Content}\n")
        
        # 请求参数
        url = "https://mp.weixin.qq.com/cgi-bin/appmsgpublish"
        count = 5
        params = {
            "sub": "list",
            "sub_action": "list_ex",
            "begin": start_page,
            "count": count,
            "fakeid": faker_id,
            "token": self.token,
            "lang": "zh_CN",
            "f": "json",
            "ajax": 1
        }
        
        session = self.session
        i = start_page
        
        print(f"开始爬取，起始页: {start_page}, 最大页: {MaxPage}\n")
        
        while True:
            if i >= MaxPage:
                print(f"已达到最大页数 {MaxPage}，停止爬取\n")
                break
            
            begin = i * count
            params["begin"] = str(begin)
            print(f"第{i+1}页开始爬取\n")
            
            # 随机暂停几秒，避免过快的请求导致过快的被查到
            time.sleep(random.randint(0, interval))
            
            try:
                headers = self.fix_header(url)
                resp = session.get(url, headers=headers, params=params, verify=False, timeout=30)
                
                msg = resp.json()
                self._cookies = resp.cookies
                
                # 流量控制了, 退出
                if msg['base_resp']['ret'] == 200013:
                    super().Error("frequencey control, stop at {}".format(str(begin)))
                    break
                
                if msg['base_resp']['ret'] == 200003:
                    super().Error("Invalid Session, stop at {}".format(str(begin)), code="Invalid Session")
                    break
                
                if msg['base_resp']['ret'] != 0:
                    super().Error("错误原因:{}:代码:{}".format(msg['base_resp']['err_msg'], msg['base_resp']['ret']), 
                                 code=msg['base_resp']['err_msg'])
                    break
                
                # 如果返回的内容中为空则结束
                if 'publish_page' not in msg:
                    super().Error("all ariticle parsed")
                    break
                
                if "publish_page" in msg:
                    msg["publish_page"] = json.loads(msg['publish_page'])
                    for item in msg["publish_page"]['publish_list']:
                        if "publish_info" in item:
                            publish_info = json.loads(item['publish_info'])
                            
                            if "appmsgex" in publish_info:
                                for item in publish_info["appmsgex"]:
                                    # 输出文章信息日志
                                    title = item.get('title', '未知标题')
                                    publish_date_str = "未知"
                                    
                                    # 尝试获取发布日期（item中可能有update_time或update_etime字段）
                                    if 'update_time' in item:
                                        try:
                                            # update_time 可能是时间戳（秒）或日期字符串
                                            update_time = item['update_time']
                                            if isinstance(update_time, (int, float)):
                                                publish_date = datetime.fromtimestamp(int(update_time))
                                                publish_date_str = publish_date.strftime("%Y-%m-%d %H:%M:%S")
                                            elif isinstance(update_time, str):
                                                publish_date_str = update_time
                                        except:
                                            publish_date_str = str(item.get('update_time', '未知'))
                                    elif 'update_etime' in item:
                                        try:
                                            update_etime = item['update_etime']
                                            if isinstance(update_etime, (int, float)):
                                                publish_date = datetime.fromtimestamp(int(update_etime))
                                                publish_date_str = publish_date.strftime("%Y-%m-%d %H:%M:%S")
                                            elif isinstance(update_etime, str):
                                                publish_date_str = update_etime
                                        except:
                                            publish_date_str = str(item.get('update_etime', '未知'))
                                    
                                    print_info(f"📰 文章信息 - 公众号: {Mps_title}, 标题: {title}, 发布日期: {publish_date_str}")
                                    
                                    if Gather_Content:
                                        if not super().HasGathered(item["aid"]):
                                            item["content"] = self.content_extract(item['link'])
                                            super().Wait(3, 10, tips=f"{item['title']} 采集完成")
                                    else:
                                        item["content"] = ""
                                    item["id"] = item["aid"]
                                    item["mp_id"] = Mps_id
                                    if CallBack is not None:
                                        super().FillBack(CallBack=CallBack, data=item, 
                                                        Ext_Data={"mp_title": Mps_title, "mp_id": Mps_id})
                    print(f"第{i+1}页爬取成功\n")
                    # 翻页 - 确保在成功处理后递增
                    i += 1
                else:
                    # 如果没有 publish_page，也递增并继续（可能是最后一页）
                    print(f"第{i+1}页无内容，继续下一页\n")
                    i += 1
                
            except requests.exceptions.Timeout:
                print(f"Request timed out at page {i+1}")
                # 超时后也递增，继续下一页
                i += 1
                # 如果连续超时多次，退出
                if i >= MaxPage:
                    break
            except requests.exceptions.RequestException as e:
                print(f"Request error at page {i+1}: {e}")
                # 请求错误后也递增，继续下一页
                i += 1
                # 如果连续错误多次，退出
                if i >= MaxPage:
                    break
            except Exception as e:
                print(f"Unexpected error at page {i+1}: {e}")
                # 其他错误后也递增，继续下一页
                i += 1
                if i >= MaxPage:
                    break
            finally:
                super().Item_Over(item={"mps_id": Mps_id, "mps_title": Mps_title}, 
                                 CallBack=Item_Over_CallBack)
        
        super().Over(CallBack=Over_CallBack)

