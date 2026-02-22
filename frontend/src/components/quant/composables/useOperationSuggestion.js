import { computed } from 'vue'

const toNumber = (value, fallback = null) => {
  const num = Number(value)
  return Number.isFinite(num) ? num : fallback
}

const clamp = (value, min = 0, max = 1) => {
  const num = toNumber(value, min)
  return Math.min(max, Math.max(min, num))
}

const formatNumber = (value, digits = 2) => {
  if (value === null || value === undefined) return '-'
  const num = Number(value)
  if (!Number.isFinite(num)) return '-'
  return num.toFixed(digits)
}

const splitRatios = (values, fallback = [0.45, 0.35, 0.2]) => {
  const nums = values.map((item) => (Number.isFinite(Number(item)) ? Math.max(Number(item), 0) : 0))
  const sum = nums.reduce((acc, item) => acc + item, 0)
  if (sum <= 0) return fallback
  return nums.map((item) => item / sum)
}

const signalAssessment = (signal) => {
  const action = signal?.action
  if (action === 'breakout') {
    return { score: 2, direction: 'buy', reason: signal?.reason || '价格突破阻力位，趋势转强。' }
  }
  if (action === 'near_support') {
    return { score: 1, direction: 'buy_watch', reason: signal?.reason || '价格接近支撑位，可小仓试探。' }
  }
  if (action === 'near_resistance') {
    return { score: -1, direction: 'reduce', reason: signal?.reason || '价格接近阻力位，优先减仓。' }
  }
  if (action === 'breakdown') {
    return { score: -2, direction: 'sell', reason: signal?.reason || '价格跌破支撑位，优先风控。' }
  }
  return { score: 0, direction: 'watch', reason: signal?.reason || '暂无明确趋势信号，先观察。' }
}

const backtestAssessment = (stats) => {
  if (!stats) return { score: -0.2, notes: ['缺少回测统计，建议先执行回测再决策。'] }
  const notes = []
  let score = 0
  const winRate = toNumber(stats.winRate, 0)
  const totalProfit = toNumber(stats.totalProfit, 0)
  const totalTrades = toNumber(stats.total, 0)

  if (winRate >= 62) score += 1.0
  else if (winRate >= 55) score += 0.5
  else if (winRate < 45) score -= 0.8

  if (totalProfit > 0) score += 0.4
  else if (totalProfit < 0) score -= 0.4

  if (totalTrades < 15) {
    score -= 0.3
    notes.push('成交样本偏少，统计稳定性不足。')
  }

  notes.push(`回测胜率 ${formatNumber(winRate, 1)}%，累计盈亏 ${formatNumber(totalProfit, 2)}。`)
  return { score, notes }
}

const gridAssessment = (summary, diagnostics, topRuns) => {
  const notes = []
  let score = 0

  if (summary) {
    const winRate = toNumber(summary.validation_win_rate ?? summary.win_rate, null)
    const drawdown = toNumber(summary.validation_max_drawdown ?? summary.max_drawdown, null)
    if (winRate !== null) {
      if (winRate >= 60) score += 0.4
      else if (winRate < 50) score -= 0.2
    }
    if (drawdown !== null) {
      if (drawdown <= 0.12) score += 0.3
      else if (drawdown >= 0.22) score -= 0.3
    }
  }

  if (diagnostics) {
    const tested = toNumber(diagnostics.tested_runs, 0)
    const total = toNumber(diagnostics.total_candidates, 0)
    if (total > 0) {
      const coverage = tested / total
      if (coverage >= 0.95) score += 0.2
      else if (coverage < 0.7) score -= 0.2
      notes.push(`参数覆盖率 ${(coverage * 100).toFixed(0)}%（${tested}/${total}）。`)
    }
  }

  if (Array.isArray(topRuns) && topRuns.length) {
    score += 0.2
    const best = topRuns[0]
    if (best?.buy_strategy || best?.sell_strategy) {
      notes.push(`当前最优组合：${best.buy_strategy || '-'} / ${best.sell_strategy || '-'}`)
    }
  }

  return { score, notes }
}

