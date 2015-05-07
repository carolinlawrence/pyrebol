#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import rebol
from pyminion import decoder


def hope_fear(kbest_list, action, rank=False):
    if action == 'hope':
        if rank is True:
            search_list = [entry.decoder_rank + entry.bleu_rank for entry in kbest_list]
            index = search_list.index(max(search_list))
            # sys.stderr.write("hope rank max: %s for %s\n" % (max(search_list),kbest_list[index]))
        else:
            search_list = [entry.decoder_score + entry.bleu_score for entry in kbest_list]
            index = search_list.index(max(search_list))
            # sys.stderr.write("hope max: %s for %s\n" % (max(search_list),kbest_list[index]))
    elif action == 'fear':
        if rank is True:
            search_list = [entry.decoder_rank - entry.bleu_rank for entry in kbest_list]
            index = search_list.index(max(search_list))
            # sys.stderr.write("fear rank max: %s for %s\n" % (max(search_list),kbest_list[index]))
        else:
            search_list = [entry.decoder_score - entry.bleu_score for entry in kbest_list]
            index = search_list.index(max(search_list))
            # sys.stderr.write("fear max: %s for %s\n" % (max(search_list),kbest_list[index]))
    else:
        sys.stderr.write("\nInvalid action: Options are either 'hope' or 'fear'\nEXITING\n")
        sys.exit(1)
    return index


def rampion(kbest_list, references, rank):  # references is a list potentially containing more than 1 reference
    top1_equals_ref = False
    for ref in references:
        if kbest_list[0].string == ref:
            top1_equals_ref = True
    if top1_equals_ref:
        hope = kbest_list[0]
        fear = kbest_list[hope_fear(kbest_list, 'fear', rank)]
        type_update = 1
    else:
        fear = kbest_list[0]
        hope = kbest_list[hope_fear(kbest_list, 'hope', rank)]
        type_update = 2
    return hope, fear, type_update


# references is a list potentially containing more than 1 reference
def rebol_fear_neg_top1(kbest_list, references, rank, fb, gold_answer, nl_parser, cache, ref_search_type=0):
    if fb is True:  # top 1 becomes hope
        type_update = 1
        hope = kbest_list[0]
        if kbest_list[0].string not in references:
            references.append(kbest_list[0].string)
        # update to use this (1) or all references (2) in bleu scores. else we stick to the initial scores
        if ref_search_type == 1:
            for entry in kbest_list:
                entry.bleu_score = decoder.per_sentence_bleu(entry.string, [kbest_list[0].string])
        elif ref_search_type == 2:
            for entry in kbest_list:
                entry.bleu_score = decoder.per_sentence_bleu(entry.string, references)
        fear = kbest_list[hope_fear(kbest_list, 'fear', rank)]
        # skip fear if it gets the right answer
        if rebol.execute_sentence(fear.string, gold_answer, nl_parser, cache)[0] is True:
            type_update *= -1
    else:
        type_update = 2
        fear = kbest_list[0]
        if ref_search_type == 2:
            for entry in kbest_list:
                entry.bleu_score = decoder.per_sentence_bleu(entry.string, references)
        hope = kbest_list[hope_fear(kbest_list, 'hope', rank)]
    return hope, fear, type_update, references


# references is a list potentially containing more than 1 reference
def rebol_light(kbest_list, references, rank, fb, gold_answer, nl_parser, cache, ref_search_type=0):
    if fb is True:  # top 1 becomes hope
        type_update = 1
        hope = kbest_list[0]
        if kbest_list[0].string not in references:
            references.append(kbest_list[0].string)
        # update to use this (1) or all references (2) in bleu scores. else we stick to the initial scores
        if ref_search_type == 1:
            for entry in kbest_list:
                entry.bleu_score = decoder.per_sentence_bleu(entry.string, [kbest_list[0].string])
        elif ref_search_type == 2:
            for entry in kbest_list:
                entry.bleu_score = decoder.per_sentence_bleu(entry.string, references)
    else:
        type_update = 2
        if ref_search_type == 2:
            for entry in kbest_list:
                entry.bleu_score = decoder.per_sentence_bleu(entry.string, references)
        hope = kbest_list[hope_fear(kbest_list, 'hope', rank)]
    fear = kbest_list[hope_fear(kbest_list, 'fear', rank)]
    # skip fear if it gets the right answer
    if rebol.execute_sentence(fear.string, gold_answer, nl_parser, cache)[0] is True:
        type_update *= -1
    return hope, fear, type_update, references


