''' Usage:
   goldComparator --gold=GOLD_OIE --out=OUTPUT_DIR [--stanford=STANFORD_OIE] [--ollie=OLLIE_OIE] [--reverb=REVERB_OIE] [--clausie=CLAUSIE_OIE] [--openiefour=OPENIEFOUR_OIE] [--props=PROPS_OIE] 
'''
import docopt
import string
import numpy as np
from sklearn.metrics import precision_recall_curve
import re
import logging
logging.basicConfig(level = logging.INFO)

from oie_readers.stanfordReader import StanfordReader
from oie_readers.ollieReader import OllieReader
from oie_readers.reVerbReader import ReVerbReader
from oie_readers.clausieReader import ClausieReader
from oie_readers.openieFourReader import OpenieFourReader
from oie_readers.propsReader import PropSReader

from oie_readers.goldReader import GoldReader
from matcher import Matcher

class GoldComparator:
    ''' Comapre a gold OIE dataset against a predicted equivalent '''
    def __init__(self, gold_fn):
        ''' Load gold Open IE, this will serve to compare against using the compare function '''
        gr = GoldReader() 
        gr.read(gold_fn)
        self.gold = gr.oie

    def compare(self, predicted, matchingFunc, output_fn):
        ''' Compare gold against predicted using a specified mode. 
            Outputs PR curve to output_fn '''
        
        y_true = []
        y_scores = []
        
        correctTotal = 0
        unmatchedCount = 0        
        predicted = GoldComparator.normalizeDict(predicted)
        gold = GoldComparator.normalizeDict(self.gold)
                
        for sent, goldExtractions in gold.items():
            if sent not in predicted:
                # The extractor didn't find any extractions for this sentence
                for goldEx in goldExtractions:   
                    unmatchedCount += len(goldExtractions)
                    correctTotal += len(goldExtractions)
                continue
                
            predictedExtractions = predicted[sent]

            
            
            for goldEx in goldExtractions:
                correctTotal += 1
                found = False
                
                for predictedEx in predictedExtractions:
                    if output_fn in predictedEx.matched:
                        # This predicted extraction was already matched against a gold extraction
                        # Don't allow to match it again
                        continue
                    
                    if matchingFunc(goldEx, 
                                    predictedEx, 
                                    ignoreStopwords = True, 
                                    ignoreCase = True):
                        
                        y_true.append(1)
                        y_scores.append(predictedEx.confidence)
                        predictedEx.matched.append(output_fn)
                        found = True
                        break
                    
                if not found:
                    unmatchedCount += 1
                    
            for predictedEx in [x for x in predictedExtractions if (output_fn not in x.matched)]:
                # Add false positives
                y_true.append(0)
                y_scores.append(predictedEx.confidence)
                
        y_true = y_true
        y_scores = y_scores
        
        # recall on y_true, y  (r')_scores computes |covered by extractor| / |True in what's covered by extractor|
        # to get to true recall we do r' * (|True in what's covered by extractor| / |True in gold|) = |true in what's covered| / |true in gold|
        p, r = GoldComparator.prCurve(np.array(y_true), np.array(y_scores),
                       recallMultiplier = ((correctTotal - unmatchedCount)/float(correctTotal)))

        # write PR to file
        with open(output_fn, 'w') as fout:
            fout.write('{0}\t{1}\n'.format("Precision", "Recall"))
            for cur_p, cur_r in sorted(zip(p, r), key = lambda (cur_p, cur_r): cur_r):
                fout.write('{0}\t{1}\n'.format(cur_p, cur_r))
    
    @staticmethod
    def prCurve(y_true, y_scores, recallMultiplier):
        # Recall multiplier - accounts for the percentage examples unreached by 
        precision, recall, _ = precision_recall_curve(y_true, y_scores)
        recall = recall * recallMultiplier
        return precision, recall

    # Helper functions:
    @staticmethod
    def normalizeDict(d):
        return dict([(GoldComparator.normalizeKey(k), v) for k, v in d.items()])
    
    @staticmethod
    def normalizeKey(k):
        return GoldComparator.removePunct(unicode(GoldComparator.PTB_unescape(k.replace(' ','')), errors = 'ignore'))

    @staticmethod
    def PTB_escape(s):
        for u, e in GoldComparator.PTB_ESCAPES:
            s = s.replace(u, e)
        return s
    
    @staticmethod
    def PTB_unescape(s):
        for u, e in GoldComparator.PTB_ESCAPES:
            s = s.replace(e, u)
        return s
    
    @staticmethod
    def removePunct(s):
        return GoldComparator.regex.sub('', s)
    
    # CONSTANTS
    regex = re.compile('[%s]' % re.escape(string.punctuation))
    
    # Penn treebank bracket escapes 
    # Taken from: https://github.com/nlplab/brat/blob/master/server/src/gtbtokenize.py
    PTB_ESCAPES = [('(', '-LRB-'),
                   (')', '-RRB-'),
                   ('[', '-LSB-'),
                   (']', '-RSB-'),
                   ('{', '-LCB-'),
                   ('}', '-RCB-'),]


if __name__ == '__main__':
    args = docopt.docopt(__doc__)
    logging.debug(args)
    
    systems = []
    if args['--stanford']:
        s = StanfordReader()
        s.read(args['--stanford'])
        systems.append(s)
    
    if args['--props']:
        p = PropSReader()
        p.read(args['--props'])
        systems.append(p)
       
    if args['--ollie']:
        o = OllieReader()
        o.read(args['--ollie'])
        systems.append(o)
    
    if args['--reverb']:
        r = ReVerbReader()
        r.read(args['--reverb'])
        systems.append(r)
    
    if args['--clausie']:
        c = ClausieReader()
        c.read(args['--clausie'])
        systems.append(c)
        
    if args['--openiefour']:
        o4 = OpenieFourReader()
        o4.read(args['--openiefour'])
        systems.append(o4)
       

    if not systems:
        logging.warning("No Open IE system was given.")


    gc = GoldComparator(args['--gold'])
    output_dir = args['--out']
    for oie in systems:
        out_filename = '{}/{}.dat'.format(output_dir, oie.name)
        logging.info("Writing PR curve of {} to {}".format(oie.name, out_filename))
        gc.compare(predicted = oie.oie, 
                   matchingFunc = Matcher.lexicalMatch,
                   output_fn = out_filename)
    
        
        
