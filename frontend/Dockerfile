# 多阶段构建 - Next.js优化部署

# 阶段1: 依赖安装
FROM node:20-slim AS deps
WORKDIR /app

# 复制依赖配置
COPY package.json package-lock.json* ./

# 安装依赖
RUN npm config set registry https://registry.npmmirror.com
RUN npm install

# 阶段2: 构建应用
FROM node:20-slim AS builder
WORKDIR /app

# 构建参数
ARG NEXT_PUBLIC_API_URL=http://api-backend:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=production

# 复制依赖
COPY --from=deps /app/node_modules ./node_modules

# 复制源代码
COPY . .

# 构建Next.js应用（启用standalone输出）
# 移除禁用SWC的环境变量，因为我们现在支持它了
RUN npm run build && npm prune --production

# 阶段3: 生产运行
FROM node:20-slim AS runner
WORKDIR /app

ENV NODE_ENV=production

# 安装健康检查依赖
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# 创建非root用户
RUN groupadd -g 1001 nodejs
RUN useradd -u 1001 -g nodejs -s /bin/sh -m nextjs

# 复制public文件
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

# 复制构建产物（standalone模式）
# standalone目录的内容应该直接复制到/app
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# standalone模式下，server.js在根目录
CMD ["node", "server.js"]
