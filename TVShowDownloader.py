from ConfigParser import SafeConfigParser
import os
import requests
import pickle
from lxml import html
import shutil

CONFIG_FILE = "config.cfg"

parser = SafeConfigParser()
parser.read(CONFIG_FILE)

USER = parser.get("DEFAULT", "username")
PASS = parser.get("DEFAULT", "password")
QUALITY = parser.get("DEFAULT", "quality")


def initfromcookies(session):
    if os.path.exists('cookies.txt'):
        try:
            with open('cookies.txt') as f:
                session.cookies = requests.utils.cookiejar_from_dict(pickle.load(f))
        except IOError:
            pass

    login(session)


def login(session):
    if isloggedin(session):
        return

    session.post('http://speed.cd/take.login.php', data={
        'username': USER,
        'password': PASS
    })

    with open('cookies.txt', 'w') as f:
        pickle.dump(requests.utils.dict_from_cookiejar(session.cookies), f)
        print 'saved the cookies to file'


def isloggedin(session):
    response = session.get('http://speed.cd/browse.php')
    return '/login.php' not in response.url


def isAvailable(session, query):
    response = session.get('http://speed.cd/browse.php?search=' + query)

    tree = html.fromstring(response.text)
    return not tree.xpath('//div[@id = "torrentTable"]/div/div[@class="boxContent"]/text()')

def download(session, query):
    response = session.get('http://speed.cd/browse.php?search=' + query)

    tree = html.fromstring(response.text)
    torrent = tree.xpath('//div[@id = "torrentTable"]//td/a/@href')[0]

    r = session.get('http://speed.cd/'+torrent)
    with open(query+'.torrent', 'wb') as f:
        f.write(r.content)

def next(show):
    nextEpisode = show
    nextEpisode['episode'] += 1
    return nextEpisode


def nextSeason(show):
    nextEpisode = show
    nextEpisode['season'] += 1
    nextEpisode['episode'] = 1
    return nextEpisode


def fromshowtosearch(show):
    search = '%(show)s S%(season)02dE%(episode)02d %(quality)s' % show
    search = search.replace(' ', '+')

    return search


def updatedownloadedfiles(show):
    parser.set(show['show'], 'episode', str(show['episode']))
    parser.set(show['show'], 'season', str(show['season']))

    with open(CONFIG_FILE, 'wb') as configfile:
        parser.write(configfile)


if __name__ == '__main__':
    session = requests.Session()
    initfromcookies(session)

    for showname in parser.sections():
        show = {
            'show': showname,
            'season': int(parser.get(showname, "season")),
            'episode': int(parser.get(showname, "episode")),
            'quality': QUALITY
        }

        nextEpisode = next(show)
        while isAvailable(session, fromshowtosearch(nextEpisode)):
            download(session, fromshowtosearch(nextEpisode))
            updatedownloadedfiles(nextEpisode)
            nextEpisode = next(nextEpisode)

        nextEpisode = nextSeason(show)
        while isAvailable(session, fromshowtosearch(nextEpisode)):
            download(session, fromshowtosearch(nextEpisode))
            updatedownloadedfiles(nextEpisode)
            nextEpisode = next(nextEpisode)
