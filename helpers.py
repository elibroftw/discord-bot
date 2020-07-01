from __future__ import unicode_literals
import glob
import isodate
import smtplib
from bson.objectid import ObjectId
from collections import OrderedDict
from contextlib import suppress
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
# noinspection PyUnresolvedReferences
from pprint import pprint
import time

import requests
from discord import opus
from pymongo import MongoClient
import tweepy
import re
import os
import json
from urllib.parse import urlparse, urlencode, parse_qs, urlsplit
from mutagen.mp3 import MP3
from mutagen import MutagenError
import subprocess
from subprocess import PIPE, DEVNULL
import pymongo.collection
from pathlib import Path
if __name__ != '__main__':
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    subprocess.call('pip install --user --upgrade youtube-dl', startupinfo=startupinfo, stdout=DEVNULL, stderr=DEVNULL)
import youtube_dl

db_client = MongoClient('localhost', 27017)
db = db_client.discord_bot
playlists_coll: pymongo.collection.Collection = db.playlists
dm_coll: pymongo.collection.Collection = db.anon_messages
portfolio_coll: pymongo.collection.Collection = db.portfolios
FFMPEG = Path(subprocess.check_output('where ffmpeg').decode()).parent
# save_coll: pymongo.collection.Collection = db.save_coll  # saving the state of the bot instead of a save.json


def backup_db():
    # should be run every startup
    backup = {}
    for collection in db.list_collection_names():
        cursor = db[collection].find({})
        backup[collection] = [document for document in cursor]

    def _default(o):
        if isinstance(o, ObjectId):
            return str(o)
        return json.JSONEncoder.default(o)

    with open('mongodb_backup.json', 'w') as fp:
        json.dump(backup, fp, default=_default)  # no indent because that takes up space


def db_from_backup(filename='mongodb_backup.json'):
    with open(filename) as fp:
        backup = json.load(fp)
    for collection_name in backup:
        collection: pymongo.collection.Collection = db[collection_name]
        collection.drop()
        for document in backup[collection_name]: collection.insert_one(document)


class Song:
    __slots__ = ('title', '_video_id', '_time_stamp', 'start_time', 'status', 'length')

    def __init__(self, title, video_id, time_stamp=0):
        self.title = title
        self._video_id = video_id
        self._time_stamp = time_stamp
        self.start_time = None
        self.status = 'NOT PLAYING'
        self.length = 'DOWNLOADING'

    def __hash__(self):
        return hash(self._video_id)

    def __repr__(self):
        return f'Song({self.title}, {self._video_id}, {self.get_time_stamp()})'

    def __str__(self, show_length=False):
        return f'Song({self.title}, {self._video_id}, {self.get_time_stamp()}, length={self.get_length()})'

    def __eq__(self, other):
        return self.__class__ == other.__class__ and other.get_video_id() == self._video_id

    def start(self, start_at=None):
        if start_at is None: start_at = self._time_stamp
        self.status = 'PLAYING'
        self.start_time = time.time() - start_at

    def play(self):
        self.start()

    def pause(self):
        self.status = 'PAUSED'
        self._time_stamp = time.time() - self.start_time

    def stop(self):
        self.status = 'NOT PLAYING'
        self._time_stamp = 0

    def get_length(self, string=False):
        if self.length == 'DOWNLOADING':
            try:
                audio = MP3(f'music/{self._video_id}.mp3')
                temp = audio.info.length
                if temp == 0: raise MutagenError
                self.length = temp
            except MutagenError: return 'DOWNLOADING'
        if string:
            temp = round(self.length)
            minutes = temp // 60
            seconds = temp % 60
            if minutes < 10: minutes = f'0{minutes}'
            if seconds < 10: seconds = f'0{seconds}'
            return f'{minutes}:{seconds}'
        return self.length

    def get_time_stamp(self, string=False):
        if self.status == 'PLAYING':
            self._time_stamp = time.time() - self.start_time
        if string:
            song_length = self.get_length(True)
            if song_length in ('DOWNLOADING', '00:00'): return ''
            temp = round(self._time_stamp)
            minutes = temp // 60
            seconds = temp % 60
            if minutes < 10: minutes = f'0{minutes}'
            if seconds < 10: seconds = f'0{seconds}'
            return f'[{minutes}:{seconds} - {song_length}]'
        return self._time_stamp

    def set_time_stamp(self, seconds):
        self._time_stamp = seconds

    def forward(self, seconds):
        self.start_time -= seconds
    fwd = forward

    def rewind(self, seconds):
        self.start_time += seconds
    rwd = rewind

    def get_status(self):
        return self.status

    def get_video_id(self):
        return self._video_id

    def to_dict(self):
        return {'title': self.title, 'video_id': self._video_id, 'status': self.status,
                'time_stamp': self.get_time_stamp()}


