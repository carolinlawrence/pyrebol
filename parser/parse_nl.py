#!/usr/bin/env python
# -*- coding: utf-8 -*-
import parse_mrl
import sys
import os
import tempfile, shutil
from extractor import Extractor
from smt_semparse_config import SMTSemparseConfig
from cdec import CDEC
from functionalizer import Functionalizer
import re


class NLParser:
    def __init__(self, experiment_dir):
        self.experiment_dir = experiment_dir
        # load config
        self.config = SMTSemparseConfig(experiment_dir + '/settings.yaml', experiment_dir + '/dependencies.yaml')
        prep_for_sed = re.sub(r"/", r"\/", experiment_dir)
        command = "sed -ie 's/feature_function=KLanguageModel .*mrl.arpa/feature_function=KLanguageModel " + prep_for_sed + "\/mrl.arpa/g' " + experiment_dir + "/cdec_test.ini"
        os.system(command)
        command = "sed -ie 's/= .*train.sa/= " + prep_for_sed + "\/train.sa/g' " + experiment_dir + "/extract.ini"
        os.system(command)

    def process_sentence(self, sentence):
        # stem
        non_stemmed = sentence
        if non_stemmed[-2:] == ' .' or non_stemmed[-2:] == ' ?':
            non_stemmed = non_stemmed[:-2]
        if non_stemmed[-1:] == '.' or non_stemmed[-1:] == '?':
            non_stemmed = non_stemmed[:-1]

        sentence = Extractor(self.config).preprocess_nl(sentence)

        # we need a temp dir!
        temp_dir = tempfile.mkdtemp("", "semparse_process_sentence")

        # decode
        cdec = CDEC(self.config)
        cdec.decode_sentence(self.experiment_dir, sentence, temp_dir)

        # convert to bracket structure
        mrl = Functionalizer(self.config).run_sentence(self.experiment_dir, temp_dir, non_stemmed, sentence)

        # delete tmp files
        shutil.rmtree(temp_dir)

        answer = parse_mrl.run_query(mrl, 0)
        return (mrl, answer)

    def process_set(self, sentences):

        # we need a temp dir!
        temp_dir = tempfile.mkdtemp("", "semparse_process_set")

        non_stemmed = list(sentences)
        for counter, sentence in enumerate(sentences):
            # stem
            if non_stemmed[counter][-2:] == ' .' or non_stemmed[counter][-2:] == ' ?':
                non_stemmed[counter] = non_stemmed[counter][:-2]
            if non_stemmed[counter][-1:] == '.' or non_stemmed[counter][-1:] == '?':
                non_stemmed[counter] = non_stemmed[counter][:-1]

            sentence = Extractor(self.config).preprocess_nl(sentence)


        # decode
        cdec = CDEC(self.config)
        cdec.decode_set(self.experiment_dir, sentences, temp_dir)

        # convert to bracket structure
        mrls = Functionalizer(self.config).run_set(self.experiment_dir, temp_dir, non_stemmed, sentences)

        # delete tmp files
        shutil.rmtree(temp_dir)

        answers = []
        for counter, mrl in enumerate(mrls):
            answers.append(parse_mrl.run_query(mrl, 0))

        return (mrls, answers)