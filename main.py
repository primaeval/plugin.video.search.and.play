# -*- coding: utf-8 -*-

from rpc import RPC
from xbmcswift2 import Plugin
from xbmcswift2 import actions
from xbmcswift2 import ListItem
import re
import requests
import xbmc,xbmcaddon,xbmcvfs,xbmcgui,xbmcvfs,xbmcplugin
import xbmcplugin
import base64
import random
#from HTMLParser import HTMLParser
import urllib
import sqlite3
import time,datetime
import threading
import HTMLParser
import json
import sys



plugin = Plugin()
big_list_view = False

if plugin.get_setting('english') == 'true':
    headers={
    'User-Agent' : 'Mozilla/5.0 (Windows NT 6.1; rv:50.0) Gecko/20100101 Firefox/50.0',
    'Accept-Language' : 'en-US,en;q=0.5',
    "X-Forwarded-For": "54.239.17.118"}
else:
    headers={}

def addon_id():
    return xbmcaddon.Addon().getAddonInfo('id')

def log(v):
    xbmc.log(repr(v),xbmc.LOGERROR)

#log(sys.argv)

def get_icon_path(icon_name):
    if plugin.get_setting('user.icons') == "true":
        user_icon = "special://profile/addon_data/%s/icons/%s.png" % (addon_id(),icon_name)
        if xbmcvfs.exists(user_icon):
            return user_icon
    return "special://home/addons/%s/resources/img/%s.png" % (addon_id(),icon_name)

