# Validate that the YAML files have sane data.

import os, sys
from datetime import date, datetime

import rtyaml

sys.path.insert(0, "scripts")
import utils
from office_validator import run as validate_offices

ok = True
def error(context, message):
  global ok
  print(context + ": " + message)
  ok = False

# Current apportionment of the U.S. House, so that we can report if there
# are any vacancies in legislators-current. Each state is mapped to an
# integer (>= 1) giving its number of House seats. Additionally the
# territories that send delegates are mapped to the string "T".
state_apportionment = {
  'AL': 7, 'AK': 1, 'AS': 'T', 'AZ': 9, 'AR': 4, 'CA': 53, 'CO': 7, 'CT': 5,
  'DE': 1, 'DC': 'T', 'FL': 27, 'GA': 14, 'GU': 'T', 'HI': 2, 'ID': 2, 'IL': 18,
  'IN': 9, 'IA': 4, 'KS': 4, 'KY': 6, 'LA': 6, 'ME': 2, 'MD': 8, 'MA': 9, 'MI': 14,
  'MN': 8, 'MS': 4, 'MO': 8, 'MT': 1, 'NE': 3, 'NV': 4, 'NH': 2, 'NJ': 12,
  'NM': 3, 'NY': 27, 'NC': 13, 'ND': 1, 'MP': 'T', 'OH': 16, 'OK': 5, 'OR': 5,
  'PA': 18, 'PR': 'T', 'RI': 2, 'SC': 7, 'SD': 1, 'TN': 9, 'TX': 36, 'UT': 4,
  'VT': 1, 'VI': 'T', 'VA': 11, 'WA': 10, 'WV': 3, 'WI': 8, 'WY': 1
  }

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
bio_keys = { "gender", "birthday" }

# get today as a date instance
def now():
  if os.environ.get('NOW'):
    # Use the date given in the environment variable so that
    # we can stage election results and have tests pass.
    # Use: export NOW=2017-01-03
    return date(*[int(v) for v in os.environ['NOW'].split('-')])
  return datetime.now().date()
now = now()

def check_legislators_file(fn, seen_ids, current=None, current_mocs=None):
  # Open and iterate over the entries.
  with open(fn) as f:
    legislators = rtyaml.load(f)
  for legislator in legislators:
    # Create a string for error messages to tell us where problems are ocurring.
    context = "{} in {}".format(fn, repr(legislator))

    # Check the IDs.
    if "id" not in legislator:
      error(context, "Missing 'id' mapping.")
    else:
      # Check that the IDs are valid.
      check_id_types(legislator, seen_ids, True, context)

    # Create a string for error messages to tell us where problems are ocurring.
    context = "{}:{}".format(fn, legislator['id']['bioguide'])

    # Check the name.
    if "name" not in legislator:
      error(context, "Missing 'name' mapping.")
    else:
      check_name(legislator["name"], context)
    for name in legislator.get("other_names", []):
      check_name(name, context + ":other_names", is_other_names=True)

    # Check the biographical fields.
    if "bio" not in legislator:
      error(context, "Missing 'bio' mapping.")
    else:
      check_bio(legislator["bio"], current, context)

    # Check the terms.
    if "terms" not in legislator:
      error(context, "Missing 'terms' list.")
    elif not isinstance(legislator["terms"], list):
      error(context, "'terms' has an invalid data type.")
    elif len(legislator["terms"]) == 0:
      error(context, "'terms' is empty.")
    else:
      prev_term = None
      for i, term in enumerate(legislator["terms"]):
        check_term(term, prev_term, context+":terms[{}]".format(i),
          current=(current and i==len(legislator["terms"])-1),
          current_mocs=current_mocs)
        prev_term = term

    # Check the leadership roles.
    check_leadership_roles(legislator.get("leadership_roles", []), current, context)

def check_leadership_roles(roles, current, context):
  for role in roles:
    # All of these fields must be strings.
    for key, value in role.items():
      if not isinstance(value, str):
        error(context, rtyaml.dump({ key: value }) + " has an invalid data type.")

    # Check required fields.
    if "title" not in role:
      error(context, rtyaml.dump(role) + " is missing title.")
    if role.get("chamber") not in ("house", "senate"):
      error(context, rtyaml.dump(role) + " has an invalid chamber.")
    if "start" not in role:
      error(context, rtyaml.dump(role) + " is missing start.")
    if "end" not in role and not current:
      # end is required only in the historical file
      error(context, rtyaml.dump(role) + " is missing end.")

    # Check dates.
    start = check_date(role['start'], context)
    if "end" in role:
      end = check_date(role['end'], context)
      if start and end and end < start:
        error(context, rtyaml.dump(role) + " has end before start.")

def check_id_types(legislator, seen_ids, is_legislator, context):
  for key, value in legislator["id"].items():
    # Check that the id key is one we know about.
    if key not in id_types:
      error(context, rtyaml.dump({ key: value }) + " is not a valid id.")

    # Check that the data type is correct.
    elif not isinstance(value, id_types[key]):
      error(context, rtyaml.dump({ key: value }) + " has an invalid data type.")

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
        error(context, "Missing %s id." % id_type)

