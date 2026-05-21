import { useEffect, useRef, useState } from 'react'
import { CartesianGrid, Line, LineChart, Tooltip, XAxis, YAxis } from 'recharts'
import { Skeleton } from '@/components/ui/skeleton'
import type { CrossReportTrendRow, TrendMetricKey } from '@/lib/metrics'

type CrossReportTrendChartProps = {
  data: CrossReportTrendRow[]
  loading: boolean
  visibleMetrics: TrendMetricKey[]
}

export default function CrossReportTrendChart({
  data,
  loading,
  visibleMetrics,
}: CrossReportTrendChartProps) {
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
    <div className="h-56 min-w-0" data-testid="cross-report-trend-chart" ref={chartRef}>
      {loading ? (
        <Skeleton className="h-full w-full" />
      ) : data.length && chartWidth > 0 ? (
        <LineChart
          data={data}
          height={224}
          margin={{ left: 8, right: 16, top: 8 }}
          width={chartWidth}
        >
          <CartesianGrid stroke="#e5e7eb" vertical={false} />
          <XAxis dataKey="label" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip
            formatter={(value, name) => [
              name === 'ROI' ? `${value}%` : value,
              name,
            ]}
            labelFormatter={(_, payload) => payload?.[0]?.payload?.fullLabel ?? ''}
          />
          {visibleMetrics.includes('roi') ? (
            <Line
              activeDot={{ r: 5 }}
              dataKey="roi"
              dot={{ r: 3 }}
              name="ROI"
              stroke="#2563eb"
              strokeWidth={2}
              type="monotone"
            />
          ) : null}
          {visibleMetrics.includes('brierScore') ? (
            <Line
              activeDot={{ r: 5 }}
              dataKey="brierScore"
              dot={{ r: 3 }}
              name="Brier"
              stroke="#059669"
              strokeWidth={2}
              type="monotone"
            />
          ) : null}
          {visibleMetrics.includes('logLoss') ? (
            <Line
              activeDot={{ r: 5 }}
              dataKey="logLoss"
              dot={{ r: 3 }}
              name="Log loss"
              stroke="#7c3aed"
              strokeWidth={2}
              type="monotone"
            />
          ) : null}
        </LineChart>
      ) : data.length ? (
        <Skeleton className="h-full w-full" />
      ) : (
        <div className="flex h-full min-h-32 items-center justify-center rounded-md border border-dashed border-slate-300 bg-slate-50 text-sm text-slate-500">
          No trend data available.
        </div>
      )}
    </div>
  )
}