const buildEvolutionSteps = ({ stats, gridSummary, gridTopRuns }) => {
  const steps = []

  if (Array.isArray(gridTopRuns) && gridTopRuns.length) {
    const best = gridTopRuns[0]
    steps.push(`围绕最优策略 ${best.buy_strategy || '-'} / ${best.sell_strategy || '-'} 做 ±20% 参数扩展寻优。`)
  } else {
    steps.push('先做参数交叉验证，拿到前 10 组合后再做二轮收敛。')
  }

  const trades = toNumber(stats?.total, 0)
  if (trades < 20) {
    steps.push('扩大回测区间到 2-3 年，或增加候选标的，提升样本有效性。')
  }

  const winRate = toNumber(stats?.winRate, 0)
  if (winRate > 0 && winRate < 52) {
    steps.push('下调仓位上限并收紧止损倍数，优先修复回撤后再追求收益。')
  } else if (winRate >= 60) {
    steps.push('保持止损不变，优先优化止盈分批比例，提高盈亏比。')
  }

  if (!gridSummary) {
    steps.push('当前缺少寻优结论，建议先运行“参数交叉验证”再执行一键闭环。')
  }

  return steps
}

export const useOperationSuggestion = ({
  analysisResult,
  backtestTradeStats,
  gridSummary,
  gridDiagnostics,
  gridTopRuns
}) => {
  const operationSuggestion = computed(() => {
    const signal = analysisResult.value?.signal || null
    const stats = backtestTradeStats.value || null

    const signalPart = signalAssessment(signal)
    const backtestPart = backtestAssessment(stats)
    const gridPart = gridAssessment(gridSummary.value, gridDiagnostics?.value, gridTopRuns.value)

    const totalScore = signalPart.score * 0.55 + backtestPart.score * 0.3 + gridPart.score * 0.15

    let confidence = '中'
    if (totalScore >= 1.3) confidence = '高'
    else if (totalScore <= -0.6) confidence = '低'

    let direction = signalPart.direction
    if (direction === 'watch') {
      if (totalScore >= 0.8) direction = 'buy_watch'
      else if (totalScore <= -0.8) direction = 'reduce'
    }
    if (direction === 'buy' && totalScore < 0.35) direction = 'buy_watch'
    if (direction === 'sell' && totalScore > -0.3) direction = 'reduce'

    let modeLabel = '观察等待'
    if (direction === 'buy' && confidence === '高') modeLabel = '主动进攻'
    else if (direction === 'buy' || direction === 'buy_watch') modeLabel = '试探进场'
    else if (direction === 'reduce' || direction === 'sell') modeLabel = '防守风控'

    let positionPct = 0.12
    if (direction === 'buy') positionPct = confidence === '高' ? 0.68 : 0.52
    else if (direction === 'buy_watch') positionPct = confidence === '高' ? 0.38 : 0.26
    else if (direction === 'reduce') positionPct = 0.15
    else if (direction === 'sell') positionPct = 0

    const winRate = toNumber(stats?.winRate, 0)
    if (winRate >= 65) positionPct = Math.min(0.8, positionPct + 0.06)
    if (winRate > 0 && winRate < 45) positionPct = Math.max(0, positionPct - 0.1)

    const lastClose = toNumber(signal?.last_close, null)
    const support = toNumber(signal?.support, null)
    const resistance = toNumber(signal?.resistance, null)

    let stopLoss = toNumber(signal?.stop_loss, null)
    let takeProfit = toNumber(signal?.take_profit, null)

    if (lastClose !== null) {
      if (stopLoss === null) {
        stopLoss = direction === 'sell' ? Number((lastClose * 1.02).toFixed(2)) : Number((lastClose * 0.95).toFixed(2))
      }
      const risk = Math.max(0.01, Math.abs(lastClose - stopLoss))
      if (takeProfit === null) {
        const rr = confidence === '高' ? 2.8 : 2.2
        takeProfit = Number((lastClose + risk * rr).toFixed(2))
      }
    }

    const tpDelta = lastClose !== null && takeProfit !== null ? Math.max(0, takeProfit - lastClose) : null
    const [entry1, entry2, entry3] = splitRatios(confidence === '高' ? [0.4, 0.35, 0.25] : [0.5, 0.3, 0.2])
    const [tp1Ratio, tp2Ratio, tp3Ratio] = splitRatios(confidence === '高' ? [0.35, 0.35, 0.3] : [0.4, 0.35, 0.25])

    const tranchePlan =
      direction === 'buy' || direction === 'buy_watch'
        ? [
            { label: '首笔建仓', ratio: entry1, trigger: '现价附近先建立试探仓。' },
            {
              label: '回踩加仓',
              ratio: entry2,
              trigger: support !== null ? `回踩 ${formatNumber(support)} 附近不破再加仓。` : '回踩短支撑不破时加仓。'
            },
            {
              label: '突破加仓',
              ratio: entry3,
              trigger: resistance !== null ? `放量突破 ${formatNumber(resistance)} 后加仓。` : '突破近端压力位后加仓。'
            }
          ]
        : [
            { label: '风险处理', ratio: 1, trigger: direction === 'sell' ? '优先清仓，停止新增仓位。' : '先降仓位，等待信号恢复。' }
          ]

    const takeProfitPlan =
      direction === 'buy' || direction === 'buy_watch'
        ? [
            {
              label: 'TP1',
              ratio: tp1Ratio,
              target: tpDelta !== null && lastClose !== null ? Number((lastClose + tpDelta * 0.5).toFixed(2)) : takeProfit
            },
            { label: 'TP2', ratio: tp2Ratio, target: takeProfit },
            {
              label: 'TP3',
              ratio: tp3Ratio,
              target: tpDelta !== null && lastClose !== null ? Number((lastClose + tpDelta * 1.4).toFixed(2)) : null
            }
          ]
        : [
            { label: '减仓线', ratio: 0.5, target: resistance },
            { label: '退出线', ratio: 0.5, target: stopLoss }
          ]

    const actionTextMap = {
      buy: '买入 / 加仓',
      buy_watch: '观察后试探买入',
      reduce: '减仓防守',
      sell: '止损退出',
      watch: '观望'
    }

    const hintParts = [...backtestPart.notes, ...gridPart.notes]
    if (support !== null || resistance !== null) {
      hintParts.push(`关键位：支撑 ${formatNumber(support)}，阻力 ${formatNumber(resistance)}。`)
    }

    return {
      direction,
      modeLabel,
      actionText: actionTextMap[direction] || actionTextMap.watch,
      confidence,
      reason: signalPart.reason,
      hint: hintParts.filter(Boolean).join(' '),
      lastClose,
      support,
      resistance,
      stopLoss,
      takeProfit,
      positionPct: clamp(positionPct, 0, 0.85),
      positionText: `${Math.round(clamp(positionPct, 0, 0.85) * 100)}%`,
      tranchePlan,
      takeProfitPlan,
      riskRule: {
        hardStop: stopLoss,
        trailStopPct: direction === 'buy' && confidence === '高' ? 0.06 : 0.05
      },
      evolutionSteps: buildEvolutionSteps({ stats, gridSummary: gridSummary.value, gridTopRuns: gridTopRuns.value }),
      workflowSteps: [
        '1. 独立选股：筛出前 10 只候选。',
        '2. 回测验证：验证候选在当前策略下的胜率与回撤。',
        '3. 量化分析：提取支撑/阻力与止损止盈位。',
        '4. 执行建议：按分批建仓与分批止盈规则执行。',
        '5. 结果复盘：将最新结果用于下一轮参数寻优。'
      ]
    }
  })

  return {
    operationSuggestion
  }
}
