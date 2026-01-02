from __future__ import annotations

from abupy.FactorBuyBu.ABuFactorBuyBase import AbuFactorBuyXD, BuyCallMixin
from abupy.FactorSellBu.ABuFactorSellBase import AbuFactorSellXD, ESupportDirection
from abupy.IndicatorBu.ABuNDMacd import calc_macd


class MacdCrossBuy(AbuFactorBuyXD, BuyCallMixin):
    """MACD 金叉买入因子（DIF 上穿 DEA）"""

    def _init_self(self, **kwargs):
        self.fast_period = int(kwargs.pop("fast_period", 12))
        self.slow_period = int(kwargs.pop("slow_period", 26))
        self.signal_period = int(kwargs.pop("signal_period", 9))
        kwargs["xd"] = int(kwargs.pop("xd", self.slow_period + self.signal_period))
        super(MacdCrossBuy, self)._init_self(**kwargs)

    def fit_day(self, today):
        dif, dea, _ = calc_macd(
            self.xd_kl.close,
            fast_period=self.fast_period,
            slow_period=self.slow_period,
            signal_period=self.signal_period,
        )
        if len(dif) < 2 or len(dea) < 2:
            return None
        if dif[-2] <= dea[-2] and dif[-1] > dea[-1]:
            return self.buy_tomorrow()
        return None


class MacdCrossSell(AbuFactorSellXD):
    """MACD 死叉卖出因子（DIF 下穿 DEA）"""

    def _init_self(self, **kwargs):
        self.fast_period = int(kwargs.pop("fast_period", 12))
        self.slow_period = int(kwargs.pop("slow_period", 26))
        self.signal_period = int(kwargs.pop("signal_period", 9))
        kwargs["xd"] = int(kwargs.pop("xd", self.slow_period + self.signal_period))
        super(MacdCrossSell, self)._init_self(**kwargs)

    def support_direction(self):
        return [ESupportDirection.DIRECTION_CAll.value, ESupportDirection.DIRECTION_PUT.value]

    def fit_day(self, today, orders):
        dif, dea, _ = calc_macd(
            self.xd_kl.close,
            fast_period=self.fast_period,
            slow_period=self.slow_period,
            signal_period=self.signal_period,
        )
        if len(dif) < 2 or len(dea) < 2:
            return None
        if dif[-2] >= dea[-2] and dif[-1] < dea[-1]:
            for order in orders:
                self.sell_tomorrow(order)
        return None
