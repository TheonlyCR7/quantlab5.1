import json

import backtrader as bt
from datetime import datetime, time

from backtrader_futures import CTPStore

with open('./params.json', 'r') as f:
    ctp_setting = json.load(f)

# 说明在交易日上午8点45到下午3点，以及晚上8点45到凌晨2点45分，可进行实时行情模拟交易。
# 中国期货交易时段(日盘/夜盘)，只有在交易时段才能进行实时模拟仿真，其他时段只能进行非实时模拟仿真。双休日不能进行模拟仿真
DAY_START = time(8, 45)  # 日盘8点45开始
DAY_END = time(15, 0)  # 下午3点结束
NIGHT_START = time(20, 45)  # 夜盘晚上8点45开始
NIGHT_END = time(2, 45)  # 凌晨2点45结束


# 是否在交易时段
def is_trading_period():
    """
    """
    current_time = datetime.now().time()
    trading = False
    if ((current_time >= DAY_START and current_time <= DAY_END)
            or (current_time >= NIGHT_START)
            or (current_time <= NIGHT_END)):
        trading = True
    return trading


store = CTPStore(ctp_setting, debug=True)
# cerebro.addstrategy(SmaCross, store=store)

# 由于历史回填数据从akshare拿，最细1分钟bar，所以以下实盘也只接收1分钟bar
# https://www.akshare.xyz/zh_CN/latest/data/futures/futures.html#id106

data0 = store.getdata(dataname='ag2112.SHFE', timeframe=bt.TimeFrame.Minutes,  # 注意符号必须带交易所代码。
                      num_init_backfill=100 if is_trading_period() else 0)  # 初始回填bar数，使用TEST服务器进行模拟实盘时，要设为0

data1 = store.getdata(dataname='rb2201.SHFE', timeframe=bt.TimeFrame.Minutes,  # 注意符号必须带交易所代码。
                      num_init_backfill=100 if is_trading_period() else 0)  # 初始回填bar数，使用TEST服务器进行模拟实盘时，要设为0

print(data0)
print(data1)