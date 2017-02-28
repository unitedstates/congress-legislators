import csv
import json
import utils

def run():

	#yaml filenames
	yamls = ["legislators-current.yaml","legislators-historical.yaml"]
	yaml_social = "legislators-social-media.yaml"



	#list of yaml field name, csv column name tuples. Split into categories which do not reflect yaml structure (structured for logical csv column ordering)
	bio_fields = [
	("last", "last_name"),
	("first", "first_name"),
	("birthday", "birthday"),
	("gender", "gender")
	]

	#ID crosswalks, omit FEC id's, which may contain (arbitrary?) number of values
	crosswalk_fields = [
	("bioguide", "bioguide_id"),
	("thomas", "thomas_id"),
	("opensecrets", "opensecrets_id"),
	("lis","lis_id"),
	("cspan", "cspan_id"),
	("govtrack", "govtrack_id"),
	("votesmart", "votesmart_id"),
	("ballotpedia", "ballotpedia_id"),
	("washington_post", "washington_post_id"),
	("icpsr", "icpsr_id"),
	("wikipedia", "wikipedia_id")
	]

	#separate list for children of "terms", csv only captures data for most recent term
	#currently excluding start/end dates - earliest start to latest end is deceptive (excludes gaps) as is start/end for most recent term
	term_fields = [
	("type", "type"),
	("state", "state"),
	("district", "district"),
	("party", "party"),
	("url", "url"),
	("address", "address"),
	("phone", "phone"),
	("contact_form", "contact_form"),
	("rss_url", "rss_url")
	]

	#pulled from legislators-social-media.yaml
	social_media_fields = [
	("twitter", "twitter"),
	("facebook", "facebook"),
	("youtube", "youtube"),
	("youtube_id", "youtube_id")
	]


	print("Loading %s..." %yaml_social)
	social = utils.load_data(yaml_social)

	for filename in yamls:
		print("Loading %s..." % filename)
		legislators = utils.load_data(filename)

		#convert yaml to json
		utils.write(
		json.dumps(legislators, sort_keys=True, indent=2, default=utils.format_datetime),
		"../alternate_formats/%s.json" %filename.rstrip(".yaml"))

		#convert yaml to csv
		csv_output = csv.writer(open("../alternate_formats/%s.csv"%filename.rstrip(".yaml"),"w"))

		head = []
		for pair in bio_fields:
			head.append(pair[1])
		for pair in term_fields:
			head.append(pair[1])
		for pair in social_media_fields:
			head.append(pair[1])
		for pair in crosswalk_fields:
			head.append(pair[1])
		csv_output.writerow(head)

		for legislator in legislators:
			legislator_row = []
			for pair in bio_fields:
				if 'name' in legislator and pair[0] in legislator['name']:
					legislator_row.append(legislator['name'][pair[0]])
				elif 'bio' in legislator and pair[0] in legislator['bio']:
					legislator_row.append(legislator['bio'][pair[0]])
				else:
					legislator_row.append(None)

			for pair in term_fields:
				latest_term = legislator['terms'][len(legislator['terms'])-1]
				if pair[0] in latest_term:
					legislator_row.append(latest_term[pair[0]])
				else:
					legislator_row.append(None)

			social_match = None
			for social_legislator in social:
				if 'bioguide' in legislator['id'] and 'bioguide' in social_legislator['id'] and legislator['id']['bioguide'] == social_legislator['id']['bioguide']:
					social_match = social_legislator
					break
				elif 'thomas' in legislator['id'] and 'thomas' in social_legislator['id'] and legislator['id']['thomas'] == social_legislator['id']['thomas']:
					social_match = social_legislator
					break
				elif 'govtrack' in legislator['id'] and 'govtrack' in social_legislator['id'] and legislator['id']['govtrack'] == social_legislator['id']['govtrack']:
					social_match = social_legislator
					break
			for pair in social_media_fields:
				if social_match != None:
					if pair[0] in social_match['social']:
						legislator_row.append(social_match['social'][pair[0]])
					else:
						legislator_row.append(None)
				else:
					legislator_row.append(None)

			for pair in crosswalk_fields:
				if pair[0] in legislator['id']:
					legislator_row.append(legislator['id'][pair[0]])
				else:
					legislator_row.append(None)

			csv_output.writerow(legislator_row)

if __name__ == '__main__':
	run()
