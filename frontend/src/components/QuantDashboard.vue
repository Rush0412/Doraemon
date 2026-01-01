<template>
  <div class="quant-shell">
    <section class="hero">
      <div class="hero-head">
        <div>
          <p class="eyebrow">Doraemon Quant Suite</p>
          <h1>阿布量化控制台</h1>
          <p class="hero-sub">
            数据更新、回测、参数寻优与量化分析一体化视图。
          </p>
        </div>
        <div class="hero-actions">
          <button class="btn-ghost" @click="refreshJobs" :disabled="actionsBusy">刷新任务</button>
          <button class="btn-primary" @click="runVerify" :disabled="actionsBusy">环境验证</button>
        </div>
      </div>
      <div class="hero-metrics">
        <div class="metric-card">
          <p class="metric-label">任务总数</p>
          <p class="metric-value">{{ jobStats.total }}</p>
        </div>
        <div class="metric-card">
          <p class="metric-label">运行中</p>
          <p class="metric-value">{{ jobStats.running }}</p>
        </div>
        <div class="metric-card">
          <p class="metric-label">成功</p>
          <p class="metric-value">{{ jobStats.succeeded }}</p>
        </div>
        <div class="metric-card">
          <p class="metric-label">失败</p>
          <p class="metric-value">{{ jobStats.failed }}</p>
        </div>
      </div>
    </section>

    <section class="flow-nav">
      <div class="flow-track">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          :class="['flow-step', { active: activeTab === tab.id }]"
          @click="setTab(tab.id)"
        >
          <span class="flow-step-index">{{ tab.step }}</span>
          <span class="flow-step-title">{{ tab.title }}</span>
          <span class="flow-step-sub">{{ tab.subtitle }}</span>
        </button>
      </div>
      <div class="flow-context">
        <div>
          <p class="eyebrow">当前步骤</p>
          <h2>{{ activeTabMeta.title }}</h2>
          <p class="muted">{{ activeTabMeta.hint }}</p>
        </div>
        <div class="flow-actions">
          <button class="btn-secondary" @click="goPrev" :disabled="isFirstTab">上一步</button>
          <button class="btn-primary" @click="goNext" :disabled="isLastTab">下一步</button>
        </div>
      </div>
    </section>

    <section class="grid grid-2" v-show="activeTab === 'prepare'">
      <div class="panel glass">
        <header class="panel-title">
          <div>
            <h2>股票检索</h2>
            <p class="muted">检索股票代码、公司名称与交易所信息。</p>
          </div>
          <span class="pill">Symbols</span>
        </header>
        <p class="panel-note">建议先导入股票库，再检索并加入选股篮。选股篮会同步到更新、回测、寻优与分析。</p>
        <div class="form-grid">
          <div>
            <label class="label">市场</label>
            <select v-model="market" class="select">
              <option value="SH">SH (Shanghai)</option>
              <option value="SZ">SZ (Shenzhen)</option>
              <option value="300">300 (ChiNext)</option>
            </select>
          </div>
          <div>
            <label class="label">关键词</label>
            <input v-model="query" placeholder="symbol / 公司名 / 关键字" @keyup.enter="search" />
          </div>
          <div>
            <label class="label">类型</label>
            <select v-model="kind" class="select">
              <option value="stock">个股</option>
              <option value="index">指数</option>
              <option value="all">全部</option>
            </select>
          </div>
        </div>
        <div class="toolbar">
          <button class="btn-secondary" @click="search" :disabled="store.symbolsLoading">查询</button>
          <button class="btn-ghost" @click="importSymbols" :disabled="store.symbolsLoading">初始化当前市场</button>
          <button class="btn-ghost" @click="importAllSymbols" :disabled="store.symbolsLoading">导入全部A股</button>
          <button class="btn-ghost" @click="selectPage" :disabled="store.symbolsLoading">全选当前页</button>
          <button class="btn-ghost" @click="invertPage" :disabled="store.symbolsLoading">反选当前页</button>
          <span class="muted">{{ store.symbolsLoading ? '加载中…' : ' ' }}</span>
          <span v-if="selectedSymbols.length" class="muted">已选 {{ selectedSymbols.length }} 只</span>
        </div>
        <p v-if="store.symbolsError" class="error">{{ store.symbolsError }}</p>
        <div class="table-wrap" v-if="!store.symbolsLoading">
          <table class="table">
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Market</th>
                <th>Type</th>
                <th>Name</th>
                <th>Exchange</th>
                <th>Industry</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in store.symbols" :key="`${item.market}-${item.symbol}`">
                <td class="mono">{{ displaySymbol(item) }}</td>
                <td>{{ item.market }}</td>
                <td>{{ displayKind(item.kind) }}</td>
                <td>{{ item.name || '-' }}</td>
                <td>{{ item.exchange || '-' }}</td>
                <td>{{ item.industry || '-' }}</td>
                <td>
                  <button class="btn-ghost" @click="toggleSymbol(item.symbol)">
                    {{ isSelected(item.symbol) ? '移除' : '使用' }}
                  </button>
                </td>
              </tr>
              <tr v-if="store.symbols.length === 0">
                <td colspan="7" class="muted">暂无结果</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="selectedSymbols.length" class="selection">
          <div class="selection-head">
            <span class="pill">选股篮</span>
            <div class="selection-actions">
              <button class="btn-secondary" @click="clearSymbols">清空</button>
              <button class="btn-secondary" @click="saveSelection">保存组合</button>
            </div>
          </div>
          <div class="selection-load">
            <select v-model="selectedPortfolio" class="select">
              <option value="">加载组合</option>
              <option v-for="name in savedPortfolios" :key="name" :value="name">{{ name }}</option>
            </select>
            <button class="btn-secondary" @click="loadPortfolio" :disabled="!selectedPortfolio">加载</button>
            <button class="btn-secondary" @click="deletePortfolio" :disabled="!selectedPortfolio">删除</button>
          </div>
          <div class="selection-chips">
            <button v-for="symbol in selectedSymbols" :key="symbol" class="chip" @click="removeSymbol(symbol)">
              {{ symbol }}
              <span class="chip-close">×</span>
            </button>
          </div>
        </div>
        <div class="pager">
          <span class="muted">共 {{ store.total }} 条</span>
          <div class="pager-controls">
            <button class="btn-secondary" @click="changePage(store.page - 1)" :disabled="store.page <= 1">
              上一页
            </button>
            <span class="mono">{{ store.page }} / {{ totalPages }}</span>
            <button class="btn-secondary" @click="changePage(store.page + 1)" :disabled="store.page >= totalPages">
              下一页
            </button>
          </div>
          <div class="pager-size">
            <span class="muted">每页</span>
            <select v-model.number="pageSize" class="select" @change="applyPageSize">
              <option :value="20">20</option>
              <option :value="50">50</option>
              <option :value="100">100</option>
            </select>
          </div>
        </div>
      </div>

      <div class="panel glass">
        <header class="panel-title">
          <div>
            <h2>数据更新</h2>
            <p class="muted">批量更新市场数据缓存，建议先执行。</p>
          </div>
          <span class="pill">Update</span>
        </header>
        <p class="panel-note">更新会将K线写入PG；建议回溯至少 1 年。选股篮为空时将全量更新当前市场。</p>
        <div class="form-grid">
          <div>
            <label class="label">回溯年数</label>
            <input v-model.number="updateForm.n_folds" type="number" min="1" />
          </div>
          <div>
            <label class="label">并发数</label>
            <input v-model.number="updateForm.n_jobs" type="number" min="1" />
          </div>
          <div>
            <label class="label">开始日期</label>
            <input v-model="updateForm.start" type="date" />
          </div>
          <div>
            <label class="label">结束日期</label>
            <input v-model="updateForm.end" type="date" />
          </div>
          <div>
            <label class="label">执行模式</label>
            <select v-model="updateForm.how" class="select">
              <option value="thread">thread</option>
              <option value="process">process</option>
              <option value="main">main</option>
            </select>
          </div>
        </div>
        <div class="toolbar">
          <button class="btn-primary" @click="runKlUpdate" :disabled="actionsBusy">启动更新</button>
          <span class="muted">将创建异步任务</span>
        </div>
        <div class="update-targets">
          <p class="muted">更新标的</p>
          <div v-if="selectedSymbols.length" class="selection-chips">
            <button v-for="symbol in selectedSymbols" :key="symbol" class="chip" @click="removeSymbol(symbol)">
              {{ symbol }}
              <span class="chip-close">×</span>
            </button>
          </div>
          <p v-else class="muted">全量更新当前市场</p>
        </div>
        <div v-if="lastUpdateSummary" class="info-card">
          <p class="muted">最近更新</p>
          <div class="result-grid">
            <div>
              <p class="muted">更新标的</p>
              <p class="metric-value">{{ lastUpdateSummary.updated_symbols || 0 }}</p>
            </div>
            <div>
              <p class="muted">写入行数</p>
              <p class="metric-value">{{ lastUpdateSummary.rows || 0 }}</p>
            </div>
            <div>
              <p class="muted">缺失标的</p>
              <p class="metric-value">{{ (lastUpdateSummary.missing_symbols || []).length }}</p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="grid grid-2" v-show="activeTab === 'strategy'">
      <div class="panel">
        <header class="panel-title">
          <div>
            <h2>历史回测</h2>
            <p class="muted">执行经典买入突破 + ATR 止损止盈。</p>
          </div>
          <span class="pill">Backtest</span>
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
        <div class="toolbar">
          <button class="btn-primary" @click="runBacktest" :disabled="actionsBusy">启动回测</button>
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
        <div v-if="showBacktestVisual" class="result-card backtest-visual">
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
            <select v-model="chartSymbol" class="select">
              <option v-for="symbol in backtestSymbols" :key="symbol" :value="symbol">
                {{ symbol }}
              </option>
            </select>
            <label class="label">订单筛选</label>
            <select v-model="orderFilter" class="select">
              <option value="all">全部</option>
              <option value="win">盈利</option>
              <option value="loss">亏损</option>
              <option value="hold">持仓</option>
            </select>
            <label class="label">选中订单</label>
            <select v-model="selectedOrderKey" class="select" @change="syncSelectedOrder">
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
              <input type="checkbox" v-model="showStopLines" />
              <span>止损/止盈线</span>
            </label>
            <button class="btn-secondary" @click="loadKlineChart" :disabled="klineLoading">
              {{ klineLoading ? '加载中' : '加载K线' }}
            </button>
            <span class="muted">上三角为买入，下三角为卖出</span>
          </div>
          <p v-if="klineError" class="error">{{ klineError }}</p>
          <div class="kline-chart" ref="klineContainer">
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
          <div class="equity-chart" ref="equityContainer">
            <p v-if="!equityData.length" class="muted">暂无收益曲线</p>
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
                    v-for="order in filteredOrders.slice(0, 80)"
                    :key="orderKey(order)"
                    :class="{ 'is-selected': orderKey(order) === selectedOrderKey }"
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
            <p class="muted">默认展示前 80 条交易记录，点击行可定位到K线标记。</p>
          </div>
        </div>
      </div>

      <div class="panel">
        <header class="panel-title">
          <div>
            <h2>参数交叉验证</h2>
            <p class="muted">多参数组合网格寻优。</p>
          </div>
          <span class="pill">Grid</span>
        </header>
        <p class="panel-note">结果里的最佳参数可一键回填到回测；寻优范围越大运行越久。</p>
        <div class="form-grid">
          <div>
            <label class="label">标的列表</label>
            <input v-model="gridForm.symbols" placeholder="sh600036, sz000001" />
          </div>
          <div>
            <label class="label">初始资金</label>
            <input v-model.number="gridForm.cash" type="number" min="1000" />
          </div>
          <div>
            <label class="label">开始日期</label>
            <input v-model="gridForm.start" type="date" />
          </div>
          <div>
            <label class="label">结束日期</label>
            <input v-model="gridForm.end" type="date" />
          </div>
          <div>
            <label class="label">买入周期列表</label>
            <input v-model="gridForm.buy_xd_list" placeholder="20, 42, 60" />
          </div>
          <div>
            <label class="label">止损倍数列表</label>
            <input v-model="gridForm.stop_loss_n_list" placeholder="0.5, 1.0" />
          </div>
          <div>
            <label class="label">止盈倍数列表</label>
            <input v-model="gridForm.stop_win_n_list" placeholder="2.0, 3.0" />
          </div>
          <div>
            <label class="label">最大运行次数</label>
            <input v-model.number="gridForm.max_runs" type="number" min="1" />
          </div>
          <div>
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
            <span class="muted">自动填充买入周期/止损/止盈</span>
          </div>
          <pre class="code">{{ gridSummaryText }}</pre>
        </div>
      </div>
    </section>

    <section class="panel" v-show="activeTab === 'tools'">
      <header class="panel-title">
        <div>
          <h2>量化分析工具</h2>
          <p class="muted">阻力位、跳空、相关性与涨跌幅分析。</p>
        </div>
        <span class="pill">Tools</span>
      </header>
      <p class="panel-note">工具结果用于解释回测结论：趋势线判断支撑/阻力，相关性用于组合分散，跳空用于风险提示。</p>
      <div class="tool-layout">
        <div class="tool-form">
          <div class="form-grid">
            <div>
              <label class="label">工具类型</label>
              <select v-model="toolForm.tool" class="select">
                <option value="support_resistance">阻力/支撑位分析</option>
                <option value="jump_gap">跳空缺口分析</option>
                <option value="trend_speed">趋势敏感速度对比</option>
                <option value="shift_distance">位移路线比分析</option>
                <option value="regress">线性拟合分析</option>
                <option value="price_channel">价格通道分析</option>
                <option value="golden_ratio">黄金分割分析</option>
                <option value="correlation">相关性分析</option>
                <option value="distance">距离矩阵分析</option>
                <option value="p_change_stats">涨跌幅统计</option>
                <option value="date_week_wave">交易日波动分析</option>
                <option value="date_week_win">交易日涨跌概率</option>
                <option value="bcut_change_vc">涨跌区间分析(固定)</option>
                <option value="qcut_change_vc">涨跌区间分析(分位)</option>
                <option value="wave_change_rate">波动套利指标</option>
              </select>
            </div>
            <div>
              <label class="label">标的列表</label>
              <input v-model="toolForm.symbols" placeholder="sh600036, sz000001" />
            </div>
            <div>
              <label class="label">回溯年数</label>
              <input v-model.number="toolForm.n_folds" type="number" min="1" />
            </div>
            <div>
              <label class="label">返回行数</label>
              <input v-model.number="toolForm.limit" type="number" min="50" />
            </div>
            <div>
              <label class="label">开始日期</label>
              <input v-model="toolForm.start" type="date" />
            </div>
            <div>
              <label class="label">结束日期</label>
              <input v-model="toolForm.end" type="date" />
            </div>
          </div>

          <div class="tool-options" v-if="toolOptionMode === 'support'">
            <label class="label">趋势线范围</label>
            <select v-model="toolOptions.only_last" class="select">
              <option :value="true">仅最近趋势线</option>
              <option :value="false">全部趋势线</option>
            </select>
          </div>

          <div class="tool-options" v-if="toolOptionMode === 'jump'">
            <label class="label">跳空模式</label>
            <select v-model="toolOptions.mode" class="select">
              <option value="stats">统计模式</option>
              <option value="gap">缺口筛选</option>
              <option value="weighted">缺口加权筛选</option>
            </select>
            <div class="form-grid">
              <div>
                <label class="label">能量阈值</label>
                <input v-model.number="toolOptions.power_threshold" type="number" step="0.1" />
              </div>
              <div>
                <label class="label">跳空阈值因子</label>
                <input v-model.number="toolOptions.jump_diff_factor" type="number" step="0.1" />
              </div>
              <div>
                <label class="label">权重 A</label>
                <input v-model.number="toolOptions.weight_a" type="number" step="0.1" />
              </div>
              <div>
                <label class="label">权重 B</label>
                <input v-model.number="toolOptions.weight_b" type="number" step="0.1" />
              </div>
            </div>
          </div>

          <div class="tool-options" v-if="toolOptionMode === 'trend'">
            <div class="form-grid">
              <div>
                <label class="label">对比标的</label>
                <input v-model="toolOptions.benchmark" placeholder="usSPY / sh000001" />
              </div>
              <div>
                <label class="label">重采样周期</label>
                <input v-model.number="toolOptions.resample" type="number" min="1" />
              </div>
              <div>
                <label class="label">对比字段</label>
                <select v-model="toolOptions.speed_key" class="select">
                  <option value="close">close</option>
                  <option value="high">high</option>
                  <option value="low">low</option>
                  <option value="p_change">p_change</option>
                </select>
              </div>
            </div>
          </div>

          <div class="tool-options" v-if="toolOptionMode === 'shift'">
            <div class="form-grid">
              <div>
                <label class="label">步长</label>
                <input v-model.number="toolOptions.step_x" type="number" step="0.1" />
              </div>
              <div>
                <label class="label">位移模式</label>
                <select v-model="toolOptions.shift_mode" class="select">
                  <option value="close">close</option>
                  <option value="maxmin">max/min</option>
                  <option value="summaxmin">sum+max/min</option>
                </select>
              </div>
            </div>
          </div>

          <div class="tool-options" v-if="toolOptionMode === 'regress'">
            <label class="label">回归模式</label>
            <select v-model="toolOptions.regress_mode" class="select">
              <option value="best">最优拟合</option>
              <option value="least">最少拟合</option>
              <option value="channel">通道拟合</option>
            </select>
          </div>

          <div class="tool-options" v-if="toolOptionMode === 'corr'">
            <div class="form-grid">
              <div>
                <label class="label">相关系数</label>
                <select v-model="toolOptions.corr_type" class="select">
                  <option value="pears">pears</option>
                  <option value="sperm">sperm</option>
                  <option value="sign">sign</option>
                  <option value="rolling">rolling</option>
                </select>
              </div>
              <div>
                <label class="label">字段</label>
                <select v-model="toolOptions.field" class="select">
                  <option value="p_change">p_change</option>
                  <option value="close">close</option>
                </select>
              </div>
            </div>
          </div>

          <div class="tool-options" v-if="toolOptionMode === 'distance'">
            <div class="form-grid">
              <div>
                <label class="label">距离类型</label>
                <select v-model="toolOptions.distance_type" class="select">
                  <option value="manhattan">manhattan</option>
                  <option value="euclidean">euclidean</option>
                  <option value="cosine">cosine</option>
                </select>
              </div>
              <div>
                <label class="label">字段</label>
                <select v-model="toolOptions.field" class="select">
                  <option value="p_change">p_change</option>
                  <option value="close">close</option>
                </select>
              </div>
            </div>
          </div>

          <div class="toolbar">
            <button class="btn-primary" @click="runTool" :disabled="actionsBusy">执行分析</button>
            <span class="muted">执行后查看任务详情</span>
          </div>
        </div>

        <div class="tool-result">
          <h3>分析结果预览</h3>
          <div v-if="analysisResult" class="code-wrap">
            <pre class="code">{{ analysisText }}</pre>
          </div>
          <div v-if="analysisResult" class="info-card">
            <div class="toolbar">
              <button class="btn-secondary" @click="syncAnalysisToChart">同步到回测K线</button>
              <label class="toggle">
                <input type="checkbox" v-model="analysisOverlayEnabled" />
                <span>叠加趋势线</span>
              </label>
            </div>
            <p class="muted">分析标的：{{ analysisResult.symbol || '-' }}</p>
            <p class="muted" v-if="analysisResult.trend_lines?.length">
              支撑/阻力线：{{ analysisResult.trend_lines.length }} 条
            </p>
            <p class="muted">切换到“策略验证”查看图表叠加效果。</p>
          </div>
          <p v-else class="muted">暂无分析结果。</p>
        </div>
      </div>
    </section>

    <section class="panel" v-show="activeTab === 'jobs'">
      <header class="panel-title">
        <div>
          <h2>任务队列</h2>
          <p class="muted">回测、更新与分析任务统一管理。</p>
        </div>
        <div v-if="store.activeJob" class="pill">
          当前任务 #{{ store.activeJob.id }} · {{ store.activeJob.type }} ·
          <span :class="['status', `status-${store.activeJob.status}`]">{{ store.activeJob.status }}</span>
        </div>
      </header>
      <p class="panel-note">成功任务可导出 JSON/CSV，用于后续复盘或策略记录。</p>

      <p v-if="store.jobsError" class="error">{{ store.jobsError }}</p>
      <div v-if="store.jobsLoading" class="muted">加载中…</div>
      <div v-else class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Type</th>
              <th>Status</th>
              <th>Created</th>
              <th>Updated</th>
              <th>Result</th>
              <th>Error</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="job in store.jobs" :key="job.id">
              <td class="mono">#{{ job.id }}</td>
              <td>{{ job.type }}</td>
              <td><span :class="['status', `status-${job.status}`]">{{ job.status }}</span></td>
              <td class="mono">{{ formatTime(job.created_at) }}</td>
              <td class="mono">{{ formatTime(job.updated_at) }}</td>
              <td class="mono">{{ brief(job.result) }}</td>
              <td class="mono">{{ brief(job.error) }}</td>
              <td>
                <div class="table-actions">
                  <a v-if="job.status === 'succeeded'" class="btn-ghost" :href="exportUrl(job.id, 'json')" target="_blank" rel="noreferrer">
                    导出 JSON
                  </a>
                  <a v-if="job.status === 'succeeded' && job.result?.orders" class="btn-ghost" :href="exportUrl(job.id, 'csv', 'orders')">
                    订单 CSV
                  </a>
                  <a v-if="job.status === 'succeeded' && job.result?.actions" class="btn-ghost" :href="exportUrl(job.id, 'csv', 'actions')">
                    行为 CSV
                  </a>
                  <button class="btn-secondary" @click="selectJob(job.id)">详情</button>
                  <button class="btn-secondary" @click="removeJob(job)" :disabled="job.status === 'running'">删除</button>
                </div>
              </td>
            </tr>
            <tr v-if="store.jobs.length === 0">
              <td colspan="8" class="muted">暂无任务</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="store.activeJob" class="result-card">
        <h3>任务详情</h3>
        <div class="result-grid">
          <div>
            <p class="muted">任务编号</p>
            <p class="metric-value">#{{ store.activeJob.id }}</p>
          </div>
          <div>
            <p class="muted">任务类型</p>
            <p class="metric-value">{{ store.activeJob.type }}</p>
          </div>
          <div>
            <p class="muted">状态</p>
            <p class="metric-value">{{ store.activeJob.status }}</p>
          </div>
          <div>
            <p class="muted">更新时间</p>
            <p class="metric-value">{{ formatTime(store.activeJob.updated_at) }}</p>
          </div>
        </div>
        <div class="code-wrap" v-if="store.activeJob.params">
          <p class="muted">参数</p>
          <pre class="code">{{ activeParamsText }}</pre>
        </div>
        <div class="code-wrap" v-if="store.activeJob.result">
          <p class="muted">结果</p>
          <pre class="code">{{ activeResultText }}</pre>
        </div>
        <div class="code-wrap" v-if="store.activeJob.error">
          <p class="muted">错误</p>
          <pre class="code">{{ activeErrorText }}</pre>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { createChart } from 'lightweight-charts'
