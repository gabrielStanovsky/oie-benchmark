# oie-benchmark

Code for converting QA-SRL to Open-IE extractions, and for comparing existing Open-IE extractors against this corpus.
This is the implementation of the algorithms described in our [EMNLP2016 paper] (https://www.cs.bgu.ac.il/~gabriels/emnlp2016.pdf).

Citing
------


Converting QA-SRL to Open IE
----------------------------
To run the code, you should first obtain the QA-SRL corpus (from [here](https://dada.cs.washington.edu/qasrl/#dataset)) and place it under "QASRL-full".
After obtaining the QA-SRL corpus, run:
```
./create_oie_corpus.sh
```

If everything runs fine, this should create an Open IE corpus (split between wiki and newswire domain) under "oie_corpus".


Evaluating an Open IE extractor:
-----------------------------
After converting QA-SRL to Open IE, you can now automatically evaluate your Open-IE system against this corpus.
Currently, we support the output format of the following systems:

* [ClausIE](https://www.mpi-inf.mpg.de/departments/databases-and-information-systems/software/clausie/)
* [OLLIE](http://knowitall.github.io/ollie/)
* [OpenIE-4](https://github.com/allenai/openie-standalone)
* [PropS](http://u.cs.biu.ac.il/~stanovg/props.html)
* [ReVerb](http://reverb.cs.washington.edu/)
* [Stanford Open IE](http://nlp.stanford.edu/software/openie.html)

To compare your extractor:
1. Run your extractor on the sentences in "oie_corpus/oie_input" (these are the row sentences) and store the output into "*your_output*.txt"
2. Depending on your output format, you can get a precision-recall curve by running "gold comparator":
```
