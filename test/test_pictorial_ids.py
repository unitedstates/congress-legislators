#!/usr/bin/env python
"""
Unit tests for pictorial_ids.py.
Run from root `congress-legislators` dir:
`python test/test_pictorial_ids.py`
"""
import sys
import unittest

sys.path.insert(0, "scripts")
from pictorial_ids import match_pictorial_id


class TestMatchBioguideID(unittest.TestCase):
    def test_basic(self):
        members_pictorial = [
            {
                "entryId": "13421",
                "memberId": 13421,
                "memberType": "Senator",
                "lastName": "Booker",
                "firstName": "Cory",
                "name": "Booker, Cory A.",
                "partyDescription": "Democrat",
                "congressionalDescription": "118th Congress",
                "title": "Not Applicable",
                "stateId": "NJ",
                "stateDescription": "New Jersey",
                "memberTypeId": "SR",
                "district": 0,
                "thumbNailImageUrl": "https://memberguide.gpo.gov/pictorialimages/118_SR_NJ_Booker_Cory.jpg",
                "imageUrl": "https://memberguide.gpo.gov/pictorialimages/118_SR_NJ_Booker_Cory.jpg",
                "imageFile": "118_SR_NJ_Booker_Cory.jpg",
            }
        ]
        legislator = {
            "id": {
                "bioguide": "B001288",
                "lis": "S370",
                "thomas": "02194",
                "govtrack": 412598,
                "opensecrets": "N00035267",
                "votesmart": 76151,
                "wikipedia": "Cory Booker",
                "ballotpedia": "Cory Booker",
                "fec": ["S4NJ00185"],
                "cspan": 84679,
                "maplight": 2051,
                "wikidata": "Q1135767",
                "google_entity_id": "kg:/m/06p430",
                "icpsr": 41308,
            },
            "name": {
                "first": "Cory",
                "middle": "Anthony",
                "last": "Booker",
                "official_full": "Cory A. Booker",
            },
            "bio": {"birthday": "1969-04-27", "gender": "M"},
            "leadership_roles": [
                {
                    "title": "Senate Democratic Policy & Communications Committee Vice Chair",
                    "chamber": "senate",
                    "start": "2023-01-03",
                }
            ],
            "terms": [
                {
                    "type": "sen",
                    "start": "2013-10-31",
                    "end": "2015-01-03",
                    "state": "NJ",
                    "class": 2,
                    "party": "Democrat",
                    "state_rank": "junior",
                    "url": "http://www.booker.senate.gov",
                    "phone": "202-224-3224",
                    "address": "141 Hart Senate Office Building Washington DC 20510",
                    "office": "141 Hart Senate Office Building",
                    "contact_form": "http://www.booker.senate.gov/?p=contact",
                },
                {
                    "type": "sen",
                    "start": "2015-01-06",
                    "end": "2021-01-03",
                    "state": "NJ",
                    "class": 2,
                    "party": "Democrat",
                    "state_rank": "junior",
                    "url": "https://www.booker.senate.gov",
                    "phone": "202-224-3224",
                    "address": "717 Hart Senate Office Building Washington DC 20510",
                    "office": "717 Hart Senate Office Building",
                    "contact_form": "https://www.booker.senate.gov/?p=contact",
                    "fax": "202-224-8378",
                },
                {
                    "type": "sen",
                    "start": "2021-01-03",
                    "end": "2027-01-03",
                    "state": "NJ",
                    "class": 2,
                    "state_rank": "junior",
                    "party": "Democrat",
                    "url": "https://www.booker.senate.gov",
                    "contact_form": "https://www.booker.senate.gov/?p=contact",
                    "address": "717 Hart Senate Office Building Washington DC 20510",
                    "office": "717 Hart Senate Office Building",
                    "phone": "202-224-3224",
                },
            ],
        }
        self.assertTrue(
            match_pictorial_id(legislator, members_pictorial)
            == members_pictorial[0]["memberId"]
        )

    def test_hassan(self):
        """First name is a nickname"""
        members_pictorial = [
            {
                "entryId": "13426",
                "memberId": 13426,
                "memberType": "Senator",
                "lastName": "Hassan",
                "firstName": "Maggie",
                "name": "Hassan, Maggie",
                "partyDescription": "Democrat",
                "congressionalDescription": "118th Congress",
                "title": "Not Applicable",
                "stateId": "NH",
                "stateDescription": "New Hampshire",
                "memberTypeId": "SR",
                "district": 0,
                "thumbNailImageUrl": "https://memberguide.gpo.gov/pictorialimages/118_SR_NH_Hassan_Maggie.jpg",
                "imageUrl": "https://memberguide.gpo.gov/pictorialimages/118_SR_NH_Hassan_Maggie.jpg",
                "imageFile": "118_SR_NH_Hassan_Maggie.jpg",
            }
        ]
        legislator = {
            "id": {
                "bioguide": "H001076",
                "fec": ["S6NH00091"],
                "govtrack": 412680,
                "votesmart": 42552,
                "wikipedia": "Maggie Hassan",
                "ballotpedia": "Maggie Hassan",
                "lis": "S388",
                "wikidata": "Q24053",
                "google_entity_id": "kg:/m/03c3zch",
                "opensecrets": "N00038397",
                "maplight": 2192,
                "cspan": 67481,
                "icpsr": 41702,
            },
            "name": {
                "first": "Margaret",
                "middle": "Wood",
                "nickname": "Maggie",
                "last": "Hassan",
                "official_full": "Margaret Wood Hassan",
            },
            "bio": {"gender": "F", "birthday": "1958-02-27"},
            "terms": [
                {
                    "type": "sen",
                    "start": "2017-01-03",
                    "end": "2023-01-03",
                    "state": "NH",
                    "class": 3,
                    "state_rank": "junior",
                    "party": "Democrat",
                    "address": "324 Hart Senate Office Building Washington DC 20510",
                    "office": "324 Hart Senate Office Building",
                    "phone": "202-224-3324",
                    "url": "https://www.hassan.senate.gov",
                    "contact_form": "https://www.hassan.senate.gov/content/contact-senator",
                },
                {
                    "type": "sen",
                    "start": "2023-01-03",
                    "end": "2029-01-03",
                    "state": "NH",
                    "class": 3,
                    "state_rank": "junior",
                    "party": "Democrat",
                    "url": "https://www.hassan.senate.gov",
                    "contact_form": "https://www.hassan.senate.gov/content/contact-senator",
                    "address": "324 Hart Senate Office Building Washington DC 20510",
                    "office": "324 Hart Senate Office Building",
                    "phone": "202-224-3324",
                },
            ],
        }
        self.assertTrue(
            match_pictorial_id(legislator, members_pictorial)
            == members_pictorial[0]["memberId"]
        )

    def test_hickenlooper(self):
        """GPO has first and last names swapped :("""
        members_pictorial = [
            {
                "entryId": "13433",
                "memberId": 13433,
                "memberType": "Senator",
                "lastName": "John",
                "firstName": "Hickenlooper",
                "name": "John, Hickenlooper",
                "partyDescription": "Democrat",
                "congressionalDescription": "118th Congress",
                "title": "Not Applicable",
                "stateId": "CO",
                "stateDescription": "Colorado",
                "memberTypeId": "SR",
                "district": 0,
                "thumbNailImageUrl": "https://memberguide.gpo.gov/pictorialimages/118_SR_CO_John_Hickenlooper.jpg",
                "imageUrl": "https://memberguide.gpo.gov/pictorialimages/118_SR_CO_John_Hickenlooper.jpg",
                "imageFile": "118_SR_CO_John_Hickenlooper.jpg",
            }
        ]
        legislator = {
            "id": {
                "bioguide": "H000273",
                "lis": "S408",
                "fec": ["S0CO00575"],
                "opensecrets": "N00044206",
                "govtrack": 456797,
                "wikidata": "Q430518",
                "wikipedia": "John Hickenlooper",
                "google_entity_id": "kg:/m/04g_1z",
                "ballotpedia": "John Hickenlooper",
            },
            "name": {
                "first": "John",
                "middle": "Wright",
                "last": "Hickenlooper",
                "official_full": "John W. Hickenlooper",
            },
            "bio": {"gender": "M", "birthday": "1952-02-07"},
            "terms": [
                {
                    "type": "sen",
                    "start": "2021-01-03",
                    "end": "2027-01-03",
                    "state": "CO",
                    "class": 2,
                    "state_rank": "junior",
                    "party": "Democrat",
                    "url": "https://www.hickenlooper.senate.gov",
                    "contact_form": "https://www.hickenlooper.senate.gov/contact/",
                    "address": "374 Russell Senate Office Building Washington DC 20510",
                    "office": "374 Russell Senate Office Building",
                    "phone": "202-224-5941",
                }
            ],
        }
        self.assertTrue(
            match_pictorial_id(legislator, members_pictorial)
            == members_pictorial[0]["memberId"]
        )

    def test_edwards(self):
        """Chuck Edwards has nickname coded differently"""
        members_pictorial = [
            {
                "entryId": "13140",
                "memberId": 13140,
                "memberType": "Representative",
                "lastName": "Edwards",
                "firstName": "Chuck",
                "name": "Edwards, Chuck",
                "partyDescription": "Republican",
                "congressionalDescription": "118th Congress",
                "title": "Not Applicable",
                "stateId": "NC",
                "stateDescription": "North Carolina",
                "memberTypeId": "RP",
                "district": 11,
                "thumbNailImageUrl": "https://memberguide.gpo.gov/pictorialimages/118_RP_NC_11_Edwards_Chuck.jpg",
                "imageUrl": "https://memberguide.gpo.gov/pictorialimages/118_RP_NC_11_Edwards_Chuck.jpg",
                "imageFile": "118_RP_NC_11_Edwards_Chuck.jpg",
            }
        ]
        legislator = {
            "id": {
                "bioguide": "E000246",
                "fec": ["H2NC14050"],
                "govtrack": 456914,
                "opensecrets": "N00049670",
                "wikidata": "Q55065043",
                "wikipedia": "Chuck Edwards",
                "google_entity_id": "kg:/g/11ghxw1t29",
                "votesmart": 166600,
            },
            "name": {
                "first": "Charles (Chuck)",
                "middle": "Marion",
                "last": "Edwards",
                "official_full": "Chuck Edwards",
            },
            "bio": {"gender": "M", "birthday": "1960-09-13"},
            "terms": [
                {
                    "type": "rep",
                    "start": "2023-01-03",
                    "end": "2025-01-03",
                    "state": "NC",
                    "district": 11,
                    "party": "Republican",
                    "url": "https://edwards.house.gov",
                    "address": "1505 Longworth House Office Building Washington DC 20515-3311",
                    "office": "1505 Longworth House Office Building",
                    "phone": "202-225-6401",
                }
            ],
        }
        self.assertTrue(
            match_pictorial_id(legislator, members_pictorial)
            == members_pictorial[0]["memberId"]
        )

    def test_leger_fernandez(self):
        """Leger Fernandez has no space in GPO"""
        members_pictorial = [
            {
                "entryId": "13164",
                "memberId": 13164,
                "memberType": "Representative",
                "lastName": "LegerFernandez",
                "firstName": "Teresa",
                "name": "LegerFernandez, Teresa",
                "partyDescription": "Democrat",
                "congressionalDescription": "118th Congress",
                "title": "Not Applicable",
                "stateId": "NM",
                "stateDescription": "New Mexico",
                "memberTypeId": "RP",
                "district": 3,
                "thumbNailImageUrl": "https://memberguide.gpo.gov/pictorialimages/118_RP_NM_3_LegerFernandez_Teresa.jpg",
                "imageUrl": "https://memberguide.gpo.gov/pictorialimages/118_RP_NM_3_LegerFernandez_Teresa.jpg",
                "imageFile": "118_RP_NM_3_LegerFernandez_Teresa.jpg",
            }
        ]

        legislator = {
            "id": {
                "bioguide": "L000273",
                "fec": ["H0NM03102"],
                "opensecrets": "N00044559",
                "govtrack": 456835,
                "wikidata": "Q96054905",
                "wikipedia": "Teresa Leger Fernandez",
                "google_entity_id": "kg:/g/11h_x7n8f5",
            },
            "name": {
                "first": "Teresa",
                "last": "Leger Fernandez",
                "official_full": "Teresa Leger Fernandez",
            },
            "bio": {"gender": "F", "birthday": "1959-07-01"},
            "terms": [
                {
                    "type": "rep",
                    "start": "2021-01-03",
                    "end": "2023-01-03",
                    "state": "NM",
                    "district": 3,
                    "party": "Democrat",
                    "address": "1432 Longworth House Office Building Washington DC 20515-3103",
                    "office": "1432 Longworth House Office Building",
                    "phone": "202-225-6190",
                    "url": "https://fernandez.house.gov",
                },
                {
                    "type": "rep",
                    "start": "2023-01-03",
                    "end": "2025-01-03",
                    "state": "NM",
                    "district": 3,
                    "party": "Democrat",
                    "url": "https://fernandez.house.gov",
                    "address": "1510 Longworth House Office Building Washington DC 20515-3103",
                    "office": "1510 Longworth House Office Building",
                    "phone": "202-225-6190",
                },
            ],
        }

        self.assertTrue(
            match_pictorial_id(legislator, members_pictorial)
            == members_pictorial[0]["memberId"]
        )

    def test_lalota(self):
        """LaLota is Nick and Nicholas"""
        members_pictorial = [
            {
                "entryId": "13169",
                "memberId": 13169,
                "memberType": "Representative",
                "lastName": "LaLota",
                "firstName": "Nick",
                "name": "LaLota, Nick",
                "partyDescription": "Republican",
                "congressionalDescription": "118th Congress",
                "title": "Not Applicable",
                "stateId": "NY",
                "stateDescription": "New York",
                "memberTypeId": "RP",
                "district": 1,
                "thumbNailImageUrl": "https://memberguide.gpo.gov/pictorialimages/118_RP_NY_1_LaLota_Nick.jpg",
                "imageUrl": "https://memberguide.gpo.gov/pictorialimages/118_RP_NY_1_LaLota_Nick.jpg",
                "imageFile": "118_RP_NY_1_LaLota_Nick.jpg",
            }
        ]

        legislator = {
            "id": {
                "bioguide": "L000598",
                "fec": ["H2NY01190"],
                "govtrack": 456920,
                "opensecrets": "N00050419",
                "wikidata": "Q115168182",
                "wikipedia": "Nick LaLota",
                "votesmart": 191957,
            },
            "name": {
                "first": "Nicolas",
                "middle": "Joseph",
                "last": "LaLota",
                "official_full": "Nick LaLota",
            },
            "bio": {"gender": "M", "birthday": "1978-06-23"},
            "terms": [
                {
                    "type": "rep",
                    "start": "2023-01-03",
                    "end": "2025-01-03",
                    "state": "NY",
                    "district": 1,
                    "party": "Republican",
                    "url": "https://lalota.house.gov",
                    "address": "1530 Longworth House Office Building Washington DC 20515-3201",
                    "office": "1530 Longworth House Office Building",
                    "phone": "202-225-3826",
                }
            ],
        }

        self.assertTrue(
            match_pictorial_id(legislator, members_pictorial)
            == members_pictorial[0]["memberId"]
        )

    def test_franklin(self):
        """Franklin's nickname is middle name"""
        members_pictorial = [
            {
                "entryId": "12999",
                "memberId": 12999,
                "memberType": "Representative",
                "lastName": "Franklin",
                "firstName": "Scott",
                "name": "Franklin, Scott",
                "partyDescription": "Republican",
                "congressionalDescription": "118th Congress",
                "title": "Not Applicable",
                "stateId": "FL",
                "stateDescription": "Florida",
                "memberTypeId": "RP",
                "district": 18,
                "thumbNailImageUrl": "https://memberguide.gpo.gov/pictorialimages/118_RP_FL_18_Franklin_C.jpg",
                "imageUrl": "https://memberguide.gpo.gov/pictorialimages/118_RP_FL_18_Franklin_C.jpg",
                "imageFile": "118_RP_FL_18_Franklin_C.jpg",
            }
        ]

        legislator = {
            "id": {
                "bioguide": "F000472",
                "fec": ["H0FL15104"],
                "opensecrets": "N00046760",
                "govtrack": 456807,
                "wikidata": "Q101198561",
                "wikipedia": "Scott Franklin (politician)",
                "google_entity_id": "kg:/g/11ft5hszwx",
            },
            "name": {
                "first": "C.",
                "middle": "Scott",
                "last": "Franklin",
                "official_full": "Scott Franklin",
            },
            "bio": {"gender": "M", "birthday": "1964-08-23"},
            "terms": [
                {
                    "type": "rep",
                    "start": "2021-01-03",
                    "end": "2023-01-03",
                    "state": "FL",
                    "district": 15,
                    "party": "Republican",
                    "address": "1517 Longworth House Office Building Washington DC 20515-0915",
                    "office": "1517 Longworth House Office Building",
                    "phone": "202-225-1252",
                    "url": "https://franklin.house.gov",
                },
                {
                    "type": "rep",
                    "start": "2023-01-03",
                    "end": "2025-01-03",
                    "state": "FL",
                    "district": 18,
                    "party": "Republican",
                    "url": "https://franklin.house.gov",
                    "address": "249 Cannon House Office Building Washington DC 20515-0918",
                    "office": "249 Cannon House Office Building",
                    "phone": "202-225-1252",
                },
            ],
        }

        self.assertTrue(
            match_pictorial_id(legislator, members_pictorial)
            == members_pictorial[0]["memberId"]
        )

    def test_mcmorris_rodgers(self):
        """Middle/last names encoded differently"""
        members_pictorial = [
            {
                "entryId": "11088",
                "memberId": 11088,
                "memberType": "Representative",
                "lastName": "Rodgers",
                "firstName": "Cathy",
                "name": "Rodgers, Cathy McMorris",
                "partyDescription": "Republican",
                "congressionalDescription": "116th Congress",
                "title": "Not Applicable",
                "stateId": "WA",
                "stateDescription": "Washington",
                "memberTypeId": "RP",
                "district": 5,
                "thumbNailImageUrl": "https://memberguide.gpo.gov/pictorialimages/116_rp_wa_5_rodgers_cathy.jpg",
                "imageUrl": "https://memberguide.gpo.gov/pictorialimages/116_rp_wa_5_rodgers_cathy.jpg",
                "imageFile": "116_rp_wa_5_rodgers_cathy.jpg",
            }
        ]

        legislator = {
            "id": {
                "bioguide": "M001159",
                "thomas": "01809",
                "govtrack": 400659,
                "opensecrets": "N00026314",
                "votesmart": 3217,
                "fec": ["H4WA05077"],
                "cspan": 1013063,
                "wikipedia": "Cathy McMorris Rodgers",
                "house_history": 18790,
                "ballotpedia": "Cathy McMorris Rodgers",
                "maplight": 664,
                "icpsr": 20535,
                "wikidata": "Q293343",
                "google_entity_id": "kg:/m/03dlf3",
            },
            "name": {
                "first": "Cathy",
                "middle": "Anne",
                "last": "McMorris Rodgers",
                "official_full": "Cathy McMorris Rodgers",
            },
            "bio": {"birthday": "1969-05-22", "gender": "F"},
            "terms": [
                {
                    "type": "rep",
                    "start": "2005-01-04",
                    "end": "2007-01-03",
                    "state": "WA",
                    "district": 5,
                    "party": "Republican",
                },
                {
                    "type": "rep",
                    "start": "2007-01-04",
                    "end": "2009-01-03",
                    "state": "WA",
                    "district": 5,
                    "party": "Republican",
                    "url": "http://mcmorris.house.gov",
                },
                {
                    "type": "rep",
                    "start": "2009-01-06",
                    "end": "2011-01-03",
                    "state": "WA",
                    "district": 5,
                    "party": "Republican",
                    "url": "http://mcmorris.house.gov",
                },
                {
                    "type": "rep",
                    "start": "2011-01-05",
                    "end": "2013-01-03",
                    "state": "WA",
                    "district": 5,
                    "party": "Republican",
                    "url": "http://mcmorris.house.gov",
                    "address": "2421 Rayburn HOB; Washington DC 20515-4705",
                    "phone": "202-225-2006",
                    "fax": "202-225-3392",
                    "contact_form": "https://mcmorrisforms.house.gov/write-to-cathy1",
                    "office": "2421 Rayburn House Office Building",
                },
                {
                    "type": "rep",
                    "start": "2013-01-03",
                    "end": "2015-01-03",
                    "state": "WA",
                    "party": "Republican",
                    "district": 5,
                    "url": "http://mcmorris.house.gov",
                    "address": "203 Cannon HOB; Washington DC 20515-4705",
                    "phone": "202-225-2006",
                    "fax": "202-225-3392",
                    "contact_form": "https://mcmorrisforms.house.gov/write-to-cathy1",
                    "office": "203 Cannon House Office Building",
                    "rss_url": "http://mcmorris.house.gov/common/rss/?rss=96",
                },
                {
                    "type": "rep",
                    "start": "2015-01-06",
                    "end": "2017-01-03",
                    "state": "WA",
                    "party": "Republican",
                    "district": 5,
                    "url": "http://mcmorris.house.gov",
                    "address": "203 Cannon HOB; Washington DC 20515-4705",
                    "phone": "202-225-2006",
                    "fax": "202-225-3392",
                    "contact_form": "https://mcmorrisforms.house.gov/write-to-cathy1",
                    "office": "203 Cannon House Office Building",
                    "rss_url": "http://mcmorris.house.gov/common/rss/?rss=96",
                },
                {
                    "type": "rep",
                    "start": "2017-01-03",
                    "end": "2019-01-03",
                    "state": "WA",
                    "district": 5,
                    "party": "Republican",
                    "phone": "202-225-2006",
                    "url": "https://mcmorris.house.gov",
                    "rss_url": "http://mcmorris.house.gov/common/rss/?rss=96",
                    "address": "1314 Longworth House Office Building; Washington DC 20515-4705",
                    "office": "1314 Longworth House Office Building",
                    "fax": "202-225-3392",
                },
                {
                    "type": "rep",
                    "start": "2019-01-03",
                    "end": "2021-01-03",
                    "state": "WA",
                    "district": 5,
                    "party": "Republican",
                    "phone": "202-225-2006",
                    "address": "1035 Longworth House Office Building Washington DC 20515-4705",
                    "office": "1035 Longworth House Office Building",
                    "url": "https://mcmorris.house.gov",
                    "rss_url": "http://mcmorris.house.gov/common/rss/?rss=96",
                },
                {
                    "type": "rep",
                    "start": "2021-01-03",
                    "end": "2023-01-03",
                    "state": "WA",
                    "district": 5,
                    "party": "Republican",
                    "url": "https://mcmorris.house.gov",
                    "rss_url": "http://mcmorris.house.gov/common/rss/?rss=96",
                    "address": "1035 Longworth House Office Building Washington DC 20515-4705",
                    "office": "1035 Longworth House Office Building",
                    "phone": "202-225-2006",
                },
            ],
        }

        self.assertTrue(
            match_pictorial_id(legislator, members_pictorial)
            == members_pictorial[0]["memberId"]
        )

    def test_de_la_cruz(self):
        """Accent"""
        members_pictorial = [
            {
                "entryId": "13272",
                "memberId": 13272,
                "memberType": "Representative",
                "lastName": "DeLaCruz",
                "firstName": "Monica",
                "name": "DeLaCruz, Monica",
                "partyDescription": "Republican",
                "congressionalDescription": "118th Congress",
                "title": "Not Applicable",
                "stateId": "TX",
                "stateDescription": "Texas",
                "memberTypeId": "RP",
                "district": 15,
                "thumbNailImageUrl": "https://memberguide.gpo.gov/pictorialimages/118_RP_TX_15_DeLaCruz_Monica.jpg",
                "imageUrl": "https://memberguide.gpo.gov/pictorialimages/118_RP_TX_15_DeLaCruz_Monica.jpg",
                "imageFile": "118_RP_TX_15_DeLaCruz_Monica.jpg",
            }
        ]

        legislator = {
            "id": {
                "bioguide": "D000594",
                "fec": ["H0TX15124"],
                "govtrack": 456943,
                "opensecrets": "N00045793",
                "wikidata": "Q115496109",
                "wikipedia": "Monica De La Cruz",
                "votesmart": 188292,
            },
            "name": {
                "first": "Mónica",
                "last": "De La Cruz",
                "official_full": "Monica De La Cruz",
            },
            "bio": {"gender": "F", "birthday": "1974-11-11"},
            "terms": [
                {
                    "type": "rep",
                    "start": "2023-01-03",
                    "end": "2025-01-03",
                    "state": "TX",
                    "district": 15,
                    "party": "Republican",
                    "url": "https://delacruz.house.gov",
                    "address": "1415 Longworth House Office Building Washington DC 20515-4315",
                    "office": "1415 Longworth House Office Building",
                    "phone": "202-225-9901",
                }
            ],
        }

        self.assertTrue(
            match_pictorial_id(legislator, members_pictorial)
            == members_pictorial[0]["memberId"]
        )


if __name__ == "__main__":
    unittest.main()
