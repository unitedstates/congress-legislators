#print out leadership roles for manual review

import rtyaml
import utils

with open("legislators-current.yaml") as f:
  legislators = rtyaml.load(f)
for legislator in legislators:
  if 'leadership_roles' in legislator:
    print("{}, {}".format(legislator["name"]["last"], legislator["name"]["first"]))
  for role in legislator.get("leadership_roles", []):
    
    start = utils.parse_date(role["start"])
    if not "end" in role:
      print("{} {} started {} with no end".format(role["chamber"], role["title"], role["start"]))
    else:
      print("{} {} started {} and ended {}".format(role["chamber"], role["title"], role["start"], role["end"]))
    
