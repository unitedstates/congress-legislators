#!/usr/bin/python

import re
import urllib.request
import json
from urllib.parse import quote, unquote
from utils import load_data, save_data
from SPARQLWrapper import SPARQLWrapper, JSON

def get_wikidata_ids(legislators):
    # Look up wikidata IDs for legislators with English Wikipedia IDs.
    for p in legislators:
        if not p["id"].get("wikidata") and p["id"].get("wikipedia"):
            w = quote(p["id"]["wikipedia"].replace(" ", "_"))
            query_url = f"https://en.wikipedia.org/w/api.php?action=query&prop=pageprops&titles={w}&format=json"
            response = json.load(urllib.request.urlopen(query_url))
            wikidata_id = list(response["query"]["pages"].values())[0]["pageprops"]["wikibase_item"]
            p["id"]["wikidata"] = wikidata_id


def get_ids_from_wikidata(legislators):
    # Query to fetch information for entities that have a bioguide ID.
    # Selecting on bioguide ID efficiently gets wikidata entries that
    # we are interested in.

    table = run_query("""
      PREFIX wdt: <http://www.wikidata.org/prop/direct/>
      PREFIX schema: <http://schema.org/>

      SELECT ?subject ?bioguide ?wikipedia ?google_entity_id ?opensecrets ?votesmart ?ballotpedia
      WHERE {
        ?subject wdt:P1157 ?bioguide .
        OPTIONAL {
            ?subject wdt:P2671 ?google_entity_id
        }
        OPTIONAL {
            ?subject wdt:P2686 ?opensecrets
        }
        OPTIONAL {
            ?subject wdt:P3344 ?votesmart
        }
        OPTIONAL {
            ?subject wdt:P2390 ?ballotpedia
        }
        OPTIONAL {
            ?wikipedia schema:about ?subject .
            ?wikipedia schema:inLanguage "en" .
            ?wikipedia schema:isPartOf <https://en.wikipedia.org/> .
        }
      }
    """)

    # make a mapping from bioguide ID to query result
    mapping = { r["bioguide"]: r for r in table }

    # update legislators
    for p in legislators:
        if p["id"].get("bioguide") in mapping:
            p["id"].update(mapping[p["id"]["bioguide"]])


def get_ids_from_wikidata_without_bioguide(legislators):
    # The SQPARL server doesn't seem to suppor VALUES or FILTER(?subject IN (...))
    # so in order to fill in values for legislators without bioguide IDs but with
    # wikidata IDs, we can just query them one by one. This probably is only useful
    # at the start of a new Congress when bioguide IDs are not yet available.
    for p in legislators:
        if not ("bioguide" not in p["id"] and "wikidata" in p["id"]): continue

        table = run_query("""
          PREFIX wd: <http://www.wikidata.org/entity/>
          PREFIX wdt: <http://www.wikidata.org/prop/direct/>
          PREFIX schema: <http://schema.org/>

          SELECT ?wikipedia ?google_entity_id ?opensecrets ?votesmart ?ballotpedia
          WHERE {
            OPTIONAL {
                ?subject wdt:P2671 ?google_entity_id
            }
            OPTIONAL {
                ?subject wdt:P2686 ?opensecrets
            }
            OPTIONAL {
                ?subject wdt:P3344 ?votesmart
            }
            OPTIONAL {
                ?subject wdt:P2390 ?ballotpedia
            }
            OPTIONAL {
                ?wikipedia schema:about ?subject .
                ?wikipedia schema:inLanguage "en" .
                ?wikipedia schema:isPartOf <https://en.wikipedia.org/> .
            }
          }
        """.replace("?subject", "wd:" + p["id"]["wikidata"]))


        p["id"].update(table[0])


def run_query(query):
    sparql_endpoint = 'https://query.wikidata.org/bigdata/namespace/wdq/sparql'
    s = SPARQLWrapper(sparql_endpoint)

    # run the query
    s.setQuery(query)
    s.setReturnFormat(JSON)
    results = s.query().convert()

    for row in results['results']['bindings']:
        if "subject" in row:
            # replace the ?subject variable with the wikidata id
            row['wikidata'] = { "value": re.search(r'/(Q\d+)', row['subject']['value']).group(1) }
            del row["subject"]

        # clean up the google entity id
        if 'google_entity_id' in row:
            row['google_entity_id']["value"] = 'kg:' + row['google_entity_id']["value"]

        # clean up the wikipedia and ballotpedia results
        if "wikipedia" in row:
            row["wikipedia"]["value"] = \
                unquote(row["wikipedia"]["value"])\
                .replace("https://en.wikipedia.org/wiki/", "")\
                .strip().replace('_',' ')
        if "ballotpedia" in row:
            row["ballotpedia"]["value"] = row["ballotpedia"]["value"].strip().replace('_',' ')

        # clean up the votesmart id
        if "votesmart" in row:
            try:
                row["votesmart"]["value"] = int(row["votesmart"]["value"])
            except ValueError:
                print("invalid value", row["votesmart"]["value"])
                continue
    # return a simple list of dicts of results
    return [
        {
            k: row[k]['value']
            for k in row
        }
        for row in results['results']['bindings']
    ]


def run():
  p1 = load_data("legislators-current.yaml")
  p2 = load_data("legislators-historical.yaml")
  get_wikidata_ids(p1+p2)
  get_ids_from_wikidata(p1+p2)
  get_ids_from_wikidata_without_bioguide(p1+p2)
  save_data(p1, "legislators-current.yaml")
  save_data(p2, "legislators-historical.yaml")

if __name__ == '__main__':
  run()


