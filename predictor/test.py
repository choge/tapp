#!/usr/bin/env python
# -*- coding:utf-8 -*-

import fasta_manager
import dataset_maker
import method_ghmm
import re
#import pickle

models = {
        'sp_with_sp': "models/sp_with_sp.xml",
        #'sp_wo_sp': "models/sp_wo_sp.xml",
        'mp_with_sp': "models/mp_with_sp.xml",
        #'mp_wo_sp': "../result2/mp_wo_sp.xml",
        #'ta': "models/ta.xml",
        'ta': "models/ta2.1.2.xml",
        'no_with_sp': "models/no_with_sp.xml"
        }

files = { 
        'ta': "datasets/TA_all.fasta",
        'sp_with_sp' : 'datasets/clustered/sp_with_sp.loose.fasta',
        'mp_with_sp' : 'datasets/clustered/mp_with_sp.loose.fasta',
        'no_with_sp' : 'datasets/clustered/no_with_sp.loose.fasta'
        }
#files = { 
#        'arabidopsis'  : "../../datasets/arabidopsis_thaliana.fasta",
#        'homo_sapiens' : "../../datasets/homo_sapiens.fasta",
#        'yeast'        : "../../datasets/saccharomyces_cerevisiae.fasta"
#        }

decoder = {
        #'ta':'LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLTTTTTTTTTTTTTTTTTTTTTTTTTCCCCCG',
        'ta':'LlTTTTTTTTTTTTTTTTTTTTTTTTTCCCCCG',
        'sp_with_sp':'SSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSGGCCCCCTTTTTTTTTTTTTTTTTTTTTTTTT',
        #'sp_wo_sp':'SGGCCCCCTTTTTTTTTTTTTTTTTTTTTTTTT',
        'mp_with_sp':'SSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSGLLLLLLLLLLLLLLLLLLLLCCCCCTTTTTTTTTTTTTTTTTTTTTTTTT',
        #'mp_wo_sp':'SGLLLLLLLLLLLLLLLLLLLLCCCCCTTTTTTTTTTTTTTTTTTTTTTTTT',
        'no_with_sp': 'SSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSG'
        }

datasets = {}
results  = method_ghmm.GHMMResultSet( [] )

dm = dataset_maker.FastaDataSetMaker( fasta_manager.ProteinFastaManager )
for key in models.keys():
    datasets[key] = dm.read_from_file( files[key] )
    models[key]   = method_ghmm.HmmPredictor( models[key] )
    # たぶん、ここでmethod_ghmmとかを使わないで、method maker的な
    # クラスがゴニョゴニョしていい感じに作ってくれるようにすべき

# Do the cross-validation
written_model = {}
for model_key in models.keys():
    print("Model:%s" % model_key)
    for test_key in models.keys():
        print("\tTest:%s" % test_key)
        if model_key == test_key:
            r = models[model_key].cross_valid( datasets[test_key], fold=10 )
        else:
            r = models[model_key].predict( datasets[test_key], reverse=(model_key=='ta') )
        r.set_decoder(method_ghmm.ListDecoder(decoder[model_key]))
        r.decode2file(test_key + "_by_" + model_key + ".tsv", reverse=(model_key=='ta'))
        #r.set_name( test_key + ":" + model_key )
        # defaultで対応.
        results.add_dataset(r, test=test_key, model=model_key)

results.output_tsv("lratio.tsv", per_res=True)
results.output_tsv("ldif.tsv", which=2, per_res=True)
