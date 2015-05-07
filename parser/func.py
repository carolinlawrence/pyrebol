#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import util
import sys
import parse_mrl
import re
import tempfile, shutil
import subprocess
import os

class Functionalizer:

  def __init__(self, config):
    self.config = config

  def run(self, neg=False):
    if neg is True:
      hyp_file = open('%s/hyp_neg.mrl.nbest' % self.config.experiment_dir)
      fun_file = open('%s/hyp_neg.fun' % self.config.experiment_dir, 'w')    
      f_non_stemmed = open('%s/test_neg.no_stem.nl' % self.config.experiment_dir)   
      f = open('%s/test_neg.nl' % self.config.experiment_dir)
    else:
      hyp_file = open('%s/hyp.mrl.nbest' % self.config.experiment_dir)
      fun_file = open('%s/hyp.fun' % self.config.experiment_dir, 'w')
      f_non_stemmed = open('%s/test.no_stem.nl' % self.config.experiment_dir)
      f = open('%s/test.nl' % self.config.experiment_dir)
    
    non_stemmed_lines = f_non_stemmed.readlines()
    lines = f.readlines()
      
    hypsets = []
    hypset = []
    last_eid = 0
    for line in hyp_file:
      try:
        parts = line.split('|||')
        eid = int(parts[0])
        if eid != last_eid:
          hypsets.append(hypset)
          for i in range(last_eid+1,eid):
            hypset = []
            hypsets.append(hypset)
          hypset = []
          last_eid = eid
        score = parts[2] + ' ||| ' + parts[3].strip()
        hyp = parts[1].strip()
        hypset.append((hyp,score))
      except: pass
    hypsets.append(hypset)

    counter = 0
    for hypset in hypsets:
      mrl_found = False      
      debug = open('%s/debug.log' % self.config.experiment_dir, 'a')
      hypset = list(reversed(hypset))
      while hypset:
        hyp, score = hypset.pop()
        new_hyp=""
        if self.config.insertat is True:
          for word in hyp.split():
            bool=False
            if "@" not in word: 
              correct_line_non_stemmed = non_stemmed_lines[counter].strip()
              correct_line = lines[counter].strip()
              word_pos = -1
              for stemmed_word_pos,stemmed_word in enumerate(correct_line.split()):
                if word==stemmed_word:
                  word_pos = stemmed_word_pos
              if word_pos != -1:
                non_stemmed=correct_line_non_stemmed.strip().split()[word_pos]
                new_hyp=new_hyp+non_stemmed[0].upper() + non_stemmed[1:]+"@s "
                bool=True
            if bool is False:
              new_hyp=new_hyp+word+" "
        else: new_hyp=hyp
        fun = self.functionalize(new_hyp)
        if fun:
          print >>fun_file, counter, '|||', fun, '|||', score
          mrl_found = True
          break
      if mrl_found == False: print >>fun_file, 'no mrl found'
      counter += 1      

  def run_sentence(self, experiment_dir, temp_dir, correct_line_non_stemmed, correct_line):
    hyp_file = open('%s/nbest.tmp' % temp_dir, 'r')

    hypsets = []
    hypset = []
    last_eid = 0
    for line in hyp_file:
      parts = line.split('|||')
      try:#in case there was no translation
        eid = int(parts[0])
      except:
        continue
      if eid != last_eid:
        hypsets.append(hypset)
        hypset = []
        last_eid = eid
      score = parts[2] + ' ||| ' + parts[3].strip()
      hyp = parts[1].strip()
      hypset.append((hyp,score))
    hypsets.append(hypset)
    hyp_file.close()

    counter = 0
    for hypset in hypsets:
      hypset = list(reversed(hypset))
      while hypset:
        hyp, score = hypset.pop()
        new_hyp=""
        if self.config.insertat is True:
          for word in hyp.split():
            bool=False
            if "@" not in word: 
              word_pos = -1
              for stemmed_word_pos,stemmed_word in enumerate(correct_line.split()):
                if word==stemmed_word:
                  word_pos = stemmed_word_pos
              if word_pos != -1:
                non_stemmed=correct_line_non_stemmed.strip().split()[word_pos]
                new_hyp=new_hyp+non_stemmed[0].upper() + non_stemmed[1:]+"@s "
                bool=True
            if bool is False:
              new_hyp=new_hyp+word+" "
        else: new_hyp=hyp
        fun = self.functionalize(new_hyp, experiment_dir)
        if fun:
          return fun
          break
      counter += 1
    return ""     

  def run_set(self, experiment_dir, temp_dir, non_stemmed_lines, lines):
    hyp_file = open('%s/nbest.tmp' % temp_dir, 'r')
    result_array = []
    hypsets = []
    hypset = []
    last_eid = 0
    for line in hyp_file:
      try:
        parts = line.split('|||')
        eid = int(parts[0])
        if eid != last_eid:
          hypsets.append(hypset)
          for i in range(last_eid+1,eid):
            hypset = []
            hypsets.append(hypset)
          hypset = []
          last_eid = eid
        score = parts[2] + ' ||| ' + parts[3].strip()
        hyp = parts[1].strip()
        hypset.append((hyp,score))
      except: pass
    hypsets.append(hypset)

    counter = -1
    for hypset in hypsets:
      counter += 1
      mrl_found = False      
      hypset = list(reversed(hypset))
      while hypset:
        hyp, score = hypset.pop()
        new_hyp=""
        if self.config.insertat is True:
          for word in hyp.split():
            bool=False
            if "@" not in word: 
              correct_line_non_stemmed = non_stemmed_lines[counter].strip()
              correct_line = lines[counter].strip()
              word_pos = -1
              for stemmed_word_pos,stemmed_word in enumerate(correct_line.split()):
                if word==stemmed_word:
                  word_pos = stemmed_word_pos
              if word_pos != -1:
                non_stemmed=correct_line_non_stemmed.strip().split()[word_pos]
                new_hyp=new_hyp+non_stemmed[0].upper() + non_stemmed[1:]+"@s "
                bool=True
            if bool is False:
              new_hyp=new_hyp+word+" "
        else: new_hyp=hyp
        fun = self.functionalize(new_hyp, experiment_dir)
        if fun:
          result_array.append(fun)
          mrl_found = True
          break
      if mrl_found == False: result_array.append("no mrl found")
    return result_array

  #xc = 0
  def functionalize(self, mrl, experiment_dir=""):
    if experiment_dir=="":
      experiment_dir=self.config.experiment_dir
    #if '_@0' in mrl and 'cityid@2' in mrl:
    #  #print '==='
    #  #print mrl
    #  self.xc += 1
    #  if self.xc > 5:
    #    exit()

    stack = []
    r = []
    tokens = list(reversed(mrl.split()))

    #print tokens

    while tokens:
      it = tokens.pop()
      #print it
      if util.ARITY_SEP not in it:
        token = it
        arity = util.ARITY_STR
        logging.warn('unrecognized token: %s', it)
      else:
        try:
          token, arity = it.rsplit(util.ARITY_SEP)
        except: 
          print mrl
          #sys.exit(1)
      if arity == util.ARITY_STR:
        arity = 0
        arity_str = True
      elif not (arity == util.ARITY_ANY):
        try:
          arity = int(arity)
        except:
          return None
          #sys.stderr.write("Warning: invalid arity in mrl: %s\n" %s mrl);
        arity_str = False
      
      if arity == util.ARITY_ANY or arity > 0:
        r.append(token)
        r.append('(')
        stack.append(arity)
      else:
        assert arity == 0
        if arity_str:
          r.append("'%s'" % token.replace('€', ' '))
        else:
          r.append(token)
          #print r
        while stack:
          top = stack.pop()
          if top == util.ARITY_ANY and tokens:
            r.append(',')
            stack.append(util.ARITY_ANY)
            break
          elif top != util.ARITY_ANY and top > 1:
            r.append(',')
            stack.append(top - 1)
            break
          else:
            r.append(')')

        if not stack and tokens:
          return None

    if stack:
      return None

    r = ''.join(r)

    # nasty hacks to fix misplaced _
    if '(_' in r:
      return None
    if ',_' in r and not ('cityid' in r):
      return None
    if '_),_)' in r:
      return None
      
    if self.config.corpus == 'spoc':
      #debug = open('%s/debug.log' % experiment_dir, 'a')
      temp_dir = tempfile.mkdtemp()
      args = [self.config.cdec_decode,
            '-c', '%s/cdec_validate.ini' % (experiment_dir),
            '-S', '1000',
            '-g', '%s/cfg/cfg_grammar_open' % (self.config.data_dir)]
      #if self.config.run=='all_all' or self.config.run=='all':
      #  args += ['-g', '%s/cfg/cfg_grammar_train+test' % (self.config.data_dir)]
      #  print >>debug, args
      #else:
      #  args += ['-g', '%s/cfg/cfg_grammar_train' % (self.config.data_dir)]
      #  print >>debug, args
      translate = r
      translate = re.sub(r"\(", r"( ", translate) 
      translate = re.sub(r",", r" , ", translate) 
      translate = re.sub(r"\)", r" )", translate)
      translate = re.sub(r"name:.*?@", r"name:lg@", translate)
      #print >>debug, mrl
      m = re.search("topx\( (.*?) \)", translate)
      if m:
        new_number=""
        for letter in m.group(1):
          new_number=new_number+letter+" "
        translate = re.sub(r"topx\( (.*?)\)", r"topx( "+new_number+")", translate) #when searching the end space is not included cos new_number will have one space too many at the end
      translate = re.sub(r" '.*?' ", r" ' variablehere ' ", translate) 
      infile = open('%s/sent.tmp' % temp_dir, 'w')
      print >>infile, translate
      #print >>debug, translate
      infile.close()
      infile = open('%s/sent.tmp' % temp_dir, 'r')  
      log = open('%s/parse.log' % temp_dir, 'w')
      #print >>log, "grepthis: %s" % mrl
      nullfile = open(os.devnull, 'w')
      p = subprocess.Popen(args, stdin=infile, stdout=nullfile, stderr=log)
      p.wait()
      infile.close()
      log.close()
      with open ('%s/parse.log' % temp_dir, "r") as parselog_file:
        parselog=parselog_file.read().replace('\n', '')
      #print >>debug, parselog
      #suggest_answer = parse_mrl.run_query(r, False)
      #if suggest_answer=="": return None
      #delete tmp files
      #sys.stderr.write("%s\t%s\n" % (mrl,temp_dir))
      shutil.rmtree(temp_dir)
      if "NO PARSE" in parselog: return None
    
    return r
