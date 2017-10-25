#!/usr/bin/env python

# Geocodes district office addresses using Google Maps.
# Opens legislators-district-offices.yaml, finds offices
# that haven't previously been geocoded and have a street
# adddress, city, and state, then geocodes them and adds
# latitude and longitude fields to the office object
# and writes back to the same file.
#
# Assumes you have a Google Maps API key in
# scripts/cache/google_maps_api_key.txt, and that
# this key is enabled for the Geocoding API in the
# Google APIs Console.

import requests
import utils

class GeocodeException(Exception):
	def __init__(self, message):
		super(GeocodeException, self).__init__(message)

def run(legislator_ids=None):
	legislators = utils.load_data('legislators-district-offices.yaml')
	try:
		for l in legislators:
			if legislator_ids and l['id']['bioguide'] not in legislator_ids:
				continue
			geocode_offices(l)
	finally:
		# Save in-progress geocodes in case of keyboard interrupt
		print("Saving data...")
		utils.save_data(legislators, 'legislators-district-offices.yaml')

def geocode_offices(l):
	for o in l.get('offices', []):
		if o.get('latitude'):
			continue
		if not o.get('address') or not o.get('city') or not o.get('state'):
			continue
		address_query = ', '.join([o['address'], o['city'], utils.states[o['state']]])
		result = None
		try:
			result = geocode(address_query)
			_sanity_check_location(o, l['id']['bioguide'], result)
		except GeocodeException as e:
			print('Geocoding failed for %s office %s (%s): %s. Query: "%s". Result: "%s"' % (
				l['id']['bioguide'], o['city'], o['address'], e, address_query,
				result['formatted_address'] if result else None))
			continue

		location = result['geometry']['location']
		o['latitude'] = location['lat']
		o['longitude'] = location['lng']
		print('Success: %s office %s, query "%s" geocoded to "%s" (%s,%s)' % (
			l['id']['bioguide'], o['city'], address_query, result['formatted_address'],
			location['lat'], location['lng']))

def geocode(address):
	params = {
		'address': address,
		'key': _get_api_key(),
		}
	response = requests.get('https://maps.googleapis.com/maps/api/geocode/json', params=params)
	js = response.json()
	if js.get('status') != 'OK':
		raise GeocodeException('Non-success response from geocoder: %s' % js.get('status'))
	return js['results'][0]

_api_key = None

def _get_api_key():
	global _api_key
	if not _api_key:
		_api_key = open('cache/google_maps_api_key.txt').read().strip()
	return _api_key

def _find_address_component(geocode_result, component_type):
	for component in geocode_result['address_components']:
		if component_type in component['types']:
			return component
	return None

SANITY_CHECK_EXEMPTIONS = (
	# (bioguide, office_city)
	('B001295', 'Mt. Vernon'),
	('B001290', 'Spotsylvania'),
	('B001300', 'San Pedro'),
	('C000984', 'Ellicott'),
	('C001038', 'Bronx'),
	('C001038', 'Queens'),
	('C001067', 'Brooklyn'),
	('D000482', 'Penn Hills'),
	('D000625', 'Brooklyn'),
	('D000625', 'Staten Island'),
	('D000626', 'West Chester'),
	('E000179', 'Bronx'),
	('E000179', 'Mt. Vernon'),
	('H000324', 'Mangonia Park'),
	('H001059', 'Campton Hills'),
	('J000294', 'Brooklyn'),
	('K000375', 'Hyannis'),
	('M000087', 'Astoria'),
	('M000087', 'Brooklyn'),
	('M001137', 'Arverne'),
	('M001137', 'Jamaica'),
	('M001151', 'Pittsburgh'),
	('M001179', 'Lake Ariel'),
	('M001188', 'Flushing'),
	('M001188', 'Forest Hills'),
	('M001193', 'Marlton'),
	('M001201', 'Shelby Township'),
	('N000002', 'Brooklyn'),
	('N000032', 'Fort Lauderdale'),
	('P000605', 'York'),
	('Q000023', 'Lakeview'),
	('R000486', 'Commerce'),
	('R000576', 'Timonium'),
	('R000601', 'Rockwall'),
	('S000248', 'Bronx'),
	('S000522', 'Hamilton'),
	('V000081', 'Brooklyn'),
	('W000808', 'Miami Gardens'),
	('W000822', 'Ewing'),
	('S000522', 'Plumsted'),
	)

def _sanity_check_location(office, bioguide_id, geocode_result):
	for exemption in SANITY_CHECK_EXEMPTIONS:
		if bioguide_id == exemption[0] and office['city'] == exemption[1]:
			return

	state_result_component = _find_address_component(geocode_result, 'administrative_area_level_1')
	if not state_result_component:
		raise GeocodeException('No state code found in geocode result')
	result_state = state_result_component['short_name']
	if result_state != office['state']:
		raise GeocodeException('Geocode result is not in the right state')

	city_result_component = _find_address_component(geocode_result, 'locality')
	if not city_result_component:
		raise GeocodeException('No city found in geocode result')
	result_city = city_result_component['long_name']
	result_city_alt = city_result_component['short_name']
	if not (_do_city_names_match(result_city, office['city']) or _do_city_names_match(result_city_alt, office['city'])):
		# For big cities, Google Maps seems to consider the "city" to be e.g. Los Angeles
		# even though the mailing address and colloquial address may be e.g. Panorama City.
		# This common name is in the "neighorhood field, so look at that too
		result_subcity_component = _find_address_component(geocode_result, 'neighborhood')
		if result_subcity_component:
			result_subcity = result_subcity_component['long_name']
			if _do_city_names_match(result_subcity, office['city']):
				return
		raise GeocodeException('Geocode result is not in the right city')

def _do_city_names_match(name1, name2):
	return name1.lower().replace('.', '') == name2.lower().replace('.', '')

if __name__ == '__main__':
	import sys
	run(legislator_ids=sys.argv[1:])
