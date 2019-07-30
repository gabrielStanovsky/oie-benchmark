import nltk
from operator import itemgetter

class Argument:
    def __init__(self, arg):
        self.words = [x for x in arg[0].strip().split(' ') if x]
        self.posTags = list(map(itemgetter(1), nltk.pos_tag(self.words)))
        self.indices = arg[1]
        self.feats = {}
        
        
COREF = 'coref'

itemgetter