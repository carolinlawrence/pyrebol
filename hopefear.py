#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import rebol
from nlpminion import decoder
import operator


def hope_fear(kbest_list, action, rank=False):
    '''
    Given a k-best list, finds a hope or fear translation.
    Hope: y+ = decoder_score - (1 - bleu_score)
    Hope: y- = decoder_score + (1 - bleu_score)
    
    :param kbest_list: a kbest_list which is a list containing Translation entries
    :param action: either 'hope' or 'fear'
    :param rank: True if the rank values should be taken rather than the actual
    scores
    '''
    if action == 'hope':
        if rank is True:
            search_list = [entry.decoder_rank + entry.bleu_rank for entry in kbest_list]
            index = search_list.index(max(search_list))
        else:
            search_list = [entry.decoder_score + entry.bleu_score for entry in kbest_list]
            index = search_list.index(max(search_list))
    elif action == 'fear':
        if rank is True:
            search_list = [entry.decoder_rank - entry.bleu_rank for entry in kbest_list]
            index = search_list.index(max(search_list))
        else:
            search_list = [entry.decoder_score - entry.bleu_score for entry in kbest_list]
            index = search_list.index(max(search_list))
    else:
        sys.stderr.write("\nInvalid action: Options are either 'hope' or 'fear'\nEXITING\n")
        sys.exit(1)
    return index


def rampion(kbest_list, references, rank):  # references is a list potentially containing more than 1 reference
    '''
    Finds hope and fear in rampion fashion (Gimpel & Smith, 2012)
    
    :param kbest_list: a kbest_list which is a list containing Translation entries
    :param references: the references for this sentence
    :param rank: a boolean that is true if rank instead of scores should be used
    
    :return: a tuple containing the Translation object that is hope and another
    that is fear, also returns type_update which is 1 to indicate that the top 1
    is equal to a references and 2 otherwise
    '''
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
    '''
    Finds hope and fear in rebol fashion. The top 1 becomes the hope if the
    parser returns the correct answer and the fear otherwise. The missing element
    is found in rampion fashion. If the fear is true the example can be skipped
    (indicated by the type_update variable)
    
    :param kbest_list: a kbest_list which is a list containing FeatureVector entries
    :param references: the references for this sentence
    :param rank: a boolean that is true if rank instead of scores should be used
    :param fb: the feedback obtained for the top 1
    :param gold_answer: this example's gold answer
    :param nl_parser: the parser to be used
    :param cache: the cache to be used
    :param ref_search_type: 0 if the original reference should be used to
    calculate bleu, 1 to use the new reference (if the top 1 is hope) and
    2 to use all references found so far and the original
    
    :return: a tuple containing the Translation object that is hope and another
    that is fear, also returns type_update which is 1 to indicate that the top 1
    has positive feedback which becomes -1 if the fear also has positive feedback,
    2 if the top 1 has negative feedback. Finally the references list
    '''
    if fb is True:  # top 1 becomes hope
        type_update = 1
        hope = kbest_list[0]
        if kbest_list[0].string not in references:
            references.append(kbest_list[0].string)
        # update to use this (1) or all references (2) in bleu scores. else we stick to the initial scores
        if ref_search_type == 1:
            for entry in kbest_list:
                entry.bleu_score = decoder.per_sentence_bleu(entry.string, [kbest_list[0].string])
            kbest_list = get_new_bleu_ranks(kbest_list)
        elif ref_search_type == 2:
            for entry in kbest_list:
                entry.bleu_score = decoder.per_sentence_bleu(entry.string, references)
            kbest_list = get_new_bleu_ranks(kbest_list)
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
            kbest_list = get_new_bleu_ranks(kbest_list)
        hope = kbest_list[hope_fear(kbest_list, 'hope', rank)]
    return hope, fear, type_update, references


# references is a list potentially containing more than 1 reference
def rebol_light(kbest_list, references, rank, fb, gold_answer, nl_parser, cache, ref_search_type=0):
    '''
    Finds hope and fear in rebol fashion. The top 1 becomes the hope if the
    parser returns the correct answer. Else the hope and is found in rampion
    fashion. The fear is always found in rampion fashion. If the fear is true
    the example can be skipped (indicated by the type_update variable)
    
    :param kbest_list: a kbest_list which is a list containing FeatureVector entries
    :param references: the references for this sentence
    :param rank: a boolean that is true if rank instead of scores should be used
    :param fb: the feedback obtained for the top 1
    :param gold_answer: this example's gold answer
    :param nl_parser: the parser to be used
    :param cache: the cache to be used
    :param ref_search_type: 0 if the original reference should be used to
    calculate bleu, 1 to use the new reference (if the top 1 is hope) and
    2 to use all references found so far and the original
    
    :return: a tuple containing the Translation object that is hope and another
    that is fear, also returns type_update which is 1 to indicate that the top 1
    has positive feedback which becomes -1 if the fear also has positive feedback,
    2 if the top 1 has negative feedback. Finally the references list
    '''
    if fb is True:  # top 1 becomes hope
        type_update = 1
        hope = kbest_list[0]
        if kbest_list[0].string not in references:
            references.append(kbest_list[0].string)
        # update to use this (1) or all references (2) in bleu scores. else we stick to the initial scores
        if ref_search_type == 1:
            for entry in kbest_list:
                entry.bleu_score = decoder.per_sentence_bleu(entry.string, [kbest_list[0].string])
            kbest_list = get_new_bleu_ranks(kbest_list)
        elif ref_search_type == 2:
            for entry in kbest_list:
                entry.bleu_score = decoder.per_sentence_bleu(entry.string, references)
            kbest_list = get_new_bleu_ranks(kbest_list)
    else:
        type_update = 2
        if ref_search_type == 2:
            for entry in kbest_list:
                entry.bleu_score = decoder.per_sentence_bleu(entry.string, references)
            kbest_list = get_new_bleu_ranks(kbest_list)
        hope = kbest_list[hope_fear(kbest_list, 'hope', rank)]
    fear = kbest_list[hope_fear(kbest_list, 'fear', rank)]
    # skip fear if it gets the right answer
    if rebol.execute_sentence(fear.string, gold_answer, nl_parser, cache)[0] is True:
        type_update *= -1
    return hope, fear, type_update, references