def check_name(name, context, is_other_names=False):
  # Check for required keys and data types of the values.
  for key, value in name.items():
    if key in ("start", "end") and is_other_names:
      if not isinstance(value, str):
        error(context, rtyaml.dump({ key: value }) + " has an invalid data type.")
    elif key not in name_keys:
      error(context, "%s is not a valid key in name." % key)
    elif key in ("first", "last"):
      # These are required.
      if not isinstance(value, str):
        error(context, rtyaml.dump({ key: value }) + " has an invalid data type.")
    else:
      # These can be set explicitly to None, but maybe we should just remove
      # those keys then.
      if not isinstance(value, (str, type(None))):
        error(context, rtyaml.dump({ key: value }) + " has an invalid data type.")

  # If a person as a first initial only, they should also have a middle name.
  # (GovTrack relies on this to generate name strings.)
  if isinstance(name.get("first"), str) and len(name["first"]) == 2 and name["first"].endswith(".") and not name.get("middle"):
        error(context, rtyaml.dump(name) + " is missing a middle name to go with its first initial.")

def check_bio(bio, is_current_legislator, context):
  for key, value in bio.items():
    if key not in bio_keys:
      error(context, "%s is not a valid key in bio." % key)
    elif not isinstance(value, str):
      error(context, rtyaml.dump({ key: value }) + " has an invalid data type.")
  if is_current_legislator:
    # These keys are required only for current legislators.
    # We don't always have the information for historical members of Congress or presidents.
    for key in bio_keys:
      if key not in bio:
        error(context, "Missing bio->{}.".format(key))

def check_term(term, prev_term, context, current=None, current_mocs=None):
  # Check type.
  if term.get("type") not in ("rep", "sen"):
    error(context, "Term has invalid 'type'.")

  # Check date range.
  start = check_date(term.get('start'), context)
  end = check_date(term.get('end'), context)
  if start and end:
    context += "({} to {})".format(start, end)

    if end < start:
      error(context, "Term has end before start.")

    if prev_term:
      prev_end = check_date(prev_term.get("end"), context)
      if prev_end:
        if start < prev_end:
          error(context, "Term has start before previous term's end.")

    if not current and (end > now):
      error(context, "Term has an end date in the future but is a past term.")
    if current and (end < now):
      error(context, "Term has an end date in the past but is a most recent term in the current file.")

    # Get the congress number of the start and end dates of the term.
    congress_start = utils.get_congress_from_date(utils.parse_date(term["start"]), "start")
    congress_end = utils.get_congress_from_date(utils.parse_date(term["end"]), "end")
    if congress_start is None:
      raise ValueError("Invalid date:" + term["start"])
    if congress_end is None:
      raise ValueError("Invalid date:" + term["end"])

    # Check that the date range makes sense.
    if term["type"] == "sen":
      # Senate terms can't span more than 3 congresses.
      if congress_end - congress_start > 2:
        error(context, "Term date range is too long: {} to {}".format(term["start"], term["end"]))
      elif term.get("class") in (1, 2, 3): # don't crash if missing, is checked below
        # Sanity-check that the term doesn't cross a year where the senators from that class
        # would face election. Class 1 senators face election after Congress numbers 1, 4, ...
        # Class 2 senators after Congress numbers 2, 5, ... And Class 3 after Congress numbers
        # 3, 6, ... A term cannot include an ending Congress number and the subsequent Congress.
        for c in range(congress_start, congress_end):
          # Congresses 'c' and 'c+1' are in the range. If 'c' is an ending Congress for this
          # term's class, it's an error.
          if ((c - 1789) % 3) == (term["class"] - 1):
            error(context, "Term date range doesn't match senate class: {} to {}".format(term["start"], term["end"]))

    elif term["type"] == "rep" and term["state"] == "PR":
      # Puerto Rico's resident commissioners' terms can't span more than 2 congresses.
      if congress_end - congress_start > 1:
        error(context, "Term date range is too long for: {} to {}".format(term["start"], term["end"]))

    elif term["type"] == "rep":
      # House terms can't span more than 1 congress.
      if congress_end - congress_start > 0:
        error(context, "Term date range is too long: {} to {}".format(term["start"], term["end"]))

  # Check how.
  if term.get("how") not in (None, "appointment",):
    error(context, "Term has invalid 'how'.")

  # Check end-type.
  if term.get("end-type") not in (None, "special-election",):
    error(context, "Term has invalid 'end-type'.")
  if term.get("end-type") == "special-election" and term.get("how") != "appointment":
    error(context, "Term can't have an 'end-type' without being an appointed senator.")

  # Check state, district, class, state_rank.
  if term.get("state") not in utils.states:
    error(context, "Term has invalid state.")
  if term.get("type") == "rep":
    if not isinstance(term.get("district"), int):
      error(context, "Term has invalid district.")
  if term.get("type") == "sen":
    if term.get("class") not in (1, 2, 3):
      error(context, "Term has invalid class.")
    if term.get("state_rank") not in ("junior", "senior", None):
      error(context, "Term has invalid senator state_rank.")
    elif current and term.get("state_rank") is None:
      error(context, "Term is missing senator state_rank.")

  if current:
    # Check uniqueness of office for current members.

    # Check office.
    office = (term.get("type"), term.get("state"), term.get("district") if term.get("type") == "rep" else term.get("class"))
    if office in current_mocs:
      error(context, "Term duplicates an office.")
    current_mocs.add(office)

    # Check senator rank isn't duplicated.
    if term.get("type") == "sen":
      office = (term.get("state"), term.get("state_rank"))
      if office in current_mocs:
        error(context, "Term duplicates state_rank in a state.")
      current_mocs.add(office)

    # Check party of current members (historical is too difficult).
    if term.get("party") not in ("Republican", "Democrat", "Independent", "Libertarian"):
      error(context, rtyaml.dump({ "party": term.get("party") }) + " is invalid.")

    # Check caucus of Independent members -- it's optional, so warn.
    if term.get("party") == "Independent" and term.get("caucus") not in ("Republican", "Democrat"):
      print(context, rtyaml.dump({ "caucus": term.get("caucus") }) + " when party is Independent.")

    # Check website -- it's optional, so warn.
    if not term.get("url"):
      print(context, "Term is missing a website url.")

    # TODO: Check party_affiliations and office information.