@plugin.route('/title_page/<url>')
def title_page(url):
    for i in re.findall('date\[(\d+)\]', url):
        url = url.replace('date[%s]' % i, (datetime.datetime.now() - datetime.timedelta(days = int(i))).strftime('%Y-%m-%d'))
    global big_list_view
    big_list_view = True
    r = requests.get(url, headers=headers)
    html = r.content
    #html = HTMLParser.HTMLParser().unescape(html)

    lister_items = html.split('<div class="lister-item ')
    items = []
    for lister_item in lister_items:
        if not re.search(r'^mode-advanced">',lister_item):
            continue
        title_type = ''
        trakt_type = ''
        #loadlate="http://ia.media-imdb.com/images/M/MV5BMjIyMTg5MTg4OV5BMl5BanBnXkFtZTgwMzkzMjY5NzE@._V1_UX67_CR0,0,67,98_AL_.jpg"
        img_url = ''
        img_match = re.search(r'<img.*?loadlate="(.*?)"', lister_item, flags=(re.DOTALL | re.MULTILINE))
        if img_match:
            img = img_match.group(1)
            if plugin.get_setting('enhance') == '2':
                img_url = re.sub(r'U[XY].*_.jpg','SX344_.jpg',img) #NOTE 344 is Confluence List View width
            else:
                if plugin.get_setting('enhance') == '0':
                    img_url = img
                else:
                    img_url = re.sub(r'UX67_CR(.*?),0,67,98','UX182_CR\g<1>,0,182,268',img)
                    img_url = re.sub(r'UY98_CR(.*?),0,67,98','UY268_CR\g<1>,0,182,268',img_url)

        title = ''
        imdbID = ''
        year = ''
        #<a href="/title/tt1985949/?ref_=adv_li_tt"\n>Angry Birds</a>
        title_match = re.search(r'<a href="/title/(tt[0-9]*)/\?ref_=adv_li_tt".>(.*?)</a>', lister_item, flags=(re.DOTALL | re.MULTILINE))
        if title_match:
            imdbID = title_match.group(1)
            title = title_match.group(2)
            #log((imdbID,title))
        else:
            #log(lister_item)
            pass

        info_type = ''
        #<span class="lister-lister_item-year text-muted unbold">(2016)</span>
        #title_match = re.search(r'<span class="lister-lister_item-year text-muted unbold">.*?\(([0-9]*?)\)<\/span>', lister_item, flags=(re.DOTALL | re.MULTILINE))
        title_match = re.search(r'<span class="lister-item-year text-muted unbold">.*?\(([0-9]{4})\)<\/span>', lister_item, flags=(re.DOTALL | re.MULTILINE))
        if title_match:
            year = title_match.group(1)
            title_type = "movie"
            trakt_type = 'movies'
            info_type = 'extendedinfo'
            #log(year)
        else:
            #log(lister_item)
            #pass

            title_match = re.search(r'<span class="lister-item-year text-muted unbold">.*?\(([0-9]{4}).*?\)<\/span>', lister_item, flags=(re.DOTALL | re.MULTILINE))
            if title_match:
                year = title_match.group(1)
                title_type = "tv_series"
                trakt_type = 'shows'
                info_type = 'extendedtvinfo'
                #log(year)
            else:
                #log(lister_item)
                pass


        #Episode:</small>\n    <a href="/title/tt4480392/?ref_=adv_li_tt"\n>\'Cue Detective</a>\n    <span class="lister-lister_item-year text-muted unbold">(2015)</span>
        #Episode:</small>\n    <a href="/title/tt4952864/?ref_=adv_li_tt"\n>#TeamLucifer</a>\n    <span class="lister-lister_item-year text-muted unbold">(2016)</span
        episode = ''
        episode_id = ''
        episode_match = re.search(r'Episode:</small>\n    <a href="/title/(tt.*?)/?ref_=adv_li_tt"\n>(.*?)</a>\n    <span class="lister-lister_item-year text-muted unbold">\((.*?)\)</span>', lister_item, flags=(re.DOTALL | re.MULTILINE))
        if episode_match:
            episode_id = episode_match.group(1)
            episode = "%s (%s)" % (episode_match.group(2), episode_match.group(3))
            year = episode_match.group(3)
            title_type = "tv_episode"
            trakt_type = 'episodes'

        #Users rated this 6.1/10 (65,165 votes)
        rating = ''
        votes = ''
        rating_match = re.search(r'title="Users rated this (.+?)/10 \((.+?) votes\)', lister_item, flags=(re.DOTALL | re.MULTILINE))
        if rating_match:
            rating = rating_match.group(1)
            votes = rating_match.group(2)
            votes = re.sub(',','',votes)

        #<p class="text-muted">\nRusty Griswold takes his own family on a road trip to "Walley World" in order to spice things up with his wife and reconnect with his sons.</p>
        plot = ''
        plot_match = re.search(r'<p class="text-muted">(.+?)</p>', lister_item, flags=(re.DOTALL | re.MULTILINE))
        if plot_match:
            plot = plot_match.group(1).strip()
            plot = re.sub('<a.*?</a>','',plot)

        #Stars:\n<a href="/name/nm0255124/?ref_=adv_li_st_0"\n>Tom Ellis</a>, \n<a href="/name/nm0314514/?ref_=adv_li_st_1"\n>Lauren German</a>, \n<a href="/name/nm1204760/?ref_=adv_li_st_2"\n>Kevin Alejandro</a>, \n<a href="/name/nm0940851/?ref_=adv_li_st_3"\n>D.B. Woodside</a>\n    </p>
        cast = []
        cast_match = re.search(r'<p class="">(.*?)</p>', lister_item, flags=(re.DOTALL | re.MULTILINE))
        if cast_match:
            cast = cast_match.group(1)
            cast_list = re.findall(r'<a.+?>(.+?)</a>', cast, flags=(re.DOTALL | re.MULTILINE))
            cast = cast_list


        #<span class="genre">\nAdventure, Comedy            </span>
        genres = ''
        genre_match = re.search(r'<span class="genre">(.+?)</span>', lister_item, flags=(re.DOTALL | re.MULTILINE))
        if genre_match:
            genres = genre_match.group(1).strip()
            #genre_list = re.findall(r'<a.+?>(.+?)</a>', genre)
            #genres = ",".join(genre_list)

        #class="runtime">99 min</span>
        runtime = ''
        runtime_match = re.search(r'class="runtime">(.+?) min</span>', lister_item, flags=(re.DOTALL | re.MULTILINE))
        if runtime_match:
            runtime = int(re.sub(',','',runtime_match.group(1))) * 60

        sort = ''
        #sort_match = re.search(r'<span class="sort"><span title="(.+?)"', lister_item, flags=(re.DOTALL | re.MULTILINE))
        #if sort_match:
        #    sort = sort_match.group(1)

        #<span class="certificate">PG</span>
        certificate = ''
        certificate_match = re.search(r'<span class="certificate">(.*?)</span>', lister_item, flags=(re.DOTALL | re.MULTILINE))
        if certificate_match:
            certificate = certificate_match.group(1)

        vlabel = title
        playable = True
        if imdbID:
            id = imdbID
            #log(title_type)
            if title_type == "tv_series" or title_type == "mini_series":
                playable = False
                trakt_type = 'shows'
                meta_url = "plugin://plugin.video.imdb.search/meta_tvdb/%s/%s" % (id,urllib.quote_plus(title.encode("utf8")))
                #meta_url = "plugin://%s/tv/search_term/%s/1" % (plugin.get_setting('catchup.plugin').lower(),urllib.quote_plus(title))
            elif title_type == "tv_episode":
                vlabel = "%s - %s" % (title, episode)
                vlabel = urllib.quote_plus(vlabel.encode("utf8"))
                meta_url = "plugin://plugin.video.imdb.search/?action=episode&imdb_id=%s&episode_id=%s&title=%s" % (imdbID,episode_id,vlabel) #TODO
                id = episode_id
            else:
                imdb_id = imdbID
                xbmcvfs.mkdirs('special://profile/addon_data/plugin.video.search.and.play/Movies.temp')
                f = xbmcvfs.File('special://profile/addon_data/plugin.video.search.and.play/Movies.temp/%s.strm' % (imdb_id), "wb")
                movie_library_url = plugin.get_setting('movie.library.url')
                meta_url = plugin.get_setting('movie.library')
                if movie_library_url == "true" and meta_url:
                    meta_url = "plugin://plugin.video.search.and.play/play_movie/%s/%s/%s" % (imdb_id,year,urllib.quote_plus(title))
                else:
                    meta_url = 'plugin://%s/movies/play/imdb/%s/library' % (plugin.get_setting('catchup.plugin').lower(),imdb_id)
                f.write(meta_url.encode("utf8"))
                f.close()
                #f = xbmcvfs.File('special://profile/addon_data/plugin.video.imdb.search/Movies.temp/%s.nfo' % (imdb_id), "wb")
                #str = "http://www.imdb.com/title/%s/" % imdb_id
                #f.write(str.encode("utf8"))
                #f.close()
                meta_url = 'special://profile/addon_data/plugin.video.search.and.play/Movies.temp/%s.strm' % (imdb_id)
            #log(meta_url)
        if imdbID:
            item = ListItem(label=title,thumbnail=img_url,path=meta_url)
            item.set_is_playable(playable)
            item.set_info('video', {'title': vlabel, 'genre': genres,'code': imdbID,
            'year':year,'mediatype':'movie','rating':rating,'plot': plot,
            'mpaa': certificate,'cast': cast,'duration': runtime, 'votes': votes})
            video_streaminfo = {'codec': 'h264'}
            video_streaminfo['aspect'] = round(1280.0 / 720.0, 2)
            video_streaminfo['width'] = 1280
            video_streaminfo['height'] = 720
            item.add_stream_info('video', video_streaminfo)
            item.add_stream_info('audio', {'codec': 'aac', 'language': 'en', 'channels': 2})
            context_items = []
            '''
            context_items.append(('Information', 'XBMC.Action(Info)'))
            try:
                if info_type and xbmcaddon.Addon('script.extendedinfo'):
                    context_items.append(('Extended Info', "XBMC.RunScript(script.extendedinfo,info=%s,imdb_id=%s)" % (info_type,imdbID)))
            except:
                pass
            #context_items.append(('Add to Trakt Watchlist', 'XBMC.RunPlugin(%s)' % (plugin.url_for('add_to_trakt_watchlist', type=trakt_type, imdb_id=imdbID, title=title))))
            try:
                if title_type == 'movie' and xbmcaddon.Addon('plugin.video.couchpotato_manager'):
                    context_items.append(('Add to Couch Potato', "XBMC.RunPlugin(plugin://plugin.video.couchpotato_manager/movies/add-by-id/%s)" % imdbID))
            except:
                pass
            if title_type == "tv_series" or title_type == "mini_series":
                try:
                    if xbmcaddon.Addon('plugin.video.sickrage'):
                        context_items.append(('Add to Sickrage', "XBMC.RunPlugin(plugin://plugin.video.sickrage?action=addshow&&show_name=%s)" % title))
                except:
                    context_items.append(('Add to Sickrage', 'XBMC.RunPlugin(%s)' % (plugin.url_for('sickrage_addshow', title=title))))

            item.add_context_menu_items(context_items)
            '''
            items.append(item)

    #href="?count=50&sort=moviemeter,asc&production_status=released&languages=en&release_date=2015,2016&boxoffice_gross_us=6.0,10.0&start=1&num_votes=100,&title_type=feature&page=2&ref_=adv_nxt"
    pagination_match = re.findall('<a href="([^"]*?&ref_=adv_nxt)"', html, flags=(re.DOTALL | re.MULTILINE))
    if pagination_match:
        next_page = 'http://www.imdb.com/search/title?'+pagination_match[-1].strip('?')
        #log(next_page)
        items.append(
        {
            'label': "Next Page >>",
            'path': plugin.url_for('title_page', url=next_page),
            'thumbnail': get_icon_path('nextpage'),
        })

    return items

