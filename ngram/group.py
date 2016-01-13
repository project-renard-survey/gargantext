# Without this, we couldn't use the Django environment
#from admin.env import *

from admin.utils import PrintException,DebugTime

from gargantext_web.db import NodeNgram,NodeNodeNgram
from gargantext_web.db import *
from gargantext_web.db import get_or_create_node, get_session

from analysis.lists import Translations, UnweightedList
from parsing.corpustools import *

import sqlalchemy as sa
from sqlalchemy.sql import func
from sqlalchemy import desc, asc, or_, and_, Date, cast, select
from sqlalchemy import literal_column
from sqlalchemy.orm import aliased

from collections import defaultdict

#from testlists import *
from math import log
from functools import reduce



def getStemmer(corpus):
    '''
    getStemmer :: Corpus -> Stemmer
    Get the stemmer
    TODO: need to be generic for all languages
    '''
    if corpus.language_id is None or corpus.language_id == cache.Language['en'].id:
        from nltk.stem.porter import PorterStemmer
        stemmer = PorterStemmer()
        #stemmer.stem('honeybees')
    elif corpus.language_id == cache.Language['fr'].id:
        from nltk.stem.snowball import FrenchStemmer
        stemmer = FrenchStemmer()
        #stemmer.stem('abeilles')
    else:
        print("No language found")

    def stemIt(ngram):
        stems = list(map(lambda x: stemmer.stem(x), ngram.split(' ')))
        stems.sort()
        return(str(' '.join(stems)))

    return(stemIt)

def compute_groups(corpus, limit_inf=None, limit_sup=None, how='Stem'):
    '''
    group ngrams according to a function (stemming or lemming)
    '''
    dbg = DebugTime('Corpus #%d - group' % corpus.id)
    dbg.show('Group')

    session = get_session()
    #spec,cvalue = getNgrams(corpus, limit_inf=limit_inf, limit_sup=limit_sup)
    #list_to_check=cvalue.union(spec)

    if how == 'Stem':
        stemIt = getStemmer(corpus)

    group_to_insert = set()
    node_group = get_or_create_node(nodetype='Group', corpus=corpus, session=session)

    miam_to_insert = set()
    miam_node = get_or_create_node(nodetype='MiamList', corpus=corpus, session=session)

    stop_node = get_or_create_node(nodetype='StopList', corpus=corpus, session=session)
    #stop_list = UnweightedList(stop_node.id)

    Stop = aliased(NodeNgram)
    frequency = sa.func.count(NodeNgram.weight)
    

    ngrams = (session.query(Ngram.id, Ngram.terms, frequency )
            .join(NodeNgram, NodeNgram.ngram_id == Ngram.id)
            .join(Node, Node.id == NodeNgram.node_id)
            #.outerjoin(Stop, Stop.ngram_id == Ngram.id)
            #.filter(Stop.node_id == stop_node.id, Stop.ngram_id == None)
            .filter(Node.parent_id==corpus.id, Node.type_id==cache.NodeType['Document'].id)
            .group_by(Ngram.id)
            .order_by(desc(frequency))
            #.all()
            .limit(limit_sup)
            )
    
    stops = (session.query(Ngram.id, Ngram.terms, frequency)
                    .join(NodeNgram, NodeNgram.ngram_id == Ngram.id)
                    .join(Node, Node.id == NodeNgram.node_id)
                    .join(Stop, Stop.ngram_id == Ngram.id)
                    .filter(Stop.node_id == stop_node.id)
                    .filter(Node.parent_id==corpus.id, Node.type_id==cache.NodeType['Document'].id)
                    .group_by(Ngram.id)
                    .all()
                    )

    ngrams = [n + (str(stemIt(n[1])),) for n in ngrams if n not in stops]
    #print(ngrams)
    group = dict()
    group_to_insert = list()
    miam_to_insert = set()

    for n in ngrams:
        # n has form (id, terms, freq, stem)
        # first if stem is not None:
        if n[3] is not None:

            # Adding the id to the forms
            group[n[3]] = group.get(n[3], dict())
            group[n[3]]['forms'] = group[n[3]].get('forms', set())
            group[n[3]]['forms'].add(n[0])
            
            # Take current max
            group[n[3]]['freq'] = group[n[3]].get('freq', 0)
            
            # Update max and mainForm if present ngram (n) has more freq
            if n[2] > group[n[3]]['freq'] :
                group[n[3]]['freq'] = n[2]
                group[n[3]]['mainForm'] = n[0]

    # Adding all ngrams in the list
    for key in group.keys():
        for form in list(group[key]['forms']):
            group_to_insert.append((node_group.id, group[key]['mainForm'], form, 1))
            miam_to_insert.add((miam_node.id, group[key]['mainForm'], 1))

#    # Deleting previous groups
    session.query(NodeNgramNgram).filter(NodeNgramNgram.node_id == node_group.id).delete()
#    # Deleting previous ngrams miam list
    session.query(NodeNgram).filter(NodeNgram.node_id == miam_node.id).delete()
    session.commit()

    bulk_insert(NodeNgramNgram
                , ('node_id', 'ngramx_id', 'ngramy_id', 'score')
                , [data for data in group_to_insert])

    bulk_insert(NodeNgram, ('node_id', 'ngram_id', 'weight'), [data for data in list(miam_to_insert)])
