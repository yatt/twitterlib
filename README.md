## What's this?

twitterlib python library is a simple and useful twitter api client library.

###twitterlib provides...

* oauth ver1.0 authentication
* easy way to access
 - REST API
 - Search API
 - Streaming API
 - User Streaming API
* support both http and https (for API v1.0)
* event-driven programming mechanizm

###you can use this module such applications below

* console application
* desktop application
* web application ([Django](https://www.djangoproject.com/), [Google App Engine](https://appengine.google.com/) etc)

### distribution contains sample application codes

* simple console client
* wxPython application
* Django project
* Google App Engine project

**so you can apply this module to your code or app immediately**

you have only to provide OAuth comsumer key/secret and define interface for saving/loading access token.
In addition, 

## requirements

* twitterlib require python 2.5, 2.6, or 2.7
* simplejson if python2.5 (except google app engine)
* SSL connection over proxy requires 2.6.3 or higher (< 2.6.3 contain interpreter bug; [issue1424152](http://bugs.python.org/issue1424152))


## install

```sh
pip install git+https://github.com/yatt/twitterlib.git
```


## sample code

twitterlib.API enables programmer to access rest api with url like method name
```python
>>> # built-in simple CLI client interface
>>> import twitterlib
>>> auth = twitterlib.TwitterOAuth(consumer_key, consumer_secret)
>>> api = twitterlib.API(auth)
>>> # authenticate with OAuth
>>> api.auth()
access url below and input pin code:  http://api.twitter.com/oauth/authorize?oauth_token=abcdefghijklmnopqrstuvwxyz1234567890
pin code: ******* (input from user)
>>> # updating status /1/statuses/update
>>> api.statuses.update(status=u'twitterlib')
>>> # fetch home timeline /1/statuses/home_timeline
>>> lst = api.statuses.home_timeline(trim_user=True)
>>> for status in lst:
...     print status['text']
>>> # follow new user /1/friendships/create
>>> api.friendships.create(screen_name='targetuser')
>>>
>>> # create new list /1/:user/lists with HTTP POST
>>> api.lists_create(user='youraccount', name='newlistname')
>>> # update list /1/:user/lists/:id with HTTP POST
>>> api.lists_update(user='youraccount', id='newlistname', name='updated name', description='foo bar')
>>> # delete list /1/:user/lists with HTTP DELETE (or POST)
>>> api.lists_delete(user='youraccount', name='newlistname')
```

## sample code (get token from env)

```bash
export twitterlib_consumer_key=CONSUMERTOKENSTRING
export twitterlib_consumer_secret=SECRETSTRING
export twitterlib_access_key=USERSACCESSKEYSTRING
export twitterlib_access_secret=USERACCESSSECRETSTRING
```

```python
>>> import twitterlib
>>> auth = twitterlib.TwitterOAuth() # get from environment vairable
>>> api = twitterlib.API(auth)
>>> api.statuses.update(status=u'twitterlib')
```