def trakt_id(imdb_id):
    from urllib2 import Request, urlopen

    headers = {
      'Content-Type': 'application/json',
      'trakt-api-version': '2',
      'trakt-api-key': base64.b64decode('NDJiYTBhYzg1MDRkYWM3ZjMwODUyNDBiYjIwNWMzNTFiM2UxNDk3MzRkYWU5MjhiOWI2YmU3N2UwZTE0ZmM2Yg==')
    }
    request = Request('https://api.trakt.tv/search/imdb/%s' % imdb_id, headers=headers)

    response_body = urlopen(request).read()
    match = re.search('"trakt":([0-9]*)',response_body)
    if match:
        id = match.group(1)
        return id

@plugin.route('/play_movie/<imdb_id>/<year>/<title>')
def play_movie(imdb_id,year,title):
    xbmcvfs.mkdirs('special://profile/addon_data/plugin.video.search.and.play/Movies.play')
    name = 'special://profile/addon_data/plugin.video.search.and.play/Movies.play/%s.strm' % (imdb_id)
    f = xbmcvfs.File(name, "wb")
    movie_library_url = plugin.get_setting('movie.library.url')
    number = plugin.get_setting('movie.library.number')
    if number == "0":
        meta_url = plugin.get_setting('movie.library')
        movie_library_addon = plugin.get_setting('movie.library.addon')
    elif number == "1":
        meta_url = plugin.get_setting('movie.library2')
        movie_library_addon = plugin.get_setting('movie.library2.addon')
    else:
        meta_url = plugin.get_setting('movie.library3')
        movie_library_addon = plugin.get_setting('movie.library3.addon')
    if movie_library_url == "true" and meta_url:
        if movie_library_addon:
            meta_url = re.sub('plugin://.*?/','plugin://%s/' % movie_library_addon,meta_url)
        if "%M" in meta_url:
            what = base64.b64decode('aHR0cHM6Ly9hcGkudGhlbW92aWVkYi5vcmcvMy9maW5kLyVzP2FwaV9rZXk9ZDY5OTkyZWM4MTBkMGY0MTRkM2RlNGEyMjk0Yjg3MDAmbGFuZ3VhZ2U9ZW4tVVMmZXh0ZXJuYWxfc291cmNlPWltZGJfaWQ=')
            url = what % imdb_id
            html = requests.get(url).content
            match = re.search('"id":([0-9]*)',html)
            if match:
                id = match.group(1)
                meta_url = meta_url.replace("%M",id)
        if "%K" in meta_url:
            trakt = trakt_id(imdb_id)
            meta_url = meta_url.replace("%K",trakt)
        meta_url = meta_url.replace("%Y",year)
        meta_url = meta_url.replace("%I",imdb_id)
        meta_url = meta_url.replace("%T",urllib.quote_plus(title))

    else:
        meta_url = 'plugin://%s/movies/play/imdb/%s/library' % (plugin.get_setting('catchup.plugin').lower(),imdb_id)
    f.write(meta_url.encode("utf8"))
    f.close()
    item = ListItem(label=title,thumbnail=get_icon_path('settings'),path=meta_url)
    return plugin.set_resolved_url(item)

