=========
scrapelib
=========

scrapelib is a library for making requests to websites, particularly those
that may be less-than-reliable.

scrapelib originated as part of the `Open States <http://openstates.org/>`_
project to scrape the websites of all 50 state legislatures and as a result
was therefore designed with features desirable when dealing with sites that
have intermittent errors or require rate-limiting.

As of version 0.7 scrapelib has been retooled to take advantage of the superb
`requests <http://python-requests.org>`_ library.

Advantages of using scrapelib over alternatives like httplib2 simply using
requests as-is:

* All of the power of the suberb `requests <http://python-requests.org>`_ library.
* HTTP, HTTPS, and FTP requests via an identical API
* support for simple caching with pluggable cache backends
* request throttling
* configurable retries for non-permanent site failures
* optional robots.txt compliance

scrapelib is a project of Sunlight Labs (c) 2013.
All code is released under a BSD-style license, see LICENSE for details.

Written by James Turk <jturk@sunlightfoundation.com>

Contributors:
    * Michael Stephens - initial urllib2/httplib2 version
    * Joe Germuska - fix for IPython embedding
    * Alex Chiang - fix to test suite


Requirements
============

* python 2.7 or 3.3
* requests >= 1.0

Installation
============

scrapelib is available on PyPI and can be installed via ``pip install scrapelib``

PyPI package: http://pypi.python.org/pypi/scrapelib

Source: http://github.com/sunlightlabs/scrapelib

Documentation: http://scrapelib.readthedocs.org/en/latest/

Example Usage
=============

::

  import scrapelib
  s = scrapelib.Scraper(requests_per_minute=10, allow_cookies=True,
                        follow_robots=True)

  # Grab Google front page
  s.urlopen('http://google.com')

  # Will raise RobotExclusionError
  s.urlopen('http://google.com/search')

  # Will be throttled to 10 HTTP requests per minute
  while True:
      s.urlopen('http://example.com')
