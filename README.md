congress-legislators
====================

Members of the United States Congress (1789-Present) and congressional committees (1973-Present) in YAML.

This repository contains data about legislators:

* legislators-current.yaml: Currently serving Members of Congress (as of last update).
* legislators-historical.yaml: Historical Members of Congress (i.e. all Members of Congress except those in the current file).
* legislators-social-media.yaml: Current social media accounts for Members of Congress.

And about committees:

* committees-current.yaml: Current committees of the Congress, with subcommittees.
* committee-membership-current.yaml: Current committee/subcommittee assignments as of the date of last update.
* committees-historical.yaml: Current and historical committees of the Congress, with subcommittees, from the 93rd Congress (1973) and on.

The files are in YAML (http://www.yaml.org/) format. YAML is a serialization format similar in structure to JSON but typically written with one field per line. Like JSON, it allows for nested structure. Each level of nesting is indicated by indentation or a dash.

This database has been collected from a variety of sources:

* GovTrack.us (http://www.govtrack.us).
* The Congressional Biographical Directory (http://bioguide.congress.gov).
* Congressional Committees, Historical Standing Committees data set by Garrison Nelson and Charles Stewart (http://web.mit.edu/17.251/www/data_page.html).
* Martis’s “The Historical Atlas of Political Parties in the United States Congress”, via Rosenthal, Howard L., and Keith T. Poole. United States Congressional Roll Call Voting Records, 1789-1990 (http://voteview.com/dwnl.htm).
* The Sunlight Labs Congress API (http://services.sunlightlabs.com/docs/Sunlight_Congress_API/).
* The Library of Congress's THOMAS website (http://thomas.loc.gov). 

The data is currently maintained both by hand and by some scripts in the `scripts` directory.

Legislators File Structure and Overview
---------------------------------------

legislators-current.yaml and legislators-historical.yaml contain biographical information on all Members of Congress that have ever served in Congress, that is, since 1789, as well as cross-walks into other databases.

Each legislator record is grouped into four guaranteed parts: id's which relate the record to other databases, name information (first, last, etc.), biographical information (birthday, gender), and terms served in Congress. A typical record looks something like this:

	- id:
		bioguide: R000570
		thomas: '01560'
		govtrack: 400351
	  name:
		first: Paul
		middle: D.
		last: Ryan
	  bio:
		gender: M
	  terms:
	  - type: rep
		start: '2011-01-05'
		end: '2012-12-31'
		state: WI
		district: 1
		party: Republican
		url: http://www.house.gov/ryan
		address: 1233 Longworth House Office Building;  20515-4901
	  - type: rep
		start: '2009-01-06'
		end: '2010-12-22'
		state: WI
		...

An optional fifth part, other_names, will list other names the legislator has gone by officially. This is helpful in cases where a Legislator's legal name has changed. These listings will only include the name attributes which differ from the current name, and a start or end date where applicable. An excerpted example:

	- id:
		bioguide: B001228
		thomas: '01465'
		govtrack: 400039
		opensecrets: N00007068
		votesmart: 1434
	  name:
		first: Mary
		middle: Whitaker
		last: Bono Mack
	  other_names:
	  - last: Bono
		end: '2007-12-17'
	  ...

Where multiple names exist, other names are listed chronologically by end date.

The split between legislators-current.yaml and legislators-historical.yaml is somewhat arbitrary because these files may not be updated immediately when a legislator leaves office. If it matters to you, just load both files.

Legislators are listed in order of the start date of their earliest term.

A separate file legislators-social-media.yaml stores social media account information. Its structure is similar but includes different fields.

Legislators Data Dictionary
---------------------------

legislators-current.yaml and legislators-historical.yaml

* id
	* bioguide: The alphanumeric ID for this legislator in http://bioguide.congress.gov. Note that at one time some legislators (women who had changed their name when they got married) had two entries on the bioguide website. Only one bioguide ID is included here.
	* thomas: The numeric ID for this legislator on http://thomas.gov and http://beta.congress.gov. The ID is stored as a string with leading zeros preserved.
	* lis: The alphanumeric ID for this legislator found in Senate roll call votes (http://www.senate.gov/pagelayout/legislative/a_three_sections_with_teasers/votes.htm).
	* govtrack: The numeric ID for this legislator on GovTrack.us.
	* opensecrets: The alphanumeric ID for this legislator on OpenSecrets.org.
	* votesmart: The numeric ID for this legislator on VoteSmart.org.
	* icpsr: The numeric ID for this legislator in Interuniversity Consortium for Political and Social Research databases.

* name
	* first: The legislator's first name. Sometimes a first initial and period (e.g. in W. Todd Akin), in which case it is suggested to not use the first name for display purposes.
	* middle: The legislator's middle name or middle initial (with period).
	* last: The legislator's last name. Many last names include non-ASCII characters. When building search systems, it is advised to index both the raw value as well as a value with extended characters replaced with their ASCII equivalents (in Python that's: u"".join(c for c in unicodedata.normalize('NFKD', lastname) if not unicodedata.combining(c))).
	* suffix: A suffix on the legislator's name, such as "Jr." or "III".
	* nickname: The legislator's nick name when used as a common alternative to his first name.
	* official_full: The full name of the legislator according to the House or Senate (usually first, middle initial, nickname, last, and suffix). Present for those serving on 2012-10-30 and later.

* bio
	* birthday: The legislator's birthday, in YYYY-MM-DD format.
	* gender: The legislator's gender, either "M" or "F".
	* religion: The legislator's religion.

* terms (one entry for each election)
	* type: The type of the term. Either "sen" for senators or "rep" for representatives.
	* start: The date the term began (i.e. typically a swearing in), in YYYY-MM-DD format.
	* end: The date the term ended (because the Congress adjourned, the legislator died or resigned, etc.). For terms that end in the future, this value is typically a rough guess at the end date of the Congressional session (currently 2012-12-31). This is the last date on which the legislator served this term.
	* state: The two-letter, uppercase USPS abbreviation for the state that the legislator is serving from. See below.
	* district: For representatives, the district number they are serving from. At-large districts are district 0. In historical data, unknown district numbers are recorded as -1.
	* class: For senators, their election class (1, 2, or 3). Note that this is unrelated to seniority.
	* party: The political party of the legislator. If the legislator changed parties, it is typically the most recent party held during the term.
	* url: The official website URL of the legislator (only valid if the term is current).
	* address: The mailing address of the legislator (only valid if the term is current).

Except where noted, fields are omitted when their value is empty or unknown.

In most cases, a legislator has a single term on any given date. In some cases a legislator resigned from one chamber and was sworn in in the other chamber on the same day.

Historically, some states sending at-large representatives actually sent multiple at-large representatives. Thus, state and district may not be a unique key.

Social Media Data Dictionary
----------------------------

The social media file legislators-social-media.yaml stores current social media account information.

Each record has two sections: id and social. The id section identifies the legislator using biogiude, thomas, and govtrack IDs (where available). The social section has social media account identifiers:

* twitter: The current official Twitter handle of the legislator.
* youtube: The current official YouTube handle of the legislator.
* facebook_graph: The numeric ID of the current official Facebook Page of the legislator in the Facebook Graph.

When a legislator leaves office, their social media account information is left in this file for historical preservation.

The file is in lexical order by bioguide ID for convenience. Legislators are only present when they have one or more social media accounts known. Fields are omitted when the account is unknown.

Committees Data Dictionary
--------------------------

The committees-current.yaml file lists all current House, Senate, and Joint committees of the United States Congress. It includes metadata and cross-walks into other databases of committee information. It is based on data scraped from House.gov and Senate.gov.

The committees-historical.yaml file is a possibly partial list of current and historical committees and subcommittees referred to in the unitedstates/congress project bill data, as scraped from THOMAS.gov. Only committees/subcommmittees that have had bills referred to them are included.

The basic structure of a committee entry looks like the following:

	- type: house
	  name: House Committee on Agriculture
	  url: http://agriculture.house.gov/
	  thomas_id: HSAG
	  house_committee_id: AG
	  subcommittees:
	     (... subcommittee list ...)

The two files are structured each as a list of committees, each entry an associative array of key/value pairs of committee metadata.

The fields available in both files are as follows:

* type: 'house', 'senate', or 'joint' indicating the type of commmittee
* name: The current (or most recent) official name of the committee.
* thomas_id: The four-letter code used for the committee on the THOMAS advanced search page.
* senate_committee_id: For Senate and Joint committees, the four-letter code used on http://www.senate.gov/pagelayout/committees/b_three_sections_with_teasers/membership.htm. Currently the same as the thomas_id.
* house_committee_id: For House committees, the two-letter code used on http://clerk.house.gov/committee_info/index.aspx. Currently always the same as the last two letters of the thomas_id.
* subcommittees: A list of subcommittees, with the following fields:
	* name: The name of the subcommittee, excluding "Subcommittee on" that appears at the start of most subcommittee names. Some subcommittee names begin with a lowercase "the" so bear that in mind during display.
	* thomas_id: The two-digit (zero-padded) code for the subcommittee as it appeared on THOMAS, and likely also the same code used on the House and Senate websites.

Additional fields are present on committee entries (but not subcommittee entries) in the committees-current.yaml file:

* url: The current website URL of the committee.
* address: The mailing address for the committee.
* phone: The phone number of the committee.

Two additional fields are present on committees and subcommmittees in the committees-historical.yaml file:

* congresses: A list of Congress numbers in which this committee appears on the THOMAS advanced search page. It is roughly an indication of the time period during which the committee was in use. However, if a committee was not referred any bills it may not appear on THOMAS's list and therefore would not appear here.
* names: A list of past names for the committee. This is an associative array from a Congress number to the name of the committee. The name is that given on the THOMAS advanced search page for previous Congresses and does not always exactly match the official names of commmittees.


Committee Membership Data Dictionary
------------------------------------

The committee-membership-current.yaml file contains current committee assignments, as of the date of the last update of this file. The file is structured as a mapping from committee IDs to a list of committee members. The basic structure looks like this:

	HSAG:
	- name: Frank D. Lucas
	  party: majority
	  rank: 1
	  title: Chair
	  bioguide: L000491
	  thomas: '00711'
	- name: Bob Goodlatte
	  party: majority
	  rank: 2
	(...snip...)
	HSAG03:
	- name: Jean Schmidt
	  party: majority
	  rank: 1
	  title: Chair

The committee IDs in this file are the thomas_id's from the committees-current.yaml file, or for subcommittees the concatentation of the thomas_id of the parent committee and the thomas_id of the subcommittee.

Each committee/subcommittee entry is a list containing the members of the committee. Each member has the following fields:

* name: The name of the Member of Congress. This field is intended for debugging. Instead, use the id fields.
* Some of the id fields used in the legislators YAML files, such as bioguide and thomas.
* party: Either "majority" or "minority." Committee work is divided strictly by party.
* rank: The apparent rank of the member on the committee, within his or her party. This is based on the order of names on the House/Senate committee membership pages. Rank 1 is always for the committee chair or ranking member (the most senior minority party member). The rank is essentially approximate, because the House/Senate pages don't necessarily make a committment that the order on the page precisely indicates actual rank (if such a concept even applies). But if you want to preserve the order as displayed by the House and Senate, you can use this attribute.
* title: The title of the member on the committee, e.g. Chair, Ranking Member, or Ex Officio. This field is not normalized, however, so be prepared to accept any string.
  
State Abbreviations
-------------------

Although you can find the USPS abbreviations for the 50 states anywhere, non-voting delegates from territories --- including historical territories that no longer exist --- are included in this database. Here is a complete list of abbreviations:

The 50 States:

	AK Alaska
	AL Alabama
	AR Arkansas
	AZ Arizona
	CA California
	CO Colorado
	CT Connecticut
	DE Delaware
	FL Florida
	GA Georgia
	HI Hawaii
	IA Iowa
	ID Idaho
	IL Illinois
	IN Indiana
	KS Kansas
	KY Kentucky
	LA Louisiana
	MA Massachusetts
	MD Maryland
	ME Maine
	MI Michigan
	MN Minnesota
	MO Missouri
	MS Mississippi
	MT Montana
	NC North Carolina
	ND North Dakota
	NE Nebraska
	NH New Hampshire
	NJ New Jersey
	NM New Mexico
	NV Nevada
	NY New York
	OH Ohio
	OK Oklahoma
	OR Oregon
	PA Pennsylvania
	RI Rhode Island
	SC South Carolina
	SD South Dakota
	TN Tennessee
	TX Texas
	UT Utah
	VA Virginia
	VT Vermont
	WA Washington
	WI Wisconsin
	WV West Virginia
	WY Wyoming

Current Territories:

Legislators serving in the House from these territories are called delegates, except for the so-called "Resident Commissioner" from Puerto Rico.

	AS American Samoa
	DC District of Columbia
	GU Guam
	MP Northern Mariana Islands
	PR Puerto Rico
	VI Virgin Islands

Historical Territories:

These territories no longer exist.

	DK Dakota Territory
	OL Territory of Orleans
	PI Philippines Territory/Commonwealth

Running Scripts
---------------

(Recommended) First, create a virtualenv in the scripts directory:

```bash
cd scripts
virtualenv virt
source virt/bin/activate
```

Install the requirements:

```bash
pip install -r requirements.txt
```

Try updating the latest committee data:

```bash
python update_committees.py
```

Check whether and how the data has changed:

```bash
git diff ../*.yaml
```
