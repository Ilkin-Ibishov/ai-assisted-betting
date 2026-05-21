import * as React from 'react'
import { cn } from '@/lib/utils'

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'default' | 'outline'
}

export function Button({
  className,
  variant = 'default',
  type = 'button',
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={cn(
        'inline-flex h-10 items-center justify-center gap-2 rounded-md px-3 text-sm font-medium transition-colors disabled:pointer-events-none disabled:opacity-50',
        variant === 'default'
          ? 'bg-slate-900 text-white hover:bg-slate-800'
          : 'border border-slate-300 bg-white text-slate-900 hover:bg-slate-50',
        className,
      )}
      {...props}
    />
  )
}
