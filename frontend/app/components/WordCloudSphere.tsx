'use client'

import { useEffect, useMemo, useRef, useState } from 'react'

type Source = { id: number; account?: string; title?: string; url?: string }
type WordItem = { word: string; weight?: number; count?: number; source_ids?: number[] }

function clamp(n: number, lo: number, hi: number) {
  return Math.max(lo, Math.min(hi, n))
}

function makeSpherePoints(n: number) {
  // Golden spiral points on a sphere (stable distribution)
  const pts: { x: number; y: number; z: number }[] = []
  const offset = 2 / n
  const increment = Math.PI * (3 - Math.sqrt(5))
  for (let i = 0; i < n; i++) {
    const y = i * offset - 1 + offset / 2
    const r = Math.sqrt(1 - y * y)
    const phi = i * increment
    const x = Math.cos(phi) * r
    const z = Math.sin(phi) * r
    pts.push({ x, y, z })
  }
  return pts
}

export function WordCloudSphere(props: {
  words: WordItem[]
  sourcesById: Record<number, Source>
  className?: string
}) {
  const { words, sourcesById, className } = props
  const containerRef = useRef<HTMLDivElement | null>(null)
  const rafRef = useRef<number | null>(null)
  const pausedRef = useRef(false)

  const [hoverWord, setHoverWord] = useState<WordItem | null>(null)
  const [mouse, setMouse] = useState<{ x: number; y: number } | null>(null)

  const pts = useMemo(() => makeSpherePoints(Math.max(1, words.length)), [words.length])

  useEffect(() => {
    // Pause the sphere while tooltip is open so the UI is stable for reading/clicking sources.
    pausedRef.current = !!hoverWord
  }, [hoverWord])

  useEffect(() => {
    const el = containerRef.current
    if (!el) return

    const tags = Array.from(el.querySelectorAll<HTMLElement>('[data-tag="1"]'))
    if (!tags.length) return

    let width = el.clientWidth
    let height = el.clientHeight
    let radius = Math.min(width, height) * 0.38
    let speedX = 0.0016
    let speedY = 0.0012

    const state = pts.map((p, i) => ({ ...p, i }))

    const onResize = () => {
      width = el.clientWidth
      height = el.clientHeight
      radius = Math.min(width, height) * 0.38
    }

    const onMove = (e: MouseEvent) => {
      const rect = el.getBoundingClientRect()
      const dx = (e.clientX - (rect.left + rect.width / 2)) / rect.width
      const dy = (e.clientY - (rect.top + rect.height / 2)) / rect.height
      speedY = clamp(dx, -0.6, 0.6) * 0.02
      speedX = clamp(-dy, -0.6, 0.6) * 0.02
    }

    const onWheel = (e: WheelEvent) => {
      // “可滚动”：滚轮缩放球体半径（更直观）
      e.preventDefault()
      const delta = clamp(e.deltaY, -200, 200)
      radius = clamp(radius - delta * 0.15, 90, Math.min(width, height) * 0.52)
    }

    window.addEventListener('resize', onResize)
    el.addEventListener('mousemove', onMove)
    el.addEventListener('wheel', onWheel, { passive: false })

    const tick = () => {
      const paused = pausedRef.current
      const sinX = paused ? 0 : Math.sin(speedX)
      const cosX = paused ? 1 : Math.cos(speedX)
      const sinY = paused ? 0 : Math.sin(speedY)
      const cosY = paused ? 1 : Math.cos(speedY)

      for (let k = 0; k < state.length; k++) {
        let { x, y, z, i } = state[k]

        // rotate around X
        let y1 = y * cosX - z * sinX
        let z1 = y * sinX + z * cosX
        y = y1
        z = z1

        // rotate around Y
        let x1 = x * cosY + z * sinY
        let z2 = -x * sinY + z * cosY
        x = x1
        z = z2

        state[k].x = x
        state[k].y = y
        state[k].z = z

        const scale = (z + 2) / 3 //  ~ [0.33, 1.0]
        const left = x * radius * scale + width / 2
        const top = y * radius * scale + height / 2

        const node = tags[i]
        if (!node) continue
        node.style.transform = `translate(-50%, -50%) translate(${left}px, ${top}px) scale(${scale})`
        node.style.opacity = String(0.25 + scale * 0.75)
        node.style.zIndex = String(Math.floor(scale * 1000))
        node.style.filter = `blur(${(1 - scale) * 0.6}px)`
      }

      rafRef.current = window.requestAnimationFrame(tick)
    }

    rafRef.current = window.requestAnimationFrame(tick)

    return () => {
      if (rafRef.current) window.cancelAnimationFrame(rafRef.current)
      window.removeEventListener('resize', onResize)
      el.removeEventListener('mousemove', onMove)
      el.removeEventListener('wheel', onWheel as any)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pts])

  if (!words?.length) return null

  const tooltip = hoverWord ? (
    <div
      className="pointer-events-auto absolute z-50 w-[360px] max-w-[90vw] rounded-xl border bg-white p-3 shadow-xl"
      style={
        mouse
          ? { left: mouse.x + 14, top: mouse.y + 14 }
          : { left: 12, top: 12 }
      }
    >
      <div className="flex items-start justify-between gap-3">
        <div className="text-sm font-semibold text-gray-900">{hoverWord.word}</div>
        <button
          type="button"
          className="shrink-0 rounded-md px-2 py-1 text-xs text-gray-600 hover:bg-gray-100"
          aria-label="关闭"
          onClick={() => setHoverWord(null)}
        >
          关闭
        </button>
      </div>
      <div className="mt-2 text-xs text-gray-500">来源（点击原标题跳转到下方来源链接）</div>
      <div className="mt-2 space-y-1">
        {(hoverWord.source_ids || []).slice(0, 6).map((sid) => {
          const s = sourcesById[sid]
          if (!s) return null
          const label = s.account ? `${s.account}｜${s.title || ''}` : (s.title || '')
          return (
            <button
              key={sid}
              className="block w-full text-left text-xs text-blue-600 hover:underline"
              onClick={() => {
                // Jump to the corresponding "来源" entry (bottom) for this item
                try {
                  window.location.hash = `src-${sid}`
                } catch {}
                const el = document.getElementById(`src-${sid}`)
                if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
              }}
              title={label}
            >
              {label}
            </button>
          )
        })}
        {(!hoverWord.source_ids || hoverWord.source_ids.length === 0) && (
          <div className="text-xs text-gray-500">暂无可追溯来源（建议重新生成该晨报）</div>
        )}
      </div>
    </div>
  ) : null

  return (
    <div className={className || ''}>
      <div className="relative">
        {tooltip}
        <div
          ref={containerRef}
          className="relative h-[320px] w-full overflow-hidden rounded-2xl border bg-gradient-to-b from-white to-slate-50"
          onMouseMove={(e) => setMouse({ x: e.clientX, y: e.clientY })}
        >
          {words.slice(0, 45).map((w, idx) => {
            const weight = clamp(Number(w.weight ?? 60), 20, 100)
            const font = 12 + (weight * 18) / 100
            return (
              <button
                key={`${w.word}-${idx}`}
                data-tag="1"
                type="button"
                aria-label={w.word}
                className="absolute left-0 top-0 select-none whitespace-nowrap font-semibold text-slate-900"
                style={{
                  fontSize: `${font}px`,
                  transform: 'translate(-50%, -50%)',
                  willChange: 'transform, opacity',
                  cursor: 'pointer',
                  background: 'transparent',
                  border: 'none',
                  padding: 0,
                }}
                onMouseEnter={() => setHoverWord(w)}
                onFocus={() => setHoverWord(w)}
                onClick={() => setHoverWord(w)}
              >
                {w.word}
              </button>
            )
          })}
        </div>
        <div className="mt-2 text-xs text-gray-500">
          提示：移动鼠标改变旋转方向；滚轮缩放词云球；悬停查看来源。
        </div>
      </div>
    </div>
  )
}


