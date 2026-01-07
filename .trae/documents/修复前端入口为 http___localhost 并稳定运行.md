## 目标
- 通过 Nginx 反向代理让前端稳定地在 `http://localhost` 打开，而不是 `:3000`
- 消除 502/504 错误与 SWC 二进制问题，避免容器反复重启

## 当前问题归因
- 前端容器使用开发模式（`npm run dev`），Next.js 在容器中需要 SWC 二进制，ARM64 + Alpine/容器网络下易报错、返回空响应导致 502。
- Compose 挂载了 `./frontend:/app`，覆盖镜像内的构建产物与依赖；`node_modules/.bin/next` 不可用，出现 `next: not found`。
- Nginx 正常工作，但上游 `frontend-web:3000` 不稳定或不响应时会产生 502/504。

## 方案选型
- 采用“生产模式 + standalone 构建”的稳定方案：先在镜像中构建，再在运行时直接 `node server.js` 提供服务，Nginx 代理到该服务。
- 保留开发模式的可选方案（若后续需要 HMR），但默认使用生产模式避免 SWC/依赖覆盖问题。

## 技术实现
### 1) Dockerfile（frontend）
- 基础镜像改为 `node:20-slim`（glibc），避免 Alpine + musl 带来的 SWC 兼容问题。
- `deps` 阶段：
  - `npm ci` 安装依赖，设置国内镜像加速（`registry.npmmirror.com`）。
  - 显式安装 `@next/swc-linux-arm64-gnu` 以保证 ARM64 构建时 SWC 可用。
- `builder` 阶段：
  - 复制源代码并运行 `npm run build`，使用 Next.js `output: 'standalone'` 产物。
- `runner` 阶段：
  - 仅复制 `.next/standalone` 和 `.next/static`；使用非 root 用户启动。
  - `CMD ["node", "server.js"]` 在 3000 端口提供生产服务。

### 2) docker-compose.yml
- `frontend-web`：
  - 使用镜像启动生产服务：`command: node server.js`。
  - 移除 `./frontend:/app` 的挂载，避免覆盖镜像内的构建产物与依赖（保持镜像“不可变”）。
  - 环境变量保留 `NEXT_PUBLIC_API_URL=http://api-backend:8000`（容器内网络）。
  - 保留 `ports: 127.0.0.1:3000:3000` 便于本机直接调试；Nginx 仍通过容器网络访问。
  - 健康检查：`curl -f http://localhost:3000/`。

### 3) Nginx（nginx/nginx.conf）
- 已配置上游 `frontend_web` 与 API；保持 WebSocket/超时增强：
  - `proxy_read_timeout/proxy_connect_timeout/proxy_send_timeout` 设置为 300s（避免首次编译或冷启动 504）。
- 无需额外改动，代理 `/` 到 `frontend_web:3000`。

## 验证步骤
1. 构建前端镜像：`docker compose build frontend-web`。
2. 以生产模式启动：`docker compose up -d frontend-web`。
3. 观察前端日志：`docker logs -f zpulse-web`，确认 `node server.js` 启动成功并监听 `0.0.0.0:3000`。
4. 代理连通性：
   - 在代理容器内 `curl http://frontend-web:3000` 返回 200。
   - 在宿主机 `curl http://localhost` 返回 200。
5. 打开浏览器访问 `http://localhost`，确认首页、日报与周报页面均正常。

## 可选：保留开发模式服务
- 如需 HMR：
  - 使用单独的 `frontend-dev` 服务，`command: sh -c "npm ci && next dev -H 0.0.0.0"`。
  - 增加匿名卷 `- /app/node_modules` 以免挂载覆盖依赖。
  - Nginx 针对 dev 服务保持现有 WebSocket 与超时配置。

## 风险与回滚
- 风险：移除挂载后，容器内代码不随本地改动自动更新（生产模式本就如此）。
- 回滚：保留一个 `frontend-dev` 服务用于开发需要；生产继续使用稳定的 `frontend-web`。

请确认以上方案。确认后我将按上述步骤修改 Dockerfile 与 Compose，重建并验证，确保 `http://localhost` 正常访问。