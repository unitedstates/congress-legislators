#!/usr/bin/env python

# gets fundamental information for every member with a bioguide ID:
# first name, nickname, middle name, last name, name suffix
# birthday

# options:
#  --cache: load from cache if present on disk (default: true)
#  --current: do *only* current legislators (default: true)
#  --historical: do *only* historical legislators (default: false)
#  --bioguide: do *only* a single legislator
#  --relatives: Get familial relationships to other members of congress past and present, when applicable

import lxml.html, StringIO
import datetime
import re, json
import utils
from collections import defaultdict
from utils import download, load_data, save_data, parse_date

def birthday_for(string):
  pattern = "born(.+?)((?:January|February|March|April|May|June|July|August|September|October|November|December),? \\d{1,2},? \\d{4})"
  match = re.search(pattern, string, re.I)
  if match:
    if len(re.findall(";", match.group(1))) <= 1:
      return match.group(2).strip()

lookup_legislator_cache = {}
diminutives = {}
def lookup_legislator(name, bioguide=None):
  import unidecode
  
  # This is a basic lookup function given the legislator's name, adapted from congress repo
  # On the first load, cache all of the legislators' terms in memory.
  # if bioguide, EXCLUDES anyone with that bioguide (useful if looking for Jr./Sr and have one already)
  global lookup_legislator_cache
  if not lookup_legislator_cache:
    lookup_legislator_cache = defaultdict(lambda: defaultdict(list))
    current = load_data("legislators-current.yaml")
    historical = load_data("legislators-historical.yaml")
    members = current + historical
    for member in members:
      if isinstance(member["name"]["last"], unicode):
        member["name"]["last"] = unidecode.unidecode(member["name"]["last"])
      lookup_legislator_cache[member["name"]["last"]][member["name"]["first"]].append({
          "bioguide": member["id"]["bioguide"],
          "birthday": member.get("bio", {}).get("birthday", ""),
          "name": member["name"]
        })

    with open("lookup.json", "w") as f:
      f.write(json.dumps(lookup_legislator_cache, indent=2))

    # get list of diminutives
    with open("diminutives.csv", "r") as f:
      for names in [x.split(",") for x in f.read().split("\r\n")]:
        diminutives[names[0].title()] = [x.title() for x in names[1:]]

  # At least one entry (John Sarbanes) errantly uses title in relationship clause
  name = name.replace("Senator ", "")

  parts = re.split(" ([A-Za-z]{2,4}\.|[IV]+$)", name)
  names = parts[0].split(" ")
  
  # parse raw name
  last_name = names[-1]
  first_name = names[0]
  middle_name = None if len(names) == 1 else names[1] 
  suffix = None if len(parts) < 2 else parts[1]
  nickname = re.findall('"(.*?)"', name)

  matches = lookup_legislator_cache[last_name][first_name]
  if bioguide:
    matches = [x for x in matches if x["bioguide"] != bioguide]
  if not len(matches):
    # try nicknames for everyone with that last name
    if len(nickname):
      for fn in lookup_legislator_cache[last_name]:
        members = lookup_legislator_cache[last_name][fn]
        for member in members:
          if member["name"].get("nickname", "") == nickname[0]:
            return member

    # try diminutives
    if first_name in diminutives:
      for fn in lookup_legislator_cache[last_name]:
        if fn in diminutives[first_name]:
          if len(lookup_legislator_cache[last_name][fn]) == 1:
            return lookup_legislator_cache[last_name][fn][0]
          else:
            matches = lookup_legislator_cache[last_name][fn]

    if not len(matches):
      print "No matches for " + name
      return []
  if len(matches) == 1:
    return matches[0]

  # if multiple people with that first name, try suffix then M.I.
  if suffix:
    for member in matches:
      if member["name"].get("suffix", "") == suffix:
        return member

  if middle_name:
    for member in matches:
      if member["name"].get("middle", "") == middle_name:
        return member
  else:
    #return first match w/o a middle name (see Frederick Frelinghuysens)
    for member in matches:
      if member["name"].get("middle", "") == "":
        return member
    
  print "Too many matches for " + name
  print matches
  return []
 
