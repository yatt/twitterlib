#!/usr/bin/python2.6
# coding: utf-8

#
# =============================================
#       WARNING (for CPython version < 2.6.3)
# =============================================
# because of intepreter bug, SSL connection
# over http proxy will failure.
# 
# see : http://www.python.org/getit/releases/2.6.3/NEWS.txt
# > - Issue #1424152: Fix for httplib, urllib2 to support SSL while working through
# >   proxy. Original patch by Christopher Li, changes made by Senthil Kumaran.
#
#

import os
import uuid
import time
import hmac
import hashlib
import cgi


import sys
py3 = sys.version_info[0] == 3
if not py3:
    import urllib
    import urllib2
    import cookielib
else:
    import urllib
    import urllib.request as urllib2
    import urllib.parse
    import http
    
    import http.cookiejar as cookielib
    urllib.urlencode = urllib.parse.urlencode

# json
try:
    # python2.6 and later
    import json
except:
    try:
        # for gae
        from django.utils import simplejson as json
    except:
        # python2.5
        import simplejson as json

# え、効かないけど・・・
#import socket
#socket.setdefaulttimeout(1)

#
# class MyClient(TwitterOAuth):
#     atokpath = './myclient_access_token.txt'
#     def loadAccessToken(self):
#         fp = open(MyClient.atokpath)
#         atok,asec = fp.read().split()
#         fp.close()
#         return atok, asec
#     def saveAccessToken(self, atok, asec):
#         fp = open(MyClient.atokpath, 'w')
#         fp.write()
#         fp.close()
#     def verify(self, url):
#         print 'access url below and input pin code: ', url
#         pin = raw_input('input pin code')
#         return pin
#     def getAccount(self):
#         msgbox('input username and password')
#         username,password = fp.read().split()
#         return (username, password)
#
#  api = API(MyClient(consumer_key, consumer_secret, use_https=True))
#  api.auth()
#  api.update('tweet from my client.')
#  for user in api.follower:
#      print user.id
#


# =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
# Note: Twitter OAuth Authorization Sequence
# =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
# 1. developer register application to twitter at
#    http://twitter.com/apps and get consumer 
#    key/secret
# 2. application access /oauth/request_token and
#    get request token 
# 2*. IF APP IS ON WEB  set `oauth_callback' parameter
#    check whether your app setting is `browser client'
#    (not `desktop client')
# 3. application display url to /oauth/authorize.
#    application set `oauth_token' to HTTP GET 
#    parameter.
#    user access twitter.com and allow application
#    to access user information.
#    then twitter issue `pin code' to user, which
#    is required to get access token.
# 4. application get access token from
#    /oauth/access_token
# 5. now the application has permission to R or 
#    R/W user information.
#

class Token(object):
    def __init__(self, tok, sec):
        self.tok = tok
        self.sec = sec

#
# +--------------+
# |     User     |
# +--------------+
#     |     |  apicall
#    str  conn
#     |     | (streaming)
# +--------------+
# |     API      |
# +--------------+
#        |     apicall
#       conn
#        |
# +--------------+
# | TwitterOAuth |
# +--------------+
#        |
# +-----------------------+
# |   Internet            |
# +-----------------------+
#

import sys
import codecs
ENC = {'win32':'cp932'}.get(sys.platform, 'utf-8')
class Logger(object):
    def __init__(self, level=1, out=codecs.getwriter(ENC)(sys.stdout)):
        self.level = level
        self.out = out
    def log(self, level, *message):
        if not isinstance(level, int):
            raise Exception('int expected for argument `level\'.')
        if level > self.level:
            msg = ' '.join(map(unicode, message))
            self.out.write('%s %s\n' % (level, msg))
logger = Logger(0)

def findProxy ():
    proxy = {'http':'', 'https':''}
    if sys.platform == 'win32':
        # todo
        pass
    elif sys.platform in ['cygwin', 'linux2', 'linux3']:
        ks = dict(map(lambda k: (k.upper(), os.environ[k]), os.environ.keys())) 
        proxy['https'] = ks.get('HTTPS_PROXY')
        proxy['http'] = ks.get('HTTP_PROXY')
        if proxy['http'] is None and proxy['https'] is None:
            proxy = None
    logger.log(0, 'findProxy:', proxy)
    return proxy