import { api } from '../services/api'
import { useQuantStore } from '../stores/quantStore'

const store = useQuantStore()
const tabs = [
  {
    id: 'prepare',
    step: '01',
    title: '数据准备',
    subtitle: '检索 → 更新',
    hint: '先检索并建立选股篮，再更新 K 线到 PG 数据库。'
  },
  {
    id: 'strategy',
    step: '02',
    title: '策略验证',
    subtitle: '回测 → 寻优',
    hint: '先回测验证，再用网格寻优确定参数并回填。'
  },
  {
    id: 'tools',
    step: '03',
    title: '量化分析',
    subtitle: '解释与对比',
    hint: '用趋势线、相关性与统计指标解释策略表现。'
  },
  {
    id: 'jobs',
    step: '04',
    title: '任务记录',
    subtitle: '导出与复盘',
    hint: '查看执行过程、导出结果并沉淀结论。'
  }
]
const activeTab = ref('prepare')
const activeTabMeta = computed(() => tabs.find((tab) => tab.id === activeTab.value) || tabs[0])
const tabIndex = computed(() => tabs.findIndex((tab) => tab.id === activeTab.value))
const isFirstTab = computed(() => tabIndex.value <= 0)
const isLastTab = computed(() => tabIndex.value >= tabs.length - 1)
const setTab = (id) => {
  activeTab.value = id
}
const goPrev = () => {
  if (isFirstTab.value) return
  activeTab.value = tabs[tabIndex.value - 1].id
}
const goNext = () => {
  if (isLastTab.value) return
  activeTab.value = tabs[tabIndex.value + 1].id
}
const market = ref(store.market)
const query = ref(store.query)
const kind = ref(store.kind)
const pageSize = ref(store.pageSize)
const selectedSymbols = ref([])
const savedPortfolios = ref([])
const selectedPortfolio = ref('')
const klineContainer = ref(null)
const equityContainer = ref(null)
const chartRef = ref(null)
const candleSeries = ref(null)
const volumeSeries = ref(null)
const equityChartRef = ref(null)
const equitySeries = ref(null)
const analysisLineSeries = ref([])
const orderPriceLines = ref([])
const klineData = ref([])
const equityData = ref([])
const klineLoading = ref(false)
const klineError = ref('')
const chartSymbol = ref('')
const orderFilter = ref('all')
const selectedOrderKey = ref('')
const selectedOrder = ref(null)
const showStopLines = ref(true)
const analysisOverlayEnabled = ref(true)

