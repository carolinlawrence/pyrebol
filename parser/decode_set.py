import sys
import os
import tempfile, shutil
from extractor import Extractor
from smt_semparse_config import SMTSemparseConfig
from cdec import CDEC
from functionalizer import Functionalizer
import re
import time

#useage: python decode_sentence.py experiment_dir set_file
#python decode_sentence.py /workspace/osm/smt-semparse/work/cdec_train_test/intersect_stem_n100_2s set_file
if __name__ == '__main__':
  if len(sys.argv) == 3:
    experiment_dir = sys.argv[1]
    set_file = sys.argv[2]
  else:
    print "Useage: python decode_sentence.py experiment_dir st_file"
    assert False
	
  # load config
  config = SMTSemparseConfig(experiment_dir+'/settings.yaml', experiment_dir+'/dependencies.yaml')
  prep_for_sed = re.sub(r"/", r"\/", experiment_dir) 
  command="sed -ie 's/feature_function=KLanguageModel .*mrl.arpa/feature_function=KLanguageModel "+prep_for_sed+"\/mrl.arpa/g' "+experiment_dir+"/cdec_test.ini"
  os.system(command)
  command="sed -ie 's/\/.*\/train.sa/\/"+prep_for_sed+"\/train.sa/g' "+experiment_dir+"/extract.ini"
  os.system(command)
  #command="sed -ie 's/grammar=.*grammar_test/grammar=\""+prep_for_sed+"\/grammar_test/g' "+experiment_dir+"/test.inline.nl"
  #os.system(command)

  with open(set_file) as f:
    sentences = f.read().splitlines()
  f.close()
  
  # we need a temp dir!
  temp_dir = tempfile.mkdtemp()
  
  non_stemmed=[]
  for index, sentence in enumerate(sentences):
    #stem
    tmp = sentence
    if tmp[-2:] == ' .' or tmp[-2:] == ' ?':
      tmp = tmp[:-2]
    if tmp[-1:] == '.' or tmp[-1:] == '?':
      tmp = tmp[:-1]
    non_stemmed.append(tmp)
      
    sentences[index] = Extractor(config).preprocess_nl(sentence)
    #sys.stderr.write("%s\n" % sentences[index])
    #sys.stderr.write("%s\n" % tmp)
  #decode
  cdec = CDEC(config)
  cdec.decode_set(experiment_dir, sentences, temp_dir)

  #convert to bracket structure
  result = Functionalizer(config).run_set(experiment_dir, temp_dir, non_stemmed, sentences)
  for item in result:
    print "%s" % item.strip()

  #delete tmp files
  shutil.rmtree(temp_dir)

