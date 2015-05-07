import logging
import os
from extractor import Extractor
from functionalizer import Functionalizer
#from slot_checker import SlotChecker
from srilm import SRILM
from moses import Moses
from cdec import CDEC
from nl_reweighter import NLReweighter
from geo_world import GeoWorld
from query_comparer import QueryComparer
from bleu_scorer import BLEUScorer
from spocShip import spocShip
import re
import sys

class SMTSemparseExperiment:

  def __init__(self, config):
    self.config = config

  def run_fold(self, fold):
    logging.info('running fold %d', fold)
    self.config.put('fold', fold)
    fold_dir = os.path.join(self.config.work_dir, str(fold))
    self.config.put('experiment_dir', fold_dir)
    os.makedirs(fold_dir)
    self.run()

  def run_split(self):
    logging.info('running split')
    self.config.put('experiment_dir', self.config.work_dir)
    self.run()

  def run(self):
    logging.info('working dir is %s', self.config.experiment_dir)

    # get data
    logging.info('extracting data')
    os.system("cp "+sys.argv[1]+" "+self.config.experiment_dir+"/settings.yaml")
    os.system("cp dependencies.yaml "+self.config.experiment_dir)
    Extractor(self.config).run()

    # learn lm
    logging.info('learning LM')
    SRILM(self.config).run_ngram_count()

    # train moses
    logging.info('training TM')
    if self.config.decoder == 'moses':
      moses = Moses(self.config)
      moses.run_train()
    elif self.config.decoder == 'cdec':
      cdec = CDEC(self.config)
      cdec.run_train()

    # reweight using monolingual data
    if self.config.monolingual:
      logging.info('learning from monolingual data')
      NLReweighter(self.config).run()

    # filter disconnected rules
    if self.config.filter:
      logging.info('filtering disconnected rules')
      moses.filter_phrase_table()

    # tune moses
    if self.config.run == 'test' or self.config.run == 'all' or self.config.run == 'all_all' :
      if self.config.decoder == 'moses':
        if self.config.weights != 'mert':
          logging.info('copying tuned weights')
          os.system("cp -r "+self.config.workdir+"/"+self.config.weights+" "+self.config.experiment_dir)
          with open(self.config.experiment_dir+"/mert-work/moses.ini", "r+") as f:
            data = f.read()
            data = re.sub(r"/.*?2.*?/", r"%s/" % self.config.experiment_dir, data)#will break at the century change 2999->3000 ;) or if we travel back to the 19 hundreds for that matter..
            f.seek(0)
            f.write(data)
            f.truncate()
        else:
          logging.info('tuning TM')
          moses.run_tune()    
      elif self.config.decoder == 'cdec':
        if self.config.weights == 'mert':
          logging.info('tuning TM using mert')
          cdec.run_tune('mert')
        elif self.config.weights == 'mira':
          logging.info('tuning TM using mira')
          cdec.run_tune('mira')
        else:
          logging.info('copying tuned weights')
          os.system("cp "+self.config.workdir+"/"+self.config.weights+" "+self.config.experiment_dir)

    if self.config.retrain: 
      logging.info('retraining TM')
      if self.config.decoder == 'moses':
        moses.run_retrain()

    # decode input
    logging.info('decoding')
    if self.config.decoder == 'moses':
      moses.run_decode()
    elif self.config.decoder == 'cdec':
      cdec.run_decode()
    if self.config.neg!="":
      if self.config.decoder == 'moses':
        moses.run_decode(True)
      elif self.config.decoder == 'cdec':
        cdec.run_decode(True)

    if self.config.nlg:
      logging.info('running BLEU')
      BLEUScorer(self.config).run()
      pass

    else:
      # functionalize
      logging.info('functionalizing')
      Functionalizer(self.config).run()
      if self.config.neg!="":
        Functionalizer(self.config).run(True)

      # compare answers
      logging.info('executing queries')
      if self.config.corpus == 'geo':
        GeoWorld(self.config).run()
      elif self.config.corpus == 'spoc':
        spocShip(self.config).run()
        if self.config.neg!="":
          spocShip(self.config).run(True)
      else:
        QueryComparer(self.config).run()
