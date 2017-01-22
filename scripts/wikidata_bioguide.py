#!/usr/bin/python

import re
from urllib.parse import unquote
from utils import load_data, save_data
from SPARQLWrapper import SPARQLWrapper, JSON

def run():
    sparql_endpoint = 'https://query.wikidata.org/bigdata/namespace/wdq/sparql'
    s = SPARQLWrapper(sparql_endpoint)

    # sparql query to fetch the wikidata url, wikipedia url, freebase id, knowledge graph id
    query = """
      PREFIX wd: <http://www.wikidata.org/entity/>
      PREFIX wdt: <http://www.wikidata.org/prop/direct/>
      PREFIX schema: <http://schema.org/>

      SELECT ?bio ?subject ?article ?freebase ?kg ?opensecrets ?votesmart
      WHERE {
        ?subject wdt:P1157 ?bio .
        OPTIONAL {
            ?subject wdt:P646 ?freebase #freebase
        }
        OPTIONAL {
            ?subject wdt:P2671 ?kg     #google knowledge graph
        }
        OPTIONAL {
            ?subject wdt:P2686 ?opensecrets
        }
        OPTIONAL {
            ?subject wdt:P3344 ?votesmart
        }
        OPTIONAL {
            ?article schema:about ?subject .
            ?article schema:inLanguage "en" .
            ?article schema:isPartOf <https://en.wikipedia.org/> .
        }
      }
    """

    # run the query and stick everything in a big hash keyed by bioguide id
    s.setQuery(query)
    s.setReturnFormat(JSON)
    results = s.query().convert()
    ret = {}

    for row in results['results']['bindings']:
        goog_id = wikidata_id = wikipedia = kg = freebase = opensecrets = votesmart = False
        rks = row.keys()
        bio = row['bio']['value']
        subject = row['subject']['value']
        article = row['article']['value']
        if('votesmart' in rks):
            votesmart = row['votesmart']['value']
        if('opensecrets' in rks):
            opensecrets = row['opensecrets']['value']
        if('freebase' in rks):
            freebase = row['freebase']['value']
        if('kg' in rks):
            kg = row['kg']['value']

        m = re.search('/(Q\d+)',subject)
        if(m):
            wikidata_id = m.group(1)

        # freebase and kg should be mutually exclusive
        goog_id = freebase or kg
        if(not goog_id or not re.search('/(m|g)/.+',goog_id)):
            goog_id = False

        article = unquote(article)
        m = re.search('en\.wikipedia\.org/wiki/(.+)',article)
        if(m):
            wikipedia = m.group(1)

        ret[bio] = [wikidata_id, goog_id, wikipedia, opensecrets, votesmart]
        #print(bio, subject, wikidata_id, article, goog_id)

    # now loop through the legislators file matching on bio id

    bks = ret.keys()
    y = load_data("legislators-current.yaml")

    for m in y:
        if(not 'id' in m.keys()):
            print(m)
            continue
        ks = m['id'].keys()
        if(not 'bioguide' in ks or not m['id']['bioguide'] in bks):
            print('not found')
            print(m)
            continue
        (wikidata_id, goog_id, wikipedia, opensecrets, votesmart) = ret[m['id']['bioguide']]

        if(wikipedia):
            m['id']['wikipedia'] = wikipedia
        if(wikidata_id):
            m['id']['wikidata'] = wikidata_id
        if(goog_id):
            m['id']['google_entity_id'] = 'kg:' + goog_id
        if(opensecrets):
            m['id']['opensecrets'] = opensecrets
        if(votesmart):
            m['id']['votesmart'] = int(votesmart)
    save_data(y, "legislators-current.yaml")

if __name__ == '__main__':
  run()
