# UI样式问题排查指南

## 问题现象
页面样式没有更新，显示的还是旧版本。

## 可能的原因和解决方案

### 1. 浏览器缓存问题（最常见）

**解决方法：**

#### 方法A：硬刷新
- **Mac**: `Cmd + Shift + R` 或 `Cmd + Option + R`
- **Windows/Linux**: `Ctrl + Shift + R` 或 `Ctrl + F5`

#### 方法B：清除浏览器缓存
1. 打开开发者工具 (F12)
2. 右键点击刷新按钮
3. 选择"清空缓存并硬性重新加载"

#### 方法C：使用无痕模式
- 打开浏览器的无痕/隐私模式
- 访问 `http://localhost/admin/login`

### 2. Next.js 构建缓存问题

**解决方法：**

```bash
# 停止前端容器
docker compose stop frontend-web

# 删除容器和镜像
docker compose rm -f frontend-web
docker rmi zpulse-frontend:latest

# 清理Next.js缓存（在本地）
cd frontend
rm -rf .next
rm -rf node_modules/.cache

# 重新构建
cd ..
docker compose build --no-cache frontend-web
docker compose up -d frontend-web
```

### 3. 检查CSS是否正确加载

**在浏览器中检查：**

1. 打开开发者工具 (F12)
2. 进入 **Network** 标签
3. 刷新页面
4. 查找 `.css` 文件
5. 确认状态码为 `200`（不是 `304` 或 `404`）

### 4. 检查图标字体加载

**问题：** 图标显示为方块或乱码

**解决方法：**

```bash
# 重新构建前端（包含图标字体）
docker compose build --no-cache frontend-web
docker compose up -d frontend-web
```

### 5. 强制刷新前端

**使用项目提供的脚本：**

```bash
# 方法1：使用脚本
./scripts/force-refresh-frontend.sh

# 方法2：手动执行
docker compose exec frontend-web rm -rf /app/.next
docker compose restart frontend-web
```

## 常见问题

### Q: 修改了CSS但页面没有变化？

A: 
1. 检查浏览器缓存（硬刷新）
2. 检查Next.js构建缓存（重新构建）
3. 检查CSS文件是否正确加载（开发者工具）

### Q: 图标显示不正常？

A: 
1. 检查图标字体文件是否正确加载
2. 重新构建前端容器
3. 清除浏览器缓存

### Q: 页面布局错乱？

A: 
1. 检查Tailwind CSS是否正确编译
2. 检查浏览器控制台是否有错误
3. 检查CSS文件是否正确加载

## 相关文档

- [部署指南](../deployment/README.md)
- [开发指南](../development.md)

