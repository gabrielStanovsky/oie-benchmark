#!/bin/bash
set -e
mkdir -p ./oie_corpus/newswire
mkdir -p ./oie_corpus/wiki
echo "Extracting from newswire..."
echo "dev..."
python ./qa_to_oie.py --in=./QASRL-full/newswire/propbank.dev.qa --out=./oie_corpus/newswire/propbank.dev.oie --dist=question_distributions/dist_wh_sbj_obj1.json
echo "train..."
python ./qa_to_oie.py --in=./QASRL-full/newswire/propbank.train.qa --out=./oie_corpus/newswire/propbank.train.oie --dist=question_distributions/dist_wh_sbj_obj1.json
echo "test..."
python ./qa_to_oie.py --in=./QASRL-full/newswire/propbank.test.qa --out=./oie_corpus/newswire/propbank.test.oie --dist=question_distributions/dist_wh_sbj_obj1.json
echo "Extracting from wiki..."
echo "dev..."
python ./qa_to_oie.py --in=./QASRL-full/wiki/wiki1.dev.qa --out=./oie_corpus/wiki/wiki1.dev.oie --dist=question_distributions/dist_wh_sbj_obj1.json
echo "train..."
python ./qa_to_oie.py --in=./QASRL-full/wiki/wiki1.train.qa --out=./oie_corpus/wiki/wiki1.train.oie --dist=question_distributions/dist_wh_sbj_obj1.json
echo "test..."
python ./qa_to_oie.py --in=./QASRL-full/wiki/wiki1.test.qa --out=./oie_corpus/wiki/wiki1.test.oie --dist=question_distributions/dist_wh_sbj_obj1.json
echo "Concatenating global train/dev/test"
cat ./oie_corpus/newswire/propbank.dev.oie ./oie_corpus/wiki/wiki1.dev.oie > ./oie_corpus/dev.oie
cat ./oie_corpus/newswire/propbank.train.oie ./oie_corpus/wiki/wiki1.train.oie > ./oie_corpus/train.oie
cat ./oie_corpus/newswire/propbank.test.oie ./oie_corpus/wiki/wiki1.test.oie > ./oie_corpus/test.oie
cat ./oie_corpus/dev.oie ./oie_corpus/train.oie ./oie_corpus/test.oie > ./oie_corpus/all.oie
echo "DONE"
