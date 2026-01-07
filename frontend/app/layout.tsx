import type { Metadata } from 'next'
import './globals.css'
import { ToastProvider } from '@/components/ui/toast'
import { ConfirmProvider } from '@/components/ui/confirm'

export const metadata: Metadata = {
  title: '浙财脉动｜浙江财政信息聚合平台',
  description: '浙财脉动：基于规则化处理+大模型的浙江财政信息聚合平台，致力于信息平权，帮助所有人了解浙江财政资金用途，支持学习与监督。',
  keywords: '浙财脉动,浙江财政,财政信息,信息平权,财政公开,财政监督,Smart Brevity,财政晨报,AI分析,政府政策',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="zh-CN">
      <body className="font-sans">
        <ToastProvider>
          <ConfirmProvider>{children}</ConfirmProvider>
        </ToastProvider>
      </body>
    </html>
  )
}

