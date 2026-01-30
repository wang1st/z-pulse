# 阿里云部署指南

## 部署前准备

### 1. SSH连接配置
确保可以SSH连接到阿里云服务器：
```bash
ssh root@47.97.115.235
```

如果需要密码，请准备好服务器密码。

### 2. 代码修改说明

本次更新包括以下修改：

#### 后端修改
1. **backend/app/routers/werss.py**
   - 修复WeRSS API路径：添加`/api/v1/wx`前缀
   - 修复响应码检查：从`code == 200`改为`code == 0`
   - 修复返回字段映射：qr_url正确映射到data.code

2. **backend/app/services/werss_monitor.py**
   - 修改邮件模板使用环境变量`WEB_URL`
   - 更新邮件链接为动态生成的relogin_url

#### 前端修改
3. **frontend/app/we-rss-qrcode-direct/page.tsx**
   - 新增直接显示二维码的页面
   - 使用动态hostname而不是硬编码localhost
   - 自动轮询检查扫码状态

## 部署方式选择

### 方式1：完整部署（推荐）
使用完整的镜像构建和部署流程：

```bash
# 1. 构建AMD64镜像
./build-amd64-images.sh

# 2. 部署到阿里云
./deploy-aliyun.sh
```

### 方式2：快速代码更新（适合小改动）
只更新代码文件，在服务器上重新构建：

```bash
# 1. 手动复制更新的文件到服务器
scp backend/app/routers/werss.py root@47.97.115.235:/root/z-pulse/backend/app/routers/
scp backend/app/services/werss_monitor.py root@47.97.115.235:/root/z-pulse/backend/app/services/
scp -r shared/* root@47.97.115.235:/root/z-pulse/shared/
scp -r frontend/app root@47.97.115.235:/root/z-pulse/frontend/

# 2. SSH登录到服务器
ssh root@47.97.115.235

# 3. 在服务器上执行
cd /root/z-pulse
docker-compose build frontend-web
docker-compose restart api-backend
docker-compose restart frontend-web
docker-compose restart reverse-proxy
```

## 验证部署

部署完成后，访问以下地址验证：

1. **主应用**: http://47.97.115.235:8899
2. **二维码页面**: http://47.97.115.235:8899/we-rss-qrcode-direct
3. **WeRSS后台**: http://47.97.115.235:8080

### API测试
在服务器上测试API：

```bash
# 测试二维码API
curl http://localhost:8000/api/werss/qrcode | jq .

# 测试状态查询API
curl http://localhost:8000/api/werss/qrcode/status | jq .
```

## 环境变量配置

确保`.env`文件包含正确的配置：

```bash
WEB_URL=http://47.97.115.235:8899
WERSS_BASE_URL=http://zpulse-rss:8001
```

## 故障排查

### 1. 页面显示"获取二维码失败"
检查前端控制台错误：
- 打开浏览器开发者工具 (F12)
- 查看Console标签页的错误信息
- 查看Network标签页的API请求状态

### 2. API返回500错误
检查后端日志：
```bash
docker logs zpulse-api --tail 50
```

### 3. 二维码无法加载
检查WeRSS服务：
```bash
docker logs zpulse-rss --tail 50
curl http://localhost:8080/api/v1/wx/sys/info -H "X-Secret: your-secret"
```

## 回滚方案

如果部署出现问题，快速回滚：

```bash
# SSH登录服务器
ssh root@47.97.115.235

# 回滚到之前版本（使用git）
cd /root/z-pulse
git checkout HEAD~1

# 重新构建并重启
docker-compose build frontend-web
docker-compose restart api-backend frontend-web
```

## 邮件测试

部署完成后，测试Token过期提醒邮件：

```bash
# 在服务器上手动运行监控脚本
cd /root/z-pulse/backend
python -m app.services.werss_monitor
```

或者查看最近收到的邮件，确认链接是否正确指向：
```
http://47.97.115.235:8899/we-rss-qrcode-direct
```

## 注意事项

1. **端口映射**：确保以下端口正常监听
   - 8899: nginx反向代理
   - 8080: WeRSS服务
   - 8000: API后端（内部）
   - 3000: 前端（内部）

2. **容器网络**：确保所有容器在同一个Docker网络中
   - api-backend需要能访问zpulse-rss:8001
   - reverse-proxy需要能访问frontend-web:3000

3. **日志监控**：部署后密切关注日志
   ```bash
   docker-compose logs -f --tail=100
   ```

## 完成检查清单

- [ ] 主页可以正常访问
- [ ] 二维码页面可以正常显示
- [ ] API返回正确的二维码URL
- [ ] 二维码图片可以正常加载
- [ ] 邮件链接指向正确的域名
- [ ] WeRSS服务正常运行
