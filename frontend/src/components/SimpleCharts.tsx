interface PieChartProps {
  data: { label: string; value: number; color: string }[]
  size?: number
  innerRadius?: number
}

export function PieChart({ data, size = 160, innerRadius = 0.55 }: PieChartProps) {
  const total = data.reduce((s, d) => s + d.value, 0)
  if (total === 0) return <div className="text-xs text-[var(--color-text-tertiary)]">暂无数据</div>

  const cx = size / 2
  const cy = size / 2
  const r = size / 2 - 4
  const ir = r * innerRadius

  let cumAngle = -90
  const slices = data.map((d) => {
    const angle = (d.value / total) * 360
    const startAngle = cumAngle
    const endAngle = cumAngle + angle
    cumAngle = endAngle

    const x1 = cx + r * Math.cos((Math.PI * startAngle) / 180)
    const y1 = cy + r * Math.sin((Math.PI * startAngle) / 180)
    const x2 = cx + r * Math.cos((Math.PI * endAngle) / 180)
    const y2 = cy + r * Math.sin((Math.PI * endAngle) / 180)
    const x3 = cx + ir * Math.cos((Math.PI * endAngle) / 180)
    const y3 = cy + ir * Math.sin((Math.PI * endAngle) / 180)
    const x4 = cx + ir * Math.cos((Math.PI * startAngle) / 180)
    const y4 = cy + ir * Math.sin((Math.PI * startAngle) / 180)

    const largeArc = angle > 180 ? 1 : 0

    const pathD =
      `M ${x1} ${y1} ` +
      `A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2} ` +
      `L ${x3} ${y3} ` +
      `A ${ir} ${ir} 0 ${largeArc} 0 ${x4} ${y4} ` +
      `Z`

    return { ...d, pathD, percent: ((d.value / total) * 100).toFixed(1) }
  })

  return (
    <svg width={size} height={size} className="shrink-0">
      {slices.map((s, i) => (
        <path key={i} d={s.pathD} fill={s.color} opacity={0.85}
          className="hover:opacity-100 transition-opacity cursor-pointer"
        />
      ))}
    </svg>
  )
}

interface BarChartProps {
  data: { label: string; value: number; color?: string }[]
  height?: number
  barColor?: string
}

export function BarChart({ data, height = 140, barColor = '#00D9A3' }: BarChartProps) {
  if (data.length === 0) return <div className="text-xs text-[var(--color-text-tertiary)]">暂无数据</div>

  const max = Math.max(...data.map(d => d.value), 1)
  const barWidth = Math.min(40, (280 - data.length * 8) / data.length)
  const gap = 4
  const svgWidth = data.length * (barWidth + gap) + 40
  const paddingTop = 20
  const chartHeight = height - 30

  return (
    <svg width="100%" height={height} viewBox={`0 0 ${svgWidth} ${height}`} preserveAspectRatio="none"
      className="overflow-visible"
    >
      {/* Grid lines */}
      {[0, 0.25, 0.5, 0.75, 1].map((p) => {
        const y = paddingTop + chartHeight * (1 - p)
        return (
          <g key={p}>
            <line x1={30} y1={y} x2={svgWidth - 10} y2={y}
              stroke="var(--color-border-subtle)" strokeWidth={0.5} strokeDasharray="3,3" />
            <text x={28} y={y + 4} textAnchor="end"
              className="text-[9px] fill-[var(--color-text-tertiary)] font-mono">
              {Math.round(max * p)}
            </text>
          </g>
        )
      })}

      {/* Bars */}
      {data.map((d, i) => {
        const x = 35 + i * (barWidth + gap)
        const barHeight = (d.value / max) * chartHeight
        const y = paddingTop + chartHeight - barHeight
        return (
          <g key={i}>
            <rect x={x} y={y} width={barWidth} height={barHeight}
              fill={d.color || barColor} rx={3} opacity={0.8}
              className="hover:opacity-100 transition-all cursor-pointer"
            />
            <text x={x + barWidth / 2} y={y - 4}
              textAnchor="middle"
              className="text-[9px] fill-[var(--color-text-secondary)] font-medium">
              {d.value}
            </text>
            <text x={x + barWidth / 2} y={height - 6}
              textAnchor="middle"
              className="text-[8px] fill-[var(--color-text-tertiary)]">
              {d.label.length > 4 ? d.label.slice(0, 4) + '…' : d.label}
            </text>
          </g>
        )
      })}
    </svg>
  )
}
