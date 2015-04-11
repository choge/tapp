#!/usr/bin/env python
# -*- coding:utf-8 -*-

import matplotlib as mp
import numpy as np

def plot_roc(fp, tp):
    '''Plot the ROC curve.'''
    mp.plot(fp, tp)
