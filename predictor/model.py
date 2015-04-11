#!/usr/bin/env python
# -*- coding:utf-8 -*-

import method
import method_ghmm


class Model(object):
    """Model 予測手法のモデルを表すクラス。

    主な属性として、データセット(複数可?)、予測手法(GHMMへのブリッジなど)
    を持つ。また、予測結果を表すオブジェクトも持っていた方がいいかも。

    Abstract Factoryパターンで生成したい。
    どんなデータ(DataSet)を、どんな手法で(Method)予測する、というのを
    指定すると、いい感じに作ってくれて、あとはどういう手法由来かをあまり
    気にせずにクロスバリデーションしたり結果を表示したりできるといい。"""

    def __init__(self, datasets, method, logfile=None):
        """Modelクラスのオブジェクトを作る。

        datasetsはDataSetクラスのオブジェクトなら何でもおk。
        methodも、Methodクラスのオブジェクトなら何でもおk。
        logfileは、ファイル名(str)か、ファイルオブジェクト。"""
        self.datasets = datasets
        self.dataset_alias = {}
        self.method = method
        self.results = []
        self.graphtool = None
        self.logfile = logfile

    def __str__(self):
        """文字列として表現する。表現する内容は、データセットの内容、
        手法の名前、予測結果をすでに持っているかどうか、など。"""
        pass

    def open_logfile(self):
        """logfileを開く。すでにself.logfileがファイルオブジェクトなら、
        何もしない。"""
        if isinstance(self.logfile, file):
            return
        else:
            pass

    def print2log(self, message):
        """logfileに情報を記録する。"""
        self.logfile.write(message)

    def add_dataset(self, dataset, alias=''):
        """新たなデータセットを追加する。名前もつけられるようにして
        おこうか(alias的な感じで)"""
        self.datasets.append( dataset )
        if not alias:
            if dataset.name:
                alias = dataset.name
            else:
                alias = len(self.datasets)
        self.dataset_alias[alias] = dataset

    def set_method(self, method):
        """self.methodに手法を登録する。今のところ登録できる手法は一つの
        モデルにつき一つにする予定。"""
        pass

    def predict_all(self, if_store=False):
        """self.datasets内のデータすべてに対して予測を行い、
        その結果を返す or self.results内に蓄える。"""
        pass

    def cv_all(self, fold=5, if_store=False):
        """self.datasets内のデータを用いて、self.methodの手法で
        クロスバリデーションを行う。その後、PredictionResultクラスの
        インスタンスを返す。if_storeオプションを指定すると、
        self.resultに結果を蓄えておく。"""
        pass

    def train(self):
        """既に持っているデータを使って、モデルを訓練する。"""
        pass

    def roc(self, names, choose_random=False):
        """ROC curveを描く。
        names どのデータセットについてやるか
        choose_random ランダムに何個かずつ選んでROCを描く
        """
        pass


class HMM(Model):
    """HMM 隠れマルコフモデル。

    """

    def __init__(self, datasets, logfile, method=method_ghmm.HmmPredictor):
        """コンストラクタ？GHMMを使う。"""
        self.datasets = datasets
        self.logfile = logfile
        self.method = method
        self.dataset_alias = {}
