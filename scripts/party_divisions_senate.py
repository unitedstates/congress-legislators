# -*- coding: utf-8 -*-
import requests
from bs4 import BeautifulSoup
from collections import OrderedDict
import re

def party_grab(party_line):
    party = party_line.split(':')[1]
    party = ''.join([i for i in party if not i.isdigit()]).strip()
    party = party.replace('&', 'and').split('(')[0].strip()
    return party


def get_indices(pattern, html):
    soup_string = str(html)
    start = [x.start() for x in re.finditer(pattern, soup_string) ]
    end = [x.end() for x in re.finditer(pattern, soup_string) ]
    html_index = []
    for index, value in enumerate(start[:-1]):
        html_index.append((value, end[index], start[index+1]))
    html_index.append((start[-1], end[-1], len(soup_string)))
    return html_index


def create_cong_dict(congress_list_data):
    maj_party = party_grab(c_data[0])
    maj_seats = c_data[0].split('(')[-1].split(' seats')[0]
    int(''.join([i for i in c_data[0] if i.isdigit()]))
    min_party = party_grab(c_data[1])
    min_seats = int(''.join([i for i in c_data[1] if i.isdigit()]))
    total_seats = int(''.join([i for i in c_data[3] if i.isdigit()]))
    
    c_dictionary['Party Divisions'].update({maj_party:maj_seats,
                                            min_party:min_seats})
    c_dictionary['Total Membership'].update({'Senators':total_seats})
    other_parties = c_data[2].split(':')[1].split(';')
    for party in other_parties:
        p = party.strip()
        seats = int(''.join([i for i in p if i.isdigit()]))
        party = ''.join([i for i in p if not i.isdigit()]).strip()
        if party:
            c_dictionary['Party Divisions'].update({party:seats})
    return c_dictionary

site = r'https://www.senate.gov/history/partydiv.htm'
url = requests.get(site)
soup = BeautifulSoup(url.content, 'html.parser')    
div_content = soup.find('div', attrs={'class':'contenttext'})


pattern = r'\d{1,3}[a-z]{2}\sCongress\s\(\d{4}-\d{4}\)'


html_index = get_indices(pattern, soup)


senate_dictionary = OrderedDict()
soup_string = str(soup)
for index in html_index:
    c_dictionary = {
            'Party Divisions':{},
            'Total Membership':{}
            }
    s = index[0]
    e = index[2]
    congress_end = index[1]
    cong = soup_string[s:congress_end]
    cong = cong.split('(')[0]
    cong = int(''.join([i for i in cong if i.isdigit()]))
    new_soup = BeautifulSoup(soup_string[s:e], 'html.parser')
            
    if cong == 107:
        new_soup = str(new_soup).split('_____')
        for s in new_soup:
           period = BeautifulSoup(s, 'html.parser')
           c_data = [x.contents for x in period.find_all('p')]
           c_data = [x[0] for x in c_data if x]
           date = c_data[0].split(":")[0].split('(')[1].replace(')','')
           maj_party = party_grab(c_data[0])
           maj_seats = int(''.join([i for i in c_data[0].split(":")[1] if i.isdigit()]))
           min_party = party_grab(c_data[1])
           min_seats = int(''.join([i for i in c_data[1] if i.isdigit()]))
           total_seats = [x for x in c_data if "Total" in x][0]
           total_seats = int(''.join([i for i in total_seats if i.isdigit()]))
           c_dictionary['Party Divisions'].update({date:{maj_party:maj_seats,
                                                    min_party:min_seats}})
           c_dictionary['Total Membership'].update({date:{'Senators':total_seats}})
        senate_dictionary.update({cong:c_dictionary})

    else:
        try:
            if index == html_index[-1]:
                c_data = [x.strip() for x in str(new_soup).split('<br/>')]
                for i,d in enumerate(c_data):
                     
                    if d[:4] == 'Note' or d[:4] == 'Tota':
                        dex = i
                c_data = c_data[:dex+1]
                
            else: c_data = [x.contents[0] for x in new_soup.find_all('p')]
            footnote = False
            for d in c_data:
               
                if d[:4] == 'Note':
                    footnote = d.split(':')[1]
                    break
            try:
                maj_party = party_grab(c_data[0])
            except:
                c_data = str(new_soup).split('<br/>')
                c_data = [x.strip() for x in c_data][1:]
                maj_party = party_grab(c_data[0])
            maj_seats = int(''.join([i for i in c_data[0] if i.isdigit()]))
            min_party = party_grab(c_data[1])
            min_seats = int(''.join([i for i in c_data[1] if i.isdigit()]))
            total_seats = [x for x in c_data if "Total" in x][0]
            total_seats = int(''.join([i for i in total_seats if i.isdigit()]))
            
            c_dictionary['Party Divisions'].update({maj_party:maj_seats,
                                                    min_party:min_seats})
            c_dictionary['Total Membership'].update({'Senators':total_seats})
            other_parties = c_data[2].split(':')[1].split(';')
            caucus = False
            for party in other_parties:
                if 'both' in party:
                    both = True
                    if 'Democrat' in party: caucus = 'Democrat'
                    elif 'Republican' in party: caucus = 'Republican'
                else: both = False
            for party in other_parties:
                p = party.strip()
                seats = int(''.join([i for i in p if i.isdigit()]))
                party = ''.join([i for i in p if not i.isdigit()]).strip()
                party = party.replace('( seat)', '')
                try:
                    note = party[party.index('(')+1:party.index(')')]
                    
                    
                    if 'Democrat' in note: caucus = 'Democrat'
                    elif 'Republican' in note: caucus = 'Republican'
            
                    party = party[:party.index('(')]
                except:
                    note = False
                
                if party:
                    party = party.strip()
                    c_dictionary['Party Divisions'].update({party:seats})
                    if caucus:
                        try:
                            c_dictionary['Party Divisions']['caucus'].update({party:caucus})
                        except:
                            c_dictionary['Party Divisions'].update({'caucus':{party:caucus}})
            if footnote:
                c_dictionary.update({'footnote':footnote.strip()})
        except:
            print(cong)
        senate_dictionary.update({cong:c_dictionary})


