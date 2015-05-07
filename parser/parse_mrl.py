#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pyparsing import *
import automated_query
import re
import sys
#MRL=MRL,MRL
#MRL=FN(MRL)
#MRL=FN(KV)


def run_query(mrl_sentence, count, return_answer=True):    
  function_name = Word(alphas)
  start_bracket = Literal("(")
  add = Literal(",")
  end_bracket = Literal(")")
  #key_value = Word(alphanums)+Literal("=")+Literal("'")+Word(alphanums)+Literal("'")
  key_value = CharsNotIn("()")
  mrl = Forward()
  mrl << function_name+(start_bracket+(mrl+add+mrl|mrl|key_value)+end_bracket)
  mrl << function_name+(start_bracket+(mrl+add+mrl+add+mrl+add+mrl|mrl+add+mrl+add+mrl|mrl+add+mrl|mrl|key_value)+end_bracket)

  def pop_beginning(counter):
    try:
      recover_query.pop()
      recover_query.pop(0)
      recover_query.pop(0)
    except:
      return ""
  
  def pop_end(counter):
    try:
      for x in range(5):
        recover_query.pop()
    except:
      return ""
    
  #sys.stderr.write(str(line_counter)+"\n")
  try:
    parse = mrl.parseString(mrl_sentence)
  except:
    #sys.stderr.write("Warning: Parsing error on mrl "+mrl_sentence+"\n");
    return ""
  recover_query = list(parse)
  query=""
  type=0 #1: findkey, 2: count, 3: least, 4: latlong
  topx=0#at least x nodes must exist or x nodes must be returned
  key=""#key to be found with type=1
  nodup=False#switch to true for no duplicates
  maxmin=0#1 to get max, 2 to get min
  #print mrl_sentence, "->", parse
  #print parse.key_value
  for counter, ele in enumerate(parse):
    if parse[counter]=="findkey":
      type = 1
      pop_beginning(counter)
    elif parse[counter]=="count":
      type = 2
      pop_beginning(counter)
    elif parse[counter]=="least":
      type = 3
      pop_beginning(counter)
    elif parse[counter]=="latlong":
      type = 4
      pop_beginning(counter)
    elif parse[counter]=="nodup":
      nodup = True
      pop_beginning(counter)
    elif parse[counter]=="max":
      maxmin = 1
      pop_beginning(counter)
    elif parse[counter]=="min":
      maxmin = 2
      pop_beginning(counter)
    elif parse[counter]=="key":
      try:
        key = parse[counter+2]#check to make sure this never leads to out of index error
        pop_end(counter)
      except:
        return ""
    elif parse[counter]=="topx":
      try:
        topx = int(parse[counter+2])#same as prev
        pop_end(counter)
      except:
        return ""
    #else:
    #  query+=parse[counter]
    counter+=1
  for ele in recover_query:
    query+=ele
  query = re.sub(r"keyval\((.*?),(.*?)\)", r"\1=\2", query)
  query = query.replace("(", "[")
  query = query.replace(")", "]")
  if "area" in query:
    #query = re.sub(r"(area)(.*?)", r"\1->.a;\2", query) 
    query = re.sub(r"(area\[.*?\]),(.*?)", r"\1->.a;\2", query) 
    query = re.sub(r"node(\[.*?\])(.*?)", r"node(area.a)\1;\2", query) 
    query = re.sub(r"way(\[.*?\])(.*?)", r"way(area.a)\1;\2", query) 
    query = re.sub(r"relation(\[.*?\])(.*?)", r"relation(area.a)\1;\2", query) 
  else:
    query = re.sub(r"(node\[.*?\])(.*?)", r"\1;\2", query) 
    query = re.sub(r"(way\[.*?\])(.*?)", r"\1;\2", query) 
    query = re.sub(r"(relation\[.*?\])(.*?)", r"\1;\2", query) 
  query+="out;"
  #query = re.sub(r"(.*?)\[([a-z])=(.*?)", r"\1[\"\2\"=\3", query) #is a-z enough?
  #print query
  query = query.replace(",", "][")
  #query = query.replace("='", "=\\\"")
  #query = query.replace("~'", "~\\\"")
  #query = query.replace("']", "\\\"]")
  query = query.replace("='", "=\"")
  query = query.replace("~'", "~\"")
  query = query.replace("']", "\"]")
  query = query.replace("=\"~\"", "~\"\"")#hack to fix misplaced regex indicator: ~
  #reverse the character protection
  query = query.replace("XXXQUOT", "\\\"")
  query = query.replace("XXXOPEN", "\(")
  query = query.replace("XXXCLOSE", "\)")
  query = query.replace("XXXEOPEN", "\[")
  query = query.replace("XXXECLOSE", "\]")
  query = query.replace("XXXSEP", ",")
  query = query.replace("xxd", ".")
  query = query.replace("xxq", "'")
  query = query.replace("xxs", "/")
  query = query.replace("xatx", "@")
  if return_answer==False: 
    return query
  answer = automated_query.execute_query(count, query, type, topx, key, nodup, maxmin)
  #print "another trial: "+automated_query.execute_query(query, type, topx, key, nodup, maxmin)#for some reason it does not return the right answer even though it should (it worked before)
  #print "suggested answer 1st: "+answer
  return answer
  