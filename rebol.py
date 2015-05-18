#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import codecs
import operator
import os
import re
import sys
import tempfile
import time
import traceback

import hopefear
from parser.parse_nl import NLParser
from nlpminion import decoder
from nlpminion import translation
from nlpminion.feature_vector import FeatureVector
from nlpminion.cache import Cache


class Statistics:
    def __init__(self):
        self.mrl = 0
        self.answer = 0
        self.correct_answer = 0

    def reset(self):
        self.mrl = 0
        self.answer = 0
        self.correct_answer = 0


def execute_sentence(nl, gold_answer, nl_parser, cache):
    cached = False
    fb = False
    mrl = ""
    answer = ""
    if nl.strip() == "":  # if there was no translation then we also do not try to parse it
        return fb, mrl, answer, cached
    if nl in cache.dict:
        cached = True
        fb, mrl, answer = cache.dict[nl]
    else:
        # get mrl+answer
        mrl, answer = nl_parser.process_sentence(nl)
        if answer.strip() == gold_answer.strip():
            fb = True
        cache.dict[nl] = (fb, mrl, answer)
    return fb, mrl, answer, cached


def execute_set(nls, gold_answers, nl_parser):
    feedback = []
    # get mrl+answer
    hyp_mrl, hyp_answer = nl_parser.process_set(nls)
    if len(hyp_answer) is not len(gold_answers):
        sys.stderr.write("ERROR: hypothesis answers and gold answers are not of same length\n")
        sys.exit(1)
    for counter, entry in enumerate(hyp_answer):
        if entry.strip() == gold_answers[counter].strip():
            feedback.append(True)
        else:
            feedback.append(False)
    return feedback, hyp_mrl, hyp_answer


def convert_time(elapsed_time):
    m, s = divmod(elapsed_time, 60)
    h, m = divmod(m, 60)
    return h, m, s


