import pandas as pd

from .algo_base import Algo


class SelectAll(Algo):
    """
    Sets temp['selected'] with all securities (based on universe).

    Selects all the securities and saves them in temp['selected'].
    By default, SelectAll does not include securities that have no
    data (nan) on current date or those whose price is zero or negative.

    Args:
        * include_no_data (bool): Include securities that do not have data?
        * include_negative (bool): Include securities that have negative
          or zero prices?
    Sets:
        * selected

    """

    def __init__(self, include_no_data=False, include_negative=False):
        super(SelectAll, self).__init__()
        self.include_no_data = include_no_data
        self.include_negative = include_negative

    def __call__(self, target):
        target.temp["selected"] = list(target.df_bar.index)
        return True


class SelectThese(Algo):
    def __init__(self, tickers):
        super(SelectThese, self).__init__()
        self.tickers = tickers

    def __call__(self, target):
        '''
        selected = []
        for s in self.tickers:
            if s in target.bar_df.index:
                selected.append(s)

        '''
        # print(self.tickers)
        target.temp['selected'] = self.tickers
        # if len(selected) == 0:
        #    return False
        return True


class SelectBySignal(Algo):
    def __init__(self, rules=[], at_least_count=1, exclude=False):
        super(SelectBySignal, self).__init__()
        self.rules = rules
        self.at_least_count = at_least_count
        self.exclude = exclude

    def _check_if_matched(self, df_bar, rules, at_least_count):
        matched_items = []
        for symbol in list(df_bar.index):
            bar = df_bar.loc[symbol]
            match = 0
            for i, rule in enumerate(rules):
                # expr = re.sub('ind\((.*?)\)', 'bar["\\1"]', rule)
                # if eval(expr):
                if rule in list(bar.index):
                    if bar[rule]:
                        match += 1
            if match >= at_least_count:
                matched_items.append(symbol)
        return matched_items

    def __call__(self, target):
        df_bar = target.bar_df
        if self.rules and len(self.rules):
            matched = self._check_if_matched(df_bar, self.rules, self.at_least_count)
        if len(matched) == 0:
            return True

        if self.exclude:  # 平仓信息命中
            if 'selected' not in target.temp.keys():
                return True
            selected = target.temp['selected']
            excluded = []
            for s in selected:
                if s not in matched:
                    excluded.append(s)
            target.temp['selected'] = excluded  # 要平仓的排除掉
        else:  # 选中信号命中
            target.temp['selected'] = matched  # 选择要持仓的
        return True


class SelectHolding(Algo):
    def __call__(self, target):
        curr_holding = list(target.strategy.curr_holding.keys())
        if 'selected' not in target.temp.keys():
            target.temp['selected'] = curr_holding
        else:
            target.temp['selected'] = list(set(target.temp['selected'] + curr_holding))
        return True


class SelectTopK(Algo):
    def __init__(self, factor_name='order_by', K=1, drop_top_n=0, b_ascending=False):
        self.K = K
        self.drop_top_n = drop_top_n  # 这算是一个魔改，就是把最强的N个弃掉，尤其动量指标，过尤不及。
        self.factor_name = factor_name
        self.b_ascending = b_ascending

    def __call__(self, target):

        selected = None
        key = 'selected'
        # print(target.now)
        df_bar = target.bar_df
        factor_sorted = df_bar.sort_values(by=self.factor_name, ascending=self.b_ascending)

        symbols = factor_sorted.index
        # bar_df = bar_df.sort_values(self.order_by, ascending=self.b_ascending)

        if not selected:
            start = 0
            if self.drop_top_n <= len(symbols):
                start = self.drop_top_n
                ordered = symbols[start: start + self.K]
            else:
                ordered = []
        else:
            ordered = []
            count = 0
            for s in symbols:  # 一定是当天有记录的
                if s in selected:
                    count += 1
                    if count > self.drop_top_n:
                        ordered.append(s)

                    if len(ordered) >= self.K:
                        break

        target.temp[key] = ordered

        return True
