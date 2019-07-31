""" Usage:
    qa_to_oie --in=INPUT_FILE --out=OUTPUT_FILE [--dist=DIST_FILE] [--oieinput=OIE_INPUT] 
"""

from docopt import docopt
import re
import itertools
from oie_readers.extraction import Extraction, escape_special_chars, normalize_element
from collections  import defaultdict
import logging
import operator
import nltk
import json

from oie_readers.extraction import QUESTION_TRG_INDEX
from oie_readers.extraction import QUESTION_PP_INDEX
from oie_readers.extraction import QUESTION_OBJ2_INDEX



## CONSTANTS

PASS_ALL = lambda x: x
MASK_ALL = lambda x: "_"
get_default_mask = lambda : [PASS_ALL] * 8

# QA-SRL vocabulary for "AUX" placement, which modifies the predicates
QA_SRL_AUX_MODIFIERS = [
 #   "are",
    "are n't",
    "can",
    "ca n't",
    "could",
    "could n't",
#    "did",
    "did n't",
#    "do",
#    "does",
    "does n't",
    "do n't",
    "had",
    "had n't",
#    "has",
    "has n't",
#    "have",
    "have n't",
#    "is",
    "is n't",
    "may",
    "may not",
    "might",
    "might not",
    "must",
    "must n't",
    "should",
    "should n't",
#    "was",
    "was n't",
#    "were",
    "were n't",
    "will",
    "wo n't",
    "would",
    "would n't",
]



class Qa2OIE:
    # Static variables
    extractions_counter = 0

    def __init__(self, qaFile, dist_file = ""):
        """
        Loads qa file and converts it into  open IE
        If a distribtion file is given, it is used to determine the hopefully correct
        order of arguments. Otherwise, these are oredered accroding to their linearization
        """
        # This next lines ensures that the json is loaded with numerical
        # indexes for loc
        self.question_dist = dict([(q, dict([(int(loc), cnt)
                                             for (loc, cnt)
                                             in dist.items()]))
                                   for (q, dist)
                                   in json.load(open(dist_file)).items()]) \
                                       if dist_file\
                                          else {}

        self.dic = self.loadFile(self.getExtractions(qaFile))

    def loadFile(self, lines):
        sent = ''
        d = {}

        indsForQuestions = defaultdict(lambda: set())

        for line in lines.split('\n'):
            line = line.strip()
            if not line:
                continue
            data = line.split('\t')
            if len(data) == 1:
                if sent:
                    for ex in d[sent]:
                        ex.indsForQuestions = dict(indsForQuestions)
                sent = line
                d[sent] = []
                indsForQuestions = defaultdict(lambda: set())

            else:
                pred = data[0]
                pred_index = data[1]
                cur = Extraction((pred, all_index(sent, pred, matchCase = False)),
                                 sent,
                                 confidence = 1.0,
                                 question_dist = self.question_dist)
                for q, a in zip(data[2::2], data[3::2]):
                    indices = all_index(sent, a, matchCase = False)
                    cur.addArg((a, indices), q)
                    indsForQuestions[q] = indsForQuestions[q].union(indices)

                if sent:
                    if cur.noPronounArgs():
                        d[sent].append(cur)
        return d

    def getExtractions(self, qa_srl_path, mask = get_default_mask()):
        """
        Parse a QA-SRL file (with raw sentences) at qa_srl_path.
        Returns output which can in turn serve as input for load_file.
        """
        lc = 0
        sentQAs = []
        curAnswers = []
        curSent = ""
        ret = ''

        for line in open(qa_srl_path, 'r'):
            if line.startswith('#'):
                continue
            line = line.strip()
            info = line.strip().split("\t")
            if lc == 0:
                # Read sentence ID.
                sent_id = int(info[0].split("_")[1])
                ptb_id = []
                lc += 1
            elif lc == 1:
                if curSent:
                    ret += self.printSent(curSent, sentQAs)
                # Write sentence.
                curSent = line
                lc += 1
                sentQAs = []
            elif lc == 2:
                if curAnswers:
                    sentQAs.append(((surfacePred, predIndex),
                                    curAnswers))
                curAnswers = []
                # Update line counter.
                if line.strip() == "":
                    lc = 0 # new line for new sent
                else:
                    # reading predicate and qa pairs
                    predIndex, basePred, count = info
                    surfacePred = basePred
                    lc += int(count)
            elif lc > 2:
                question = encodeQuestion("\t".join(info[:-1]), mask)
                curSurfacePred = augment_pred_with_question(basePred, question)
                if len(curSurfacePred) > len(surfacePred):
                    surfacePred = curSurfacePred
                answers = self.consolidate_answers(info[-1].split("###"))
                curAnswers.append(list(zip([question]*len(answers), answers)))

                lc -= 1
                if (lc == 2):
                    # Reached the end of this predicate's questions
                    sentQAs.append(((surfacePred, predIndex),
                                    curAnswers))
                    curAnswers = []
        # Flush
        if sentQAs:
            ret += self.printSent(curSent, sentQAs)

        return ret

    def printSent(self, sent, sentQAs):
        ret =  sent + "\n"
        for (pred, pred_index), predQAs in sentQAs:
            for element in itertools.product(*predQAs):
                self.encodeExtraction(element)
                ret += "\t".join([pred, pred_index] + ["\t".join(x) for x in element]) + "\n"
        ret += "\n"
        return ret

    def encodeExtraction(self, element):
        questions = list(map(operator.itemgetter(0),element))
        extractionSet = set(questions)
        encoding = repr(extractionSet)
        (count, _, extractions) = extractionsDic.get(encoding, (0, extractionSet, []))
        extractions.append(Qa2OIE.extractions_counter)
        Qa2OIE.extractions_counter += 1
        extractionsDic[encoding] = (count+1, extractionSet, extractions)


    def consolidate_answers(self, answers):
        """
        For a given list of answers, returns only minimal answers - e.g., ones which do not
        contain any other answer in the set.
        This deals with certain QA-SRL anntoations which include a longer span than that is needed.
        """
        ret = []
        for i, first_answer in enumerate(answers):
            includeFlag = True
            for j, second_answer in enumerate(answers):
                if (i != j) and (is_str_subset(second_answer, first_answer)) :
                    includeFlag = False
                    continue
            if includeFlag:
                ret.append(first_answer)
        return ret

    def createOIEInput(self, fn):
        with open(fn, 'a') as fout:
            for sent in self.dic:
                fout.write(sent + '\n')

    def writeOIE(self, fn):
        with open(fn, 'w') as fout:
            for sent, extractions in self.dic.items():
                for ex in extractions:
                    fout.write('{}\t{}\n'.format(escape_special_chars(sent), 
                                                 ex.__str__()))