def main():
    start = time.time()
    sys.stderr.write("STARTING RUN\n")
    # cache
    cache = Cache()

    weights_tmp = ""

    debug = codecs.open("debug.log", "w", encoding="utf-8")

    argparser = argparse.ArgumentParser()
    argparser.add_argument("-r", "--train", type=str, required=True,
                           help="the train data location (assumes the following appropriate file endings: "
                                ".in, .mrl, .gold)")
    argparser.add_argument("-s", "--test", type=str, required=True,
                           help="the test data location (assumes the following appropriate file endings: "
                                ".in, .mrl, .gold)")
    argparser.add_argument("-w", "--weights", type=str, required=True, help="the initial weights")
    argparser.add_argument("-d", "--decoder", type=str, required=True, help="the location where cdec resides")
    argparser.add_argument("-c", "--ini", type=str, required=True, help="the decoder's ini file")
    argparser.add_argument("-o", "--model_dir", type=str, required=True, default="",
                           help="specify cache file if one is to be used")
    argparser.add_argument("-p", "--cache", type=str, required=False, default="", help="the decoder's ini file")
    argparser.add_argument("-e", "--hold_out", type=int, required=False, default=0,
                           help="number of example to hold out for early stopping")
    argparser.add_argument("-t", "--type", type=str, required=True, help="the variant type")
    argparser.add_argument("-l", "--learning_rate", type=float, required=True, help="the learning rate")
    argparser.add_argument("-n", "--iterations", type=int, default=999, help="the number of iterations")
    argparser.add_argument("-k", "--kbest", type=int, required=False, default=100, help="size of kbest list")
    argparser.add_argument("-x", "--max", type=int, required=False, default=100,
                           help="number of entries considered when searching for hope/fear translation")
    argparser.add_argument("-v", "--verbose", type=int, choices=[0, 1, 2], required=False, default=0,
                           help="size of kbest list")
    argparser.add_argument("-b", "--bleu_ref_type", type=int, choices=[0, 1, 2, 3], required=False, default=3,
                           help="which reference(s) should be used to calculate per sentence bleu: 0 uses original reference, 1 uses new, just found reference, 2 uses all")
    argparser.add_argument("--rank", action="store_true", default=False, help="use ranks instead of scores")
    argparser.add_argument('--test_all', action="store_true", default=False,
                           help="run test for every weight generated during training")
    argparser.add_argument('--skip_train', action="store_true", default=False,
                           help="allows the training to be skipped in case only testing is to occur")
    argparser = argparser.parse_args()

    # initialise parser
    nl_parser = NLParser(argparser.model_dir)

    try:
        last_trained_iteration = argparser.iterations
        if not argparser.skip_train:
            ''' Run Train '''
            ''' if argparser.bleu_ref_type is 3 that means the algorithms own indented default is used:
            for rebol light & fear_neg_top1: 0. only use original reference
            for rebol too full: 1. use new reference'''
            if argparser.bleu_ref_type == 3:
                if argparser.type == 'rebol_too_full':
                    argparser.bleu_ref_type = 1
                if argparser.type == 'rebol_light' or argparser.type == 'rebol_fear_neg_top1' :
                    argparser.bleu_ref_type = 0

            sys.stderr.write("CONFIGURATION\n")
            sys.stderr.write("=============\n")
            for option in vars(argparser):
                sys.stderr.write("%s: %s\n" % (option, getattr(argparser, option)))
            sys.stderr.write("Corpus: SPOC\n")
            sys.stderr.write("=============\n\n")

            # load cache
            if argparser.cache.strip() is not "":
                try:
                    cache.from_gz_file(argparser.cache, " ||| ", True)
                except (OSError, IOError):
                    sys.stderr.write("WARNING: Specified cache file does not exist: %s\n" % argparser.cache)

            with open("%s.in" % argparser.train) as f:
                nl = f.read().splitlines()
            f.close()
            with open("%s.ref" % argparser.train) as f:
                reference = []
                for line in f:
                    # a list of lists, where the first entry is always the gold reference
                    reference.append([line.strip()])
            f.close()
            with open("%s.mrl" % argparser.train) as f:
                gold_mrl = f.read().splitlines()
            f.close()
            with open("%s.gold" % argparser.train) as f:
                gold_answer = f.read().splitlines()
            f.close()

            # if use a hold out set, we splice the correct number from the top of the list
            if argparser.hold_out>0:
                # TODO make sure there is no 1 sent overlap between dev and train
                dev_prefix = "dev"
                nl_dev_out = open("%s.in" % dev_prefix, 'w')
                for ele in nl[:argparser.hold_out]:
                    print >>nl_dev_out, ele
                nl_dev_out.close()
                nl = nl[argparser.hold_out:]
                reference_dev_out = open("%s.ref" % dev_prefix, 'w')
                for ele in reference[:argparser.hold_out]:
                    print >>reference_dev_out, ele
                reference_dev_out.close()
                reference = reference[argparser.hold_out:]
                gold_answer_dev_out = open("%s.gold" % dev_prefix, 'w')
                for ele in gold_answer[:argparser.hold_out]:
                    print >>gold_answer_dev_out, ele
                gold_answer_dev_out.close()
                gold_answer = gold_answer[argparser.hold_out:]
                gold_mrl = gold_mrl[argparser.hold_out:]

            # get init weights
            weights = FeatureVector()
            weights.from_file(argparser.weights)

            # initialise Statistics
            top1_stat = Statistics()
            hope_stat = Statistics()
            fear_stat = Statistics()

            own_trans_refs = [[] for _ in xrange(0, len(nl))]

            prev_1_dev_score = 0.0
            prev_2_dev_score = 0.0

            sys.stderr.write("STARTING LEARNING\n")
            # iterations
            for it in xrange(1, argparser.iterations + 1):
                start_it = time.time()
                sys.stderr.write("STARTING ITERATION %s\n" % it)
                sys.stderr.write("=============\n")

                # reset counters
                no_trans = 0
                type_1_actual = 0
                type_2_actual = 0
                type_1_total = 0
                type_2_total = 0
                top1_stat.reset()
                hope_stat.reset()
                fear_stat.reset()

                # examples
                for sent_counter, sent in enumerate(nl):

                    sys.stderr.write("-------------\n")
                    sys.stderr.write("EXAMPLE %s\n" % (sent_counter))
                    sys.stderr.write("INPUT: %s\n" % re.match(r".*?\">(.*?)</.*?", sent).groups()[0])
                    sys.stderr.write("REFERENCE(S): %s\n" % reference[sent_counter])
                    sys.stderr.write("GOLD MRL: %s\n" % gold_mrl[sent_counter])
                    sys.stderr.write("GOLD ANSWER: %s\n" % gold_answer[sent_counter])

                    # write weights to tempfile
                    weights_handle, weights_tmp = tempfile.mkstemp("", "rebol_py_")
                    if argparser.verbose >= 1:
                        sys.stderr.write("TEMP: %s\n" % weights_tmp)
                    weights.to_file(weights_tmp)
                    weights.to_file("weights_%s_%s" % (it,sent_counter))
                    os.close(weights_handle)
                    # weights.to_file("weights_%s" % sent_counter)

                    # call to the decoder
                    out_raw = decoder.translate_sentence("%s/decoder/cdec" %
                                                         argparser.decoder, argparser.ini, weights_tmp,
                                                         sent, argparser.kbest)
                    kbest_list = []
                    if out_raw.strip() == "":
                        no_trans += 1
                        sys.stderr.write("NO TRANSLATION, SKIPPING\n")
                        sys.stderr.write("-------------\n\n")
                        os.remove(weights_tmp)
                        continue
                    for entry in out_raw.strip().split("\n"):
                        kbest_list.append(translation.Translation(entry.strip()))

                    inverse_rank = len(kbest_list)
                    prev = "start"
                    # get per-sentence BLEU + assign decoder rank
                    for entry in kbest_list:
                        # only use the original reference at this point, but it still need to be a list
                        entry.bleu_score = decoder.per_sentence_bleu(entry.string, [reference[sent_counter][0]])
                        if prev != entry.decoder_score and prev != "start":
                            inverse_rank -= 1
                        entry.decoder_rank = inverse_rank
                        prev = entry.decoder_score

                    inverse_rank = len(kbest_list)
                    prev = "start"
                    for entry in sorted(kbest_list, key=operator.attrgetter('bleu_score'), reverse=True):
                        if prev != entry.bleu_score and prev != "start":
                            inverse_rank -= 1
                        entry.bleu_rank = inverse_rank
                        prev = entry.bleu_score

                    # sys.stderr.write("kbest list size: %s\n" % len(kbest_list))
                    # sys.stderr.write("kbest list: %s\n" % kbest_list)

                    # adjust decoder scores to lie between [0,1]
                    min_score = min(entry.decoder_score for entry in kbest_list)
                    max_score = max(entry.decoder_score for entry in kbest_list)
                    sys.stderr.write("\n")
                    for count, entry in enumerate(kbest_list):
                        entry.decoder_ori = entry.decoder_score
                        entry.decoder_score = (entry.decoder_score - min_score) / (max_score - min_score)
                        sys.stderr.write("%s\t%s ||| %s ||| %s ||| %s ||| %s\n" % (
                            count, entry.string, entry.decoder_score, entry.bleu_score, entry.decoder_rank,
                            entry.bleu_rank))

                    # execute top 1
                    fb, mrl, answer, cached = execute_sentence(
                        kbest_list[0].string, gold_answer[sent_counter], nl_parser, cache)
                    sys.stderr.write("\n[TOP 1]\n")
                    sys.stderr.write("        nrl: %s\n" % kbest_list[0].string)
                    sys.stderr.write("        mrl: %s\n" % mrl)
                    sys.stderr.write("     answer: %s\n" % answer)
                    sys.stderr.write("   correct?: %s\n" % fb)
                    sys.stderr.write("   cached?: %s\n" % cached)
                    if mrl.strip() != "":
                        top1_stat.mrl += 1
                    if answer.strip() != "":
                        top1_stat.answer += 1
                    if fb:
                        top1_stat.correct_answer += 1

                    # variants to find hope/fear
                    # type contains 0 by default, 1 for top1 is true and 2 for top1 is false,
                    # -1 is type 1 is skipped, -2 if type 2 is skipped
                    if argparser.type == 'rampion':
                        hope, fear, update_type = hopefear.rampion(kbest_list, reference[sent_counter], argparser.rank)
                    elif argparser.type == 'rebol_too_full':
                        hope, fear, update_type, reference[sent_counter], own_trans_refs[sent_counter] = \
                            hopefear.rebol_too_full(kbest_list, reference[sent_counter], fb,
                                                    gold_answer[sent_counter], argparser.max, nl_parser, cache,
                                                    own_trans_refs[sent_counter], argparser.bleu_ref_type)
                    elif argparser.type == 'rebol_light':
                        hope, fear, update_type, reference[sent_counter] = \
                            hopefear.rebol_light(kbest_list, reference[sent_counter], argparser.rank, fb,
                                                 gold_answer[sent_counter], nl_parser, cache, argparser.bleu_ref_type)
                    elif argparser.type == 'rebol_fear_neg_top1':
                        hope, fear, update_type, reference[sent_counter] = \
                            hopefear.rebol_fear_neg_top1(kbest_list, reference[sent_counter], argparser.rank, fb,
                                                         gold_answer[sent_counter], nl_parser, cache, argparser.bleu_ref_type)
                    elif argparser.type == 'exec_only':
                        hope, fear, update_type, reference[sent_counter], own_trans_refs[sent_counter] = \
                            hopefear.exec_only(kbest_list, reference[sent_counter], fb, gold_answer[sent_counter],
                                               argparser.max, nl_parser, cache, own_trans_refs[sent_counter])
                    else:
                        sys.stderr.write("\nUnknown variant type: %s\nEXITING\n" % argparser.type)
                        sys.exit(1)

                    # execute & print info for hope
                    sys.stderr.write("\n[HOPE]\n")
                    if hope is not None:
                        fb, mrl, answer, cached = execute_sentence(
                            hope.string, gold_answer[sent_counter], nl_parser, cache)
                        sys.stderr.write("        nrl: %s\n" % hope.string)
                        sys.stderr.write("        mrl: %s\n" % mrl)
                        sys.stderr.write("     answer: %s\n" % answer)
                        sys.stderr.write("   correct?: %s\n" % fb)
                        sys.stderr.write("   cached?: %s\n" % cached)
                    else:
                        sys.stderr.write("None found\n")
                    if mrl.strip() != "":
                        hope_stat.mrl += 1
                    if answer.strip() != "":
                        hope_stat.answer += 1
                    if fb:
                        hope_stat.correct_answer += 1

                    # execute & print info for fear
                    sys.stderr.write("\n[FEAR]\n")
                    if hope is not None:
                        fb, mrl, answer, cached = execute_sentence(
                            fear.string, gold_answer[sent_counter], nl_parser, cache)
                        sys.stderr.write("        nrl: %s\n" % fear.string)
                        sys.stderr.write("        mrl: %s\n" % mrl)
                        sys.stderr.write("     answer: %s\n" % answer)
                        sys.stderr.write("   correct?: %s\n" % fb)
                        sys.stderr.write("   cached?: %s\n" % cached)
                    else:
                        sys.stderr.write("None found\n")
                    if mrl.strip() != "":
                        fear_stat.mrl += 1
                    if answer.strip() != "":
                        fear_stat.answer += 1
                    if fb:
                        fear_stat.correct_answer += 1

                    # update type counter
                    if update_type == 1:
                        type_1_actual += 1
                        type_1_total += 1
                    elif update_type == 2:
                        type_2_actual += 1
                        type_2_total += 1
                    elif update_type == -1:
                        type_1_total += 1
                    elif update_type == -2:
                        type_2_total += 1

                    # check skip: changed position
                    if update_type == -1 or update_type == -2 or hope is None or fear is None:
                        sys.stderr.write("SKIPPING EXAMPLE: No appropriate hope/fear\n")
                        os.remove(weights_tmp)
                        continue

                    # update weights
                    sys.stderr.write("weights: %s\n" % str(weights))
                    sys.stderr.write("hope: %s\n" % str(hope.features))
                    sys.stderr.write("fear: %s\n" % str(fear.features))
                    weights += (hope.features - fear.features) * argparser.learning_rate
                    sys.stderr.write("weights after: %s\n" % str(weights))

                    # delete old weights_tmp
                    os.remove(weights_tmp)

                    # sys.stderr.write("open files rebol.py: %s\n" % get_open_fds())
                    sys.stderr.write("-------------\n\n")

                # print iteration statistics
                sys.stderr.write("=============\n\n")
                val = time.time() - start_it
                h, m, s = convert_time(val)
                sys.stderr.write("Iteration %s took: %d:%02d:%02d (%s)\n" % (it, h, m, s, val))
                sys.stderr.write("=============\n")
                sys.stderr.write("iteration %s/%s: %s examples\n" % (it, argparser.iterations, len(nl)))
                sys.stderr.write("type 1 updates: %s / %s (actual / total)\n" % (type_1_actual, type_1_total))
                sys.stderr.write("type 2 updates: %s / %s (actual / total)\n" % (type_2_actual, type_2_total))
                sys.stderr.write("# of no translation: %s\n" % no_trans)

                sys.stderr.write("\n TOP1: %s / %s / %s (# mrl / answer / correct answer)\n" % (
                    top1_stat.mrl, top1_stat.answer, top1_stat.correct_answer))
                sys.stderr.write("\n HOPE: %s / %s / %s (# mrl / answer / correct answer)\n" % (
                    hope_stat.mrl, hope_stat.answer, hope_stat.correct_answer))
                sys.stderr.write("\n FEAR: %s / %s / %s (# mrl / answer / correct answer)\n" % (
                    fear_stat.mrl, fear_stat.answer, fear_stat.correct_answer))
                sys.stderr.write("=============\n\n")

                # gz weights
                weights.to_gz_file("output-weights.%s.gz" % it)

                # check if we should stop
                if argparser.hold_out>0:
                    sys.stderr.write("STARTING DEV TEST\n")
                    start_dev = time.time()
                    f1_dev, bleu_dev = run_test(dev_prefix, argparser, cache, nl_parser, it, True)
                    h, m, s = convert_time(time.time() - start_dev)
                    sys.stderr.write("Dev testing took: %d:%02d:%02d\n" % (h, m, s))
                    if argparser.type == 'rampion':
                        score_of_intereset_dev = bleu_dev
                        sys.stderr.write("DEV SCORE: %s BLEU\n" % score_of_intereset_dev)
                    else:
                        score_of_intereset_dev = f1_dev
                        sys.stderr.write("DEV SCORE: %s F1\n" % score_of_intereset_dev)
                    if prev_1_dev_score > score_of_intereset_dev and prev_2_dev_score > prev_1_dev_score:
                        sys.stderr.write("BEST DEV TEST REACHED LAST ITERATION: STOPPING TRAINING\n")
                        sys.stderr.write("BEST ITERATION: %s\n\n" % (it-2))
                        last_trained_iteration = it - 2
                        break
                    prev_2_dev_score = prev_1_dev_score
                    prev_1_dev_score = score_of_intereset_dev
                    sys.stderr.write("BEST DEV TEST NOT YET REACHED: CONTINUING TRAINING\n\n")

            # print total run statistics
            h, m, s = convert_time(time.time() - start)
            sys.stderr.write("Learning took: %d:%02d:%02d\n" % (h, m, s))
            sys.stderr.write("LEARNING COMPLETE\n\n")

        ''' Run Test '''
        sys.stderr.write("STARTING TESTING\n")
        start_test = time.time()

        if argparser.test_all is True:
            for it in range(1, last_trained_iteration + 1):
                run_test(argparser.test, argparser, cache, nl_parser, it)
        else:
            run_test(argparser.test, argparser, cache, nl_parser, last_trained_iteration)

        h, m, s = convert_time(time.time() - start_test)
        sys.stderr.write("Testing took: %d:%02d:%02d\n" % (h, m, s))
        sys.stderr.write("TESTING COMPLETE\n\n")
        h, m, s = convert_time(time.time() - start)
        sys.stderr.write("Total run time was: %d:%02d:%02d\n" % (h, m, s))
        sys.stderr.write("RUN COMPLETE\n\n")

        # save cache
        cache.to_gz_file("output-cache.%s.gz" % os.path.basename(argparser.model_dir), " ||| ")
    except:
        debug.close()
        exception_info = traceback.format_exc()
        # save cache
        cache.to_gz_file("output-cache.%s.gz" % os.path.basename(argparser.model_dir), " ||| ")
        # delete old weights_tmp
        try:
            os.remove(weights_tmp)
        except OSError:
            pass
        sys.stderr.write(exception_info)


