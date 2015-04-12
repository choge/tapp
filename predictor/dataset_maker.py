#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""DataSetMaker データセットを作る。

"""

from . import util
from . import dataset
from os.path import splitext, basename
from . import fasta_manager


class DataSetMaker(object):
    """DataSetMaker データセットを作るためのクラス。

    このクラスのサブクラスで実際に実装するよ！"""

    def __init__(self, builder, reader, data_type):
        """builder 個々の配列をどういう方法で構築するか、具体的に実装してあるクラス。
        現状だと、FastaManagerを使うかFastaMakerを使うか、選択できるようにする。
        reader ファイルなりデータベースなりを読み込むためのクラス。

        流れは、readerの属性値としてbuilderをセットする→readerはその
        builderを使って、データのリストを返す→このクラスがそれを
        data_typeに従って、DataSetクラスのインスタンスにして返す。

        両クラスとも、createメソッドで実際のFastaオブジェクトを生成している。
        今後新たなクラスを追加するときも、このインターフェースを
        継承すればおk。
        """
        self.builder = builder()
        self.reader = reader(builder)

    def read_from_file(self, filename, name='', label=None):
        """filenameのファイルから読み込む。

        readerがデータのリストを返してくれるので、それを使って
        各DataSetクラスは新しいインスタンスを生成する。
        """
        if not name:
            name, ext = splitext( basename( filename ) )
        data_list = self.reader.parse_file(filename)
        return self.data_type(data_list, name=name, origin=name, labels=label)

    def read_from_sqlite(self, dbname, query, name=""):
        """SQLite3データベースから、データセットを作成する。
        dbnameとqueryは必須。"""
        if isinstance(self.builder, type):
            self.builder = self.builder()
        data_list = []
        for r in self.reader.parse_sqlite(dbname, query):
            data_list.append(r)
        return self.data_type(data_list, name=name, origin=name)

    def create_new_maker(self, classname, baseclasses, attr):
        """自分で好きなDataSetMakerを作る。
        このとき、attrにはbuilderとreaderをセットする。"""
        return type(classname, baseclasses, attr)

    def import_from_db(self, dbname, username='', password=''):
        """データベースからデータセットをインポートする。"""
        data_list = self.reader.parse_db(dbname, username, password)
        return self.data_type(data_list)


class FastaDataSetMaker(DataSetMaker):
    """FastaDataSetMaker Fastaファイルから新しいデータセットを作る。
    """

    def __init__(self, builder=fasta_manager.ProteinFastaManager,
                       reader=FastaReader,
                       data_type=dataset.FastaDataSet):
        """builderはFastaMakerあるいはFastaManager。
        """
        self.builder = builder
        self.reader = reader(builder())
        self.data_type = data_type

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
