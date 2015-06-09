#!/bin/bash
cwd=$(pwd)
cd $cwd

MODELDIR=/workspace/osm/smt-semparse/work/cdec_all_test/intersect_stem_n100_mert_@_pp.l.w
CDEC=/toolbox/cdec/
VARIANT="rampion"
INI=/workspace/osm/rebol/spoc_exp/cdec.ini
INIT_WEIGHTS=/workspace/osm/rebol/data/weights.init
IT=10
MAX=100
REBOL=/workspace/osm/rebol
E=0.03
NAME="v=$VARIANT.e=$E.m=$(basename $MODELDIR)_unittest"

cd $cwd
mkdir $NAME
cd $NAME

python $REBOL/pyrebol/test_rebol.py \
  -k 1000 \
  -r $REBOL/data/spoc/baseship.train \
  -s $REBOL/data/spoc/baseship.test \
  -w $INIT_WEIGHTS \
  -d $CDEC \
  -c $INI \
  -o $MODELDIR \
  -l $E \
  -n $IT \
  -x $MAX \
  -v 1 \
  --test_following 0 \
  -p $(pwd)/../output-cache.$(basename $MODELDIR).gz \
  -t $VARIANT 2>> output-stderr > output-stdout


