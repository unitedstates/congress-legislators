# Runs various validation tests on current legislators.

import rtyaml

# Congressional district apportionment for the 113th-... Congresses.
# The territories with delegates have 'T'. All others have the number
# of districts (e.g. 1 for one at-large district).
apportionment = {'AL': 7, 'AK': 1, 'AS': 'T', 'AZ': 9, 'AR': 4, 'CA': 53, 'CO': 7, 'CT': 5, 'DE': 1, 'DC': 'T', 'FL': 27, 'GA': 14, 'GU': 'T', 'HI': 2, 'ID': 2, 'IL': 18, 'IN': 9, 'IA': 4, 'KS': 4, 'KY': 6, 'LA': 6, 'ME': 2, 'MD': 8, 'MA': 9, 'MI': 14, 'MN': 8, 'MS': 4, 'MO': 8, 'MT': 1, 'NE': 3, 'NV': 4, 'NH': 2, 'NJ': 12, 'NM': 3, 'NY': 27, 'NC': 13, 'ND': 1, 'MP': 'T', 'OH': 16, 'OK': 5, 'OR': 5, 'PA': 18, 'PR': 'T', 'RI': 2, 'SC': 7, 'SD': 1, 'TN': 9, 'TX': 36, 'UT': 4, 'VT': 1, 'VI': 'T', 'VA': 11, 'WA': 10, 'WV': 3, 'WI': 8, 'WY': 1}

def run():

	P = rtyaml.load(open("../legislators-current.yaml"))
	P_historical = rtyaml.load(open("../legislators-historical.yaml"))

	offices = { }
	senate_ranks = { }

	for p in P:
		# IDs.

		if not p['id'].get('thomas'):
			print("No THOMAS ID for %s." % p['id']['bioguide'])
		elif not isinstance(p['id']['thomas'], str) or p['id']['thomas'][0] != '0':
			print("Invalid THOMAS ID for %s: %s." % (p['id']['bioguide'], str(p['id']['thomas'])))

		# Biographical data.

		if p.get("bio", {}).get("gender") not in ("M", "F"):
			print("Gender of %s is not valid: %s." % (p['id']['bioguide'], str(p.get("bio", {}).get("gender")) ))
		if len(p.get("bio", {}).get("birthday", "")) != 10:
			print("Birthday of %s is not valid: %s." % (p['id']['bioguide'], p.get("bio", {}).get("birthday", "")))

		# Get the current term.

		term = p['terms'][-1]

		# Start/end dates.

		if term['start'] not in ('2011-01-05', '2013-01-03', '2015-01-06'):
			print("Term start date of %s is not right: %s." % (p['id']['bioguide'], term['start']))

		if term['end'] not in ('2017-01-03', '2019-01-03', '2021-01-03'):
			print("Term end date of %s is not right: %s." % (p['id']['bioguide'], term['end']))

		# State and district.

		if term['state'] not in apportionment:
			print("Term state in %s is invalid: %s." % (p['id']['bioguide'], term['state']))

		else:
			if term['type'] == 'rep':
				ap = apportionment[term['state']]
				if not isinstance(term['district'], int) or term['district'] < 0:
					print("Term district in %s is invalid: %s." % (p['id']['bioguide'], str(term['district'])))
				elif ap in ("T", 1) and term['district'] != 0:
					print("Term district in %s is invalid for an at-large state: %s." % (p['id']['bioguide'], str(term['district'])))
				elif ap not in ("T", 1) and term['district'] == 0:
					print("Term district in %s is invalid for a not-at-large state: %s." % (p['id']['bioguide'], str(term['district'])))
				elif ap not in ("T", 1) and term['district'] > ap:
					print("Term district in %s is invalid: %s." % (p['id']['bioguide'], str(term['district'])))
			elif term['type'] == 'sen':
				if term.get("class") not in (1, 2, 3):
					print("Term class in %s is invalid: %s." % (p['id']['bioguide'], str(term['class'])))

		# Make sure there are no duplicate offices -- checked at the end.

		office = (term['type'], term['state'], term['district'] if term['type'] == 'rep' else term['class'])
		offices.setdefault(office, []).append(p)

		# Seate state rank.

		# Collect all of the senate state ranks so we can check that the distribution
		# within each state is correct, at the end.
		if term['type'] == 'sen':
			senate_ranks.setdefault(term['state'], []).append((p['id']['bioguide'], term['state_rank']))

		# Party.

		if term['party'] not in ("Republican", "Democrat", "Independent"):
			print("Suspicious party for %s: %s." % (p['id']['bioguide'], term['party']))
		elif term['party'] != "Independent" and term.get("caucus") != None:
			print("caucus field should not be used if the party is not Indpeendent, in %s: %s." % (p['id']['bioguide'], term['caucus']))
		elif term['party'] == "Independent" and term.get("caucus") is None:
			print("caucus field should be used if the party is Indpeendent, in %s: %s." % (p['id']['bioguide'], term['caucus']))

	# Check for duplicate offices.
	for k, v in offices.items():
		if len(v) > 1:
			print("Multiple holders of the office", k)
			print(rtyaml.dump(v))

	# Check for duplicate use of any of the IDs.
	ids = set()
	for p in P + P_historical:
		# Collect IDs for uniqueness test.
		for k, v1 in p['id'].items():
			# The 'fec' ID is a list, convert the others to a list.
			if not isinstance(v1, list):
				v1 = [v1]
			for v in v1:
				key = (k, v)
				if key in ids:
					print("Duplicate ID: %s %s" % (k, v))
					continue
				ids.add(key)


	for state, ranks in senate_ranks.items():
		# There can be a junior and senior senator, a senior senator, or no senators.
		# There can't be two juniors, two seniors, or just a junior senator.
		r = sorted(rr[1] for rr in ranks)
		if r not in [['junior', 'senior'], ['senior'], []]:
			print("State ranks for %s cannot be right: %s." % (state, ranks))

if __name__ == '__main__':
  run()
