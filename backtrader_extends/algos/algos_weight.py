import numpy as np
import pandas as pd
import sklearn

from .algo_base import Algo
#from ..ffn_performance import calc_erc_weights


class WeightEqually(Algo):
    """
    Sets temp['weights'] by calculating equal weights for all items in
    selected.

    Equal weight Algo. Sets the 'weights' to 1/n for each item in 'selected'.

    Sets:
        * weights

    Requires:
        * selected

    """

    def __init__(self):
        super(WeightEqually, self).__init__()

    def __call__(self, target):
        selected = target.temp["selected"]
        n = len(selected)

        if n == 0:
            target.temp["weights"] = {}
        else:
            w = 1.0 / n
            target.temp["weights"] = {x: w for x in selected}

        return True




class WeightERC(Algo):
    """
    Sets temp['weights'] based on equal risk contribution algorithm.

    Sets the target weights based on ffn's calc_erc_weights. This
    is an extension of the inverse volatility risk parity portfolio in
    which the correlation of asset returns is incorporated into the
    calculation of risk contribution of each asset.

    The resulting portfolio is similar to a minimum variance portfolio
    subject to a diversification constraint on the weights of its components
    and its volatility is located between those of the minimum variance and
    equally-weighted portfolios (Maillard 2008).

    See:
        https://en.wikipedia.org/wiki/Risk_parity

    Args:
        * lookback (DateOffset): lookback period for estimating covariance
        * initial_weights (list): Starting asset weights [default inverse vol].
        * risk_weights (list): Risk target weights [default equal weight].
        * covar_method (str): method used to estimate the covariance. See ffn's
          calc_erc_weights for more details. (default ledoit-wolf).
        * risk_parity_method (str): Risk parity estimation method. see ffn's
          calc_erc_weights for more details. (default ccd).
        * maximum_iterations (int): Maximum iterations in iterative solutions
          (default 100).
        * tolerance (float): Tolerance level in iterative solutions (default 1E-8).


    Sets:
        * weights

    Requires:
        * selected

    """

    def __init__(
            self,
            lookback=pd.DateOffset(months=3),
            initial_weights=None,
            risk_weights=None,
            covar_method="ledoit-wolf",
            risk_parity_method="ccd",
            maximum_iterations=100,
            tolerance=1e-8,
            lag=pd.DateOffset(days=0),
    ):
        super(WeightERC, self).__init__()
        self.lookback = lookback
        self.initial_weights = initial_weights
        self.risk_weights = risk_weights
        self.covar_method = covar_method
        self.risk_parity_method = risk_parity_method
        self.maximum_iterations = maximum_iterations
        self.tolerance = tolerance
        self.lag = lag

    def __call__(self, target):
        selected = target.temp["selected"]

        if len(selected) == 0:
            target.temp["weights"] = {}
            return True

        if len(selected) == 1:
            target.temp["weights"] = {selected[0]: 1.0}
            return True


        t0 = target.now - self.lag
        prc = target.df_close.loc[t0 - self.lookback: t0, selected]

        returns = prc.to_returns().dropna()
        if len(returns) < 10:
            return False
        #ERC = EqualRiskContribution(returns.cov())
        #ERC.solve()

        #tw = ERC.x
        #print(tw)

        tw = calc_erc_weights(
            prc.to_returns().dropna(),
            initial_weights=self.initial_weights,
            risk_weights=self.risk_weights,
            covar_method=self.covar_method,
            risk_parity_method=self.risk_parity_method,
            maximum_iterations=self.maximum_iterations,
            tolerance=self.tolerance,
        )

        target.temp["weights"] = tw.dropna().to_dict()
        return True


class TargetVol(Algo):
    def __init__(
            self,
            target_volatility,
            lookback=pd.DateOffset(months=3),
            lag=pd.DateOffset(days=0),
            covar_method="standard",
            annualization_factor=252,
            exclude=[]
    ):
        super(TargetVol, self).__init__()
        self.target_volatility = target_volatility
        self.lookback = lookback
        self.lag = lag
        self.covar_method = covar_method
        self.annualization_factor = annualization_factor
        self.exclude = exclude

    def __call__(self, target):
        current_weights = target.temp["weights"]
        selected = current_weights.keys()

        # if there were no weights already set then skip
        if len(selected) == 0:
            return True

        t0 = target.now - self.lag
        prc = target.df_close.loc[t0 - self.lookback: t0, selected]
        returns = prc.to_returns()

        if len(returns)< 10:
            return True

        # calc covariance matrix
        if self.covar_method == "ledoit-wolf":
            covar = sklearn.covariance.ledoit_wolf(returns)
        elif self.covar_method == "standard":
            covar = returns.cov()
        else:
            raise NotImplementedError("covar_method not implemented")

        weights = pd.Series(
            [current_weights[x] for x in covar.columns], index=covar.columns
        )

        vol = np.sqrt(
            np.matmul(weights.values.T, np.matmul(covar.values, weights.values))
            * self.annualization_factor
        )

        # 波动率偏小
        count = 0
        if vol < self.target_volatility:
            while vol < self.target_volatility:
                count += 1
                if count > 10:
                    break

                mul = self.target_volatility / vol

                for k in target.temp["weights"].keys():
                    if k in self.exclude:  # exclude通常为债券等低风险
                        continue
                    target.temp["weights"][k] = (
                            target.temp["weights"][k] * mul
                    )

                weights = pd.Series(
                    [target.temp["weights"][x] for x in covar.columns], index=covar.columns
                )

                vol = np.sqrt(
                    np.matmul(weights.values.T, np.matmul(covar.values, weights.values))
                    * self.annualization_factor
                )

            if vol is float('NaN'):
                return True
            weights = pd.Series(
                [target.temp["weights"][x] for x in covar.columns], index=covar.columns
            )
            #print(target.temp["weights"])
            target.temp["weights"] = weights / weights.sum()
            #print(target.temp["weights"])
            return True

        for k in target.temp["weights"].keys():
            if k in self.exclude:  # exclude通常为债券等低风险
                continue
            target.temp["weights"][k] = (
                    target.temp["weights"][k] * self.target_volatility / vol
            )

        '''

        print(self.target_volatility[k] / vol,weights, new_weights)
        print(new_vol)
        '''

        return True