try: GOOGLE_API = os.environ['google']
except KeyError:
    from environs import Env

    env = Env()
    env.read_env()
    GOOGLE_API = os.environ['google']


YT_API_URL = 'https://www.googleapis.com/youtube/v3/'
twitter_auth = tweepy.OAuthHandler(os.environ['TWITTER_CONSUMER_KEY'], os.environ['TWITTER_CONSUMER_SECRET'])
twitter_auth.set_access_token(os.environ['TWITTER_ACCESS_TOKEN'], os.environ['TWITTER_ACCESS_TOKEN_SECRET'])
TWITTER_API = tweepy.API(twitter_auth)


def file_friendly_title(title):
    return title.replace('&quot;', '\'').replace('&amp;', '&').replace(
        '/', '_').replace('?', '').replace(':', ' -').replace('&#39;', "'").replace(' || ', '_')


def fix_youtube_title(title):
    return title.replace('&quot;', '\'').replace('&amp;', '&').replace('&#39;', "'")


def youtube_search(text, return_info=False, limit_duration=False, duration_limit=600):
    if text in ('maagnolia', 'magnolia') and return_info:
        text = 'magnolia (Audio)'
    # icon = 'https://cdn4.iconfinder.com/data/icons/social-media-icons-the-circle-set/48/youtube_circle-512.png'
    p = re.compile('--[1-4][0-9]|--[1-2]')
    try: results = int(p.search(text).group()[2:])
    except AttributeError: results = 1
    p = re.compile('--channel|--playlist')  # defaults to video so I removed --video
    try: kind = p.search(text).group()[2:]
    except AttributeError: kind = 'video'
    with suppress(ValueError): text = text[text.index(' '):text.index('--')]
    f = {'part': 'id,snippet', 'maxResults': min(results + 5, 50), 'order': 'relevance',
         'q': text, 'type': kind, 'key': GOOGLE_API}
    query_string = urlencode(f)
    r = requests.get(f'{YT_API_URL}search?{query_string}')
    search_response = json.loads(r.text)
    videos, channels, play_lists = OrderedDict(), [], []
    # Add each result to the appropriate list, and then display the lists of
    # matching videos, channels, and playlists.
    for search_result in search_response.get('items', []):
        if search_result['id']['kind'] == 'youtube#video':
            if search_result['snippet']['liveBroadcastContent'] == 'none' or not return_info:
                title = search_result['snippet']['title']
                video_id = search_result['id']['videoId']
                desc = search_result['snippet']['description'][:160]
                videos[video_id] = [title, desc]
        elif search_result['id']['kind'] == 'youtube#channel':
            channels.append([f'{search_result["snippet"]["title"]}', f'{search_result["id"]["channelId"]}'])
        elif search_result['id']['kind'] == 'youtube#playlist':
            play_lists.append([f'{search_result["snippet"]["title"]}', f'{search_result["id"]["playlistId"]}'])
    title, video_id, desc, channel_id, playlist_id, an_id = None, None, None, None, None, None
    if limit_duration:
        duration_dict = get_video_durations(videos.keys())
        for video_id, duration in duration_dict.items():
            if duration > duration_limit: videos.pop(video_id)

    if kind == 'video':
        results = min(len(videos), results - 1)
        video_id = list(videos.items())[results][0]
        # video_id = videos_list[result]
        title, desc = videos[video_id]
    else:
        a = channels if kind == 'channel' else play_lists
        results = min(len(a), results - 1)
        an_id = a[results][1]
        playlist_id = channel_id = an_id
    url_dict = {'video': f'https://www.youtube.com/watch?v={video_id}',
                'channel': f'https://www.youtube.com/channel/{channel_id}',
                'playlist': f'https://www.youtube.com/playlist?list={playlist_id}'}
    # id_dict = {'video': video_id, 'channel': channel_id, 'playlist': playlist_id}
    url = url_dict[kind]
    if 'None' in url: url = f'No {kind} found'
    if return_info and url != 'No video found': return url, fix_youtube_title(title), video_id
    return url
    # image = f'https://img.youtube.com/vi/{vid_id}/mqdefault.jpg'


