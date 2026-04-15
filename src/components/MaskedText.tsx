import { maskValue, type MaskKind } from '../lib/privacy'
import { cn } from '../lib/utils'

export default function MaskedText({
  value,
  kind,
  reveal = false,
  className
}: {
  value: string
  kind: MaskKind
  reveal?: boolean
  className?: string
}) {
  const text = reveal ? value : maskValue(value, kind)
  return <span className={cn('font-mono', className)}>{text}</span>
}