const updateForm = reactive({
  market: market.value,
  n_folds: 1,
  start: '',
  end: '',
  n_jobs: 8,
  how: 'thread',
  symbols: ''
})

const backtestForm = reactive({
  market: market.value,
  symbols: '',
  cash: 1000000,
  buy_xd: 42,
  stop_loss_n: 0.5,
  stop_win_n: 3.0,
  n_folds: 1,
  start: '',
  end: ''
})

const gridForm = reactive({
  market: market.value,
  symbols: '',
  cash: 1000000,
  buy_xd_list: '20, 42, 60',
  stop_loss_n_list: '0.5, 1.0',
  stop_win_n_list: '2.0, 3.0',
  n_folds: 1,
  start: '',
  end: '',
  max_runs: 30
})

const toolForm = reactive({
  market: market.value,
  tool: 'support_resistance',
  symbols: '',
  n_folds: 1,
  start: '',
  end: '',
  limit: 200
})

const toolOptions = reactive({
  only_last: true,
  mode: 'stats',
  jump_diff_factor: 1.0,
  power_threshold: 2.0,
  weight_a: 0.5,
  weight_b: 0.5,
  benchmark: '',
  resample: 5,
  speed_key: 'close',
  step_x: 1.0,
  shift_mode: 'close',
  regress_mode: 'best',
  corr_type: 'pears',
  distance_type: 'manhattan',
  field: 'p_change'
})

