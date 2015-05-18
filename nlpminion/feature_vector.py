#!/usr/bin/env python
# -*- coding: utf-8 -*-
import gzip
from abstract_sparse_vector import AbstractSparseVector
from decimal import Decimal

class FeatureVector(AbstractSparseVector):

    def from_string(self, string, item_sep=" ", key_val_sep="="):
        for feature in string.split(item_sep):
            (key, val) = feature.split(key_val_sep)
            self.dict[key] = float(val)

    def from_file(self, in_file, sep=" "):
        f = open(in_file, "r")
        for line in f:
            (key, val) = tuple(line.strip().split(sep, 1))
            self.dict[key] = float(val)
        f.close()

    def from_gz_file(self, in_file, sep=" "):
        f = gzip.open(in_file, "rb")
        for line in f:
            (key, val) = tuple(line.strip().split(sep, 1))
            self.dict[key] = float(val)
        f.close()

    def to_file(self, out_file, sep=" "):
        f = open(out_file, "w")
        for key in sorted(self.dict):
            print >> f, "%s%s%s" % (key, sep, Decimal(self.dict[key]))
        f.close()

    def to_gz_file(self, out_file, sep=" "):
        f = gzip.open(out_file, "wb")
        for key in self.dict:
            f.write("%s%s%s\n" % (key, sep, Decimal(self.dict[key])))
        f.close()

    def __add__(self, x):  # x has to be a DictVector, modifies self
        for key in x.dict:
            if key in self.dict:
                self.dict[key] = self.dict[key] + x.dict[key]
            else:
                self.dict[key] = x.dict[key]
        return self

    def __sub__(self, x):  # x has to be a DictVector, modifies self
        for key in x.dict:
            if key in self.dict:
                self.dict[key] = self.dict[key] - x.dict[key]
            else:
                self.dict[key] = 0 - x.dict[key]
        return self

    def __mul__(self, x):  # x is scalar, modifies self
        for key in self.dict:
            self.dict[key] = self.dict[key] * x
        return self