@plugin.route('/play_movie_play/<imdb_id>/<year>/<title>')
def play_movie_play(imdb_id,year,title):
    item = play_movie(imdb_id,year,title)
    xbmc.Player().play(item[0].get_path())

@plugin.route('/movie_search/<title>')
def movie_search(title):
    # latest|recent movies
    # star wars
    # latest star wars movie
    # recent star wars movies
    # recent star wars movies sorted by date descending
    # sci-fi movies
    # latest sci-fi movies
    # recent sci-fi movies
    # movies starring brad pitt
    # movies with a plot about  berlin
    # movies filmed in berlin
    # best recent sci-fi movies called star wars with a plot about paris filmed in berlin starring brad pitt
    autoplay = False
    language = "&languages=en"

    title = title.lower()
    if title.startswith("the "):
        title = ' '.join(title.split()[1:])

    if title.startswith("awful") or title.startswith("worst"):
        title = ' '.join(title.split()[1:])
        rating = "&user_rating=,3.0"
    elif title.startswith("bad"):
        title = ' '.join(title.split()[1:])
        rating = "&user_rating=,5.0"
    elif title.startswith("good"):
        title = ' '.join(title.split()[1:])
        rating = "&user_rating=6.0,"
    elif title.startswith("best"):
        title = ' '.join(title.split()[1:])
        rating = "&user_rating=7.0,"
    else:
        rating = ""

    votes = plugin.get_setting('votes')
    if votes:
        votes = "&num_votes=%s," % votes

    if title.startswith("recent"):
        title = ' '.join(title.split()[1:])
        days=365
        since = (datetime.datetime.now() - datetime.timedelta(days = int(days))).strftime('%Y-%m-%d')
        recent = "&release_date=%s," % since
    elif title.startswith("latest"):
        title = ' '.join(title.split()[1:])
        days=90
        since = (datetime.datetime.now() - datetime.timedelta(days = int(days))).strftime('%Y-%m-%d')
        recent = "&release_date=%s," % since
    else:
        recent = ""

    found_genre = ""
    genres = ["action", "adventure", "animation", "biography",  "comedy", "crime", "documentary", "drama", "family", "fantasy", "film noir", "game show", "history", "horror", "music", "musical", "mystery", "news", "reality tv", "romance", "sci-fi", "sport", "talk show", "thriller", "war", "western"]
    for g in genres:
        search = g + ' ' + "movies"
        if title.startswith(search):
            found_genre = g
            title = title.replace(search,'')
            break
    if found_genre:
        g = found_genre.replace('-','_').replace(' ','_')
        genre = "&genres=%s" % g
    else:
        genre = ""
    extra_genres = plugin.get_setting('genres')
    if extra_genres:
        if genre:
            genre = genre + ',' + extra_genres
        else:
            genre = "&genres=%s" % extra_genres

    role = ""
    if "starring" in title:
        title,who = title.split('starring')
        title = title.strip()
        who = who.strip().replace(' ','_')
        html = requests.get('https://v2.sg.media-imdb.com/suggests/names/%s/%s.json' % (who[0],who),headers=headers).content
        match = re.search('"id":"(nm[0-9]*)"',html)
        if match:
            id = match.group(1)
            role = "&role=%s" % id


    location = ""
    if "filmed in"  in title:
        title,where = title.split('filmed in')
        title = title.strip()
        where = where.strip().replace(' ','+')
        location = "&locations=%s" % where

    plot = ""
    if "with a plot about"  in title:
        title,words = title.split('with a plot about')
        title = title.strip()
        words = words.strip().replace(' ','+')
        plot = "&plot=%s" % words

    sort = ""
    if title in ["movies" , "movie"]:
        title = ""
    if title:
        title = "&title=%s" % title.replace(' ','+')
        autoplay = True
        if plugin.get_setting('order') == '1':
            sort = "&sort=year,asc"

    url = "http://www.imdb.com/search/title?count=50&production_status=released&title_type=feature"
    url = url + recent + rating + language + genre + role + location + plot + votes + sort + title
    log(url)
    #xbmcgui.Dialog().notification("title", genres)
    results = title_page(url)
    if autoplay and plugin.get_setting('autoplay') == 'true':
        xbmc.Player().play(results[0]._path)
    return results