def relationships_of(bioguide_id, string):
  # relationship data is stored in a parenthetical immediately after the end of the </font> tag in the bio
  # e.g. "(son of Joseph Patrick Kennedy, II, and great-nephew of Edward Moore Kennedy and John Fitzgerald Kennedy)"
  pattern = "^\((.*?)\)"
  match = re.search(pattern, string, re.I)

  relationships = []
  
  if match and len(match.groups()) > 0:
    relationship_text = match.group(1)
    if isinstance(relationship_text, unicode):
      relationship_text = relationship_text.encode("ascii", "xmlcharrefreplace").replace("&#146;", "'").replace("&#147;", '"').replace("&#148;", '"').replace("&#225;", 'a')
      
    # since some relationships refer to multiple people--great-nephew of Edward Moore Kennedy AND John Fitzgerald Kennedy--we need a special grammar
    from nltk import tree, pos_tag, RegexpParser
    tokens = re.split("[ ,;]+|(-(?![A-Z]))", relationship_text)
    tokens = [x for x in tokens if x]
    pos = pos_tag(tokens)

    grammar = r"""
      NAME: {<NNP>+}
      NAME: {<NAME><:><NAME>}
      NAMES: { <IN><NAME>(?:<CC><NAME>)* }
      RELATIONSHIP: { <JJ|NN|RB|VB|VBD|VBN|IN|:|PRP\$>+ }
      MATCH: { <RELATIONSHIP><NAMES> }
      """
    cp = RegexpParser(grammar)   
    chunks = cp.parse(pos)

    # iterate through the Relationship/Names pairs
    for n in chunks:
      if isinstance(n, tree.Tree) and n.node == "MATCH":
        people = []
        relationship = None
        for piece in n:
          if piece.node == "RELATIONSHIP":
            relationship = " ".join([x[0] for x in piece])
          elif piece.node == "NAMES":
            for name in [x for x in piece if isinstance(x, tree.Tree)]:
              people.append(" ".join([x[0] for x in name]))
        for person in people:
          match = lookup_legislator(person, bioguide)
          relationships.append({
            "name": person.replace(" , ", ", "),
            "relation_to": relationship.replace(" - ", "-"),
            "bioguide": "" if not len(match) else match["bioguide"]
          })
  return relationships


debug = utils.flags().get('debug', False)

# default to caching
cache = utils.flags().get('cache', True)
force = not cache

# pick either current or historical
# order is important here, since current defaults to true
if utils.flags().get('historical', False):
  filename = "legislators-historical.yaml"
elif utils.flags().get('current', True):
  filename = "legislators-current.yaml"
else:
  print "No legislators selected."
  exit(0)

print "Loading %s..." % filename
legislators = load_data(filename)


# reoriented cache to access by bioguide ID
by_bioguide = { }
for m in legislators:
  if m["id"].has_key("bioguide"):
    by_bioguide[m["id"]["bioguide"]] = m

# optionally focus on one legislator

bioguide = utils.flags().get('bioguide', None)
if bioguide:
  bioguides = [bioguide]
else:
  bioguides = by_bioguide.keys()

warnings = []
missing = []
count = 0
families = [0, 0, 0]

for bioguide in bioguides:
  url = "http://bioguide.congress.gov/scripts/biodisplay.pl?index=%s" % bioguide
  cache = "legislators/bioguide/%s.html" % bioguide
  try:
    body = download(url, cache, force)
    dom = lxml.html.parse(StringIO.StringIO(body)).getroot()
  except lxml.etree.XMLSyntaxError:
    print "Error parsing: ", url
    continue

  if len(dom.cssselect("title")) == 0:
    print "[%s] No page for this bioguide!" % bioguide
    missing.append(bioguide)
    continue

  try:
    name = dom.cssselect("p font")[0]
    main = dom.cssselect("p")[0]
  except IndexError:
    print "[%s] Missing name or content!" % bioguide
    exit(0)

  name = name.text_content().strip()
  main = main.text_content().strip().replace("\n", " ").replace("\r", " ")
  main = re.sub("\s+", " ", main)

  birthday = birthday_for(main)
  if not birthday:
    print "[%s] NO BIRTHDAY :(\n\n%s" % (bioguide, main)
    warnings.append(bioguide)
    continue

  if debug:
    print "[%s] Found birthday: %s" % (bioguide, birthday)

  try:
    birthday = datetime.datetime.strptime(birthday.replace(",", ""), "%B %d %Y")
  except ValueError:
    print "[%s] BAD BIRTHDAY :(\n\n%s" % (bioguide, main)
    warnings.append(bioguide)
    continue

  birthday = "%04d-%02d-%02d" % (birthday.year, birthday.month, birthday.day)
  
  # some older legislators may not have a bio section yet
  if not by_bioguide[bioguide].has_key("bio"):
    by_bioguide[bioguide]["bio"] = {}

  by_bioguide[bioguide]["bio"]["birthday"] = birthday

  if utils.flags().get("relatives", False):
    #relationship information, if present, is in a parenthetical immediately after the name.
    #should always be present if we passed the IndexError catch above
    after_name = dom.cssselect("p font")[0].tail.strip()
    relationships = relationships_of(bioguide, after_name)
    if len(relationships):
      by_bioguide[bioguide]["family"] = relationships
      families[0] += 1
      families[1] += len(relationships)
      families[2] += len([x for x in relationships if x["bioguide"] == ""])
     
  count = count + 1


