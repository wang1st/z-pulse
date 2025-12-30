'use client'

import { useState } from 'react'
import Icon, { Icons } from '@/components/Icon'

type Source = { id: number; account?: string; title?: string; url?: string; date?: string }

export function SmartBrevityDaily(props: {
  reportTypeLabel?: '晨报' | '周报'
  reportDate: string
  createdAt: string
  articleCount: number
  contentJson: any
}) {
  const { reportTypeLabel = '晨报', reportDate, createdAt, articleCount, contentJson } = props
  const [selectedHotspotIndex, setSelectedHotspotIndex] = useState<number>(0)

  const header = contentJson?.header || {}
  const headline = String(header?.title || '')
  const lede = String(header?.lede || '')
  const why = String(contentJson?.why_it_matters || '')
  const big = String(contentJson?.big_picture || '')
  const recentHotspots = Array.isArray(contentJson?.recent_hotspots) ? contentJson.recent_hotspots : []
  const hotspotsMeta = contentJson?.recent_hotspots_meta && typeof contentJson.recent_hotspots_meta === 'object' ? contentJson.recent_hotspots_meta : null
  const legacyHotwords = Array.isArray(contentJson?.recent_hotwords) ? contentJson.recent_hotwords : []
  const keywords = recentHotspots.length > 0 ? recentHotspots : (legacyHotwords.length > 0 ? legacyHotwords : (Array.isArray(contentJson?.keywords) ? contentJson.keywords : []))
  const sources = Array.isArray(contentJson?.sources) ? contentJson.sources : []
  const easterEgg = contentJson?.easter_egg && typeof contentJson.easter_egg === 'object' ? contentJson.easter_egg : null
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

  const stripMarkers = (t: string) =>
    String(t || '')
      .replace(/【\s*(为何重要|为什么重要|大局)\s*】/g, '')
      .replace(/^\s*(为何重要|为什么重要|大局)\s*[:：]\s*/g, '')
      .replace(/\s+/g, ' ')
      .trim()

  const focusText = [lede, why, big].filter(Boolean).map(stripMarkers).filter(Boolean).join(' ')

  const focusSourceIds = Array.from(
    new Set(
      [...ledeCits, ...whyCits, ...bigCits]
        .map((n: any) => Number(n))
        .filter((n: number) => Number.isFinite(n) && n > 0)
    )
  )

  const hotspotsList = keywords
    .map((k: any) => {
      if (recentHotspots.length > 0) {
        return {
          event: String(k?.event || '').trim(),
          sourceIds: Array.isArray(k?.source_ids) ? k.source_ids.map((x: any) => Number(x)).filter((n: number) => Number.isFinite(n) && n > 0) : [],
        }
      }
      return {
        event: String(k?.word || '').trim(),
        sourceIds: Array.isArray(k?.source_ids) ? k.source_ids.map((x: any) => Number(x)).filter((n: number) => Number.isFinite(n) && n > 0) : [],
      }
    })
    .filter((x: any) => x.event)

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    const month = date.getMonth() + 1
    const day = date.getDate()
    return `${month}月${day}日`
  }

  return (
    <div className="mb-16">
      <div className="px-8 py-16 md:px-16" style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
        <div className="flex items-center justify-between max-w-6xl mx-auto">
          <div>
            <h1 className="text-4xl md:text-6xl font-bold tracking-tight text-white mb-4">这里财动</h1>
            <p className="text-lg text-white/80">大模型聚合的财政情报 · 每日10点更新</p>
          </div>
          <div className="text-right">
            <div className="text-xl md:text-2xl font-bold text-white mb-2">{formatDate(reportDate)}</div>
            <div className="text-lg md:text-xl font-semibold text-white/90">{reportTypeLabel}</div>
          </div>
        </div>
      </div>

      <div className="mt-8 px-8 md:px-16 -mt-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="hidden md:block"></div>
          <div className="space-y-6">
            <div className="rounded-2xl p-8 shadow-sm bg-white border border-slate-100">
              <div className="mb-6 flex items-center gap-3">
                <div className="h-1 w-12 rounded-full" style={{ background: 'linear-gradient(to right, #667eea, #764ba2)' }} />
                <span className="text-sm font-medium text-slate-500 uppercase tracking-wide">今日焦点</span>
              </div>
              <h2 className="text-3xl md:text-4xl font-bold text-slate-900 mb-6 leading-tight">
                {headline}
              </h2>
              {focusText && (
                <div className="text-lg leading-relaxed text-slate-600 mb-6">
                  {focusText}
                </div>
              )}

              {focusSourceIds.length > 0 && (
                <div className="pt-6 border-t border-slate-100">
                  <div className="text-xs font-medium text-slate-500 mb-3">引用来源</div>
                  <div className="space-y-2">
                    {focusSourceIds.slice(0, 4).map((sid) => {
                      const s = sourcesById[sid]
                      const titleFull = s?.title ? String(s.title) : `引用`
                      const url = s?.url ? String(s.url) : ''
                      const account = s?.account ? String(s.account) : ''
                      return (
                        <a
                          key={sid}
                          href={url || '#'}
                          target={url ? '_blank' : undefined}
                          rel={url ? 'noreferrer' : undefined}
                          title={titleFull}
                          className="flex items-start gap-3 rounded-lg p-3 hover:bg-slate-50 transition-colors group"
                        >
                          <Icon name={Icons.link} size={12} className="text-slate-400 group-hover:text-purple-600 shrink-0 mt-1" />
                          <div className="min-w-0 flex-1">
                            {account && <div className="text-xs text-slate-500 mb-0.5">{account}</div>}
                            <div className="text-sm text-slate-900 group-hover:text-purple-700 line-clamp-2">{titleFull}</div>
                          </div>
                        </a>
                      )
                    })}
                  </div>
                </div>
              )}
            </div>

            {hotspotsList.length > 0 && (
              <div className="rounded-2xl p-8 shadow-sm bg-white border border-slate-100">
                <div className="mb-6 flex items-center gap-3">
                  <div className="h-1 w-12 rounded-full" style={{ background: 'linear-gradient(to right, #667eea, #764ba2)' }} />
                  <span className="text-sm font-medium text-slate-500 uppercase tracking-wide">近日热点</span>
                </div>

                <div className="mb-6 flex flex-wrap gap-2">
                  {hotspotsList.slice(0, 9).map((it: any, idx: number) => (
                    <button
                      key={`tag-${it.event}-${idx}`}
                      onClick={() => setSelectedHotspotIndex(idx)}
                      className="px-4 py-2 rounded-lg text-sm font-medium transition-all"
                      style={{
                        backgroundColor: selectedHotspotIndex === idx ? '#667eea' : '#f8fafc',
                        color: selectedHotspotIndex === idx ? '#ffffff' : '#475569',
                        border: selectedHotspotIndex === idx ? 'none' : '1px solid #e2e8f0',
                        boxShadow: selectedHotspotIndex === idx ? '0 4px 15px rgba(102, 126, 234, 0.3)' : 'none',
                      }}
                    >
                      {it.event}
                    </button>
                  ))}
                </div>

                {hotspotsList[selectedHotspotIndex] && (() => {
                  const selectedHotspot = hotspotsList[selectedHotspotIndex]
                  const displaySourceId = selectedHotspot.sourceIds[0]
                  const displaySource = sourcesById[displaySourceId]
                  const articleTitle = displaySource?.title || ''
                  const articleUrl = displaySource?.url || '#'

                  return (
                    <div className="rounded-xl bg-slate-50 p-5">
                      {articleUrl !== '#' ? (
                        <a href={articleUrl} target="_blank" rel="noreferrer" className="group flex items-start gap-3">
                          <Icon name={Icons.link} size={14} className="text-slate-400 shrink-0 mt-0.5 group-hover:text-purple-600" />
                          <div className="min-w-0 flex-1">
                            <div className="text-sm text-slate-900 group-hover:text-purple-700 line-clamp-2">{articleTitle}</div>
                          </div>
                        </a>
                      ) : (
                        <div className="text-sm text-slate-900 line-clamp-2">{articleTitle}</div>
                      )}
                    </div>
                  )
                })()}
              </div>
            )}

            {easterEgg && (easterEgg?.url || easterEgg?.title || easterEgg?.teaser) && (
              <div className="rounded-2xl p-8 shadow-sm bg-white border border-slate-100">
                <div className="mb-6 flex items-center gap-3">
                  <div className="h-1 w-12 rounded-full" style={{ background: 'linear-gradient(to right, #f59e0b, #d97706)' }} />
                  <span className="text-sm font-medium text-slate-500 uppercase tracking-wide">今日彩蛋</span>
                </div>
                <div className="text-base font-semibold text-slate-900 mb-3">
                  {String(easterEgg?.title || '')}
                </div>
                {easterEgg?.teaser && (
                  easterEgg?.url ? (
                    <a href={String(easterEgg.url)} target="_blank" rel="noreferrer" className="group inline-flex items-start gap-2">
                      <Icon name={Icons.link} size={12} className="text-slate-400 shrink-0 mt-1 group-hover:text-amber-600" />
                      <span className="text-sm leading-relaxed text-slate-600 group-hover:text-amber-700">
                        {String(easterEgg.teaser)}
                      </span>
                    </a>
                  ) : (
                    <div className="text-sm leading-relaxed text-slate-600">
                      {String(easterEgg.teaser)}
                    </div>
                  )
                )}
              </div>
            )}
          </div>
          <div className="hidden md:block"></div>
        </div>
      </div>
    </div>
  )
}
