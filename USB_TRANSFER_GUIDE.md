# Z-Pulse USB 传输和部署指南

## 📦 备份文件清单

### 在开发机 (macOS) 上生成的文件

当前目录：`/Users/ethan/Codes/z-pulse`

```
zpulse_usb_backup/
├── zpulse_images.tar.gz.part.00  (1.0GB) - 镜像分卷 1
├── zpulse_images.tar.gz.part.01  (240MB) - 镜像分卷 2
├── zpulse_db.sql                 (44MB)  - PostgreSQL 数据库
├── werss.db                      (490MB) - we-mp-rss 数据库
├── docker-compose.yml            (11KB)  - Docker 配置
├── nginx.conf                    (5KB)   - Nginx 配置
└── .env                          (3KB)   - 环境配置

根目录：
├── zpulse_usb_backup_deploy.sh   - 部署脚本
```

**总大小**: 约 1.8GB

---

## 🔄 USB 传输流程

### 步骤 1：在 macOS 开发机上复制到 USB

```bash
cd /Users/ethan/Codes/z-pulse

# 插入 USB 磁盘（假设挂载在 /Volumes/USB）

# 复制所有文件到 USB
cp -r zpulse_usb_backup /Volumes/USB/
cp zpulse_usb_backup_deploy.sh /Volumes/USB/

# 验证文件完整性
ls -lh /Volumes/USB/zpulse_usb_backup/
ls -lh /Volumes/USB/zpulse_usb_backup_deploy.sh

# 应该看到：
# zpulse_images.tar.gz.part.00 (1.0GB)
# zpulse_images.tar.gz.part.01 (240MB)
# zpulse_db.sql (44MB)
# werss.db (490MB)
# docker-compose.yml (11KB)
# nginx.conf (5KB)
# .env (3KB)
# zpulse_usb_backup_deploy.sh (几KB)
```

### 步骤 2：在 Ubuntu 机器上准备上传

```bash
# 1. 插入 USB 磁盘到 Ubuntu 机器
# 2. 挂载 USB（假设挂载在 /mnt/usb）

sudo mount /dev/sdb1 /mnt/usb

# 3. 验证文件
ls -lh /mnt/usb/zpulse_usb_backup/
ls -lh /mnt/usb/zpulse_usb_backup_deploy.sh

# 4. 复制到 Ubuntu 机器（可选，但推荐）
cp -r /mnt/usb/zpulse_usb_backup ~/
cp /mnt/usb/zpulse_usb_backup_deploy.sh ~/
```

### 步骤 3：从 Ubuntu 上传到阿里云服务器

```bash
# 方式 A：使用 scp（推荐）

# 1. 上传镜像分卷（2个文件）
scp /mnt/usb/zpulse_usb_backup/zpulse_images.tar.gz.part.* root@47.97.115.235:/root/

# 2. 上传数据文件
scp /mnt/usb/zpulse_usb_backup/zpulse_db.sql root@47.97.115.235:/root/
scp /mnt/usb/zpulse_usb_backup/werss.db root@47.97.115.235:/root/

# 3. 上传配置文件
scp /mnt/usb/zpulse_usb_backup/docker-compose.yml root@47.97.115.235:/root/
scp /mnt/usb/zpulse_usb_backup/nginx.conf root@47.97.115.235:/root/
scp /mnt/usb/zpulse_usb_backup/.env root@47.97.115.235:/root/

# 4. 上传部署脚本
scp /mnt/usb/zpulse_usb_backup_deploy.sh root@47.97.115.235:/root/deploy.sh

# 方式 B：使用 rsync（更快，支持断点续传）

# 上传整个目录
rsync -avz --progress /mnt/usb/zpulse_usb_backup/ \
  root@47.97.115.235:/root/

rsync -avz --progress /mnt/usb/zpulse_usb_backup_deploy.sh \
  root@47.97.115.235:/root/deploy.sh
```

### 步骤 4：在阿里云服务器上部署

```bash
# 1. SSH 登录服务器
ssh root@47.97.115.235
# 输入密码: Wang@703711!

# 2. 检查文件完整性
cd /root
ls -lh

# 应该看到：
# zpulse_images.tar.gz.part.00 (1.0GB)
# zpulse_images.tar.gz.part.01 (240MB)
# zpulse_db.sql (44MB)
# werss.db (490MB)
# docker-compose.yml (11KB)
# nginx.conf (5KB)
# .env (3KB)
# deploy.sh

# 3. 重命名部署脚本（如果需要）
mv deploy.sh deploy-on-server.sh
chmod +x deploy-on-server.sh

# 4. 移动文件到正确位置
mkdir -p zpulse_deploy
mv zpulse_images.tar.gz.part.* zpulse_deploy/
mv zpulse_db.sql zpulse_deploy/
mv werss.db zpulse_deploy/
mv docker-compose.yml zpulse_deploy/
mv nginx.conf zpulse_deploy/
mv .env zpulse_deploy/
mv deploy-on-server.sh zpulse_deploy/

# 5. 进入部署目录
cd zpulse_deploy

# 6. 运行部署脚本
bash deploy-on-server.sh
```

