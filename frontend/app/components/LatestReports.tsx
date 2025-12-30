'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { formatDistanceToNow } from 'date-fns'
import { zhCN } from 'date-fns/locale'
import Icon, { Icons } from '@/components/Icon'
import { formatBeijingYmd, parseApiDateTimeToDate } from '@/lib/datetime'

interface Report {
  id: number
  report_type: string
  report_date: string
  title: string
  summary_markdown: string
  content_json?: any
  article_count: number
  created_at: string
}

export function LatestReports() {
  const [reports, setReports] = useState<Report[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchLatestReports()
  }, [])

  const fetchLatestReports = async () => {
    try {
      const response = await fetch('/api/reports/?limit=6')
      const data = await response.json()
      setReports(data)
    } catch (error) {
      console.error('Failed to fetch reports:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <div className="text-center py-8">加载中...</div>
  }

  if (reports.length === 0) {
    return <div className="text-center py-8 text-gray-500">暂无报告</div>
  }

  const stripHtml = (s: string) =>
    String(s || '')
      .replace(/<[^>]*>/g, ' ')
      .replace(/\s+/g, ' ')
      .trim()

  // 从Markdown提取H1标题
  const extractH1FromMarkdown = (markdown: string): string | null => {
    if (!markdown) return null
    // 如果是HTML格式（旧格式），尝试提取其中的Markdown
    if (markdown.trim().startsWith('<')) {
      // 使用 [\s\S] 代替 . 来匹配包括换行符在内的所有字符（兼容 ES2017）
      const match = markdown.match(/<pre><code[^>]*class="language-markdown"[^>]*>([\s\S]*?)<\/code><\/pre>/)
      if (match) {
        markdown = match[1]
        // Unescape HTML entities
        markdown = markdown.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&')
      } else {
        return null
      }
    }
    // 提取第一个H1标题
    const h1Match = markdown.match(/^#\s+(.+)$/m)
    return h1Match ? h1Match[1].trim() : null
  }

  // 从Markdown提取前几段文字作为摘要
  const extractSummaryFromMarkdown = (markdown: string, maxLength: number = 160): string => {
    if (!markdown) return ''
    // 如果是HTML格式，先提取Markdown
    if (markdown.trim().startsWith('<')) {
      // 使用 [\s\S] 代替 . 来匹配包括换行符在内的所有字符（兼容 ES2017）
      const match = markdown.match(/<pre><code[^>]*class="language-markdown"[^>]*>([\s\S]*?)<\/code><\/pre>/)
      if (match) {
        markdown = match[1]
        markdown = markdown.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&')
      } else {
        return stripHtml(markdown).substring(0, maxLength)
      }
    }
    // 移除标题和代码块
    let text = markdown
      .replace(/^#+\s+.+$/gm, '') // 移除所有标题
      .replace(/```[\s\S]*?```/g, '') // 移除代码块
      .replace(/`[^`]+`/g, '') // 移除行内代码
      .replace(/\*\*([^*]+)\*\*/g, '$1') // 移除粗体标记
      .replace(/\*([^*]+)\*/g, '$1') // 移除斜体标记
      .replace(/\[([^\]]+)\]\([^\)]+\)/g, '$1') // 移除链接，保留文本
      .replace(/\n+/g, ' ') // 换行变空格
      .trim()
    return text.substring(0, maxLength)
  }

  const formatReportDate = (iso: string) => formatBeijingYmd(iso)

  return (
    <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
      {reports.map((report) => (
        (() => {
          const isDaily = report.report_type === 'daily' || report.report_type === 'DAILY'
          const header = report?.content_json?.header || {}
          
          // 对于周报，从Markdown提取标题；对于日报，使用content_json
          let focusTitle: string
          if (!isDaily && report.summary_markdown) {
            const h1Title = extractH1FromMarkdown(report.summary_markdown)
            focusTitle = h1Title || report.title
          } else {
            focusTitle =
              (typeof header?.title === 'string' && header.title.trim()) ||
              (typeof report?.content_json?.focus_topic === 'string' && report.content_json.focus_topic.trim()) ||
              report.title
          }
          
          // 提取摘要
          let focusLede: string
          if (!isDaily && report.summary_markdown) {
            focusLede = extractSummaryFromMarkdown(report.summary_markdown)
          } else {
            focusLede =
              (typeof header?.lede === 'string' && header.lede.trim()) ||
              stripHtml(report.summary_markdown || '')
          }

          return (
        <Link
          key={report.id}
          href={`/reports/${report.id}`}
          className="block bg-white rounded-lg shadow-md hover:shadow-xl transition-shadow p-6"
        >
          <div className="flex items-center mb-3">
            <span className={`px-3 py-1 rounded-full text-sm font-medium ${
              report.report_type === 'daily'
                ? 'bg-blue-100 text-blue-800'
                : 'bg-purple-100 text-purple-800'
            }`}>
              {report.report_type === 'daily' ? `晨报｜${formatReportDate(report.report_date)}` : `周报｜${formatReportDate(report.report_date)}`}
            </span>
            <span className="ml-auto text-sm text-gray-500">
              {formatDistanceToNow(parseApiDateTimeToDate(report.created_at) || new Date(report.created_at), {
                addSuffix: true,
                locale: zhCN
              })}
            </span>
          </div>
          
          <div className="text-xs font-medium text-gray-500 mb-1">
            {report.report_type === 'daily' ? '今日焦点' : '本期摘要'}
          </div>

          <h3 className="text-lg font-semibold text-gray-900 mb-2 line-clamp-2">
            {focusTitle}
          </h3>
          
          <p className="text-gray-600 text-sm line-clamp-3 mb-4">
            {focusLede && focusLede.length > 0 ? (focusLede.length > 160 ? `${focusLede.substring(0, 160)}...` : focusLede) : '点击查看详情'}
          </p>
          
          <div className="flex items-center text-sm text-gray-500">
            <span className="inline-flex items-center gap-2">
              <Icon name={Icons.fileText} size={16} className="text-gray-500" />
              {report.article_count} 篇文章
            </span>
          </div>
        </Link>
          )
        })()
      ))}
    </div>
  )
}