def get_video_duration(video_id):
    f = {'part': 'contentDetails,snippet', 'id': video_id, 'key': GOOGLE_API}
    query_string = urlencode(f)
    r = requests.get(f'{YT_API_URL}videos?{query_string}')
    search_response = json.loads(r.text)
    item = search_response.get('items', [])[0]
    if item['snippet']['liveBroadcastContent'] == 'live': duration = 2088000
    else:  duration = int(isodate.parse_duration(item['contentDetails']['duration']).total_seconds())
    return duration


def get_video_durations(video_ids):
    video_ids = ','.join(video_ids)
    url = f'{YT_API_URL}videos?part=contentDetails&id={video_ids}&key={GOOGLE_API}'
    search_response = json.loads(requests.get(url).text)
    return_dict = {}
    for item in search_response.get('items', []):
        return_dict[item['id']] = int(isodate.parse_duration(item['contentDetails']['duration']).total_seconds())
    return return_dict


def detect_silence(input_file):
    # https://stackoverflow.com/a/42509904/7732434
    ffmpeg_location = r'ffmpeg\bin\ffmpeg'
    args_1 = f'{ffmpeg_location} -i {input_file} -af silencedetect=d=0.2 -f null - 2>&1 -loglevel quiet'
    yes_or_no = os.system(args_1)
    # yes_or_no = yes_or_no.split('\n')
    return yes_or_no


def remove_silence(input_file, output_file):
    if input_file == output_file:
        return False
    ffmpeg_location = r'ffmpeg\bin\ffmpeg'
    args = f'-i "{input_file}" -af silenceremove=start_periods=1:stop_periods=1:detection=peak "{output_file}"'
    os.system(f'{ffmpeg_location} -loglevel quiet ' + args)
    os.remove(input_file)


# noinspection SpellCheckingInspection
def youtube_download(url_or_video_id, verbose=False, use_external_downloader=False):
    # https://github.com/ytdl-org/youtube-dl/blob/3e4cedf9e8cd3157df2457df7274d0c842421945/youtube_dl/YoutubeDL.py#L137-L312
    ydl_opts = {
        'external_downloader': 'aria2c.exe' if use_external_downloader else None,
        'external_downloader_args': ['-c', '-j', '3', '-x', '3', '-s', '3', '-k', '1M'],
        # https://aria2.github.io/manual/en/html/aria2c.html#options
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'postprocessor_args': ['-threads', '1'],
        # 'outtmpl': 'music/%(title)s - %(id)s.%(ext)s',
        'outtmpl': 'music/%(id)s.%(ext)s',
        'ffmpeg_location': FFMPEG,
        'verbose': verbose,  # for some reason it has to be True to work  # 4/18/2020
        'cachedir': False,
        # 'nooverwrites': True,
        'quiet': not verbose,
        'audio-quality': 0
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url_or_video_id])
        # info_dict = ydl.extract_info(url_or_video_id, download=False)
        # video_id = info_dict['display_id']
        # input_file = f'music/{video_id}.mp3'
        # output_file = f'music/{video_id}.mp3'
        # remove_silence(input_file, output_file)
        # return info_dict
        return 'downloaded'


def extract_video_id(url):
    query = urlparse(url)
    if query.hostname == 'youtu.be': return query.path[1:]
    if query.hostname in ('www.youtube.com', 'youtube.com'):
        if query.path == '/watch': return parse_qs(query.query)['v'][0]
        if query.path[:7] == '/embed/': return query.path.split('/')[2]
        if query.path[:3] == '/v/': return query.path.split('/')[2]
    # fail?
    return None


def get_songs_from_youtube_playlist(url, to_play=False):
    playlist_id = parse_qs(urlsplit(url).query)['list'][0]
    songs, playlist_name = get_videos_from_playlist(playlist_id, return_title=True, to_play=to_play)
    return songs, playlist_name


