'use client'

import React, { createContext, useCallback, useContext, useMemo, useState } from 'react'

type ToastVariant = 'default' | 'success' | 'error'

export type ToastOptions = {
  title?: string
  description: string
  variant?: ToastVariant
  durationMs?: number
}

type ToastItem = ToastOptions & { id: string }

type ToastContextValue = {
  toast: (opts: ToastOptions) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

function randomId() {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([])

  const remove = useCallback((id: string) => {
    setItems((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const toast = useCallback(
    (opts: ToastOptions) => {
      const id = randomId()
      const durationMs = opts.durationMs ?? 2500
      const item: ToastItem = {
        id,
        title: opts.title,
        description: opts.description,
        variant: opts.variant ?? 'default',
        durationMs,
      }
      setItems((prev) => [item, ...prev])
      window.setTimeout(() => remove(id), durationMs)
    },
    [remove]
  )

  const value = useMemo(() => ({ toast }), [toast])

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="fixed top-4 right-4 z-[60] flex flex-col gap-2 w-[360px] max-w-[calc(100vw-2rem)]">
        {items.map((t) => (
          <div
            key={t.id}
            className={[
              'rounded-lg border shadow-lg backdrop-blur-sm px-4 py-3',
              'bg-white/95',
              t.variant === 'success' ? 'border-green-200' : '',
              t.variant === 'error' ? 'border-red-200' : '',
            ].join(' ')}
            role="status"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                {t.title ? (
                  <div className="font-semibold text-gray-900">{t.title}</div>
                ) : null}
                <div className="text-sm text-gray-700 break-words">{t.description}</div>
              </div>
              <button
                className="text-xs text-gray-500 hover:text-gray-800"
                onClick={() => remove(t.id)}
                aria-label="Close toast"
              >
                关闭
              </button>
            </div>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used within ToastProvider')
  return ctx
}


