#!/usr/bin/env python
#coding: utf-8
__author__ = 'stsmith'

# congress_lookup: Look up information about congress from the congress-legislators database
# See: https://github.com/unitedstates/congress-legislators and https://github.com/TheWalkers/congress-legislators

# The project is in the public domain within the United States, and
# copyright and related rights in the work worldwide are waived
# through the CC0 1.0 Universal public domain dedication.

# Author 2017 Steven T. Smith <steve dot t dot smith at gmail dot com>

import argparse as ap, contextlib, errno, fnmatch, os, urllib2, urlparse, yaml

class CongressLookup:
    '''A class used to lookup legislator properties from the github congress-legislators YAML database.'''

    def __init__(self):
        self.args = self.parseArgs()
        self.data_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),self.args.data_dir)
        self.properties = dict()
        self.database_load()
        for prop in self.args.properties: self.lookup_property(prop)

    def parseArgs(self):
        parser = ap.ArgumentParser()
        parser.add_argument('properties', metavar='PROPS', type=str, nargs='+',
                            help='Properties to look up')
        parser.add_argument('-c', '--committee', help="Committee name (wildcard)", type=str, default=None)
        parser.add_argument('-n', '--last-name', help="Last name of legislator (wildcard)", type=str, default=None)
        parser.add_argument('-d', '--data-dir', help="Database directory", type=str, default='.')
        parser.add_argument('-r', '--repo', help="GitHub repo URL", type=str, default='https://github.com/essandess/congress-legislators/')
        parser.add_argument('-D', '--download', help="Download data", action='store_true', default=True)
        parser.add_argument('-g', '--debug', help="Debug flag", action='store_true')
        return parser.parse_args()

    def lookup_property(self,property):
        if self.args.committee is not None:
            self.lookup_by_committee(property)
        if self.args.last_name is not None:
            self.lookup_by_lastname(property)

    def lookup_by_committee(self,property):
        for comm in (comm for comm in self.committees if self.inclusive_wildcard_match(comm['name'],self.args.committee)):
            if self.args.debug: print(comm)
            print('"{}" member properties:'.format(comm['name'].encode('utf-8')))
            members = self.membership[comm['thomas_id']] if comm['thomas_id'] in self.membership else []
            for member in members: self.lookup_by_member(property,member)

    def inclusive_wildcard_match(self,name,pat):
        if any(c in pat for c in '*?[]'):	# a wildcard pattern
            # prepend or append a * for inclusiveness if not already there
            if pat[0] is not '*': pat = '*' + pat
            if pat[-1] is not '*': pat = pat + '*'
        else:					# not a wildcard
            pat = '*' + pat + '*'
        return fnmatch.fnmatch(name,pat)

    def lookup_by_member(self,property,member):
        for leg in ( leg for leg in self.legislators if \
                    (leg['name']['official_full'] == member['name']) \
                    or ('bioguide' in leg['id'] and leg['id']['bioguide'] == member['bioguide']) \
                    or ('thomas' in leg['id'] and leg['id']['thomas'] == member['thomas']) ):
            self.lookup_legislator_properties(property,leg)

    def lookup_by_lastname(self,property):
        for leg in (leg for leg in self.legislators if fnmatch.fnmatch(leg['name']['last'],self.args.last_name)):
            if self.args.debug: print(leg)
            self.lookup_legislator_properties(property,leg)

    def lookup_legislator_properties(self,property,legislator):
        self.properties[property] = [term[property] for term in legislator['terms'] if property in term and len(term[property]) > 0]
        for off in self.offices:
            if self.args.debug: print(off)
            if any(off['id'][db] == legislator['id'][db] for db in off['id'] if db in off['id'] and db in legislator['id']):
                self.properties[property] += [ok[property] for ok in off['offices'] if property in ok and len(ok[property]) > 0]
                break
        print('Property \'{}\' for {}:'.format(property,legislator['name']['official_full'].encode('utf-8')))
        print('\n'.join(self.properties[property]))

    def database_load(self):
        try:
	    with self.database_access('legislators-current.yaml') as y:
    	        self.legislators = yaml.load(y, Loader=yaml.CLoader)
            with self.database_access('legislators-district-offices.yaml') as y:
                self.offices = yaml.load(y, Loader=yaml.CLoader)
            if self.args.committee is not None:
                with self.database_access('committees-current.yaml') as y:
                    self.committees = yaml.load(y, Loader=yaml.CLoader)
                with self.database_access('committee-membership-current.yaml') as y:
                    self.membership = yaml.load(y, Loader=yaml.CLoader)
            else:
                self.committees = None
        except (BaseException,IOError) as e:
            print(e)
            raise Exception('Clone data from {} and copy it to {}.'.format(self.args.repo,self.data_path))

    def database_access(self,filename):
        if self.args.download:
            if self.args.repo[-1] != '/': self.args.repo += '/'
            url_base = urlparse.urljoin(urlparse.urlunparse(urlparse.urlparse(self.args.repo)._replace(netloc='raw.githubusercontent.com')),'master/')
            # contextlib required for urlopen in with ... as for v < 3.3
            res = contextlib.closing(urllib2.urlopen( urlparse.urljoin(url_base,filename) ))
        else:
            res = open(os.path.join(self.data_path,filename),'r')
        return res        

if __name__ == "__main__":
    res = CongressLookup()
