#!/usr/bin/env python
# -*- coding: utf-8 -*-
from feature_vector import FeatureVector


class Translation:
    def __init__(self, kbest_entry):
        self.bleu_score = None
        self.decoder_rank = None
        self.bleu_rank = None
        self.decoder_ori = None
        self.features = FeatureVector()
        (self.idval, self.string, features_raw, self.decoder_score) = tuple(kbest_entry.strip().split(" ||| "))
        self.decoder_score = float(self.decoder_score)
        self.features.from_string(features_raw)

    def __str__(self):
        return "<%s:%s:%s:%s:%s>" % (
            self.string, self.decoder_score, self.bleu_score, self.decoder_rank, self.bleu_rank)

    def __repr__(self):
        return "<%s:%s:%s:%s:%s>" % (
            self.string, self.decoder_score, self.bleu_score, self.decoder_rank, self.bleu_rank)