@plugin.route('/movie_search_dialog')
def movie_search_dialog():
    d = xbmcgui.Dialog()
    title = d.input("Movie Title")
    if title:
        #url = "http://www.imdb.com/search/title?count=50&production_status=released&title_type=feature,tv_movie&title=%s&sort=year,asc" % who.replace(' ','+')
        return movie_search(title)

@plugin.route('/play/<url>')
def play(url):
    xbmc.executebuiltin('PlayMedia("%s")' % url)

@plugin.route('/execute/<url>')
def execute(url):
    xbmc.executebuiltin(url)

@plugin.route('/')
def index():
    items = []
    items.append(
    {
        'label': "Simple Movie Title Search",
        'path': plugin.url_for('movie_search_dialog'),
        'thumbnail':get_icon_path('search'),

    })
    items.append(
    {
        'label': "Test Simple Movie Title Search (Star Wars)",
        #'path': plugin.url_for('movie_search',title="sci-fi movies containing the words death star filmed in tunisia starring mark hamill"),
        'path': plugin.url_for('movie_search',title="star wars"),
        'thumbnail':get_icon_path('search'),

    })
    return items



if __name__ == '__main__':

    plugin.run()
    if big_list_view == True:
        view_mode = int(plugin.get_setting('view'))
        if view_mode:
            #pass
            plugin.set_view_mode(view_mode)
