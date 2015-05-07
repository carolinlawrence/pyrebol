#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import subprocess
import math
import gzip
from collections import Counter  # multiset represented by dictionary
from ast import literal_eval as make_tuple


def translate(decoder_bin, ini, weights, nl_file, kbest=0):
    args = [decoder_bin,
            '-c', ini,
            '-w', weights,
            '-i', nl_file]
    if kbest!=0:
        args += ['-k', '%s' % kbest, '-r']
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (out, err) = proc.communicate()
    proc.stdout.close()
    proc.stderr.close()
    try:
        proc.kill()
    except OSError:
        pass
    return out

def translate_sentence(decoder_bin, ini, weights, nl, kbest=0):
    args = [decoder_bin,
            '-c', ini,
            '-w', weights]
    if kbest!=0:
        args += ['-k', '%s' % kbest, '-r']
    echo = subprocess.Popen(('echo', '%s' % nl), stdout=subprocess.PIPE)
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=echo.stdout)
    (out, err) = proc.communicate()
    echo.stdout.close()
    proc.stdout.close()
    proc.stderr.close()
    try:
        proc.kill()
    except OSError:
        pass
    try:
        echo.kill()
    except OSError:
        pass
    return out

def bleu(script_path, references, input):
    args = [script_path,
            '-r', references,
            '-i', input]
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (out, err) = proc.communicate()
    sys.stderr.write("out: %s\n" % out)
    sys.stderr.write("err: %s\n" % err)
    proc.stdout.close()
    proc.stderr.close()
    try:
        proc.kill()
    except OSError:
        pass
    return out

def per_sentence_bleu(nl, references, n=4, smooth=0.0):
    if nl.strip() == "":
        return 0.0  # no translation
    log_bleu = 0.0
    # get longest ref
    longest_ref = max(len(ref.split()) for ref in references)
    for i in range(1, n + 1):  # 1 to n-gram
        try:
            log_bleu += ngram(nl, references, i)
        except ValueError:
            return 0.0
    log_bleu = log_bleu / min(n, longest_ref)  # divide by n or length of ref if its lower than n
    # word penalty calculations
    input_len = len(nl.strip().split(" "))
    # adding the ref len outside the abs again allows us to pick the smaller ref when there is a draw
    diff = [math.fabs(input_len - len(ref.split())) + len(ref.split()) for enum, ref in enumerate(references)]
    best_match_length = len(references[diff.index(min(diff))].strip().split(" "))
    brevity_penalty = min(0.0, 1.0 - ((best_match_length + smooth) / input_len))
    log_bleu += brevity_penalty
    return math.exp(log_bleu)


def ngram(nl, references, n):
    input_ngrams = Counter(zip(*[nl.split(" ")[i:] for i in range(n)]))
    references_ngrams = []
    for ref in references:
        references_ngrams.append(Counter(zip(*[ref.split(" ")[i:] for i in range(n)])))
    count_input_ngrams = 0
    count_clipped = 0
    if n >= 2:
        add = 1.0
    else:
        add = 0.0
    for ngram in input_ngrams:
        count_clipped += max(ref[ngram] for ref in references_ngrams)
        count_input_ngrams += input_ngrams[ngram]
    if (count_clipped+add)==0:#means that the sentence does not even contain a unigram of the reference, would cause log(0) below so we raise here so we can catch and return 0.0 BLEU in caller function
        raise ValueError("math domain error")
    return math.log(count_clipped + add) - math.log(count_input_ngrams + add)


class Translation:
    def __init__(self, kbest_entry):
        self.bleu_score = None
        self.decoder_rank = None
        self.bleu_rank = None
        self.decoder_ori = None
        self.features = DictVector()
        (self.idval, self.string, features_raw, self.decoder_score) = tuple(kbest_entry.strip().split(" ||| "))
        self.decoder_score = float(self.decoder_score)
        self.features.from_string(features_raw)

    def __str__(self):
        return "<%s:%s:%s:%s:%s>" % (
            self.string, self.decoder_score, self.bleu_score, self.decoder_rank, self.bleu_rank)

    def __repr__(self):
        return "<%s:%s:%s:%s:%s>" % (
            self.string, self.decoder_score, self.bleu_score, self.decoder_rank, self.bleu_rank)


class DictVector:
    def __init__(self):
        self.dict = {}

    def from_string(self, string, item_sep=" ", key_val_sep="="):
        for feature in string.split(item_sep):
            (key, val) = feature.split(key_val_sep)
            self.dict[key] = float(val)

    def from_file(self, file, sep=" "):
        f = open(file, "r")
        for line in f:
            (key, val) = tuple(line.strip().split(sep, 1))
            self.dict[key] = float(val)
        f.close()

    def from_gz_file(self, file, sep=" ", value_is_tuple=False):
        f = gzip.open(file, "rb")
        for line in f:
            (key, val) = tuple(line.strip().split(sep, 1))
            val = make_tuple(val)
            if val[0] == "True":
                val[0] = True
            elif val[0] == "False":
                val[0] = False
            if value_is_tuple is True:
                self.dict[key] = val
            else:
                self.dict[key] = float(val)
        f.close()

    def to_file(self, file, sep=" "):
        f = open(file, "w")
        for key in sorted(self.dict):
            print >> f, "%s%s%s" % (key, sep, self.dict[key])
        f.close()

    def to_gz_file(self, file, sep=" "):
        f = gzip.open(file, "wb")
        for key in self.dict:
            f.write("%s%s%s\n" % (key, sep, self.dict[key]))
        f.close()

    def add(self, key, val):
        self.dict[key] = val

    def pop(self, key):
        self.dict.pop(key)

    def __str__(self):
        return str(self.dict)

    def __repr__(self):
        return str(self.dict)

    def __add__(self, x):  # x has to be a DictVector, modifies self
        # sys.stderr.write("add self: %s\n\n" % self.dict)
        # sys.stderr.write("add x: %s\n\n" % x)
        for key in x.dict:
            if key in self.dict:
                self.dict[key] = self.dict[key] + x.dict[key]
            else:
                self.dict[key] = x.dict[key]
                # sys.stderr.write("add result: %s\n\n" % self.dict)
        # sys.stderr.write("self result: %s\n\n" % self.dict)
        return self

    def __sub__(self, x):  # x has to be a DictVector, modifies self
        # sys.stderr.write("sub self: %s\n\n" % self.dict)
        # sys.stderr.write("sub x: %s\n\n" % x)
        for key in x.dict:
            if key in self.dict:
                self.dict[key] = self.dict[key] - x.dict[key]
            else:
                self.dict[key] = 0 - x.dict[key]
        # sys.stderr.write("sub result: %s\n\n" % self.dict)
        return self

    def __mul__(self, x):  # x is scalar, modifies self
        # sys.stderr.write("mult self: %s\n\n" % self.dict)
        for key in self.dict:
            self.dict[key] = self.dict[key] * x
        # sys.stderr.write("mult result: %s\n\n" % self.dict)
        return self