# やっぱり、最初から最後までAPIからコントロールするべきなんじゃないかと思う
#
# api = API oauth()
# for status in api.streaming.filter():
#     print status
#
class TwitterOAuth(object):
    Site = 'api.twitter.com'
    SearchSite = 'search.twitter.com'
    StreamSite = 'stream.twitter.com'
    UserStreamSite = 'userstream.twitter.com'
    UploadSite = 'upload.twitter.com'
    def __init__(self, consumer_key, consumer_secret, use_https=False):
        if type(consumer_key) == unicode:
            consumer_key = str(consumer_key)
        if type(consumer_secret) == unicode:
            consumer_secret = str(consumer_secret)
        self.scheme = 'http' + ['', 's'][use_https]
        self.ctok = Token(consumer_key, consumer_secret)
        self.rtok = Token('', '')
        self.atok = Token('', '')
        self.verifier = None
        self.opener = urllib2.build_opener()
        # for debug
        #self.opener = urllib2.build_opener(urllib2.HTTPHandler(debuglevel=1))
        self.authdone = False

        self._proxies = None
    def _setProxies(self, proxies):
        self.proxies = proxies
        for i, handler in enumerate(self.opener.handlers):
            if isinstance(handler, urllib2.ProxyHandler):
                self.opener.handlers[i].proxies = proxies
                #print self.opener.handlers[i].proxies
        else:
            self.opener.add_handler(urllib2.ProxyHandler(proxies))

    @property
    def authorized(self):
        return self.authdone
        
    def p(self, path):
        site = TwitterOAuth.Site
        scheme = self.scheme
        logger.log(0, 'OAuth.p path :',path)
        if path[0] == 'u':
            # user stream is https only
            # http://dev.twitter.com/pages/user_streams#ImportantItems
            logger.log(0, '*** userstreaming')
            scheme = 'https'
        if path[0] in 'usm':
            site = {
                's': TwitterOAuth.StreamSite,
                'u': TwitterOAuth.UserStreamSite,
                'm': TwitterOAuth.UploadSite,
                }[path[0]]
            path = path[1:]
        if path == '/search':
            site = TwitterOAuth.SearchSite
        url = scheme + '://' + site + path
        logger.log(0, 'OAuth.p oauth:',url)
        return url
    
    # argument `url' will be hided when variable `url' is passed as keyword argument
    # for api calling
    def buildRequest(self, method, _url, **kwargs):
        # build urllib2.Request instance with oauth
        
        # http method name check
        if not method.upper() in ['GET', 'POST']:
            raise Exception('invalid method')
        method = method.upper()
        
        # build OAuth paarmeters
        dat = {
            'oauth_consumer_key': self.ctok.tok,
            'oauth_signature_method': 'HMAC-SHA1',
            'oauth_timestamp': str(int(time.time())),
            'oauth_nonce': str(uuid.uuid4()),
            'oauth_version': '1.0',
        }
        q = lambda s: urllib.quote(s, '')
        qq = lambda s: urllib.quote(s, '~')
        logger.log(0, 'args:', kwargs)
        for key in kwargs:
            value = kwargs[key]
            if isinstance(value, unicode):
                dat[key] = value.encode('utf-8')
            else:
                dat[key] = str(value)
        # sign
        prm = '&'.join('%s=%s' % (q(k), qq(dat[k])) for k in sorted(dat))
        # right side key is access token secret if session is for api calling,
        # request token secret for others.
        key = '%s&%s' % (self.ctok.sec, [self.atok.sec, self.rtok.sec][self.atok.sec is None])
        msg = '&'.join([method, q(_url), q(prm)])
        sig = hmac.new(key, msg, hashlib.sha1)
        dat['oauth_signature'] = sig.digest().encode('base64').strip()
        # build request parameter line (including oauth_signature)
        prm = '&'.join('%s=%s' % (q(k), qq(dat[k])) for k in sorted(dat))
        method = method.upper() # normalize
        req_url = _url
        authkeys = sorted([
            'oauth_consumer_key',
            'oauth_nonce',
            'oauth_signature',
            'oauth_signature_method',
            'oauth_timestamp',
            'oauth_token',
            'oauth_version',
            ])
        if method == 'GET':
            if _url.startswith('http://' + TwitterOAuth.Site + '/oauth') or \
               _url.startswith('https://' + TwitterOAuth.Site + '/oauth'):
                req_url += '?' + prm
            else:
                prm = '&'.join('%s=%s' % (q(k), qq(dat[k])) for k in sorted(dat) if not k in authkeys)
                if prm != '':
                    req_url += '?' + prm
            logger.log(0, 'req_url:',req_url)
        req = urllib2.Request(url=req_url)
        if method == 'POST':
            req.add_data(prm)
            logger.log(0, 'req_data:',req.get_data())
        
        # signature requires additional parameters
        # but authorization headaer doesn't requires
        # those of them.
        # variable injection
        #req.authheader = ','.join('%s=%s' % (q(k), qq(dat.get(k, ''))) for k in authkeys)
        #
        # HTTP 500 matters:
        # http://groups.google.com/group/twitter-development-talk/browse_thread/thread/d0178df0b370c12a/70cbcd8f92c6d649?lnk=gst&q=500+streaming#70cbcd8f92c6d649
        # > It is working now after I quoted the oauth values. 
        req.authheader = ','.join('%s="%s"' % (q(k), qq(dat.get(k, ''))) for k in authkeys)
        
        return req
    
    def getRequestToken(self, callback_url=None):
        url = self.p('/oauth/request_token')
        if callback_url:
            req = self.buildRequest('GET', url, oauth_callback=callback_url)
        else:
            req = self.buildRequest('GET', url)
        conn = self.opener.open(req)
        cont = conn.read()
        dic = cgi.parse_qs(cont)
        self.rtok.tok = dic['oauth_token'][0]
        self.rtok.sec = dic['oauth_token_secret'][0]
    
    def setRequestToken(self, tok, sec):
        self.rtok.tok = tok
        self.rtok.sec = sec
        
    def getVerifier(self):
        url = self.getVerifyURL()
        try:
            pin = self.verify(url)
        except Exception, e:
            raise e
        self.verifier = pin
    
    def getVerifyURL(self):
        p = '/oauth/authorize?oauth_token=' + self.rtok.tok
        url = self.p(p)
        return url
    
    def setVerifier(self, verifier):
        self.verifier = verifier
    
    def getAccessToken(self):
        url = self.p('/oauth/access_token')
        req = self.buildRequest('GET', url, oauth_token=self.rtok.tok, oauth_verifier=self.verifier)
        self.opener.addheaders = [('Authorization', 'OAuth')]
        conn = self.opener.open(req)
        cont = conn.read()
        dic = cgi.parse_qs(cont)
        self.atok.tok = dic['oauth_token'][0]
        self.atok.sec = dic['oauth_token_secret'][0]
    
    def setAccessToken(self, key, sec):
        # TODO: validate passed access token
        self.atok.tok = key
        self.atok.sec = sec
        self.authdone = True
        
    def apicall(self, method, path, **kwargs):
        method = method.upper()
        url = self.p(path)
        req = self.buildRequest(method, url, oauth_token=self.atok.tok, **kwargs)
        logger.log(0, 'url:', req.get_full_url())
        logger.log(0, 'authorization header:',req.authheader)
        self.opener.addheaders = [('Authorization', 'OAuth ' + req.authheader)]

        # encode unicode to utf-8
        kwargs = dict(kwargs)
        for key in kwargs:
            value = kwargs[key]
            if isinstance(value, unicode):
                kwargs[key] = value.encode('utf-8')
            else:
                kwargs[key] = str(value)

        postdata = urllib.urlencode(kwargs)
        logger.log(0, 'param line:',postdata)
        if method == 'POST':
            req.add_data(postdata)
        try:
            logger.log(0, '- open')
            conn = self.opener.open(req)
            logger.log(0, '- opened')
            return conn
        except urllib2.HTTPError, e:
            raise e
    
    def login(self):
        # TODO: implement
        """
        login to twitter via web
        """
        # login via web if not logged in
        username,password = self.loadAccount()
        # requie: has session <- login
        dat = {
            'session[username_or_email]': username,
            'session[password]': password,
        }
        url = 'https://twitter.com/sessions'
        req = urllib2.Request(url=url, data=urllib.urlencode(dat))
        # add cookie processing handler
        proc = urllib2.HTTPCookieProcessor(cookielib.CookieJar())
        self.opener.add_handler(proc)
        # add redirect handler ? 
        pass
        # login
        conn = self.opener.open(req)
        print 'login successful'
        
        conn = self.opener.open('http://twitter.com/')
        fp = open('out.html', 'w')
        fp.write(conn.read())
        fp.close()
    
    def auth(self):
        """
        authenticate with OAuth
        application can call api after calling this method
        """
        if self.authorized:
            return
        ret = self.loadAccessToken()
        if ret is None:
            self.getRequestToken()
            self.getVerifier()
            self.getAccessToken()
            self.saveAccessToken((self.atok.tok, self.atok.sec))
        elif not (isinstance(ret, tuple) or isinstance(ret, list)) or len(ret) != 2:
            raise Exception('loadAccessToken must return sequence with length 2')
        else:
            # access token is successfully loaded
            self.atok.tok = ret[0]
            self.atok.sec = ret[1]
        self.authdone = True
    
    #
    # methods to be customized 
    #  - save/load consumer token
    #  - save/load request token
    #  - save/load access token
    #  - save/load verifier
    #  - save/load user account
    #  - verify
    #
    def saveAccessToken(self, token):
        return None
    def loadAccessToken(self):
        return None

    def saveVerifier(self, verifier):
        self.verifier = verifier
    def loadVerifier(self):
        return None
    def verify(self, url):
        print 'access url below and input pin code: ', url
        pin = raw_input('input pin code: ')
        return pin

    def saveRequestToken(self, token):
        return None
    def loadRequestToken(self):
        return None
    
    def saveConsumerToken(self, token):
        return None
    def loadConsumerToken(self):
        return None
    
    def saveUserAccount(self, username, password):
        return None
    def loadUserAccount(self):
        return None


