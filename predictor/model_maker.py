#!/usr/bin/env python
# -*- coding:utf-8 -*-

import model


class ModelMaker(object):
    """ModelMaker 複数のデータセットと一つの手法からなるモデルを構築する。

    1: どんなデータセットを持っているか
    2: どんな手法で予測するのか
    3: その他細々したこと(ログファイルとか)
    を指定する感じ？"""

    def __init__(self):
        """たぶん何にもしない。"""
        pass

    def make(self, datasets, methods, logfile):
        """直接引数を与えて作成する。あまり賢くはないが簡単。
        """
        m = model.Model(datasets, methods, logfile)
        return m

    def construct(self):
        """順番に作成していく。"""
        self.m = model.Model()

    def add_dataset(self, dataset):
        """datasetを追加する。"""
        pass
