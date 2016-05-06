#coding=utf-8

import requests, codecs, re
from models import Message
from bs4 import BeautifulSoup, SoupStrainer

print("Modules loaded.\n")

class MatchManager():

    def matcher(self,messageObject):
        youtubeResult = None         
       
        youtubeResult = re.search(self.youtubeRe, messageObject.message)
        if youtubeResult and messageObject.author != "Malbolge":
            return self.youtube(youtubeResult.group(0),messageObject)
 
        return False

    def youtube(self,url,message):
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/37.0.2062.94 Chrome/37.0.2062.94 Safari/537.36'
        }
        url += 'http://'
        result = requests.get(url, headers=headers)
        only_the_title = SoupStrainer('meta', attrs={'name': 'title'})
        try:
            contentMeta = BeautifulSoup(
                result.text,'lxml',parse_only=only_the_title).meta['content']
        except KeyError:
            contentMeta = None
        if contentMeta:
            return message.author + ' has posted a video: ' + contentMeta
        else:
            return message.author + ', unrecognized video'
    
    def __init__(self):
        self.youtubeRe = (
        '(youtube|youtu|youtube-nocookie)\.(com|be)/'
        '(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
        )


class NetworkManager():
    URL_BASE = 'http://<forum_address>/index.php'
    LIST_XML = '?action=shoutbox;sa=get;xml;row=0'

    def __init__(self):
        self.session = requests.session()

    def login(self, username, password):
        '''
        Let's not mince words here: this is a ghetto-ass way to extract the
        session token from the response, a holdover from the last incarnation
        of the bot.
        '''

        #To do: rewrite this to use something less dumb than searching through
        #the entire response.text
        
        formdata = {
            'user': username,
            'passwrd': password,
            'cookielength': '1'
        }
        response = self.session.post(self.__class__.URL_BASE + self.__class__.LOGIN_URL, data=formdata)
        m = re.search(r"sSessionId: '(?P<sessionToken>.+)'", response.text)
        token = m.group('sessionToken').encode('ascii')
        return token

    def writeToTestFile(self,messages):
        #Disused. Can be repurposed to allow for keeping of a message log.
        with codecs.open('testiiii2 .txt','w','utf-8') as f:
            for message in messages:
                f.write(message.printable + '\n')

    def main(self):
        response = self.session.get(self.__class__.URL_BASE + self.__class__.LIST_XML)
        messages = Message.getMessageList(response)
        return messages

class Bot(object):
    def __enter__(self):
        return NetworkManager()

    def __exit__(self, exc_type, exc_value, traceback):
        Message.storeLastMsg()
        print('Program terminated.')
        return isinstance(exc_value, KeyboardInterrupt)

