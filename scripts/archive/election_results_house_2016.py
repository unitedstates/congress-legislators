import collections, requests, lxml
from utils import load_data, save_data

try:
	from yaml import CLoader
	assert CLoader #silence pyflakes
except ImportError:
	print("Warning: libyaml not found, loading will be slow...")

# # Open existing data.
historical = load_data("legislators-historical.yaml")
current = load_data("legislators-current.yaml")

# # Map bioguide IDs to records.
bioguide = { }
for entry in historical + current:
	bioguide[entry['id']['bioguide']] = entry

# # Get highest existing GovTrack ID.
govtrack_id = max(p['id']['govtrack'] for p in historical+current)

# load members-elect
xml = requests.get("http://clerk.house.gov/member_info/unofficial-115-member-elect-data.xml")
root=lxml.etree.fromstring(xml.content)

elected = []
for xml_member in root.findall('./members/member'):
	mi = xml_member.find("member-info")
	bioguide_id = mi.find("bioguideID").text

	#print("bioguide_id is {} for {}".format(bioguide_id, xml_member.find("statedistrict").text))
	if bioguide_id is None:
		print("WARN: no member found for {}".format(xml_member.find("statedistrict").text))
		continue
	
	if bioguide_id in bioguide:
		# Incumbent won or current representative has become a senator
		# or historical member is returning to office.
		p = bioguide[bioguide_id]
		party = p['terms'][-1]['party']

	else:
		# Make a new entry.
		govtrack_id += 1
		p = collections.OrderedDict([
			("id", collections.OrderedDict([
				("bioguide", bioguide_id),
				#("fec", [row['fec']]),
				("govtrack", govtrack_id),
				#("opensecrets", None), # don't know yet
				#("votesmart", int(row['votesmart'])),
				#("wikipedia", row['wikipedia']),
				#("ballotpedia", row['ballotpedia']),
			])),
			("name", collections.OrderedDict([
				("first", mi.find('firstname').text),
				("last", mi.find('lastname').text),
				#("official_full", mi.find('official_full').text), #not available yet
			])),
			("bio", collections.OrderedDict([
			 	("gender", "M" if mi.find('courtesy').text == "Mr." else "F"),
			 	#("birthday", row['birthday']),
			])),
			("terms", []),
		])

	party_char = mi.find('party').text
	party = 'Republican' if party_char == 'R' else 'Democrat' # valid?
	caucus_char = mi.find('caucus').text
	caucus = 'Republican' if caucus_char == 'R' else 'Democrat' # valid?

	district = int(xml_member.find("statedistrict").text[2:])
	# Add a new term.
	p['terms'].append(collections.OrderedDict([
		("type", "rep"),
		("start", "2017-01-03"),
		("end", "2019-01-03"),
		("state", mi.find('state').get('postal-code')),
		("district", district),
		("party", party),
		("phone", mi.find("phone").text),
	]))

	if caucus != party:
		p['terms'][-1]['caucus'] = caucus

	if len(p['terms']) > 1:
		# This is an incumbent. Copy some fields forward.
		for k in ('url', 'rss_url'):
			if k in p['terms'][-2]:
				p['terms'][-1][k] = p['terms'][-2][k]
			
	# Add to array.
	elected.append(p)

# Move losers to the historical file.
for p in list(current):
	if p['terms'][-1]['type'] == 'rep' and p not in elected:
		#print("moving {} {} {} to historical".format(p['id']['bioguide'], p['name']['first'], p['name']['last']))
		current.remove(p)
		historical.append(p)

		# If they have any current leadership roles, end it.
		for r in p.get('leadership_roles', []):
			if not r.get('end'):
				r['end'] = "2017-01-03"

# Move returning members to the current file 
for p in elected:
	if p in historical:
		historical.remove(p)
		current.append(p)

# Add new members to the current file, after the returning members.
for p in elected:
	if p not in current:
		current.append(p)

# Save.
save_data(current, "legislators-current.yaml")
save_data(historical, "legislators-historical.yaml")
