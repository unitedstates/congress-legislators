# Validate that the YAML files have sane data.

import sys
from datetime import date

import rtyaml

sys.path.insert(0, "scripts")
import utils

ok = True
def error(message):
  global ok
  print(message)
  ok = False

# data types expected for each sort of ID
id_types = {
  "bioguide": str,
  "bioguide_previous": list,
  "lis": str,
  "fec": list,
  "govtrack": int,
  "opensecrets": str,
  "votesmart": int,
  "maplight": int,
  "icpsr": int,
  "cspan": int,
  "wikipedia": str,
  "ballotpedia": str,
  "house_history": int,
  "house_history_alternate": int,
  "wikidata": str,

  # deprecated/to be removed
  "thomas": str,
  "washington_post": str,
}

# name keys
name_keys = { "first", "middle", "nickname", "last", "suffix", "official_full" }

# bio keys
bio_keys = { "gender", "birthday", "religion" }

# get today as a date instance
def now():
  import datetime
  return datetime.datetime.now().date()
now = now()

def check_legislators_file(fn, seen_ids, current=None, current_mocs=None):
  # Open and iterate over the entries.
  with open(fn) as f:
    legislators = rtyaml.load(f)
  for legislator in legislators:
    
    # Check the IDs.
    if "id" not in legislator:
      error(repr(legislator) + " is missing 'id'.")
    else:
      # Check that the IDs are valid.
      check_id_types(legislator)

      # Every legislator should have a bioguide and GovTrack ID.
      if "bioguide" not in legislator["id"]:
        error("Legislator is missing a bioguide ID.")
      if "govtrack" not in legislator["id"]:
        error("Legislator is missing a govtrack ID.")

    # Check the name.
    if "name" not in legislator:
      error(repr(legislator) + " is missing 'name'.")
    else:
      check_name(legislator["name"])
    for name in legislator.get("other_names", []):
      check_name(name, is_other_names=True)

    # Check the biographical fields.
    if "bio" not in legislator:
      error(repr(legislator) + " is missing 'bio'.")
    else:
      for key, value in legislator["bio"].items():
        if key not in bio_keys:
          error("%s is not a valid key in bio." % key)
        elif not isinstance(value, str):
          error(rtyaml.dump({ key: value }) + " has an invalid data type.")

    # Check the terms.
    if "terms" not in legislator:
      error(repr(legislator) + " is missing 'terms'.")
    elif not isinstance(legislator["terms"], list):
      error(repr(legislator) + " terms has an invalid data type.")
    elif len(legislator["terms"]) == 0:
      error(repr(legislator) + " terms is empty.")
    else:
      prev_term = None
      for i, term in enumerate(legislator["terms"]):
        check_term(term, prev_term,
          current=(current and i==len(legislator["terms"])-1),
          current_mocs=current_mocs)
        prev_term = term

    # Check the leadership roles.
    for role in legislator.get("leadership_roles", []):
      # All of these fields must be strings.
      for key, value in role.items():
        if not isinstance(value, str):
          error(rtyaml.dump({ key: value }) + " has an invalid data type.")

      # Check required fields.
      if "title" not in role:
        error(rtyaml.dump(role) + " is missing title.")
      if role.get("chamber") not in ("house", "senate"):
        error(rtyaml.dump(role) + " has an invalid chamber.")
      if "start" not in role:
        error(rtyaml.dump(role) + " is missing start.")
      if "end" not in role and not current:
        # end is required only in the historical file
        error(rtyaml.dump(role) + " is missing end.")

      # Check dates.
      start = check_date(role['start'])
      if "end" in role:
        end = check_date(role['end'])
        if start and end and end < start:
          error(rtyaml.dump(role) + " has end before start.")

def check_id_types(legislator):
  for key, value in legislator["id"].items():
    # Check that the id key is one we know about.
    if key not in id_types:
      error(rtyaml.dump({ key: value }) + " is not a valid id.")

    # Check that the data type is correct.
    elif not isinstance(value, id_types[key]):
      error(rtyaml.dump({ key: value }) + " has an invalid data type.")

    else:
      # Check that the ID isn't duplicated across legislators.
      # Since some values are lists of IDs, check the elements.
      if not isinstance(value, list): value = [value]
      for v in value:
        if (key, v) in seen_ids:
          error(rtyaml.dump({ key: v }) + " is duplicated.")
        seen_ids.add((key, v))

