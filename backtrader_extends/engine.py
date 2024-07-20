# encoding:utf8
from datetime import datetime

import backtrader as bt
import pandas as pd
import empyrical

from datafeed.dataloader import CSVDataloader
from .strategy import StrategyAlgo


def to_backtrader_dataframe(df):
    df.set_index('date', inplace=True)
    df.index = pd.to_datetime(df.index)
    df['openinterest'] = 0
    df = df[['open', 'high', 'low', 'close', 'volume', 'openinterest']]
    # for c in ['open', 'high', 'low', 'close']:
    #    df.loc[:, c] = df[c] / df[c][0]
    return df


class StFetcher(object):
    _STRATS = []

    @classmethod
    def register(cls, target):
        cls._STRATS.append(target)

    @classmethod
    def COUNT(cls):
        return range(len(cls._STRATS))

    def __new__(cls, *args, **kwargs):
        idx = kwargs.pop('idx')
        obj = cls._STRATS[idx](*args, **kwargs)
        return obj


class BacktraderEngine:
    def __init__(self, df_data, init_cash=1000000.0, benchmark='000300.SH', start=datetime(2010, 1, 1),
                 end=datetime.now().date()):
        self.optimize = None
        self.results = None
        self.init_cash = init_cash
        self.start = start
        self.end = end
        self.benchmark = benchmark
        cerebro = bt.Cerebro()
        cerebro.broker.setcash(init_cash)

        # 设置手续费
        cerebro.broker.setcommission(0.0001)
        # 滑点：双边各 0.0001
        cerebro.broker.set_slippage_perc(perc=0.0001)

        self.cerebro = cerebro
        self.cerebro.addanalyzer(bt.analyzers.PyFolio, _name='_PyFolio')

        self.df_data = df_data
        self.symbols = list(set(self.df_data['symbol']))
        self._add_symbols_data()

    def _init_analyzers(self):
        '''
        self.cerebro.addanalyzer(bt.analyzers.Returns, _name='_Returns')
        self.cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='_TradeAnalyzer')
        self.cerebro.addanalyzer(bt.analyzers.AnnualReturn, _name='_AnnualReturn')
        self.cerebro.addanalyzer(bt.analyzers.SharpeRatio, riskfreerate=0.0, annualize=True, _name='_SharpeRatio')
        self.cerebro.addanalyzer(bt.analyzers.DrawDown, _name='_DrawDown')
         '''
        self.cerebro.addanalyzer(bt.analyzers.PyFolio, _name='_PyFolio')

    def _add_symbols_data(self):
        # 加载数据
        for s in self.symbols:
            df_symbol = self.df_data[self.df_data['symbol'] == s].copy(deep=True)
            df = to_backtrader_dataframe(df_symbol)
            print(df)
            data = bt.feeds.PandasData(dataname=df, name=s, fromdate=self.start, todate=self.end)

            self.cerebro.adddata(data)
            self.cerebro.addobserver(bt.observers.Benchmark,
                                     data=data)
            self.cerebro.addobserver(bt.observers.TimeReturn)

    def run_algo_strategy(self, algo_list):
        self.cerebro.addstrategy(StrategyAlgo, algo_list=algo_list, engine=self)
        self.results = self.cerebro.run()

    def run_strategy(self, stra):
        self.cerebro.addstrategy(stra)
        self.results = self.cerebro.run()

    def run_multi_strategies(self):
        self.cerebro.optstrategy(StFetcher, idx=StFetcher.COUNT())
        self.results = self.cerebro.run(maxcpus=1, optreturn=False)
        self.optimize = True

    def bokeh_plot(self):
        from backtrader_plotting import Bokeh
        from backtrader_plotting.schemes import Tradimo
        plotconfig = {
            'id:ind#0': dict(
                subplot=True,
            ),
        }
        b = Bokeh(style='line', scheme=Tradimo(), plotconfig=plotconfig)

    def _show_result(self, returns):
        returns.index = returns.index.tz_convert(None)

        print('累计收益：', round(empyrical.cum_returns_final(returns), 3))
        print('年化收益：', round(empyrical.annual_return(returns), 3))
        print('最大回撤：', round(empyrical.max_drawdown(returns), 3))
        print('夏普比', round(empyrical.sharpe_ratio(returns), 3))
        print('卡玛比', round(empyrical.calmar_ratio(returns), 3))

        # import matplotlib.pyplot as plt
        # (1 + returns).cumprod().plot()
        # plt.show()
        # print('omega', round(empyrical.omega_ratio(returns)), 3)

        # import matplotlib
        # matplotlib.use('QT5Agg')
        # self.cerebro.plot(iplot=False)

    def show_result_empyrical(self):

        if self.optimize:
            strats = [x[0] for x in self.results]  # flatten the result
            for i, strategy in enumerate(strats):
                print(strategy.p.name)
                pyfolio = strategy.analyzers.getbyname('_PyFolio')
                returns, positions, transactions, gross_lev = pyfolio.get_pf_items()
                self._show_result(returns)

        else:
            portfolio_stats = self.results[0].analyzers.getbyname('_PyFolio')
            returns, positions, transactions, _ = portfolio_stats.get_pf_items()
            self._show_result(returns)

    def analysis(self, pyfolio=True):
        portfolio_stats = self.results[0].analyzers.getbyname('_PyFolio')
        returns, positions, transactions, _ = portfolio_stats.get_pf_items()
        returns.index = returns.index.tz_convert(None)
        self.show_result_empyrical(returns)

        self._bokeh_plot()
        # self.cerebro.plot()

        if pyfolio:
            from pyfolio.tears import create_full_tear_sheet
            create_full_tear_sheet(returns, positions=positions, transactions=transactions)
        else:
            import quantstats
            # df = self.feed.get_df(self.benchmark)
            # df['rate'] = df['close'].pct_change()
            # df = df[['rate']]
            quantstats.reports.html(returns, download_filename='stats.html', output='stats.html',
                                    title='AI量化平台')
            import webbrowser
            webbrowser.open('stats.html')

        '''

        import pyfolio as pf
        pf.create_full_tear_sheet(
            returns,
            positions=positions,
            transactions=transactions)
        '''
        # self.cerebro.plot(volume=False)


'''

# 策略选择类
class StFetcher(object):
    _STRATS = [StratgeyBuyHold, StrategyRotation]  # 注册策略

    def __new__(cls, *args, **kwargs):
        idx = kwargs.pop('idx')  # 策略索引

        obj = cls._STRATS[idx](*args, **kwargs)
        return obj
'''
