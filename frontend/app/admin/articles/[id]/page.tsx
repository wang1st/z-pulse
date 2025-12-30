'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import api from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import Icon, { Icons } from '@/components/Icon'
import { useToast } from '@/components/ui/toast'

interface ArticleDetail {
  id: number
  account_id: number
  account_name?: string
  title: string
  content: string | null
  article_url: string
  published_at: string
  collected_at: string
  status: string
}

export default function AdminArticleDetailPage() {
  const params = useParams()
  const router = useRouter()
  const { toast } = useToast()

  const formatBeijing = (value: string) => {
    if (!value) return ''
    const dt = new Date(value)
    if (isNaN(dt.getTime())) return value
    const s = new Intl.DateTimeFormat('zh-CN', {
      timeZone: 'Asia/Shanghai',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    }).format(dt)
    return s.replaceAll('/', '-')
  }
  const id = params?.id as string

  const [loading, setLoading] = useState(true)
  const [article, setArticle] = useState<ArticleDetail | null>(null)

  useEffect(() => {
    const run = async () => {
      try {
        setLoading(true)
        const resp = await api.get(`/admin/articles/${id}`, { timeout: 20000 })
        setArticle(resp.data)
      } catch (e) {
        console.error(e)
        toast({ title: '加载失败', description: '获取文章详情失败', variant: 'error' })
      } finally {
        setLoading(false)
      }
    }
    if (id) run()
  }, [id])

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
          <p className="mt-4 text-muted-foreground">加载中...</p>
        </div>
      </div>
    )
  }

  if (!article) {
    return (
      <div className="space-y-4">
        <Button variant="outline" onClick={() => router.back()}>
          返回
        </Button>
        <div className="text-sm text-muted-foreground">文章不存在或加载失败</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-3">
        <Button variant="outline" onClick={() => router.back()}>
          <Icon name={Icons.arrowLeft} size={16} className="mr-2" />
          返回列表
        </Button>
        <Button asChild className="bg-white text-green-600 hover:bg-green-50">
          <a href={article.article_url} target="_blank" rel="noreferrer">
            打开原文
          </a>
        </Button>
      </div>

      <Card className="shadow-xl border-0 backdrop-blur-sm" style={{ background: 'rgba(255, 255, 255, 0.7)' }}>
        <CardHeader className="bg-gradient-to-r from-green-50 to-emerald-50 rounded-t-lg">
          <CardTitle className="flex items-center gap-2">
            <Icon name={Icons.fileText} size={20} className="text-green-600" />
            {article.title}
          </CardTitle>
          <CardDescription>
            {article.account_name ? `来源：${article.account_name}` : `账号 ${article.account_id}`}；发布时间：
            {article.published_at ? ` ${formatBeijing(article.published_at)}` : '（未知）'}
          </CardDescription>
        </CardHeader>
        <CardContent className="pt-6">
          <div className="text-sm text-muted-foreground mb-4">
            采集时间：{article.collected_at ? formatBeijing(article.collected_at) : '（未知）'}
          </div>

          <div className="rounded-lg border border-green-200 bg-white/70 p-4">
            <div className="text-sm text-gray-900 whitespace-pre-wrap leading-7">
              {article.content || '（无正文内容）'}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}


