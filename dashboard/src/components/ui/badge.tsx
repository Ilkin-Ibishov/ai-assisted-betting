import * as React from 'react'
import { cn } from '@/lib/utils'

type BadgeProps = React.HTMLAttributes<HTMLSpanElement> & {
  variant?: 'default' | 'secondary'
}

export function Badge({ className, variant = 'default', ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex h-6 items-center rounded-md px-2 text-xs font-medium',
        variant === 'default'
          ? 'bg-slate-900 text-white'
          : 'border border-slate-200 bg-slate-100 text-slate-700',
        className,
      )}
      {...props}
    />
  )
}
