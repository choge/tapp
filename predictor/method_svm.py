#!/usr/bin/env python
# -*- encoding:utf-8 -*-

import dataset
import svmutil
import method
import re
import os
from bitarray import bitarray
import numpy as np

class SVMPredictor( method.Method ):
    """SVMPredictor SVMを利用して予測を行う。

    LibSVMのPythonラッパーを使用している。"""
    def __init__(self, filename='', attr=None, converter=None):
        """ファイルからモデルを読み込む、あるいは、既存のデータセットから
        新たなモデルを構築する。両方してある場合はファイルからの読み込みを
        優先する。"""
        #super(SVMPredictor).__init__(self)
        self.method_name = 'svm'
        self.model = None
        if filename:
            self.load( filename )
        elif attr:
            self.model = svmutil.svm_train( attr )
        if converter:
            self.converter = converter

    def train(self, datasets, convert_args=None, svm_args=None, return_model=False, converter=None):
        """Train the SVM with a dataset.

        @param datasets a list of DataSet objects.
        The dataset will be converted to LibSVM format."""
        if isinstance(datasets, dataset.DataSet):
            datasets = [datasets]
        if convert_args is None:
            convert_args = {}
        if svm_args is None:
            svm_args = {}
        # convert dataset
        labels, features = self.convert_dataset(datasets, converter=converter, **convert_args)
        # retrieve the result
        model = svmutil.svm_train(labels, features, **svm_args)
        if return_model:
            return model
        else:
            self.model = model

    def predict(self, datasets, converter=None, model=None, convert_args=None, svm_args=None):
        """Predict datasets in dataset_dict, where the keys reperesent their
        labels."""
        if isinstance(datasets, dataset.DataSet):
            datasets = [datasets]
        if convert_args is None:
            convert_args = {}
        if svm_args is None:
            svm_args = {}
        labels, features = self.convert_dataset(datasets, converter=converter, **convert_args)
        if model == None:
            lab, acc, val = svmutil.svm_predict(labels, features, self.model, **svm_args)
        else:
            lab, acc, val = svmutil.svm_predict(labels, features, model, **svm_args)
        return self.convert_result(lab, acc, val, datasets)


    def convert_dataset(self, datasets, converter=None, regions=None, **extra):
        '''Convert the dataset into numerical forms so that SVM can resd it.

        @param datasets  A list of DataSet objects WITH LABELS.
        @param converter  A SVMConverter object for conversion of the datasets
        @param regions  A list or tuple of lists or tuples, which indicates where to
                        convert for each sequence.
        @param **extra  Extra arguments that are passes to self.converter.'''
        labels = []
        features = []
        for i in range(len(datasets)):
            ds = datasets[i]
            try:
                region = regions[i]
            except TypeError:
                # if no region has been specified, define region as an
                # empty list. The if statement below sees the length of
                # region
                region = []
            labels.extend(ds.get_labels())
            if converter == None:
                converter = self.converter
            if len(region) == len(ds):
                features.extend(
                        [converter.convert(
                            ds[j].sequence,
                            start = region[j][0],
                            end   = region[j][1],
                            **extra
                            ) for j in ds.identifiers])
            else:
                features.extend(
                        [converter.convert(ds[j].sequence, **extra)
                            for j in ds.identifiers]
                        )
        return labels, features

    def convert_result(self, lab, acc, val, datasets):
        '''Convert the result of svm-predict into easy-to-manipulate style.'''
        return SVMResult(lab, acc, val, datasets)

    def cross_valid(self, datasets, fold=5, converter=None,
                    convert_args=None, svm_args=None):
        '''Perform cross-validation. The number of folds and other options
        can be specified.'''
        if convert_args is None:
            convert_args = {}
        if svm_args is None:
            svm_args = {}
        datasets_cv = [ds.cv(fold=fold) for ds in datasets]
        # A list of lists that comprise dictionaries (!)
        # dataset_cv = [[ds1], [ds2], ..., [dsN]]
        # ds1 = [ {test:hoge, train:fuga}, {...}, ..]
        for i in range(fold):
            test, train = None, None
            for n in range(len(datasets_cv)):
                if test == None:
                    test = datasets_cv[n][i]['test']
                    test.name = 'test'
                else:
                    test.merge(datasets_cv[n][i]['test'])
                if train == None:
                    train = datasets_cv[n][i]['train']
                    train.name = 'train'
                else:
                    train.merge(datasets_cv[n][i]['train'])
            print 'test:', test
            print 'train: ', train
            model = self.train(
                    [train], converter=converter,
                    return_model=True, convert_args=convert_args,
                    svm_args=svm_args
                    )
            result = self.predict(
                    [test], converter=converter, model=model,
                    convert_args=convert_args, svm_args=svm_args
                    )
            if i == 0: # The first test
                resultset = result
            else:
                resultset.merge(result)  #, verbose=True)
        return resultset

    def grid(self, datasets, fold=5, start=-8, end=-1,
             convert_args=None, svm_args=None, converter=None):
        '''Perform Grid search for the best parameter C and γ.'''
        if convert_args is None:
            convert_args = {}
        if svm_args is None:
            svm_args = {}
        #pass


