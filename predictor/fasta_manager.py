#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""FastaManager Fastaクラスのインスタンスを生成する。

このクラスはFastaMakerと異なり、Factory Methodではなく
Prototypeパターンでオブジェクトを生成する。
ただし、通常のPrototypeパターンのようにインスタンスを
登録するのではなく、クラスを登録するようにしておく。
(Pythonの辞書にはクラスも格納できる!!)"""

import fasta
import re

class FastaManager( object ):
    """Manager プロトタイプを登録・管理するクラス。

    値の登録、登録された値からの適切なプロトタイプの選択などの
    基本的な機能を実装しておく。"""

    def __init__(self, default):
        """コンストラクタ。
        """
        self.regex = {} # 正規表現を持つ。
        self.prototypes = {} #
        self.default_prototype = default

    def register(self, prototype_name, prototype, regex):
        """prototype_nameに対応するクラスと正規表現を
        登録する。すでに登録してある場合は、エラー。"""
        if prototype_name in self.prototypes or prototype_name in self.regex:
            raise ValueError(prototype_name + " already registered.")
        if isinstance(regex, str):
            regex = re.compile( regex )
        if not isinstance(prototype, type):
            raise TypeError(prototype + " is not a Fasta object.")
        self.prototypes[ prototype_name ] = prototype
        self.regex[ prototype_name ] = regex

    def guess_database(self, unknown_str):
        """unknown_strがどのプロトタイプに適合するのかを
        判定し、適切なプロトタイプを返す。

        @unknown_str Fasta配列そのものを想定。"""
        # 最初の行のみを取得
        unknown_str = unknown_str.split("\n", 1)[0]
        if len( unknown_str ) == 0:
            raise ValueError("Empty string.")
        elif unknown_str[0] != '>':
            raise ValueError("")
        for prototype_name, regex in self.regex.items():
            result = regex.match( unknown_str )
            if result: # 正規表現がマッチした場合
                return self.prototypes[ prototype_name ]
        # ここまで処理が流れてくると、どのプロトタイプにもマッチしなかった
        # ということ。デフォルトのプロトタイプを返す。
        return self.default_prototype

    def create(self, unknown_str):
        """インスタンスを生成するメソッド。
        """
        prototype = self.guess_database(unknown_str)
        return prototype( unknown_str )

    def new_class(self, classname, baseclass, attr, regex):
        """動的に新しいクラスを生成して、登録します。

        @classname 新たなクラスの名前。既存のものと衝突しないものである
        必要があります。
        ＠baseclass 基底クラス。通常はFastaまたはProteinFastaあたりを指定
        すると良いと思います。
        @attr そのクラスが持つ属性値。re_identifierなどの正規表現を登録する
        必要があります。
        @regex 新たなクラスであるかどうかを判別するための正規表現です。
        """
        # 名前の衝突をチェック
        if classname in self.prototypes:
            raise ValueError(classname + "は既に登録されています。")
        # 正規表現は新たに登録する必要がある。
        required_attrs = ['re_identifier', 're_accession', 're_organism']
        for required_attr in required_attrs:
            if not required_attr in attr:
                raise ValueError(required_attr + "は必須です。")
        new_class = type( classname, baseclass, attr )
        self.register(classname, new_class, regex)

class ProteinFastaManager( FastaManager ):
    """ProteinFastaManager アミノ酸配列のFastaオブジェクトを作成する。

    あらかじめよく使うクラスを登録しておく。"""

    def __init__(self):
        """コンストラクタ"""
        self.regex = {}
        self.prototypes = {}
        self.default_prototype = fasta.BasicProteinFasta

        # SwissProt
        self.new_class('SwissProt', (fasta.BasicProteinFasta,), {
            're_identifier' : re.compile("^>sp\|[^\|]+\|(\S+) .*"),
            're_accession'  : re.compile("^>sp\|([^\|]+)\|.*"),
            're_organism'   : re.compile(".* OS=(\w+ \w+(?: [^=]+)?) .*"),
            }, re.compile("^>sp") )
        # SwissProt
        self.new_class('TrEMBLE', (fasta.BasicProteinFasta,), {
            're_identifier' : re.compile("^>tr\|[^\|]+\|(\S+) .*"),
            're_accession'  : re.compile("^>tr\|([^\|]+)\|.*"),
            're_organism'   : re.compile(".* OS=(\w+ \w+(?: [^=]+)?) .*"),
            }, re.compile("^>tr") )
        # GenBank / RefSeq
        self.new_class('GenBank_refseq', (fasta.BasicProteinFasta, ), {
            're_identifier' : re.compile("^>gi\|\d+\|ref\|([^\|]+)\|? .*"),
            're_accession'  : re.compile("^>gi\|(\d+)\|ref.*"),
            're_organism'   : re.compile(".* \[(\w+ \w+(?: \w+)?)\].*"),
            }, re.compile("^>gi\|\d+\|ref") )
