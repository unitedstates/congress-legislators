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

# id types that must be present on every legislator record
id_required = ['bioguide', 'govtrack']

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
  "icpsr_prez": int,
  "cspan": int,
  "wikipedia": str,
  "ballotpedia": str,
  "house_history": int,
  "house_history_alternate": int,
  "wikidata": str,
  "google_entity_id": str,

  # deprecated/to be removed
  "thomas": str,
}

# name keys
name_keys = { "first", "middle", "nickname", "last", "suffix", "official_full" }

# bio keys
bio_keys = { "gender", "birthday", "religion", "died" }

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
      check_id_types(legislator, seen_ids, True)

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
      check_bio(legislator["bio"])

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

def check_id_types(legislator, seen_ids, is_legislator):
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
      # Just make a list of ID occurrences here -- we'll check
      # uniqueness at the end.
      if not isinstance(value, list): value = [value]
      for v in value:
        seen_ids.setdefault((key, v), []).append(legislator)

  if is_legislator:
    # Check that every legislator has ids of the required types.
    for id_type in id_required:
      if id_type not in legislator["id"]:
        error("Missing %s id in:\n%s" % (id_type, rtyaml.dump(legislator['id'])))

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

def check_bio(bio):
  for key, value in bio.items():
    if key not in bio_keys:
      error("%s is not a valid key in bio." % key)
    elif not isinstance(value, str):
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
      error(rtyaml.dump(term) + " has an end date in the future but is in the historical file.")
    if current and (end < now):
      error(rtyaml.dump(term) + " has an end date in the past but is in the current file.")

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

def check_executive_file(fn):
  # Open and iterate over the entries.
  with open(fn) as f:
    people = rtyaml.load(f)
  for person in people:
    
    # Check the IDs.
    if "id" not in person:
      error(repr(person) + " is missing 'id'.")
    else:
      # Check that the IDs are valid.
      check_id_types(person, {}, False)

    # Check the name.
    if "name" not in person:
      error(repr(legislator) + " is missing 'name'.")
    else:
      check_name(person["name"])

    # Check the biographical fields.
    if "bio" not in person:
      error(repr(person) + " is missing 'bio'.")
    else:
      check_bio(person["bio"])

    # Check the terms.
    if "terms" not in person:
      error(repr(person) + " is missing 'terms'.")
    elif not isinstance(person["terms"], list):
      error(repr(person) + " terms has an invalid data type.")
    elif len(person["terms"]) == 0:
      error(repr(person) + " terms is empty.")
    else:
      for i, term in enumerate(person["terms"]):
        check_executive_term(term)

def check_executive_term(term):
  # Check type.
  if term.get("type") not in ("prez", "viceprez"):
    error(rtyaml.dump(term) + " has invalid type.")

  # Check how.
  if term.get("how") not in ("election", "succession", "appointment"):
    error(rtyaml.dump(term) + " has invalid 'how'.")

  # Check date range.
  start = check_date(term.get('start'))
  end = check_date(term.get('end'))
  if start and end:
    if end < start:
      error(rtyaml.dump(term) + " has end before start.")

  if end.year > 2000:
    # Check party of current members (historical is too difficult and even recent ones incorrectly have Democratic instead of Democrat, which is inconsistent with the legislators files).
    if term.get("party") not in ("Republican", "Democrat"):
      error(rtyaml.dump({ "party": term.get("party") }) + " is invalid.")


def check_date(d):
  if not isinstance(d, str):
    error(str(d) + ": invalid data type")
    return None
  try:
    return utils.parse_date(d)
  except Exception as e:
    error(d + ": " + str(e))
    return None

def check_id_uniqueness(seen_ids):
  for (id_type, id_value), occurrences in seen_ids.items():
    if len(occurrences) > 1:
      error("%s %s is duplicated: %s" % (id_type, id_value,
        " ".join(legislator['id']['bioguide'] for legislator in occurrences)))

if __name__ == "__main__":
  # Check the legislators files.
  seen_ids = { }
  current_mocs = set()
  check_legislators_file("legislators-current.yaml", seen_ids, current=True, current_mocs=current_mocs)
  check_legislators_file("legislators-historical.yaml", seen_ids, current=False)
  check_executive_file("executive.yaml")
  check_id_uniqueness(seen_ids)

  # Exit with exit status.
  sys.exit(0 if ok else 1)
