#!/usr/bin/env python
# -*- coding: utf-8 -*-
from abc import ABCMeta

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

    def __str__(self):
        return str(self.dict)

    def __repr__(self):
        return str(self.dict)