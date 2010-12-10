#!/usr/bin/python2.6
# coding: utf-8

#
# ***TODO
# how interface should provide to non-authrequired api.
# hot interface should provide to web app.
# streaming api

# *** ChangeLog
# 2010/11/04 Write base code including OAuth association
# 2010/11/20 Write base code for calling api
# 2010/11/20 Support Tweets resource
# 2010/11/20 Support Timeline resources
# 2010/11/20 Support Legal resources
# 2010/11/20 Support Help resources
# 2010/11/20 Support Spam Reporting resources
# 2010/11/20 Support Trends resources
# 2010/11/20 Support Favorites resources
# 2010/11/20 Support Direct Messages resources
# 2010/11/20 Support Saved Searches resources
# 2010/11/21 Support User resources
# 2010/11/21 Support Local Trends resources
# 2010/11/24 Override API.__repr__ for easy use and debugging
# 2010/11/24 Support Account resources
# 2010/11/24 Support Blocks resources
# 2010/11/24 Support Notification resources
# 2010/11/25 Support Friendships resources
# 2010/11/25 Support List resources
#
# ** Progress
# 100 Timeline
# 100 Tweets
# 100 User
# 100 Trends
# 100 Local Trends
# 100 List
#  90 List Members
#  90 List Subscribers
# 100 Direct Messages
# 100 Friendship
# 100 Friends and Followers Friendship
# 100 Account
# 100 Favorites
# 100 Notifications
# 100 Block
# 100 Spam Reporting
# 100 Saved Searches
# 100 OAuth
#   0 Geo
# 100 Legal
# 100 Help
#   0 Streamed Tweets
#   0 Search
#
# 2010/11/20  9/23
# 2010/11/22 11/23
# 2010/11/24 15/23
# 2010/11/25 16/23

import uuid
import time
import hmac
import hashlib
import urllib
import urllib2
import cookielib
import simplejson
import cgi

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

class TwitterOAuth(object):
    Site = 'api.twitter.com'
    def __init__(self, consumer_key, consumer_secret, use_https=False):
        self.scheme = 'http' + ['', 's'][use_https]
        self.ctok = Token(consumer_key, consumer_secret)
        self.rtok = Token('', '')
        self.atok = Token('', '')
        self.verifier = None
        self.opener = urllib2.build_opener()
        self.authdone = False
        # for debug
        #self.opener = urllib2.build_opener(urllib2.HTTPHandler(debuglevel=1))
    @property
    def authorized(self):
        return self.authdone
        
    def loadAccessToken(self):
        pass
    def saveAccessToken(self, tokenpair):
        pass
    def verify(self, url):
        pass
    def getAccount(self):
        pass

    def p(self, path):
        return self.scheme + '://' + TwitterOAuth.Site + path
    
    # 2010/11/24 urlが/account/update_profileと被るのでアンダースコア付加
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
        print 'args:', kwargs
        for key in kwargs:
            value = kwargs[key]
            if isinstance(value, unicode):
                dat[key] = value.encode('utf-8')
            else:
                dat[key] = str(value)
        # sign
        prm = '&'.join('%s=%s' % (q(k), qq(dat[k])) for k in sorted(dat))
        # 2010/11/7 self.rtok.secとあるけどapi呼び出しの時はアクセストークンシークレットだぞ。
        key = '%s&%s' % (self.ctok.sec, self.rtok.sec)
        if not self.atok.sec is None:
            key = '%s&%s' % (self.ctok.sec, self.atok.sec)
        msg = '&'.join([method, q(_url), q(prm)])
        sig = hmac.new(key, msg, hashlib.sha1)
        dat['oauth_signature'] = sig.digest().encode('base64').strip()
        # build request parameter line (including oauth_signature)
        prm = '&'.join('%s=%s' % (q(k), qq(dat[k])) for k in sorted(dat))
        # 
        method = method.upper()
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
            #req_url += '?' + prm
            ## ugly!
            if _url.startswith('http://api.twitter.com/oauth') or _url.startswith('https://api.twitter.com/oauth'):
                req_url += '?' + prm
            else:
                prm = '&'.join('%s=%s' % (q(k), qq(dat[k])) for k in sorted(dat) if not k in authkeys)
                req_url += '?' + prm
            print 'req_url:',req_url
        req = urllib2.Request(url=req_url)
        if method == 'POST':
            req.add_data(prm)
            print 'req_data:',req.get_data()
        # signature requires additional parameters
        # but authorization headaer doesn't requires
        # those of them
        
        # variable injection
        req.authheader = ','.join('%s=%s' % (q(k), qq(dat.get(k, ''))) for k in authkeys)
        return req
    
    def getRequestToken(self):
        url = self.p('/oauth/request_token')
        req = self.buildRequest('GET', url)
        conn = self.opener.open(req)
        cont = conn.read()
        dic = cgi.parse_qs(cont)
        self.rtok.tok = dic['oauth_token'][0]
        self.rtok.sec = dic['oauth_token_secret'][0]
        
    def getVerifier(self):
        url = self.p('/oauth/authorize?oauth_token=' + self.rtok.tok)
        try:
            pin = self.verify(url)
        except Exception, e:
            raise e
        self.verifier = pin
    
    def getAccessToken(self):
        url = self.p('/oauth/access_token')
        req = self.buildRequest('GET', url, oauth_token=self.rtok.tok, oauth_verifier=self.verifier)
        self.opener.addheaders = [('Authorization', 'OAuth')]
        conn = self.opener.open(req)
        cont = conn.read()
        dic = cgi.parse_qs(cont)
        self.atok.tok = dic['oauth_token'][0]
        self.atok.sec = dic['oauth_token_secret'][0]
        
    def apicall(self, method, path, **kwargs):
        method = method.upper()
        url = self.p(path)
        req = self.buildRequest(method, url, oauth_token=self.atok.tok, **kwargs)
        print 'url:', req.get_full_url()
        self.opener.addheaders = [('Authorization', 'OAuth ' + req.authheader)]
        postdata = urllib.urlencode(kwargs)
        print 'param line:',postdata
        if method == 'POST':
            req.add_data(postdata)
        try:
            conn = self.opener.open(req)
            cont = conn.read()
            return simplejson.loads(cont)
        except urllib2.HTTPError, e:
            raise e
    
    def login(self):
        """
        login to twitter via web
        """
        # login via web if not logged in
        username,password = self.getAccount()
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
        if self.authdone:
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


