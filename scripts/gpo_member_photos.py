#!/usr/bin/env python
"""
Scrape http://www.memberguide.gpoaccess.gov and save members' photos named after their Bio IDs.
"""
import argparse
from BeautifulSoup import BeautifulSoup # pip install BeautifulSoup
import mechanize # pip install mechanize
import os
import re
import urlparse

# TODO could download http://unitedstates.sunlightfoundation.com/legislators/legislators.csv directly when needed

def get_front_page(br, congress_number):
    url = r'http://www.memberguide.gpoaccess.gov/GetMembersSearch.aspx'
    links = []

    ######################################
    # First, open the page to get the form
    ######################################
    br.set_handle_robots(False)   # no robots
    br.set_handle_refresh(False)  # can sometimes hang without this
    br.addheaders = [('User-agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1')]

    print "Open..."
    response = br.open(url).read()

    # print response.read()      # the text of the page
    print 'href="' + congress_number in response
    # print response

    ##############################
    # Next, choose congress number
    ##############################
    br.select_form(nr=0)
    br.set_all_readonly(False)      # allow everything to be written to
    form = br.form
    form.set_all_readonly(False)    # allow everything to be written to

    for control in br.form.controls:
        if control.name == "ctl00_ContentPlaceHolder1_Memberstelerikrid_ctl00_ctl02_ctl00_GoToPageTextBox_ClientState":
            print "ctl00_ContentPlaceHolder1_Memberstelerikrid_ctl00_ctl02_ctl00_GoToPageTextBox_ClientState"
            print control
            print "type=", control.type
            print "name=", control.name
            print "value=", br[control.name]
        # print control
        # print "type=%s, name=%s value=%s" % (control.type, control.name, br[control.name])    
    # end
    
    # The only submit button is "Clear Search" and we don't want to do that!
    for control in br.form.controls:
        if control.name == "ctl00$ContentPlaceHolder1$btnClear":
            control.disabled = True
            break

    # The search button is hooked up to a Javascript __doPostBack() function that sets __EVENTTARGET
    # control = form.find_control("__EVENTTARGET")
    print br['__EVENTTARGET']
    br['__EVENTTARGET']='ctl00$ContentPlaceHolder1$btnSearch'
    print br['__EVENTTARGET']

    # Set the congress session number
    print br['ctl00$ContentPlaceHolder1$ddlCongressSession']
    br['ctl00$ContentPlaceHolder1$ddlCongressSession']=[congress_number] # Use a list for select controls with multiple values
    print br['ctl00$ContentPlaceHolder1$ddlCongressSession']

    print "Submit..."
    response = br.submit().read()

    print 'href="' + congress_number in response
    br.select_form(nr=0)
    form = br.form
    print br['ctl00$ContentPlaceHolder1$ddlCongressSession']

    # TODO could change members-per-page so we don't need to keep clicking next
    
    #############################
    # Choose next page until done
    #############################
    keep_going = True
    
    last_page = None
    this_page = br['ctl00$ContentPlaceHolder1$Memberstelerikrid$ctl00$ctl03$ctl01$GoToPageTextBox']

    while(last_page != this_page):

        # Harvest links
        for link in br.links():
            if congress_number + "/" in link.url:
                print link.text, link.url
                links.append(link)
        print "Page:", br['ctl00$ContentPlaceHolder1$Memberstelerikrid$ctl00$ctl03$ctl01$GoToPageTextBox']
        print "Links:", len(links)

        # return links # TEMP!!! TODO!!! for testing

        br.select_form(nr=0)
        br.set_all_readonly(False)      # allow everything to be written to
        form = br.form
        form.set_all_readonly(False)    # allow everything to be written to

        # The only submit button is "Clear Search" and we don't want to do that!
        for control in br.form.controls:
            if control.name == "ctl00$ContentPlaceHolder1$btnClear":
                control.disabled = True
                break

        # The search button is hooked up to a Javascript __doPostBack() function that sets __EVENTTARGET
        # control = form.find_control("__EVENTTARGET")
        print br['__EVENTTARGET']
        br['__EVENTTARGET']='ctl00$ContentPlaceHolder1$Memberstelerikrid$ctl00$ctl02$ctl00$ctl28'
        print br['__EVENTTARGET']

        print "Submit..."
        response = br.submit().read()

        print "href=\"112" in response
        print 'href="' + congress_number in response
        br.select_form(nr=0)
        form = br.form
        print br['ctl00$ContentPlaceHolder1$ddlCongressSession']

        print br['ctl00$ContentPlaceHolder1$Memberstelerikrid$ctl00$ctl02$ctl00$ChangePageSizeTextBox']
        print br['ctl00$ContentPlaceHolder1$Memberstelerikrid$ctl00$ctl03$ctl01$ChangePageSizeTextBox']
        
        last_page = this_page
        this_page = br['ctl00$ContentPlaceHolder1$Memberstelerikrid$ctl00$ctl03$ctl01$GoToPageTextBox']

    ###########################################
    # Done, return links for further processing
    ###########################################
    return links

    
def download_photos(br, member_links, outdir):
    print "Found a total of", len(member_links), "links"
    if not os.path.exists(outdir):
        os.makedirs(outdir)

    todo_resolve = []
    for i, member_link in enumerate(member_links):
        print "---"
        print "Processing member", i+1, "of", len(member_links), ":", member_link.text
        bio_id = None
        
        response = br.follow_link(member_link)
        print response.geturl()
        # print response.read()
        
        for link in br.links():
            if "bioguide.congress.gov" in link.url:
                # print link.text, link.url
                bio_id = urlparse.parse_qs(urlparse.urlparse(link.url).query)['index'][0].strip("/")
                break

        # if not bio_id:
            # TODO resolve name using congress-legislators data, using the 
            # last name, state, and chamber for disambiguation where needed

        if bio_id:
            print "Bio ID:", bio_id
            soup = BeautifulSoup(response.read())
            image_tags = soup.findAll('img')
            
            for image in image_tags: # TODO: ok for now as only one image on the page
                filename = os.path.join(outdir, bio_id + ".jpg") # TODO: correct to assume jpg?
                if os.path.isfile(filename):
                    print "Image already exists:", filename
                elif not args.test:
                    print "Saving image to", filename
                    data = br.open(image['src']).read()
                    br.back()
                    save = open(filename, 'wb')
                    save.write(data)
                    save.close()
                break
        else:
            print "Bio ID not found"
            todo_resolve.append(member_link)

    # TODO For each entry here, need to add a resolving case above
    print "Didn't have bio IDs:", len(todo_resolve)
    for member_link in todo_resolve:
        print member_link.text, member_link.url

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Scrape http://www.memberguide.gpoaccess.gov and save members' photos named after their Bio IDs", 
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-c', '--congress', default='113',
        help="Congress session number, for example: 110, 111, 112, 113")
    parser.add_argument('-o', '--outdir', default="images",
        help="Directory to save photos in")
    parser.add_argument('-t', '--test', action='store_true',
        help="Test mode: don't actually save images")
    args = parser.parse_args()

    br = mechanize.Browser()
    member_links = get_front_page(br, args.congress)
    download_photos(br, member_links, args.outdir)

# End of file
