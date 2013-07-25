import logging
import os
import sys
import tempfile
import time

import requests
from .cache import CachingSession, FileCache    # noqa

if sys.version_info[0] < 3:         # pragma: no cover
    from urllib2 import urlopen as urllib_urlopen
    from urllib2 import URLError as urllib_URLError
    import urlparse
    import robotparser
    _str_type = unicode
else:                               # pragma: no cover
    PY3K = True
    from urllib.request import urlopen as urllib_urlopen
    from urllib.error import URLError as urllib_URLError
    from urllib import parse as urlparse
    from urllib import robotparser
    _str_type = str

__version__ = '0.9.0'
_user_agent = ' '.join(('scrapelib', __version__,
                        requests.utils.default_user_agent()))


class NullHandler(logging.Handler):
    def emit(self, record):
        pass

_log = logging.getLogger('scrapelib')
_log.addHandler(NullHandler())


class RobotExclusionError(requests.RequestException):
    """
    Raised when an attempt is made to access a page denied by
    the host's robots.txt file.
    """

    def __init__(self, message, url, user_agent):
        super(RobotExclusionError, self).__init__(message)
        self.url = url
        self.user_agent = user_agent


class HTTPMethodUnavailableError(requests.RequestException):
    """
    Raised when the supplied HTTP method is invalid or not supported
    by the HTTP backend.
    """

    def __init__(self, message, method):
        super(HTTPMethodUnavailableError, self).__init__(message)
        self.method = method


class HTTPError(requests.HTTPError):
    """
    Raised when urlopen encounters a 4xx or 5xx error code and the
    raise_errors option is true.
    """

    def __init__(self, response, body=None):
        message = '%s while retrieving %s' % (response.status_code,
                                              response.url)
        super(HTTPError, self).__init__(message)
        self.response = response
        self.body = body or self.response.text


class FTPError(requests.HTTPError):
    def __init__(self, url):
        message = 'error while retrieving %s' % url
        super(FTPError, self).__init__(message)


class ResultStr(_str_type):
    """
    Wrapper for responses.  Can treat identically to a ``str``
    to get body of response, additional headers, etc. available via
    ``response`` attribute.
    """
    def __new__(cls, scraper, response, requested_url):
        try:
            self = _str_type.__new__(cls, response.text)
        except TypeError:
            # use UTF8 as a default encoding if one couldn't be guessed
            response.encoding = 'utf8'
            self = _str_type.__new__(cls, response.text)
        self._scraper = scraper
        self.bytes = response.content
        self.encoding = response.encoding
        self.response = response
        # augment self.response
        #   manually set: requested_url
        #   aliases: code -> status_code
        self.response.requested_url = requested_url
        self.response.code = self.response.status_code
        return self


class ThrottledSession(requests.Session):
    def _throttle(self):
        now = time.time()
        diff = self._request_frequency - (now - self._last_request)
        if diff > 0:
            _log.debug("sleeping for %fs" % diff)
            time.sleep(diff)
            self._last_request = time.time()
        else:
            self._last_request = now

    @property
    def requests_per_minute(self):
        return self._requests_per_minute

    @requests_per_minute.setter
    def requests_per_minute(self, value):
        if value > 0:
            self._throttled = True
            self._requests_per_minute = value
            self._request_frequency = 60.0 / value
            self._last_request = 0
        else:
            self._throttled = False
            self._requests_per_minute = 0
            self._request_frequency = 0.0
            self._last_request = 0

    def request(self, method, url, **kwargs):
        if self._throttled:
            self._throttle()
        return super(ThrottledSession, self).request(method, url, **kwargs)


