<template>
  <section class="grid grid-2 strategy-layout" v-show="active">
    <div class="panel strategy-main">
      <header class="panel-title">
        <div>
          <h2>历史回测</h2>
          <p class="muted">执行经典买入突破 + ATR 止损止盈。</p>
        </div>
        <span class="pill">回测</span>
      </header>
      <p class="panel-note">建议回测区间 ≥ 1 年；若无成交请缩短买入周期或扩大回测时间。</p>
      <div class="form-grid">
        <div>
          <label class="label">标的列表</label>
          <input v-model="backtestForm.symbols" placeholder="sh600036, sz000001" />
        </div>
        <div>
          <label class="label">初始资金</label>
          <input v-model.number="backtestForm.cash" type="number" min="1000" />
        </div>
        <div>
          <label class="label">买入周期</label>
          <input v-model.number="backtestForm.buy_xd" type="number" min="1" />
        </div>
        <div>
          <label class="label">止损倍数</label>
          <input v-model.number="backtestForm.stop_loss_n" type="number" step="0.1" />
        </div>
        <div>
          <label class="label">止盈倍数</label>
          <input v-model.number="backtestForm.stop_win_n" type="number" step="0.1" />
        </div>
        <div>
          <label class="label">回溯年数</label>
          <input v-model.number="backtestForm.n_folds" type="number" min="1" />
        </div>
        <div>
          <label class="label">开始日期</label>
          <input v-model="backtestForm.start" type="date" />
        </div>
        <div>
          <label class="label">结束日期</label>
          <input v-model="backtestForm.end" type="date" />
        </div>
      </div>
      <div class="form-grid">
        <div>
          <label class="label">买入策略</label>
          <select v-model="buyStrategyIdProxy" class="select">
            <option v-for="item in buyStrategies" :key="item.id" :value="item.id">
              {{ item.name }}
            </option>
          </select>
        </div>
        <div>
          <label class="label">卖出策略</label>
          <select v-model="sellStrategyIdProxy" class="select">
            <option v-for="item in sellStrategies" :key="item.id" :value="item.id">
              {{ item.name }}
            </option>
          </select>
        </div>
        <div v-for="param in (activeBuyStrategy?.params || [])" :key="`buy-${param.key}`">
          <label class="label">{{ param.label }}</label>
          <input
            v-if="param.type !== 'bool'"
            v-model.number="buyStrategyParams[param.key]"
            :type="param.type === 'int' || param.type === 'float' ? 'number' : 'text'"
            :step="param.step || (param.type === 'int' ? 1 : 0.1)"
            :min="param.min"
            :max="param.max"
          />
          <label v-else class="toggle">
            <input type="checkbox" v-model="buyStrategyParams[param.key]" />
            <span>{{ param.label }}</span>
          </label>
        </div>
        <div v-for="param in (activeSellStrategy?.params || [])" :key="`sell-${param.key}`">
          <label class="label">{{ param.label }}</label>
          <input
            v-if="param.type !== 'bool'"
            v-model.number="sellStrategyParams[param.key]"
            :type="param.type === 'int' || param.type === 'float' ? 'number' : 'text'"
            :step="param.step || (param.type === 'int' ? 1 : 0.1)"
            :min="param.min"
            :max="param.max"
          />
          <label v-else class="toggle">
            <input type="checkbox" v-model="sellStrategyParams[param.key]" />
            <span>{{ param.label }}</span>
          </label>
        </div>
      </div>
      <div class="toolbar">
        <button class="btn-primary" @click="runBacktest" :disabled="actionsBusy">启动回测</button>
        <button class="btn-secondary" @click="runStockSelect" :disabled="actionsBusy">独立选股</button>
        <button class="btn-secondary" @click="runClosedLoop" :disabled="actionsBusy">一键闭环</button>
        <span class="muted">回测完成后可导出 CSV</span>
      </div>
      <div v-if="backtestSummary" class="result-card">
        <h3>回测摘要</h3>
        <div class="result-grid">
          <div>
            <p class="muted">订单行数</p>
            <p class="metric-value">{{ backtestSummary.orders_rows }}</p>
          </div>
          <div>
            <p class="muted">行为行数</p>
            <p class="metric-value">{{ backtestSummary.actions_rows }}</p>
          </div>
          <div>
            <p class="muted">基准</p>
            <p class="metric-value">{{ backtestSummary.benchmark || '-' }}</p>
          </div>
        </div>
      </div>
      <div v-if="backtestTopSymbols?.length" class="result-card">
        <h3>股票回测榜单（前 {{ backtestTopSymbols.length }}）</h3>
        <div class="table-wrap">
          <table class="table">
            <thead>
              <tr>
                <th>#</th>
                <th>标的</th>
                <th>胜率</th>
                <th>累计盈亏</th>
                <th>已平仓</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in backtestTopSymbols" :key="`backtest-symbol-${row.rank}-${row.symbol}`">
                <td class="mono">{{ row.rank }}</td>
                <td class="mono">{{ row.symbol }}</td>
                <td class="mono">{{ formatNumber(row.win_rate, 1) }}%</td>
                <td class="mono">{{ formatNumber(row.profit_sum) }}</td>
                <td class="mono">{{ row.closed_orders }}</td>
                <td>
                  <button class="btn-secondary" @click="applySymbolToBacktest(row.symbol)">用于回测</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <div v-if="backtestActionableCandidates?.length" class="result-card">
        <h3>近期可操作候选（回测）</h3>
        <div class="table-wrap">
          <table class="table">
            <thead>
              <tr>
                <th>标的</th>
                <th>建议动作</th>
                <th>建议仓位</th>
                <th>胜率</th>
                <th>止损/止盈</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in backtestActionableCandidates" :key="`backtest-action-${row.symbol}`">
                <td class="mono">{{ row.symbol }}</td>
                <td>{{ row.action }}</td>
                <td class="mono">{{ row.position_range }}</td>
                <td class="mono">{{ formatNumber(row.win_rate, 1) }}%</td>
                <td class="mono">{{ formatNumber(row.stop_loss) }} / {{ formatNumber(row.take_profit) }}</td>
                <td class="table-actions">
                  <button class="btn-secondary" @click="applySymbolToBacktest(row.symbol)">用于回测</button>
                  <button class="btn-secondary" @click="applySymbolToAnalysis(row.symbol)">量化分析</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <div v-if="stockSelectSummary" class="result-card">
        <h3>独立选股结果</h3>
        <div class="result-grid">
          <div>
            <p class="muted">请求标的数</p>
            <p class="metric-value">{{ stockSelectSummary.requested_symbols ?? '-' }}</p>
          </div>
          <div>
            <p class="muted">有效标的数</p>
            <p class="metric-value">{{ stockSelectSummary.available_symbols ?? '-' }}</p>
          </div>
          <div>
            <p class="muted">已评估标的数</p>
            <p class="metric-value">{{ stockSelectSummary.evaluated_symbols ?? '-' }}</p>
          </div>
          <div>
            <p class="muted">推荐模式</p>
            <p class="metric-value">{{ stockSelectRecommendation?.mode || '-' }}</p>
          </div>
        </div>
        <p class="muted" v-if="stockSelectRecommendation?.notes?.length">
          {{ stockSelectRecommendation.notes.join('；') }}
        </p>
        <p class="muted" v-if="stockSelectDiagnostics">
          评估上限 {{ stockSelectDiagnostics.eval_limit ?? '-' }}，最小K线 {{ stockSelectDiagnostics.min_kline_rows ?? '-' }}
        </p>
      </div>
      <div v-if="stockSelectTopSymbols?.length" class="result-card">
        <h3>独立选股 Top {{ stockSelectTopSymbols.length }}</h3>
        <div class="table-wrap">
          <table class="table">
            <thead>
              <tr>
                <th>#</th>
                <th>标的</th>
                <th>胜率</th>
                <th>累计盈亏</th>
                <th>夏普</th>
                <th>回撤</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in stockSelectTopSymbols" :key="`select-${row.rank}-${row.symbol}`">
                <td class="mono">{{ row.rank }}</td>
                <td class="mono">{{ row.symbol }}</td>
                <td class="mono">{{ formatNumber(row.win_rate, 1) }}%</td>
                <td class="mono">{{ formatNumber(row.profit_sum) }}</td>
                <td class="mono">{{ formatNumber(row.sharpe, 2) }}</td>
                <td class="mono">{{ formatNumber(row.max_drawdown, 3) }}</td>
                <td class="table-actions">
                  <button class="btn-secondary" @click="applySymbolToBacktest(row.symbol)">用于回测</button>
                  <button class="btn-secondary" @click="applySymbolToAnalysis(row.symbol)">量化分析</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <div v-if="stockSelectActionableCandidates?.length" class="result-card">
        <h3>独立选股可操作候选</h3>
        <div class="table-wrap">
          <table class="table">
            <thead>
              <tr>
                <th>标的</th>
                <th>建议动作</th>
                <th>建议仓位</th>
                <th>止损/止盈</th>
                <th>原因</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in stockSelectActionableCandidates" :key="`select-action-${row.symbol}`">
                <td class="mono">{{ row.symbol }}</td>
                <td>{{ row.action }}</td>
                <td class="mono">{{ row.position_range }}</td>
                <td class="mono">{{ formatNumber(row.stop_loss) }} / {{ formatNumber(row.take_profit) }}</td>
                <td>{{ row.reason }}</td>
                <td class="table-actions">
                  <button class="btn-secondary" @click="applySymbolToBacktest(row.symbol)">用于回测</button>
                  <button class="btn-secondary" @click="applySymbolToAnalysis(row.symbol)">量化分析</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <div v-if="showBacktestVisual" class="result-card backtest-visual trading-stage">
        <h3>回测可视化</h3>
        <div class="result-grid" v-if="backtestTradeStats">
          <div>
            <p class="muted">交易次数</p>
            <p class="metric-value">{{ backtestTradeStats.total }}</p>
          </div>
          <div>
            <p class="muted">胜率</p>
            <p class="metric-value">{{ formatNumber(backtestTradeStats.winRate, 1) }}%</p>
          </div>
          <div>
            <p class="muted">总盈利</p>
            <p class="metric-value">{{ formatNumber(backtestTradeStats.totalProfit, 2) }}</p>
          </div>
          <div>
            <p class="muted">单笔均值</p>
            <p class="metric-value">{{ formatNumber(backtestTradeStats.avgProfit, 2) }}</p>
          </div>
        </div>
        <p v-else class="muted">暂无交易明细，建议扩大回测区间或调整买入周期。</p>
        <div class="toolbar">
          <label class="label">展示标的</label>
          <select v-model="chartSymbolProxy" class="select">
            <option v-for="symbol in backtestSymbols" :key="symbol" :value="symbol">
              {{ symbol }}
            </option>
          </select>
          <label class="label">订单筛选</label>
          <select v-model="orderFilterProxy" class="select">
            <option value="all">全部</option>
            <option value="win">盈利</option>
            <option value="loss">亏损</option>
            <option value="hold">持仓</option>
          </select>
          <label class="label">选中订单</label>
          <select v-model="selectedOrderKeyProxy" class="select">
            <option value="">未选择</option>
            <option v-for="order in filteredOrders" :key="orderKey(order)" :value="orderKey(order)">
              {{ order.symbol }} · {{ formatKlineDate(order.buy_date) }} · {{ formatNumber(order.buy_price) }}
            </option>
          </select>
          <label class="label">显示区间</label>
          <input v-model.number="chartWindow.size" type="range" min="60" max="360" step="20" />
          <span class="muted">最近 {{ chartWindow.size }} 根</span>
          <button class="btn-secondary" @click="shiftWindow(1)">更早</button>
          <button class="btn-secondary" @click="shiftWindow(-1)">更晚</button>
          <label class="toggle">
            <input type="checkbox" v-model="showStopLinesProxy" />
            <span>止损/止盈线</span>
          </label>
          <button class="btn-secondary" @click="loadKlineChart" :disabled="klineLoading">
            {{ klineLoading ? '加载中' : '加载K线' }}
          </button>
          <span class="muted">上三角为买入，下三角为卖出</span>
        </div>
        <p v-if="klineError" class="error">{{ klineError }}</p>
        <div class="kline-chart" :ref="setKlineContainer">
          <div v-if="hoverInfo" class="kline-tooltip">
            <div class="mono">日期 {{ hoverInfo.date }}</div>
            <div class="mono">开 {{ formatNumber(hoverInfo.open) }}</div>
            <div class="mono">高 {{ formatNumber(hoverInfo.high) }}</div>
            <div class="mono">低 {{ formatNumber(hoverInfo.low) }}</div>
            <div class="mono">收 {{ formatNumber(hoverInfo.close) }}</div>
            <div class="mono">量 {{ hoverInfo.volume ?? '-' }}</div>
          </div>
          <p v-if="klineLoading" class="muted">K线加载中…</p>
          <p v-else-if="!klineData.length" class="muted">请点击“加载K线”查看图表</p>
        </div>
        <p class="muted">收益曲线（累计盈亏）</p>
        <div class="equity-chart" :ref="setEquityContainer">
          <p v-if="!equityData.length" class="muted">暂无收益曲线</p>
        </div>
        <div v-if="operationSuggestion" class="result-card advice-card">
          <h3>当日操作建议</h3>
          <div class="toolbar advice-profile-toolbar">
            <label class="label">风险模板</label>
            <select v-model="adviceProfileProxy" class="select">
              <option v-for="item in adviceProfileOptions" :key="item.key" :value="item.key">
                {{ item.label }}
              </option>
            </select>
            <span class="muted">可手动调整仓位、建仓比例、止盈比例、移动止损</span>
          </div>
          <div v-if="adviceTemplate" class="info-card advice-template-card">
            <p class="muted">模板参数（当前档位）</p>
            <div class="form-grid">
              <div>
                <label class="label">强信号买入仓位</label>
                <input v-model.number="adviceTemplate.position.buyHigh" type="number" min="0" max="1" step="0.05" />
              </div>
              <div>
                <label class="label">中信号买入仓位</label>
                <input v-model.number="adviceTemplate.position.buyMid" type="number" min="0" max="1" step="0.05" />
              </div>
              <div>
                <label class="label">观察买入(强)仓位</label>
                <input
                  v-model.number="adviceTemplate.position.buyWatchHigh"
                  type="number"
                  min="0"
                  max="1"
                  step="0.05"
                />
              </div>
              <div>
                <label class="label">观察买入(中)仓位</label>
                <input
                  v-model.number="adviceTemplate.position.buyWatchMid"
                  type="number"
                  min="0"
                  max="1"
                  step="0.05"
                />
              </div>
              <div>
                <label class="label">减仓比例</label>
                <input v-model.number="adviceTemplate.position.reduce" type="number" min="0" max="1" step="0.05" />
              </div>
              <div>
                <label class="label">观望仓位</label>
                <input v-model.number="adviceTemplate.position.watch" type="number" min="0" max="1" step="0.05" />
              </div>
              <div>
                <label class="label">建仓一批比例</label>
                <input v-model.number="adviceTemplate.entry.first" type="number" min="0" max="1" step="0.05" />
              </div>
              <div>
                <label class="label">回踩加仓比例</label>
                <input v-model.number="adviceTemplate.entry.pullback" type="number" min="0" max="1" step="0.05" />
              </div>
              <div>
                <label class="label">突破加仓比例</label>
                <input v-model.number="adviceTemplate.entry.breakout" type="number" min="0" max="1" step="0.05" />
              </div>
              <div>
                <label class="label">止盈一批比例</label>
                <input v-model.number="adviceTemplate.takeProfit.tp1" type="number" min="0" max="1" step="0.05" />
              </div>
              <div>
                <label class="label">止盈二批比例</label>
                <input v-model.number="adviceTemplate.takeProfit.tp2" type="number" min="0" max="1" step="0.05" />
              </div>
              <div>
                <label class="label">止盈三批比例</label>
                <input v-model.number="adviceTemplate.takeProfit.tp3" type="number" min="0" max="1" step="0.05" />
              </div>
              <div>
                <label class="label">移动止损比例</label>
                <input v-model.number="adviceTemplate.trailStopPct" type="number" min="0" max="1" step="0.01" />
              </div>
            </div>
          </div>
          <div class="result-grid">
            <div>
              <p class="muted">建议动作</p>
              <p class="metric-value">{{ operationSuggestion.actionText }}</p>
            </div>
            <div>
              <p class="muted">信号强度</p>
              <p class="metric-value">{{ operationSuggestion.confidence }}</p>
            </div>
            <div>
              <p class="muted">最新收盘</p>
              <p class="metric-value">{{ formatNumber(operationSuggestion.lastClose) }}</p>
            </div>
            <div>
              <p class="muted">建议仓位</p>
              <p class="metric-value">{{ operationSuggestion.positionText }}</p>
              <p class="muted">模板：{{ operationSuggestion.profileLabel || operationSuggestion.profileKey }}</p>
            </div>
            <div>
              <p class="muted">止损 / 止盈</p>
              <p class="metric-value">
                {{ formatNumber(operationSuggestion.stopLoss) }} / {{ formatNumber(operationSuggestion.takeProfit) }}
              </p>
            </div>
          </div>
          <p class="panel-note">{{ operationSuggestion.reason }}</p>
          <p class="muted" v-if="operationSuggestion.hint">{{ operationSuggestion.hint }}</p>
          <div class="info-card" v-if="operationSuggestion.tranchePlan?.length">
            <p class="muted">建仓规则</p>
            <div class="table-wrap">
              <table class="table">
                <thead>
                  <tr>
                    <th>批次</th>
                    <th>仓位占比</th>
                    <th>触发条件</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in operationSuggestion.tranchePlan" :key="`entry-${row.label}`">
                    <td>{{ row.label }}</td>
                    <td class="mono">{{ formatNumber((row.ratio || 0) * 100, 0) }}%</td>
                    <td>{{ row.trigger }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
          <div class="info-card" v-if="operationSuggestion.takeProfitPlan?.length">
            <p class="muted">分批止盈</p>
            <div class="table-wrap">
              <table class="table">
                <thead>
                  <tr>
                    <th>批次</th>
                    <th>减仓占比</th>
                    <th>目标价</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in operationSuggestion.takeProfitPlan" :key="`tp-${row.label}`">
                    <td>{{ row.label }}</td>
                    <td class="mono">{{ formatNumber((row.ratio || 0) * 100, 0) }}%</td>
                    <td class="mono">{{ formatNumber(row.target) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p class="muted">
              硬止损：{{ formatNumber(operationSuggestion.riskRule?.hardStop) }}，
              移动止损：{{ formatNumber((operationSuggestion.riskRule?.trailStopPct || 0) * 100, 0) }}%
            </p>
          </div>
        </div>
        <div v-if="filteredOrders.length" class="result-card">
          <h3>交易明细</h3>
          <div class="table-wrap">
            <table class="table">
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>买入日期</th>
                  <th>买入价</th>
                  <th>卖出日期</th>
                  <th>卖出价</th>
                  <th>止损价</th>
                  <th>止盈价</th>
                  <th>盈亏</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="order in pagedOrders"
                  :key="orderKey(order)"
                  :class="{ 'is-selected': orderKey(order) === selectedOrderKeyProxy }"
                  @click="selectOrder(order)"
                >
                  <td class="mono">{{ order.symbol }}</td>
                  <td class="mono">{{ formatKlineDate(order.buy_date) }}</td>
                  <td class="mono">{{ formatNumber(order.buy_price) }}</td>
                  <td class="mono">{{ formatKlineDate(order.sell_date) }}</td>
                  <td class="mono">{{ formatNumber(order.sell_price) }}</td>
                  <td class="mono">{{ formatNumber(order.stop_loss_price) }}</td>
                  <td class="mono">{{ formatNumber(order.stop_win_price) }}</td>
                  <td class="mono">{{ formatNumber(resolveOrderProfit(order)) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="pager">
            <span class="muted">共 {{ filteredOrders.length }} 条</span>
            <div class="pager-controls">
              <button
                class="btn-secondary"
                @click="orderPageProxy = Math.max(1, orderPageProxy - 1)"
                :disabled="orderPageProxy <= 1"
              >
                上一页
              </button>
              <span class="mono">{{ orderPageProxy }} / {{ orderTotalPages }}</span>
              <button
                class="btn-secondary"
                @click="orderPageProxy = Math.min(orderTotalPages, orderPageProxy + 1)"
                :disabled="orderPageProxy >= orderTotalPages"
              >
                下一页
              </button>
            </div>
            <div class="pager-size">
              <span class="muted">每页</span>
              <select v-model.number="orderPageSizeProxy" class="select">
                <option :value="10">10</option>
                <option :value="20">20</option>
                <option :value="50">50</option>
              </select>
            </div>
          </div>
          <p class="muted">点击行可定位到K线标记。</p>
        </div>
      </div>
    </div>

    <div class="panel strategy-side">
      <header class="panel-title">
        <div>
          <h2>参数交叉验证</h2>
          <p class="muted">多参数组合网格寻优。</p>
        </div>
        <span class="pill">寻优</span>
      </header>
      <p class="panel-note">结果里的最佳参数可一键回填到回测；寻优范围越大运行越久。</p>
      <div class="toolbar strategy-merge-toggle">
        <label class="toggle">
          <input type="checkbox" v-model="gridUseBacktestBaseProxy" />
          <span>复用回测基础参数（市场、标的、资金、日期、年数）</span>
        </label>
      </div>
      <div class="toolbar strategy-merge-toggle">
        <label class="toggle">
          <input type="checkbox" v-model="gridExploreAllStrategiesProxy" />
          <span>自动探索全部买卖策略组合（用于筛选最优组合）</span>
        </label>
      </div>
      <div v-if="gridUseBacktestBaseProxy" class="selection strategy-shared-summary">
        <div class="selection-head">
          <strong>当前共用回测基础参数</strong>
        </div>
        <div class="result-grid">
          <div>
            <p class="muted">市场</p>
            <p class="mono">{{ backtestForm.market || '-' }}</p>
          </div>
          <div>
            <p class="muted">标的</p>
            <p class="mono">{{ backtestForm.symbols || '-' }}</p>
          </div>
          <div>
            <p class="muted">初始资金</p>
            <p class="mono">{{ formatNumber(backtestForm.cash, 0) }}</p>
          </div>
          <div>
            <p class="muted">开始/结束</p>
            <p class="mono">{{ backtestForm.start || '-' }} / {{ backtestForm.end || '-' }}</p>
          </div>
          <div>
            <p class="muted">回溯年数</p>
            <p class="mono">{{ backtestForm.n_folds ?? '-' }}</p>
          </div>
        </div>
      </div>
      <div class="form-grid">
        <div v-if="!gridUseBacktestBaseProxy">
          <label class="label">标的列表</label>
          <input v-model="gridForm.symbols" placeholder="sh600036, sz000001" />
        </div>
        <div v-if="!gridUseBacktestBaseProxy">
          <label class="label">初始资金</label>
          <input v-model.number="gridForm.cash" type="number" min="1000" />
        </div>
        <div v-if="!gridUseBacktestBaseProxy">
          <label class="label">开始日期</label>
          <input v-model="gridForm.start" type="date" />
        </div>
        <div v-if="!gridUseBacktestBaseProxy">
          <label class="label">结束日期</label>
          <input v-model="gridForm.end" type="date" />
        </div>
        <div>
          <label class="label">买入策略</label>
          <select v-model="buyStrategyIdProxy" class="select">
            <option v-for="item in buyStrategies" :key="item.id" :value="item.id">
              {{ item.name }}
            </option>
          </select>
        </div>
        <div>
          <label class="label">卖出策略</label>
          <select v-model="sellStrategyIdProxy" class="select">
            <option v-for="item in sellStrategies" :key="item.id" :value="item.id">
              {{ item.name }}
            </option>
          </select>
        </div>
        <div>
          <label class="label">买入策略列表</label>
          <input v-model="gridForm.buy_strategies" placeholder="breakout, macd_cross" />
        </div>
        <div>
          <label class="label">卖出策略列表</label>
          <input v-model="gridForm.sell_strategies" placeholder="atr_stop, macd_cross" />
        </div>
        <div v-for="param in (activeBuyStrategy?.params || [])" :key="`grid-buy-${param.key}`">
          <label class="label">{{ param.label }}列表</label>
          <input
            v-model="gridBuyParamLists[param.key]"
            type="text"
            :placeholder="param.type === 'bool' ? 'true,false' : '20, 42, 60'"
          />
        </div>
        <div v-for="param in (activeSellStrategy?.params || [])" :key="`grid-sell-${param.key}`">
          <label class="label">{{ param.label }}列表</label>
          <input
            v-model="gridSellParamLists[param.key]"
            type="text"
            :placeholder="param.type === 'bool' ? 'true,false' : '0.5, 1.0'"
          />
        </div>
        <div>
          <label class="label">验证模式</label>
          <select v-model="gridForm.validation_mode" class="select">
            <option value="none">不启用</option>
            <option value="holdout">训练/验证切分</option>
            <option value="walk_forward">滚动验证</option>
          </select>
        </div>
        <div>
          <label class="label">训练比例</label>
          <input v-model.number="gridForm.train_ratio" type="number" min="0.5" max="0.9" step="0.05" />
        </div>
        <div v-if="gridForm.validation_mode === 'walk_forward'">
          <label class="label">滚动窗口天数</label>
          <input v-model.number="gridForm.walk_forward_days" type="number" min="60" />
        </div>
        <div v-if="gridForm.validation_mode === 'walk_forward'">
          <label class="label">滚动步长天数</label>
          <input v-model.number="gridForm.walk_forward_step_days" type="number" min="30" />
        </div>
        <div>
          <label class="label">最大运行次数</label>
          <input v-model.number="gridForm.max_runs" type="number" min="1" />
        </div>
        <div>
          <label class="label">排序指标</label>
          <select v-model="gridForm.ranking_metric" class="select">
            <option value="profit">累计收益优先</option>
            <option value="win_rate">胜率优先</option>
            <option value="sharpe">夏普优先</option>
            <option value="annual_return">年化收益优先</option>
            <option value="custom">自定义指标</option>
          </select>
        </div>
        <div v-if="gridForm.ranking_metric === 'custom'">
          <label class="label">自定义: 收益权重</label>
          <input v-model.number="gridForm.ranking_weights.profit" type="number" min="0" step="0.1" />
        </div>
        <div v-if="gridForm.ranking_metric === 'custom'">
          <label class="label">自定义: 胜率权重</label>
          <input v-model.number="gridForm.ranking_weights.win_rate" type="number" min="0" step="0.1" />
        </div>
        <div v-if="gridForm.ranking_metric === 'custom'">
          <label class="label">自定义: 夏普权重</label>
          <input v-model.number="gridForm.ranking_weights.sharpe" type="number" min="0" step="0.1" />
        </div>
        <div v-if="gridForm.ranking_metric === 'custom'">
          <label class="label">自定义: 年化权重</label>
          <input v-model.number="gridForm.ranking_weights.annual_return" type="number" min="0" step="0.1" />
        </div>
        <div v-if="gridForm.ranking_metric === 'custom'">
          <label class="label">自定义: 回撤惩罚</label>
          <input v-model.number="gridForm.ranking_weights.drawdown" type="number" min="0" step="0.1" />
        </div>
        <div>
          <label class="label">前N股票数量</label>
          <input v-model.number="gridForm.symbol_top_n" type="number" min="1" max="50" />
        </div>
        <div>
          <label class="label">股票评估上限</label>
          <input v-model.number="gridForm.symbol_eval_limit" type="number" min="10" max="500" />
        </div>
        <div v-if="!gridUseBacktestBaseProxy">
          <label class="label">回溯年数</label>
          <input v-model.number="gridForm.n_folds" type="number" min="1" />
        </div>
      </div>
      <div class="toolbar">
        <button class="btn-secondary" @click="runGridSearch" :disabled="actionsBusy">启动寻优</button>
        <span class="muted">输出最佳参数组合</span>
      </div>
      <div v-if="gridSummary" class="result-card">
        <h3>最佳组合</h3>
        <div class="toolbar">
          <button class="btn-secondary" @click="applyGridToBacktest">应用到回测参数</button>
          <button
            v-if="gridNextParamSuggestions"
            class="btn-secondary"
            @click="applyGridNextSuggestions"
          >
            生成下一轮参数组合
          </button>
          <span class="muted">自动填充买入周期/止损/止盈</span>
        </div>
        <div v-if="gridDiagnostics" class="info-card">
          <div class="result-grid">
            <div>
              <p class="muted">候选组合</p>
              <p class="mono">{{ gridDiagnostics.candidate_runs ?? '-' }}</p>
            </div>
            <div>
              <p class="muted">已测试组合</p>
              <p class="mono">{{ gridDiagnostics.tested_runs ?? '-' }}</p>
            </div>
            <div>
              <p class="muted">是否完整测试</p>
              <p class="mono">{{ gridDiagnostics.fully_tested ? '是' : '否' }}</p>
            </div>
            <div>
              <p class="muted">是否被截断</p>
              <p class="mono">{{ gridDiagnostics.truncated ? '是' : '否' }}</p>
            </div>
            <div>
              <p class="muted">报错组合数</p>
              <p class="mono">{{ gridDiagnostics.error_count ?? 0 }}</p>
            </div>
          </div>
        </div>
        <div v-if="gridRecommendation" class="info-card">
          <p class="muted">推荐操作模式</p>
          <p class="metric-value">{{ gridRecommendation.mode || '-' }}</p>
          <p class="muted">
            建议策略：{{ gridRecommendation.buy_strategy || '-' }} / {{ gridRecommendation.sell_strategy || '-' }}
          </p>
          <p class="muted">建议仓位区间：{{ gridRecommendation.position_range || '-' }}</p>
          <p class="muted" v-if="gridRecommendation.notes?.length">
            {{ gridRecommendation.notes.join('；') }}
          </p>
        </div>
        <div v-if="gridErrors?.length" class="info-card">
          <p class="muted">寻优报错样本（最多展示 {{ gridErrors.length }} 条）</p>
          <div class="code-wrap">
            <pre class="code">{{ JSON.stringify(gridErrors, null, 2) }}</pre>
          </div>
        </div>
        <pre class="code">{{ gridSummaryText }}</pre>
      </div>
      <div v-if="gridTopSymbols?.length" class="result-card">
        <h3>最佳组合股票榜单（前 {{ gridTopSymbols.length }}）</h3>
        <div class="table-wrap">
          <table class="table">
            <thead>
              <tr>
                <th>#</th>
                <th>标的</th>
                <th>胜率</th>
                <th>累计盈亏</th>
                <th>夏普</th>
                <th>回撤</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in gridTopSymbols" :key="`grid-symbol-${row.rank}-${row.symbol}`">
                <td class="mono">{{ row.rank }}</td>
                <td class="mono">{{ row.symbol }}</td>
                <td class="mono">{{ formatNumber(row.win_rate, 1) }}%</td>
                <td class="mono">{{ formatNumber(row.profit_sum) }}</td>
                <td class="mono">{{ formatNumber(row.sharpe, 2) }}</td>
                <td class="mono">{{ formatNumber(row.max_drawdown, 3) }}</td>
                <td>
                  <button class="btn-secondary" @click="applySymbolToBacktest(row.symbol)">用于回测</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <div v-if="gridActionableCandidates?.length" class="result-card">
        <h3>近期可操作候选（最佳组合）</h3>
        <div class="table-wrap">
          <table class="table">
            <thead>
              <tr>
                <th>标的</th>
                <th>建议动作</th>
                <th>建议仓位</th>
                <th>胜率</th>
                <th>止损/止盈</th>
                <th>原因</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in gridActionableCandidates" :key="`grid-action-${row.symbol}`">
                <td class="mono">{{ row.symbol }}</td>
                <td>{{ row.action }}</td>
                <td class="mono">{{ row.position_range }}</td>
                <td class="mono">{{ formatNumber(row.win_rate, 1) }}%</td>
                <td class="mono">{{ formatNumber(row.stop_loss) }} / {{ formatNumber(row.take_profit) }}</td>
                <td>{{ row.reason }}</td>
                <td class="table-actions">
                  <button class="btn-secondary" @click="applySymbolToBacktest(row.symbol)">用于回测</button>
                  <button class="btn-secondary" @click="applySymbolToAnalysis(row.symbol)">量化分析</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <div v-if="gridTopRuns?.length" class="result-card">
        <h3>策略组合榜单（前 {{ gridTopRuns.length }}）</h3>
        <div class="table-wrap">
          <table class="table">
            <thead>
              <tr>
                <th>#</th>
                <th>买入</th>
                <th>卖出</th>
                <th>收益</th>
                <th>胜率</th>
                <th>回撤</th>
                <th>评分</th>
                <th>参数</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in gridTopRuns" :key="`grid-top-${row.rank}`">
                <td class="mono">{{ row.rank }}</td>
                <td class="mono">{{ row.buy_strategy }}</td>
                <td class="mono">{{ row.sell_strategy }}</td>
                <td class="mono">{{ formatNumber(metricOf(row, 'profit_sum')) }}</td>
                <td class="mono">{{ formatNumber(metricOf(row, 'win_rate'), 1) }}%</td>
                <td class="mono">{{ formatNumber(metricOf(row, 'max_drawdown'), 3) }}</td>
                <td class="mono">{{ formatNumber(row.score, 2) }}</td>
                <td class="mono params-cell">{{ paramsBrief(row) }}</td>
                <td>
                  <button class="btn-secondary" @click="applyGridRunToBacktest(row)">应用</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  active: Boolean,
  backtestForm: Object,
  gridForm: Object,
  gridUseBacktestBase: Boolean,
  gridExploreAllStrategies: Boolean,
  buyStrategies: Array,
  sellStrategies: Array,
  activeBuyStrategy: Object,
  activeSellStrategy: Object,
  gridBuyParamLists: Object,
  gridSellParamLists: Object,
  buyStrategyId: String,
  sellStrategyId: String,
  buyStrategyParams: Object,
  sellStrategyParams: Object,
  runBacktest: Function,
  runStockSelect: Function,
  runClosedLoop: Function,
  actionsBusy: Boolean,
  backtestSummary: Object,
  backtestTopSymbols: Array,
  backtestActionableCandidates: Array,
  stockSelectSummary: Object,
  stockSelectDiagnostics: Object,
  stockSelectTopSymbols: Array,
  stockSelectActionableCandidates: Array,
  stockSelectRecommendation: Object,
  backtestTradeStats: Object,
  backtestSymbols: Array,
  chartSymbol: String,
  orderFilter: String,
  selectedOrderKey: String,
  showStopLines: Boolean,
  chartWindow: Object,
  klineLoading: Boolean,
  klineError: String,
  hoverInfo: Object,
  klineData: Array,
  equityData: Array,
  operationSuggestion: Object,
  adviceProfile: String,
  adviceTemplates: Object,
  filteredOrders: Array,
  pagedOrders: Array,
  orderPage: Number,
  orderPageSize: Number,
  orderTotalPages: Number,
  orderKey: Function,
  formatNumber: Function,
  formatKlineDate: Function,
  resolveOrderProfit: Function,
  selectOrder: Function,
  shiftWindow: Function,
  loadKlineChart: Function,
  showBacktestVisual: Boolean,
  runGridSearch: Function,
  gridSummary: Object,
  gridDiagnostics: Object,
  gridTopSymbols: Array,
  gridActionableCandidates: Array,
  gridRecommendation: Object,
  gridErrors: Array,
  gridNextParamSuggestions: Object,
  gridTopRuns: Array,
  gridSummaryText: String,
  applyGridToBacktest: Function,
  applyGridRunToBacktest: Function,
  applyGridNextSuggestions: Function,
  applySymbolToBacktest: Function,
  applySymbolToAnalysis: Function,
  setKlineContainer: Function,
  setEquityContainer: Function
})

const emit = defineEmits([
  'update:buyStrategyId',
  'update:sellStrategyId',
  'update:adviceProfile',
  'update:gridUseBacktestBase',
  'update:gridExploreAllStrategies',
  'update:chartSymbol',
  'update:orderFilter',
  'update:selectedOrderKey',
  'update:showStopLines',
  'update:orderPage',
  'update:orderPageSize'
])

const buyStrategyIdProxy = computed({
  get: () => props.buyStrategyId,
  set: (value) => emit('update:buyStrategyId', value)
})

const sellStrategyIdProxy = computed({
  get: () => props.sellStrategyId,
  set: (value) => emit('update:sellStrategyId', value)
})

const chartSymbolProxy = computed({
  get: () => props.chartSymbol,
  set: (value) => emit('update:chartSymbol', value)
})

const adviceProfileProxy = computed({
  get: () => props.adviceProfile || 'balanced',
  set: (value) => emit('update:adviceProfile', value)
})

const gridUseBacktestBaseProxy = computed({
  get: () => !!props.gridUseBacktestBase,
  set: (value) => emit('update:gridUseBacktestBase', value)
})

const gridExploreAllStrategiesProxy = computed({
  get: () => !!props.gridExploreAllStrategies,
  set: (value) => emit('update:gridExploreAllStrategies', value)
})

const orderFilterProxy = computed({
  get: () => props.orderFilter,
  set: (value) => emit('update:orderFilter', value)
})

const selectedOrderKeyProxy = computed({
  get: () => props.selectedOrderKey,
  set: (value) => emit('update:selectedOrderKey', value)
})

const showStopLinesProxy = computed({
  get: () => props.showStopLines,
  set: (value) => emit('update:showStopLines', value)
})

const orderPageProxy = computed({
  get: () => props.orderPage ?? 1,
  set: (value) => emit('update:orderPage', value)
})

const orderPageSizeProxy = computed({
  get: () => props.orderPageSize ?? 20,
  set: (value) => emit('update:orderPageSize', value)
})

const adviceProfileOptions = computed(() => {
  const templates = props.adviceTemplates || {}
  return Object.entries(templates).map(([key, template]) => ({
    key,
    label: template?.label || key
  }))
})

const adviceTemplate = computed(() => {
  const templates = props.adviceTemplates || {}
  return templates[adviceProfileProxy.value] || null
})

const metricOf = (row, key) => {
  if (!row) return null
  const validationValue = row[`validation_${key}`]
  if (validationValue !== undefined && validationValue !== null) return Number(validationValue)
  if (row[key] !== undefined && row[key] !== null) return Number(row[key])
  return null
}

const paramsBrief = (row) => {
  const buy = row?.buy_params ? Object.entries(row.buy_params).map(([k, v]) => `B.${k}:${v}`) : []
  const sell = row?.sell_params ? Object.entries(row.sell_params).map(([k, v]) => `S.${k}:${v}`) : []
  const merged = [...buy, ...sell]
  if (!merged.length) return '-'
  return merged.join(', ')
}
</script>

