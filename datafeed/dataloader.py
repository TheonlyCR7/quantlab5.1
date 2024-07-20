import pandas as pd

from config import DATA_DIR_QUOTES
from loguru import logger
from datetime import datetime


class CSVDataloader:
    def __init__(self):
        pass

    @staticmethod
    def get_backtrader_df(symbol: str, start_date='20100101', end_date=datetime.now().strftime('%Y%m%d')):
        df = CSVDataloader.get_df([symbol], start_date=start_date)
        df.set_index('date', inplace=True)
        df['openinterest'] = 0
        df = df[['open', 'high', 'low', 'close', 'volume', 'openinterest']]
        df = df[df.index >= start_date]
        df = df[df.index <= end_date]
        return df

    @staticmethod
    def read_csv(symbol):
        csv = DATA_DIR_QUOTES.joinpath('{}.csv'.format(symbol))
        if not csv.exists():
            logger.warning('{}不存在'.format(csv.resolve()))
            return None

        df = pd.read_csv(csv.resolve(), index_col=None)
        df['date'] = df['date'].apply(lambda x: str(x))
        df['date'] = pd.to_datetime(df['date'])

        df['symbol'] = symbol
        return df

    @staticmethod
    def get_df(symbols: list[str], set_index=False, start_date='20100101'):
        dfs = []
        for s in symbols:
            df = CSVDataloader.read_csv(s)
            if df is not None:
                dfs.append(df)

        df = pd.concat(dfs, axis=0)
        if set_index:
            df.set_index('date', inplace=True)
            df.index = pd.to_datetime(df.index)
            df.sort_index(inplace=True, ascending=True)
            df = df[start_date:]
        else:
            df.sort_values(by='date', ascending=True, inplace=True)
            df = df[df['date'] >= start_date]

        return df

    @staticmethod
    def get(symbols: list[str], col='close', start_date='20100101'):
        df_all = CSVDataloader.get_df(symbols, set_index=True)
        if col not in df_all.columns:
            logger.error('{}列不存在')
            return None
        df_close = df_all.pivot_table(values=col, index=df_all.index, columns='symbol')
        df_close = df_close[start_date:]
        return df_close


if __name__ == '__main__':
    # df_close = CSVDataloader.get(['000300.SH', '000905.SH'])
    # print(df_close)

    # df = CSVDataloader.get_df(['000300.SH', '000905.SH'], set_index=False)
    # print(df)

    df = CSVDataloader.get_backtrader_df('000300.SH')
    print(df)