def run_test(input_files, argparser, cache, nl_parser, it, dev_run=False):
    with open("%s.in" % input_files) as f:
        nl_input = f.read().splitlines()
    f.close()
    with open("%s.gold" % input_files) as f:
        gold_answer_input = f.read().splitlines()
    f.close()
    basename_model_dir = os.path.basename(argparser.model_dir)
    if dev_run is True:
        prefix = "dev"
    else:
        prefix = "test"
    # call to the decoder
    sys.stderr.write("DECODING...\n")
    translation_out = open('output-translation.%s.%s.%s.%s' % (prefix, argparser.type, basename_model_dir, it), 'w')
    print >> translation_out, decoder.translate("%s/decoder/cdec" % argparser.decoder, argparser.ini,
                                                "output-weights.%s.gz" % it, "%s.in" % input_files).strip()
    translation_out.close()

    with open('output-translation.%s.%s.%s.%s' % (prefix, argparser.type, basename_model_dir, it)) as f:
        translation_test = f.read().splitlines()
    f.close()

    # get bleu
    sys.stderr.write("SCORE BLEU...\n")
    bleu_out = open('output-bleu.%s.%s.%s.%s' % (prefix, argparser.type, basename_model_dir, it), 'w')
    bleu_raw = decoder.bleu("%s/mteval/fast_score" % argparser.decoder, "%s.ref" % input_files,
                                    'output-translation.%s.%s.%s.%s' % (prefix, argparser.type, basename_model_dir, it)).strip()
    print >> bleu_out, bleu_raw
    bleu_out.close()

    mrl_out = open('output-mrl.%s.%s.%s.%s' % (prefix, argparser.type, basename_model_dir, it), 'w')
    answer_out = open('output-answers.%s.%s.%s.%s' % (prefix, argparser.type, basename_model_dir, it), 'w')
    sigf_out = open('output-sigf.%s.%s.%s.%s' % (prefix, argparser.type, basename_model_dir, it), 'w')

    # get mrl + answer + f1 sigf
    # TODO: change to set execution? there we won't have the cache so it is not clear if it is worth it
    sys.stderr.write("PARSING...\n")
    nr_total = len(nl_input)
    nr_answer = 0
    nr_correct = 0
    for sent_counter, sent in enumerate(nl_input):
        test_fb, test_mrl, test_answer, cached = execute_sentence(
            translation_test[sent_counter], gold_answer_input[sent_counter], nl_parser, cache)

        sigf_value = ["0", "0", "1"]  # assumes no mrl ("")
        if test_fb is True:
            nr_correct += 1
            sigf_value[0] = "1"
            sigf_value[1] = "1"
        elif test_answer.strip() is not "":
            sigf_value[1] = "1"
        if test_answer.strip() is not "":
            nr_answer += 1
        sys.stderr.write("\n%s EXAMPLE %s\n" % (prefix.upper(), str(sent_counter + 1)))
        sys.stderr.write("        nrl: %s\n" % translation_test[sent_counter])
        sys.stderr.write("        mrl: %s\n" % test_mrl)
        sys.stderr.write("     answer: %s\n" % test_answer)
        sys.stderr.write("gold answer: %s\n" % gold_answer_input[sent_counter])
        sys.stderr.write("   correct?: %s\n" % test_fb)
        sys.stderr.write("   cached?: %s\n" % cached)
        print >> mrl_out, test_mrl
        print >> answer_out, test_answer
        print >> sigf_out, ' '.join(sigf_value)

    mrl_out.close()
    answer_out.close()
    sigf_out.close()

    # get eval
    sys.stderr.write("EVAL...\n")
    eval_out = open('output-eval.%s.%s.%s.%s' % (prefix, argparser.type, basename_model_dir, it), 'w')
    recall = 100 * (float(nr_correct) / float(nr_total))
    precision = 100 * (float(nr_correct) / float(nr_answer))
    if recall + precision != 0:
        f1 = ((2 * recall * precision) / (recall + precision))
    else:
        f1 = 0
    eval_info = "recall=%.2f (%s / %s) precision=%.2f (%s / %s) f1=%.2f" \
                % (round(recall, 2), nr_correct, nr_total, round(precision, 2), nr_correct, nr_answer, round(f1, 2))
    print >> eval_out, eval_info
    eval_out.close()
    # print test statistics
    sys.stderr.write("EVALUATION: %s\n" % eval_info)
    return round(f1, 2), float(bleu_raw)


if __name__ == '__main__':
    main()