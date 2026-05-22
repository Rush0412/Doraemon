import { createChart } from 'lightweight-charts'

const buildBaseChartOptions = ({ width, height }) => ({
  height,
  width,
  layout: {
    background: { color: '#ffffff' },
    textColor: '#1b1a18',
    fontFamily: "Sora, 'Noto Sans SC', sans-serif",
    attributionLogo: false
  },
  grid: {
    vertLines: { color: 'rgba(27, 26, 24, 0.08)' },
    horzLines: { color: 'rgba(27, 26, 24, 0.08)' }
  },
  rightPriceScale: {
    borderColor: 'rgba(27, 26, 24, 0.2)'
  },
  timeScale: {
    borderColor: 'rgba(27, 26, 24, 0.2)',
    timeVisible: true,
    secondsVisible: false
  }
})

export const createKlineChartRuntime = ({ container, onCrosshairMove }) => {
  if (!container?.clientWidth) return null
  const chart = createChart(
    container,
    {
      ...buildBaseChartOptions({ width: container.clientWidth, height: 560 }),
      crosshair: {
        mode: 0
      }
    }
  )
  const candleSeries = chart.addCandlestickSeries({
    upColor: '#c23531',
    downColor: '#2f7d32',
    wickUpColor: '#c23531',
    wickDownColor: '#2f7d32',
    borderVisible: false
  })
  const volumeSeries = chart.addHistogramSeries({
    priceFormat: { type: 'volume' },
    priceScaleId: '',
    scaleMargins: { top: 0.8, bottom: 0 }
  })
  if (typeof onCrosshairMove === 'function') {
    chart.subscribeCrosshairMove(onCrosshairMove)
  }
  return { chart, candleSeries, volumeSeries }
}

export const createEquityChartRuntime = ({ container }) => {
  if (!container?.clientWidth) return null
  const chart = createChart(container, buildBaseChartOptions({ width: container.clientWidth, height: 280 }))
  const equitySeries = chart.addLineSeries({
    color: '#1f7a4b',
    lineWidth: 2
  })
  return { chart, equitySeries }
}

export const resizeChartRuntime = ({ chart, container }) => {
  if (!chart || !container?.clientWidth) return
  chart.applyOptions({ width: container.clientWidth })
}

export const destroyChartRuntime = (chart) => {
  if (!chart) return
  chart.remove()
}