class RobotsTxtSession(requests.Session):

    def __init__(self):
        super(RobotsTxtSession, self).__init__()
        self._robot_parsers = {}
        self.follow_robots = True

    def _robot_allowed(self, user_agent, parsed_url):
        _log.info("checking robots permission for %s" % parsed_url.geturl())
        robots_url = urlparse.urljoin(parsed_url.scheme + "://" +
                                      parsed_url.netloc, "robots.txt")

        try:
            parser = self._robot_parsers[robots_url]
            _log.info("using cached copy of %s" % robots_url)
        except KeyError:
            _log.info("grabbing %s" % robots_url)
            parser = robotparser.RobotFileParser()
            parser.set_url(robots_url)
            parser.read()
            self._robot_parsers[robots_url] = parser

        return parser.can_fetch(user_agent, parsed_url.geturl())

    def request(self, method, url, **kwargs):
        parsed_url = urlparse.urlparse(url)
        user_agent = (kwargs.get('headers', {}).get('User-Agent') or
                      self.headers.get('User-Agent'))
        # robots.txt is http-only
        if (parsed_url.scheme in ('http', 'https') and
                self.follow_robots and
                not self._robot_allowed(user_agent, parsed_url)):
            raise RobotExclusionError(
                "User-Agent '%s' not allowed at '%s'" % (
                    user_agent, url), url, user_agent)

        return super(RobotsTxtSession, self).request(method, url, **kwargs)


# this object exists because Requests assumes it can call
# resp.raw._original_response.msg.getheaders() and we need to cope with that
class DummyObject(object):
    def getheaders(self, name):
        return ''

    def get_all(self, name, default):
        return default

_dummy = DummyObject()
_dummy._original_response = DummyObject()
_dummy._original_response.msg = DummyObject()


class FTPAdapter(requests.adapters.BaseAdapter):

    def send(self, request, stream=False, timeout=None, verify=False,
             cert=None, proxies=None):
        if request.method != 'GET':
            raise HTTPMethodUnavailableError(
                "FTP requests do not support method '%s'" % request.method,
                request.method)
        try:
            real_resp = urllib_urlopen(request.url, timeout=timeout)
            # we're going to fake a requests.Response with this
            resp = requests.Response()
            resp.status_code = 200
            resp.url = request.url
            resp.headers = {}
            resp._content = real_resp.read()
            resp.raw = _dummy
            return resp
        except urllib_URLError:
            raise FTPError(request.url)


class RetrySession(requests.Session):

    def __init__(self):
        super(RetrySession, self).__init__()
        self._retry_attempts = 0
        self.retry_wait_seconds = 10

    # retry_attempts is a property so that it can't go negative
    @property
    def retry_attempts(self):
        return self._retry_attempts

    @retry_attempts.setter
    def retry_attempts(self, value):
        self._retry_attempts = max(value, 0)

    def accept_response(self, response, **kwargs):
        return response.status_code < 400

    def request(self, method, url, retry_on_404=False, **kwargs):
        # the retry loop
        tries = 0
        exception_raised = None

        while tries <= self.retry_attempts:
            exception_raised = None

            try:
                resp = super(RetrySession, self).request(method, url, **kwargs)
                # break from loop on an accepted response
                if self.accept_response(resp) or (resp.status_code == 404
                                                  and not retry_on_404):
                    break

            except (requests.HTTPError, requests.ConnectionError,
                    requests.Timeout) as e:
                exception_raised = e

            # if we're going to retry, sleep first
            tries += 1
            if tries <= self.retry_attempts:
                # twice as long each time
                wait = (self.retry_wait_seconds * (2 ** (tries - 1)))
                _log.debug('sleeping for %s seconds before retry' % wait)
                time.sleep(wait)

        # out of the loop, either an exception was raised or we had a success
        if exception_raised:
            raise exception_raised
        else:
            return resp


