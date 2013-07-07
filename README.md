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

This repository also contains a database of presidents and vice presidents in executive.yaml. Recall that vice presidents are also president of the Senate and cast tie-breaking votes.

The files are in YAML (http://www.yaml.org/) format. YAML is a serialization format similar in structure to JSON but typically written with one field per line. Like JSON, it allows for nested structure. Each level of nesting is indicated by indentation or a dash.

This database has been collected from a variety of sources:

* GovTrack.us (http://www.govtrack.us).
* The Congressional Biographical Directory (http://bioguide.congress.gov).
* Congressional Committees, Historical Standing Committees data set by Garrison Nelson and Charles Stewart (http://web.mit.edu/17.251/www/data_page.html).
* Martis’s “The Historical Atlas of Political Parties in the United States Congress”, via Rosenthal, Howard L., and Keith T. Poole. United States Congressional Roll Call Voting Records, 1789-1990 (http://voteview.com/dwnl.htm).
* The Sunlight Labs Congress API (http://sunlightlabs.github.com/congress/).
* The Library of Congress's THOMAS website (http://thomas.loc.gov).
* C-SPAN's Congressional Chronicle (http://www.c-spanvideo.org/congress)

The data is currently maintained both by hand and by some scripts in the `scripts` directory.

Legislators File Structure and Overview
---------------------------------------

legislators-current.yaml and legislators-historical.yaml contain biographical information on all Members of Congress that have ever served in Congress, that is, since 1789, as well as cross-walks into other databases.

Each legislator record is grouped into four guaranteed parts: id's which relate the record to other databases, name information (first, last, etc.), biographical information (birthday, gender), and terms served in Congress. A typical record looks something like this:

	- id:
		bioguide: R000570
		thomas: '01560'
		govtrack: 400351
		opensecrets: N00004357
		votesmart: 26344
		fec:
		  - H8WI01024
		cspan: 57970
		wikipedia: Paul Ryan
		ballotpedia: Paul Ryan
		house_history: 20785
		opencong: '400351'	       
	  name:
		first: Paul
		middle: D.
		last: Ryan
	  bio:
		birthday: '1970-01-29'
		gender: M
	  terms:
	  ...
	  - type: rep
		start: '2011-01-03'
		end: '2013-01-03'
	  ...
	  - type: rep
		start: '2013-01-03'
		end: '2015-01-03'
		state: WI
		party: Republican
		district: 1
		url: http://paulryan.house.gov
		address: 1233 Longworth HOB; Washington DC 20515-4901
		phone: 202-225-3031
		fax: 202-225-3393
		contact_form: http://www.house.gov/ryan/email.htm
		office: 1233 Longworth House Office Building

Terms correspond to elections and are listed in chronological order. If a legislator is currently serving, the current term information will always be the last one. To check if a legislator is currently serving, check that the end date on the last term is in the future.

The split between legislators-current.yaml and legislators-historical.yaml is somewhat arbitrary because these files may not be updated immediately when a legislator leaves office. If it matters to you, just load both files.

A separate file legislators-social-media.yaml stores social media account information. Its structure is similar but includes different fields.

Legislators Data Dictionary
---------------------------

The following fields are available in legislators-current.yaml and legislators-historical.yaml:

* id
	* bioguide: The alphanumeric ID for this legislator in http://bioguide.congress.gov. Note that at one time some legislators (women who had changed their name when they got married) had two entries on the bioguide website. Only one bioguide ID is included here.
	* thomas: The numeric ID for this legislator on http://thomas.gov and http://beta.congress.gov. The ID is stored as a string with leading zeros preserved.
	* lis: The alphanumeric ID for this legislator found in Senate roll call votes (http://www.senate.gov/pagelayout/legislative/a_three_sections_with_teasers/votes.htm).
	* fec: A *list* of IDs for this legislator in Federal Election Commission data.
	* govtrack: The numeric ID for this legislator on GovTrack.us (stored as an integer).
	* opensecrets: The alphanumeric ID for this legislator on OpenSecrets.org.
	* votesmart: The numeric ID for this legislator on VoteSmart.org (stored as an integer).
	* icpsr: The numeric ID for this legislator in Keith Poole's VoteView.com website, originally based on an ID system by the Interuniversity Consortium for Political and Social Research (stored as an integer).
	* cspan: The numeric ID for this legislator on C-SPAN's video website, e.g. http://www.c-spanvideo.org/person/1745 (stored as an integer).
	* wikipedia: The Wikipedia page name for the person (spaces are given as spaces, not underscores).
	* ballotpedia: The ballotpedia.org page name for the person (spaces are given as spaces, not underscores).
	* opencong: the quoted open congress numeric id from http://www.opencongress.org/ the name is not needed ( http://www.opencongress.org/people/show/412564_Brad_Wenstrup and http://www.opencongress.org/people/show/412564 are both valid )
	* house_history: The numeric ID for this legislator on http://history.house.gov/People/Search/. The ID is present only for members who have served in the U.S. House.
	* bioguide_previous: When bioguide.congress.gov mistakenly listed a legislator under multiple IDs, this field is a *list* of alternative IDs. (This often ocurred for women who changed their name.) The IDs in this list probably were removed from bioguide.congress.gov but might still be in use in the wild.

* name
	* first: The legislator's first name. Sometimes a first initial and period (e.g. in W. Todd Akin), in which case it is suggested to not use the first name for display purposes.
	* middle: The legislator's middle name or middle initial (with period).
	* last: The legislator's last name. Many last names include non-ASCII characters. When building search systems, it is advised to index both the raw value as well as a value with extended characters replaced with their ASCII equivalents (in Python that's: u"".join(c for c in unicodedata.normalize('NFKD', lastname) if not unicodedata.combining(c))).
	* suffix: A suffix on the legislator's name, such as "Jr." or "III".
	* nickname: The legislator's nick name when used as a common alternative to his first name.
	* official_full: The full name of the legislator according to the House or Senate (usually first, middle initial, nickname, last, and suffix). Present for those serving on 2012-10-30 and later.

* other_names, when present, lists other names the legislator has gone by officially. This is helpful in cases where a legislator's legal name has changed. These listings will only include the name attributes which differ from the current name, and a start or end date where applicable. Where multiple names exist, other names are listed chronologically by end date. An excerpted example:

	- id:
		bioguide: B001228
		thomas: '01465'
		govtrack: 400039
		opensecrets: N00007068
	  name:
		first: Mary
		middle: Whitaker
		last: Bono Mack
	  other_names:
	  - last: Bono
		end: '2007-12-17'
	  ...

* bio
	* birthday: The legislator's birthday, in YYYY-MM-DD format.
	* gender: The legislator's gender, either "M" or "F".
	* religion: The legislator's religion.

* terms (one entry for each election)
	* type: The type of the term. Either "sen" for senators or "rep" for representatives and delegates to the House.
	* start: The date the term began (i.e. typically a swearing in), in YYYY-MM-DD format. In contemporary data (>1940), it may be Jan. 3 on odd-numbered years or later if Congress does not meet immediately.
	* end: The date the term ended (because the Congress ended, the legislator died or resigned, etc.). For Members of Congress that served their whole term, starting with the 112th Congress end dates follow the Constitutional end of a Congress, Jan. 3 on odd-numbered years (which is unfortunately the same date the next Congress begins), but prior to the 112th Congress end dates were set to the last date of adjournment of Congress. The end date is the last date on which the legislator served this term.
	* state: The two-letter, uppercase USPS abbreviation for the state that the legislator is serving from. See below.
	* district: For representatives, the district number they are serving from. At-large districts are district 0. In historical data, unknown district numbers are recorded as -1.
	* class: For senators, their election class (1, 2, or 3). Note that this is unrelated to seniority.
	* state_rank: For senators, whether they are the "junior" or "senior" senator (only valid if the term is current, otherwise the senator's rank at the time the term ended).
	* party: The political party of the legislator. If the legislator changed parties, it is typically the most recent party held during the term. This is typically "Democrat", "Independent", or "Republican". The party reflects the partisan caucuses in Congress, and it may differ from the party listed on the ballot during the legislator's election.
	* url: The official website URL of the legislator (only valid if the term is current).
	* address: The mailing address of the legislator's Washington, D.C. office (only valid if the term is current, otherwise the last known address).
	* phone: The phone number of the legislator's Washington, D.C. office (only valid if the term is current, otherwise the last known number).
	* fax: The fax number of the legislator's Washington, D.C. office (only valid if the term is current, otherwise the last known number).
	* contact_form: The website URL of the contact page on the legislator's official website (only valid if the term is current, otherwise the last known URL).
	* office: Similar to the address field, this is just the room and building number, suitable for display (only valid if the term is current, otherwise the last known office).
	* rss_url The URL to the official website's RSS feed (only valid if the term is current, otherwise the last known URL).


**Leadership roles**:

```yaml
leadership_roles:
  - title: Minority Leader
    chamber: senate
    start: '2007-01-04'
    end: '2009-01-06'
```

For members with top formal positions of leadership in each party in each chamber, a `leadership_roles` field will include an array of start/end dates and titles documenting when they held this role.

Leadership terms are not identical to legislative terms, and so start and end dates will be different than legislative term dates. However, leaders do need to be re-elected each legislative term, so their leadership terms should all be subsets of their legislative terms.

Except where noted, fields are omitted when their value is empty or unknown. Any field may be unknown.

Notes:
In most cases, a legislator has a single term on any given date. In some cases a legislator resigned from one chamber and was sworn in in the other chamber on the same day.
Terms for senators list each six-year term, so the terms span three Congresses. For representatives and delegates, each two-year term is listed, each corresponding to a single Congress. But Puerto Rico's Resident Commissioner serves four-year terms, and so the Resident Commissioner will have a single term covering two Congresses (this has not been updated in historical data).

Historically, some states sending at-large representatives actually sent multiple at-large representatives. Thus, state and district may not be a unique key.

Social Media Data Dictionary
----------------------------

The social media file legislators-social-media.yaml stores current social media account information.

Each record has two sections: id and social. The id section identifies the legislator using biogiude, thomas, and govtrack IDs (where available). The social section has social media account identifiers:

* twitter: The current official Twitter handle of the legislator.
* youtube: The current official YouTube username, of the legislator.
* youtube_id: The current official YouTube channel ID of the legislator.
* facebook: The username of the current official Facebook presence of the legislator.
* facebook_id: The numeric ID of the current official Facebook presence of the legislator.

Several legislators do not have an assigned YouTube username.  In these cases, only the youtube_id field is populated.

All values can be turned into URLs by preceding them with the domain name of the service in question:

* `http://twitter.com/[username]`
* `http://youtube.com/user[username]` or http://youtube.com/channel/[channelId]`
* `http://facebook.com/[username or ID]`

Legislators are only present when they have one or more social media accounts known. Fields are omitted when the account is unknown.

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

Additional fields are present on current committee entries (that is, in committees-current.yaml):

* url: The current website URL of the committee.
* address: The mailing address for the committee.
* phone: The phone number of the committee.
* rss_url: The URL for the committee's RSS feed.
* minority_rss_url: The URL for the committee's minority party website's RSS feed.

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

The Executive Branch
--------------------

Because of their role in the legislative process, we also include a file executive.yaml which contains terms served by U.S. presidents (who signed legislation) and U.S. vice presidents (who are nominally the president of the Senate and occassionally cast tie-breaking votes there).

This file has a similar structure as the legislator files. The file contains a list, where each entry is a person. Each entry is a dict with id, name, bio, and terms fields. The id, bio, and name fields are the same as those listed above. Each term has the following fields:

* type: either "prez" (a presidential term) or "viceprez" (a vice presidential term).
* start: The start date of the term. In modern times, typically January 20 following an election year.
* end: The end date of the term. In modern times, typically January 20 following an election year.
* party: The political party from which the person was elected.
* how: How the term came to be, either "election" (the normal case), "succession" (presidential succession), or "appointment" (the appointment by the president of a new vice president).

Presidents and vice presidents that previously served in Congress will also be listed in one of the legislator files, but their Congressional terms will only appear in the legislator files and their executive-branch terms will only appear in executive.yaml.

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

Try updating the House members contact information (mailing address, etc.):

```bash
python house_contacts.py
```

Check whether and how the data has changed:

```bash
git diff ../*.yaml
```

We run the following scripts periodically to scrape for new information and keep the data files up to date. The scripts do not take any command-line arguments.

* `house_contacts.py`: Updates House members' contact information (address, office, and phone fields on their current term, and their official_full name field)
* `house_websites.py`: Updates House members' current website URLs.
* `senate_contacts.py`: Updates senator information (party, class, state_rank, address, office, phone, and contact_form fields on their current term, and their official_full name, bioguide ID, and lis ID fields)
* `committee_membership.py`: Updates committees-current.yaml (name, address, and phone fields for House committees; name and url fields for Senate committees; creates new subcommittees when found with name and thomas_id fields) and writes out a whole new committee-membership-current.yaml file by scraping the House and Senate websites.
* `historical_committees.py`: Updates committees-historical.yaml based on the committees listed on THOMAS.gov, which are committees to which bills have been referred since the 103rd Congress (1973).
* `social_media.py`: Generates leads for Twitter, YouTube, and Facebook accounts for members of Congress by scraping their official websites. Uses a blacklist CSV and a whitelist CSV to manage false positives and negatives.
* `influence_ids.py`: Grabs updated FEC and OpenSecrets IDs from the [Influence Explorer API](http://data.influenceexplorer.com/api). Will only work for members with a Bioguide ID.

Who's Using This Data
---------------------

Here are the ones we know about:

* [GovTrack.us](http://govtrack.us)
* [Sunlight Congress API](http://sunlightlabs.github.com/congress/)
* [Scout](https://scout.sunlightfoundation.com/)
* [The New York Times Congress API](http://developer.nytimes.com/docs/read/congress_api)

Other Scripts
----------------------
The ballotpedia and opencong field has been created using code from James Michael DuPont, which extracts the links from wikipedia and  ballotpedia itself.
To git@github.com:h4ck3rm1k3/rootstrikers-wikipedia.git