# references is a list potentially containing more than 1 reference
# own_trans_ref is a list with Translation objects
def rebol_too_full(kbest_list, references, fb, gold_answer, max_spot, nl_parser, cache, own_trans_ref, ref_search_type=0):
    '''
    Finds hope and fear in rebol fashion. The top 1 becomes the hope if the
    parser returns the correct answer. Else we fall back on a previously found hope,
    else the k-best list is traversed for a hope and is found in rampion
    fashion but has to have positive feedback. The fear is the top 1 if it has
    negative feedback else the k-best list is traversed and the fear found in
    rampion fashion but has to have negative feedback. 
    
    :param kbest_list: a kbest_list which is a list containing FeatureVector entries
    :param references: the references for this sentence
    :param rank: a boolean that is true if rank instead of scores should be used
    :param fb: the feedback obtained for the top 1
    :param gold_answer: this example's gold answer
    :param max_spot: how far the k-best list should be traversed to find a
    hope/fear
    :param nl_parser: the parser to be used
    :param cache: the cache to be used
    :param own_trans_ref: contains only reference found by this function (thus
    not the original)
    :param ref_search_type: 0 if the original reference should be used to
    calculate bleu, 1 to use the new reference (if the top 1 is hope) and
    2 to use all references found so far and the original
    
    :return: a tuple containing the Translation object that is hope and another
    that is fear, also returns type_update which is 1 to indicate that the top 1
    has positive feedback, 2 otherwise. Finally the references list containg the
    original and the own reference list, not containing the original
    '''
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
            kbest_list = get_new_bleu_ranks(kbest_list)
        elif ref_search_type == 2:
            for entry in kbest_list:
                entry.bleu_score = decoder.per_sentence_bleu(entry.string, references)
            kbest_list = get_new_bleu_ranks(kbest_list)
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
            kbest_list = get_new_bleu_ranks(kbest_list)
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
    '''
    Finds hope and fear using only feedback from the parser (no BLEU is used).
    The top 1 becomes the hope if the parser returns the correct answer.
    Else we fall back on a previously found hope,
    else the k-best list is traversed for a hope by executing each and returning
    the first with positive feedback.
    The fear is the top 1 if it has negative feedback else the k-best list is
    traversed for a hope by executing each and returning the first with negative
    feedback.
    
    :param kbest_list: a kbest_list which is a list containing FeatureVector entries
    :param references: the references for this sentence
    :param rank: a boolean that is true if rank instead of scores should be used
    :param fb: the feedback obtained for the top 1
    :param gold_answer: this example's gold answer
    :param max_spot: how far the k-best list should be traversed to find a
    hope/fear
    :param nl_parser: the parser to be used
    :param cache: the cache to be used
    :param own_trans_ref: contains only reference found by this function (thus
    not the original)
    :param ref_search_type: 0 if the original reference should be used to
    calculate bleu, 1 to use the new reference (if the top 1 is hope) and
    2 to use all references found so far and the original
    
    :return: a tuple containing the Translation object that is hope and another
    that is fear, also returns type_update which is 1 to indicate that the top 1
    has positive feedback, 2 otherwise. Finally the references list containg the
    original and the own reference list, not containing the original
    '''
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

def get_new_bleu_ranks(kbest_list):
    '''
    Reranks the k-best list if new bleu scores are calculated.
    
    :param kbest_list: the k-best list
    :returns: the k-best list
    '''
    inverse_rank = len(kbest_list)
    prev = "start"
    sys.stderr.write("\nNEW BLEU SCORES:\n")
    for count, entry in enumerate(sorted(kbest_list, key=operator.attrgetter('bleu_score'), reverse=True)):
        if prev != entry.bleu_score and prev != "start":
            inverse_rank -= 1
        entry.bleu_rank = inverse_rank
        prev = entry.bleu_score
        sys.stderr.write("%s\t%s ||| %s ||| %s ||| %s ||| %s\n" % (
                            count, entry.string, entry.decoder_score, entry.bleu_score, entry.decoder_rank,
                            entry.bleu_rank))
    return kbest_list