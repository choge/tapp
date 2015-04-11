#!/usr/bin/env python
# -*- coding:utf-8 -*-

import method_ghmm
import dataset_maker
import re

model_name = 'ta'
#model_file = 'models/ta.xml'
model_file = 'models/ta2.1.xml'
#prediction_name = 'no_with_sp'
prediction_name = 'ta'
prediction_file = 'datasets/TA_all.fasta'
#prediction_file = '../TA_classifier/stat/blast/saccharomyces_cerevisiae.fasta'
reversed = True
foldnum  = 10

dm = dataset_maker.FastaDataSetMaker()
data = dm.read_from_file(prediction_file, name=prediction_name)
model = method_ghmm.HmmPredictor(filename=model_file)

decoder_list = {
        #'ta':'LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLTTTTTTTTTTTTTTTTTTTTTTTTTCCCCCG',
        'ta': 'LLTTTTTTTTTTTTTTTTTTTTTTTTTCCCCCG',
        'sp_with_sp':'SSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSGGCCCCCTTTTTTTTTTTTTTTTTTTTTTTTT',
        #'sp_wo_sp':'SGGCCCCCTTTTTTTTTTTTTTTTTTTTTTTTT',
        'mp_with_sp':'SSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSGLLLLLLLLLLLLLLLLLLLLCCCCCTTTTTTTTTTTTTTTTTTTTTTTTT',
        #'mp_wo_sp':'SGLLLLLLLLLLLLLLLLLLLLCCCCCTTTTTTTTTTTTTTTTTTTTTTTTT',
        'no_with_sp': 'SSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSG'
        }

decoder = method_ghmm.ListDecoder(decoder_list[model_name])

#result = model.predict(data, reverse=reversed)
result = model.cross_valid(data, fold=foldnum, reverse=True)
result.set_decoder(decoder)

tmd = re.compile('T+')
for dic in result.decode_all(reverse=reversed):
        id = dic['id']
        likelihood = result.likelihood(id)
        tmd_match = tmd.search(dic['raw_path'])
        if tmd_match:
            tmd_pos = str(tmd_match.start()) + ":" + str(tmd_match.end())
        else:
            tmd_pos = "N/A"

        dic['header'] += ' likelihood=' + str(likelihood) + ' tmd=' + tmd_pos
        print dic['header']
        for l in range(len(dic['seq'])):
            print 'Seq : ' + dic['seq'][l]
            print 'Path: ' + dic['path'][l] + "\n"
model.save('ta2.1.3.xml')
