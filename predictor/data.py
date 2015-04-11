#!/usr/bin/env python
# -*- coding:utf-8 -*-

class Data( object ):
    """Data データを表す。インターフェース的な感じのクラス。
    """

    def connect_db(self, query=''):
        """データを取ってきたデータベースにクエリーを投げる。
        """
        pass
