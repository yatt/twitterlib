# coding: utf-8 
# サポートしている機能
#  - ダブルクリックによるリンクURLのオープン
#  - 選択中のtweetをCtrl + Alt + RでRT補完
#  - 選択中のtweetをCtrl + Alt + Xで公式RT
#
# TODO:
#    日本語うまく処理できてない。unicodeでapiに渡されているのに。
#    streamingのサポート。
#    公式RTのサポート。
#
import os
import time
import datetime
import urllib
import urllib2
import re
import threading
import Queue
import webbrowser
from xml.sax.saxutils import unescape

import wx
from wx import xrc
import twitterlib


IMAGESIZE = (48, 48)
#
def wxNotify(title, msg, parent=None, size=(200, 200), pos=wx.DefaultPosition):
    dialog = wx.MessageDialog(parent, msg, title, wx.OK|wx.ICON_INFORMATION, pos)
    dialog.SetSize(size)
    dialog.ShowModal()
    dialog.Destroy()
#
class AuthDialog(object):
    """dialog for authenticating using OAuth
    """
    def __init__(self, res):
        self.res = res
        self.dialog = self.res.LoadDialog(None, 'AuthDialog')
        self.ctrls = [
              'lblProc1'
            , 'lblConsumerKey'
            , 'txtConsumerKey'
            , 'lblConsumerSecret'
            , 'txtConsumerSecret'
            , 'btnTokenSet'
            , 'lblProc2'
            , 'lblVerifier'
            , 'txtVerifier'
            , 'btnVerifier'
            ]
        for ctrl in self.ctrls:
            setattr(self, ctrl, xrc.XRCCTRL(self.dialog, ctrl))
        
        self.btnTokenSet.Bind(wx.EVT_BUTTON, self.btnTokenSet_onClick)
        self.btnVerifier.Bind(wx.EVT_BUTTON, self.btnVerifier_onClick)
        # TODO: delete
        self.txtConsumerKey.Value = '3uKsjJkQhLpWwJ9M7XlH4g'
        self.txtConsumerSecret.Value = 'HxMJBINiiCw8Oc1lFYWvydFqDjB9I7XmyD9vKpUmkRk'
    
        self.TokenSetPhase()
    
    def TokenSetPhase(self):
        self.setControls(True)
    
    def VerifierPhase(self):
        self.setControls(False)
    
    def btnTokenSet_onClick(self, event):
        global API
        self.VerifierPhase()
        
        # authentication
        ckey = str(self.txtConsumerKey.Value)
        csec = str(self.txtConsumerSecret.Value)
        API = TweetAPI(ckey, csec, use_https=True)
        try:
            API.oauth.getRequestToken()
            webbrowser.open_new_tab(API.oauth.getVerifyURL())
        except Exception, e:
            self.TokenSetPhase()
            wxNotify('error', 'hint: consumer key/secret is correct?\nnetwork is alive?') 
            print e
        
    def btnVerifier_onClick(self, event):
        global APIThread
        for i,ctrl in enumerate(self.ctrls):
            getattr(self, ctrl).Enabled = False
        # set verifier and get access token
        v = str(self.txtVerifier.Value)
        API.oauth.verifier = v
        try:
            API.oauth.getAccessToken()
            API.oauth.authdone = True
            API.setUser()
            # construct threads
            APIThread = TweetAPIThread(API, app.ctrl)
        except Exception, e:
            wxNotify('error', 'hint: verifier is correct?\nnetwork is alive?')
            print e
            self.VerifierPhase()
        
        self.dialog.Close()

    def setControls(self, boolval):
        for i,ctrl in enumerate(self.ctrls):
            getattr(self, ctrl).Enabled = boolval if i < 6 else not boolval
    

