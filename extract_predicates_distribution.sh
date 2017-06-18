#!/bin/bash
## Output predicates by their number of words from the given OIE corpus to the given output file.
set -e
cut -f2 ./oie_corpus/all.oie | sort | uniq -c | sort -n > predicate_list.txt