def report_vacancies(current_mocs):
  for state, apportionment in state_apportionment.items():
    # If this is one of the 50 states, check that we saw two
    # senators.
    if apportionment != "T":
      senators = [m for m in current_mocs if m in [("sen", state, 1), ("sen", state, 2), ("sen", state, 3)]]
      if len(senators) != 2:
        print("Vacancy in", state, "senators.")

    # Check that we have someone in each district.
    if apportionment in ("T", 1):
      districts = [0]
    else:
      districts = range(1, apportionment+1)
    for district in districts:
      if ("rep", state, district) not in current_mocs:
        print("Vacancy in", state, "district", district, ".")

def check_executive_file(fn):
  # Open and iterate over the entries.
  with open(fn) as f:
    people = rtyaml.load(f)
  for person in people:
    # Create a string for error messages to tell us where problems are ocurring.
    context = "{} in {}".format(fn, repr(person))

    # Check the IDs.
    if "id" not in person:
      error(context, "Missing 'id' mapping.")
    else:
      # Check that the IDs are valid.
      check_id_types(person, {}, False, context)

    # Check the name.
    if "name" not in person:
      error(context, "Missing 'name' mapping.")
    else:
      check_name(person["name"], context)

    # Check the biographical fields.
    if "bio" not in person:
      error(context, "Missing 'bio' mapping.")
    else:
      check_bio(person["bio"], False, repr(person))

    # Check the terms.
    if "terms" not in person:
      error(context, "Missing 'terms' list.")
    elif not isinstance(person["terms"], list):
      error(context, "'terms' has an invalid data type.")
    elif len(person["terms"]) == 0:
      error(context, "'terms' is empty.")
    else:
      for i, term in enumerate(person["terms"]):
        check_executive_term(term, context+":term[{}]".format(i))

def check_executive_term(term, context):
  # Check type.
  if term.get("type") not in ("prez", "viceprez"):
    error(context, "Term has invalid 'type'.")

  # Check how.
  if term.get("how") not in ("election", "succession", "appointment"):
    error(context, "Term has invalid 'how'.")

  # Check date range.
  start = check_date(term.get('start'), context)
  end = check_date(term.get('end'), context)
  if start and end:
    if end < start:
      error(context, "Term has end before start.")

  if end.year > 2000:
    # Check party of current members (historical is too difficult and even recent ones incorrectly have Democratic instead of Democrat, which is inconsistent with the legislators files).
    if term.get("party") not in ("Republican", "Democrat"):
      error(context, rtyaml.dump({ "party": term.get("party") }) + " is invalid.")


def check_date(d, context):
  if not isinstance(d, str):
    error(context, str(d) + ": invalid data type")
    return None
  try:
    return utils.parse_date(d)
  except Exception as e:
    error(context, d + ": " + str(e))
    return None

def check_id_uniqueness(seen_ids):
  for (id_type, id_value), occurrences in seen_ids.items():
    if len(occurrences) > 1:
      error("", "%s %s is duplicated: %s" % (id_type, id_value,
        " ".join(legislator['id']['bioguide'] for legislator in occurrences)))

def check_district_offices():
    has_errors = validate_offices(skip_warnings=True)
    if has_errors:
        pass # error("", "District offices have errors")


if __name__ == "__main__":
  # Check the legislators files.
  seen_ids = { }
  current_mocs = set()
  check_legislators_file("legislators-current.yaml", seen_ids, current=True, current_mocs=current_mocs)
  report_vacancies(current_mocs)
  check_legislators_file("legislators-historical.yaml", seen_ids, current=False)
  check_executive_file("executive.yaml")
  check_id_uniqueness(seen_ids)
  check_district_offices()

  # Exit with exit status.
  sys.exit(0 if ok else 1)
