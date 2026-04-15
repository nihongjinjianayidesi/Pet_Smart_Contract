import { cn } from '../lib/utils'
import type { ReactNode } from 'react'

export type StatusTone = 'orange' | 'green' | 'red' | 'zinc' | 'blue'

const toneMap: Record<StatusTone, { bg: string; text: string }> = {
  orange: { bg: 'bg-orange-100', text: 'text-orange-700' },
  green: { bg: 'bg-green-100', text: 'text-green-700' },
  red: { bg: 'bg-red-100', text: 'text-red-700' },
  zinc: { bg: 'bg-zinc-100', text: 'text-zinc-700' },
  blue: { bg: 'bg-blue-100', text: 'text-blue-700' }
}

export default function StatusPill({
  children,
  tone = 'zinc',
  className
}: {
  children: ReactNode
  tone?: StatusTone
  className?: string
}) {
  const t = toneMap[tone]
  return (
    <span className={cn('px-2 py-0.5 rounded text-[10px] font-black', t.bg, t.text, className)}>
      {children}
    </span>
  )
}