class UserImageContainer(object):
    """controlling cache and convert bitmap user profile image
    """
    PREFIX = 'img'
    def __init__(self):
        self.expire = datetime.timedelta(minutes=5)
        root = self.getrootdir()
        if not os.path.exists(root):
            os.mkdir(root)
        self.cache = {}
        self.imgserver = UserImageServer(self)
        
    def start(self):
        self.imgserver.start()
    def stop(self):
        self.imgserver.stop()
        
    def loadCache(self):
        # App must be instantinated before using wx.Image
        root = self.getrootdir()
        for screen_name in os.listdir(root):
            path = os.path.join(root, screen_name)
            bmp = wx.Image(path, wx.BITMAP_TYPE_ANY).ConvertToBitmap()
            self.cache[screen_name] = (bmp, datetime.datetime.now())
    
    def getrootdir(self):
        path = os.path.join(os.path.dirname(__file__), self.PREFIX)
        return path

    def getfilepath(self, screen_name):
        path = os.path.join(self.getrootdir(), screen_name + '.png')
        return path
        
    def fill(self, user):
        # fetch save user icon from web
        url = user.profile_image_url
        filepath = os.path.join(self.getrootdir(), user.screen_name + url[url.rfind('.'):])
        urllib.urlretrieve(user.profile_image_url, filepath)
        # load user icon, resize, convert to png, and save it back
        img = wx.Image(filepath, wx.BITMAP_TYPE_ANY)
        if IMAGESIZE:
            img = img.Resize(IMAGESIZE, (0, 0))
        img.SaveFile(self.getfilepath(user.screen_name), wx.BITMAP_TYPE_PNG)
        os.remove(filepath)
        bmp = img.ConvertToBitmap()
        # set pair (bitmap image, current time)
        self.cache[user.screen_name] = (bmp, datetime.datetime.now())

    def isexpired(self, user):
        return self.expire < datetime.datetime.now() - self.cache[user.screen_name][1]

    def modified(self, user):
        url = user.profile_image_url
        opener = urllib2.build_opener()
        f = urllib2.urlopen(url)
        last = f.info()['Last-Modified']
        f.close()
        format = '%a, %d %b %Y %H:%M:%S GMT'
        last = time.strptime(last, format)
        last = datetime.datetime(*last[:-3])

        locallast = self.cache[user.screen_name][1]
        return locallast < last
    
    def requestImage(self, user):
        k = user.screen_name
        if not k in self.cache:
            self.fill(user)
        elif self.isexpired(user):
            if self.modified(user):
                self.fill(user)
            else:
                self.cache[k] = (self.cache[k][0], datetime.datetime.now())
        else:
            pass
        return self.cache[k][0]
    
    def requestImageAsync(self, user, callback):
        """asyncronous user iamge fetch"""
        self.imgserver.request(user, callback)

#
# classes for asyncronous loading user image
#
class UserImageHandler(threading.Thread):
    def __init__(self, server):
        threading.Thread.__init__(self)
        self.server = server
        self.final = False
    def run(self):
        while True:
            if self.final:
                break
            try:
                user, callback = self.server.taskq.get(True, 2)
                bmp = self.server.container.requestImage(user)
                callback(user, bmp)
            except Exception, e:
                continue

class UserImageServer(object):
    def __init__(self, container):
        self.container = container
        self.taskq = Queue.Queue()
        self.threads = [UserImageHandler(self) for i in range(5)]
    
    def request(self, user, callback):
        self.taskq.put((user, callback))
    
    def start(self):
        for thread in self.threads:
            thread.start()
    
    def stop(self):
        for thread in self.threads:
            thread.final = True
        for thraed in self.threads:
            thread.join()




# Models
class Model(object):
    """mechanism for listening event and callback
    """
    def __init__(self):
        self._listener = []
    def addlistener(self, lis):
        self._listener.append(lis)
    def update(self):
        for lis in self._listener:
            lis()


class TweetAPI(Model):
    """API Wrapper for twitter api
    """
    def __init__(self, consumer_key, consumer_secret, use_https=True, maxhistentries=400):
        Model.__init__(self)
        self.maxhistentries = maxhistentries
        
        self.oauth = twitterlib.TwitterOAuth(consumer_key, consumer_secret, use_https)
        self.api = twitterlib.API(self.oauth)
        
        self.user = None # will be assigned when oauth authentication complete.
        
        self.tweets = []
        self.updateQueue = []
        self.lasttweetid = None

        self.container = UserImageContainer()
    def post(self, msg):
        self.api.statuses.update(status=msg)
        self.update()
    def retweet(self, status):
        tid = int(status.id)
        self.api.statuses.retweet(id=tid)
    def update(self):
        if self.lasttweetid is None:
            statuses = self.api.statuses.home_timeline()
        else:
            statuses = self.api.statuses.home_timeline(since_id=self.lasttweetid)
        statuses = list(reversed(statuses))
        # start asyncronous load user icon
        for status in statuses:
            self.container.requestImageAsync(status.user, lambda user, bmp: None)
        self.tweets = (statuses + self.tweets)[:self.maxhistentries]
        self.updateQueue.extend(statuses[:self.maxhistentries])
        super(TweetAPI, self).update()
    def normalize(self, status):
        return (str(status.id), status.user.screen_name, unescape(status.text))
    def newStatuses(self):
        for t in self.updateQueue:
            yield self.normalize(t)
        self.updateQueue = []
    def __iter__(self):
        for t in self.tweets:
            yield self.normalize(t)
    def __getitem__(self, index):
        return self.tweets[index]
    def __len__(self):
        return len(self.tweets)

    def setUser(self):
        # oauth authentication
        self.user = self.api.account.verify_credentials()
    
    def lookup(self, sel):
        for status in self.tweets:
            if long(sel[0]) == status.id:
                return status
    
    def insertStatus(self, status):
        self.tweets.insert(0, status)
        if len(self.tweets) > self.maxhistentries:
            self.tweets.pop()
        

