import backtrader as bt
import pandas as pd
from loguru import logger


class StrategyBase(bt.Strategy):
    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        logger.info('%s, %s' % (dt.isoformat(), txt))

    # 取当前的日期
    def get_current_dt(self):
        # print(self.datas[0].datetime)
        dt = self.datas[0].datetime.date(0).strftime('%Y-%m-%d')
        # print(dt)
        return dt

    # 取当前持仓的data列表
    def get_current_holding_datas(self):
        holdings = []
        for data in self.datas:
            if self.getposition(data).size > 0:
                holdings.append(data)
        return holdings

    # 打印订单日志
    def notify_order(self, order):

        order_status = ['Created', 'Submitted', 'Accepted', 'Partial',
                        'Completed', 'Canceled', 'Expired', 'Margin', 'Rejected']
        # 未被处理的订单
        if order.status in [order.Submitted, order.Accepted]:
            return
            self.log('未处理订单：订单号:%.0f, 标的: %s, 状态状态: %s' % (order.ref,
                                                           order.data._name,
                                                           order_status[order.status]))
            return
        # 已经处理的订单
        if order.status in [order.Partial, order.Completed]:

            if order.isbuy():
                self.log(
                    'BUY EXECUTED, 状态: %s, 订单号:%.0f, 标的: %s, 数量: %.2f, 价格: %.2f, 成本: %.2f, 手续费 %.2f' %
                    (order_status[order.status],  # 订单状态
                     order.ref,  # 订单编号
                     order.data._name,  # 股票名称
                     order.executed.size,  # 成交量
                     order.executed.price,  # 成交价
                     order.executed.value,  # 成交额
                     order.executed.comm))  # 佣金
            else:  # Sell
                self.log(
                    'SELL EXECUTED, status: %s, ref:%.0f, name: %s, Size: %.2f, Price: %.2f, Cost: %.2f, Comm %.2f' %
                    (order_status[order.status],
                     order.ref,
                     order.data._name,
                     order.executed.size,
                     order.executed.price,
                     order.executed.value,
                     order.executed.comm))

        elif order.status in [order.Canceled, order.Margin, order.Rejected, order.Expired]:
            # order.Margin资金不足，订单无法成交
            # 订单未完成
            self.log('未完成订单，订单号:%.0f, 标的 : %s, 订单状态: %s' % (
                order.ref, order.data._name, order_status[order.status]))

        self.order = None

    def notify_trade(self, trade):
        logger.debug('trade......', trade.status)
        # 交易刚打开时
        if trade.justopened:
            self.log('开仓, 标的: %s, 股数: %.2f,价格: %.2f' % (
                trade.getdataname(), trade.size, trade.price))
        # 交易结束
        elif trade.isclosed:
            self.log('平仓, 标的: %s, 股数: %.2f,价格: %.2f, GROSS %.2f, NET %.2f, 手续费 %.2f' % (
                trade.getdataname(), trade.size, trade.price, trade.pnl, trade.pnlcomm, trade.commission))
        # 更新交易状态
        else:
            self.log('交易更新, 标的: %s, 仓位: %.2f,价格: %.2f' % (
                trade.getdataname(), trade.size, trade.price))


class StrategyAlgo(StrategyBase):
    def __init__(self, algo_list, engine):
        self.algos = algo_list
        self.df_data = engine.df_data
        self.temp = {}
        self.perm = {}
        self.index = -1
        self.dates = list(self.df_data.index.unique())

    def next(self):
        self.index += 1
        self.now = self.dates[self.index]

        self.df_bar = self.df_data.loc[self.now]
        if type(self.df_bar) is pd.Series:
            self.df_bar = self.df_bar.to_frame().T
        self.df_bar.set_index('symbol', inplace=True)

        for algo in self.algos:
            if algo(self) is False:  # 如果algo返回False,直接不运行
                return
