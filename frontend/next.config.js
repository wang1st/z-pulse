/** @type {import('next').NextConfig} */
const nextConfig = {
  // 禁用SWC压缩，改用Terser，避免下载swc二进制文件失败
  swcMinify: false,
  output: 'standalone',
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'mmbiz.qpic.cn',
      },
      {
        protocol: 'http',
        hostname: 'mmbiz.qpic.cn',
      }
    ],
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://api-backend:8000'}/:path*`,
      },
    ]
  },
}

module.exports = nextConfig

