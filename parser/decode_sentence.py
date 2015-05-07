import sys
import os
import tempfile, shutil
from extractor import Extractor
from smt_semparse_config import SMTSemparseConfig
from cdec import CDEC
from functionalizer import Functionalizer
import re
import time

#useage: python decode_sentence.py experiment_dir sentence_file
#python decode_sentence.py /workspace/osm/smt-semparse/work/cdec_train_test/intersect_stem_n100_2s "How many different works of art can I look at in Heidelberg?"
if __name__ == '__main__':
  sentence = ''
  if len(sys.argv) == 3:
    experiment_dir = sys.argv[1]
    sentence = sys.argv[2]
  else:
    print "Useage: python decode_sentence.py experiment_dir sentence_file"
    assert False
	
  # load config
  config = SMTSemparseConfig(experiment_dir+'/settings.yaml', experiment_dir+'/dependencies.yaml')
  prep_for_sed = re.sub(r"/", r"\/", experiment_dir) 
  command="sed -ie 's/feature_function=KLanguageModel .*mrl.arpa/feature_function=KLanguageModel "+prep_for_sed+"\/mrl.arpa/g' "+experiment_dir+"/cdec_test.ini"
  os.system(command)
  command="sed -ie 's/= .*train.sa/= "+prep_for_sed+"\/train.sa/g' "+experiment_dir+"/extract.ini"
  os.system(command)
  #command="sed -ie 's/grammar=.*grammar_test/grammar=\""+prep_for_sed+"\/grammar_test/g' "+experiment_dir+"/test.inline.nl"
  #os.system(command)

  #stem
  non_stemmed = sentence
  if non_stemmed[-2:] == ' .' or non_stemmed[-2:] == ' ?':
    non_stemmed = non_stemmed[:-2]
  if non_stemmed[-1:] == '.' or non_stemmed[-1:] == '?':
    non_stemmed = non_stemmed[:-1]
      
  sentence = Extractor(config).preprocess_nl(sentence)
  #print non_stemmed
  #print sentence
  # we need a temp dir!
  temp_dir = tempfile.mkdtemp()

  #decode
  cdec = CDEC(config)
  cdec.decode_sentence(experiment_dir, sentence, temp_dir)

  #convert to bracket structure
  result = Functionalizer(config).run_sentence(experiment_dir, temp_dir, non_stemmed, sentence)
  
  print result
  #sys.stderr.write("%s\t%s\n" % (result,temp_dir))
  
  #delete tmp files
  shutil.rmtree(temp_dir)