#
# [permission, parameters]
#
# permission:
#     integer in range [0, 7]
#     bit0: GET or POST
#     bit1: authentication required or not
#     Bit2: api limitation exists or not
# parameters:
#     integer
#     if paraminfo[len(paraminfo) - i - 1] is available in
#     specified api, then bit i is raised.
#
paraminfo = [
    #"""3 count int f
    #2 delimited str f
    #1 follow int f
    #""".split()
    # streaming api
    ['count', int, False],
    ['delimited', str, False],
    ['follow', int, False],
    ['track', str, False],
    #
    
    
    ['list_id', str, True],
    
    ['id', int, False],
    
    ['list_id', str, False],
    
    ['name', str, True],
    ['mode', str, False],

    ['source_id', int, False],
    ['source_screen_name', str, False],
    ['target_id', int, False],
    ['target_screen_name', str, False],
   
    ['user_a', str, True], 
    ['user_b', str, True], 
    
    ['follow', str, False],
    
    ['name', unicode, False],
    ['url', str, False],
    ['location', unicode, False],
    ['description', unicode, False],

    ['tile', bool, False],
    
    ['image', str, True],
    
    ['profile_background_color', str, False],
    ['profile_text_color',    str, False],
    ['profile_link_color',    str, False],
    ['profile_sidebar_fill_color', str, False],
    ['profile_sidebar_border_color',  str, False],
    
    ['device',                str, True],
    ['size',                  str, False],
    ['screen_name',           str, True],
    ['query',                 unicode, False],
    ['text',                  unicode, True],
    ['cursor',                int, False],
    ['q',                     unicode, True],
    ['per_page',              int, False],
    ['id',                    str,  False],
    ['date',                  str, False],
    ['exclude',               str, False],
    ['display_coordinates',   bool, False],
    ['place_id',              int,  False],
    ['geo_enabled',           bool, False],
    ['long',                  float, False],
    ['lat',                   float, False],
    ['in_reply_to_status_id', int, False],
    ['status',                unicode, True],
    ['id',                    int, True],
    ['user_id',               int, False],
    ['screen_name',           str, False],
    ['include_rts',           bool, False],
    ['page',                  int,  False],
    ['count',                 int,  False],
    ['max_id',                int,  False],
    ['since_id',              int,  False],
    ['include_entities',      bool, False],
    ['trim_user',             bool, False],
]
apiinfo = {
    'report_spam'            : [6, 0x182],
    'saved_searches': {
        ''                   : [3, 0],
        'show/:id'           : [2, 0x200],
        'create'             : [6, 0x1000000],
        'destroy/:id'        : [6, 0x200],
    },
    'statuses': {
        # Timeline resources
        'public_timeline'     : [0, 0x3],
        'home_timeline'       : [3, 0x1f],
        'friends_timeline'    : [3, 0x7f],
        'user_timeline'       : [3, 0x1ff],
        'mentions'            : [3, 0x7f],
        'retweeted_by_me'     : [3, 0x3f],
        'retweeted_to_me'     : [3, 0x3f],
        'retweets_of_me'      : [3, 0x3f],

        # Tweets resources    
        'show/:id'            : [3, 0x203],
        'update'              : [6, 0x1fc03],
        'destroy/:id'         : [6, 0x203],
        'retweet/:id'         : [6, 0x203],
        #'retweets/:id'        : [3, 0x203],
        ':id/retweeted_by': {
            ''                : [3, 0x1b],
            'ids'             : [3, 0x1b],
            },
        
        
        'friends'  : [3, 0x400182],
        'followers': [3, 0x400182],
    },
    'users': {
        'show'  : [1, 0x182],
        # TODO: test
        'lookup': [3, 0x182],
        # TODO: test
        'search': [3, 0x300022],
        # request suggestions/:slug if keyword argument 'slug' is passed.
        'suggestions': [1, 0],
        'profile_image/:screen_name': [0, 0x6000000],
    },
    'trends': {
        # trends resources
        ''                    : [1, 0],
        'current'             : [1, 0x20000],
        'daily'               : [1, 0x60000],
        'weekly'              : [1, 0x60000],
        
        # local trends resources
        'available': [1, 0x3000],
        # 1 -> one
        'one': [1, 0],
    },
    # TODO: Geo Resource
    'geo': {
        'nearby_places': (),
        'search': (),
        'similarr_places': (),
        'reverse_geocode': (),
        'id': (),
        'place': (),
    },
    'direct_messages': {
        ''           : [3, 0x3e],
        'new'        : [6, 0x800182],
        'sent'       : [3, 0x3e],
        'destroy/:id': [6, 0x202],
    },
    'favorites': {
        ''              : [3, 0x80022],
        'create/:id'    : [6, 0x202],
        'destroy/:id'   : [6, 0x202],
    },
    'account': {
        'verify_credentials': [3, 2],
        'rate_limit_status' : [2, 0],
        'end_session'       : [6, 0],
        'update_delivery_device': [6, 0x8000002],
        # TODO: test
        'update_profile_colors': [6, 0x1f0000002],
        # TODO: test
        'update_profile_image': [6, 0x200000002],
        # TODO: test
        'update_profile_background_image': [6, 0x600000002],
        'update_profile': [6, 0x7800000002],
    },
    'legal': {
        'tos'    : [1, 0],
        'privacy': [1, 0],
    },
    'help': {
        'test'   : [0, 0],
    },
    
    # block resources
    'blocks': {
        'create'  : [6, 0x182],
        'destroy' : [6, 0x182],
        # TODO: http 401
        'exists'  : [3, 0x182],
        'blocking': {
            ''    : [3, 0x22],
            'ids' : [3, 0],
        },
    },
    # notification resources
    # TODO: test
    'notifications': {
        'follow': [6, 0x182],
        'leave' : [6, 0x182],
    },
    
    # oauth resources
    # TODO: implement
    'oauth': {
        'request_token': [],
        'authorize': [0, 0],
        'authenticate': [],
        'access_token': [],
    },
    
    
    # friends and followers resources
    'friends': {
        'ids': [3, 0x400180],
    },
    'followers': {
        'ids': [3, 0x400180],
    },

    # friendships resources
    'friendships': {
        'create'  : [6, 0x8000000182],
        'destroy' : [6, 0x182],
        'exists'  : [1, 0x30000000000],
        'show'    : [1, 0x3c0000000000],
        'incoming': [3, 1<<22],
        'outgoing': [3, 1<<22],
    },
    
    # list resources
    ':user/lists': {
        '': [3, 1<<22],
        ':id/statuses' : [1, (1<<20)+0x2e],
        'memberships'  : [3, 1<<22],
        'subscriptions': [3, 1<<22]
     },
    ':user/lists_create': [6, (1<<35)+(1<<46)+(1<<47)],
    ':user/lists_update/:id': [6, (1<<35)+(1<<46)+(1<<47)],
    ':user/lists_delete/:id': [6, 1<<19],
    # list member resources
    ':user/:list_id/members': [3, (1<<48)+(1<<22)+2],
    ':user/:list_id/members_create': [6, (1<<9)+(1<<50)],
    ':user/:list_id/members_delete': [6, (1<<9)+(1<<50)],
    # TODO: test
    ':user/:list_id/create_all'    : [6, 0x180],
    # TODO: test
    ':user/:list_id/ismemberof/:id': [3, (1<<9)+(1<<50)+2],
    
    # list subscribers resources
    ':user/:list_id/subscribers': [3, (1<<48)+(1<<22)+2],
    # TODO: test
    ':user/:list_id/subscribers_create': [6, 1<<50],
    # TODO: test
    ':user/:list_id/subscribers_delete': [6, 1<<50],
    # TODO: test
    ':user/:list_id/issubscriberof/:id': [3, 0x4000000000202],
    
    #
    # Search .. search.twitter.com
    #
    'search': [3, 1 << 21], # TODO: 

    #
    # Streaming API
    #
    'streaming': {
        'statuses': {
            # http://dev.twitter.com/doc/post/statuses/filter
            'filter'   : [6, (1<<51)+(1<<52)+(1<<53)+(1<<54)],
            'firehose' : [3, (1<<53)+(1<<54)],
            'retweet'  : [3, 1<<53],
            'sample'   : [3, (1<<53)+(1<<54)],
            },   
    },
    
    #
    # User Streaming API
    #
    'userstreaming': {
        # http://dev.twitter.com/pages/user_streams
        'user': [2, 0]
    },
    
    #
    # Site Streaming API
    #
    # future support

    #
    # update status with media
    # ref: https://dev.twitter.com/docs/api/1/post/statuses/update_with_media
    #
    'upload': {
    },

    # Activity API
    # *  have not been announced officially yet,
    #    url may change in future
    'i': {
        'activity': {
            'about_me': [3, 0x13],
            'by_friends': [3, 0x13],
        },
    },
}