paraminfo = [
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
    
    ['follow',                str, False],
    
    ['name',                  unicode, False],
    ['url',                   str, False],
    ['location',              unicode, False],
    ['description',           unicode, False],

    ['tile',                  bool, False],
    
    ['image',                 str, True],
    
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
    ['user_id',               str, False],
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
    'report_spam'            : [0b110, 0x182],
    'saved_searches': {
        ''                   : [0b011, 0],
        'show/:id'           : [0b011, 0x200],
        'create'             : [0b110, 0x1000000],
        'destroy/:id'        : [0b110, 0x200],
    },
    'statuses': {
        # Timeline resources
        # 2010/11/20
        'public_timeline'     : [0b000, 0x3],
        'home_timeline'       : [0b011, 0x1f],
        'friends_timeline'    : [0b011, 0x7f],
        'user_timeline'       : [0b011, 0x1ff],
        'mentions'            : [0b011, 0x7f],
        'retweeted_by_me'     : [0b011, 0x3f],
        'retweeted_to_me'     : [0b011, 0x3f],
        'retweets_of_me'      : [0b011, 0x3f],

        # Tweets resources    
        'show/:id'            : [0b011, 0x203],
        'update'              : [0b110, 0x1fc03],
        'destroy/:id'         : [0b110, 0x203],
        # 2010/11/20 下の二つ。公式ドキュメントでは認証不要になってるけど認証を要求されるんだけど。どういうことだよ。
        'retweet/:id'         : [0b110, 0x203],
        # 実行できねえ。なぜだろ
        #'retweets/:id'        : [0b011, 0x203],
        ':id/retweeted_by': {
            ''                : [0b011, 0x1b],
            'ids'             : [0b011, 0x1b],
            },
        
        
        'friends'  : [0b011, 0x400182],
        'followers': [0b011, 0x400182],
    },
    'users': {
        'show'  : [0b001, 0x182],
        # TODO: test
        'lookup': [0b011, 0x182],
        # TODO: test
        'search': [0b011, 0x300022],
        # request suggestions/:slug if keyword argument 'slug' is passed.
        'suggestions': [0b001, 0],
        'profile_image/:screen_name': [0b000, 0x6000000],
    },
    'trends': {
        # trends resources
        ''                    : [0b001, 0],
        'current'             : [0b001, 0x20000],
        'daily'               : [0b001, 0x60000],
        'weekly'              : [0b001, 0x60000],
        
        # local trends resources
        'available': [0b001, 0x3000],
        # 1 -> one
        'one': [0b001, 0],
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
        ''           : [0b011, 0x3e],
        'new'        : [0b110, 0x800182],
        'sent'       : [0b011, 0x3e],
        'destroy/:id': [0b110, 0x202],
    },
    'favorites': {
        ''              : [0b011, 0x80022],
        'create/:id'    : [0b110, 0x202],
        'destroy/:id'   : [0b110, 0x202],
    },
    'account': {
        'verify_credentials': [0b011, 2],
        'rate_limit_status' : [0b010, 0],
        'end_session'       : [0b110, 0],
        'update_delivery_device': [0b110, 0x8000002],
        # TODO: test
        'update_profile_colors': [0b110, 0x1f0000002],
        # TODO: test
        'update_profile_image': [0b110, 0x200000002],
        # TODO: test
        'update_profile_background_image': [0b110, 0x600000002],
        'update_profile': [0b110, 0x7800000002],
    },
    'legal': {
        'tos'    : [0b001, 0],
        'privacy': [0b001, 0],
    },
    'help': {
        'test'   : [0b000, 0],
    },
    
    # block resources
    'blocks': {
        'create'  : [0b110, 0x182],
        'destroy' : [0b110, 0x182],
        # TODO: http 401
        'exists'  : [0b011, 0x182],
        'blocking': {
            ''    : [0b011, 0x22],
            'ids' : [0b011, 0],
        },
    },
    # notification resources
    # TODO: test
    'notifications': {
        'follow': [0b110, 0x182],
        'leave' : [0b110, 0x182],
    },
    
    # oauth resources
    # TODO: implement
    'oauth': {
        'request_token': [],
        'authorize': [0b000, 0],
        'authenticate': [],
        'access_token': [],
    },
    
    
    # friends and followers resources
    'friends': {
        'ids': [0b011, 0x400180],
    },
    'followers': {
        'ids': [0b011, 0x400180],
    },

    # friendships resources
    'friendships': {
        'create'  : [0b110, 0x8000000182],
        'destroy' : [0b110, 0b110000010],
        'exists'  : [0b001, 0x30000000000],
        'show'    : [0b001, 0x3c0000000000],
        'incoming': [0b011, 1<<22],
        'outgoing': [0b011, 1<<22],
    },
    
    # list resources
    ':user/lists': {
        '': [0b011, 1<<22],
        ':id/statuses' : [0b001, (1<<20)+0b0101110],
        'memberships'  : [0b011, 1<<22],
        'subscriptions': [0b011, 1<<22]
     },
    ':user/lists_create': [0b110, (1<<35)+(1<<46)+(1<<47)],
    ':user/lists_update/:id': [0b110, (1<<35)+(1<<46)+(1<<47)],
    ':user/lists_delete/:id': [0b110, 1<<19],
    # list member resources
    ':user/:list_id/members': [0b011, (1<<48)+(1<<22)+2],
    ':user/:list_id/members_create': [0b110, (1<<9)+(1<<50)],
    ':user/:list_id/members_delete': [0b110, (1<<9)+(1<<50)],
    # TODO: test
    ':user/:list_id/create_all'    : [0b110, 0b110000000],
    # TODO: test
    ':user/:list_id/ismemberof/:id': [0b011, (1<<9)+(1<<50)+2],
    
    # list subscribers resources
    ':user/:list_id/subscribers': [0b011, (1<<48)+(1<<22)+2],
    # TODO: test
    ':user/:list_id/subscribers_create': [0b110, 1<<50],
    # TODO: test
    ':user/:list_id/subscribers_delete': [0b110, 1<<50],
    # TODO: test
    ':user/:list_id/issubscriberof/:id': [0b011, 0x4000000000202],
}