class StatusIdList(object):
    def __init__(self, statuses):
        self.statuses = statuses
    def __getitem__(self, index):
        return self.statuses[index].id
    def __len__(self):
        return len(self.statuses)


API = None


import threading
class TweetAPIThread(threading.Thread):
    """thread for receiving streaming api data and update ui
    """
    def __init__(self, tweetapi, ctrl):
        threading.Thread.__init__(self)
        self.tweetapi = tweetapi
        self.ctrl = ctrl
        self.final = False
    def run(self):
        self.tweetapi.container.start() # run image server
        for tweet in self.tweetapi.api.userstreaming.user():
            if self.final:
                break
            if not 'user' in tweet: continue
            self.tweetapi.insertStatus(tweet)
            self.ctrl.insertStatus(self.tweetapi.normalize(tweet))
    def stop(self):
        self.final = True
APIThread = None

# GUI Controller
class DisplayCtrl(object):
    """one of main gui parts on TwitterCtrl
    displaying current tweet information
    """
    def __init__(self, parent):
        self.parent = parent
        self.image  = xrc.XRCCTRL(parent, 'display_userimage') # StaticBitmap
        self.name   = xrc.XRCCTRL(parent, 'display_username')  # TextCtrl
        self.text   = xrc.XRCCTRL(parent, 'display_usertext')  # TextCtrl
        self.date   = xrc.XRCCTRL(parent, 'display_timestamp') # StaticText
        self.screen_name = None
        
        self.emp = self.image.GetBitmap()
        
        # events
    def display(self, status):
        def dateFromString(s):
            r = datetime.datetime.strptime(s, '%a %b %d %H:%M:%S +0000 %Y')
            # UTC -> Asia/Tokyo
            r = r + datetime.timedelta(hours=9)
            r = r.strftime('%m/%d\n%H:%M:%S')
            return r
        if self.screen_name != status.user.screen_name:
            self.image.SetBitmap(self.emp)
            #self.image.SetBitmap(API.container.requestImage(status.user))
            self.screen_name = status.user.screen_name
            API.container.requestImageAsync(status.user, self.onload)
        
        self.name.SetValue(u'%s / %s' % (status.user.name, status.user.screen_name))
        self.text.SetValue(unescape(status.text))
        self.date.SetLabel(dateFromString(status.created_at))
    def onload(self, user, bmp):
        if self.screen_name == user.screen_name:
            self.image.SetBitmap(bmp)
        self.image.Refresh()
        


class TweetListCtrl(object):
    """one of main gui parts on TwitterCtrl
    displaying timeline
    """
    def __init__(self, parent, displayctrl, postctrl):
        self.parent = parent
        self.displayctrl = displayctrl
        self.postctrl = postctrl
        self.list   = xrc.XRCCTRL(parent, 'tweetlist') # ListCtrl
        #
        self.list.InsertColumn(0, u'tweetid')
        self.list.InsertColumn(0, u'name')
        self.list.InsertColumn(0, u'post')
        
        self.list.SetColumnWidth(0, 0)
        self.w_name = 90
        self.list.SetColumnWidth(1, self.w_name)
        
        # events
        self.list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.onSelect)
        self.list.Bind(wx.EVT_SIZE, self.onSize)
        self.list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.onActivated)
        self.list.Bind(wx.EVT_KEY_DOWN, self.onKeyDown)
        
        self.onSize(None)
    def selectedItem(self):
        index = self.list.GetFirstSelected() # => int
        lst = self.list
        sel = tuple(lst.GetItem(index, i).GetText() for i in range(lst.GetColumnCount()))
        return sel
    def onSelect(self, event):
        item = self.selectedItem()
        self.displayctrl.display(API.lookup(item))
    def onActivated(self, event):
        # open url: enter or double click
        tid,name,text = self.selectedItem()
        found = re.findall(r'https?://\S+', text)
        if found != []:
            webbrowser.open_new_tab(found[0])
    def onSize(self, event):
        w,h = self.list.GetSize()
        w -= 10 + self.w_name
        self.list.SetColumnWidth(2, w)
        if event:
            event.Skip()
    def onKeyDown(self, event):
        # RT: Control + Alt + R
        if event.ControlDown() and event.AltDown() and event.GetKeyCode() in [ord('R'), ord('r')]:
            name,text = self.selectedItem()
            self.postctrl.text.SetValue('RT @' + name + ' ' + text)
        # Official RT: Control + Alt + X
        if event.ControlDown() and event.AltDown() and event.GetKeyCode() in [ord('X'), ord('x')]:
            status = API.lookup(self.selectedItem())
            API.retweet(status)
            mes = u'RT \n%s\n%s' % (status.user.screen_name, status.text)
            dialog = wx.MessageDialog(None, mes, u'RT', wx.OK|wx.ICON_INFORMATION)
            dialog.ShowModal()
            dialog.Destroy()
        event.Skip()