class API(object):
    callcount = 0
    def __init__(self, oauthobj, version=1, format='json', path=[], current=apiinfo, streaming_version=1, userstreaming_version=2, proxies=None):
        self._oauthobj = oauthobj
        self._version = version
        self._streaming_version = streaming_version
        self._userstreaming_version = userstreaming_version
        self._format = format
        self._path = path
        self._current = current

        self.proxies = proxies
        self._oauthobj._setProxies(proxies)
    def setProxies(proxies):
        self.proxies = proxies
        self._oauthobj._setProxies(proxies)

    def p(self, relpath):
        if relpath.startswith('/streaming'):
            path = 's/' + str(self._streaming_version) + relpath[len('/streaming'):]
        elif relpath.startswith('/userstreaming'):
            path = 'u/' + str(self._userstreaming_version) + relpath[len('/userstreaming'):]
        elif relpath.startswith('/i/'): # activity api (not official announced)
            path = relpath
        else:
            path = '/' + str(self._version) + relpath
        path = path + '.' + self._format
        return path
    def buildparams(self, pinfo):
        ps = []
        n = pinfo
        m = 1
        while n != 0:
            if n & 1 == 1:
                ps.append(paraminfo[-m])
            n >>= 1
            m += 1
        return ps
    def apicall(self, method, relpath, auth_required, rate_limited, **kwargs):
        API.callcount += 1
        method = method.upper()
        path = self.p(relpath)
        
        logger.log(0, 'relpath:',relpath)
        logger.log(0, 'path:',path)
        logger.log(0, 'param:',kwargs)
        
        # wrap
        if path[0] in 'us':
            kwargs['delimited'] = 'length'
       
        if auth_required:
            cont = None
            try:
                conn = self._oauthobj.apicall(method, path, **kwargs)
                cont = conn.read()
                logger.log(-1, 'content readed:\n' + cont)
            except Exception, e:
                raise e
            if relpath.startswith('/streaming'):
                logger.log(0, '**Streaming')
                return Stream(conn, self)
            if relpath.startswith('/userstreaming'):
                logger.log(0, '**User Streaming')
                return UserStream(conn, self)
            return self.asvalidformat(cont)
        url = self._oauthobj.p(path)
        data = urllib.urlencode(kwargs)
        fun = {
            'GET':  lambda: urllib.urlopen(url + '?' + data),
            'POST': lambda: urllib.urlopen(url, data)
        }
        cont = ''
        try:
            conn = fun[method]()
            cont = conn.read()
            return self.asvalidformat(cont)
        except Exception, e:
            #raise e
            return cont
    def asvalidformat(self, cont):
        #if 'profile_image' in relpath: # return actual image
        #    return cont
        if self._format == 'json':
            d = json.loads(cont)
            d = objectwrap(d)
            return d

    # :idを含むやつは、飛ばしてアクセスする.パラメータにidを要求する。
    # （APIのパラメータに必要かどうかは関係なく。）
    # /yy/:id/xxxなら
    # yy.xxx(id=id)
    def __call__(self, *args, **kwargs):
        info = self._current
        if type(info) == dict and '' in info:
            self._current = self._current['']
            info = self._current
        
        def rep(x):
            # 検索ワードとかに入ってると置換されてしまうぞ
            if ':id' in x:
                x = x.replace(':id', str(kwargs['id']))
            if ':screen_name' in x:
                x = x.replace(':screen_name', str(kwargs['screen_name']))
            if ':slug' in kwargs:
                # suggestions/:slug
                if x == 'suggestions':
                    x = 'suggestions/' + kwargs['slug']
                else:
                    x = x.replace(':slug', str(kwargs['slug']))
            if ':user' in x:
                x = x.replace(':user', str(kwargs['user']))
            if ':list_id' in x:
                x = x.replace(':list_id', str(kwargs['list_id']))
            if 'lists_create' in x:
                x = x.replace('_create', '')
            if 'lists_update' in x:
                x = x.replace('_update', '')
            if 'lists_delete' in x:
                x = x.replace('_delete', '')
                # ref: http://dev.twitter.com/doc/delete/:user/lists/:id
                kwargs['_method'] = 'DELETE'
            if 'members_create' in x:
                x = x.replace('_create', '')
            if 'members_delete' in x:
                x = x.replace('_delete', '')
                # ref: http://dev.twitter.com/doc/delete/:user/:list_id/members
                kwargs['_method'] = 'DELETE'
            if 'ismemberof' in x:
                x = x.replace('ismemberof', 'members')

            if 'subscribers_create' in x:
                x = x.replace('_create', '')
            if 'subscribers_delete' in x:
                x = x.replace('_delete', '')
                # ref: http://dev.twitter.com/doc/delete/:user/:list_id/subscribers
                kwargs['_method'] = 'DELETE'
            if 'issubscriberof' in x:
                x = x.replace('issubscriberof', 'subscribers')
            logger.log(0, '!',x)
            return x
        pinfo        = info[1]
        info         = info[0]
        path         = '/' + '/'.join(rep(p) for p in self._path)
        method       = ['get', 'post'][(info & 4) / 4]
        authrequired = [False, True][(info & 2) / 2]
        limitexists  = [False, True][info & 1]
        
        params = self.buildparams(pinfo)
        # parameter check
        param = {}
        for pname, ptype, require in params:
            if require and not pname in kwargs:
                raise Exception('argument "%s" is required.' % pname)
            if pname in kwargs and not isinstance(kwargs[pname], ptype):
                 if not (ptype is int and isinstance(kwargs[pname], long)):
                     raise Exception('argument "%s" is must be type %s' % (pname, ptype))
            if pname in kwargs:
                if ptype is bool and kwargs[pname] is True:
                    param[pname] = 't'
                else:
                    param[pname] = kwargs[pname]
        # alter http method
        if '_method' in kwargs:
            param['_method'] = kwargs['_method']
        
        try:
            ret = self.apicall(method, path, authrequired, limitexists, **param)
            return ret
        except Exception, e:
            raise e

    def __getattr__(self, name):
        info = self._current 
        for p in self._path + [name]:
            for k in info:
                r = k
                for w in ['id', 'screen_name', 'user', 'list_id']:
                    r = r.replace(':%s/' % w, '')
                    r = r.replace('/:%s' % w, '')
                    r = r.replace(':%s' % w, '')
                #print '"%s" "%s" "%s"'%( p,r,k)
                if r == p:
                    return API(self._oauthobj, self._version, self._format, self._path + [k], self._current[k], self._streaming_version, self._userstreaming_version, self.proxies)
        return self.__dict__[name]
    def auth(self):
        try:
            if not self._oauthobj.authorized:
                self._oauthobj.auth()
        except Exception, e:
            raise e
    def selfauth(self):
        ret = self.oauth.requet_token()
        dic = cgi.parse_qs(ret)
        
        ret = self.oauth.access_token()
        
    def __repr__(self):
        if self._path == []:
            return '<API %s>' % ','.join(apiinfo.keys())
        if isinstance(self._current, dict):
            return '<%s %s>' % (self._path[-1], ','.join(self._current.keys()))
        return '<%s(callable) %s>' % (self._path[-1], ','.join(map(lambda s: ['','*'][s[2]] + s[0], self.buildparams(self._current[1]))))
        