# MORE HELPER
def augment_pred_with_question(pred, question):
    """
    Decide what elements from the question to incorporate in the given
    corresponding predicate
    """
    # Parse question
    wh, aux, sbj, trg, obj1, pp, obj2 = list(map(normalize_element,
                                            question.split(' ')[:-1])) # Last split is the question mark

    # Add auxiliary to the predicate
    if aux in QA_SRL_AUX_MODIFIERS:
        return " ".join([aux, pred])

    # Non modified predicates
    return pred


def is_str_subset(s1, s2):
    """ returns true iff the words in string s1 are contained in string s2 in the same order by which they appear in s2 """
    all_indices = [find_all_indices(s2.split(" "), x) for x in s1.split()]
    if not all(all_indices):
        return False
    for combination in itertools.product(*all_indices):
        if strictly_increasing(combination):
            return True
    return False

def find_all_indices(ls, elem):
    return  [i for i,x in enumerate(ls) if x == elem]

def strictly_increasing(L):
    return all(x<y for x, y in zip(L, L[1:]))


questionsDic = {}
extractionsDic = {}

def encodeQuestion(question, mask):
    info = [mask[i](x).replace(" ","_") for i,x in enumerate(question.split("\t"))]
    encoding = "\t".join(info)
    # get the encoding of a question, and the count of times it appeared
    (val, count) = questionsDic.get(encoding, (len(questionsDic), 0))
    questionsDic[encoding] = (val, count+1)
    ret = " ".join(info)
    return ret

def all_index(s, ss, matchCase = True, ignoreSpaces = True):
    ''' find all occurrences of substring ss in s '''
    if not matchCase:
        s = s.lower()
        ss = ss.lower()

    if ignoreSpaces:
        s = s.replace(' ', '')
        ss = ss.replace(' ','')

    return [m.start() for m in re.finditer(re.escape(ss), s)]

def longest_common_substring(s1, s2):
    m = [[0] * (1 + len(s2)) for i in range(1 + len(s1))]
    longest, x_longest = 0, 0
    for x in range(1, 1 + len(s1)):
        for y in range(1, 1 + len(s2)):
            if s1[x - 1] == s2[y - 1]:
                m[x][y] = m[x - 1][y - 1] + 1
                if m[x][y] > longest:
                    longest = m[x][y]
                    x_longest = x
            else:
                m[x][y] = 0

    start = x_longest - longest
    end = x_longest

    return s1[start:end]



## MAIN
if __name__ == '__main__':
    logging.basicConfig(level = logging.INFO)
    # Parse arguments and call conversions
    args = docopt(__doc__)
    logging.debug(args)
    inp = args['--in']
    out = args['--out']
    dist_file = args['--dist'] if args['--dist']\
           else ''
    q = Qa2OIE(args['--in'], dist_file = dist_file)
    q.writeOIE(args['--out'])
    if args['--oieinput']:
        q.createOIEInput(args['--oieinput'])


