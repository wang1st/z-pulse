/** @type {import('next').NextConfig} */
const nextConfig = {
  // 关键配置：启用standalone输出，用于Docker部署优化
  output: 'standalone',
  
  // API重写：将 /api/* 请求转发到后端API
  async rewrites() {
    // 在Docker环境中，使用服务名；在本地开发时，使用localhost
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://api-backend:8000';
    
    // 确保URL格式正确
    if (apiUrl && (apiUrl.startsWith('http://') || apiUrl.startsWith('https://'))) {
      return [
        {
          source: '/api/:path*',
          destination: `${apiUrl}/api/:path*`,
        },
      ];
    }
    // 如果没有有效的API URL，使用默认的Docker服务名
    return [
      {
        source: '/api/:path*',
        destination: 'http://api-backend:8000/api/:path*',
      },
    ];
  },
  
  // 环境变量
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://api-backend:8000',
  },
  
  // 图片优化
  images: {
    domains: ['localhost', 'api-backend'],
  },
}

module.exports = nextConfig