const actionsBusy = computed(
  () => store.jobsLoading || store.activeJobLoading || store.symbolsLoading
)

const defaultSymbolForMarket = (value) => {
  if (value === 'SH') return 'sh600036'
  if (value === 'SZ') return 'sz000001'
  if (value === '300') return 'sz300750'
  if (value === 'US') return 'usAAPL'
  if (value === 'HK') return 'hk00700'
  return 'sh600036'
}

if (!backtestForm.symbols) backtestForm.symbols = defaultSymbolForMarket(market.value)
if (!gridForm.symbols) gridForm.symbols = defaultSymbolForMarket(market.value)
if (!toolForm.symbols) toolForm.symbols = defaultSymbolForMarket(market.value)

watch(market, (val) => {
  updateForm.market = val
  backtestForm.market = val
  gridForm.market = val
  toolForm.market = val
  if (!backtestForm.symbols) backtestForm.symbols = defaultSymbolForMarket(val)
  if (!gridForm.symbols) gridForm.symbols = defaultSymbolForMarket(val)
  if (!toolForm.symbols) toolForm.symbols = defaultSymbolForMarket(val)
})

const jobStats = computed(() => {
  const stats = { total: 0, running: 0, succeeded: 0, failed: 0 }
  stats.total = store.jobs.length
  for (const job of store.jobs) {
    if (job.status === 'running') stats.running += 1
    if (job.status === 'succeeded') stats.succeeded += 1
    if (job.status === 'failed') stats.failed += 1
  }
  return stats
})

const lastUpdateSummary = computed(() => {
  const job = store.jobs.find((item) => item.type === 'kl_update' && item.status === 'succeeded')
  return job?.result || null
})

const latestJobByType = (type) => {
  if (!type) return null
  const jobs = store.jobs.filter((job) => job.type === type)
  if (!jobs.length) return null
  return jobs.reduce((latest, job) => (job.id > latest.id ? job : latest), jobs[0])
}

const backtestJob = computed(() => {
  if (store.activeJob && store.activeJob.type === 'backtest') return store.activeJob
  return latestJobByType('backtest')
})

const backtestSummary = computed(() => backtestJob.value?.result?.summary || null)

const backtestOrders = computed(() => backtestJob.value?.result?.orders || [])

