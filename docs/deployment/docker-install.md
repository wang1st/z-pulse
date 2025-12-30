# Docker安装指南

## macOS

### 问题
`docker-compose: command not found` 或 `docker: command not found`

### ✅ 解决方案：安装Docker Desktop

#### 方法1: 使用Homebrew安装（推荐）

```bash
# 1. 安装Homebrew（如果还没有）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. 安装Docker Desktop
brew install --cask docker

# 3. 启动Docker Desktop
open -a Docker

# 4. 等待Docker Desktop完全启动（约30秒）
# 看到菜单栏有Docker图标，且图标不再动画时表示已启动

# 5. 验证安装
docker --version
docker compose version
```

#### 方法2: 直接下载安装（如果不用Homebrew）

1. **访问Docker官网**
   - 打开：https://www.docker.com/products/docker-desktop/
   - 点击 "Download for Mac"

2. **选择版本**
   - **Apple Silicon (M1/M2/M3/M4)**: 下载 `Docker.dmg` (Apple Silicon)
   - **Intel Mac**: 下载 `Docker.dmg` (Intel)

3. **安装**
   - 双击下载的 `.dmg` 文件
   - 将Docker图标拖到Applications文件夹
   - 在Applications中打开Docker
   - 按照提示完成安装

4. **启动Docker Desktop**
   - 在Applications中找到Docker并打开
   - 首次启动需要输入管理员密码
   - 等待Docker完全启动（菜单栏出现Docker图标）

5. **验证安装**
   ```bash
   docker --version
   docker compose version
   ```

## Linux (Ubuntu/Debian)

```bash
# 安装 Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# 启动 Docker
systemctl start docker
systemctl enable docker

# 安装 Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# 验证安装
docker --version
docker-compose --version
```

## Linux (CentOS/RHEL)

```bash
# 安装 Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# 启动 Docker
systemctl start docker
systemctl enable docker

# 安装 Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# 验证安装
docker --version
docker-compose --version
```

## Windows

1. **下载Docker Desktop**
   - 访问：https://www.docker.com/products/docker-desktop/
   - 点击 "Download for Windows"

2. **安装**
   - 运行下载的安装程序
   - 按照提示完成安装
   - 重启计算机（如果需要）

3. **启动Docker Desktop**
   - 从开始菜单启动Docker Desktop
   - 等待Docker完全启动

4. **验证安装**
   ```powershell
   docker --version
   docker compose version
   ```

## 验证安装

安装完成后，运行以下命令验证：

```bash
docker --version
docker compose version
docker ps
```

如果所有命令都能正常执行，说明Docker安装成功。

## 常见问题

### Q: Docker Desktop启动失败？

A: 
1. 检查系统要求（macOS需要10.15+，Windows需要Windows 10/11）
2. 检查虚拟化是否启用（Windows需要在BIOS中启用虚拟化）
3. 重启计算机后重试

### Q: 权限问题？

A: 
- macOS/Windows: 确保Docker Desktop正在运行
- Linux: 将用户添加到docker组：
  ```bash
  sudo usermod -aG docker $USER
  # 重新登录后生效
  ```

## 相关文档

- [服务重启指南](./restart.md)
- [阿里云部署指南](./aliyun.md)

