import csv
import json
import glob
import os

import utils


def generate_csv():

	#yaml filenames
	yamls = ["legislators-current.yaml","legislators-historical.yaml"]
	yaml_social = "legislators-social-media.yaml"



	#list of yaml field name, csv column name tuples. Split into categories which do not reflect yaml structure (structured for logical csv column ordering)
	bio_fields = [
	("last", "last_name"),
	("first", "first_name"),
	("middle", "middle_name"),
	("suffix", "suffix"),
	("nickname", "nickname"),
	("official_full", "full_name"),
	("birthday", "birthday"),
	("gender", "gender")
	]

	#ID crosswalks, omit FEC id's, which may contain (arbitrary?) number of values
	crosswalk_fields = [
	("bioguide", "bioguide_id"),
	("thomas", "thomas_id"),
	("opensecrets", "opensecrets_id"),
	("lis","lis_id"),
	("fec","fec_ids"),
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
	("class", "senate_class"),
	("party", "party"),
	("url", "url"),
	("address", "address"),
	("phone", "phone"),
	("contact_form", "contact_form"),
	("rss_url", "rss_url"),
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
		print("Converting %s to YAML..." % filename)

		legislators = utils.load_data(filename)

		#convert yaml to csv
		csv_output = csv.writer(open("../" + filename.replace(".yaml", ".csv"),"w"))

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
					value = legislator['id'][pair[0]]
					if isinstance(value, list):
						# make FEC IDs comma-separated
						value = ",".join(value)
					legislator_row.append(value)
				else:
					legislator_row.append(None)

			csv_output.writerow(legislator_row)

	generate_district_office_csv()


def generate_district_office_csv():
	filename = "legislators-district-offices.yaml"
	legislators_offices = utils.load_data(filename)
	fields = [
		"bioguide", "thomas", "govtrack", "id", "address", "building",
		"city", "fax", "hours", "phone", "state", "suite", "zip",
		"latitude", "longitude"]

	f = open("../" + filename.replace(".yaml", ".csv"), "w")
	csv_output = csv.DictWriter(f, fieldnames=fields)
	csv_output.writeheader()

	for legislator_offices in legislators_offices:
		legislator_ids = legislator_offices['id']
		for office in legislator_offices['offices']:
			office.update(legislator_ids)
			csv_output.writerow(office)


def generate_json():

	#yaml filenames
    yamls = list(map(os.path.basename, glob.glob("../*.yaml")))

    for filename in yamls:
        print("Converting %s to JSON..." % filename)
        data = utils.load_data(filename)
        '''handle edge case of incorrect coercion for twitter ids in social media data
    		json/js can only handle maximum of 53-bit integers, so 64-bit integer twitter ids *must* be stringified
    		to consistently preserve value in json. otherwise they may be rounded and malformed
    	'''
        if 'legislators-social-media' in filename:
        	for social_legislator in data:
        		if 'twitter_id' in social_legislator['social']:
        			social_legislator['social']['twitter_id'] = str(social_legislator['social']['twitter_id'])

		#convert yaml to json
        utils.write(
            json.dumps(data, default=utils.format_datetime, indent=2),
            "../" + filename.replace(".yaml", ".json"))

if __name__ == '__main__':
	generate_csv()
	generate_json()

