from sklearn.preprocessing.data import binarize
from oie_readers.argument import Argument
from operator import itemgetter
from collections import defaultdict
import nltk
import logging

class Extraction:
    ''' holds sentence, single predicate and corresponding arguments '''
    def __init__(self, pred, sent, confidence, question_dist = '', splits_conjunctions = False):
        self.pred = pred
        self.sent = sent
        self.args = []
        self.confidence = confidence
        self.matched = []
        self.questions = {}
        self.indsForQuestions = defaultdict(lambda: set())
        self.is_mwp = False
        self.question_dist = question_dist
        self.splits_conjunctions = splits_conjunctions

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
        sortedExtraction = sorted(markPred, key = lambda ws_indices_f : ws_indices_f[1][0])
        s =  ' '.join(['{1} {0} {1}'.format(self.elementToStr(elem), SEP) if elem[2] else self.elementToStr(elem) for elem in sortedExtraction])
        binArgs = [a for a in s.split(SEP) if a.rstrip().lstrip()]
        
        if len(binArgs) == 2:
            return binArgs
        
        # failure 
        return []
    
    def bow(self):
        return ' '.join([self.elementToStr(elem) for elem in [self.pred] + self.args])

    def getSortedArgs(self):
        """
        Sort the list of arguments.
        If a question distribution is provided - use it,
        otherwise, default to the order of appearance in the sentence.
        """
        if self.question_dist:
            # There's a question distribtuion - use it
            return self.sort_args_by_distribution()
        ls = []
        for q, args in self.questions.items():
            if (len(args) != 1):
                logging.debug("Not one argument: {}".format(args))
                continue
            arg = args[0]
            indices = list(self.indsForQuestions[q].union(arg.indices))
            if not indices:
                logging.debug("Empty indexes for arg {} -- backing to zero".format(arg))
                indices = [0]
            ls.append(((arg, q), indices))
        return [a for a, _ in sorted(ls,
                                     key = lambda __indices: min(__indices[1]))]

    def question_prob_for_loc(self, question, loc):
        """
        Returns the probability of the given question leading to argument
        appearing in the given location in the output slot.
        """
        gen_question = generalize_question(question)
        q_dist = self.question_dist[gen_question]
        logging.debug("distribution of {}: {}".format(gen_question,
                                                      q_dist))

        return float(q_dist.get(loc, 0)) /  \
            sum(q_dist.values())

    def sort_args_by_distribution(self):
        """
        Use this instance's question distribution (this func assumes it exists)
        in determining the positioning of the arguments.
        Greedy algorithm:
        0. Decide on which argument will serve as the ``subject'' (first slot) of this extraction
        0.1 Based on the most probable one for this spot
        (special care is given to select the highly-influential subject position)
        1. For all other arguments, sort arguments by the prevalance of their questions
        2. For each argument:
        2.1 Assign to it the most probable slot still available
        2.2 If non such exist (fallback) - default to put it in the last location
        """
        INF_LOC = 100 # Used as an impractical last argument

        # Store arguments by slot
        ret = {INF_LOC: []}
        logging.debug("sorting: {}".format(self.questions))

        # Find the most suitable arguemnt for the subject location
        logging.debug("probs for subject: {}".format([(q, self.question_prob_for_loc(q, 0))
                                                      for (q, _) in self.questions.items()]))

        subj_question, subj_args = max(iter(self.questions.items()),
                                       key = lambda q__: self.question_prob_for_loc(q__[0], 0))

        ret[0] = [(subj_args[0], subj_question)]

        # Find the rest
        for (question, args) in sorted([(q, a)
                                        for (q, a) in self.questions.items() if (q not in [subj_question])],
                                       key = lambda q__1: \
                                       sum(self.question_dist[generalize_question(q__1[0])].values()),
                                       reverse = True):
            gen_question = generalize_question(question)
            arg = args[0]
            assigned_flag = False
            for (loc, count) in sorted(iter(self.question_dist[gen_question].items()),
                                       key = lambda __c: __c[1],
                                       reverse = True):
                if loc not in ret:
                    # Found an empty slot for this item
                    # Place it there and break out
                    ret[loc] = [(arg, question)]
                    assigned_flag = True
                    break

            if not assigned_flag:
                # Add this argument to the non-assigned (hopefully doesn't happen much)
                logging.debug("Couldn't find an open assignment for {}".format((arg, gen_question)))
                ret[INF_LOC].append((arg, question))

        logging.debug("Linearizing arg list: {}".format(ret))

        # Finished iterating - consolidate and return a list of arguments
        return [arg
                for (_, arg_ls) in sorted(iter(ret.items()),
                                          key = lambda k_v: int(k_v[0]))
                for arg in arg_ls]


    def __str__(self):
        pred_str = self.elementToStr(self.pred)
        return '{}\t{}\t{}'.format(self.get_base_verb(pred_str),
                                   self.compute_global_pred(pred_str,
                                                            list(self.questions.keys())),
                                   '\t'.join([escape_special_chars(self.augment_arg_with_question(self.elementToStr(arg),
                                                                                                  question))
                                              for arg, question in self.getSortedArgs()]))

    def get_base_verb(self, surface_pred):
        """
        Given the surface pred, return the original annotated verb
        """
        # Assumes that at this point the verb is always the last word
        # in the surface predicate
        return surface_pred.split(' ')[-1]


    def compute_global_pred(self, surface_pred, questions):
        """
        Given the surface pred and all instansiations of questions,
        make global coherence decisions regarding the final form of the predicate
        This should hopefully take care of multi word predicates and correct inflections
        """
        from operator import itemgetter
        split_surface = surface_pred.split(' ')

        if len(split_surface) > 1:
            # This predicate has a modal preceding the base verb
            verb = split_surface[-1]
            ret = split_surface[:-1] # get all of the elements in the modal
        else:
            verb = split_surface[0]
            ret = []

        split_questions = [question.split(' ') for question in questions]

        preds = list(map(normalize_element,
                    list(map(itemgetter(QUESTION_TRG_INDEX),
                        split_questions))))
        if len(set(preds)) > 1:
            # This predicate is appears in multiple ways, let's stick to the base form
            ret.append(verb)

        if len(set(preds)) == 1:
            # Change the predciate to the inflected form
            # if there's exactly one way in which the predicate is conveyed
            ret.append(preds[0])

            pps = list(map(normalize_element,
                      list(map(itemgetter(QUESTION_PP_INDEX),
                          split_questions))))

            obj2s = list(map(normalize_element,
                        list(map(itemgetter(QUESTION_OBJ2_INDEX),
                            split_questions))))

            if (len(set(pps)) == 1):
                # If all questions for the predicate include the same pp attachemnt -
                # assume it's a multiword predicate
                self.is_mwp = True # Signal to arguments that they shouldn't take the preposition
                ret.append(pps[0])

        # Concat all elements in the predicate and return
        return " ".join(ret).strip()


    def augment_arg_with_question(self, arg, question):
        """
        Decide what elements from the question to incorporate in the given
        corresponding argument
        """
        # Parse question
        wh, aux, sbj, trg, obj1, pp, obj2 = list(map(normalize_element,
                                                question.split(' ')[:-1])) # Last split is the question mark

        # Place preposition in argument
        # This is safer when dealing with n-ary arguments, as it's directly attaches to the
        # appropriate argument
        if (not self.is_mwp) and pp and (not obj2):
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
    return elem.replace("_", " ") \
        if (elem != "_")\
           else ""

## Helper functions
def escape_special_chars(s):
    return s.replace('\t', '\\t')


def generalize_question(question):
    """
    Given a question in the context of the sentence and the predicate index within
    the question - return a generalized version which extracts only order-imposing features
    """
    import nltk   # Using nltk since couldn't get spaCy to agree on the tokenization
    wh, aux, sbj, trg, obj1, pp, obj2 = question.split(' ')[:-1] # Last split is the question mark
    return ' '.join([wh, sbj, obj1])



## CONSTANTS
SEP = ';;;'
QUESTION_TRG_INDEX =  3 # index of the predicate within the question
QUESTION_PP_INDEX = 5
QUESTION_OBJ2_INDEX = 6
