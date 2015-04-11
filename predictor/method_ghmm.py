#!/usr/bin/env python
# -*- coding:utf-8 -*-

import ghmm
import predictor.method as method
import predictor.dataset as dsclass
from math import ceil
import re
from bitarray import bitarray
#from array import array
import numpy as np


class HmmPredictor(method.Method):
    """HmmPredictor 隠れマルコフモデルに予測を扱うクラス。

    GHMMライブラリのPythonバインディングのラッパー。
    たいていの要素はすでにGHMMの方で定義してあるので、
    あとはMethodクラスのAPIに合わせるだけ。

    現状では、タンパク質配列のことしか考えていないので、
    余裕があればghmm一般のテンプレート的なクラスと、
    アミノ酸配列用のクラスに分けるべき。"""

    emission_domain = ghmm.Alphabet("ACDEFGHIKLMNPQRSTVWY")
    invalid_chars   = "BJOUXZ"

    def __init__(self, filename='', attr={}):
        """ファイルからの読み込みをメインにしたい。
        filenameが指定してあれば、そのファイルから読み込む。
        filenameがなく、attrが指定してあれば、そこから
        HMMFromMatricesを使って作る。"""
        self.method_name = 'ghmm'
        self.model_file = ''
        if filename:
            self.load(filename)
        elif attr:
            self.method = ghmm.HMMFromMatrices(**attr)
        else:
            raise ValueError("filenameもattrも設定されていません。")

    def load(self, filename):
        """filenameにあるモデルを読み込む。
        読み込みにはghmmのHMMOpenを用いている。"""
        self.model_file = filename
        self.method = ghmm.HMMOpen(filename)

    def save(self, filename):
        """filenameにモデルを保存する。"""
        if isinstance(self.method, ghmm.HMM):
            self.method.write(filename)
        else:
            raise ValueError("Something is wrong.")

    def initialize(self, attr={}):
        """ファイルから登録してモデルを作成していた場合、
        再び読み直して新たなモデルとする。そうじゃない場合は
        もう一回パラメータを要求している。
        もうちょっとスマートな方法があればいいんだけど。"""
        if self.model_file:
            self.load(self.model_file)
        elif attr:
            self.method = ghmm.HMMFromMatrices(**attr)
        else:
            raise ValueError("filenameもattrも設定されていません。")

    def convert_dataset(self, dataset, reverse=False):
        """datasetをghmmのデータセットオブジェクトに変換する。
        ghmm.SequenceSet()を作っている。
        reverseがTrueならば、各データを逆順にして登録する。"""
        seqset = []
        # 一応変な文字があるかもしれないので消しておく。
        #self.delete_invalid_char()
        for seq in dataset:
            sequence = seq.sequence
            # 不正な文字を削除する
            sequence = sequence.replace('X', '')
            sequence = sequence.replace('U', '')
            sequence = sequence.replace('B', '')
            sequence = sequence.replace('Z', '')
            # reverseがTrueなら逆順にする。
            if reverse:
                sequence = sequence[::-1]
            seqset.append(sequence)
        return ghmm.SequenceSet(self.emission_domain, seqset)

    def train(self, dataset, how='baumWelch', reverse=False):
        """datasetを使って、モデルを訓練する。"""
        dataset_tmp = self.convert_dataset(dataset, reverse)
        if how == 'baumWelch':
            self.method.baumWelch(dataset_tmp)
        else:
            raise ValueError("訓練する方法が指定されていません。")
        #return self.convert_result(result_tmp, dataset)

    def convert_result(self, result_list, dataset):
        """result_listをPredictionResultクラスのオブジェクトに
        変換する。datasetがないと辞書っぽくできないので
        エラー。"""
        return GHMMResult(result_list, dataset, dataset.name)

    def predict(self, dataset, how='viterbi', reverse=False):
        """datasetを予測する。"""
        dataset_tmp = self.convert_dataset(dataset, reverse)
        if how == 'viterbi':
            result_tmp = self.method.viterbi(dataset_tmp)
        else:
            raise ValueError("訓練する方法が指定されていません。")
        return self.convert_result(result_tmp, dataset)

    def cross_valid(self, dataset, fold=5, reverse=False, train=True):
        """datasetを用いてクロスバリデーションを行う。
        """
        datasets_for_cv = dataset.cv(fold=fold)
        result_of_cv = None
        for dic in datasets_for_cv:
            self.initialize()
            self.train(dic['train'], reverse=reverse)
            r = self.predict(dic['test'], reverse=reverse)
            if result_of_cv == None:
                result_of_cv = r
            else:
                result_of_cv.merge(r)
        if train:
            self.train(dataset, reverse=reverse)
        return result_of_cv


