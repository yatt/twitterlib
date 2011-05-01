#!/usr/bin/env python
import os
import logging
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from appengine_utilities.sessions import Session
import twitterlib


#
#
# assign your application's consumer key/secret
#
#
CONSUMER_KEY = 'ABq0OCA9l9rAC0SIOdXPMQ'
CONSUMER_SECRET = 'xHIaSAyhuTTcVrGa1BSSEASsZPYRkQ61SkjLnHnCIjA'



def create_oauth():
    #return twitterlib.TwitterOAuth(CONSUMER_KEY, CONSUMER_SECRET)
    return twitterlib.TwitterOAuth(CONSUMER_KEY, CONSUMER_SECRET, use_https=True) # for https only user

class MainHandler(webapp.RequestHandler):
    def get(self):
        session = Session()
        auth = create_oauth()
        if not session.has_key('accesstoken'):
            if not session.has_key('requesttoken'):
                self.redirect('/login')
                return
            else:
                # save verifier and get access token
                rtok = session['requesttoken']
                auth.setRequestToken(rtok[0], rtok[1])
                verifier = self.request.get('oauth_verifier')
                auth.saveVerifier(verifier)
                auth.getAccessToken()
                session['accesstoken'] = (auth.atok.tok, auth.atok.sec)
        # fetch home timeline
        tok = session['accesstoken']
        auth.setAccessToken(tok[0], tok[1])
        api = twitterlib.API(auth)
        lst = api.statuses.home_timeline()
        
        u = api.account.verify_credentials().screen_name
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
        self.response.out.write(htmldoc)


class LoginHandler(webapp.RequestHandler):
    def get(self):
        session = Session()
        auth = create_oauth()
        assert os.environ['SERVER_NAME'] != 'localhost'
        callback_url = 'http://%s/' % os.environ['HTTP_HOST']
        try:
            auth.getRequestToken(callback_url)
        except Exception, e:
            logging.error(e.read())
            raise e
        session['requesttoken'] = (auth.rtok.tok, auth.rtok.sec)
        self.response.out.write("""
<a href="https://twitter.com/oauth/authorize?oauth_token=%s">authenticate</a>
        """ % auth.rtok.tok)

class LogoutHandler(webapp.RequestHandler):
    def get(self):
        Session().delete()
        self.redirect('/login')

def main():
    application = webapp.WSGIApplication([
            ('/', MainHandler),
            ('/login', LoginHandler),
            ('/logout', LogoutHandler),
        ],
        debug=True
        )
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