##################################################
# streaming data wrapper
##################################################
class StreamBase(object):
    def __init__(self, conn, api):
        # delimited=lengthを指定していること.
        self.conn = conn
        self.api = api
    def __iter__(self):
        return self
    def RecoveryConnection(self, maxtry=10):
        wait = 1
        ntry = 0
        while True:
            try:
                # TODO: 前回接続時のリクエストを記憶しておく必要
                self.conn = request
                return
            except:
                ntry += 1
                wait *= 2
                if ntry >= maxtry:
                    raise Exception('Connection Failure')
                time.sleep(wait)
            
    def fetchLine(self):
        while True:
            line = self.conn.readline()
            if line.strip() != '': # 接続維持のための空行
                return line
    def next(self):
        #bytelength = int(self.fetchLine())
        length = self.fetchLine()
        #print 'delimited length:',length
        jsonstr = self.fetchLine()
        #print 'content:',jsonstr
        try:
            return objectwrap(json.loads(jsonstr))
        except Exception, e:
            self.recovery()

class Stream(StreamBase):
    def __init__(self, conn, api):
        super(Stream, self).__init__(conn, api)
    def next(self):
        return StreamBase.next(self)

# delimitedじゃない生の接続がほしいときはどうすればいいの？
# -> あとまわし。大抵はラッパーつかう。

