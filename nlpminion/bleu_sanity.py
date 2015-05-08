import sys
import decoder



#print decoder.per_sentence_bleu("how many works i could in heidelberg ?", ["how many different works of art can i look at in heidelberg ?"], 4)


#with open("../spoc_exp/cdec/output-translation.cdec") as f:
#  input = f.read().splitlines()
#f.close()
#with open("../data/spoc/baseship.test.tok+lc.en") as f:
#  ref = f.read().splitlines()
#f.close()

#for c, sent in enumerate(input):
#
#
sent = "at how many places can i go climbing in paris ?"
ref = "in how many spots can i go climbing in paris ?"
print decoder.per_sentence_bleu(sent, [ref], 4)
