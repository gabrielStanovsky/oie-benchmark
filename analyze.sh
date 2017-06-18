#!/bin/bash
## Calculate generalized question distribution and store in a dedicated json file
set -e
python ./analyze.py --in ./QASRL-full/all.qa  --out ./dist_wh_sbj_obj1.json
