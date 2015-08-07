#!/usr/bin/env python
#
# This module builds a modgrammar context free grammar & parser
# for the text of biographical entries for Members of Congress
# at http://bioguide.congress.gov.
#
###############################################################

import datetime, copy
from modgrammar import *

# Utilities....

def grammar_from_list(literals, titlecase_too=True):
  # Turns a list of strings into a Grammar that accepts
  # any of those strings, i.e.:
  #  grammar_from_list(["ABC", "xyz"])
  #    == LITERAL("ABC") | LITERAL("XYZ")
  g = None
  for w in literals:
    l = LITERAL(w)
    if titlecase_too:
      l |= LITERAL(w.title())
    if g is None:
      g = l
    else:
      g |= l
  return g

MULTIWORD = WORD('-A-Za-z0-9’(),." ', greedy=True)
MULTIWORD_NOTGREEDY = WORD('-A-Za-z0-9’(),." ', greedy=False)

################################################################
# Build a grammar of cardinal (one, two, three, ...) and ordinal
# (first, second, third, ...) numbers, which we need for parsing
# strings like "One-hudred thirteen Congress".
################################################################

cardinal_numbers_1 = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine',
  'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen', 'nineteen']
cardinal_numbers_10 = ["twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]

ordinal_numbers_1 = ["first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth", "eleventh", "twelf", "thirteenth", "fourteenth", "fifteenth", "sixteenth", "seventeenth", "eighteenth", "nineteenth"]
ordinal_numbers_10 = ["twentieth", "thirtieth", "fortieth", "fiftieth", "sixtieth", "seventieth", "eightieth", "ninetieth", "one hundredth"]

class CardinalNumber(Grammar):
  # Matches a cardinal number from "zero" to "nineteen".
  grammar = grammar_from_list(cardinal_numbers_1)
  def value(self):
    # Turn the string into an integer by lookup into the cardinal_numbers_1 array.
    return cardinal_numbers_1.index(self.string.lower())

class OrdinalNumber1(Grammar):
  # Matches an ordinal number from "first" to "nineteenth" and two-
  # word ordinal numbers like "twenty-first".
  grammar = (OPTIONAL(G(grammar_from_list(cardinal_numbers_10), LITERAL('-'))), grammar_from_list(ordinal_numbers_1))
  def value(self):
    # Turn the string into an integer by lookup into the cardinal_numbers_10 array.
    x = ordinal_numbers_1.index(self[1].string.lower()) + 1
    if self[0]:
      x += (cardinal_numbers_10.index(self[0][0].string.lower()) + 2) * 10
    return x

class OrdinalNumber2(Grammar):
  # Matches an ordinal number that is a multiple of ten from "twentieth"
  # to "one hundredth".
  grammar = grammar_from_list(ordinal_numbers_10)
  def value(self):
    # Turn the string into an integer by lookup into the ordinal_numbers_10 array.
    return (ordinal_numbers_10.index(self[0].string.lower()) + 2) * 10

class OrdinalNumber3(Grammar):
  # Matches an ordinal number above "one hundredth".
  grammar = CardinalNumber, LITERAL(' hundred ') | LITERAL(' Hundred '), OrdinalNumber1 | OrdinalNumber2
  def value(self):
    # Turn the string into an integer.
    return 100 * self[0].value() + self[2].value()

class OrdinalNumber(Grammar):
  # Matches any ordinal number (via the grammars above).
  grammar = OrdinalNumber1 | OrdinalNumber2 | OrdinalNumber3
  def value(self):
    # Turn the string into a number by calling the value() method of
    # whichever grammar rule matched.
    return self[0].value()

################################################################
# Build a grammar of dates.
################################################################

month_names = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']

class Date(Grammar):
  # Matches a date, or just a year alone. So matches:
  # e.g. "Janary 1, 1950" or just "1950".
  grammar = OPTIONAL(grammar_from_list(month_names), LITERAL(' '), WORD('0-9', min=1, max=2), LITERAL(', ')), G(L('1') | L('2'), WORD('0-9', min=3, max=3))
  def value(self):
    # Return the parsed date.
    if self[0]:
      # If it's a full date, return a datetime.date instance.
      return datetime.date(int(self[1].string), month_names.index(self[0][0].string)+1, int(self[0][2].string))
    else:
      # If it's a year alone, return the integer for the year.
      return int(self[1].string)

class DateOptRange(Grammar):
  # Match a date or a date range (e.g. "January 1, 1950-January 10, 1950").
  grammar = Date, OPTIONAL(LITERAL('-') | LITERAL('–'), Date | L('present'))
  def value(self):
    # Return the parsed date, or if it's a range then a dict with
    # 'start' and 'end' keys.
    if self[1] is None:
      return self[0].value()
    else:
      return { "start": self[0].value(), "end": self[1][1].value() if isinstance(self[1][1], Date) else "present" }

################################################################
# Biographies begin with some parenthetical information about
# the person's name and relations to other Members of Congress,
# and a summary of the person's roles in Congress.
################################################################

class FamilyInfo(Grammar):
  # Match relationships to other Members of Congress:
  #  e.g. "(grand-step-daughter-in-law of [name])"
  grammar = (
    ZERO_OR_MORE(grammar_from_list(['grand-', 'grand', 'great, ', 'great ', 'great-', 'great', 'half ', 'half-', 'second ', 'step-', 'step'], titlecase_too=False)),
    grammar_from_list(['relative', 'brother', 'cousin', 'daughter', 'father', 'husband', 'mother', 'nephew', 'niece', 'sister', 'son', 'uncle', 'wife', 'nephew and adopted son'], titlecase_too=False),
    OPTIONAL(grammar_from_list(['-in-law'], titlecase_too=False)),
    L(' of '),
    LIST_OF(ANY_EXCEPT(';[]', greedy=False), sep=L(', ') | L(' and ') | L(', and '), greedy=False),
    OPTIONAL(G(L(' ['), Date, L('-'), Date, L(']')))
    )
  def info(self):
    # Returns the relation and the name of the other person as a dict.
    ret = {
      "relation":  self[0].string + self[1].string + (self[2].string if self[2] else ""),
      "to": { "name": self[4].string },
      }
    if self[5]:
      ret["to"]["born"] = self[5][1].value()
      ret["to"]["died"] = self[5][3].value()
    return ret

class NameInfo(Grammar):
  # Match some other name information in the initial parenthesis, e.g.
  #   e.g. "(elected under the name [name])"
  grammar = (
    grammar_from_list(["elected under the name", "served under the name of", "formerly", "later", "subsequently", "original name,", "after election married", "fomerly married to", "formerly married to"], titlecase_too=False),
    L(" "),
    WORD('-A-Za-z0-9’,. '), # no parenthesis or semicolon so we can be greedy
    )
  def info(self):
    return {
      "type":  self[0].string,
      "name": self[2].string
      }

class ParentheticalInfo(Grammar):
  # Match the parenthetical information at the start of a biography,
  # which is a list of FamilyInfo and NameInfo phrases.
  grammar = L("("), LIST_OF(FamilyInfo | NameInfo, sep=L('; ') | L(', ') | L(' and ') | L(', and ')), L("), ")
  def info(self):
    # Returns the parsed information by calling the info() methods
    # of the parsed phrases.
    return {
        "family-relations": [x.info() for x in self[1] if isinstance(x, FamilyInfo)],
        "name-info": [x.info() for x in self[1] if isinstance(x, NameInfo)],
      }

state_to_abbr = { "Alabama": "AL", "Alaska": "AK", "American Samoa": "AS", "Arizona": "AZ", "Arkansas": "AR", "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Dakota": "DK", "Delaware": "DE", "the District of Columbia": "DC", "Florida": "FL", "Georgia": "GA", "Guam": "GU", "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY", "North Carolina": "NC", "North Dakota": "ND", "Northern Mariana Islands": "MP", "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA", "Philippines Territory/Commonwealth": "PI", "Puerto Rico": "PR", "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD", "Tennessee": "TN", "Orleans": "OL", "Texas": "TX", "Utah": "UT", "Vermont": "VT", "the Virgin Islands": "VI", "Virginia": "VA", "Washington": "WA", "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY" }

class StateName(Grammar):
  # Matches any state name, including 'the Territory of ' + various state names
  # for the period before they were states.
  grammar = (
    OPTIONAL(L("the Territory of ")),
    grammar_from_list(state_to_abbr.keys())
    )
  def value(self):
    return state_to_abbr[self[1].string]

class CongressRole(Grammar):
  # Matches e.g. "a Representative and a Senator from New York".
  grammar = (LIST_OF(
        GRAMMAR(
          L("a "), 
          L("Representative") | L("Senator") | L("Resident Commissioner") | L('Delegate'),
          name="type"),
        sep=L(", ") | L(" and ") | L(", and ")),
         L(" from "),
         StateName)
  def info(self):
    # Returns the parsed information. Since there may be multiple
    # roles that share a state name, break them apart into role-state
    # pairs and return a dict.
    return [{
      "type": x[1].string,
      "state": self[2].value(),
    } for x in self[0] if x.grammar_name == "type"]

class VPRole(Grammar):
  # Matches "Vice President of the United States".
  grammar = L("Vice President of the United States")
  def info(self):
    return [{ "type": self.string }]

class PresidentRole(Grammar):
  # Matches e.g. "5th President of the United States".
  grammar = WORD("0-9"), WORD("a-z"), L(" President of the United States")
  def info(self):
    return [{
      "type": self[2].string.strip(),
      "ordinal": int(self[0].string),
    }]

class RoleSummaryInfo(Grammar):
  # Match the full role summary information at the start of a biography
  # entry, which is a list of CongressRoles or vice-president/president
  # roles. 
  grammar = LIST_OF(CongressRole | VPRole | PresidentRole, sep=' and ')
  def info(self):
    # Returns the full list of roles by concatenating all of the
    # roles returned by the info() methods of the matched grammars.
    return sum([x.info() for x in self[0] if isinstance(x, (CongressRole, VPRole, PresidentRole))], [])

################################################################
# Grammars for "born in", "died on", and the lines about degrees
# held parts of the biography.
################################################################

class BornIn(Grammar):
  # Match "born [birthname] in/near [city], [date]".
  grammar = (LITERAL("born "), OPTIONAL(WORD('A-Za-z,. ', greedy=False), L(" ")), L("in ") | L("near ") | L("at "), WORD('A-Za-z,. ', greedy=False), LITERAL(', ') | LITERAL(', in '), Date)
  def info(self):
    # Returns a dict with the parsed information.
    ret = { "born": {
      "location": self[3].string,
      "date": self[5].value(),
    } }
    if self[1]:
      ret["birth-name"] = self[1][0].string
    return ret

class Died1(Grammar):
  # Match "died on [date], in [city]"
  grammar = (L("died "), OPTIONAL(L("on ")), Date, OPTIONAL(L(', in '), MULTIWORD))
  def info(self):
    # Returns a dict with the parsed information.
    return { "died": {
      "location": self[3][1].string if self[3] else None,
      "date": self[2].value()
      } }

class Died2(Grammar):
  # Match "died in [city] on [date]"
  grammar = (L("died in "), MULTIWORD_NOTGREEDY, OPTIONAL(L(" on ") | L(", "), Date))
  def info(self):
    # Returns a dict with the parsed information.
    return { "died": {
      "location": self[1].string if self[1] else None,
      "date": self[2][1].value() if self[2] else None,
      } }

class Died(Grammar):
  # Match either of the forms of the death sentence.
  grammar = Died1 | Died2
  def info(self):
    # Returns a dict with the parsed information by calling
    # the info() method of whichever grammar matched.
    return self[0].info()

class Degree(Grammar):
  grammar = grammar_from_list(['LL.B.', 'LL.D.', 'J.D.', 'B.A.', 'M.A.', 'Ph.D.', 'D.V.M.', 'M.D.']), LITERAL(', '), MULTIWORD
  def multi_info(self): return ("degrees", { "degree": self[0].string, "institution": self[2].string })

################################################################
# Grammars for parsing the really important part of this: the
# parts describing when and how a person was elected.
################################################################

class ElectedFromState(Grammar):
  # Matches "from [state].
  grammar = L('from '), StateName
  def info(self):
    return { "state": self[1].value() }

class ToFillTheVacancy(Grammar):
  # Matches "to fill the vacancy [in the term ending [date]] caused by the death of....".
  grammar = (
    OPTIONAL(L('by special election ') | L('in a special election ')),
    LITERAL('to fill the vacancy '),
    OPTIONAL(LITERAL('in the term ending '), Date, LITERAL(', ')),
    LITERAL('caused by '),
    MULTIWORD_NOTGREEDY
    )
  def info(self):
    return { "fill-vacancy": {
      "term-ending": self[2][1].value() if self[2] else None,
      "reason": self[4].string } }

class DidNotAssumeOffice(Grammar):
  grammar = L('but did not assume office until '), Date
  def info(self):
    return { "did-not-assume-office-until": self[1].value() }

class ReelectedSucceedingCongresses(Grammar):
  # Matches "relected to the seven succeeding Congresses", which is
  # used for people elected to consecutive House terms.
  grammar = OPTIONAL(LITERAL("reelected ")), LITERAL("to the "), CardinalNumber, LITERAL(" succeeding Congresses")
  def value(self):
    return self[2].value()

class ReelectedInYear(Grammar):
  # Matches "relected in [year], [year], ...", which is
  # used for people elected to consecutive Senate terms.
  grammar = LITERAL("reelected in "), LIST_OF(Date, sep=L(', ') | L(' and ') | L(', and '))
  def value(self):
    return [x.value() for x in self[1] if isinstance(x, Date)]

Party = grammar_from_list(['Adams', 'Adams Republican', 'Adams-Clay Federalist', 'Adams-Clay Republican', 'Alliance', 'American', 'American (Know-Nothing)', 'American Laborite', 'American Party', 'Anti Jacksonian', 'Anti-Administration', 'Anti-Democrat', 'Anti-Jacksonian', 'Anti-Lecompton Democrat', 'Anti-Masonic', 'Anti-Monopolist', 'Anti-administration', 'Coalitionist', 'Conservative', 'Conservative Republican', 'Constitutional Unionist', 'Crawford Federalist', 'Crawford Republican', 'Crawford Republicans', 'Democrat', 'Democrat Farmer Labor', 'Democrat-Farm Labor', 'Democrat-Liberal', 'Democrat/Independent', 'Democrat/Jacksonian', 'Democrat/Republican', 'Democrat;Republican', 'DemocratI', 'Democratic', 'Democratic Republican', 'Democratic and Union Labor', 'Farmer Laborite', 'Federalist', 'Free Silver', 'Free Soil', 'Free Soilier', 'Greenbacker', 'Home Rule', 'Independence Party (Minnesota)', 'Independent', 'Independent Democrat', 'Independent Republican', 'Independent Whig', 'Independent/Democrat', 'Independent/Republican', 'Jackson', 'Jackson  Democrat', 'Jackson Democrat', 'Jackson Federalist', 'Jackson Republican', 'Jacksonian', 'Jacksonian Republican', 'Labor', 'Law and Order', 'Liberal', 'Liberal Republican', 'Liberty', 'NA', 'National', 'Nationalist', 'New Progressive', 'Nonpartisan', 'Nullifier', 'Opposition', 'Opposition Party', 'Oppositionist Party', 'PARTY', 'Popular Democrat', 'Populist', 'Pro-Administration', 'Pro-administration', 'Progressive', 'Progressive Republican', 'Prohibitionist', 'Readjuster', 'Representative', 'Republican', 'Republican\t', 'Republican-Conservative', 'Republican/Democrat', 'Republican; Independent', 'RepublicanCap', 'Silver', 'Silver Republican', 'Socialist', 'State Rights Democrat', 'States Rights', 'Unconditional Unionist', 'Union', 'Union Labor', 'Union Republican', 'Unionist', 'Unknown', 'Van Buren Democrat', 'Whig'])

class BecomingParty(Grammar):
  # Matches "relected in [year], [year], ...", which is
  # used for people elected to consecutive Senate terms.
  grammar = LITERAL("becoming a "), Party, LITERAL(" in "), Date
  def info(self):
    return { "changed-party": { "party": self[1].string, "date": self[3].value() } }

class ElectionDetail(Grammar):
  # Various election details.
  grammar = ElectedFromState | ReelectedSucceedingCongresses | ReelectedInYear | ToFillTheVacancy \
    | DidNotAssumeOffice | BecomingParty
  grammar_collapse = True

class HouseElection1(Grammar):
  # Matches "to the Fiftieth Congress", which is used when a person
  # is elected to the House for either one or three or more consecutive
  # terms.
  grammar = (
    LITERAL('to the '),
    OPTIONAL(LITERAL('U.S. House of Representatives for the ')),
    OrdinalNumber,
    OPTIONAL(LITERAL(' Congress')), # missing when grouped with "and relected to the X succeeding Congresses"
    )
  def info(self):
    return {
      "type": "house",
      "congresses": [self[2].value()],
    }

class HouseElection2(Grammar):
  # Matches "to the Fiftieth and Fifty-first Congresses".
  grammar = (
    LITERAL('to the '),
    LIST_OF(OrdinalNumber, sep=L(', ') | L(' and ') | L(', and ')),
    LITERAL(' Congresses'),
    )
  def info(self):
    return {
      "type": "house",
      "congresses": [x.value() for x in self[1] if isinstance(x, OrdinalNumber)],
    }

class SenateElection(Grammar):
  # Matches "to the United States Senate [in 1990]".
  grammar = (
    L('to the United States Senate'),
    OPTIONAL(L(' in ') | L(', '), Date)
    )
  def info(self):
    ret = {
      "type": "senate",
    }
    if self[1]:
      ret["date"] = self[1][1].value()
    return ret

class Election(Grammar):
  # Matches "elected on [date] as a [party name] ..... [election details".
  grammar = (
    LITERAL('elected ') | LITERAL('reelected ') | LITERAL('successfully contested ') | LITERAL('appointed ') | LITERAL('appointed and subsequently elected '),
    OPTIONAL(LITERAL('on ') | LITERAL('in '), Date, LITERAL(', ') | LITERAL(' ')),
    OPTIONAL(LITERAL('as a '), Party, LITERAL(' ')),
    OPTIONAL(LITERAL('(later '), REPEAT(ANY), L(') ')),
    OPTIONAL(G('the election of ', MULTIWORD_NOTGREEDY)),
    HouseElection1 | HouseElection2 | SenateElection,
    ZERO_OR_MORE(G(LITERAL(', ') | LITERAL(', and ') | LITERAL(' and ') | LITERAL(' '),
        ElectionDetail)),
    )
  def info(self):
    ret = []

    # Election info.
    el = self[5].info()
    el.update({
      "party": self[2][1].string if self[2] else None,
      "how": self[0].string.strip(),
    })
    if self[1]:
      el["date"] = self[1][1].value()
    if self[3]:
      el["party-later"] = self[3][1].string
    if self[4]:
      el["contested"] = self[4].string

    # Multiple House elections are specified at once.
    if el.get("congresses"):
      for c in el["congresses"]:
        el2 = dict(el) # clone
        del el2["congresses"]
        el2["congress"] = c
        ret.append(el2)
    else:
      ret.append(el)

    # Reelections.
    for item in self[6]:
      item = item[1]
      if isinstance(item, ReelectedSucceedingCongresses):
        for x in range(1, 1+item.value()):
          el2 = {
            "how": "reelected",
            "type": el["type"],
            "congress": el["congresses"][0] + x,
          }
          ret.append(el2)
      elif isinstance(item, ReelectedInYear):
        for x in item.value():
          el2 = {
            "how": "reelected",
            "type": el["type"],
            "date": x,
          }
          ret.append(el2)
      else:
        # Update the first election info.
        ret[0].update(item.info())

    return ret

class ElectionsDateRange1(Grammar):
  # Matches "([date]-[date])".
  grammar = LITERAL(' ('), DateOptRange, LITERAL(')')
  def value(self):
    return self[1].value()

class ElectionsDateRange2(Grammar):
  # Matches ", and served [ from [date] ] to [date] / until his/her resignation on [date]"
  grammar = (
    OPTIONAL(','),
    OPTIONAL(
      LITERAL(' and served from ') | LITERAL('; served from '),
      Date,
      OPTIONAL(LITERAL(',')),
    ),
    OPTIONAL(
      LITERAL(' to ') | LITERAL(' until ') | LITERAL(' until her resignation on ') | LITERAL(' until his resignation on '),
      Date,
      OPTIONAL(LITERAL(', when he resigned'), MULTIWORD_NOTGREEDY)
    ),
    OPTIONAL(LITERAL(' until his death')),
    )
  def value(self):
    ret = {
      "start": self[1][1].value() if self[1] else None,
      "end": self[2][1].value() if self[2] else None,
      }
    if self[2] and "resignation" in self[2].string:
      ret["end-reason"] = "resignation"
    elif self[2] and self[2][2]:
      ret["end-reason"] = "resignation"
    elif self[3]:
      ret["end-reason"] = "death"
    return ret


class Elected(Grammar):
  # Main grammar for matching an "elected ..." part of the biographical
  # entry. This phrase starts with "elected" and ends with a date range.
  # Within the date range there may be multiple elections.
  grammar = (
    OPTIONAL(
      GRAMMAR(L("upon the readmission of the State of "), StateName, OPTIONAL(L(" to repreesntation")), L(" was "))
      | GRAMMAR(L("upon the admission of "), StateName, L(" as a State into the Union, was "))
      ),
    LIST_OF(Election, sep=LITERAL(" and ") | LITERAL('; ')),
    ElectionsDateRange1 | ElectionsDateRange2,
    OPTIONAL(ElectionsDateRange1)
    )
  def multi_info(self):
    ret = {
      "elections": sum([e.info() for e in self[1] if isinstance(e, Election)], []),
      "dates": self[2].value(),
    }
    if self[3]:
      # Sometimes both types of date ranges are provided, e.g.:
      # "until his resignation on February 28, 2010 (January 3, 1991-February 28, 2010)"
      # In that case, replace values where they are redundant.
      ret['dates'].update(self[3].value())
    return ("elected", ret)

################################################################
# Fall-back grammar for parsing all other activity lines.
################################################################

class Activity(Grammar):
  grammar = (
    REPEAT(ANY, greedy=False),
    OPTIONAL(LITERAL(', ') | LITERAL(' in ') | LITERAL(' '), DateOptRange)
    )
  def multi_info(self):
    ret = {
      "text": self[0].string,
    }
    if self[1]:
      ret["date"] = self[1][1].value()
    return ("activities", ret)

################################################################
# Match any single phrase in the biography separated by
# semicolons.
################################################################

class BiographyEntry(Grammar):
  # Activity goes last because it catches anything that isn't
  # picked up by one of the other grammars. This works because
  # the grammars are left-to-right greedy.
  grammar = BornIn | Died | Degree | Elected | Activity
  grammar_collapse = True

################################################################
# Match a whole biography.
################################################################

class Biography(Grammar):
  grammar = LIST_OF(BiographyEntry, sep='; ')
  def info(self):
    info = { }
    for r in self[0]:
      if hasattr(r, 'info'):
        info.update(r.info())
      elif hasattr(r, 'multi_info'):
        key, value = r.multi_info()
        info.setdefault(key, []).append(value)
    return info

################################################################
# Main function for parsing a bioguide entry.
################################################################

parser = Biography.parser()

def parse_bioguide_entry(name, biography):
  # strip the name from the biography
  biography = biography[len(name)+1:].strip()

  # The parser is super slow when we make it complex. So
  # we handle the initial parts of the biography in pieces.
  info = { }
  if biography.startswith("("):
    # There is some parenthesized content first. Parse
    # it and strip it out.
    try:
      r = ParentheticalInfo.parser().parse_text(biography)
    except ParseError as e:
      return { "_parse_error": str(e) }
    biography = biography[len(r.string):]
    info.update(r.info())

  # The next part is a summary of the roles this person held.
  # Parse that and then strip it off.
  try:
    r = RoleSummaryInfo.parser().parse_text(biography)
    info['roles'] = r.info()
    biography = biography[len(r.string):]
  except ParseError as e:
    return { "_parse_error": str(e) }

  # The rest of the biography is a ;-delimited list of biography pieces.
  biography = biography.rstrip('.') # biography always ends in a period
  try:
    r = parser.parse_text(biography, reset=True, matchtype='complete', eof=True)
  except ParseError as e:
    return { "_parse_error": str(e) }
  info.update(r.info())

  for r in info.get('elected', []):
    if isinstance(r['dates'], dict) and not r['dates']['end'] and r['dates'].get('end-reason') == 'death' and info.get('died'):
      r['dates']['end'] = copy.deepcopy(info['died']['date']) # cloning the date prevents wierd YAML object references in output


  return info