# compose sessions, order matters
class Scraper(RobotsTxtSession,    # first, check robots.txt
              ThrottledSession,    # throttle requests
              CachingSession,      # cache responses
              RetrySession,        # do retries
              ):
    """
    Scraper is the most important class provided by scrapelib (and generally
    the only one to be instantiated directly).  It provides a large number
    of options allowing for customization.

    Usage is generally just creating an instance with the desired options and
    then using the :meth:`urlopen` & :meth:`urlretrieve` methods of that
    instance.

    :param raise_errors: set to True to raise a :class:`HTTPError`
        on 4xx or 5xx response
    :param requests_per_minute: maximum requests per minute (0 for
        unlimited, defaults to 60)
    :param follow_robots: respect robots.txt files (default: True)
    :param retry_attempts: number of times to retry if timeout occurs or
        page returns a (non-404) error
    :param retry_wait_seconds: number of seconds to retry after first failure,
        subsequent retries will double this wait
    """
    def __init__(self,
                 raise_errors=True,
                 requests_per_minute=60,
                 follow_robots=True,
                 retry_attempts=0,
                 retry_wait_seconds=5,
                 header_func=None):

        super(Scraper, self).__init__()
        self.mount('ftp://', FTPAdapter())

        # added by this class
        self.raise_errors = raise_errors

        # added by ThrottledSession
        self.requests_per_minute = requests_per_minute

        # added by RobotsTxtSession
        self.follow_robots = follow_robots

        # added by RetrySession
        self.retry_attempts = retry_attempts
        self.retry_wait_seconds = retry_wait_seconds

        # added by this class
        self._header_func = header_func

        # added by CachingSession
        self.cache_storage = None
        self.cache_write_only = True

        # non-parameter options
        self.timeout = None
        self.user_agent = _user_agent

    @property
    def user_agent(self):
        return self.headers['User-Agent']

    @user_agent.setter
    def user_agent(self, value):
        self.headers['User-Agent'] = value

    @property
    def disable_compression(self):
        return self.headers['Accept-Encoding'] == 'text/*'

    @disable_compression.setter
    def disable_compression(self, value):
        # disabled: set encoding to text/*
        if value:
            self.headers['Accept-Encoding'] = 'text/*'
        # enabled: if set to text/* pop, otherwise leave unmodified
        elif self.headers.get('Accept-Encoding') == 'text/*':
            self.headers['Accept-Encoding'] = 'gzip, deflate, compress'

    def request(self, method, url, **kwargs):
        # apply global timeout
        timeout = kwargs.pop('timeout', self.timeout)

        if self._header_func:
            headers = requests.structures.CaseInsensitiveDict(
                self._header_func(url))
        else:
            headers = {}
        try:
            # requests < 1.2.2
            headers = requests.sessions.merge_kwargs(headers, self.headers)
            headers = requests.sessions.merge_kwargs(kwargs.pop('headers', {}),
                                                     headers)
        except AttributeError:
            # requests >= 1.2.2
            headers = requests.sessions.merge_setting(headers, self.headers)
            headers = requests.sessions.merge_setting(
                kwargs.pop('headers', {}), headers)

        return super(Scraper, self).request(method, url, timeout=timeout,
                                            headers=headers, **kwargs)

    def urlopen(self, url, method='GET', body=None, retry_on_404=False):
        """
            Make an HTTP request and return a :class:`ResultStr` object.

            If an error is encountered may raise any of the scrapelib
            `exceptions`_.

            :param url: URL for request
            :param method: any valid HTTP method, but generally GET or POST
            :param body: optional body for request, to turn parameters into
                an appropriate string use :func:`urllib.urlencode()`
            :param retry_on_404: if retries are enabled, retry if a 404 is
                encountered, this should only be used on pages known to exist
                if retries are not enabled this parameter does nothing
                (default: False)
        """

        _log.info("{0} - {1}".format(method.upper(), url))

        resp = self.request(method, url, data=body, retry_on_404=retry_on_404)

        if self.raise_errors and not self.accept_response(resp):
            raise HTTPError(resp)
        else:
            return ResultStr(self, resp, url)

    def urlretrieve(self, url, filename=None, method='GET', body=None):
        """
        Save result of a request to a file, similarly to
        :func:`urllib.urlretrieve`.

        If an error is encountered may raise any of the scrapelib
        `exceptions`_.

        A filename may be provided or :meth:`urlretrieve` will safely create a
        temporary file.  Either way it is the responsibility of the caller
        to ensure that the temporary file is deleted when it is no longer
        needed.

        :param url: URL for request
        :param filename: optional name for file
        :param method: any valid HTTP method, but generally GET or POST
        :param body: optional body for request, to turn parameters into
            an appropriate string use :func:`urllib.urlencode()`
        :returns filename, response: tuple with filename for saved
            response (will be same as given filename if one was given,
            otherwise will be a temp file in the OS temp directory) and
            a :class:`Response` object that can be used to inspect the
            response headers.
        """
        result = self.urlopen(url, method, body)

        if not filename:
            fd, filename = tempfile.mkstemp()
            f = os.fdopen(fd, 'wb')
        else:
            f = open(filename, 'wb')

        f.write(result.bytes)
        f.close()

        return filename, result.response


_default_scraper = Scraper(follow_robots=False, requests_per_minute=0)


def urlopen(url, method='GET', body=None):  # pragma: no cover
    return _default_scraper.urlopen(url, method, body)
