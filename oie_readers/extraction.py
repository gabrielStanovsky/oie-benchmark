from sklearn.preprocessing.data import binarize
from oie_readers.argument import Argument
from operator import itemgetter
from collections import defaultdict
import nltk
import logging 

class Extraction:
    ''' holds sentence, single predicate and corresponding arguments '''
    def __init__(self, pred, sent, confidence):
        self.pred = pred
        self.sent = sent
        self.args = []
        self.confidence = confidence
        self.matched = []
        self.questions = {}
        self.indsForQuestions = defaultdict(lambda: set())

    def distArgFromPred(self, arg):
        assert(len(self.pred) == 2)
        dists = []
        for x in self.pred[1]:
            for y in arg.indices:
                dists.append(abs(x - y))

        return min(dists)

    def argsByDistFromPred(self, question):
        return sorted(self.questions[question], key = lambda arg: self.distArgFromPred(arg))

    def addArg(self, arg, question = None):
        self.args.append(arg)
        if question:
            self.questions[question] = self.questions.get(question,[]) + [Argument(arg)]

    def noPronounArgs(self):
        """
        Returns True iff all of this extraction's arguments are not pronouns.
        """
        for (a, _) in self.args:
            tokenized_arg = nltk.word_tokenize(a)
            if len(tokenized_arg) == 1:
                _, pos_tag = nltk.pos_tag(tokenized_arg)[0]
                if ('PRP' in pos_tag):
                    return False
        return True

    def isContiguous(self):
        return all([indices for (_, indices) in self.args])

    def toBinary(self):
        ''' Try to represent this extraction's arguments as binary
        If fails, this function will return an empty list.  '''

        ret = [self.elementToStr(self.pred)]

        if len(self.args) == 2:
            # we're in luck
            return ret + [self.elementToStr(arg) for arg in self.args]

        return []

        if not self.isContiguous():
            # give up on non contiguous arguments (as we need indexes)
            return []

        # otherwise, try to merge based on indices
        # TODO: you can explore other methods for doing this
        binarized = self.binarizeByIndex()

        if binarized:
            return ret + binarized

        return []


    def elementToStr(self, elem):
        ''' formats an extraction element (pred or arg) as a raw string
        removes indices and trailing spaces '''
        if isinstance(elem, str):
            return elem
        if isinstance(elem, tuple): #TODO: fix this
            ret = elem[0].rstrip().lstrip()
        else:
            ret = ' '.join(elem.words)
        assert ret, "empty element? {0}".format(elem)
        return ret 
    
    def binarizeByIndex(self):
        extraction = [self.pred] + self.args
        markPred = [(w, ind, i == 0) for i, (w, ind) in enumerate(extraction)]
        sortedExtraction = sorted(markPred, key = lambda (ws, indices, f) : indices[0])
        s =  ' '.join(['{1} {0} {1}'.format(self.elementToStr(elem), SEP) if elem[2] else self.elementToStr(elem) for elem in sortedExtraction])
        binArgs = [a for a in s.split(SEP) if a.rstrip().lstrip()]
        
        if len(binArgs) == 2:
            return binArgs
        
        # failure 
        return []
    
    def bow(self):
        return ' '.join([self.elementToStr(elem) for elem in [self.pred] + self.args])

    def getSortedArgs(self):
        ls = []
        for q, args in self.questions.iteritems():
            if (len(args) != 1):
                logging.debug("Not one argument: {}".format(args))
                continue
            arg = args[0]
            indices = list(self.indsForQuestions[q].union(arg.indices))
            if not indices:
                logging.debug("Empty indexes for arg {} -- backing to zero".format(arg))
                indices = [0]
            ls.append(((arg, q), indices))
        return [a for a, _ in sorted(ls, key = lambda (_, indices): min(indices))]


    
    def __str__(self):
        return '{0}\t{1}'.format(self.elementToStr(self.pred),
                                 '\t'.join([escape_special_chars(augment_arg_with_question(self.elementToStr(arg),
                                                                                           question))
                                            for arg, question in self.getSortedArgs()]))

def augment_arg_with_question(arg, question):
    """
    Decide what elements from the question to incorporate in the given
    corresponding predicate
    """
    # Parse question
    wh, aux, sbj, trg, obj1, pp, obj2 = map(normalize_element,
                                            question.split(' ')[:-1]) # Last split is the question mark

    # Place preporition in argument
    # This is safer when dealing with n-ary arguments, as it's directly attaches to the
    # appropriate argument
    if pp and (not obj2):
        if not(arg.startswith("{} ".format(pp))):
            # Avoid repeating the preporition in cases where both question and answer contain it
            return " ".join([pp,
                             arg])

    # Normal cases
    return arg

def normalize_element(elem):
    """
    Return a surface form of the given question element.
    the output should be properly able to precede a predicate (or blank otherwise)
    """
    return elem \
        if (elem != "_")\
           else ""

## Helper functions
def escape_special_chars(s):
    return s.replace('\t', '\\t')



## CONSTANTS
SEP = ';;;'