class PostCtrl(object):
    """one of main gui parts on TwitterCtrl
    for updating status
    """
    def __init__(self, parent):
        self.parent = parent
        self.text   = xrc.XRCCTRL(parent, 'post_text') # TextCtrl
        self.count  = xrc.XRCCTRL(parent, 'post_wordcounter') # StaticText
        self.button = xrc.XRCCTRL(parent, 'post_update') # Button
        # events
        self.text.Bind(wx.EVT_TEXT, self.onText)
        self.text.Bind(wx.EVT_TEXT_ENTER, self.onPost)
        self.button.Bind(wx.EVT_BUTTON, self.onPost)
    def onText(self, event):
        length = self.text.GetLineLength(0)
        c = ['black', 'red'][length > 140]
        self.count.SetLabel(str(length))
        self.count.SetForegroundColour(c)
    def onPost(self, event):
        text = self.text.GetValue()
        if 0 < len(text) <= 140:
            API.post(text)
            self.text.SetValue('')


class TwitterFrameCtrl(object):
    """main window of this application.
    """
    def __init__(self, resource):
        self.res         = resource
        self.frame       = self.res.LoadFrame(None, 'SimpleTweetFrame')
        self.displayctrl = DisplayCtrl(self.frame)
        self.postctrl    = PostCtrl(self.frame)
        self.listctrl    = TweetListCtrl(self.frame, self.displayctrl, self.postctrl)
        
      
        #self.tick = 60 # seconds
        #self.count = self.tick
        # events
        self.frame.Bind(wx.EVT_KEY_DOWN, self.onKeyDown)
        self.frame.Bind(wx.EVT_CLOSE, self.onClose)
        #self.frame.Bind(wx.EVT_TIMER, self.onTimer)
        #self.timer = wx.Timer(self.frame)
        #self.timer.Start(1000)

    def onClose(self, event):
        API.container.stop()
        APIThread.stop()
        APIThread.join()
        event.Skip()
    
    def insertStatus(self, normalized):
        item = normalized
        index = self.listctrl.list.InsertStringItem(0, item[0])
        for i,elem in enumerate(item[1:]):
            self.listctrl.list.SetStringItem(index, i+1, elem)
    
    def bindAPI(self):
        API.addlistener(self.reload)
        
    #def onTimer(self, event):
    #    if API is None:
    #        return
    #    self.count -= 1
    #    if self.count == 0:
    #        API.update()
    #        self.count = self.tick
    #    self.frame.SetStatusText(u'next update: ' + str(self.count) + u'sec', 0)
    #    event.Skip()
    def onKeyDown(self, event):
        key = event.KeyCode
        if event.ControlDown() and key in [ord('r'), ord('R')]:
            API.update()
        event.Skip()
    def reload(self):
        for rowdata in API.newStatuses():
            self.insertStatus(rowdata)
        self.listctrl.list.Update()


class MyApp(wx.App):
    def OnInit(self):
        self.res = xrc.XmlResource('resource.xrc')
        self.ctrl = TwitterFrameCtrl(self.res)
        self.authdialog = AuthDialog(self.res)
        return True


app = MyApp(0)
# do oauth
app.authdialog.dialog.ShowModal()
# initialize ui
app.ctrl.bindAPI()

APIThread.start()
API.update()

# show main window
app.ctrl.frame.Show()
app.MainLoop()