const filteredOrders = computed(() => {
  const orders = backtestOrders.value || []
  const scoped = chartSymbol.value
    ? orders.filter((item) => String(item.symbol || '').toLowerCase() === chartSymbol.value.toLowerCase())
    : orders
  if (orderFilter.value === 'win') return scoped.filter((item) => resolveOrderProfit(item) > 0)
  if (orderFilter.value === 'loss') return scoped.filter((item) => resolveOrderProfit(item) < 0)
  if (orderFilter.value === 'hold') {
    return scoped.filter((item) => {
      const sellDate = Number(item.sell_date || 0)
      return !sellDate
    })
  }
  return scoped
})

const backtestSymbols = computed(() => {
  const raw = backtestJob.value?.result?.summary?.symbols || backtestJob.value?.params?.symbols
  if (Array.isArray(raw)) return raw
  if (typeof raw === 'string') {
    return raw
      .split(/[\s,;]+/)
      .map((item) => item.trim())
      .filter(Boolean)
  }
  return []
})

const backtestTradeStats = computed(() => {
  const orders = backtestOrders.value || []
  if (!orders.length) return null
  const profits = orders.map((item) => resolveOrderProfit(item))
  const total = orders.length
  const wins = profits.filter((p) => p > 0).length
  const totalProfit = profits.reduce((sum, val) => sum + val, 0)
  const avgProfit = total ? totalProfit / total : 0
  return {
    total,
    wins,
    winRate: total ? (wins / total) * 100 : 0,
    totalProfit,
    avgProfit
  }
})

const showBacktestVisual = computed(() => {
  return (
    !!backtestSummary.value ||
    !!chartSymbol.value ||
    klineLoading.value ||
    (klineData.value && klineData.value.length > 0)
  )
})

const chartWindow = reactive({
  size: 160,
  offset: 0
})
const hoverInfo = ref(null)

const gridSummary = computed(() => {
  if (!store.activeJob || store.activeJob.type !== 'grid_search') return null
  return store.activeJob.result?.best || null
})

const analysisResult = computed(() => {
  if (!store.activeJob || store.activeJob.type !== 'analysis') return null
  return store.activeJob.result || null
})

const gridSummaryText = computed(() =>
  gridSummary.value ? JSON.stringify(gridSummary.value, null, 2) : ''
)

const analysisText = computed(() =>
  analysisResult.value ? JSON.stringify(analysisResult.value, null, 2) : ''
)

const applyGridToBacktest = () => {
  if (!gridSummary.value) return
  if (gridSummary.value.buy_xd) backtestForm.buy_xd = gridSummary.value.buy_xd
  if (gridSummary.value.stop_loss_n !== undefined) backtestForm.stop_loss_n = gridSummary.value.stop_loss_n
  if (gridSummary.value.stop_win_n !== undefined) backtestForm.stop_win_n = gridSummary.value.stop_win_n
  if (Array.isArray(gridSummary.value.symbols) && gridSummary.value.symbols.length) {
    backtestForm.symbols = gridSummary.value.symbols.join(', ')
  }
  if (gridSummary.value.market) backtestForm.market = gridSummary.value.market
  activeTab.value = 'strategy'
}

watch(backtestSummary, (val) => {
  if (!val) return
  const symbols = backtestSymbols.value
  if (symbols.length && !chartSymbol.value) {
    chartSymbol.value = symbols[0]
  }
  if (chartSymbol.value) {
    loadKlineChart()
  }
})

watch(chartSymbol, (val, oldVal) => {
  if (!val || val === oldVal) return
  loadKlineChart()
})

watch(
  () => [chartWindow.size, chartWindow.offset, klineData.value.length],
  () => {
    if (klineData.value.length) updateChartData()
  }
)

watch(filteredOrders, () => {
  syncSelectedOrder()
  if (klineData.value.length) updateChartData()
  updateEquityChart()
})

watch(selectedOrder, () => {
  applyOrderLines()
})

watch(showStopLines, () => {
  applyOrderLines()
})

watch([analysisResult, analysisOverlayEnabled], () => {
  if (klineData.value.length) applyAnalysisOverlay()
})

watch(activeTab, async (val) => {
  if (val !== 'strategy') return
  await nextTick()
  handleResize()
})

const activeParamsText = computed(() =>
  store.activeJob?.params ? JSON.stringify(store.activeJob.params, null, 2) : ''
)
const activeResultText = computed(() =>
  store.activeJob?.result ? JSON.stringify(store.activeJob.result, null, 2) : ''
)
const activeErrorText = computed(() =>
  store.activeJob?.error ? String(store.activeJob.error) : ''
)

const toolOptionMode = computed(() => {
  if (toolForm.tool === 'support_resistance') return 'support'
  if (toolForm.tool === 'jump_gap') return 'jump'
  if (toolForm.tool === 'trend_speed') return 'trend'
  if (toolForm.tool === 'shift_distance') return 'shift'
  if (toolForm.tool === 'regress' || toolForm.tool === 'price_channel') return 'regress'
  if (toolForm.tool === 'correlation') return 'corr'
  if (toolForm.tool === 'distance') return 'distance'
  return 'base'
})

const totalPages = computed(() => Math.max(1, Math.ceil(store.total / store.pageSize)))

const formatTime = (v) => {
  if (!v) return '-'
  try {
    const d = typeof v === 'string' ? new Date(v) : new Date(String(v))
    if (Number.isNaN(d.getTime())) return String(v)
    return d.toLocaleString()
  } catch {
    return String(v)
  }
}

const brief = (v) => {
  if (!v) return ''
  const s = typeof v === 'string' ? v : JSON.stringify(v)
  return s.length > 60 ? `${s.slice(0, 57)}...` : s
}

const formatNumber = (value, digits = 2) => {
  if (value === null || value === undefined) return '-'
  const num = Number(value)
  if (!Number.isFinite(num)) return '-'
  return num.toFixed(digits)
}

const toDateInt = (value) => {
  if (value === null || value === undefined) return null
  if (typeof value === 'number') return Number.isFinite(value) ? value : null
  const raw = String(value).trim()
  if (!raw) return null
  if (/^\d{8}$/.test(raw)) return Number(raw)
  const date = new Date(raw)
  if (Number.isNaN(date.getTime())) return null
  const yyyy = date.getFullYear()
  const mm = String(date.getMonth() + 1).padStart(2, '0')
  const dd = String(date.getDate()).padStart(2, '0')
  return Number(`${yyyy}${mm}${dd}`)
}

const formatKlineDate = (value) => {
  const dateInt = toDateInt(value)
  if (!dateInt) return '-'
  const raw = String(dateInt)
  return `${raw.slice(0, 4)}-${raw.slice(4, 6)}-${raw.slice(6, 8)}`
}

const toChartTime = (value) => {
  const dateInt = toDateInt(value)
  if (!dateInt) return null
  const raw = String(dateInt)
  return `${raw.slice(0, 4)}-${raw.slice(4, 6)}-${raw.slice(6, 8)}`
}

const orderKey = (order) => {
  if (!order) return ''
  const dateInt = toDateInt(order.buy_date) || 0
  const price = Number(order.buy_price) || 0
  return `${order.symbol || 'unknown'}-${dateInt}-${price}`
}

const focusOrder = (order) => {
  if (!order || !klineData.value.length) return
  const dateInt = toDateInt(order.buy_date)
  if (!dateInt) return
  const index = klineData.value.findIndex((item) => toDateInt(item.date) === dateInt)
  if (index < 0) return
  const total = klineData.value.length
  const size = Math.max(60, Math.min(chartWindow.size || 160, total))
  const to = Math.min(total - 1, index + Math.floor(size / 2))
  chartWindow.offset = Math.max(0, total - 1 - to)
  applyVisibleRange()
}

