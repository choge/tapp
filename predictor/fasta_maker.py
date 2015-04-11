#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""FastaMaker Fastaクラスのインスタンスを生成するためのクラス群。

## こんな感じにしたい↓
factory method をパラメータ化する。このパターンの変形として、
factory method が数種類の ConcreteProduct オブジェクトを
生成できるようにしておくこともできる。factory method は、
生成するオブジェクトの種類を識別するためにパラメータを取る。
factory method が生成するすべてのオブジェクトは共通して
Product クラスのインタフェースを持つことになる。

たぶんこれによって、新しいデータベースのFastaファイルを扱わなきゃ
いけなくなったときも、ProteinFastaのサブクラスとしてその
データベースのfastaのクラスを作り、guess_databaseとcreate_fasta
の２つのメソッドを修正するだけでオーケー。"""

import os.path

class FastaMaker( object ):
    """FastaMaker Fastaクラスのインスタンスを作るクラス。

    抽象クラス。"""

    def __init__(self):
        """コンストラクタ。fasta_typeによって何を作るか決める。
        """
        pass

    def create(self, fasta):
        """Fastaオブジェクトを生成する。

        @fasta ファイルまたは文字列、タプル、リストのどれか。
        要はヘッダーと配列部分の両方が手に入ればいい。"""
        if isinstance(fasta, str):
            # fastaが文字列の場合
            pass
        elif isinstance(fasta, file):
            # fastaがファイルの場合:ただし、1ファイルに１配列の時。
            pass
        elif isinstance(fasta, list) or isinstance(fasta, tuple):
            # fastaがリストあるいはタプルの場合。
            # 一個目の要素がsequence、二個目の要素がheader。逆のがいいかな？？
            pass
        elif isinstance(fasta, dict):
            # fastaが辞書の時。Keyはsequenceとheaderにすべし。
            pass
        else:
            raise TypeError(fasta + "は正しい型ではありません。")


class ProteinFastaMaker( object ):
    """ProteinFastaMaker タンパク質のFasta配列オブジェクトを作成する。

    どのデータベース由来のfastaなのか(あるいは野良fastaなのか)を
    判別して、適切なクラスのインスタンスを作れるようにしたい。"""
    
    def __init__(self):
        """コンストラクタ。何かする必要あるかな？"""
        pass

    def create(self, fasta):
        """Fastaオブジェクトを生成する。
        あとは何も考えてない。"""
        pass

    def guess_database(self, header):
        """ヘッダー行を与えられると、そのヘッダー行がどのデータベースに
        由来するものなのかを推測する関数。
        もしかしたら、ここも何か別なクラスみたいな感じにした方が
        いいのかもしれない。"""
        if header[:3] == 'gi|':
            pass
        elif header[:4] == 'pir|':
            pass

class DNAFastaMaker( object ):
    """DNAFastaMaker DNAのFasta配列のオブジェクトを作成する。

    これも同じくどこのデータベースのものなのかを判別して、
    適切なサブクラスにしたい。こういうのってFactory Method
    パターンじゃないのかな？UML図を見るとサブクラス毎に
    ファクトリを作ってる気がするんだけど。"""
    
    def __init__(self):
        """コンストラクタ。"""
        pass

    def create_fasta(self, fasta):
        """Fastaオブジェクトを作る。
        このメソッドの中でデータベースを判別するための別の
        メソッドを呼べばいいのかな？"""
        pass

    def guess_database(self, header):
        """ヘッダー行から、由来するデータベースを推測する。"""
        pass
