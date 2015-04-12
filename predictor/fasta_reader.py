#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""util いろいろユーティリティーだとおもう。
"""

import os
import sqlite3
#import predictor.fasta_manager

class FastaReader( object ):
    """FastaUtil A utility class for fasta sequences.

    hogehoge
    """

    def __init__(self, builder, protein=True):
        """Constructor.
        """
        self.manager = builder

    def parse_file(self, filename, protein=True):
        """複数のfasta配列が入ってるファイルをパースして、
        Fastaオブジェクトのリストにして返す。とりあえず
        アミノ酸配列だけ対応したよ。"""
        if os.path.exists( filename ):
            f = open( filename, 'r' )
        else:
            raise ValueError(filename + " not found.")

        seq = ''
        fasta_list = []
        #seq_num = 0
        for line in f:
            if line == '' or line == "\n" or line[0] == '#':
                continue
            elif len( seq ) > 0 and line[0] == '>':
                #seq_num += 1
                fasta_list.append( self.manager.create(seq) )
                seq = line
            else:
                seq += line
        ## Add the last line
        fasta_list.append( self.manager.create(seq) )
        return fasta_list

    def parse_sqlite(self, dbname, query='', username='', password=''):
        """SQLite3のデータを読み込み、そこからデータセットを作る。"""
        con = sqlite3.connect(dbname)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute(query)
        for r in cur:
            txt = '>' + r['name'] + "\n" + r['sequence']
            yield self.manager.create(txt)
        con.close()
