# Scans Wikipedia for pages using the CongBio and CongLinks
# templates, which have Bioguide IDs. Updates the 'wikipedia'
# ID field for matching Members of Congress, and for pages
# using the CongLinks template also updates a variety of
# other ID as found in the template.

import lxml.etree, re, urllib.request, urllib.parse, urllib.error
import utils, os.path

def run():

	# Field mapping. And which fields should be turned into integers.
	# See https://en.wikipedia.org/wiki/Template:CongLinks for what's possibly available.
	fieldmap = {
		"congbio": "bioguide",
		#"fec": "fec", # handled specially...
		"govtrack": "govtrack", # for sanity checking since we definitely have this already (I caught some Wikipedia errors)
		"opensecrets": "opensecrets",
		"votesmart": "votesmart",
		"cspan": "cspan",
	}
	int_fields = ("govtrack", "votesmart", "cspan")

	# default to not caching
	cache = utils.flags().get('cache', False)

	# Load legislator files and map bioguide IDs.
	y1 = utils.load_data("legislators-current.yaml")
	y2 = utils.load_data("legislators-historical.yaml")
	bioguides = { }
	for y in y1+y2:
	  bioguides[y["id"]["bioguide"]] = y

	# Okay now the Wikipedia stuff...

	def get_matching_pages():
		# Does a Wikipedia API search for pages containing either of the
		# two templates. Returns the pages.

		page_titles = set()

		for template in ("CongLinks", "CongBio"):
			eicontinue = ""
			while True:
				# construct query URL, using the "eicontinue" of the last query to get the next batch
				url = 'http://en.wikipedia.org/w/api.php?action=query&list=embeddedin&eititle=Template:%s&eilimit=500&format=xml' % template
				if eicontinue: url += "&eicontinue=" + eicontinue

				# load the XML
				print("Getting %s pages (%d...)" % (template, len(page_titles)))
				dom = lxml.etree.fromstring(utils.download(url, None, True)) # can't cache eicontinue probably

				for pgname in dom.xpath("query/embeddedin/ei/@title"):
					page_titles.add(pgname)

				# get the next eicontinue value and loop
				eicontinue = dom.xpath("string(query-continue/embeddedin/@eicontinue)")
				if not eicontinue: break

		return page_titles

	# Get the list of Wikipedia pages that use any of the templates we care about.
	page_list_cache_file = os.path.join(utils.cache_dir(), "legislators/wikipedia/page_titles")
	if cache and os.path.exists(page_list_cache_file):
		# Load from cache.
		matching_pages = open(page_list_cache_file).read().split("\n")
	else:
		# Query Wikipedia API and save to cache.
		matching_pages = get_matching_pages()
		utils.write(("\n".join(matching_pages)), page_list_cache_file)

	# Filter out things that aren't actually pages (User:, Talk:, etcetera, anything with a colon).
	matching_pages = [p for p in matching_pages if ":" not in p]

	# Load each page's content and parse the template.
	for p in sorted(matching_pages):
		if " campaign" in p: continue
		if " (surname)" in p: continue
		if "career of " in p: continue
		if "for Congress" in p: continue
		if p.startswith("List of "): continue
		if p in ("New York in the American Civil War", "Upper Marlboro, Maryland"): continue

		# Query the Wikipedia API to get the raw page content in XML,
		# and then use XPath to get the raw page text.
		url = "http://en.wikipedia.org/w/api.php?action=query&titles=" + urllib.parse.quote(p.encode("utf8")) + "&export&exportnowrap"
		cache_path = "legislators/wikipedia/pages/" + p
		dom = lxml.etree.fromstring(utils.download(url, cache_path, not cache))
		page_content = dom.xpath("string(mw:page/mw:revision/mw:text)", namespaces={ "mw": "http://www.mediawiki.org/xml/export-0.8/" })

		# Build a dict for the IDs that we want to insert into our files.
		new_ids = {
			"wikipedia": p # Wikipedia page name, with spaces for spaces (not underscores)
		}

		if "CongLinks" in page_content:
			# Parse the key/val pairs in the template.
			m = re.search(r"\{\{\s*CongLinks\s+([^}]*\S)\s*\}\}", page_content)
			if not m: continue # no template?
			for arg in m.group(1).split("|"):
				if "=" not in arg: continue
				key, val = arg.split("=", 1)
				key = key.strip()
				val = val.strip()
				if val and key in fieldmap:
					try:
						if fieldmap[key] in int_fields: val = int(val)
					except ValueError:
						print("invalid value", key, val)
						continue

					if key == "opensecrets": val = val.replace("&newMem=Y", "").replace("&newmem=Y", "").replace("&cycle=2004", "").upper()
					new_ids[fieldmap[key]] = val

			if "bioguide" not in new_ids: continue
			new_ids["bioguide"] = new_ids["bioguide"].upper() # hmm
			bioguide = new_ids["bioguide"]

		else:
			m = re.search(r"\{\{\s*CongBio\s*\|\s*(\w+)\s*\}\}", page_content)
			if not m: continue # no template?
			bioguide = m.group(1).upper()


		if not bioguide in bioguides:
			print("Member not found: " + bioguide, p, "(Might have been a delegate to the Constitutional Convention.)")
			continue

		# handle FEC ids specially because they are stored in an array...
		fec_id = new_ids.get("fec")
		if fec_id: del new_ids["fec"]

		member = bioguides[bioguide]
		member["id"].update(new_ids)

		# ...finish the FEC id.
		if fec_id:
			if fec_id not in bioguides[bioguide]["id"].get("fec", []):
				bioguides[bioguide]["id"].setdefault("fec", []).append(fec_id)

		#print p.encode("utf8"), new_ids

	utils.save_data(y1, "legislators-current.yaml")
	utils.save_data(y2, "legislators-historical.yaml")

if __name__ == '__main__':
  run()