class SVMResult(dataset.DataSet):
    '''SVMResult represents the result of svm-predict.

    it enables looking for a specific sequence by an identifier
    and seeking the threshold that can divide the labels the best.'''

    def __init__(self, p_labels, p_acc, p_vals, datasets, name=''):
        '''Constructer

        @param svmresult  the returned value(s) of svm_predict method.
                          It returns 3 values (p_labels, p_acc, p_vals),
                        where all of them are lists.
        @param datasets  a list of the datasets predicted.'''
        #super(SVMResult).__init__(self)
        self.container = {}
        self.labels    = {}
        self.identifiers = []
        self.seqnum = 0
        self.name = name
        self.acc = {
                'ACC': p_acc[0],
                'MSE': p_acc[1],
                'SCC': p_acc[2]
                }
        self.data_type = dict
        for ds in datasets:
            self.identifiers.extend(ds.identifiers)
            self.labels.update(ds.labels)
        for n in range(len(self.identifiers)):
            identifier = self.identifiers[n]
            plab, pval = p_labels[n], p_vals[n]
            self.container[identifier] = {'label': plab, 'value': pval[0]}
            # Somehow pval is a list of one value/

    def get_label(self, identifier):
        '''get label'''
        if identifier in self.identifiers:
            return self.labels[identifier]
        elif identifier < self.seqnum:
            return self.labels[ self.identifiers[identifier] ]
        else:
            raise ValueError(str(identifier) + ' not found')

    def get_acc(self):
        '''return the accuracy'''
        return self.acc['ACC']

    def get_mse(self):
        '''returns the mean squared error'''
        return self.acc['MSE']

    def get_coef(self):
        '''returns squared correlation coefficient'''
        return self.acc['SCC']

    def _recalc_stats(self):
        '''Re-calculate stats such as acc and mse. This method uses methods
        from svmutil.py.'''
        predicted = [seq['label'] for seq in self]
        acc, mse, scc = svmutil.evaluations(self.get_labels(), predicted)
        self.acc = {'ACC': acc, 'MSE': mse, 'SCC':scc}

    def calc_acc(self, threshold):
        '''Calculate acc with given threshold.'''
        correct = 0
        for identifier in self.identifiers:
            seq = self[identifier]
            if self.get_label(identifier) == 1 and seq['value'] >= threshold:
                correct += 1
            elif self.get_label(identifier) == -1 and seq['value'] < threshold:
                correct += 1
        print str(correct), str(self.seqnum)
        return (0.0 + correct) / self.seqnum

    def calc_threshold(self):
        '''calculate the best threshold that can divide two datasets.'''
        maxval, maxthr = 0.0, 0.0
        dec_values = sorted([seq['value'] for seq in self], reverse=True)
        for i in range(1, len(dec_values)):
            thr = (dec_values[i] + dec_values[i - 1]) / 2
            acc = self.calc_acc(thr)
            if acc > maxval:
                maxval = acc
                maxthr = thr
        return maxval, maxthr

    def merge(self, other, do_copy=False, verbose=False):
        '''Merge the results. After meging has finished, re-calculate
        various stats such as accuracy and mse.'''
        super(self.__class__, self).merge(other, do_copy, verbose)
        self._recalc_stats()

    def roc(self):
        '''calculate true positive and false positive rate'''
        labels = bitarray([self.get_label(i) == 1 for i in self.identifiers])
        dec = [seq['value'] for seq in self]
        sorted_dec = sorted(dec, reverse=True)
        number = len(dec)
        tp_rate, fp_rate = np.zeros(number - 1), np.zeros(number - 1)
        #for thr in [(sorted_dec[i] + sorted_dec[i - 1]) / 2
        #            for i in range(1, number)]:
        for i in range(1, number):
            thr = (sorted_dec[i] + sorted_dec[i - 1]) / 2
            positive = bitarray([j >= thr for j in dec])
            tp_rate[i - 1] = (positive & labels).count(1)
            fp_rate[i - 1] = (positive & ~labels).count(1)
        tp_rate /= float(labels.count(1))
        fp_rate /= float(labels.count(0))
        auc = sum([
            (fp_rate[i] - fp_rate[i - 1]) *
            (tp_rate[i] + tp_rate[i - 1]) / 2
            for i in range(1, number - 1)])
        return tp_rate, fp_rate, auc




