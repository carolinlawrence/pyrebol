import logging
import subprocess

class KENLM:

  def __init__(self, config):
    self.config = config

  def build_lm(self):
    infile = open('%s/train.%s.lm' % (self.config.experiment_dir, self.config.tgt))
    log = open('%s/lm.log' % self.config.experiment_dir, 'w')
    outfile = open('%s/%s.arpa' % (self.config.experiment_dir, self.config.tgt), 'w')
    print '%s/train.%s.lm' % (self.config.experiment_dir, self.config.tgt)
    print '%s/%s.arpa' % (self.config.experiment_dir, self.config.tgt)
    p = subprocess.Popen([self.config.lmplz, '-o', '5'], stdin=infile, stdout=outfile, stderr=log)
    p.wait()
    infile.close()
    log.close()
    outfile.close()