---

## 🚀 部署脚本会自动完成

1. ✅ 检查 Docker 和 Docker Compose 环境
2. ✅ 停止现有服务（如果有）
3. ✅ 合并镜像分卷文件
4. ✅ 解压并加载所有 Docker 镜像
5. ✅ 导入 PostgreSQL 数据库
6. ✅ 恢复 we-mp-rss 数据库
7. ✅ 启动所有服务
8. ✅ 检查服务状态

---

## 🔍 部署后验证

### 1. 检查服务状态

```bash
cd /root/zpulse_deploy
docker-compose ps
```

所有服务应该是 `Up` 状态：
- zpulse-db
- zpulse-redis
- zpulse-api
- zpulse-web
- zpulse-proxy
- zpulse-rss
- zpulse-ingestion-worker
- zpulse-ai-worker

### 2. 访问服务

在浏览器中访问：

- **主应用**: http://47.97.115.235:8899
- **管理后台**: http://47.97.115.235:8899/admin
- **API 文档**: http://47.97.115.235:8899/docs
- **RSS 采集**: http://47.97.115.235:8080

### 3. 测试登录

**Z-Pulse 管理后台**
- URL: http://47.97.115.235:8899/admin/login
- 用户名: `admin`
- 密码: `admin@9988`

**we-mp-rss 管理界面**
- URL: http://47.97.115.235:8080
- 用户名: `admin`
- 密码: `admin@9988`

**⚠️ 重要：we-mp-rss 需要重新扫码登录微信**

---

## 📊 定时任务配置

部署完成后，以下定时任务会自动运行：

1. **晨报生成**: 每天 09:45
2. **周报生成**: 每周一 10:00
3. **RSS 采集**: 每 30 分钟

---

## 🛠️ 常用运维命令

```bash
cd /root/zpulse_deploy

# 查看所有服务状态
docker-compose ps

# 查看服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f ai-worker
docker-compose logs -f ingestion-worker

# 重启所有服务
docker-compose restart

# 重启单个服务
docker-compose restart ai-worker

# 停止所有服务
docker-compose down

# 启动所有服务
docker-compose up -d
```

---

## 🔧 故障排查

### 问题 1：上传速度慢

**解决方案**：
- 使用 rsync 而不是 scp（支持断点续传）
- 分批上传文件
- 在网络负载低时上传

### 问题 2：文件损坏

**解决方案**：
```bash
# 在服务器上验证文件
md5sum zpulse_images.tar.gz.part.00
md5sum zpulse_db.sql

# 对比 macOS 上的 md5 值
md5 zpulse_images.tar.gz.part.00
```

### 问题 3：容器无法启动

**解决方案**：
```bash
# 查看详细日志
docker-compose logs [service-name]

# 检查磁盘空间
df -h

# 检查内存
free -h
```

---

## 📝 文件传输检查清单

### 在 macOS 上
- [ ] 所有文件已复制到 USB
- [ ] USB 文件完整性验证通过
- [ ] USB 安全弹出

### 在 Ubuntu 上
- [ ] USB 成功挂载
- [ ] 所有文件可见且大小正确
- [ ] 上传到服务器成功

### 在服务器上
- [ ] 所有文件已接收
- [ ] 文件大小与源文件一致
- [ ] 部署脚本可执行
- [ ] 部署成功完成
- [ ] 所有服务正常运行

---

## 🎯 快速参考

### 文件大小参考
| 文件 | 大小 | 用途 |
|------|------|------|
| zpulse_images.tar.gz.part.00 | 1.0GB | Docker 镜像分卷 1 |
| zpulse_images.tar.gz.part.01 | 240MB | Docker 镜像分卷 2 |
| zpulse_db.sql | 44MB | PostgreSQL 数据库 |
| werss.db | 490MB | we-mp-rss 数据库 |
| docker-compose.yml | 11KB | Docker 配置 |
| nginx.conf | 5KB | Nginx 配置 |
| .env | 3KB | 环境配置 |

### 网络带宽参考
| 文件 | 大小 | 上传时间（10Mbps） | 上传时间（100Mbps） |
|------|------|-------------------|-------------------|
| 镜像分卷 00 | 1.0GB | 约 13分钟 | 约 1.3分钟 |
| 镜像分卷 01 | 240MB | 约 3分钟 | 约 20秒 |
| 数据文件 | 534MB | 约 7分钟 | 约 40秒 |
| 配置文件 | 几KB | <1秒 | <1秒 |

**总计上传时间**：
- 10Mbps: 约 25分钟
- 100Mbps: 约 2.5分钟

---

**部署完成后，请妥善保管 USB 备份！**
