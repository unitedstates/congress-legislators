# -*- coding: utf-8 -*-
import requests
from bs4 import BeautifulSoup


url = requests.get("http://history.house.gov/Institution/Party-Divisions/Party-Divisions/")
soup = BeautifulSoup(url.content, 'html.parser')


table = soup.select('table')[0]
links = []
for a in table.find_all('a', href = True):
    links.append(a['href'])
links = [x for x in links if '/Congressional-Overview/Profiles/' in x]    
    
congress_dictionary = {}

for link in links:
    base = 'http://history.house.gov/'
    url = base + link
    url = requests.get(url)
    soup = BeautifulSoup(url.content, 'html.parser')
    div = soup.find('div', {'id':'divResults'})
    congress = div.find('h2').contents[0].replace('\r','').replace('\n','').strip().split(' ')[0]
    congress = int(congress[:-2])
    
    dictionary = {
                    'Total Membership':{},
                    'Party Divisions':{},
                    'Leadership and Officers':{}
                  }
    for child in div.children:
        try:
            if child.contents[0] == 'Total Membership:':
                membs = child.find_next('ul')
                reps = membs.findAll('li')
                for rep in reps:
                    clean_rep = str(rep.text).strip().split(' ')
                    number = clean_rep[0]
                    tipo = ' '.join(clean_rep[1:])
                    dictionary['Total Membership'].update({tipo:number})
        except: pass
        try:
            if child.contents[0] == 'Party Divisions:':    
                pd = child.find_next('ul')
                for li in pd.children:
                    try:
                        number = li.contents[0].split(' ')[0].strip()
                        party = str(' '.join([x.strip() for x in li.contents[0].split(' ')][1:]).strip())
                        dictionary['Party Divisions'].update({party:number})
                    except:pass
        except: pass
    
    
    lo = div.find('a', attrs={'name':'leadership-and-fficers'}).find_next('div')
    
    for positions, persons in zip(lo.findAll('dt'),lo.findAll('dd')):
        position = str(positions.text).replace(':','')
        #get rid of supserscripts
        try:
            for item in persons.findAll('sup'):
                item.decompose()
        except:pass
        # there may be more than one person per position, this cleans that up
        person = list(filter(None,str(persons.text).strip().split('    ')))
        person_clean = []
        for p in person:
            person_clean.append(p.replace('\r','').replace('\n','').strip())
        dictionary['Leadership and Officers'].update({position:person_clean})
        
    congress_dictionary.update({congress:dictionary})
    
    