class GHMMResult(dsclass.PredictionResult):
    """GHMMResult GHMMの結果を格納する。

    IDとの紐付け、クロスバリデーションを行った際に出てくる
    複数の結果をまとめるなどを考えている。"""

    def __init__(self, result_list, dataset, name):
        """result_list ghmm.HMM.viterbi()で帰ってくるリスト。
        正確には、予測した配列が複数なら、
        [ [[パス1], [パス2], ..], [尤度1, 尤度2, ..] ]
        単数なら[ [0,1,..], -100] という形。最初がパス、次が
        Likelihood。。。だったはず。"""
        self.data_type = dict
        self.container = {}
        self.labels = {}
        self.identifiers = []
        self.seqnum = 0
        self.name = name
        self.decoder = None
        identifiers = dataset.identifiers
        if isinstance(result_list[1], list):
            # 複数配列を予測したとき。
            if len(result_list[0]) != len(identifiers):
                raise ValueError("予測結果の数と指定されたIDの数が一致しません。"
                        + "prediction :" + str(len(result_list[0]))
                        + "Identifiers:" + str(len(identifiers)))
            for i in range(len(identifiers)):
                # 個々の配列毎に
                identifier = identifiers[i]
                self.container[identifier] = {'path': result_list[0][i],  # list
                        'likelihood': result_list[1][i],
                        'sequence': dataset[identifier].sequence,
                        'seqlen'  : len(dataset[identifier].sequence) }  # dict
            self.identifiers = identifiers
            self.seqnum = len(identifiers)
        else:
            # 予測した配列が一つの時
            self.container[identifiers[0]] = result_list[0]
            self.identifiers = identifiers
            self.seqnum = 1
        ## ラベルをアップデートする
        self.labels.update(dataset.labels)

    def likelihood(self, index):
        """indexに対応する配列のLikelihoodを求める。
        """
        return self[index]['likelihood']

    def set_decoder(self, decoder):
        """decodeメソッドのために、整数値とデコード後の文字を
        対応させる。decoderは、整数値を与えると文字を返すもの
        なら何でも良い。"""
        self.decoder = decoder

    def decode(self, index, if_set=False, reverse=True):
        """整数値の配列であるpathを、わかりやすい文字列に
        デコーディングする。疎水性だとH、みたいな感じで。
        if_set==Trueならば、デコードした値をインデクスに対応する
        レコードの'decoded'として辞書に登録する。"""
        decoded = ""
        for s in self[index]['path']:
            decoded += self.decoder.decode(s)
        if if_set:
            self[index]['decoded'] = decoded
        return decoded[::-1] if reverse else decoded

    def decode_all(self, col=60, reverse=False):
        """全部デコーディングする。ファイルに書き出すのではなく、
        Generatorを使用して、呼び出し元でfor文なんかで回せるように
        しておく。ファイルに書いたりはそっちでやるってことで。"""
        for seqid in self.identifiers:
            decoded = self.decode(seqid, reverse=reverse)
            sequence = self[seqid]['sequence']
            txt      = { 'id':seqid, 'seq':[], 'path':[], 'header':'>'+seqid,
                    'raw_seq':sequence, 'raw_path':decoded}
            for k in range( int(ceil( (float(len(sequence)))/col) ) ):
                start = k*col
                end   = (k+1)*col if (k+1)*col <= len(sequence) else len(sequence)
                txt['seq'].append( sequence[start:end] )
                txt['path'].append( decoded[start:end] )
            yield txt

    def decode2file(self, filename, col=60, reverse=False):
        '''Decode all sequences to filename.'''
        with open(filename, 'w') as f:
            for seqid in self.identifiers:
                decoded = self.decode(seqid, reverse=reverse)
                sequence = self[seqid]['sequence']
                f.write('>' + seqid + ' likelihood=' + str(self.likelihood(seqid)) + "\n")
                for k in range(int(ceil(float(len(sequence)))/col)):
                    start = k*col
                    if (k + 1) * col <= len(sequence):
                        end = (k + 1) * col
                    else:
                        end = len(sequence)
                    f.write('Seq : ' + sequence[start:end] + "\n")
                    f.write('Path: ' + decoded[start:end] + "\n\n")

    def find_positions(self, identifier, seq, reverse=False):
        '''Find positions that match seq for a decoded sequence
        This method returns the start position and the end position.
        If there is no match, returns None, None'''
        if 'decoded' in self[identifier]:
            decoded = self[identifier]['decoded']
        else:
            decoded = self.decode(identifier, reverse=reverse)
        if hasattr(seq, 'search'):  # Maybe a regex object/
            seq = seq
        else:
            seq = re.compile(seq)
        m = seq.search(decoded)
        if m:  # If seq matches in decoded, m is a MatchObject (which is True)
            start = m.start()
            end   = m.end()
            return start + 1, end
        else:  # No matches
            return None, None

