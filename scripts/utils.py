# Helpful functions for finding data about members and committees

CURRENT_CONGRESS = 115
states = {
        'AK': 'Alaska',
        'AL': 'Alabama',
        'AR': 'Arkansas',
        'AS': 'American Samoa',
        'AZ': 'Arizona',
        'CA': 'California',
        'CO': 'Colorado',
        'CT': 'Connecticut',
        'DC': 'District of Columbia',
        'DE': 'Delaware',
        'FL': 'Florida',
        'GA': 'Georgia',
        'GU': 'Guam',
        'HI': 'Hawaii',
        'IA': 'Iowa',
        'ID': 'Idaho',
        'IL': 'Illinois',
        'IN': 'Indiana',
        'KS': 'Kansas',
        'KY': 'Kentucky',
        'LA': 'Louisiana',
        'MA': 'Massachusetts',
        'MD': 'Maryland',
        'ME': 'Maine',
        'MI': 'Michigan',
        'MN': 'Minnesota',
        'MO': 'Missouri',
        'MP': 'Northern Mariana Islands',
        'MS': 'Mississippi',
        'MT': 'Montana',
        'NA': 'National',
        'NC': 'North Carolina',
        'ND': 'North Dakota',
        'NE': 'Nebraska',
        'NH': 'New Hampshire',
        'NJ': 'New Jersey',
        'NM': 'New Mexico',
        'NV': 'Nevada',
        'NY': 'New York',
        'OH': 'Ohio',
        'OK': 'Oklahoma',
        'OR': 'Oregon',
        'PA': 'Pennsylvania',
        'PR': 'Puerto Rico',
        'RI': 'Rhode Island',
        'SC': 'South Carolina',
        'SD': 'South Dakota',
        'TN': 'Tennessee',
        'TX': 'Texas',
        'UT': 'Utah',
        'VA': 'Virginia',
        'VI': 'Virgin Islands',
        'VT': 'Vermont',
        'WA': 'Washington',
        'WI': 'Wisconsin',
        'WV': 'West Virginia',
        'WY': 'Wyoming',
        'OL': 'Orleans',
        'DK': 'Dakota',
        'PI': 'Philippine Islands'
}


import urllib.request, urllib.error, urllib.parse
import os, errno, sys, traceback
import re, html.entities
import pprint
import rtyaml
from datetime import datetime, date
import time
import json

import lxml.html # for meta redirect parsing
import yaml

import smtplib
import email.utils
from email.mime.text import MIMEText


# read in an opt-in config file for supplying email settings
# returns None if it's not there, and this should always be handled gracefully
path = "email/config.yml"
if os.path.exists(path):
  email_settings = yaml.load(open(path, 'r')).get('email', None)
else:
  email_settings = None


def congress_from_legislative_year(year):
  return ((year + 1) / 2) - 894

def legislative_year(date=None):
  if not date:
    date = datetime.now()

  if date.month == 1:
    if date.day == 1 or date.day == 2:
      return date.year - 1
    elif date.day == 3:
        if isinstance(date,datetime):
          if date.hour < 12:
            return date.year -1
          else:
            return date.year
        else:
          return date.year
    else:
      return date.year
  else:
    return date.year

def congress_start_end_dates(congress):
  # Get the start date and end date of the given Congress (i.g. 1 for the 1st Congress).
  # Sadly, the date of the end of one Congress is identical with the date of the start
  # of the next because the switchover time is at noon (at least since 1935).
  # Also see get_congress_from_date.
  start_year = 1789 + (congress-1)*2
  end_year = start_year + 2
  if congress < 73:
    # The 1st Congress met on March 4, 1789, per an act of the Continental
    # Congress adpoted Sept 13, 1788. The Constitutional term period would
    # end two years later, of course. Looking at actual adjournment dates,
    # it seems that Congress believed its term ended on March 3rd's.
    if congress != 69:
      return (date(start_year, 3, 4), date(end_year, 3, 3))
    else:
      # But the 69th Congress (and only that Congress) adjourned on a March 4,
      # which means that they must have viewed their Constitutional term as
      # expiring at the actual time of day that the first Congress began?
      # Since we use March 4 as the term end dates for the 69th Congress in our
      # data, we'll use that as the end date for the 69th Congress only.
      return (date(start_year, 3, 4), date(end_year, 3, 4))
  elif congress == 73:
    # The end of the 73rd Congress was changed by the 20th Amendment. So
    # it began on a March 4 but ended on the January 3rd (at noon) that
    # preceded the usual March 3 (1935). (Congress adjourned in 1934 anyway.)
    return (date(start_year, 3, 4), date(end_year, 1, 3))
  else:
    # Starting with the 74th Congress, Congresses begin and end on January
    # 3rds at noon.
    return (date(start_year, 1, 3), date(end_year, 1, 3))

