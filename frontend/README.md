# Frontend (Vue3 + Vite)

前端是 Doraemon 的量化工作台，负责交互、任务发起、结果可视化与导出。

## 技术栈

- Vue 3 + Vite
- Pinia
- Vue Router
- Axios
- lightweight-charts

## 启动步骤

```powershell
cd frontend
npm install
npm run dev
```

默认地址：`http://localhost:5173`

## 后端代理

`frontend/vite.config.js` 已配置：

- `/api` -> `http://localhost:8002`

也可通过 `VITE_API_TARGET` 覆盖代理目标。

## 页面结构

- 数据准备：股票检索、导入、选股篮、K 线更新
- 策略验证：回测参数配置、结果摘要、K 线与收益曲线、订单明细
- 参数交叉验证：网格寻优与回填
- 量化分析：支撑阻力/相关性/跳空等工具
- 任务记录：任务详情、JSON/CSV 导出

## 前端 API 入口

统一通过 `src/services/api.js` 调用，基础前缀：

- `/api/v1`

常用调用：

- `GET /quant/symbols`
- `POST /quant/kl/update`
- `POST /quant/backtest`
- `POST /quant/grid-search`
- `POST /quant/tools`
- `GET /jobs/`
- `GET /jobs/{id}`

## 状态管理

主 store：`src/stores/quantStore.js`

- 管理 symbol 搜索、策略目录、任务列表与当前任务
- 统一处理请求异常消息