# references is a list potentially containing more than 1 reference
# own_trans_ref is a list with Translation objects
def rebol_too_full(kbest_list, references, fb, gold_answer, max_spot, nl_parser, cache, own_trans_ref, ref_search_type=0):
    hope = None
    fear = None
    if fb is True:  # top 1 becomes hope
        type_update = 1
        hope = kbest_list[0]
        if kbest_list[0].string not in references:
            references.append(kbest_list[0].string)
            own_trans_ref.append(kbest_list[0])
        # update to use this (1) or all references (2) in bleu scores. else we stick to the initial scores
        if ref_search_type == 1:
            for entry in kbest_list:
                entry.bleu_score = decoder.per_sentence_bleu(entry.string, [kbest_list[0].string])
        elif ref_search_type == 2:
            for entry in kbest_list:
                entry.bleu_score = decoder.per_sentence_bleu(entry.string, references)
        # get fear
        for count, entry in enumerate(
                sorted(kbest_list, key=lambda translation: translation.decoder_score-translation.bleu_score, reverse=True)):
            if count == 0:
                continue  # we already checked top1
            if count == max_spot:
                break  # we do not want to look beyond max_spot
            if rebol.execute_sentence(entry.string, gold_answer, nl_parser, cache)[0] is False:
                fear = entry
                break
    elif len(own_trans_ref) > 0:  # we fall back to a previously found correct sentence as our hope
        hope = own_trans_ref[0]  # TODO which do we choose as hope if there is more than 1
        type_update = 2
        fear = kbest_list[0]
    else:
        type_update = 2
        fear = kbest_list[0]
        if ref_search_type == 2:
            for entry in kbest_list:
                entry.bleu_score = decoder.per_sentence_bleu(entry.string, references)
        # get hope
        for count, entry in enumerate(
                sorted(kbest_list, key=lambda translation: translation.decoder_score+translation.bleu_score, reverse=True)):
            if count == 0:
                continue  # we already checked top1
            if count == max_spot:
                break  # we do not want to look beyond max_spot
            if rebol.execute_sentence(entry.string, gold_answer, nl_parser, cache)[0] is True:
                hope = entry
                break
    return hope, fear, type_update, references, own_trans_ref


# references is a list potentially containing more than 1 reference
# own_trans_ref is a list with Translation objects
def exec_only(kbest_list, references, fb, gold_answer, max_spot, nl_parser, cache, own_trans_ref):
    hope = None
    fear = None
    hope_idx = 0
    if fb is True:  # top 1 becomes hope
        type_update = 1
        hope = kbest_list[0]
        if kbest_list[0].string not in references:
            references.append(kbest_list[0].string)
            own_trans_ref.append(kbest_list[0])
    elif len(own_trans_ref) > 0:  # we fall back to a previously found correct sentence as our hope
        hope = own_trans_ref[0]  # TODO which do we choose as hope if there is more than 1
        type_update = 2
    else:  # we search the nbest list (ordered by decocder score) for a sentence with correct answer
        # that will become our hope, else hope remains None
        for count, entry in enumerate(kbest_list):
            if count == 0:
                continue  # we already checked top1
            if count == max_spot:
                break  # we do not want to look beyond max_spot
            if rebol.execute_sentence(entry.string, gold_answer, nl_parser, cache)[0] is True:
                hope_idx = count  # so we can skip it when looking for fear
                hope = entry
                break
        type_update = 2
    # find fear
    for count, entry in enumerate(kbest_list):
        if count == 0 or count == hope_idx:
            continue  # we already checked top1 & that hope
        if count == max_spot:
            break  # we do not want to look beyond max_spot
        if rebol.execute_sentence(entry.string, gold_answer, nl_parser, cache)[0] is False:
            fear = entry
            break
    if hope is None or fear is None:
        type_update *= -1
    return hope, fear, type_update, references, own_trans_ref