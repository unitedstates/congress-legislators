# Runs various validation tests on current legislators.

import rtyaml

P = rtyaml.load(open("../legislators-current.yaml"))

senate_ranks = { }

for p in P:
	term = p['terms'][-1]

	# Collect all of the senate state ranks.
	if term['type'] == 'sen':
		senate_ranks.setdefault(term['state'], []).append((p['id']['bioguide'], term['state_rank']))

for state, ranks in senate_ranks.items():
	# There can be a junior and senior senator, a senior senator, or no senators.
	# There can't be two juniors, two seniors, or just a junior senator.
	r = sorted(rr[1] for rr in ranks)
	if r not in [['junior', 'senior'], ['senior'], []]:
		print("State ranks for %s cannot be right: %s." % (state, ranks))