const resolveOrderProfit = (order) => {
  if (!order) return 0
  if (order.profit !== undefined && order.profit !== null) {
    const val = Number(order.profit)
    if (Number.isFinite(val)) return val
  }
  const buy = Number(order.buy_price)
  const sell = Number(order.sell_price)
  if (Number.isFinite(buy) && Number.isFinite(sell)) return sell - buy
  return 0
}

const syncSelectedOrder = () => {
  if (!selectedOrderKey.value) {
    selectedOrder.value = null
    return
  }
  const next = filteredOrders.value.find((order) => orderKey(order) === selectedOrderKey.value)
  if (!next) {
    selectedOrderKey.value = ''
  }
  selectedOrder.value = next || null
  if (next) {
    focusOrder(next)
  }
}

const selectOrder = (order) => {
  if (!order) return
  selectedOrderKey.value = orderKey(order)
  selectedOrder.value = order
  focusOrder(order)
}

const ensureChart = () => {
  if (chartRef.value || !klineContainer.value) return
  const width = klineContainer.value.clientWidth
  if (!width) return
  chartRef.value = createChart(klineContainer.value, {
    height: 340,
    width,
    layout: {
      background: { color: '#ffffff' },
      textColor: '#1b1a18',
      fontFamily: "Sora, 'Noto Sans SC', sans-serif"
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
    },
    crosshair: {
      mode: 0
    }
  })
  candleSeries.value = chartRef.value.addCandlestickSeries({
    upColor: '#1f7a4b',
    downColor: '#b33a3a',
    wickUpColor: '#1f7a4b',
    wickDownColor: '#b33a3a',
    borderVisible: false
  })
  volumeSeries.value = chartRef.value.addHistogramSeries({
    priceFormat: { type: 'volume' },
    priceScaleId: '',
    scaleMargins: { top: 0.8, bottom: 0 }
  })
  chartRef.value.subscribeCrosshairMove((param) => {
    if (!param || !param.time || !candleSeries.value) {
      hoverInfo.value = null
      return
    }
    const candle = param.seriesData.get(candleSeries.value)
    if (!candle) {
      hoverInfo.value = null
      return
    }
    const volume = volumeSeries.value ? param.seriesData.get(volumeSeries.value) : null
    const time =
      typeof param.time === 'string'
        ? param.time
        : `${param.time.year}-${String(param.time.month).padStart(2, '0')}-${String(param.time.day).padStart(2, '0')}`
    hoverInfo.value = {
      date: time,
      open: candle.open,
      high: candle.high,
      low: candle.low,
      close: candle.close,
      volume: volume?.value ?? null
    }
  })
}

