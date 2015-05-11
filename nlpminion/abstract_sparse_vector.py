#!/usr/bin/env python
# -*- coding: utf-8 -*-
from abc import ABCMeta
import sys

class AbstractSparseVector:
    __metaclass__ = ABCMeta

    def __init__(self):
        self.dict = {}

    def from_string(self, string, item_sep, key_val_sep):
        raise NotImplementedError()

    def from_file(self, in_file, sep):
        raise NotImplementedError()

    def from_gz_file(self, in_file, sep):
        raise NotImplementedError()

    def to_file(self, out_file, sep):
        raise NotImplementedError()

    def to_gz_file(self, out_file, sep):
        raise NotImplementedError()

    def add(self, key, val):
        self.dict[key] = val

    def pop(self, key):
        self.dict.pop(key)

    # the repr() call on a tuple causes hex to be printed ö -> \xc3\xb6g
    def __repr__(self):
        print_dict = "{"
        for key in self.dict:
            print_dict += "'%s': %s, " % (key, str(self.dict[key]))
        print_dict = print_dict[:-2]
        print_dict += "}"
        return print_dict