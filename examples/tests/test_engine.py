from datetime import datetime
from multiprocessing import freeze_support

import backtrader as bt
from backtrader_extends.engine import BacktraderEngine, StFetcher
from datafeed.dataloader import CSVDataloader
from backtrader_extends.strategy import StrategyBase, StrategyAlgo
from backtrader_extends.algos import *


# df_test = CSVDataloader.get_df(['000300.SH'])

class StrategyBuyAndHold(StrategyBase):
    def __init__(self):
        pass

    def next(self):
        if self.position:
            return
        print('全仓买入')
        self.order_target_percent(self.data, 0.99)


@StFetcher.register
class St0(bt.SignalStrategy):
    params = dict(
        name='策略1',
    )

    def __init__(self):
        sma1, sma2 = bt.ind.SMA(period=10), bt.ind.SMA(period=30)
        crossover = bt.ind.CrossOver(sma1, sma2)
        self.signal_add(bt.SIGNAL_LONG, crossover)


@StFetcher.register
class St1(bt.SignalStrategy):
    params = dict(
        name='策略2',
    )

    def __init__(self):
        sma1 = bt.ind.SMA(period=10)
        crossover = bt.ind.CrossOver(self.data.close, sma1)
        self.signal_add(bt.SIGNAL_LONG, crossover)


if __name__ == '__main__':
    freeze_support()
    df = CSVDataloader.get_df(['000300.SH'], start_date='20120101')
    engine = BacktraderEngine(df, start=datetime(2005, 1, 1))
    engine.run_strategy(StrategyBuyAndHold)

    # engine.run_multi_strategies()
    '''
    
    engine.run_algo_strategy(algo_list=[
        RunOnce(),
        SelectAll(),
        WeightEqually(),
        Rebalance()
    ])
    '''
    engine.show_result_empyrical()
    # engine.bokeh_plot()
