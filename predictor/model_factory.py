#!/usr/bin/env python
# -*- coding:utf-8 -*-

from . import model
from . import fasta_maker
from . import fasta_manager
from . import dataset_maker

class ModelFactory(object):
    """ModelFactory Modelを生成するためのクラス。

    Abstract Factory.
    このクラスのに引数をつけて、どんなモデルを構築するか
    決定する。"""

    def __init__(self):
        """コンストラクタ。何もしないでいいよね。"""
        pass


class ModelBuilder(object):
    """ModelBuilder Modelを生成する。こちらは色々組み合わせて作る系。

    FastaManager的な感じで。"""

    default_fasta_parser = fasta_manager.ProteinFastaManager()
    default_dataset_maker = dataset_maker.FastaDataSetMaker()

    def __init__(self, fasta_parser=None, dataset_maker=None):
        """コンストラクタ。何も指定しないと、デフォルトの値を用いる。"""
        if fasta_parser == None:
            self.fasta_parser = self.default_fasta_parser
        else:
            self.fasta_parser = fasta_parser

        if dataset_maker == None:
            self.dataset_maker = self.default_dataset_maker
        else:
            self.dataset_maker = dataset_maker

    def start(self, name):
        """nameという名前のモデルの構築を開始する。"""
        m = model.Model()
        ## 腹減った。帰るか。
        return m
