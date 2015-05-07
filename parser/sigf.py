import sys

class SIGF:
  def __init__(self, config):
    self.config = config
    
  def run(self):
    eval_file = open('%s/eval_true.scored' % (self.config.experiment_dir))
    sigf_file = open('%s/sigf_format' % (self.config.experiment_dir), 'w')
    
    for eval_line in eval_file.readlines():
      stat = ["0", "0", "1"]; #assumes "empty" or ""
      if eval_line.strip()=="yes":
        stat[0] = "1"
        stat[1] = "1"
      elif eval_line.strip()=="no":
        stat[1] = "1"
      print >>sigf_file, ' '.join(stat)
      
    eval_file.close()
    sigf_file.close()
    
    eval_file = open('eval_true.scored')
    eval_file_neg = open('eval_true_neg.scored')
    sigf_file = open('sigf_format_fdr', 'w')
   
    #contains TP & FN   
    for eval_line in eval_file.readlines():
      stat = ["0", "0"]; #assumes "empty" or "" or "no"->fn
      if eval_line.strip()=="yes":#tp
        stat[0] = "1"
        stat[1] = "1"
      print >>sigf_file, ' '.join(stat)

    #contains FP & TN
    for eval_line in eval_file_neg.readlines():
      stat = ["1", "0"]; #assumes "empty" or "" or "no"->tn
      if eval_line.strip()=="yes":#fp
        stat[0] = "0"
        stat[1] = "1"
      print >>sigf_file, ' '.join(stat)

    eval_file.close()
    eval_file_neg.close()
    sigf_file.close()
  