const ensureEquityChart = () => {
  if (equityChartRef.value || !equityContainer.value) return
  const width = equityContainer.value.clientWidth
  if (!width) return
  equityChartRef.value = createChart(equityContainer.value, {
    height: 220,
    width,
    layout: {
      background: { color: '#ffffff' },
      textColor: '#1b1a18',
      fontFamily: "Sora, 'Noto Sans SC', sans-serif"
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
  equitySeries.value = equityChartRef.value.addLineSeries({
    color: '#1f7a4b',
    lineWidth: 2
  })
}

const applyVisibleRange = () => {
  if (!chartRef.value || !klineData.value.length) return
  const total = klineData.value.length
  const size = Math.max(60, Math.min(chartWindow.size || 160, total))
  const maxOffset = Math.max(0, total - size)
  if (chartWindow.offset > maxOffset) chartWindow.offset = maxOffset
  if (chartWindow.offset < 0) chartWindow.offset = 0
  const to = total - 1 - chartWindow.offset
  const from = Math.max(0, to - size + 1)
  chartRef.value.timeScale().setVisibleLogicalRange({ from, to })
}

const buildMarkers = () => {
  const orders = (filteredOrders.value || []).slice(0, 200)
  const markers = []
  orders.forEach((order) => {
    const buyTime = toChartTime(order.buy_date)
    const sellTime = toChartTime(order.sell_date)
    if (buyTime) {
      markers.push({
        time: buyTime,
        position: 'belowBar',
        color: '#1f7a4b',
        shape: 'arrowUp',
        text: `买 ${formatNumber(order.buy_price)}`
      })
    }
    if (sellTime && Number(order.sell_date) > 0) {
      markers.push({
        time: sellTime,
        position: 'aboveBar',
        color: '#c17f2f',
        shape: 'arrowDown',
        text: `卖 ${formatNumber(order.sell_price)}`
      })
    }
  })
  return markers.sort((a, b) => String(a.time).localeCompare(String(b.time)))
}

const clearOrderLines = () => {
  if (!candleSeries.value || !orderPriceLines.value.length) {
    orderPriceLines.value = []
    return
  }
  orderPriceLines.value.forEach((line) => {
    try {
      candleSeries.value.removePriceLine(line)
    } catch {
      // ignore stale lines
    }
  })
  orderPriceLines.value = []
}

const applyOrderLines = () => {
  clearOrderLines()
  if (!candleSeries.value || !selectedOrder.value) return
  const order = selectedOrder.value
  const lines = []
  const buyPrice = Number(order.buy_price)
  if (Number.isFinite(buyPrice) && buyPrice > 0) {
    lines.push(
      candleSeries.value.createPriceLine({
        price: buyPrice,
        color: '#1f7a4b',
        lineWidth: 2,
        lineStyle: 0,
        axisLabelVisible: true,
        title: '买入'
      })
    )
  }
  const sellPrice = Number(order.sell_price)
  const sellDate = Number(order.sell_date || 0)
  if (Number.isFinite(sellPrice) && sellPrice > 0 && sellDate > 0) {
    lines.push(
      candleSeries.value.createPriceLine({
        price: sellPrice,
        color: '#c17f2f',
        lineWidth: 2,
        lineStyle: 0,
        axisLabelVisible: true,
        title: '卖出'
      })
    )
  }
  if (showStopLines.value) {
    const stopLoss = Number(order.stop_loss_price)
    if (Number.isFinite(stopLoss) && stopLoss > 0) {
      lines.push(
        candleSeries.value.createPriceLine({
          price: stopLoss,
          color: '#b33a3a',
          lineWidth: 1,
          lineStyle: 2,
          axisLabelVisible: true,
          title: '止损'
        })
      )
    }
    const stopWin = Number(order.stop_win_price)
    if (Number.isFinite(stopWin) && stopWin > 0) {
      lines.push(
        candleSeries.value.createPriceLine({
          price: stopWin,
          color: '#1f7a4b',
          lineWidth: 1,
          lineStyle: 2,
          axisLabelVisible: true,
          title: '止盈'
        })
      )
    }
  }
  orderPriceLines.value = lines
}

const clearAnalysisOverlay = () => {
  if (!chartRef.value || !analysisLineSeries.value.length) {
    analysisLineSeries.value = []
    return
  }
  analysisLineSeries.value.forEach((series) => {
    try {
      chartRef.value.removeSeries(series)
    } catch {
      // ignore stale series
    }
  })
  analysisLineSeries.value = []
}

const applyAnalysisOverlay = () => {
  clearAnalysisOverlay()
  if (!analysisOverlayEnabled.value || !analysisResult.value || !chartRef.value) return
  const lines = analysisResult.value.trend_lines
  if (!Array.isArray(lines) || !lines.length || !klineData.value.length) return
  const symbol = (analysisResult.value.symbol || '').toLowerCase()
  if (symbol && chartSymbol.value && symbol !== chartSymbol.value.toLowerCase()) return
  lines.forEach((line) => {
    const startIdx = Math.max(0, Math.min(klineData.value.length - 1, Math.round(Number(line.x_start) || 0)))
    const endIdx = Math.max(0, Math.min(klineData.value.length - 1, Math.round(Number(line.x_end) || 0)))
    const startTime = toChartTime(klineData.value[startIdx]?.date)
    const endTime = toChartTime(klineData.value[endIdx]?.date)
    if (!startTime || !endTime) return
    const color = line.type === 'support' ? '#2f6fdd' : '#c17f2f'
    const series = chartRef.value.addLineSeries({
      color,
      lineWidth: 1,
      lineStyle: 2
    })
    series.setData([
      { time: startTime, value: Number(line.y_start) || 0 },
      { time: endTime, value: Number(line.y_end) || 0 }
    ])
    analysisLineSeries.value.push(series)
  })
}

const syncAnalysisToChart = async () => {
  if (!analysisResult.value) return
  if (analysisResult.value.symbol) {
    chartSymbol.value = analysisResult.value.symbol
    if (!backtestForm.symbols) {
      backtestForm.symbols = analysisResult.value.symbol
    }
  }
  backtestForm.market = toolForm.market
  if (toolForm.start) backtestForm.start = toolForm.start
  if (toolForm.end) backtestForm.end = toolForm.end
  analysisOverlayEnabled.value = true
  activeTab.value = 'strategy'
  await nextTick()
  await loadKlineChart()
}

const updateChartData = () => {
  ensureChart()
  if (!chartRef.value || !candleSeries.value || !volumeSeries.value) return
  const data = (klineData.value || []).slice().sort((a, b) => {
    const left = toDateInt(a.date) || 0
    const right = toDateInt(b.date) || 0
    return left - right
  })
  if (!data.length) {
    candleSeries.value.setData([])
    volumeSeries.value.setData([])
    hoverInfo.value = null
    clearOrderLines()
    clearAnalysisOverlay()
    return
  }
  const candleData = data
    .map((item) => ({
      time: toChartTime(item.date),
      open: Number(item.open ?? item.close ?? 0),
      high: Number(item.high ?? item.close ?? 0),
      low: Number(item.low ?? item.close ?? 0),
      close: Number(item.close ?? item.open ?? 0)
    }))
    .filter((item) => item.time)
  candleSeries.value.setData(candleData)
  volumeSeries.value.setData(
    data
      .map((item) => ({
        time: toChartTime(item.date),
        value: Number(item.volume ?? 0),
        color:
          Number(item.close ?? 0) >= Number(item.open ?? 0)
            ? 'rgba(31, 122, 75, 0.4)'
            : 'rgba(179, 58, 58, 0.4)'
      }))
      .filter((item) => item.time)
  )
  candleSeries.value.setMarkers(buildMarkers())
  applyVisibleRange()
  applyOrderLines()
  applyAnalysisOverlay()
}

const buildEquitySeries = () => {
  const orders = filteredOrders.value || []
  const rows = orders
    .map((order) => {
      const time = toChartTime(order.sell_date || order.buy_date)
      return {
        time,
        profit: resolveOrderProfit(order)
      }
    })
    .filter((row) => row.time)
    .sort((a, b) => String(a.time).localeCompare(String(b.time)))
  let cumulative = 0
  return rows.map((row) => {
    cumulative += row.profit
    return { time: row.time, value: Number(cumulative.toFixed(2)) }
  })
}

const updateEquityChart = () => {
  const points = buildEquitySeries()
  equityData.value = points
  ensureEquityChart()
  if (!equityChartRef.value || !equitySeries.value) return
  equitySeries.value.setData(points)
  if (points.length) {
    equityChartRef.value.timeScale().fitContent()
  }
}

const shiftWindow = (direction) => {
  const data = klineData.value || []
  if (!data.length) return
  const step = Math.max(10, Math.floor((chartWindow.size || 160) / 5))
  const size = Math.max(60, Math.min(chartWindow.size || 160, data.length))
  const maxOffset = Math.max(0, data.length - size)
  chartWindow.offset = Math.min(maxOffset, Math.max(0, chartWindow.offset + direction * step))
  applyVisibleRange()
}

const loadKlineChart = async () => {
  const symbols = backtestSymbols.value.length
    ? backtestSymbols.value
    : backtestForm.symbols.split(/[\s,;]+/).filter(Boolean)
  if (!symbols.length) return
  if (!chartSymbol.value) chartSymbol.value = symbols[0]
  klineLoading.value = true
  klineError.value = ''
  try {
    const { data } = await api.get('/quant/klines', {
      params: {
        symbol: chartSymbol.value,
        market: backtestForm.market,
        start: backtestForm.start || undefined,
        end: backtestForm.end || undefined,
        limit: 600
      }
    })
    const items = data.data?.items || []
    klineData.value = items.slice().sort((a, b) => {
      const left = toDateInt(a.date) || 0
      const right = toDateInt(b.date) || 0
      return left - right
    })
    chartWindow.offset = 0
    await nextTick()
    updateChartData()
  } catch (err) {
    klineError.value = err?.message || String(err)
  } finally {
    klineLoading.value = false
  }
}

const parseNumberList = (raw) =>
  String(raw)
    .split(/[\s,;]+/)
    .map((item) => Number(item))
    .filter((item) => Number.isFinite(item))

const search = async () => {
  await store.searchSymbols({
    market: market.value,
    q: query.value,
    kind: kind.value,
    page: 1,
    pageSize: pageSize.value
  })
}

const importSymbols = async () => {
  const data = await store.importSymbols(market.value)
  if (data) {
    await store.searchSymbols({
      market: market.value,
      q: query.value,
      kind: kind.value,
      page: 1,
      pageSize: pageSize.value
    })
  }
}

const importAllSymbols = async () => {
  const data = await store.importSymbols('CN')
  if (data) {
    await store.searchSymbols({
      market: market.value,
      q: query.value,
      kind: kind.value,
      page: 1,
      pageSize: pageSize.value
    })
  }
}

const refreshJobs = async () => {
  await store.fetchJobs()
}

const selectJob = async (id) => {
  await store.fetchJob(id)
}

const removeJob = async (job) => {
  if (job.status === 'running') return
  await store.deleteJob(job.id)
}

const exportUrl = (id, format, section) => {
  const params = new URLSearchParams()
  if (format) params.set('format', format)
  if (section) params.set('section', section)
  const qs = params.toString()
  return `/api/v1/jobs/${encodeURIComponent(String(id))}/export${qs ? `?${qs}` : ''}`
}

const addSymbol = (symbol) => {
  if (!symbol || selectedSymbols.value.includes(symbol)) return
  selectedSymbols.value = [...selectedSymbols.value, symbol]
  syncSelectedSymbols()
}

const displaySymbol = (item) => {
  if (!item || !item.symbol) return ''
  const lower = item.symbol.toLowerCase()
  if (lower.startsWith('sh') || lower.startsWith('sz')) {
    return item.symbol.slice(2)
  }
  return item.symbol
}

const displayKind = (kind) => {
  if (kind === 'index') return '指数'
  if (kind === 'stock') return '个股'
  return '-'
}

const isSelected = (symbol) => selectedSymbols.value.includes(symbol)

const toggleSymbol = (symbol) => {
  if (isSelected(symbol)) {
    removeSymbol(symbol)
    return
  }
  addSymbol(symbol)
}

const removeSymbol = (symbol) => {
  selectedSymbols.value = selectedSymbols.value.filter((item) => item !== symbol)
  syncSelectedSymbols()
}

const clearSymbols = () => {
  selectedSymbols.value = []
  syncSelectedSymbols()
}

const selectPage = () => {
  const pageSymbols = store.symbols.map((item) => item.symbol)
  const merged = new Set([...selectedSymbols.value, ...pageSymbols])
  selectedSymbols.value = Array.from(merged)
  syncSelectedSymbols()
}

const invertPage = () => {
  const pageSymbols = new Set(store.symbols.map((item) => item.symbol))
  const next = selectedSymbols.value.filter((symbol) => !pageSymbols.has(symbol))
  for (const symbol of pageSymbols) {
    if (!selectedSymbols.value.includes(symbol)) {
      next.push(symbol)
    }
  }
  selectedSymbols.value = next
  syncSelectedSymbols()
}

const saveSelection = () => {
  const name = window.prompt('保存组合名称')
  if (!name) return
  const trimmed = name.trim()
  if (!trimmed) return
  const payload = { name: trimmed, symbols: selectedSymbols.value }
  localStorage.setItem(`doraemon_portfolio_${trimmed}`, JSON.stringify(payload))
  const indexKey = 'doraemon_portfolios'
  const list = JSON.parse(localStorage.getItem(indexKey) || '[]')
  if (!list.includes(trimmed)) list.push(trimmed)
  localStorage.setItem(indexKey, JSON.stringify(list))
  savedPortfolios.value = list
  selectedPortfolio.value = trimmed
}

const loadPortfolio = () => {
  if (!selectedPortfolio.value) return
  const raw = localStorage.getItem(`doraemon_portfolio_${selectedPortfolio.value}`)
  if (!raw) return
  try {
    const parsed = JSON.parse(raw)
    selectedSymbols.value = Array.isArray(parsed.symbols) ? parsed.symbols : []
    syncSelectedSymbols()
  } catch {
    // ignore malformed payload
  }
}

const deletePortfolio = () => {
  if (!selectedPortfolio.value) return
  localStorage.removeItem(`doraemon_portfolio_${selectedPortfolio.value}`)
  const indexKey = 'doraemon_portfolios'
  const list = JSON.parse(localStorage.getItem(indexKey) || '[]').filter(
    (name) => name !== selectedPortfolio.value
  )
  localStorage.setItem(indexKey, JSON.stringify(list))
  savedPortfolios.value = list
  selectedPortfolio.value = ''
}

const syncSelectedSymbols = () => {
  const text = selectedSymbols.value.join(', ')
  backtestForm.symbols = text
  gridForm.symbols = text
  toolForm.symbols = text
  updateForm.symbols = text
}

const changePage = async (nextPage) => {
  if (nextPage < 1 || nextPage > totalPages.value) return
  await store.searchSymbols({
    market: market.value,
    q: query.value,
    kind: kind.value,
    page: nextPage,
    pageSize: pageSize.value
  })
}

const applyPageSize = async () => {
  await store.searchSymbols({
    market: market.value,
    q: query.value,
    kind: kind.value,
    page: 1,
    pageSize: pageSize.value
  })
}

const runVerify = async () => {
  const job = await store.startVerify()
  await store.fetchJob(job.id)
}

const runKlUpdate = async () => {
  const symbols = selectedSymbols.value.length ? selectedSymbols.value.join(',') : ''
  const job = await store.startKlUpdate({
    market: updateForm.market,
    n_folds: updateForm.n_folds,
    start: updateForm.start || undefined,
    end: updateForm.end || undefined,
    how: updateForm.how,
    n_jobs: updateForm.n_jobs,
    symbols: symbols || undefined,
    all: !symbols
  })
  await store.fetchJob(job.id)
}

const runBacktest = async () => {
  const job = await store.startBacktest({
    market: backtestForm.market,
    symbols: backtestForm.symbols,
    n_folds: backtestForm.n_folds,
    start: backtestForm.start || undefined,
    end: backtestForm.end || undefined,
    cash: backtestForm.cash,
    buy_xd: backtestForm.buy_xd,
    stop_loss_n: backtestForm.stop_loss_n,
    stop_win_n: backtestForm.stop_win_n
  })
  await store.fetchJob(job.id)
}

const runGridSearch = async () => {
  const job = await store.startGridSearch({
    market: gridForm.market,
    symbols: gridForm.symbols,
    n_folds: gridForm.n_folds,
    start: gridForm.start || undefined,
    end: gridForm.end || undefined,
    cash: gridForm.cash,
    buy_xd_list: parseNumberList(gridForm.buy_xd_list).map((n) => Math.round(n)),
    stop_loss_n_list: parseNumberList(gridForm.stop_loss_n_list),
    stop_win_n_list: parseNumberList(gridForm.stop_win_n_list),
    max_runs: gridForm.max_runs
  })
  await store.fetchJob(job.id)
}

const buildToolOptions = () => {
  const opts = {}
  if (toolForm.tool === 'support_resistance') opts.only_last = toolOptions.only_last
  if (toolForm.tool === 'jump_gap') {
    opts.mode = toolOptions.mode
    opts.jump_diff_factor = toolOptions.jump_diff_factor
    opts.power_threshold = toolOptions.power_threshold
    opts.weight = [toolOptions.weight_a, toolOptions.weight_b]
  }
  if (toolForm.tool === 'trend_speed') {
    opts.benchmark = toolOptions.benchmark
    opts.resample = toolOptions.resample
    opts.speed_key = toolOptions.speed_key
  }
  if (toolForm.tool === 'shift_distance') {
    opts.step_x = toolOptions.step_x
    opts.mode = toolOptions.shift_mode
  }
  if (toolForm.tool === 'regress' || toolForm.tool === 'price_channel') {
    opts.mode = toolOptions.regress_mode
  }
  if (toolForm.tool === 'correlation') {
    opts.corr_type = toolOptions.corr_type
    opts.field = toolOptions.field
  }
  if (toolForm.tool === 'distance') {
    opts.distance_type = toolOptions.distance_type
    opts.field = toolOptions.field
  }
  return opts
}

const runTool = async () => {
  const job = await store.startQuantTool({
    market: toolForm.market,
    tool: toolForm.tool,
    symbols: toolForm.symbols,
    n_folds: toolForm.n_folds,
    start: toolForm.start || undefined,
    end: toolForm.end || undefined,
    limit: toolForm.limit,
    options: buildToolOptions()
  })
  await store.fetchJob(job.id)
}

const handleResize = () => {
  if (chartRef.value && klineContainer.value) {
    chartRef.value.applyOptions({ width: klineContainer.value.clientWidth })
  }
  if (equityChartRef.value && equityContainer.value) {
    equityChartRef.value.applyOptions({ width: equityContainer.value.clientWidth })
  }
  if (klineData.value.length) updateChartData()
  if (equityData.value.length) updateEquityChart()
}

onMounted(async () => {
  savedPortfolios.value = JSON.parse(localStorage.getItem('doraemon_portfolios') || '[]')
  window.addEventListener('resize', handleResize)
  await Promise.all([
    store.fetchJobs(),
    store.searchSymbols({
      market: market.value,
      q: query.value,
      kind: kind.value,
      page: store.page,
      pageSize: store.pageSize
    })
  ])
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  if (chartRef.value) {
    chartRef.value.remove()
    chartRef.value = null
  }
  if (equityChartRef.value) {
    equityChartRef.value.remove()
    equityChartRef.value = null
  }
})
</script>
