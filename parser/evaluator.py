import logging
import os

class Evaluator:

  def __init__(self, config):
    self.config = config

  def run(self, neg=False):  
    if self.config.run == 'debug':
      s_p, s_r, s_f = self.score('%s/1' % self.config.work_dir, neg)
    elif self.config.run == 'dev':
      s_p = 0
      s_r = 0
      s_f = 0
      for i in range(10):
        p, r, f = self.score('%s/%d' % (self.config.work_dir, i), neg)
        s_p += p
        s_r += r
        s_f += f
      s_p /= 10
      s_r /= 10
      s_f /= 10
    elif self.config.run == 'test' or self.config.run == 'all' or self.config.run == 'all_all' :
      if neg is True:
        s_p, s_r, s_f = self.score(self.config.work_dir, False)
        s_p_neg, s_r_neg, s_f_neg = self.score(self.config.work_dir, True)
        s_p_e, s_tnr_e, s_f_e, s_fdr_e = self.score_extensive(self.config.work_dir)
      else:
        s_p, s_r, s_f = self.score(self.config.work_dir, neg)
    
    print 'p: %f, r: %f, f: %f' % (s_p, s_r, s_f)
    logging.info('p: %f, r: %f, f: %f' % (s_p, s_r, s_f))
    if neg is True:
      print 'negative set: p: %f, r: %f, f: %f' % (s_p_neg, s_r_neg, s_f_neg)
      print 'alternative eval: p: %f, tnr: %f, f: %f' % (s_p_e, s_tnr_e, s_f_e)
      logging.info('negative set: p: %f, r: %f, f: %f' % (s_p_neg, s_r_neg, s_f_neg))
      logging.info('alternative eval: p: %f, tnr: %f, f: %f, fdr: %f' % (s_p_e, s_tnr_e, s_f_e, s_fdr_e))


  def score(self, experiment_dir, neg=False):
    alt_string=""
    if neg is True:
      result_file = open('%s/eval_true_neg.scored%s' % (experiment_dir,alt_string)) #adds "_alt" if we want to eval the alt file
    else:
      result_file = open('%s/eval_true.scored%s' % (experiment_dir,alt_string))
    tp = 0
    fp = 0
    count = 0
    for line in result_file.readlines():
      count += 1
      tag = line.strip()
      if tag == 'empty':
        continue
      if self.config.corpus!="spoc":
        tag, score = tag.split()
        score = float(score)
      if tag == 'yes':
        tp += 1
      elif tag == 'no':
        fp += 1

    try:
      p = 1.0 * tp / (tp + fp)
    except:
      p = 0
    r = 1.0 * tp / count
    if (p+r)==0:
      f=0
    else:
      f = 2.0 * p * r / (p + r)

    return (p, r, f)
    
  def score_extensive(self, experiment_dir):
    result_file_neg = open('%s/eval_true_neg.scored' % (experiment_dir))
    result_file = open('%s/eval_true.scored' % (experiment_dir))
    tp = 0 #correct english, correct answer
    fp = 0 #inccorrect english, correct answer
    tn = 0 #incorrect english, wrong answer
    fn = 0 #correct english, wrong answer
    count_total = 0
    for line in result_file.readlines():#correct english: tp or fn
      count_total += 1
      tag = line.strip()
      if tag == 'yes':
        tp += 1
      elif tag == 'no' or tag == 'empty':
        fn += 1
    for line in result_file_neg.readlines():#incorrect english: fp or tn
      count_total += 1
      tag = line.strip()
      if tag == 'yes':
        fp += 1
      elif tag == 'no' or tag == 'empty':
        tn += 1
    print "tp: %f, fn: %f, fp: %f, tn: %f" % (tp,fn,fp,tn)  
    logging.info('tp: %f, fn: %f, fp: %f, tn: %f' % (tp,fn,fp,tn)) 
    p = 1.0 * tp/(tp+fp)
    tnr = 1.0 * tn/(tn+fp)
    f = 2.0 * p * tnr / (p + tnr)
    dfr = 1.0 * fp/(tp+fp)
    #f=0.0
    return (p, tnr, f, dfr)