class UserStream(StreamBase):
    def __init__(self, conn, api):
        super(UserStream, self).__init__(conn, api)
        self.first = True
    def next(self):
        # ref: http://dev.twitter.com/pages/user_streams#Schema
        if self.first:
            self.fetchLine() # delimited length
            self.friends = self.fetchLine()
            #print 'friends', self.friends
            self.first = False
        return StreamBase.next(self)


# ----------------------------------------
# 2011/01/30~

class EventHandler(object):
    def __init__(self, api):
        self.api = api

class PollingHandler(EventHandler):
    def __init__(self, api):
        super(PollingHandler, self).__init__(api)
    def onEvent(self, jsondoc):
        self.callback(jsondoc)
    def callback(self, jsondoc):
        pass

class StreamHandler(EventHandler):
    def __init__(self, api):
        pass
    
class UserStreamHandler(EventHandler):
    def __init__(self, api):
        super(UserStreamHandler, self).__init__(api)
        self.user = api.account.verify_credentials()
    def onEvent(self, jsondoc):
        self.onAllEvent(jsondoc)
        if 'delete' in jsondoc:
            self.onDelete(jsondoc)
        else:
            m = '@' + self.user['screen_name']
            self.onUpdate(jsondoc)
            if m in jsondoc['text']:
                self.onMention(jsondoc)
    def onAllEvent(self, jsondoc):
        pass
    def onDelete(self, jsondoc):
        pass
    def onFavorite(self, jsondoc):
        pass
    def onUpdate(self, jsondoc):
        pass