class SVMConverter( object ):
    """SVMConverter DataSetクラスのオブジェクトを、SVMのデータセットの形に変換する。

    どうやって変換するかをオブジェクトを作成するときに決定する。
    個々の方法はサブクラスで実装する。"""
    def __init__(self, how):
        """howで指定した方法でオブジェクトを作成する。"""
        pass

    def load(self, filename):
        """文字データを数値データに変換したい場合に用いる、特定の特徴スコア
        があるファイルを読み込む。形式はtsvかcsvでいいかな。"""
        sep = re.compile("[,\t]\s*")
        with open(filename, 'r') as f:
            for line in f:
                key, value = sep.split(line.rstrip())
                self.dic[key] = float(value)

    def normalize(self, converted, maxval=1, minval=0, normalizer='linear'):
        '''normalize the converted numerical data'''
        pass


class AA2NumConverter( SVMConverter ):
    """AA2NumConverter アミノ酸配列を数値データに変換する

    変換のためには、オブジェクトの作成時に変換方法を記述したファイルを
    読み込ませるか、あるいは文字と数値を対応づけた辞書オブジェクトを渡す。
    どちらも指定されない場合はエラーとなる。"""
    def __init__(self, filename=None, dic=None, when_missing='error'):
        """コンストラクタ。2つの引数の内どちらかが必要。

        @param filename tsvまたはcsvのファイル名。ファイルオブジェクトでも可。
        @param dic 辞書オブジェクト。
        @param when_missing 知らない文字を処理する際に、どうするか。デフォルトでは
        'error'で、知らない文字がある場合エラーを吐く。'continue'を指定することで
        知らない文字を無視して処理を続けるように設定できる。"""
        if not dic == None:
            self.dic = dic
        elif os.path.exists(filename):
            self.load(filename)
        else:
            raise ValueError("Neither filename nor dic is specified.")
        self.when_missing = when_missing

    def convert(self, string, start=0, end=None,
                normalize=True, minval=-1, maxval=1):
        """@param string 文字列。知らない(辞書にない)文字が来たら、オブジェクト作成時に
        @param start Integer specifying where to start conversion.
        @param end   Integer or None. Indicates where to terminate conversion.
        決められたとおりに振る舞う(エラーを吐くか、無視して処理するか)"""
        continue_missing = self.when_missing != 'error'
        converted = []
        string = string[start:end]
        for char in string:
            try:
                num = self.dic[char]
            except KeyError:
                if continue_missing:  # 処理を続行する。
                    continue
                else:
                    raise ValueError(char + " not found in AA2NumConverter.")
            converted.append(num)
        if normalize:
            converted = list(normalize_linear(converted, minval, maxval))
        return converted

class SpectrumKernelConverter(SVMConverter):
    '''SpectrumKernelConverter アミノ酸配列を数値データに変換する。

    こちらはSpectrum Kernelを用いる。'''

    def __init__(self, k=2, characters='ACDEFGHIKLMNPQRSTVWXY'):
        '''hoge'''
        self.k = k
        self.keys = characters
        self.keys = self.generate_keys()

    def generate_keys(self):
        '''Generate keys of k-spectrum.'''
        keys = list(self.keys)
        i = 1
        while i < self.k:
            new_keys = []
            for c in keys:
                new_keys.extend(self.expander(c))
            i += 1
            keys = new_keys
        return keys

    def expander(self, c):
        '''expand c to a list'''
        if not isinstance(c, str):
            raise TypeError('c must be a string')
        return [c + s for s in self.keys]

    def convert(self, string, start=0, end=None):
        '''@param string  文字列。この文字列からk-spectrunを作成する。
        @param start  int。ここからスタートする。
        @param end    int. Stop conversion at this position.'''
        end = len(string) if end is None else end
        parts = [string[i:i + self.k] for i in range(start, end - self.k)]
        #keys  = sorted(set(parts))
        spectrum = [parts.count(key) for key in self.keys]
        return spectrum


### OTHER UTIL FUNCTIONS ###
def check_variable(var):
    '''examine var and returns var or None'''
    try:
        var
    except NameError:
        return None
    return var

def normalize_linear(v, minval=0, maxval=1):
    '''Normalize given numbers using linear method.'''
    if not isinstance(v, np.ndarray):
        v = np.array(v)
    smallest = v.min()
    ptp = v.ptp()  # peak to peak: largest - smallest
    linear = lambda x: minval + (maxval - minval) * (x - smallest) / ptp
    # can apply linear function to the numpy array.
    return linear(v)

def normalize_sigmoid(v, gain=1):
    '''Normalize given numbers using sigmoid function.'''
    if not isinstance(v, np.ndarray):
        v = np.array(v)
    sigmoid = lambda x: 1.0 / (1.0 + np.exp(gain * x))
    return sigmoid(v)


KYTE_DOOLITTLE = {
        'I':  4.5,
        'V':  4.2,
        'L':  3.8,
        'F':  2.8,
        'C':  2.5,
        'M':  1.9,
        'A':  1.8,
        'G': -0.4,
        'T': -0.7,
        'W': -0.9,
        'S': -1.3,
        'Y': -1.6,
        'P': -3.2,
        'H': -3.5,
        'E': -3.5,
        'Q': -3.5,
        'D': -3.5,
        'N': -3.5,
        'K': -3.9,
        'R': -4.5
        }
