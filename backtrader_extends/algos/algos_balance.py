import numpy as np
import pandas as pd

from .algo_base import Algo


class Rebalance(Algo):

    def __init__(self):
        super(Rebalance, self).__init__()

    def __call__(self, target):
        if "weights" not in target.temp:
            return True

        targets = target.temp["weights"]
        # print(targets)
        if type(targets) is pd.Series:
            targets = targets.to_dict()

        for data, w in targets.items():
            target.order_target_percent(data, w*0.99)

        return True