class API(object):
    def __init__(self, oauthobj, version=1, format='json', path=[], current=apiinfo):
        self._oauthobj = oauthobj
        self._version = version
        self._format = format
        self._path = path
        self._current = current
    def p(self, relpath):
        path = '/' + str(self._version) + relpath + '.' + self._format
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
        method = method.upper()
        path = self.p(relpath)
        
        print 'path:',path
        print 'param:',kwargs
       
        if auth_required:
            return self._oauthobj.apicall(method, path, **kwargs)
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
            if 'profile_image' in relpath: # return actual image
                return cont
            jsonobj = simplejson.loads(cont)
            return jsonobj
        except Exception, e:
            #raise e
            return cont
    # 2010/11/20
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
            print '!',x
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
                raise Exception('argument "%s" is must be type %s' % (pname, ptype))
            if pname in kwargs:
                if   ptype == bool and kwargs[pname] is True:
                    param[pname] = 't'
                else:
                    param[pname] = kwargs[pname]
        # alter http method
        if '_method' in kwargs:
            param['_method'] = kwargs['_method']
        
        try:
            jsonobj = self.apicall(method, path, authrequired, limitexists, **param)
            return jsonobj
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
                    return API(self._oauthobj, self._version, self._format, self._path + [k], self._current[k])
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
        

# utility
class SimpleTwitterOAuth(TwitterOAuth):
    def setAccessToken(self, access_token, access_token_secret):
        self.atok.tok = access_token
        self.atok.sec = access_token_secret
    def verify(self, url):
        print 'access url below and input pin code: ', url
        pin = raw_input('pin code: ')
        return pin

def main():
    pass

if __name__ == '__main__':
    main()
