from django.http import HttpResponse, HttpResponseRedirect
import twitterlib as tw
from django.conf import settings

def tauth():
    t = settings.CONSUMER_KEY
    s = settings.CONSUMER_SECRET
    o = tw.TwitterOAuth(t, s)
    return o

def index(req):
    o = tauth()
    if not 'access_token' in req.session:
        if not 'request_token' in req.session:
            return HttpResponseRedirect('/login')
            
    t = req.session['access_token']
    s = req.session['access_secret']
    o.setAccessToken(t, s)
    api = tw.API(o)
    try:
        r = api.account.verify_credentials()
    except Exception, e: # http 401
        return HttpResponseRedirect('/login')
    
    # screen_name
    r = api.account.verify_credentials()
    u = r.screen_name
    # home timeline
    lst = api.statuses.home_timeline()
    tl = '<br>'.join([s.user.screen_name + ' ' + s.text for s in lst])
    htmldoc = """
<!DOCTYPE html>
<html>
    <head>
        <meta charset="utf-8"/>
        <title>timeline</title>
    </head>
    <body>
        <h3>hello, %s!</h3>
        <p><a href="./logout">logout</a></p>
        %s
    </body>
</html>
    """ % (u, tl)
    return HttpResponse(htmldoc)

def oauthlogin(req):
    o = tauth()
    callback_url = 'http://%s:%s/save_token' % (req.META['SERVER_NAME'], req.META['SERVER_PORT'])
    try:
        o.getRequestToken(callback_url)
    except Exception, e:
        return HttpResponse("<html><body>something wrong: %s</body></html>" % str(e))
    # save request token to session
    req.session['request_token'] = o.rtok.tok
    req.session['request_secret'] = o.rtok.sec
    return HttpResponse("""
<!DOCTYPE html>
<html>
    <head>
        <meta charset="utf-8"/>
        <title>login</title>
    </head>
    <body>
        <a href="https://twitter.com/oauth/authenticate?oauth_token=%s">authenticate (https)</a>
    </body>
</html>
            """ % o.rtok.tok)

def save_token(req):
    o = tauth()
    
    # set request token/secret and verifier to
    # exchange access token
    
    # set request token from session
    rt = req.session['request_token']
    rs = req.session['request_secret']
    o.setRequestToken(rt, rs)
    
    # set verifier from http get parameter
    v = req.GET['oauth_verifier']
    o.setVerifier(v)
    
    # fetch access token
    o.getAccessToken()
    
    # save access token
    req.session['access_token'] = o.atok.tok
    req.session['access_secret'] = o.atok.sec
    
    return HttpResponseRedirect('/')

def logout(req):
    req.session.clear()
    return HttpResponseRedirect('/')