def check_name(name, is_other_names=False):
  for key, value in name.items():
    if key in ("start", "end") and is_other_names:
      if not isinstance(value, str):
        error(rtyaml.dump({ key: value }) + " has an invalid data type.")
    elif key not in name_keys:
      error("%s is not a valid key in name." % key)
    elif key in ("first", "last"):
      # These are required.
      if not isinstance(value, str):
        error(rtyaml.dump({ key: value }) + " has an invalid data type.")
    else:
      # These can be set explicitly to None, but maybe we should just remove
      # those keys then.
      if not isinstance(value, (str, type(None))):
        error(rtyaml.dump({ key: value }) + " has an invalid data type.")

def check_term(term, prev_term, current=None, current_mocs=None):
  # Check type.
  if term.get("type") not in ("rep", "sen"):
    error(rtyaml.dump(term) + " has invalid type.")

  # Check date range.
  start = check_date(term.get('start'))
  end = check_date(term.get('end'))
  if start and end:
    if end < start:
      error(rtyaml.dump(term) + " has end before start.")

    # TODO: Remove 'and end > "2000-"'. I'm just adding it because
    # lots of historical data fails this test.
    if prev_term and end > date(2000,1,1):
      prev_end = check_date(prev_term.get("end"))
      if prev_end:
        if start < prev_end:
          error(rtyaml.dump(term) + " has start before previous term's end.")

    if not current and (end > now):
      error(rtyaml.dump(term) + " has an end date in the future but should be historical.")
    if current and (end < now):
      error(rtyaml.dump(term) + " has an end date in the past but should be current.")

  # Check state, district, class, state_rank.
  if term.get("state") not in utils.states:
    error(rtyaml.dump(term) + " has invalid state.")
  if term.get("type") == "rep":
    if not isinstance(term.get("district"), int):
      error(rtyaml.dump(term) + " has invalid district.")
  if term.get("type") == "sen":
    if term.get("class") not in (1, 2, 3):
      error(rtyaml.dump(term) + " has invalid class.")
    if term.get("state_rank") not in ("junior", "senior", None):
      error(rtyaml.dump(term) + " has invalid senator state_rank.")
    elif current and term.get("state_rank") is None:
      error(rtyaml.dump(term) + " is missing senator state_rank.")

  if current:
    # Check uniqueness of office for current members.

    # Check office.
    office = (term.get("type"), term.get("state"), term.get("district") or term.get("class"))
    if office in current_mocs:
      error(rtyaml.dump(term) + " duplicates an office.")
    current_mocs.add(office)

    # Check senator rank isn't duplicated.
    if term.get("type") == "sen":
      office = (term.get("state"), term.get("state_rank"))
      if office in current_mocs:
        error(rtyaml.dump(term) + " duplicates state_rank in a state.")
      current_mocs.add(office)

    # Check party of current members (historical is too difficult).
    if term.get("party") not in ("Republican", "Democrat", "Independent"):
      error(rtyaml.dump({ "party": term.get("party") }) + " is invalid.")

    # Check caucus of Independent members.
    if term.get("party") == "Independent" and term.get("caucus") not in ("Republican", "Democrat"):
      error(rtyaml.dump({ "caucus": term.get("caucus") }) + " is invalid when party is Independent.")

    # TODO: Check party_affiliations, url, and office information.  

def check_date(d):
  if not isinstance(d, str):
    error(str(d) + ": invalid data type")
    return None
  try:
    return utils.parse_date(d)
  except Exception as e:
    error(d + ": " + str(e))
    return None

if __name__ == "__main__":
  # Check the legislators files.
  seen_ids = set()
  current_mocs = set()
  check_legislators_file("legislators-current.yaml", seen_ids, current=True, current_mocs=current_mocs)
  check_legislators_file("legislators-historical.yaml", seen_ids, current=False)

  # Exit with exit status.
  sys.exit(0 if ok else 1)