def get_songs_from_playlist(playlist_name, guild_id, author_id, to_play=False):
    songs = []
    if playlist_name.startswith('https://www.youtube.com/playlist'):
        playlist_id = parse_qs(urlsplit(playlist_name).query)['list'][0]
        return get_videos_from_playlist(playlist_id, return_title=True, to_play=to_play)
        # return get_songs_from_youtube_playlist(playlist_name, to_play=to_play)
    playlist = None
    try: scope = int(re.compile('--[2-3]').search(playlist_name).group()[2:])
    except AttributeError: scope = 1
    if scope == 1: playlist = playlists_coll.find_one({'guild_id': guild_id, 'playlist_name': playlist_name, 'creator_id': author_id})
    if scope == 2 or not playlist: playlist = playlists_coll.find_one({'guild_id': guild_id, 'playlist_name': playlist_name})
    if scope == 3 or not playlist: playlist = playlists_coll.find_one({'playlist_name': playlist_name})
    if playlist: songs = [Song(*item) for item in playlist['songs']]
    return songs, playlist_name


def get_videos_from_playlist(playlist_id, return_title=False, to_play=False):
    f = {'part': 'snippet',  'playlistId': playlist_id, 'key': GOOGLE_API, 'maxResults': 50}
    response = json.loads(requests.get(f'{YT_API_URL}playlistItems?{urlencode(f)}').text)
    if to_play:
        songs_dict = {item['snippet']['resourceId']['videoId']: item['snippet']['title'] for item in response['items']}
        video_ids = list(songs_dict.keys())
        durations = get_video_durations(video_ids).items()
        songs = [Song(songs_dict[video_id], video_id) for video_id, duration in durations if duration <= 1800]
    else:
        songs = [Song(item['snippet']['title'], item['snippet']['resourceId']['videoId']) for item in response['items']]

    if return_title:
        f = {'part': 'snippet',  'id': playlist_id, 'key': GOOGLE_API}
        response = json.loads(requests.get(f'{YT_API_URL}playlists?{urlencode(f)}').text)
        return songs, response['items'][0]['snippet']['title']
    return songs


def get_all_playlists():
    playlists = playlists_coll.find({'type': 'playlist'}, {'_id': 0, 'playlist_name': 1, 'creator_id': 1})
    return playlists


def get_video_titles(video_ids):
    video_ids = ','.join(video_ids)
    url = f'{YT_API_URL}videos?part=contentDetails&id={video_ids}&key={GOOGLE_API}'
    search_response = json.loads(requests.get(url).text)['items']
    return [item['title'] for item in search_response]


def get_video_title(video_id):
    f = {'part': 'snippet',  'id': video_id, 'key': GOOGLE_API}
    response = json.loads(requests.get(f'{YT_API_URL}videos?{urlencode(f)}').text)
    title = response['items'][0]['snippet']['title']
    return fix_youtube_title(title)


def get_related_video(video_id, done_queue):
    dq = done_queue[:20]  # songs have a possibility of repeating after 20 songs
    results = min(5 + len(dq), 50)
    f = {'part': 'id,snippet',  'maxResults': results, 'order': 'relevance', 'relatedToVideoId': video_id,
         'type': 'video', 'key': GOOGLE_API}
    search_response = json.loads(requests.get(f'{YT_API_URL}search?{urlencode(f)}').text)
    # TODO: use get_video_durations(video_ids)
    video_ids = [item['id']['videoId'] for item in search_response['items']]
    video_durations = get_video_durations(video_ids)
    for item in search_response['items']:
        title = item['snippet']['title']
        video_id = item['id']['videoId']
        related_song = Song(title, video_id)
        if related_song not in dq and video_durations[video_id] <= 1800:  # 30 minutes
            related_url = f'https://www.youtube.com/watch?v={video_id}'
            return related_url, fix_youtube_title(title), video_id
    raise Exception('No related videos found :(')


async def check_net_worth(author: str):  # use a database
    return f'You have ${os.environ[author]}\nNot as rich as me'


def update_net_worth(author: str):
    try:
        os.environ[author] = str(int(os.environ[author]) + 1)
    except KeyError:
        os.environ[author] = '1'


OPUS_LIBS = ['libopus-0.x86.dll', 'libopus-0.x64.dll', 'libopus-0.dll', 'libopus.so.0', 'libopus.0.dylib']


