#!/usr/bin/env python
# -*- coding: utf-8 -*-
import optparse
import sys
import subprocess
from xml.dom import minidom
import warnings
import re

def parseToString(list):
  counter = 0
  return_string=""
  for ele in list:
    if counter==0:
      return_string += ele
    else:
      return_string += ", " + ele
    counter+=1
  return return_string

#TODO: add support for parsing opening hours
def findKeyGetValue(query, output, maxmin, key, nodup, topx):
  try:
    xmldoc = minidom.parseString(output)
    itemlist = xmldoc.getElementsByTagName('tag') 
    collect_answer = []
    counter = 0
    for ele in itemlist :
      if ele.attributes['k'].value==key:
        replaced = re.sub(r"^_(.*?)", r"\1", ele.attributes['v'].value)     
        replaced = replaced.replace("_", " ");        
        replaced = replaced.replace(",", ";");
        replaced = replaced.split(";");
        for rep in replaced:
          rep = re.sub(r"^ +(.*?)", r"\1", rep)       
          rep = re.sub(r"(.*?) +$", r"\1", rep)     
          collect_answer.append(rep)
          counter+=1
          if counter==topx: return parseToString(collect_answer)
    if nodup: return parseToString(list(set(collect_answer)))
    if maxmin==1:
      return max(collect_answer)
    elif maxmin==2:
      return min(collect_answer)
    return parseToString(collect_answer)
  except:
    sys.stderr.write("Warning: Parsing error on xml output of query: "+query+"\n");
  #return "I don't have the necessary information to answer this question"
  return ""

def countNodes(query, output):
  try:
    xmldoc = minidom.parseString(output)
    total = 0
    itemlist = xmldoc.getElementsByTagName('node') 
    total = total + len(itemlist)
    itemlist = xmldoc.getElementsByTagName('way') 
    total = total + len(itemlist)
    itemlist = xmldoc.getElementsByTagName('relation') 
    total = total + len(itemlist)
    return str(total)
  except:
    sys.stderr.write("Warning: Parsing error on xml output of query: "+query+"\n");
  return "0"

def atLeastX(query, output, topx):
  try:
    xmldoc = minidom.parseString(output)
    total = 0
    itemlist = xmldoc.getElementsByTagName('node')
    total = total + len(itemlist)
    itemlist = xmldoc.getElementsByTagName('way')
    total = total + len(itemlist)
    itemlist = xmldoc.getElementsByTagName('relation')
    total = total + len(itemlist)
    if total>=topx: return "yes"
  except:
    sys.stderr.write("Warning: Parsing error on xml output of query: "+query+"\n");
  return "no"


def getLatLon(query, output, topx):
  try:
    xmldoc = minidom.parseString(output)
    itemlist = xmldoc.getElementsByTagName('node') 
    latlon = ""
    counter = 0
    for ele in itemlist :
      if ele.attributes['lat'].value and ele.attributes['lon'].value:
        if counter==0:
          latlon += "%s %s" % (ele.attributes['lat'].value, ele.attributes['lon'].value)
        else:
          latlon += ", %s %s" % (ele.attributes['lat'].value, ele.attributes['lon'].value)
      counter+=1
      if topx == counter: break
    #print "latlon: "+latlon
    return latlon
  except:
    sys.stderr.write("Warning: Parsing error on xml output of query: "+query+"\n");
  return ""

#TODO: check that right combinations where provided
def execute_query(count, query, type, topx=0, key="", nodup=False, maxmin=0):
  #assumes that $EXEC_DIR and $DB_DIR are correctly set
  proc = subprocess.Popen('$EXEC_DIR/bin/osm3s_query --db-dir=$DB_DIR',
                        shell=True,
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        )
  stdout_value, stderr_value = proc.communicate(query)
  proc.stdin.close()
  proc.stdout.close()
  proc.stderr.close()
  try:
    proc.kill()
  except OSError:
    pass
  output=""
  #sys.stderr.write("Grepthis: "+str(len(stdout_value))+"\n");
  if len(stdout_value)>999999: #max output length of xml doc, if the output is too large, minidom.parseString cannot handle it and we have very high memory usage 
    sys.stderr.write("Warning: The xml output on the following query is considered too long: "+query+"\n");
    return ""
  if len(stdout_value)>0: 
    output = stdout_value
  else:
    sys.stderr.write("Warning: Parsing error on query "+str(count)+": "+query+"\n");
    return ""

  #print query
  #print stderr_value
  #print output
  #print count
  
  if type==1:
    return findKeyGetValue(query, output, maxmin, key, nodup, topx).encode('utf-8')
  elif type==2:
    return countNodes(query, output)
  elif type==3:
    return atLeastX(query, output, topx)
  elif type==4:
    return getLatLon(query, output, topx).encode('utf-8')
  else:
    return ""