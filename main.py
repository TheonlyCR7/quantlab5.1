import sys

sys.path.append('../')
from matplotlib import rcParams

rcParams['font.family'] = 'SimHei'
import backtrader as bt

from datafeed.dataloader import CSVDataloader


class TurtleStrategy(bt.Strategy):
    # 默认参数
    params = (('long_period', 20),
              ('short_period', 10),
              ('printlog', False),)

    def __init__(self):
        self.order = None
        self.buyprice = 0
        self.buycomm = 0
        self.buy_size = 0
        self.buy_count = 0
        # 海龟交易法则中的唐奇安通道和平均波幅ATR
        self.H_line = bt.indicators.Highest(self.data.high(-1), period=self.p.long_period)
        self.L_line = bt.indicators.Lowest(self.data.low(-1), period=self.p.short_period)
        self.TR = bt.indicators.Max((self.data.high(0) - self.data.low(0)), \
                                    abs(self.data.close(-1) - self.data.high(0)), \
                                    abs(self.data.close(-1) - self.data.low(0)))
        self.ATR = bt.indicators.SimpleMovingAverage(self.TR, period=14)
        # 价格与上下轨线的交叉
        self.buy_signal = bt.ind.CrossOver(self.data.close(0), self.H_line)
        self.sell_signal = bt.ind.CrossOver(self.data.close(0), self.L_line)

    def next(self):
        if self.order:
            return
            # 入场：价格突破上轨线且空仓时
        if self.buy_signal > 0 and self.buy_count == 0:
            atr = self.ATR[0]

            self.buy_size = self.broker.getvalue() * 0.01 / self.ATR
            self.buy_size = int(self.buy_size / 100) * 100
            self.sizer.p.stake = self.buy_size  # 指定买卖多少股。
            print('ATR', atr, 'buy_size', self.sizer.p.stake, 'close', self.data.close[0], '市值',
                  self.broker.getvalue() * 0.01)
            self.buy_count = 1
            # print('空仓时买入', self.buy_size)
            self.order = self.buy()
            # 加仓：价格上涨了买入价的0.5的ATR且加仓次数少于3次（含）
        elif self.data.close > self.buyprice + 0.5 * self.ATR[0] and 0 < self.buy_count <= 4:
            # print('加仓买入')
            self.buy_size = self.broker.getvalue() * 0.01 / self.ATR
            self.buy_size = int(self.buy_size / 100) * 100
            self.sizer.p.stake = self.buy_size
            self.order = self.buy()

            self.buy_count += 1
            # 离场：价格跌破下轨线且持仓时
        elif self.sell_signal < 0 and self.buy_count > 0:
            # print('平仓信号卖出')
            self.order = self.sell()
            self.buy_count = 0
            # 止损：价格跌破买入价的2个ATR且持仓时
        elif self.data.close < (self.buyprice - 2 * self.ATR[0]) and self.buy_count > 0:
            # print('止损信号卖出')
            self.order = self.sell()
            self.buy_count = 0

            # 交易记录日志（默认不打印结果）

    def log(self, txt, dt=None, doprint=False):
        if self.params.printlog or doprint:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()},{txt}')

    # 记录交易执行情况（默认不输出结果）
    def notify_order(self, order):
        # 如果order为submitted/accepted,返回空
        if order.status in [order.Submitted, order.Accepted]:
            return
        # 如果order为buy/sell executed,报告价格结果
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'买入:\n价格:{order.executed.price},\
                成本:{order.executed.value},\
                手续费:{order.executed.comm}')

                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:
                self.log(f'卖出:\n价格：{order.executed.price},\
                成本: {order.executed.value},\
                手续费{order.executed.comm}')

            self.bar_executed = len(self)

            # 如果指令取消/交易失败, 报告结果
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('交易失败')
        self.order = None

    # 记录交易收益情况（可省略，默认不输出结果）
    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        self.log(f'策略收益：\n毛收益 {trade.pnl:.2f}, 净收益 {trade.pnlcomm:.2f}')

    def stop(self):
        self.log(f'(组合线：{self.p.long_period},{self.p.short_period})； \
        期末总资金: {self.broker.getvalue():.2f}', doprint=True)

        '''
        
        strat0 = strats[0]

        pyfolio = strat0.analyzers.getbyname('pyfolio')
        returns, positions, transactions, gross_lev = pyfolio.get_pf_items()
        import empyrical as em
        em.annual_return(returns)
        transactions
        '''


class TradeSizer(bt.Sizer):
    params = (('stake', 1),)

    def _getsizing(self, comminfo, cash, data, isbuy):
        if isbuy:
            return self.p.stake
        position = self.broker.getposition(data)
        if not position.size:
            return 0
        else:
            return position.size
        return self.p.stake


def main(symbol, long_list, short_list, start, end, startcash=1000000, com=0.001):
    # 创建主控制器
    cerebro = bt.Cerebro()
    cerebro.addstrategy(TurtleStrategy)
    # 导入策略参数寻优
    # cerebro.optstrategy(TurtleStrategy, long_period=long_list, short_period=short_list)
    # 获取数据
    df = CSVDataloader.get_backtrader_df(symbol, start_date=start, end_date=end)

    data = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data)
    # broker设置资金、手续费
    cerebro.broker.setcash(startcash)
    cerebro.broker.setcommission(commission=com)
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe_ratio')
    cerebro.addanalyzer(bt.analyzers.PyFolio, _name='pyfolio')
    # 设置买入设置，策略，数量
    cerebro.addsizer(TradeSizer)
    print('期初总资金: %.2f' % cerebro.broker.getvalue())
    optimized_runs = cerebro.run(maxcpus=1)
    #cerebro.plot()

    import matplotlib
    matplotlib.use('QT5Agg')
    cerebro.plot(iplot=False)

    # optimized_runs = cerebro.run()

    '''
    
    final_results_list = []
    for run in optimized_runs:
        for strategy in run:
            pyfolio = strategy.analyzers.getbyname('pyfolio')
            returns, positions, transactions, gross_lev = pyfolio.get_pf_items()
            import empyrical as em
            rets = em.annual_return(returns)
            # PnL = round(strategy.broker.get_value() - 10000, 2)
            # sharpe = strategy.analyzers.sharpe_ratio.get_analysis()
            final_results_list.append([strategy.params.long_period,
                                       strategy.params.short_period, rets])

    sort_by_sharpe = sorted(final_results_list, key=lambda x: x[2],
                            reverse=True)
    for line in sort_by_sharpe[:5]:
        print(line)
    '''


long_list = range(20, 70, 5)
short_list = range(5, 20, 5)
main('000300.SH', long_list, short_list, '20050101', '20240709')