# noinspection PyDefaultArgument
def load_opus_lib(opus_libs=OPUS_LIBS):
    if opus.is_loaded(): return True
    for opus_lib in opus_libs:
        with suppress(OSError):
            opus.load_opus(opus_lib)
            return
        raise RuntimeError(f"Could not load an opus lib ({opus_lib}). Tried {', '.join(opus_libs)}")


def send_email(recipient, name='', subject=''):  # NOTE: for later
    password = os.environ['PASSWORD']
    my_address = os.environ['EMAIL']
    s = smtplib.SMTP('smtp.gmail.com', 587)
    s.starttls()
    s.login(my_address, password)
    msg = MIMEMultipart()
    message = f'Hey {name}, this is just a test'
    msg['From'] = my_address
    msg['To'] = recipient
    msg['Subject'] = f'{subject}'
    msg.attach(MIMEText(message, 'plain'))
    s.send_message(msg)
    s.quit()


def search_for(directory, contains):
    contains_list = []
    for file in glob.glob(f'{directory}/*'):
        if contains in file:
            contains_list.append(file)
    return contains_list


def format_time_ffmpeg(s):
    total_msec = s * 1000
    total_seconds = s
    total_minutes = s / 60
    total_hours = s / 3600
    msec = int(total_msec % 1000)
    sec = int(total_seconds % 60 - (msec / 3600000))
    mins = int(total_minutes % 60 - (sec / 3600) - (msec / 3600000))
    hours = int(total_hours - (mins / 60) - (sec / 3600) - (msec / 3600000))
    return "{:02d}:{:02d}:{:02d}".format(hours, mins, sec)


# TODO: TURN GET TWEET INTO ONE FUNCTION

def twitter_get_screen_name(username):
    """
    :raises tweepy.TweepError
    :param username: username or something
    :return:
    """
    return TWITTER_API.get_user(username).screen_name


def twitter_get_tweets(screen_name, quantity=1):
    """
    :raises tweepy.TweepError
    :param screen_name: the screen name of the user
    :param quantity: the number of latest tweets to return
    :return: a list of links of the users' latest tweets
    """
    statuses = TWITTER_API.user_timeline(screen_name, count=quantity)
    screen_name = TWITTER_API.get_user(screen_name).screen_name
    tweets = [f'https://twitter.com/{screen_name}/status/{status.id_str}' for status in statuses]
    return tweets


def twitter_search_user(query, users_to_search=5):
    """
    :param query: query to search for
    :param users_to_search: return result length
    :return: list_of(Display Name, Screen Name)
    """
    query = TWITTER_API.search_users(query, perpage=users_to_search)
    users = []
    for i in range(users_to_search):
        try:
            user = query[i]
            users.append((user.name, user.screen_name))
        except IndexError:
            break
    return users


if __name__ == "__main__":
    # tests go here
    assert twitter_search_user('Lady Gaga')
    assert twitter_get_tweets(twitter_search_user('Elon Musk')[0][1])
    assert twitter_get_tweets('discord')
    assert extract_video_id('https://www.youtube.com/watch?v=JnIO6AQRS2k') == 'JnIO6AQRS2k'
    assert extract_video_id('https://www.youtube.com/watch?v=oEAjv2vgUGc') == 'oEAjv2vgUGc'
    assert extract_video_id('http://youtu.be/SA2iWivDJiE') == 'SA2iWivDJiE'
    assert extract_video_id('http://www.youtube.com/watch?v=_oPAwA_Udwc&feature=feedu') == '_oPAwA_Udwc'
    assert extract_video_id('http://www.youtube.com/embed/SA2iWivDJiE') == 'SA2iWivDJiE'
    assert extract_video_id('http://www.youtube.com/v/SA2iWivDJiE?version=3&amp;hl=en_US') == 'SA2iWivDJiE'
    assert get_video_title('oEAjv2vgUGc') == 'Poseidon'
    assert extract_video_id('https:/test.ca') is None
    assert extract_video_id('This is a test') is None
    assert extract_video_id('youtube') is None
    assert get_video_duration('JnIO6AQRS2k') == 3682
    assert get_videos_from_playlist('PLY4YLSp44QYvmvSNX3Q_0y-mOQ02ZWIbu')
    start_time = time.time()
    youtube_download('https://www.youtube.com/watch?v=oEAjv2vgUGc', verbose=True)
    print('Download time:', time.time() - start_time)
    print('ALL TESTS PASSED')
