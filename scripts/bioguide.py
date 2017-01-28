#!/usr/bin/env python

# gets fundamental information for every member with a bioguide ID:
# first name, nickname, middle name, last name, name suffix
# birthday

# options:
#  --cache: load from cache if present on disk (default: true)
#  --current: do *only* current legislators (default: true)
#  --historical: do *only* historical legislators (default: false)
#  --bioguide: do *only* a single legislator
#  --relationships: Get familial relationships to other members of congress past and present, when applicable

import lxml.html, io
import datetime
import re
import utils
from utils import download, load_data, save_data

def run():

  def update_birthday(bioguide, person, main):

    birthday = birthday_for(main)
    if not birthday:
      print("[%s] NO BIRTHDAY :(\n\n%s" % (bioguide, main))
      warnings.append(bioguide)
      return
    if birthday == "UNKNOWN":
      return

    try:
      birthday = datetime.datetime.strptime(birthday.replace(",", ""), "%B %d %Y")
    except ValueError:
      print("[%s] BAD BIRTHDAY :(\n\n%s" % (bioguide, main))
      warnings.append(bioguide)
      return

    birthday = "%04d-%02d-%02d" % (birthday.year, birthday.month, birthday.day)
    person.setdefault("bio", {})["birthday"] = birthday


  def birthday_for(string):
    # exceptions for not-nicely-placed semicolons
    string = string.replace("born in Cresskill, Bergen County, N. J.; April", "born April")
    string = string.replace("FOSTER, A. Lawrence, a Representative from New York; September 17, 1802;", "born September 17, 1802")
    string = string.replace("CAO, Anh (Joseph), a Representative from Louisiana; born in Ho Chi Minh City, Vietnam; March 13, 1967", "born March 13, 1967")
    string = string.replace("CRITZ, Mark S., a Representative from Pennsylvania; born in Irwin, Westmoreland County, Pa.; January 5, 1962;", "born January 5, 1962")
    string = string.replace("SCHIFF, Steven Harvey, a Representative from New Mexico; born in Chicago, Ill.; March 18, 1947", "born March 18, 1947")
    string = string.replace('KRATOVIL, Frank, M. Jr., a Representative from Maryland; born in Lanham, Prince George\u2019s County, Md.; May 29, 1968', "born May 29, 1968")

    # look for a date
    pattern = r"born [^;]*?((?:January|February|March|April|May|June|July|August|September|October|November|December),? \d{1,2},? \d{4})"
    match = re.search(pattern, string, re.I)
    if not match or not match.group(1):
      # specifically detect cases that we can't handle to avoid unnecessary warnings
      if re.search("birth dates? unknown|date of birth is unknown", string, re.I): return "UNKNOWN"
      if re.search("born [^;]*?(?:in|about|before )?(?:(?:January|February|March|April|May|June|July|August|September|October|November|December) )?\d{4}", string, re.I): return "UNKNOWN"
      return None
    return match.group(1).strip()

  def relationships_of(string):
    # relationship data is stored in a parenthetical immediately after the end of the </font> tag in the bio
    # e.g. "(son of Joseph Patrick Kennedy, II, and great-nephew of Edward Moore Kennedy and John Fitzgerald Kennedy)"
    pattern = "^\((.*?)\)"
    match = re.search(pattern, string, re.I)

    relationships = []

    if match and len(match.groups()) > 0:
      relationship_text = match.group(1).encode("ascii", "replace")

      # since some relationships refer to multiple people--great-nephew of Edward Moore Kennedy AND John Fitzgerald Kennedy--we need a special grammar
      from nltk import tree, pos_tag, RegexpParser
      tokens = re.split("[ ,;]+|-(?![0-9])", relationship_text)
      pos = pos_tag(tokens)

      grammar = r"""
        NAME: {<NNP>+}
        NAMES: { <IN><NAME>(?:<CC><NAME>)* }
        RELATIONSHIP: { <JJ|NN|RB|VB|VBD|VBN|IN|PRP\$>+ }
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
            relationships.append({ "relation": relationship, "name": person})
    return relationships

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
    print("No legislators selected.")
    exit(0)

  print("Loading %s..." % filename)
  legislators = load_data(filename)


  # reoriented cache to access by bioguide ID
  by_bioguide = { }
  for m in legislators:
    if "bioguide" in m["id"]:
      by_bioguide[m["id"]["bioguide"]] = m


  # optionally focus on one legislator

  bioguide = utils.flags().get('bioguide', None)
  if bioguide:
    bioguides = [bioguide]
  else:
    bioguides = list(by_bioguide.keys())

  warnings = []
  missing = []
  count = 0
  families = 0

  for bioguide in bioguides:
    # Download & parse the HTML of the bioguide page.
    try:
    	dom = fetch_bioguide_page(bioguide, force)
    except Exception as e:
    	print(e)
    	missing.append(bioguide)
    	continue

    # Extract the member's name and the biography paragraph (main).

    try:
      name = dom.cssselect("p font")[0]
      main = dom.cssselect("p")[0]
    except IndexError:
      print("[%s] Missing name or content!" % bioguide)
      exit(0)

    name = name.text_content().strip()
    main = main.text_content().strip().replace("\n", " ").replace("\r", " ")
    main = re.sub("\s+", " ", main)

    # Extract the member's birthday.

    update_birthday(bioguide, by_bioguide[bioguide], main)

    # Extract relationships with other Members of Congress.

    if utils.flags().get("relationships", False):
      #relationship information, if present, is in a parenthetical immediately after the name.
      #should always be present if we passed the IndexError catch above
      after_name = dom.cssselect("p font")[0].tail.strip()
      relationships = relationships_of(after_name)
      if len(relationships):
        families = families + 1
        by_bioguide[bioguide]["family"] = relationships

    count = count + 1


  print()
  if warnings:
    print("Missed %d birthdays: %s" % (len(warnings), str.join(", ", warnings)))

  if missing:
    print("Missing a page for %d bioguides: %s" % (len(missing), str.join(", ", missing)))

  print("Saving data to %s..." % filename)
  save_data(legislators, filename)

  print("Saved %d legislators to %s" % (count, filename))

  if utils.flags().get("relationships", False):
    print("Found family members for %d of those legislators" % families)

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

def fetch_bioguide_page(bioguide, force):
  url = "http://bioguide.congress.gov/scripts/biodisplay.pl?index=%s" % bioguide
  cache = "legislators/bioguide/%s.html" % bioguide
  try:
    body = download(url, cache, force)

    # Fix a problem?
    body = body.replace("&Aacute;\xc2\x81", "&Aacute;")

    # Entities like &#146; are in Windows-1252 encoding. Normally lxml
    # handles that for us, but we're also parsing HTML. The lxml.html.HTMLParser
    # doesn't support specifying an encoding, and the lxml.etree.HTMLParser doesn't
    # provide a cssselect method on element objects. So we'll just decode ourselves.
    body = utils.unescape(body, "Windows-1252")

    dom = lxml.html.parse(io.StringIO(body)).getroot()
  except lxml.etree.XMLSyntaxError:
    raise Exception("Error parsing: " + url)

  # Sanity check.

  if len(dom.cssselect("title")) == 0:
    raise Exception("No page for bioguide %s!" % bioguide)

  return dom

if __name__ == '__main__':
  run()
