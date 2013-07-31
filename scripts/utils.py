# Helpful functions for finding data about members and committees

CURRENT_CONGRESS = 113
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


import urllib2
import os, errno, sys, traceback
import re, htmlentitydefs
import pprint
import rtyaml
from datetime import datetime
import time

import lxml.html # for meta redirect parsing

import yaml

import smtplib
import email.utils
from email.mime.text import MIMEText
import getpass


# read in an opt-in config file for supplying email settings
# returns None if it's not there, and this should always be handled gracefully
path = "email/config.yml"
if os.path.exists(path):
  email_settings = yaml.load(open(path, 'r')).get('email', None)
else:
  email_settings = None


def current_congress():
  year = current_legislative_year()
  return congress_from_legislative_year(year)

def congress_from_legislative_year(year):
  return ((year + 1) / 2) - 894

def legislative_year(date=None):
  if not date:
    date = datetime.datetime.now()

  year = date.year

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

def parse_date(date):
  return datetime.strptime(date, "%Y-%m-%d").date()

def log(object):
  if isinstance(object, (str, unicode)):
    print object
  else:
    pprint(object)

def uniq(seq):
  seen = set()
  seen_add = seen.add
  return [ x for x in seq if x not in seen and not seen_add(x)]

def flags():
  options = {}
  for arg in sys.argv[1:]:
    if arg.startswith("--"):

      if "=" in arg:
        key, value = arg.split('=')
      else:
        key, value = arg, True

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
  return yaml_dump(data, os.path.join(data_dir(), path))


##### Downloading

import scrapelib
scraper = scrapelib.Scraper(requests_per_minute=60, follow_robots=False, retry_attempts=3)
scraper.user_agent = "github.com/unitedstates/congress-legislators"

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
        response = urllib2.urlopen(url)
        body = response.read()
      else:
        response = scraper.urlopen(url)
        body = response.encode('utf-8')
    except scrapelib.HTTPError as e:
      log("Error downloading %s" % url)
      return None

    # don't allow 0-byte files
    if (not body) or (not body.strip()):
      return None

    # the downloader can optionally parse the body as HTML
    # and look for meta redirects. a bit expensive, so opt-in.
    if options.get('check_redirects', False):
      html_tree = lxml.html.fromstring(body)
      meta = html_tree.xpath("//meta[translate(@http-equiv, 'REFSH', 'refsh') = 'refresh']/@content")
      if meta:
        attr = meta[0]
        wait, text = attr.split(";")
        if text.lower().startswith("url="):

          new_url = text[4:]
          print "Found redirect, downloading %s instead.." % new_url

          options.pop('check_redirects')
          body = download(new_url, None, True, options)

    # cache content to disk
    if cache: write(body, cache)


  return body

def write(content, destination):
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
def unescape(text):

  def remove_unicode_control(str):
    remove_re = re.compile(u'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]')
    return remove_re.sub('', str)

  def fixup(m):
    text = m.group(0)
    if text[:2] == "&#":
      # character reference
      try:
        if text[:3] == "&#x":
          return unichr(int(text[3:-1], 16))
        else:
          return unichr(int(text[2:-1]))
      except ValueError:
        pass
    else:
      # named entity
      try:
        text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
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
    import cPickle as pickle, os.path, hashlib
    h = hashlib.sha1(open(path).read()).hexdigest()
    if use_cache and os.path.exists(path + ".pickle"):

        try:
          store = pickle.load(open(path + ".pickle"))
          if store["hash"] == h:
            return store["data"]
        except EOFError:
          pass # bad .pickle file, pretend it doesn't exist

    # No cached pickled data exists, so load the YAML file.
    data = rtyaml.load(open(path))

    # Store in a pickled file for fast access later.
    pickle.dump({ "hash": h, "data": data }, open(path+".pickle", "w"))

    return data

def yaml_dump(data, path):
    rtyaml.dump(data, open(path, "w"))

    # Store in a pickled file for fast access later.
    import cPickle as pickle, hashlib
    h = hashlib.sha1(open(path).read()).hexdigest()
    pickle.dump({ "hash": h, "data": data }, open(path+".pickle", "w"))

def pprint(data):
    rtyaml.pprint(data)


# if email settings are supplied, email the text - otherwise, just print it
def admin(body):
  try:
    if isinstance(body, Exception):
      body = format_exception(body)

    print body # always print it

    if email_settings:
        send_email(body)

  except Exception as exception:
    print "Exception logging message to admin, halting as to avoid loop"
    print format_exception(exception)

def format_exception(exception):
  exc_type, exc_value, exc_traceback = sys.exc_info()
  return "\n".join(traceback.format_exception(exc_type, exc_value, exc_traceback))

# this should only be called if the settings are definitely there
def send_email(message):
  print "Sending email to %s..." % email_settings['to']

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

  print "Sent email to %s." % email_settings['to']
