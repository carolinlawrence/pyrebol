import logging
import os
import subprocess
import gzip
import re
import time
import sys

from subprocess import Popen, PIPE, STDOUT

class CDEC:

  def __init__(self, config):
    self.config = config

  def run_train(self):
    args = [self.config.moses_train,
            '--root-dir', self.config.experiment_dir,
            '--corpus', '%s/%s' % (self.config.experiment_dir,
                                   self.config.train_name),
            '--f', self.config.src,
            '--e', self.config.tgt,
            '--first-step', '1',
            '--last-step', '3',
            '--parallel',
            '-hierarchical',
            '-glue-grammar',
            '--alignment', self.config.symm,
			'-external-bin-dir', self.config.giza]

    logging.info(' '.join(args))

    log = open('%s/train.log' % self.config.experiment_dir, 'w')
    p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=log)
    p.wait()
    nullfile = open(os.devnull, 'w')
    
    #compile for extractor
    args = [self.config.cdec_sacompile,
            '-a', '%s/model/aligned.%s' % (self.config.experiment_dir, self.config.symm),        
            '-f', '%s/%s.%s' % (self.config.experiment_dir, self.config.train_name, self.config.src),
            '-e', '%s/%s.%s' % (self.config.experiment_dir, self.config.train_name, self.config.tgt),
            '-c', '%s/extract.ini' % (self.config.experiment_dir),
            '-o', '%s/train.sa/' % (self.config.experiment_dir)]

    logging.info(' '.join(args))

    p = subprocess.Popen(args, stdin=nullfile, stdout=nullfile, stderr=log)
    p.wait()


    #extract phrase table tune
    if self.config.weights == 'mert' or self.config.weights == 'mira':
      infile = open('%s/tune.%s' % (self.config.experiment_dir, self.config.src))
      outfile = open('%s/tune.inline.%s' % (self.config.experiment_dir, self.config.src), 'w')
      args = [self.config.cdec_extractpy,
            '-g', '%s/grammar_tune/' % (self.config.experiment_dir),
            '-c', '%s/extract.ini' % (self.config.experiment_dir),
            '--tight_phrases', '0']

      logging.info(' '.join(args))

      p = subprocess.Popen(args, stdin=infile, stdout=outfile, stderr=log)
      p.wait()
      infile.close()
      outfile.close()

    #extract phrase table test
    infile = open('%s/test.%s' % (self.config.experiment_dir, self.config.src))
    outfile = open('%s/test.inline.%s' % (self.config.experiment_dir, self.config.src), 'w')
    args = [self.config.cdec_extractpy,
            '-g', '%s/grammar_test/' % (self.config.experiment_dir),
            '-c', '%s/extract.ini' % (self.config.experiment_dir),
            '--tight_phrases', '0']

    logging.info(' '.join(args))

    p = subprocess.Popen(args, stdin=infile, stdout=outfile, stderr=log)
    p.wait()
    infile.close()
    outfile.close()
   
    if self.config.neg!="":
      infile = open('%s/test_neg.%s' % (self.config.experiment_dir, self.config.src))
      outfile = open('%s/test_neg.inline.%s' % (self.config.experiment_dir, self.config.src), 'w')
      args = [self.config.cdec_extractpy,
              '-g', '%s/grammar_test_neg/' % (self.config.experiment_dir),
              '-c', '%s/extract.ini' % (self.config.experiment_dir),
              '--tight_phrases', '0']

      logging.info(' '.join(args))

      p = subprocess.Popen(args, stdin=infile, stdout=outfile, stderr=log)
      p.wait()
      infile.close()
      outfile.close()

    #create cdec_tune.ini, weights.start and cdec_test.ini
    cdec_tune = open('%s/cdec_tune.ini' % (self.config.experiment_dir), 'w')
    cdec_tune.write('formalism=scfg\n\
intersection_strategy=cube_pruning\n\
cubepruning_pop_limit=1000\n\
add_pass_through_rules=true\n\
scfg_max_span_limit=20\n\
feature_function=KLanguageModel %s/%s.arpa\n\
feature_function=WordPenalty\n\
density_prune=100\n' % (self.config.experiment_dir, self.config.tgt))
#    if self.config.pos_tune:
#      cdec_tune.write('feature_function=PassThroughNE %s\n' % self.config.pos_tune)
    if "mira" in self.config.weights:
      cdec_tune.write('\nfeature_function=RuleIdentityFeatures \n\
feature_function=RuleSourceBigramFeatures \n\
feature_function=RuleTargetBigramFeatures \n\
feature_function=RuleShape\n')
    cdec_tune.close()

    weights = open('%s/weights.start' % (self.config.experiment_dir), 'w')
    weights.write('CountEF 0.1\n\
EgivenFCoherent -0.1\n\
Glue 0.01\n\
IsSingletonF -0.01\n\
IsSingletonFE -0.01\n\
LanguageModel 0.1\n\
LanguageModel_OOV -1\n\
MaxLexFgivenE -0.1\n\
MaxLexEgivenF -0.1\n\
PassThrough -0.1\n\
SampleCountF -0.1\n\
nelist -0.9\n\
WordPenalty -0.1\n')
    #if self.config.pos_test:
    #  weights.write('PassThroughNE 2.0')
    weights.close()

    cdec_test = open('%s/cdec_test.ini' % (self.config.experiment_dir), 'w')
    cdec_test.write('formalism=scfg\n\
intersection_strategy=cube_pruning\n\
cubepruning_pop_limit=1000 \n\
scfg_max_span_limit=20 \n\
feature_function=KLanguageModel %s/%s.arpa\n\
feature_function=WordPenalty\n\
add_pass_through_rules=true\n' % (self.config.experiment_dir, self.config.tgt))
    #if self.config.pos_test:
    #  cdec_test.write('feature_function=PassThroughNE %s\n' % self.config.pos_test)
    if "mira" in self.config.weights:
      cdec_test.write('\nfeature_function=RuleIdentityFeatures \n\
feature_function=RuleSourceBigramFeatures \n\
feature_function=RuleTargetBigramFeatures \n\
feature_function=RuleShape\n')
    cdec_test.close()
    
    if self.config.corpus == 'spoc':
      cdec_val = open('%s/cdec_validate.ini' % (self.config.experiment_dir), 'w')
      cdec_val.write('formalism=scfg\n\
intersection_strategy=cube_pruning\n\
cubepruning_pop_limit=1000\n\
scfg_max_span_limit=20')
      cdec_val.close()
    log.close()

  def run_tune(self, method):  
    wd = os.getcwd()
    os.chdir(self.config.experiment_dir) #need to change to current experiment directory else dpmert folder is created where the python program was started
    log = open('%s/tune.log' % self.config.experiment_dir, 'w')
    
    if method == 'mira': 
      args = [self.config.cdec_mira,
            '-w', '%s/weights.start' % (self.config.experiment_dir),
            '-c', '%s/cdec_tune.ini' % (self.config.experiment_dir),
            '-i', '%s/tune.inline.%s' % (self.config.experiment_dir, self.config.src),
            '-r', '%s/tune.%s' % (self.config.experiment_dir, self.config.tgt)]
      logging.info(' '.join(args))
      p = subprocess.Popen(args, stdout=log, stderr=log)
      p.wait()
      
    elif method == 'mert':
      outfile = open('%s/tune.mert' % (self.config.experiment_dir), 'w')
      args = [self.config.cdec_paste,
            '%s/tune.inline.%s' % (self.config.experiment_dir, self.config.src),
            '%s/tune.%s' % (self.config.experiment_dir, self.config.tgt)]

      logging.info(' '.join(args))

      #tune with mert
      p = subprocess.Popen(args, stdout=outfile, stderr=log)
      p.wait()
      outfile.close()
      args = [self.config.cdec_tune,
            '-w', '%s/weights.start' % (self.config.experiment_dir),
            '-c', '%s/cdec_tune.ini' % (self.config.experiment_dir),
            '-d', '%s/tune.mert' % (self.config.experiment_dir)]

      if self.config.np:
        if self.config.stem:
          args += ['-g', '%s/cfg/cfg_grammar_%s.stem.train' % (self.config.data_dir, self.config.np_type)]      
        else:
          args += ['-g', '%s/cfg/cfg_grammar_%s.train' % (self.config.data_dir, self.config.np_type)]
      elif self.config.np and (self.config.run=='all_all' or self.config.run=='all'):
        if self.config.stem:
          args += ['-g', '%s/cfg/cfg_grammar_%s.all' % (self.config.data_dir, self.config.np_type)]
        else:
          args += ['-g', '%s/cfg/cfg_grammar_%s.all' % (self.config.data_dir, self.config.np_type)]

      logging.info(' '.join(args))
      p = subprocess.Popen(args, stdout=log, stderr=log)
      p.wait()
      
    log.close()
    os.chdir(wd)

  def run_decode(self, neg=False):
    if neg is True:
      args = [self.config.cdec_decode,
            '-c', '%s/cdec_test.ini' % (self.config.experiment_dir),
            '-i', '%s/test_neg.inline.%s' % (self.config.experiment_dir, self.config.src)]
    else:
      args = [self.config.cdec_decode,
            '-c', '%s/cdec_test.ini' % (self.config.experiment_dir),
            '-i', '%s/test.inline.%s' % (self.config.experiment_dir, self.config.src)]
            
    if self.config.run == 'test' or self.config.run == 'all' or self.config.run == 'all_all':
      if self.config.weights == 'mert':
        args += ['-w', '%s/dpmert/weights.final' % (self.config.experiment_dir)]      
      elif self.config.weights == 'mira':
        args += ['-w', '%s/weights.mira-final-avg.gz' % (self.config.experiment_dir)]      
      else:
        weights_file_name = re.search(".*/(.*)", self.config.weights).groups()
        args += ['-w', '%s/%s' % (self.config.experiment_dir,weights_file_name[0])]
    else:
      args += ['-w', '%s/weights.start' % self.config.experiment_dir]

    if self.config.np:
      if self.config.stem:
        args += ['-g', '%s/cfg/cfg_grammar_%s.stem.train' % (self.config.data_dir, self.config.np_type)]      
      else:
        args += ['-g', '%s/cfg/cfg_grammar_%s.train' % (self.config.data_dir, self.config.np_type)]
    elif self.config.np and (self.config.run=='all_all' or self.config.run=='all'):
      if self.config.stem:
        args += ['-g', '%s/cfg/cfg_grammar_%s.all' % (self.config.data_dir, self.config.np_type)]
      else:
        args += ['-g', '%s/cfg/cfg_grammar_%s.all' % (self.config.data_dir, self.config.np_type)]
    
    if neg is True:
      outfile = open('%s/hyp_neg.%s' % (self.config.experiment_dir, self.config.tgt), 'w')
      log = open('%s/decode.log' % self.config.experiment_dir, 'w')
    else:
      outfile = open('%s/hyp.%s' % (self.config.experiment_dir, self.config.tgt), 'w')
      log = open('%s/decode.log' % self.config.experiment_dir, 'w')
    p = subprocess.Popen(args, stdout=outfile, stderr=log)
    p.wait()
    outfile.close()
    args += ['-k', '%s' % (self.config.nbest), '-r']
    if neg is True:
      outfile = open('%s/hyp_neg.%s.nbest' % (self.config.experiment_dir, self.config.tgt), 'w')
      log = open('%s/decode_neg.log' % self.config.experiment_dir, 'w')
    else:
      outfile = open('%s/hyp.%s.nbest' % (self.config.experiment_dir, self.config.tgt), 'w')
      log = open('%s/decode.log' % self.config.experiment_dir, 'w')
    p = subprocess.Popen(args, stdout=outfile, stderr=log)
    p.wait()
    outfile.close()
    log.close()

  def decode_sentence(self, experiment_dir, sentence, temp_dir):
    wd = os.getcwd()
    os.chdir(experiment_dir)
    infile = open('%s/sent.tmp' % temp_dir, 'w')
    print >>infile, sentence
    infile.close()
    nullfile = open(os.devnull, 'w')
    #first need to get grammar
    infile = open('%s/sent.tmp' % temp_dir, 'r')
    outfile = open('%s/sent.inline.tmp' % temp_dir, 'w')
    #debug = open('debug.log', 'w')
    args = [self.config.cdec_extractpy,
            '-g', '%s/grammar/' % (temp_dir),
            '-c', '%s/extract.ini' % (experiment_dir),
            '--tight_phrases', '0']
    #print >>debug,' '.join(args)
    p = subprocess.Popen(args, stdin=infile, stdout=outfile, stderr=nullfile)
    p.wait()
    infile.close()
    outfile.close()

    #actual decoding
    if self.config.weights.strip()=="mira":
      weights_file_name = "weights.mira-final.gz"
    elif self.config.weights.strip()=="mert":
      weights_file_name = "dpmert/weights.final"    
    else:
      weights_file_name = re.search(".*/(.*)", self.config.weights).groups()[0]
    args = [self.config.cdec_decode,
            '-c', '%s/cdec_test.ini' % (experiment_dir),
            '-w', '%s/%s' % (experiment_dir,weights_file_name),
            '-k', '%s' % (self.config.nbest), '-r',
            '-i', '%s/sent.inline.tmp' % (temp_dir)]
    outfile = open('%s/nbest.tmp' % temp_dir, 'w')
    p = subprocess.Popen(args, stdin=nullfile, stdout=outfile, stderr=nullfile)
    p.wait()
    os.chdir(wd)
    return

  def decode_set(self, experiment_dir, sentences, temp_dir):
    wd = os.getcwd()
    os.chdir(experiment_dir)
    infile = open('%s/sents.tmp' % temp_dir, 'w')
    for sentence in sentences:
      print >>infile, "%s" % sentence.strip()
    infile.close()
    nullfile = open(os.devnull, 'w')
    #first need to get grammar
    infile = open('%s/sents.tmp' % temp_dir, 'r')
    outfile = open('%s/sents.inline.tmp' % temp_dir, 'w')
    #debug = open('debug.log', 'w')
    args = [self.config.cdec_extractpy,
            '-g', '%s/grammar/' % (temp_dir),
            '-c', '%s/extract.ini' % (experiment_dir),
            '--tight_phrases', '0']
    #print >>debug,' '.join(args)
    p = subprocess.Popen(args, stdin=infile, stdout=outfile, stderr=nullfile)
    p.wait()
    infile.close()
    outfile.close()

    #actual decoding
    if self.config.weights.strip()=="mira":
      weights_file_name = "weights.mira-final.gz"
    elif self.config.weights.strip()=="mert":
      weights_file_name = "dpmert/weights.final"    
    else:
      weights_file_name = re.search(".*/(.*)", self.config.weights).groups()[0]
    args = [self.config.cdec_decode,
            '-c', '%s/cdec_test.ini' % (experiment_dir),
            '-w', '%s/%s' % (experiment_dir,weights_file_name),
            '-k', '%s' % (self.config.nbest), '-r']
    infile = open('%s/sents.inline.tmp' % temp_dir, 'r')
    outfile = open('%s/nbest.tmp' % temp_dir, 'w')
    p = subprocess.Popen(args, stdin=infile, stdout=outfile, stderr=nullfile)
    p.wait()
    infile.close()
    os.chdir(wd)
    return