# oie-benchmark

Code for converting QA-SRL to Open-IE extractions and comparing Open-IE extractors against this corpus.
This is the implementation of the algorithms described in our [EMNLP2016 paper] (https://www.cs.bgu.ac.il/~gabriels/emnlp2016.pdf).

Citing
------
If you use this software, please cite:
```
@InProceedings{Stanovsky2016EMNLP,
  author    = {Gabriel Stanovsky and Ido Dagan},
  title     = {Creating a Large Benchmark for Open Information Extraction},
  booktitle = {Proceedings of the 2016 Conference on Empirical Methods in Natural Language Processing (EMNLP)},
  month     = {November},
  year      = {2016},
  address   = {Austin, Texas},
  publisher = {Association for Computational Linguistics},
  pages     = {(to appear)},
}
```

Converting QA-SRL to Open IE
----------------------------
To run the code, you should first obtain the QA-SRL corpus (from [here](https://dada.cs.washington.edu/qasrl/#dataset)) and place it under [QASRL-full](QASRL-full).
After obtaining the QA-SRL corpus, run:
```
./create_oie_corpus.sh
```

If everything runs fine, this should create an Open IE corpus (split between wiki and newswire domain) under [oie_corpus](oie_corpus).


Evaluating an Open IE Extractor
-----------------------------
After converting QA-SRL to Open IE, you can now automatically evaluate your Open-IE system against this corpus.
Currently, we support the following output formats:

* [ClausIE](https://www.mpi-inf.mpg.de/departments/databases-and-information-systems/software/clausie/)
* [OLLIE](http://knowitall.github.io/ollie/)
* [OpenIE-4](https://github.com/allenai/openie-standalone)
* [PropS](http://u.cs.biu.ac.il/~stanovg/props.html)
* [ReVerb](http://reverb.cs.washington.edu/)
* [Stanford Open IE](http://nlp.stanford.edu/software/openie.html)

To compare your extractor:

1. Run your extractor on the sentences in [oie_corpus/oie_input.txt](oie_corpus/oie_input.txt) (these are the row sentences) and store the output into "*your_output*.txt"

2. Depending on your output format, you can get a precision-recall curve by running [benchmark.py](benchmark.py):
``` 
Usage:
   benchmark --gold=GOLD_OIE --out=OUTPUT_FILE (--stanford=STANFORD_OIE | --ollie=OLLIE_OIE |--reverb=REVERB_OIE | --clausie=CLAUSIE_OIE | --openiefour=OPENIEFOUR_OIE | --props=PROPS_OIE)

Options:
  --gold=GOLD_OIE              The gold reference Open IE file (by default, it should be under ./oie_corpus/all.oie).
  --out-OUTPUT_FILE            The output file, into which the precision recall curve will be written.
  --clausie=CLAUSIE_OIE        Read ClausIE format from file CLAUSIE_OIE.
  --ollie=OLLIE_OIE            Read OLLIE format from file OLLIE_OIE.
  --openiefour=OPENIEFOUR_OIE  Read Open IE 4 format from file OPENIEFOUR_OIE.
  --props=PROPS_OIE            Read PropS format from file PROPS_OIE
  --reverb=REVERB_OIE          Read ReVerb format from file REVERB_OIE
  --stanford=STANFORD_OIE      Read Stanford format from file STANFORD_OIE
```

Evaluating Existing Systems
---------------------------

In the course of this work we tested the above mentioned Open IE parsers against our benchmark.
We provide the output files (i.e., Open IE extractions) of each of these
systems in [systems_output](systems_output).
You can give each of these files to [benchmark.py](benchmark.py) (as described above), to
get the corresponding precision recall curve.

For example, to can to evaluate Stanford Open IE output, run:
```
python benchmark.py --gold=./oie_corpus/all.oie --out=./StanfordPR.dat --stanford=./systems_output/stanford_output.txt
```

