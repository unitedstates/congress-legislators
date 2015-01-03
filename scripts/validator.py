# Runs various validation tests on current legislators.

import rtyaml

P = rtyaml.load(open("../legislators-current.yaml"))

senate_ranks = { }

for p in P:
	# Get the current term.
	term = p['terms'][-1]

	if term['start'] not in ('2011-01-05', '2013-01-03', '2015-01-06'):
		print("Term start date of %s is not right: %s." % (p['id']['bioguide'], term['start']))

	if term['end'] not in ('2017-01-03', '2019-01-03', '2021-01-03'):
		print("Term end date of %s is not right: %s." % (p['id']['bioguide'], term['end']))

	# Collect all of the senate state ranks so we can check that the distribution
	# within each state is correct, at the end.
	if term['type'] == 'sen':
		senate_ranks.setdefault(term['state'], []).append((p['id']['bioguide'], term['state_rank']))

for state, ranks in senate_ranks.items():
	# There can be a junior and senior senator, a senior senator, or no senators.
	# There can't be two juniors, two seniors, or just a junior senator.
	r = sorted(rr[1] for rr in ranks)
	if r not in [['junior', 'senior'], ['senior'], []]:
		print("State ranks for %s cannot be right: %s." % (state, ranks))
