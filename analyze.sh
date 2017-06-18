#!/bin/bash
## Calculate generalized question distribution and store in a dedicated json file
set -e
echo "Analyzing Distribution..."
python ./analyze.py --in ./QASRL-full/all.qa  --out ./question_distributions/dist_wh_sbj_obj1.json
echo "DONE! Output written to ./dist_wh_sbj_obj1.json"
