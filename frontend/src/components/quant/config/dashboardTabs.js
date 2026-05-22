export const quantDashboardTabs = [
  {
    id: 'prepare',
    step: '01',
    title: '数据准备',
    subtitle: '标的与更新',
    hint: '搜索标的、维护组合，并先完成 K 线更新。'
  },
  {
    id: 'strategy',
    step: '02',
    title: '回测与寻优',
    subtitle: '验证策略',
    hint: '执行历史回测、参数交叉验证，并将最优组合应用到回测。'
  },
  {
    id: 'tools',
    step: '03',
    title: '量化分析',
    subtitle: '信号工具',
    hint: '运行支撑阻力、跳空、趋势速度等工具，生成交易信号。'
  },
  {
    id: 'ml',
    step: '04',
    title: 'ML 模型',
    subtitle: '特征训练与预测',
    hint: '构建特征、训练模型、生成预测并输出操作建议。'
  },
  {
    id: 'trend',
    step: '05',
    title: '走势分析',
    subtitle: '扩展预留',
    hint: '上传 K 线截图元数据与特征，验证未来走势分析 Demo 链路。'
  },
  {
    id: 'jobs',
    step: '06',
    title: '任务中心',
    subtitle: '状态与导出',
    hint: '查看任务状态、结果明细并导出。'
  }
]