class HmmPredictorSet(method.Method):
    '''HmmPredictorSet is a class that manages several HmmPredictor objects.
    This combines each predictor and its result, and calculate some dicision
    values from them.
    For now, this class assumes the problem as 2-class classification.
    (Means multi-class classification and regression are not supported)'''

    def __init__(self, models={}):
        '''Constructer.
        @param models  a dictionary having "+1" and "-1" as keys'''
        self.method_name = 'hmm_set'
        self.methods = (models['+1'], models['-1'])

    def train(self, datasets):
        '''Train all predictors by given datasets.'''
        pass


class Decoder( object ):
    """Decoder HMMのPathを表す整数値から、状態を表す文字列を返す。

    decodeメソッドに整数値を渡すことによって、必要な文字を返してくれる。
    実装的にはリスト/タプルを使うか、辞書を使うか、かな。。"""
    def decode(self, index):
        """indexは整数値。返す値は文字。"""
        pass

class ListDecoder(Decoder):
    """ListDecoder タプルを用いてデコーディングを行う。

    状態の数が少ないときはこちらを用いるのがよい。と思う。"""
    def __init__(self, lst):
        """コンストラクタ。タプルをそのまま登録する。"""
        self.lst = lst

    def decode(self, index):
        """単純に対応する値を返す。"""
        return self.lst[index]

    def register(self, indices, val):
        """値をセットする。indeicesはリスト、文字列でも可。
        リストの場合は一括して、文字列の場合はsplicingの要領で
        値をセットする."""
        if isinstance(indices, int):
            self.lst[indices] = val
        elif isinstance(indices, list) or isinstance(indices, tuple):
            for i in indices:
                self.lst[i] = val
        elif isinstance(indices, str):
            start, end, interval = str.split(":")
            for i in range(start, end, interval):
                self.lst[i] = val

