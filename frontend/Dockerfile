# 多阶段构建 - Next.js优化部署

# 阶段1: 依赖安装
FROM node:20-alpine AS deps
WORKDIR /app

# 兼容 SWC/一些原生依赖在 musl 环境的运行
RUN apk add --no-cache libc6-compat

# 复制依赖配置
COPY package.json package-lock.json* ./

# 安装依赖
RUN npm ci

# 阶段2: 构建应用
FROM node:20-alpine AS builder
WORKDIR /app

RUN apk add --no-cache libc6-compat

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
RUN npm run build && npm prune --production

# 阶段3: 生产运行
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production

# 安装健康检查依赖
RUN apk add --no-cache curl

# 创建非root用户
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# 复制public文件
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

# 复制构建产物（standalone模式）
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# 复制生产依赖
COPY --from=builder --chown=nextjs:nodejs /app/node_modules ./node_modules

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