def get_congress_from_date(d, range_type=None):
  # This is the inverse of congress_start_end_dates.
  #
  # Return the Congress number that the date 'd' occurs in by first computing
  # the 'legislative year' it occurs in, and then using some simple arithmetic
  # counting back to 1789 (the first legislative year) and dividing by two
  # (since Congresses are two years).
  #
  # Since Congresses start and end on the same date at noon (at least since
  # 1935, but we treat it similarly for prior years), those dates are ambiguous.
  # The caller passes range_type='start' to exclude the possibility that
  # if the date is on a transition date that it is in the subsequent Congress,
  # and vice versa for range_type='end'.
  if (d.year % 2) == 0:
    # Even years occur entirely within a Congress.
    y = d.year
  else:
    # In odd-numbered years, the period before the transition date, and if
    # range_type == 'end' the transition date itself, is assigned to the
    # previous legislative year

    # Get the transition date of this year.
    if d.year < 1935:
      # Through 1933, the transition date was March 4. Although most
      # Congresses adjourned on March 3 or earlier probably to not
      # have to deal with the question of what time the first session
      # began.
      td = date(d.year, 3, 4)
    else:
      # Since 1935, the transition date is Jan 3.
      td = date(d.year, 1, 3)

    # Check if d is before, after, or on the transition date.
    if d < td:
      y = d.year - 1
    elif d > td:
      y = d.year
    else:
      if range_type == "end":
      	# Assign this date to the previous Congress.
        y = d.year - 1
      elif range_type == "start":
      	# Assign this date to the next Congress.
        y = d.year
      else:
        raise ValueError("Date {} is ambiguous; must pass range_type='start' or 'end'.".format(d))

  # Now do some simple integer math to compute the Congress number.
  return ((y + 1) // 2) - 894

def parse_date(date):
  return datetime.strptime(date, "%Y-%m-%d").date()

def log(object):
  if isinstance(object, str):
    print(object)
  else:
    pprint(object)

def uniq(seq):
  seen = set()
  seen_add = seen.add
  return [ x for x in seq if x not in seen and not seen_add(x)]

def args():
  args = []
  for token in sys.argv[1:]:
    if not token.startswith("--"):
      args.append(token)
  return args

def flags():
  options = {}
  for token in sys.argv[1:]:
    if token.startswith("--"):

      if "=" in token:
        key, value = token.split('=')
      else:
        key, value = token, True

      key = key.split("--")[1]
      if value == 'True': value = True
      elif value == 'False': value = False
      options[key.lower()] = value
  return options

##### Data management

def data_dir():
  return ".."

def load_data(path):
  return yaml_load(os.path.join(data_dir(), path))

def save_data(data, path):
  yaml_dump(data, os.path.join(data_dir(), path))
  write(
		json.dumps(data, default=format_datetime),
		"../alternate_formats/%s" %path.replace(".yaml", ".json"))

##### Downloading

import scrapelib
scraper = scrapelib.Scraper(requests_per_minute=60, retry_attempts=3)
scraper.user_agent = "the @unitedstates project (https://github.com/unitedstates/congress-legislators)"

def cache_dir():
  return "cache"

def download(url, destination=None, force=False, options=None):
  if not destination and not force:
    raise TypeError("destination must not be None if force is False.")

  if not options:
    options = {}

  # get the path to cache the file, or None if destination is None
  cache = os.path.join(cache_dir(), destination) if destination else None

  if not force and os.path.exists(cache):
    if options.get('debug', False):
      log("Cached: (%s, %s)" % (cache, url))

    with open(cache, 'r') as f:
      body = f.read()
  else:
    try:
      if options.get('debug', False):
        log("Downloading: %s" % url)

      if options.get('urllib', False):
        response = urllib.request.urlopen(url)
        body = response.read().decode("utf-8") # guessing encoding
      else:
        response = scraper.urlopen(url)
        body = str(response) # ensure is unicode not bytes
    except scrapelib.HTTPError:
      log("Error downloading %s" % url)
      return None

    # don't allow 0-byte files
    if (not body) or (not body.strip()):
      return None

    # the downloader can optionally parse the body as HTML
    # and look for meta redirects. a bit expensive, so opt-in.
    if options.get('check_redirects', False):
      try:
        html_tree = lxml.html.fromstring(body)
      except ValueError:
        log("Error parsing source from url {0}".format(url))
        return None

      meta = html_tree.xpath("//meta[translate(@http-equiv, 'REFSH', 'refsh') = 'refresh']/@content")
      if meta:
        attr = meta[0]
        wait, text = attr.split(";")
        if text.lower().startswith("url="):

          new_url = text[4:]
          if not new_url.startswith(url): #dont print if a local redirect
            print("Found redirect for {}, downloading {} instead..".format(url, new_url))

          options.pop('check_redirects')
          body = download(new_url, None, True, options)

    # cache content to disk
    if cache: write(body, cache)


  return body

from pytz import timezone
eastern_time_zone = timezone('US/Eastern')
def format_datetime(obj):
  if isinstance(obj, datetime):
    return eastern_time_zone.localize(obj.replace(microsecond=0)).isoformat()
  elif isinstance(obj, str):
    return obj
  else:
    return None

def write(content, destination):
  # content must be a str instance (not bytes), will be written in utf-8 per open()'s default
  mkdir_p(os.path.dirname(destination))
  f = open(destination, 'w')
  f.write(content)
  f.close()

# mkdir -p in python, from:
# http://stackoverflow.com/questions/600268/mkdir-p-functionality-in-python
def mkdir_p(path):
  try:
    os.makedirs(path)
  except OSError as exc: # Python >2.5
    if exc.errno == errno.EEXIST:
      pass
    else:
      raise

def format_exception(exception):
  exc_type, exc_value, exc_traceback = sys.exc_info()
  return "\n".join(traceback.format_exception(exc_type, exc_value, exc_traceback))

# taken from http://effbot.org/zone/re-sub.htm#unescape-html
def unescape(text, encoding=None):

  def remove_unicode_control(str):
    remove_re = re.compile('[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]')
    return remove_re.sub('', str)

  def fixup(m):
    text = m.group(0)
    if text[:2] == "&#":
      # character reference
      if encoding == None:
        try:
          if text[:3] == "&#x":
            return chr(int(text[3:-1], 16))
          else:
            return chr(int(text[2:-1]))
        except ValueError:
          pass
      else:
        try:
          if text[:3] == "&#x":
            return bytes([int(text[3:-1], 16)]).decode(encoding)
          else:
            return bytes([int(text[2:-1])]).decode(encoding)
        except ValueError:
          pass
    else:
      # named entity
      try:
        text = chr(html.entities.name2codepoint[text[1:-1]])
      except KeyError:
        pass
    return text # leave as is

  text = re.sub("&#?\w+;", fixup, text)
  text = remove_unicode_control(text)
  return text

##### YAML serialization ######

# Apply some common settings for loading/dumping YAML and cache the
# data in pickled format which is a LOT faster than YAML.

def yaml_load(path, use_cache=True):
    # Loading YAML is ridiculously slow, so cache the YAML data
    # in a pickled file which loads much faster.

    # Check if the .pickle file exists and a hash stored inside it
    # matches the hash of the YAML file, and if so unpickle it.
    import pickle as pickle, os.path, hashlib
    h = hashlib.sha1(open(path, 'rb').read()).hexdigest()
    if use_cache and os.path.exists(path + ".pickle"):

        try:
          store = pickle.load(open(path + ".pickle", 'rb'))
          if store["hash"] == h:
            return store["data"]
        except EOFError:
          pass # bad .pickle file, pretend it doesn't exist

    # No cached pickled data exists, so load the YAML file.
    data = rtyaml.load(open(path))

    # Store in a pickled file for fast access later.
    pickle.dump({ "hash": h, "data": data }, open(path+".pickle", "wb"))

    return data

def yaml_dump(data, path):
    # write file
    rtyaml.dump(data, open(path, "w"))

    # Store in a pickled file for fast access later.
    import pickle as pickle, hashlib
    h = hashlib.sha1(open(path, 'rb').read()).hexdigest()
    pickle.dump({ "hash": h, "data": data }, open(path+".pickle", "wb"))

# if email settings are supplied, email the text - otherwise, just print it
def admin(body):
  try:
    if isinstance(body, Exception):
      body = format_exception(body)

    print(body) # always print it

    if email_settings:
        send_email(body)

  except Exception as exception:
    print("Exception logging message to admin, halting as to avoid loop")
    print(format_exception(exception))

# this should only be called if the settings are definitely there
def send_email(message):
  print("Sending email to %s..." % email_settings['to'])

  # adapted from http://www.doughellmann.com/PyMOTW/smtplib/
  msg = MIMEText(message)
  msg.set_unixfrom('author')
  msg['To'] = email.utils.formataddr(('Recipient', email_settings['to']))
  msg['From'] = email.utils.formataddr((email_settings['from_name'], email_settings['from']))
  msg['Subject'] = "%s - %i" % (email_settings['subject'], int(time.time()))

  server = smtplib.SMTP(email_settings['hostname'])
  try:
    server.ehlo()
    if email_settings['starttls'] and server.has_extn('STARTTLS'):
      server.starttls()
      server.ehlo()

    server.login(email_settings['user_name'], email_settings['password'])
    server.sendmail(email_settings['from'], [email_settings['to']], msg.as_string())
  finally:
    server.quit()

  print("Sent email to %s." % email_settings['to'])
