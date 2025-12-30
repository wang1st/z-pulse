'use client'

import React, { createContext, useCallback, useContext, useMemo, useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

export type ConfirmOptions = {
  title: string
  description?: string
  confirmText?: string
  cancelText?: string
  variant?: 'default' | 'destructive'
}

type ConfirmContextValue = {
  confirm: (opts: ConfirmOptions) => Promise<boolean>
}

const ConfirmContext = createContext<ConfirmContextValue | null>(null)

export function ConfirmProvider({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false)
  const [opts, setOpts] = useState<ConfirmOptions | null>(null)
  const resolverRef = useRef<((v: boolean) => void) | null>(null)

  const close = useCallback((result: boolean) => {
    setOpen(false)
    resolverRef.current?.(result)
    resolverRef.current = null
    // 延迟清理，避免关闭动画期间内容闪烁
    window.setTimeout(() => setOpts(null), 150)
  }, [])

  const confirm = useCallback((next: ConfirmOptions) => {
    setOpts(next)
    setOpen(true)
    return new Promise<boolean>((resolve) => {
      resolverRef.current = resolve
    })
  }, [])

  const value = useMemo(() => ({ confirm }), [confirm])

  return (
    <ConfirmContext.Provider value={value}>
      {children}
      <Dialog
        open={open}
        onOpenChange={(v) => {
          if (!v) close(false)
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{opts?.title ?? '请确认'}</DialogTitle>
            {opts?.description ? <DialogDescription>{opts.description}</DialogDescription> : null}
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => close(false)}>
              {opts?.cancelText ?? '取消'}
            </Button>
            <Button
              variant={opts?.variant === 'destructive' ? 'destructive' : 'default'}
              onClick={() => close(true)}
            >
              {opts?.confirmText ?? '确认'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </ConfirmContext.Provider>
  )
}

export function useConfirm() {
  const ctx = useContext(ConfirmContext)
  if (!ctx) throw new Error('useConfirm must be used within ConfirmProvider')
  return ctx
}


