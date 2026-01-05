import uvicorn
from core.config import cfg
from core.print import print_warning
import threading
from driver.auth import *
import os
if __name__ == '__main__':
    print("环境变量:")
    for k,v in os.environ.items():
        print(f"{k}={v}")
    if cfg.args.init=="True":
        import init_sys as init
        init.init()
    if  cfg.args.job =="True" and cfg.get("server.enable_job",False):
        from jobs import start_all_task
        threading.Thread(target=start_all_task,daemon=False).start()
    else:
        print_warning("未开启定时任务")
    print("启动服务器")
    AutoReload=cfg.get("server.auto_reload",False)
    thread=cfg.get("server.threads",1)
    # 强制单 worker 模式，避免 Playwright greenlet 线程切换错误
    # Playwright 不支持多线程，必须使用单进程单线程
    workers=1 if thread > 0 else 1
    print(f"启动配置: workers={workers}, threads={thread} (Playwright 需要单进程模式)")
    uvicorn.run("web:app", host="0.0.0.0", port=int(cfg.get("port",8001)),
            reload=AutoReload,
            reload_dirs=['core','web_ui'],
            reload_excludes=['static','web_ui','data'], 
            workers=workers,  # 强制单 worker，避免 greenlet 错误
            )
    pass