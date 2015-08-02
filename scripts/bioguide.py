#!/usr/bin/env python

# Updates our database using a deep parse of the bioguide.

# options:
#  --cache: load bioguide from cache if present on disk (default: true)
#  --bioguide X000000: do *only* a single legislator

import lxml.html, io
import datetime
import re
import utils
from utils import download, load_data, save_data

from bioguide2 import parse_bioguide_entry

def run():
  # Fetch the bioguide. Hits the network if the cache of the bioguide
  # isn't present yet, or if --cache=False is set.
  one_bioguide, bioguide_entries = download_the_bioguide()

  # Do a deep parse on the bioguide.
  parse_the_bioguide(bioguide_entries)

  # Save result.
  if not one_bioguide:
    # Save a cached file if we aren't just parsing one record.
    save_data(bioguide_entries, "bioguide-parsed.yaml")
  else:
    import rtyaml
    print(one_bioguide)
    print(rtyaml.dump(bioguide_entries[one_bioguide]))



def download_the_bioguide():
  # default to caching
  cache = utils.flags().get('cache', True)
  force = not cache

  bioguide_entries = { }
  for filename in ("legislators-historical.yaml", "legislators-current.yaml"):
    print("Fetching bioguide entries for legislators in %s..." % filename)
    legislators = load_data(filename)

    # reoriented cache to access by bioguide ID
    by_bioguide = { }
    for m in legislators:
      if "bioguide" in m["id"]:
        by_bioguide[m["id"]["bioguide"]] = m

    # optionally focus on one legislator
    one_bioguide = utils.flags().get('bioguide', None)
    if one_bioguide:
      if one_bioguide not in by_bioguide:
        continue
      bioguides = [one_bioguide]
    else:
      bioguides = sorted(by_bioguide.keys())

    # Download & parse the HTML of the bioguide pages.
    for bioguide in bioguides:
      try:
      	dom = fetch_bioguide_page(bioguide, force)
      except Exception as e:
      	print(e)
      	continue

      # Extract the member's name and the biography paragraph.
      try:
        name = dom.cssselect("p font")[0]
        biography = dom.cssselect("p")[0]
      except IndexError:
        print("[%s] Missing name or content!" % bioguide)
        continue

      name = name.text_content().strip().rstrip(',')
      biography = biography.text_content().strip().replace("\n", " ").replace("\r", " ")
      biography = re.sub("\s+", " ", biography)

      bioguide_entries[bioguide] = {
        "name": name,
        "text": biography,
      }

  return one_bioguide, bioguide_entries

def fetch_bioguide_page(bioguide, force):
  url = "http://bioguide.congress.gov/scripts/biodisplay.pl?index=%s" % bioguide
  cache = "legislators/bioguide/%s.html" % bioguide
  try:
    body = download(url, cache, force, options={ "log_downloads": True })

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

def parse_the_bioguide(bioguide_entries):
  # Parse the bioguide entries using our modgrammar grammar.
  # This part is slow and CPU-bound, so use a pool of workers.

  from multiprocessing import Pool

  with Pool() as pool:
    # Queue up all of the tasks.
    tasks = { }
    for bioguide in sorted(bioguide_entries):
      # Queue up a call to parse_bioguide_entry. This returns an
      # AsyncResult which lets us check later if the call completed.
      ar = pool.apply_async(
        parse_bioguide_entry,
        [bioguide_entries[bioguide]['name'], bioguide_entries[bioguide]['text']])
      tasks[bioguide] = ar

    # Wait for all of the tasks to complete and store the results
    # in the main dict.
    for bioguide, ar in sorted(tasks.items()):
      print(bioguide, bioguide_entries[bioguide]['name'], '...')
      parsed_info = ar.get()
      bioguide_entries[bioguide].update(parsed_info)
      


if __name__ == '__main__':
  run()