class GHMMResultSet(dsclass.DataSet):
    """GHMMResultSet GHMMResultのデータセット。

    GHMMResultは、一つのモデルのパスと尤度を持っているもの
    だが、たくさんのモデルの尤度を比較したりする際に不便。
    そのため、個々のID毎に、モデルによる尤度の差を比べる事
    が出来るようにする。"""

    def __init__(self, ghmmresults):
        """ghmmresultsはGHMMResultクラスのインスタンスのリスト。
        identifiersはデータセットの名前。"""
        self.data_type = dict
        self.container = {}
        self.identifiers = []
        self.models = []
        self.seqnum = 0
        self.dataset_num = 0
        self.labels = {}
        for r in ghmmresults:
            self.add_dataset(r)

    def add_dataset(self, dataset, test="", model=""):
        """datasetをこのセットに加える。"""
        if dataset is not []:
            self.dataset_num += 1
        if not test:
            test = dataset.name
        if not model:
            model = dataset.name
        #if model in self.models:
        #    model += "_"
        if not model in self.models:
            self.models.append( model )
        for i in dataset.identifiers:
            seq = dataset[i]
            if i in self.container:
                self.container[i][model] = seq
            else:
                self.container[i] = {model: seq, 'origin': test}
                self.seqnum += 1
                self.identifiers.append(i)
        self.labels.update(dataset.labels)

    def compare_likelihood(self):
        """Likelihoodの比を出す。
        self.container[id]['ratio'][hoge_fuga]に格納"""
        models = self.models
        for i in range(len(models)):
            numer = models[i]
            for j in range(i+1, len(models)):
                denom = models[j]
                name = numer + "_" + denom
                for i in self.identifiers:
                    if not 'ratio' in self.container[i]:
                        self.container[i]['ratio'] = {}
                    r = self.container[i][numer]['likelihood'] / self.container[i][denom]['likelihood']
                    self.container[i]['ratio'][name] = r

    def get_seqlen(self, i):
        """i番目あるいはIDがiであるような配列の配列長を取り出す。"""
        return len( self[i][ self.models[0] ]['sequence'] )

    def compare_likelihood2(self):
        """Likelihoodを配列の長さで割り、その差を取ったものを
        計算する。"""
        models = self.models
        for k in range(len(models)):
            n = models[k]
            for j in range(k+1, len(models)):
                d = models[j]
                name = n + "-" + d
                for i in self.identifiers:
                    if not 'diff' in self.container[i]:
                        self.container[i]['diff'] = {}
                    r = self.container[i][n]['likelihood'] - self.container[i][d]['likelihood']
                    self.container[i]['diff'][name] = r / self.get_seqlen(i)

    def fisher_ld(self, origins=['ta', '*']):
        '''Perform Fisher's linear discriminant.

        For now, this functions as two-class discrimination only.
        @param origins  specify the classes'''
        #v1 = np.array([])
        pass

    def get_lratio(self, identifier, numer, denom):
        """numerのLikelihoodをdenomのLikelihoodで割った値を得る。
        ratio自体がまだ無い場合は先に計算する。
        登録されている値と逆の順番の場合、単純に逆数を返す。"""
        # まずはratioを計算してあるかチェック
        if not 'ratio' in self[identifier]:
            self.compare_likelihood()
        # 次にnumer_denomという値があるかチェック
        if numer + "_" + denom in self[identifier]['ratio']:
            return self[identifier]['ratio'][numer + "_" + denom]
        elif denom + "_" + numer in self[identifier]['ratio']:
            return 1 / self[identifier]['ratio'][denom + "_" + numer]
        else:
            raise ValueError("Not found( " + numer + ", " + denom + ")")

    def get_ldiff(self, identifier, numer, denom):
        """長さで割ったLikelihoodの差"""
        if not 'diff' in self[identifier]:
            self.compare_likelihood2()
        # 次にnumer_denomという値があるかチェック
        if numer + "-" + denom in self[identifier]['diff']:
            return self[identifier]['diff'][numer + "-" + denom]
        elif denom + "-" + numer in self[identifier]['diff']:
            return -1 * self[identifier]['diff'][denom + "-" + numer]
        else:
            raise ValueError("Not found( " + numer + ", " + denom + ")")

    def get_origin(self, identifier):
        """originを(あれば)返す。"""
        if 'origin' in self[identifier]:
            return self[identifier]['origin']

    def get_likelihood(self, identifier, model=''):
        """Likelihoodを返す。modelを指定しない場合、すべてのモデル
        のものを含むdictを返す。"""
        if model == '':
            l = {}
            for m in self.models:
                l[m] = self[identifier][m]['likelihood']
        elif isinstance(model, list) or isinstance(model, tuple):
            l = {}
            for m in model:
                if m in self.models:
                    l[m] = self[identifier][m]['likelihood']
        else:
            l = self[identifier][model]['likelihood']
        return l

    def get_by_origin(self, origin):
        """(あれば)originによって配列を取得する。"""
        return [ self[i] for i in self.identifiers if self[i]['origin'] == origin ]

    def iter_by_origin(self, origin):
        """Return a generator for each sequence with 'origin'."""
        for i in self.identifiers:
            if self[i]['origin'] == origin:
                yield self[i]
            else:
                continue

    def get_id_by_origin(self, origin):
        """上のとほとんど同じだけど、こちらはIDを返す。"""
        return [ i for i in self.identifiers if self[i]['origin'] == origin ]

    def output_tsv(self, filename, models=[], which=1, per_res=False ):
        """filenameにタブ区切り形式で結果を出力する。"""
        f = open( filename, 'w')
        if len(models) == 0:
            models = self.models
        # Write the header lines
        f.write("id\torigin\tseqlen",)
        for m in models:
            f.write("\t" + m)
        for j in range(len(models)):
            m1 = models[j]
            for k in range(j+1, len(models)):
                m2 = models[k]
                f.write("\t" + m1 + "_" + m2)
        f.write("\n")
        # Done writing the header line
        # Write each likelihood
        for i in self.identifiers:
            f.write(i + "\t" + self.get_origin(i))
            f.write("\t" + str(self.get_seqlen(i)) )
            for m in models:
                if per_res:
                    f.write("\t" + str(self.get_likelihood(i, m) / self.get_seqlen(i)))
                else:
                    f.write( "\t" + str(self.get_likelihood(i, m)) )
            # Done writing each likelihood
            # Write ratio of likelihoods
            #for m1 in models:
            for j in range(len(models)):
                m1 = models[j]
                #for m2 in models:
                for k in range(j+1, len(models)):
                    m2 = models[k]
                    if which == 1:
                        f.write("\t" + str(self.get_lratio(i, m1, m2)) )
                    elif which == 2:
                        f.write("\t" + str(self.get_ldiff(i, m1, m2)) )
            f.write("\n")
        f.close()

    def roc(self, origins, mode='raw'):
        """Plot an ROC curve with sequences with specified origin."""
        origin_list = {i: self.get_origin(i) for i in self.identifiers}
        labels = bitarray([self.get_label(i) == 1
                  for i in self.identifiers
                  if origin_list[i] in origins])
        dec = [self.get_likelihood(i, model=origin_list[i])
               for i in self.identifiers
               if origin_list[i] in origins]
        sorted_dec = sorted(dec, reverse=True)
        number = len(dec)
        tp_rate, fp_rate = np.zeros(number - 1), np.zeros(number - 1)
        #for thr in [(sorted_dec[i] + sorted_dec[i - 1]) / 2 for i in range(1, number)]:
        for i in range(1, number):
            thr = (sorted_dec[i] + sorted_dec[i - 1]) / 2
            positive = bitarray([j >= thr for j in dec])
            tp_rate[i - 1] = (positive & labels).count(1)
            fp_rate[i - 1] = (positive & ~labels).count(1)
        tp_rate /= float(number)
        fp_rate /= float(number)
        auc = sum([
            (fp_rate[i] - fp_rate[i - 1]) *
            (tp_rate[i] + tp_rate[i - 1]) / 2
            for i in range(1, number - 1)])
        return tp_rate, fp_rate, auc
