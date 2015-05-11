#!/usr/bin/env python
# -*- coding: utf-8 -*-
import gzip
from ast import literal_eval as make_tuple
from abstract_sparse_vector import AbstractSparseVector


class Cache(AbstractSparseVector):

    def from_string(self, string, item_sep="\n", key_val_sep=" ||| ", value_is_tuple=False):
        for feature in string.split(item_sep):
            (key, val) = tuple(feature.strip().split(key_val_sep, 1))
            if value_is_tuple is True:
                val = make_tuple(val)
            if val[0] == "True":
                val[0] = True
            elif val[0] == "False":
                val[0] = False
            self.dict[key] = val

    def from_file(self, in_file, sep=" |||  ", value_is_tuple=False):
        f = open(in_file, "r")
        for line in f:
            (key, val) = tuple(line.strip().split(sep, 1))
            if value_is_tuple is True:
                val = make_tuple(val)
            if val[0] == "True":
                val[0] = True
            elif val[0] == "False":
                val[0] = False
            self.dict[key] = val
        f.close()

    def from_gz_file(self, in_file, sep=" ||| ", value_is_tuple=False):
        f = gzip.open(in_file, "rb")
        for line in f:
            if line.starswith(" ||| "): #then there was no translation for this sentence, need for backward compability
                continue
            (key, val) = tuple(line.strip().split(sep, 1))
            if value_is_tuple is True:
                val = make_tuple(val)
            if val[0] == "True":
                val[0] = True
            elif val[0] == "False":
                val[0] = False
            self.dict[key] = val
        f.close()

    def to_file(self, out_file, sep=" ||| "):
        f = open(out_file, "w")
        for key in self.dict:
            f.write("%s%s%s\n" % (key, sep, self.dict[key]))
        f.close()

    def to_gz_file(self, out_file, sep=" ||| "):
        f = gzip.open(out_file, "wb")
        for key in self.dict:
            f.write("%s%s%s\n" % (key, sep, self.dict[key]))
        f.close()