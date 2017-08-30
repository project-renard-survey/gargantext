"""
   Gargantext Software Copyright (c) 2016-2017 CNRS ISC-PIF -
http://iscpif.fr
    Licence (see :
http://gitlab.iscpif.fr/humanities/gargantext/blob/stable/LICENSE )
    - In France : a CECILL variant affero compliant
    - GNU aGPLV3 for all other countries
"""
#!/usr/bin/env python
import sys
import os


# Django settings
dirname = os.path.dirname(os.path.realpath(__file__))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gargantext.settings")

# initialize Django application
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

from gargantext.util.toolchain.main import parse_extract_indexhyperdata
from gargantext.util.db import *
from gargantext.models import Node
from gargantext.util.toolchain.main import parse_extract_indexhyperdata
from nltk.tokenize import wordpunct_tokenize

from gargantext.models import *
from nltk.tokenize import word_tokenize
import nltk as nltk
from statistics import mean
from math import log
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np
import datetime

from collections import Counter
from langdetect import detect as detect_lang

def documents(corpus_id):
    return (session.query(Node).filter( Node.parent_id==corpus_id
                                  , Node.typename=="DOCUMENT"
                                  )
        # .order_by(Node.hyperdata['publication_date'])
        .all()
        )


#import seaborn as sns
import pandas as pd

def chart(docs, field):
    year_publis = list(Counter([doc.hyperdata[field] for doc in docs]).items())
    frame0 = pd.DataFrame(year_publis, columns=['Date', 'DateValue'])
    frame1 = pd.DataFrame(year_publis, columns=['Date', 'DateValue'], index=frame0.Date)
    return frame1

from gargantext.util.crawlers.HAL import HalCrawler
def scan_hal(request):
    hal = HalCrawler()
    return hal.scan_results(request)

def scan_gargantext(corpus_id, lang, request):
    connection = get_engine().connect()
    # TODO add some sugar the request (ideally request should be the same for hal and garg)
    query = """select count(n.id) from nodes n
                  where to_tsvector('%s', hyperdata ->> 'abstract' || 'title') 
                  @@ to_tsquery('%s')
                  AND n.parent_id = %s;""" % (lang, request, corpus_id) 
    return [i for i in connection.execute(query)][0][0]
    connection.close()


def myProject_fromUrl(url):
    """
    myProject :: String -> Project
    """
    project_id = url.split("/")[4]
    project = session.query(Node).filter(Node.id == project_id).first()
    return project


def newCorpus(project, resourceName=11, name="Machine learning", query="LSTM"):
    print("Corpus \"%s\" in project \"%s\" created" % (name, project.name))
    
    corpus = project.add_child(name="Corpus name", typename='CORPUS')
    corpus.hyperdata["resources"] = [{"extracted" : "true", "type" : 11}]
    corpus.hyperdata["statuses"]  = [{"action" : "notebook", "complete" : "true"}]
    # [TODO] Add informations needed to get buttons on the Project view.
    session.add(corpus)
    session.commit()
    
    hal = HalCrawler()
    max_result = hal.scan_results(query)
    paging = 100 
    for page in range(0, max_result, paging):
        print("%s documents downloaded / %s." % (str( paging * (page +1)), str(max_result) ))
        docs = (hal._get(query, fromPage=page, count=paging)
                     .get("response", {})
                      .get("docs", [])
               )
            
        from gargantext.util.parsers.HAL import HalParser
        # [TODO] fix boilerplate for docs here
        new_docs = HalParser(docs)._parse(docs)
        
        for doc in new_docs:
            new_doc = (corpus.add_child( name      = doc["title"][:255]
                                       , typename  = 'DOCUMENT')
                      )
            new_doc["hyperdata"] = doc
            session.add(new_doc)
            session.commit()
    
    print("Extracting the ngrams")
    parse_extract_indexhyperdata(corpus)
    
    print("Corpus is ready to explore:")
    print("http://imt.gargantext.org/projects/%s/corpora/%s/" % (project.id, corpus.id))
    
    return corpus
