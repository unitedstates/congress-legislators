# -*- coding: utf-8 -*-

from scripts.party_divisions_house import house_dictionary
from scripts.party_divisions_senate import senate_dictionary
from collections import OrderedDict
import yaml

party_divisions = OrderedDict()
hd = house_dictionary['Congress']

for k,v in hd.items():
    party_divisions.update({k:{'House':v,'Senate':senate_dictionary[k]}})
party_divisions.update({'README':{'House':house_dictionary['README'], 
                                  'Senate':{'source':'https://www.senate.gov/history/partydiv.htm'}
                                  }})

    
with open('party-divisions.yaml', 'w') as outfile:
    yaml.dump(party_divisions, outfile, default_flow_style=False)    
    
    
