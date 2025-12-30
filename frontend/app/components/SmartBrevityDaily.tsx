'use client'

import { useState } from 'react'
import Icon, { Icons } from '@/components/Icon'
import { formatBeijingDate, formatBeijingDateTimeFromApi, parseYmdAsShanghaiDate } from '@/lib/datetime'
type Source = { id: number; account?: string; title?: string; url?: string; date?: string }

export function SmartBrevityDaily(props: {
  reportTypeLabel?: '晨报' | '周报'
  reportDate: string
  createdAt: string
  articleCount: number
  contentJson: any
}) {
  const { reportTypeLabel = '晨报', reportDate, createdAt, articleCount, contentJson } = props

  const header = contentJson?.header || {}
  const headline = String(header?.title || '')
  const lede = String(header?.lede || '')
  const why = String(contentJson?.why_it_matters || '')
  const big = String(contentJson?.big_picture || '')
  // Prefer recent hotspots (近日热点); fallback to legacy recent_hotwords/keywords
  const recentHotspots = Array.isArray(contentJson?.recent_hotspots) ? contentJson.recent_hotspots : []
  const hotspotsMeta =
    contentJson?.recent_hotspots_meta && typeof contentJson.recent_hotspots_meta === 'object' ? contentJson.recent_hotspots_meta : null
  const legacyHotwords = Array.isArray(contentJson?.recent_hotwords) ? contentJson.recent_hotwords : []
  const keywords =
    recentHotspots.length > 0 ? recentHotspots : (legacyHotwords.length > 0 ? legacyHotwords : (Array.isArray(contentJson?.keywords) ? contentJson.keywords : []))
  const sources = Array.isArray(contentJson?.sources) ? contentJson.sources : []
  const easterEgg = contentJson?.easter_egg && typeof contentJson.easter_egg === 'object' ? contentJson.easter_egg : null
  const visualFocus = String(contentJson?.visual_focus || '')
  const focusStyle = String(contentJson?.focus_style || '')
  const ledeCits: number[] = Array.isArray(header?.lede_citations) ? header.lede_citations : []
  const whyCits: number[] = Array.isArray(contentJson?.why_citations) ? contentJson.why_citations : []
  const bigCits: number[] = Array.isArray(contentJson?.big_picture_citations) ? contentJson.big_picture_citations : []

  const sourcesById: Record<number, Source> = {}
  for (const s of sources) {
    if (!s || typeof s !== 'object') continue
    const id = Number(s.id)
    if (!id) continue
    sourcesById[id] = s
  }

  const focusLabel =
    visualFocus === 'common_issue' ? '普遍性问题' : visualFocus === 'high_impact_event' ? '高影响力事件' : (visualFocus || '视觉焦点')

  const focusStyleLabel =
    focusStyle === 'data_snapshot' ? '硬事实快照' :
      focusStyle === 'action_chain' ? '动作链' :
        focusStyle === 'what_changed' ? '变化对比' :
          focusStyle === 'timeline' ? '时间轴' :
            focusStyle === 'qna_gaps' ? '问答+缺口' : ''

  const stripMarkers = (t: string) =>
    String(t || '')
      .replace(/【\s*(为何重要|为什么重要|大局)\s*】/g, '')
      .replace(/^\s*(为何重要|为什么重要|大局)\s*[:：]\s*/g, '')
      .replace(/\s+/g, ' ')
      .trim()

  const focusText = [lede, why, big].filter(Boolean).map(stripMarkers).filter(Boolean).join(' ')
  const focusMore = [why, big].filter(Boolean).map(stripMarkers).filter(Boolean).join(' ')

  const focusSourceIds = Array.from(
    new Set(
      [...ledeCits, ...whyCits, ...bigCits]
        .map((n: any) => Number(n))
        .filter((n: number) => Number.isFinite(n) && n > 0)
    )
  )

  const hotspotWindowDays = (() => {
    try {
      const wd = Number(hotspotsMeta?.window_days || 0)
      return Number.isFinite(wd) && wd > 0 ? wd : 0
    } catch {
      return 0
    }
  })()

  const [selectedHotspotIndex, setSelectedHotspotIndex] = useState<number>(0)
  const [hoveredSourceId, setHoveredSourceId] = useState<number | null>(null)
  const [showAllHotspots, setShowAllHotspots] = useState<boolean>(false)
  const [expandedHotspotSources, setExpandedHotspotSources] = useState<Record<number, boolean>>({})
  const [expandedFocusSources, setExpandedFocusSources] = useState<boolean>(false)

  const hotspotsList = keywords
    .map((k: any) => {
      // new schema: recent_hotspots
      if (recentHotspots.length > 0) {
        const coverageDocs = Number(k?.coverage_docs || 0)
        const coverageAccounts = Number(k?.coverage_accounts || 0)
        // 计算热度：热度 = 20 + 文档数 × 18 + 账号数 × 10，最高100分
        const calculatedHotness = Math.min(100, 20 + coverageDocs * 18 + coverageAccounts * 10)
        return {
          event: String(k?.event || '').trim(),
          hotness: calculatedHotness,
          whyHot: String(k?.why_hot || '').trim(),
          category: String(k?.category || '').trim(),
          sourceIds: Array.isArray(k?.source_ids) ? k.source_ids.map((x: any) => Number(x)).filter((n: number) => Number.isFinite(n) && n > 0) : [],
          coverageDocs,
          coverageAccounts,
          lastSeen: String(k?.last_seen || '').trim(),
        }
      }
      // legacy: hotwords/keywords
      const coverageDocs = Number(k?.coverage_docs || 0)
      const coverageAccounts = Number(k?.coverage_accounts || 0)
      const calculatedHotness = Math.min(100, 20 + coverageDocs * 18 + coverageAccounts * 10)
      return {
        event: String(k?.word || '').trim(),
        hotness: calculatedHotness,
        whyHot: '',
        category: '',
        sourceIds: Array.isArray(k?.source_ids) ? k.source_ids.map((x: any) => Number(x)).filter((n: number) => Number.isFinite(n) && n > 0) : [],
        coverageDocs,
        coverageAccounts,
        lastSeen: String(k?.last_seen || '').trim(),
      }
    })
    .filter((x: any) => x.event && x.coverageAccounts >= 3)
    // 排序：按热度降序（因为已经过滤了 coverage_accounts >= 3）
    .sort((a: any, b: any) => {
      return b.hotness - a.hotness
    })

  // Format date for Hero: "12月19日"
  const heroDate = (() => {
    const d = parseYmdAsShanghaiDate(reportDate)
    if (!d) return reportDate
    const month = d.getMonth() + 1
    const day = d.getDate()
    return `${month}月${day}日`
  })()

  // Get keywords data (convert hotspots to keywords format if needed)
  const keywordsList = (() => {
    if (Array.isArray(contentJson?.keywords) && contentJson.keywords.length > 0) {
      return contentJson.keywords.map((k: any) => ({
        word: String(k?.word || '').trim(),
        hotness: Number(k?.weight || k?.hotness || 0),
        citations: Number(k?.citations || (Array.isArray(k?.source_ids) ? k.source_ids.length : 0)),
        sourceIds: Array.isArray(k?.source_ids) ? k.source_ids.map((x: any) => Number(x)).filter((n: number) => Number.isFinite(n) && n > 0) : [],
        snippets: Array.isArray(k?.snippets) ? k.snippets : [],
      })).filter((k: any) => k.word)
    }
    // Fallback: convert hotspots to keywords format
    return hotspotsList.slice(0, 3).map((h: any) => ({
      word: h.event,
      hotness: h.hotness,
      citations: h.sourceIds.length,
      sourceIds: h.sourceIds,
      snippets: [],
    }))
  })()

  return (
    <div className="mb-16">
      {/* Hero Section - same style as WeeklyReview */}
      <div className="relative overflow-hidden rounded-3xl border bg-gradient-to-br from-slate-950 to-slate-950 text-white shadow-2xl mb-6">
        <div className="relative p-7 md:p-10">
          <div className="flex items-center justify-between max-w-6xl mx-auto">
          <div>
              <h1 className="text-4xl md:text-6xl font-bold tracking-tight text-white mb-4">这里财动</h1>
              <p className="text-lg text-white/80">
                大模型聚合的财政情报 · 每日10点更新
              </p>
            </div>
            <div className="text-right">
              <div className="text-sm md:text-base font-bold text-white mb-2">{heroDate}</div>
              <div className="text-xs md:text-sm font-semibold text-white/90">{reportTypeLabel}</div>
            </div>
          </div>
        </div>
      </div>

      {/* 今日焦点 Section */}
      <div className="bg-white rounded-3xl shadow-xl overflow-hidden mb-6 border-l-4 border-amber-600">
        {/* 标题栏 */}
        <div className="bg-gradient-to-r from-slate-50 to-amber-50/30 px-6 pt-6 pb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-amber-600 flex items-center justify-center shadow-md">
              <span className="text-white font-bold text-lg">i</span>
      </div>
            <div>
              <div className="text-xl font-bold text-gray-900">今日焦点</div>
              <div className="text-sm text-gray-600 mt-0.5">近24小时最值得关注的财政动态</div>
            </div>
          </div>
        </div>
        
        {/* 内容区 */}
        <div className="p-8 md:p-10 pl-10 md:pl-12 bg-slate-50/20">
          {headline && (
            <h2 className="text-3xl md:text-4xl font-medium text-gray-900 mb-5">
            {headline}
            </h2>
          )}
          
          {focusText && (() => {
            // 提取首句（到第一个句号、问号或感叹号）
            const firstSentenceMatch = focusText.match(/^[^。！？]+[。！？]/)
            const firstSentence = firstSentenceMatch ? firstSentenceMatch[0] : focusText.split('。')[0] + (focusText.includes('。') ? '。' : '')
            const restText = firstSentenceMatch ? focusText.slice(firstSentence.length).trim() : focusText.slice(firstSentence.length).trim()
            
            return (
              <div className="text-xl md:text-2xl leading-relaxed text-gray-900 mb-6 font-light">
                {firstSentence && (
                  <span className="bg-amber-50/50 px-2 py-1 rounded">{firstSentence}</span>
                )}
                {restText && <span className="ml-1">{restText}</span>}
              </div>
            )
          })()}

          {focusSourceIds.length > 0 && (
            <div className="mt-6">
              <div className="flex flex-wrap gap-2">
                {(expandedFocusSources ? focusSourceIds : focusSourceIds.slice(0, 3)).map((sid) => {
                  const s = sourcesById[sid]
                  const titleFull = s?.title ? String(s.title) : `引用`
                  const url = s?.url ? String(s.url) : ''
                  const account = s?.account ? String(s.account) : ''
                  const displayText = account ? `${account} · ${titleFull}` : titleFull
                  return (
                    <a
                      key={sid}
                      href={url || '#'}
                      target={url ? '_blank' : undefined}
                      rel={url ? 'noreferrer' : undefined}
                      title={displayText}
                      className="inline-flex items-center px-3 py-1.5 rounded-full text-xs bg-slate-100 hover:bg-slate-200 text-gray-700 transition-colors line-clamp-1"
                    >
                      {displayText}
                    </a>
                  )
                })}
                {focusSourceIds.length > 3 && !expandedFocusSources && (
                  <button
                    onClick={() => setExpandedFocusSources(true)}
                    className="inline-flex items-center px-3 py-1.5 rounded-full text-xs bg-slate-100 hover:bg-slate-200 text-gray-700 transition-colors border border-slate-300"
                  >
                    更多（+{focusSourceIds.length - 3}）
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
        </div>

      {/* 近日热点 Section */}
        {hotspotsList.length > 0 && (
        <div className="bg-white rounded-3xl shadow-lg overflow-hidden mb-6">
          {/* 标题栏 */}
          <div className="bg-gradient-to-r from-slate-50 to-emerald-50/30 px-6 pt-6 pb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-emerald-600 flex items-center justify-center shadow-md">
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <div>
                <div className="text-xl font-bold text-gray-900">近日热点</div>
                <div className="text-sm text-gray-600 mt-0.5">近3天覆盖3个不同公众号的话题</div>
              </div>
            </div>
              </div>

          {/* 内容区 */}
          <div className="p-8 md:p-10">
            <div className="space-y-4 mb-6">
              {(showAllHotspots ? hotspotsList : hotspotsList.slice(0, 3)).map((hotspot: any, idx: number) => {
                const isExpanded = expandedHotspotSources[idx] || false
                
                // 来源排序逻辑：优先不同公众号，再按时间倒序
                const sortedSourceIds = [...hotspot.sourceIds].sort((a: number, b: number) => {
                  const sa = sourcesById[a]
                  const sb = sourcesById[b]
                  if (!sa || !sb) return 0
                  
                  // 优先不同公众号：每个公众号先选1个（该公众号内最新）
                  if (sa.account !== sb.account) {
                    return (sa.account || '').localeCompare(sb.account || '')
                  }
                  
                  // 再按时间倒序：剩余来源按日期从新到旧
                  const dateA = sa.date ? new Date(sa.date).getTime() : 0
                  const dateB = sb.date ? new Date(sb.date).getTime() : 0
                  return dateB - dateA
                })
                
                // 获取不同公众号的第一个来源
                const accountMap = new Map<string, number[]>()
                sortedSourceIds.forEach((sid: number) => {
                  const s = sourcesById[sid]
                  if (s?.account) {
                    const acc = String(s.account)
                    if (!accountMap.has(acc)) {
                      accountMap.set(acc, [])
                    }
                    accountMap.get(acc)!.push(sid)
                  }
                })
                
                // 优先不同公众号：每个公众号先选1个（该公众号内最新）
                const prioritizedSources: number[] = []
                accountMap.forEach((sids) => {
                  // 每个公众号内按时间倒序，取第一个
                  const sorted = sids.sort((a: number, b: number) => {
                    const sa = sourcesById[a]
                    const sb = sourcesById[b]
                    if (!sa || !sb) return 0
                    const dateA = sa.date ? new Date(sa.date).getTime() : 0
                    const dateB = sb.date ? new Date(sb.date).getTime() : 0
                    return dateB - dateA
                  })
                  prioritizedSources.push(sorted[0])
                })
                
                // 然后添加剩余来源（按时间倒序）
                sortedSourceIds.forEach((sid: number) => {
                  if (!prioritizedSources.includes(sid)) {
                    prioritizedSources.push(sid)
                  }
                })
                
                const defaultSources = prioritizedSources.slice(0, 2)
                const moreSources = prioritizedSources.slice(2)

                return (
                  <div key={idx} className="border border-gray-200 rounded-xl p-5 bg-gradient-to-br from-gray-50 to-white hover:shadow-md transition-shadow">
                    {/* 事件名 */}
                    <div className="text-xl md:text-2xl font-medium text-gray-900 mb-2">
                      {hotspot.event}
                    </div>

                    {/* 一句话说明 */}
                    {hotspot.whyHot && (
                      <div className="text-sm text-slate-600 leading-relaxed mb-3 font-light">
                        {hotspot.whyHot}
                      </div>
                    )}
                    
                    {/* Sources - Badge Style */}
                    <div className="flex flex-wrap gap-2">
                      {defaultSources.map((sid: number) => {
                        const s = sourcesById[sid]
                        if (!s) return null
                        const title = s.title ? String(s.title) : ''
                        const url = s.url ? String(s.url) : ''
                        const account = s.account ? String(s.account) : ''
                        if (!title) return null
                        const displayText = account ? `${account} · ${title}` : title
                        return (
                          <a
                            key={sid}
                            href={url || '#'}
                            target={url ? '_blank' : undefined}
                            rel={url ? 'noreferrer' : undefined}
                            title={displayText}
                            className="inline-flex items-center px-3 py-1.5 rounded-full text-xs bg-slate-100 hover:bg-slate-200 text-gray-700 transition-colors line-clamp-1"
                          >
                            {displayText}
                          </a>
                        )
                      })}
                      
                      {/* 更多（+N）按钮 */}
                      {moreSources.length > 0 && !isExpanded && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            setExpandedHotspotSources({ ...expandedHotspotSources, [idx]: true })
                          }}
                          className="inline-flex items-center px-3 py-1.5 rounded-full text-xs bg-slate-100 hover:bg-slate-200 text-gray-700 transition-colors border border-slate-300"
                        >
                          更多（+{moreSources.length}）
                        </button>
                      )}
                    </div>
                    
                    {/* 展开的更多来源 */}
                    {isExpanded && moreSources.length > 0 && (
                      <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-gray-100">
                        {moreSources.map((sid: number) => {
                          const s = sourcesById[sid]
                          if (!s) return null
                          const title = s.title ? String(s.title) : ''
                          const url = s.url ? String(s.url) : ''
                          const account = s.account ? String(s.account) : ''
                          if (!title) return null
                          const displayText = account ? `${account} · ${title}` : title
                          return (
                            <a
                              key={sid}
                              href={url || '#'}
                              target={url ? '_blank' : undefined}
                              rel={url ? 'noreferrer' : undefined}
                              title={displayText}
                              className="inline-flex items-center px-3 py-1.5 rounded-full text-xs bg-slate-100 hover:bg-slate-200 text-gray-700 transition-colors line-clamp-1"
                            >
                              {displayText}
                            </a>
                          )
                        })}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>

            {/* 更多热点按钮 */}
            {hotspotsList.length > 3 && !showAllHotspots && (
              <div className="text-center">
                <button
                  onClick={() => setShowAllHotspots(true)}
                  className="px-4 py-1.5 text-sm text-gray-600 hover:text-gray-800 transition-colors"
                >
                  更多热点（+{hotspotsList.length - 3}）
                </button>
              </div>
            )}
            
            {showAllHotspots && hotspotsList.length > 3 && (
              <div className="text-center">
                <button
                  onClick={() => setShowAllHotspots(false)}
                  className="px-4 py-1.5 text-sm text-gray-600 hover:text-gray-800 transition-colors"
                >
                  收起
                </button>
          </div>
        )}
      </div>
        </div>
      )}

      {/* 今日彩蛋 Section */}
      {easterEgg && (easterEgg?.url || easterEgg?.title || easterEgg?.teaser) && (
        <div className="bg-white rounded-3xl shadow-lg overflow-hidden mb-6">
          {/* 标题栏 */}
          <div className="bg-gradient-to-r from-slate-50 to-rose-50/30 px-6 pt-6 pb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-rose-600 flex items-center justify-center shadow-md">
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
            <div>
                <div className="text-xl font-bold text-gray-900">今日彩蛋</div>
                {easterEgg?.account && (
                  <div className="text-sm text-gray-600 mt-0.5">
                    来自: {String(easterEgg.account)}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* 内容区 */}
          <div className="p-8 md:p-10">
            <div className="text-lg md:text-xl font-medium text-gray-900 mb-2">
                {String(easterEgg?.title || '')}
              </div>
              {easterEgg?.teaser && (
                easterEgg?.url ? (
                  <a
                    href={String(easterEgg.url)}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center px-3 py-1.5 rounded-full text-xs bg-slate-100 hover:bg-slate-200 text-gray-700 transition-colors line-clamp-1"
                    title={String(easterEgg.teaser)}
                  >
                    {String(easterEgg.teaser)}
                  </a>
                ) : (
                  <span className="inline-flex items-center px-3 py-1.5 rounded-full text-xs bg-slate-100 text-gray-700 line-clamp-1">
                    {String(easterEgg.teaser)}
                  </span>
                )
              )}
          </div>
        </div>
      )}
    </div>
  )
}


