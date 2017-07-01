# gets nimsp IDs from votesmart manual data
# https://github.com/votesmart/political-id-match/

import utils
from utils import load_data, save_data
import csv


# default to caching
cache = utils.flags().get('cache', True)
force = not cache

historical = load_data("legislators-historical.yaml")
current = load_data("legislators-current.yaml")

vs_to_nimsp = {}

destination = "matrix.csv"
matrix_url = 'https://github.com/votesmart/political-id-match/raw/master/id_matrix.csv'
matrix = utils.download(matrix_url, destination, force)

for row in csv.DictReader(open('cache/matrix.csv'), delimiter=";"):
    if row['votesmart_candidate_id'] and row['nimsp_entity_id']:
        vs_to_nimsp[row['votesmart_candidate_id']] = row['nimsp_entity_id']

for legislator in current:
    if 'votesmart' in legislator['id']:
        if str(legislator['id']['votesmart']) in vs_to_nimsp:
            legislator['id']['nimsp'] = vs_to_nimsp[str(legislator['id']['votesmart'])]
            print("Found {}, {} is {}".format(legislator['name']['last'],
                                              legislator['id']['votesmart'],
                                              legislator['id']['nimsp']))

utils.save_data(current, "legislators-current.yaml")

for legislator in historical:
    if 'votesmart' in legislator['id']:
        if str(legislator['id']['votesmart']) in vs_to_nimsp:
            legislator['id']['nimsp'] = vs_to_nimsp[str(legislator['id']['votesmart'])]
            print("Found {}, {} is {}".format(legislator['name']['last'],
                                              legislator['id']['votesmart'],
                                              legislator['id']['nimsp']))

utils.save_data(historical, "legislators-historical.yaml")
