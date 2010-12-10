"""
twitterlib module is a simple and useful twitter api client library.
twitterlib module provides
  * oauth authentication for both desktop application and webapp.
  * easy to use url like library api
  * Both http and https connection

programmer have only to provide comsumer key/secret and define
interface for sending/receiving access token.

twitterlib module usage example below.
twitterlib.API enables programmer to access rest api with url
like method name

>>> # build-in very simple CLI client interface
>>> import twitterlib
>>> o = lt.SimpleTwitterOAuth(consumer_key, consumer_secret)
>>> api = twitterlib.API(o)
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
"""

__author__ = 'darknesssharp@gmail.com'
__version__ = '0.1'
__license__ = 'MIT License'