print
if warnings:
  print "Missed %d birthdays: %s" % (len(warnings), str.join(", ", warnings))

if missing:
  print "Missing a page for %d bioguides: %s" % (len(missing), str.join(", ", missing))

print "Saving data to %s..." % filename
save_data(legislators, filename)

print "Saved %d legislators to %s" % (count, filename)

if utils.flags().get("relatives", False):
  print "Found %d family members for %d of those legislators" % (families[1], families[0])
  print "Failed to find bioguide ids for %d of those family members" % families[2]

# Some testing code to help isolate and fix issued:
# f
# none = "PEARSON, Joseph, a Representative from North Carolina; born in Rowan County, N.C., in 1776; completed preparatory studies; studied law; was admitted to the bar and commenced practice in Salisbury, N.C.; member of the State house of commons; elected as a Federalist to the Eleventh, Twelfth, and Thirteenth Congresses (March 4, 1809-March 3, 1815); while in Congress fought a duel with John George Jackson, of Virginia, and on the second fire wounded his opponent in the hip; died in Salisbury, N.C., October 27, 1834."
# print "Pearson (none): %s" % birthday_for(none)

# owens = "OWENS, William, a Representative from New York; born in Brooklyn, Kings County, N.Y., January, 20, 1949; B.S., Manhattan College, Riverdale, N.Y., 1971; J.D., Fordham University, New York, N.Y., 1974; United States Air Force; lawyer, private practice; faculty, State University of New York, Plattsburgh, N.Y., 1978-1986; elected as a Democrat to the One Hundred Eleventh Congress, by special election to fill the vacancy caused by the resignation of United States Representative John McHugh, and reelected to the two succeeding Congresses (November 3, 2009-present)."
# print "Owens (January, 20, 1949): %s" % birthday_for(owens)

# shea = "SHEA-PORTER, Carol, a Representative from New Hampshire; born in New York City, New York County, N.Y., December, 1952; graduated from Oyster River High School, Durham, N.H., 1971; B.A., University of New Hampshire, Durham, N.H., 1975; M.P.A., University of New Hampshire, Durham, N.H., 1979; social worker; professor; elected as a Democrat to the One Hundred Tenth Congress and to the succeeding Congress (January 3, 2007-January 3, 2011); unsuccessful candidate for reelection to the One Hundred Twelfth Congress in 2010; elected as a Democrat to the One Hundred Thirteenth Congress (January 3, 2013-present)."
# print "Shea (none): %s" % birthday_for(shea)

# control = "PEARSON, Richmond, a Representative from North Carolina; born at Richmond Hill, Yadkin County, N.C., January 26, 1852; attended Horner's School, Oxford, N.C., and was graduated from Princeton College in 1872; studied law; was admitted to the bar in 1874; in the same year was appointed United States consul to Verviers and Liege, Belgium; resigned in 1877; member of the State house of representatives 1884-1886; elected as a Republican to the Fifty-fourth and Fifty-fifth Congresses (March 4, 1895-March 3, 1899); successfully contested the election of William T. Crawford to the Fifty-sixth Congress and served from May 10, 1900, to March 3, 1901; appointed by President Theodore Roosevelt as United States consul to Genoa, Italy, December 11, 1901, as Envoy Extraordinary and Minister Plenipotentiary to Persia in 1902, and as Minister to Greece and Montenegro in 1907; resigned from the diplomatic service in 1909; died at Richmond Hill, Asheville, N.C., September 12, 1923; interment in Riverside Cemetery."
# print "\nControl (January 26, 1852): %s" % birthday_for(control)
