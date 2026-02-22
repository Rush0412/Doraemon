import { computed, reactive, ref } from 'vue'

const formatNumber = (value, digits = 2) => {
  if (value === null || value === undefined) return '-'
  const num = Number(value)
  if (!Number.isFinite(num)) return '-'
  return num.toFixed(digits)
}

const clamp01 = (value, fallback = 0) => {
  const num = Number(value)
  if (!Number.isFinite(num)) return fallback
  return Math.max(0, Math.min(1, num))
}

const normalizeTriplet = (a, b, c, defaults = [0.4, 0.4, 0.2]) => {
  const values = [Number(a), Number(b), Number(c)].map((item) => (Number.isFinite(item) ? Math.max(item, 0) : 0))
  const sum = values.reduce((acc, item) => acc + item, 0)
  if (sum <= 0) return defaults
  return values.map((item) => item / sum)
}

export const useOperationSuggestion = ({
  analysisResult,
  backtestTradeStats,
  gridSummary,
  gridTopRuns
}) => {
  const adviceProfile = ref('balanced')
  const adviceTemplates = reactive({
    conservative: {
      label: '稳健',
      position: {
        buyHigh: 0.45,
        buyMid: 0.3,
        buyWatchHigh: 0.28,
        buyWatchMid: 0.18,
        reduce: 0.15,
        watch: 0.1
      },
      entry: { first: 0.45, pullback: 0.35, breakout: 0.2 },
      takeProfit: { tp1: 0.3, tp2: 0.4, tp3: 0.3 },
      trailStopPct: 0.04
    },
    balanced: {
      label: '平衡',
      position: {
        buyHigh: 0.6,
        buyMid: 0.45,
        buyWatchHigh: 0.4,
        buyWatchMid: 0.25,
        reduce: 0.2,
        watch: 0.12
      },
      entry: { first: 0.5, pullback: 0.3, breakout: 0.2 },
      takeProfit: { tp1: 0.4, tp2: 0.4, tp3: 0.2 },
      trailStopPct: 0.05
    },
    aggressive: {
      label: '激进',
      position: {
        buyHigh: 0.75,
        buyMid: 0.6,
        buyWatchHigh: 0.5,
        buyWatchMid: 0.35,
        reduce: 0.25,
        watch: 0.15
      },
      entry: { first: 0.55, pullback: 0.25, breakout: 0.2 },
      takeProfit: { tp1: 0.35, tp2: 0.35, tp3: 0.3 },
      trailStopPct: 0.06
    }
  })

  const currentAdviceTemplate = computed(() => adviceTemplates[adviceProfile.value] || adviceTemplates.balanced)

  const operationSuggestion = computed(() => {
    const signal = analysisResult.value?.signal || null
    const stats = backtestTradeStats.value
    const hasGridBest = !!gridSummary.value || gridTopRuns.value.length > 0
    const tpl = currentAdviceTemplate.value

    let direction = 'watch'
    let reason = '暂无明确趋势信号，建议等待突破或支撑确认。'
    let score = 0

    if (signal?.action === 'breakout') {
      direction = 'buy'
      reason = signal.reason || '价格向上突破阻力位。'
      score += 2
    } else if (signal?.action === 'near_support') {
      direction = 'buy_watch'
      reason = signal.reason || '价格接近支撑位，等待确认后分批加仓。'
      score += 1
    } else if (signal?.action === 'breakdown') {
      direction = 'sell'
      reason = signal.reason || '价格跌破支撑位。'
      score -= 2
    } else if (signal?.action === 'near_resistance') {
      direction = 'reduce'
      reason = signal.reason || '价格接近阻力位，建议减仓保护收益。'
      score -= 1
    } else if (signal?.reason) {
      reason = signal.reason
    }

    if (stats) {
      if (stats.winRate >= 60) score += 1
      else if (stats.winRate < 45) score -= 1
    }
    if (hasGridBest) score += 0.5

    if (direction === 'buy' && score <= 0) direction = 'buy_watch'
    if (direction === 'sell' && score >= 0) direction = 'reduce'

    const confidence = score >= 2 ? 'High' : score <= -1 ? 'Low' : 'Medium'

    let positionPct = clamp01(tpl.position.watch, 0.1)
    if (direction === 'buy') {
      positionPct = confidence === 'High' ? clamp01(tpl.position.buyHigh, 0.6) : clamp01(tpl.position.buyMid, 0.45)
    } else if (direction === 'buy_watch') {
      positionPct =
        confidence === 'High' ? clamp01(tpl.position.buyWatchHigh, 0.4) : clamp01(tpl.position.buyWatchMid, 0.25)
    } else if (direction === 'reduce') {
      positionPct = clamp01(tpl.position.reduce, 0.2)
    } else if (direction === 'sell') {
      positionPct = 0
    }

    if (stats?.winRate && stats.winRate < 45) positionPct = Math.max(0, positionPct - 0.1)
    if (stats?.winRate && stats.winRate > 65) positionPct = Math.min(0.85, positionPct + 0.1)

    const stopLoss = signal?.stop_loss ?? null
    const takeProfit = signal?.take_profit ?? null
    const lastClose = signal?.last_close ?? null
    if (lastClose && stopLoss && Number(stopLoss) >= Number(lastClose)) {
      positionPct = Math.min(positionPct, 0.15)
    }

    const delta =
      Number.isFinite(Number(takeProfit)) && Number.isFinite(Number(lastClose))
        ? Number(takeProfit) - Number(lastClose)
        : null
    const tp1Price =
      Number.isFinite(delta) && delta > 0 && Number.isFinite(Number(lastClose))
        ? Number((Number(lastClose) + delta * 0.5).toFixed(2))
        : takeProfit
    const tp2Price = Number.isFinite(Number(takeProfit)) ? Number(Number(takeProfit).toFixed(2)) : null
    const tp3Price =
      Number.isFinite(delta) && delta > 0 && Number.isFinite(Number(takeProfit))
        ? Number((Number(takeProfit) + delta * 0.5).toFixed(2))
        : null

    const [entry1, entry2, entry3] = normalizeTriplet(tpl.entry.first, tpl.entry.pullback, tpl.entry.breakout, [0.5, 0.3, 0.2])
    const [tp1Ratio, tp2Ratio, tp3Ratio] = normalizeTriplet(tpl.takeProfit.tp1, tpl.takeProfit.tp2, tpl.takeProfit.tp3, [0.4, 0.4, 0.2])

    const hintParts = []
    if (stats) {
      hintParts.push(`回测胜率 ${formatNumber(stats.winRate, 1)}%，累计盈亏 ${formatNumber(stats.totalProfit, 2)}`)
    }
    if (hasGridBest) {
      hintParts.push('已获得寻优组合，建议先对重点标的做二次回测后再实盘。')
    }
    if (signal?.support || signal?.resistance) {
      hintParts.push(`支撑位 ${formatNumber(signal?.support)}，阻力位 ${formatNumber(signal?.resistance)}`)
    }

    const actionTextMap = {
      buy: '买入 / 加仓',
      buy_watch: '观察待买',
      sell: '止损 / 清仓',
      reduce: '减仓',
      watch: '观望'
    }

    return {
      direction,
      actionText: actionTextMap[direction] || actionTextMap.watch,
      confidence,
      reason,
      hint: hintParts.join('；'),
      lastClose,
      stopLoss,
      takeProfit,
      positionPct,
      positionText: `${Math.round(positionPct * 100)}%`,
      profileKey: adviceProfile.value,
      profileLabel: tpl.label,
      tranchePlan:
        direction === 'buy' || direction === 'buy_watch'
          ? [
              { label: '首批', ratio: entry1, trigger: '当前价附近先建第一笔仓位' },
              { label: '回踩加仓', ratio: entry2, trigger: '回踩支撑不破时加仓' },
              { label: '突破加仓', ratio: entry3, trigger: '突破确认后追加仓位' }
            ]
          : [{ label: '防守', ratio: 1, trigger: '优先降低风险敞口' }],
      takeProfitPlan:
        direction === 'buy' || direction === 'buy_watch'
          ? [
              { label: 'TP1', ratio: tp1Ratio, target: tp1Price },
              { label: 'TP2', ratio: tp2Ratio, target: tp2Price },
              { label: 'TP3', ratio: tp3Ratio, target: tp3Price }
            ]
          : [
              { label: '减仓线', ratio: 0.5, target: signal?.resistance ?? null },
              { label: '退出线', ratio: 0.5, target: stopLoss }
            ],
      riskRule: {
        hardStop: stopLoss,
        trailStopPct: clamp01(tpl.trailStopPct, 0.05)
      }
    }
  })

  return {
    adviceProfile,
    adviceTemplates,
    operationSuggestion
  }
}