class Action(object):
    def __init__(self, api, handler):
        self.api = api
        self._handler = handler(api)
    def start(self):
        for jsondoc in self:
            self._handler.onEvent(jsondoc)
    def __iter__(self):
        return self
    def next(self):
        raise StopIteration()
    def onEvent(self, jsondoc):
        pass

import time
class PollingAction(Action):
    def __init__(self, api, handler, interval=60, apitype='home_timeline'):
        super(PollingAction, self).__init__(api, handler)
        #assert apitype in ['public_timeline', 'home_timeline', 'friends_timeline', 'user_timeline']
        #assert apitype in ['public_timeline', 'home_timeline', 'friends_timeline', 'user_timeline', 'activity']
        assert apitype in ['public_timeline', 'home_timeline', 'friends_timeline', 'user_timeline', 'activity/by_friends', 'activity/about_me']
        self.interval = interval
        self.isfirst = True
        self.lasttime = None
        self.apitype = apitype
        self.since_id = None
        self.buf = []
    def fill(self):
        if not self.isfirst:
            dif = self.interval - (time.time() - self.lasttime)
            if dif > 0:
                time.sleep(dif)
        else:
            self.isfirst = False
        
        self.lasttime = time.time()
        if self.apitype == 'activity/by_friends':
            apicall = self.api.i.activity.by_friends
        elif self.apitype == 'activity/about_me':
            apicall = self.api.i.activity.about_me
        else:
            apicall = getattr(self.api.statuses, self.apitype)
        lst = None
        if self.since_id:
            lst = apicall(since_id=self.since_id)
        else:
            lst = apicall()
        
        self.buf.extend(lst)
        
        if len(lst) > 0:
            self.since_id = lst[0].id
        
    def next(self):
        while self.buf == []:
            self.fill()
        item = self.buf.pop(0)
        return item

class StreamAction(Action):
    def __init__(self, api, handler, streamtype='filter'):
        super(StreamAction, self).__init__(api, handler)
        self.stream = api.streaming.filter()
    def __iter__(self):
        return self.stream

class UserStreamAction(Action):
    def __init__(self, api, handler):
        super(UserStreamAction, self).__init__(api, handler)
        self.stream = api.userstreaming.user()
    def __iter__(self):
        return self.stream

class DictWrap(dict):
    def __getattr__(self, name):
        return self.get(name, None)
def objectwrap(item):
    if type(item) == dict:
        item = DictWrap(item)
        for k in item:
            item[k] = objectwrap(item[k])
    elif type(item) == list:
        for i in xrange(len(item)):
            item[i] = objectwrap(item[i])
    return item

#    
# class Handler(UserStreamHandler):
#     def onMention(self, status):
#         src = status['user']['screen_name']
#         self.api.statuses.update(status=u'@%s hello' % src)
# 
# act = UserStreamAction(api, Handler())
# act.start()
#

