import { useEffect, useRef, useState } from 'react'
import { Bar, BarChart, CartesianGrid, Tooltip, XAxis, YAxis } from 'recharts'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import type { ChartRow } from '@/lib/metrics'

type MetricChartProps = {
  data: ChartRow[]
  dataKey: keyof Pick<ChartRow, 'roi' | 'brier' | 'logLoss' | 'settledBets'>
  description: string
  loading: boolean
  title: string
}

export default function MetricChart({
  data,
  dataKey,
  description,
  loading,
  title,
}: MetricChartProps) {
  const chartRef = useRef<HTMLDivElement>(null)
  const [chartWidth, setChartWidth] = useState(0)

  useEffect(() => {
    const element = chartRef.current
    if (!element) {
      return
    }

    const resizeObserver = new ResizeObserver(([entry]) => {
      setChartWidth(Math.floor(entry.contentRect.width))
    })
    resizeObserver.observe(element)

    return () => resizeObserver.disconnect()
  }, [])

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-64 min-w-0" ref={chartRef}>
          {loading ? (
            <Skeleton className="h-full w-full" />
          ) : data.length && chartWidth > 0 ? (
            <BarChart
              data={data}
              height={256}
              margin={{ left: 8, right: 8, top: 8 }}
              width={chartWidth}
            >
              <CartesianGrid stroke="#e5e7eb" vertical={false} />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} interval={0} height={48} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip labelFormatter={(_, payload) => payload?.[0]?.payload?.fullLabel ?? ''} />
              <Bar dataKey={dataKey} fill="#2563eb" radius={[4, 4, 0, 0]} />
            </BarChart>
          ) : data.length ? (
            <Skeleton className="h-full w-full" />
          ) : (
            <EmptyState text="No comparison runs available." />
          )}
        </div>
      </CardContent>
    </Card>
  )
}

function EmptyState({ text }: { text: string }) {
  return (
    <div className="flex h-full min-h-32 items-center justify-center rounded-md border border-dashed border-slate-300 bg-slate-50 text-sm text-slate-500">
      {text}
    </div>
  )
}
