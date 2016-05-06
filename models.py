from bs4 import BeautifulSoup, SoupStrainer
import re, sys, pickle
import json

class Message:
    lastMsg = ''
    
    def __init__(self,author,time,message,links,printable):
        self.author = author
        self.time = time
        self.message = message
        self.links = links
        self.printable = printable

    def __str__(self):
        return self.printable.encode(sys.stdout.encoding,'ignore')

    @staticmethod
    def getMessageList(response):
        '''
        Accepts a Requests response object. Verifies the validity of the
        contents of its 'text' attribute and handles some errors when the
        attribute is invalid.
        Returns a list of processed new messages for the bot to use.
        '''
        response = response.text
        if not response: return []
        try:
            assert('<?xml version="1.0" encoding="UTF-8"?>' in response)
        except AssertionError:
            #This part of the code was copied directly from the main loop
            #function from one of the previous versions of the bot,
            #so it doesn't actually do anything except printing a message.
            #Should probably change this to return an AssertionError
            #to be handled further down the pipeline.
            print("Invalid response. The server might be experiencing problems.\nRetrying in {} seconds".format(300))
            return []
        response = response.replace('<![CDATA[','',1)
        onlyTheMessages = SoupStrainer('tr',id=re.compile("^shoutbox_row([0-9]+)"))
        raw = BeautifulSoup(response, 'lxml',parse_only=onlyTheMessages).contents
        new = Message.getNewMsgs(raw,Message.getLastMsg())
        return map(Message.process, new)

    @staticmethod
    def getNewMsgs(other, recent):
        '''
        Assumes other is a list of messages of length at least 1.
        Takes messages from other and compares them one by one against the most
        recent registered message. Stops if the two are the same. Skips the check
        altogether if the list is reasonably short (defined here as <= 10).
        Always updates the most recent message. Returns a list of new messages.
        (We don't expect there to be more than 1 new message at a time.)
        (The <= 10 rule should allow for registering repeating messages that
        aren't ultra excessive flood.)
        '''

        if len(other) <= 10:
            Message.setLastMsg(str(other[-1].contents))
            return other
        
        for i in xrange(len(other) -1, -1, -1):
            if recent == str(other[i].contents):
                break
        Message.setLastMsg(str(other[-1].contents))
        return other[i:]
    
    @staticmethod
    def process(message):
        '''
        Takes a single message in HTML format, enclosed in a <tr> tag with the
        id="shoutbox_rowX", where X is some number. Strips all the <a> and <img>
        tags (THIS MUTATES THE TREE, but that's a desired effect here),
        finds the date, name of the author and body of the message. Returns
        the entire message (for now) in writable format, along with some other
        useful information. Assumes all <img> tags have an 'alt' attribute
        (img.has_attr('alt') = True).

        Operates under the assumption that each message is divided into two
        table cells (<td>), where the second one contains the body and
        formatting of the message, and the first one stores the name and the
        date (unless it's a "/me" kind of message).
        '''
        segment1 = message.td
        segment2 = message.td.next_sibling
        time = segment1.span.string
        links = []
        
        if len(list(segment1.strings)) == 4:
            name = segment1.a.string
            body = segment2.span
        else:
            name = segment2.span.next_element.rstrip()
            body = segment2.span.span

        for link in body.find_all('a'):
            links.append(link['href'])
            link.replace_with(link['href'])

        for image in body.find_all('img'):
            image.replace_with(image['alt'])

        body = body.get_text() #identical with segment2.get_text()

        return Message(name,time,body,links,segment1.get_text().lstrip() + ' ' + body)

    @classmethod
    def getLastMsg(cls):
        if cls.lastMsg:
            return cls.lastMsg
        try:
            with open('lastmsg','r') as f:
                return pickle.load(f)
        except IOError:
            print("Warning: Last message file not found.")
            return ''

    @classmethod
    def setLastMsg(cls,msg):
        cls.lastMsg = msg
    
    @classmethod
    def storeLastMsg(cls):
        with open('lastmsg','w') as f:
            pickle.dump(cls.lastMsg,f)


class Database:
    def __init__(self,dbPath):
        self.dbPath = dbPath
        self.tables = {}
        for table in ['userstats']:
            self.tables[table] = self.load(table)

    def getPath(self):
        return self.dbPath
        
    def getTable(self,name):
        return self.tables[name]
        
    def getTableList(self):
        return self.tables.keys()

    def updateUserRecord(self,message):
        userStats = self.getTable('userstats')
        record = userStats.setdefault(message.author, {
            'msgCount' : 0,
            'totalLen' : 0,
            'linksPosted' : 0,
            'activityPattern' : [0 for i in range(24)]
            })
        record['msgCount'] += 1
        record['totalLen'] += len(message.message)
        record['linksPosted'] += len(message.links)
        hour = int(message.time[1:3]) % 24
        record['activityPattern'][hour] += 1

    def save(self,table):
        with open(self.getPath() + table, 'w') as datafile:
            json.dump(self.getTable(table), datafile)

    def load(self,table):
        try:
            with open(self.getPath() + table) as datafile:
                return json.load(datafile)
        except IOError:
            print("Table '{}' not found, creating a new one.".format(table))
            return {}

class DatabaseConnection(object):
    '''
    Usage:
    
        with DatabaseConnection() as <variable>:
            <variable>.doStuff(vars)
        
    And then you just call the Database class methods through <variable>
    as normal.
    
    This connection makes sure that all changes to the database are saved to
    a file when exiting the 'with' segment. Saving the changes at the end is
    probably what you want, and using this class is more convenient and
    readable than using "try" and "finally" statements.
    '''
    def __enter__(self, dbPath = ''):
        self.db = Database(dbPath)
        return self.db
    def __exit__(self, exc_type, exc_value, traceback):
        for table in self.db.getTableList():
            self.db.save(table)
        print("All statistics tables saved successfully.")
        return isinstance(exc_value, KeyboardInterrupt)
