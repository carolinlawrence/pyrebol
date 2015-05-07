eval_file = open('eval.scored')
sigf_file = open('sigf_format', 'w')
    
for eval_line in eval_file.readlines():
  stat = ["0", "0", "1"]; #assumes "empty" or ""
  if eval_line.strip()=="yes":
    stat[0] = "1"
    stat[1] = "1"
  elif eval_line.strip()=="no":
    stat[1] = "1"
  print >>sigf_file, ' '.join(stat)
  