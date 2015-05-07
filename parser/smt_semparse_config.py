from config import Config
import sys

class SMTSemparseConfig(Config):

  def __init__(self, settings_path, dependencies_path):
    Config.__init__(self, settings_path, dependencies_path)

    self.put('data_dir', '%s/data/%s' % (self.smt_semparse, self.corpus))

    if self.np:
      self.train_name = 'train.np'
    else:
      self.train_name = 'train'

    if self.__hasattr__('srilm'):
      self.put('lm', 'srilm')
      self.put('srilm_ngram_count', '%s/bin/%s/ngram-count' % \
                                 (self.srilm, self.srilm_arch))

    elif self.__hasattr__('kenlm'):
      self.put('lm', 'kenlm')
      self.put('lmplz', '%s/bin/lmplz' % self.kenlm)
      self.put('binary', '%s/bin/build_binary' % self.kenlm)
    else:
      print "Please specify the location of either SRILM or KENLM"
      sys.exit(1)

    if self.__hasattr__('cdec'):
      self.put('decoder', 'cdec')
      self.put('cdec_align', '%s/word-aligner/fast_align' % self.cdec)
      self.put('cdec_atools', '%s/utils/atools' % self.cdec)
      self.put('cdec_extract', '%s/extractor/run_extractor' % self.cdec)
      self.put('cdec_sacompile', '%s/extractor/sacompile' % self.cdec)
      self.put('cdec_extractpy', '%s/extractor/extract' % self.cdec)
      self.put('cdec_paste', '%s/corpus/paste-files.pl' % self.cdec)
      self.put('cdec_tune', '%s/training/dpmert/dpmert.pl' % self.cdec)
      self.put('cdec_mira', '%s/training/mira/kbest_mira' % self.cdec)
      self.put('cdec_decode', '%s/decoder/cdec' % self.cdec)
      self.put('moses_train', '%s/scripts/training/train-model.perl' % self.moses)
    elif self.__hasattr__('moses'):
      self.put('decoder', 'moses')
      self.put('moses_train', '%s/scripts/training/train-model.perl' % self.moses)
      self.put('moses_tune', '%s/scripts/training/mert-moses.pl' % self.moses)
      self.put('moses_decode_phrase', '%s/bin/moses' % self.moses)
      self.put('moses_decode_hier', '%s/bin/moses_chart' % self.moses)
      self.put('bleu_eval', '%s/scripts/generic/multi-bleu.perl' % self.moses)
    else:
      print "Please specify the location of either moses or cdec"
      sys.exit(1)

    if self.__hasattr__('wasp'):
      self.put('wasp_eval', '%s/data/geo-funql/eval/eval.pl' % self.wasp)

    if self.nlg:
      self.put('src', 'mrl')
      self.put('tgt', 'nl')
    else:
      self.put('src', 'nl')
      self.put('tgt', 'mrl')
