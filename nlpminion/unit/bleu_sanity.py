import decoder
import sys

print decoder.per_sentence_bleu("how many works i could in heidelberg ?", ["how many different works of art can i look at in heidelberg ?"], 4)


#with open("../spoc_exp/cdec/output-translation.cdec") as f:
#  input = f.read().splitlines()
#f.close()
#with open("../data/spoc/baseship.test.tok+lc.en") as f:
#  ref = f.read().splitlines()
#f.close()

#for c, sent in enumerate(input):
#  print decoder.per_sentence_bleu(sent, ref[c])
