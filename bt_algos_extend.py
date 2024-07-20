import bt


class SelectTopK(bt.AlgoStack):
    def __init__(self, signal, K, sort_descending=True, all_or_none=False, filter_selected=False):
        super(SelectTopK, self).__init__(bt.algos.SetStat(signal),
                                         bt.algos.SelectN(K, sort_descending, all_or_none, filter_selected))
