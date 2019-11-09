from __future__ import unicode_literals
import glob
import isodate
import smtplib
from collections import OrderedDict
from contextlib import suppress
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
# noinspection PyUnresolvedReferences
from pprint import pprint
from time import time

import requests
from discord import opus
from pymongo import MongoClient
# import tweepy
import re
import os
import json
from urllib.parse import urlparse, parse_qs, urlencode
from mutagen.mp3 import MP3
from mutagen import MutagenError
import subprocess
if __name__ != '__main__':
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    subprocess.Popen('pip install --user --upgrade youtube-dl', startupinfo=startupinfo).wait()
import youtube_dl

db_client = MongoClient('localhost', 27017)
db = db_client.discord_bot
posts = db.posts


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
        self.start_time = time() - start_at

    def play(self):
        self.start()

    def pause(self):
        self.status = 'PAUSED'
        self._time_stamp = time() - self.start_time

    def stop(self):
        self.status = 'NOT PLAYING'
        self._time_stamp = 0

    def get_length(self, string=False):
        if self.length == 'DOWNLOADING':
            try:
                audio = MP3(f'Music/{self._video_id}.mp3')
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
            self._time_stamp = time() - self.start_time
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


try: google_api_key = os.environ['google']
except KeyError:
    from environs import Env

    env = Env()
    env.read_env()
    google_api_key = os.environ['google']


youtube_api_url = 'https://www.googleapis.com/youtube/v3/'


# twitter_auth = tweepy.OAuthHandler(os.environ['twitter_consumer_key'], os.environ['twitter_consumer_secret'])
# twitter_auth.set_access_token(os.environ['twitter_access_token'], os.environ['twitter_access_token_secret'])
# twitter_api = tweepy.API(twitter_auth)


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
         'q': text, 'type': kind, 'key': google_api_key}
    query_string = urlencode(f)
    r = requests.get(f'{youtube_api_url}search?{query_string}')
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
    f = {'part': 'contentDetails,snippet', 'id': video_id, 'key': google_api_key}
    query_string = urlencode(f)
    r = requests.get(f'{youtube_api_url}videos?{query_string}')
    search_response = json.loads(r.text)
    item = search_response.get('items', [])[0]
    if item['snippet']['liveBroadcastContent'] == 'live': duration = 2088000
    else:  duration = int(isodate.parse_duration(item['contentDetails']['duration']).total_seconds())
    return duration


def get_video_durations(video_ids):
    video_ids = ','.join(video_ids)
    url = f'{youtube_api_url}videos?part=contentDetails&id={video_ids}&key={google_api_key}'
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


def youtube_download(url_or_video_id, verbose=False):
    ydl_opts = {
        # 'external_downloader': 'aria2c',
        # 'external_downloader_args': ['-c', '-j3', '-x3','-s3', '-k1M'],
        # https://aria2.github.io/manual/en/html/aria2c.html#options
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'postprocessor_args': ['-threads', '1'],
        # 'outtmpl': 'Music/%(title)s - %(id)s.%(ext)s',
        'outtmpl': 'Music/%(id)s.%(ext)s',
        'ffmpeg_location': 'ffmpeg\\bin',
        'verbose': verbose,
        'quiet': not verbose,
        'audio-quality': 0
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url_or_video_id])
        # info_dict = ydl.extract_info(url_or_video_id, download=False)
        # video_id = info_dict['display_id']
        # input_file = f'Music/{video_id}.mp3'
        # output_file = f'Music/{video_id}.mp3'
        # remove_silence(input_file, output_file)
        # return info_dict
        return 'downloaded'


def get_video_id(url):
    # This was taken from StackOverflow
    # Examples:
    # - http://youtu.be/SA2iWivDJiE
    # - http://www.youtube.com/watch?v=_oPAwA_Udwc&feature=feedu
    # - http://www.youtube.com/embed/SA2iWivDJiE
    # - http://www.youtube.com/v/SA2iWivDJiE?version=3&amp;hl=en_US
    query = urlparse(url)
    if query.hostname == 'youtu.be': return query.path[1:]
    if query.hostname in ('www.youtube.com', 'youtube.com'):
        if query.path == '/watch': return parse_qs(query.query)['v'][0]
        if query.path[:7] == '/embed/': return query.path.split('/')[2]
        if query.path[:3] == '/v/': return query.path.split('/')[2]
    # fail?
    return None


def get_songs_from_youtube_playlist(url):
    playlist_id = parse_qs(url)['list']
    songs, playlist_name = get_videos_from_playlist(playlist_id, return_title=True, to_play=to_play)
    return songs, playlist_name


def get_songs_from_playlist(playlist_name, guild_id, author_id, to_play=False):
    songs = []
    if playlist_name.startswith('https://www.youtube.com/playlist'):
        return get_songs_from_youtube_playlist(playlist_name)
    playlist = None
    try: scope = int(re.compile('--[2-3]').search(playlist_name).group()[2:])
    except AttributeError: scope = 1
    if scope == 1: playlist = posts.find_one({'guild_id': guild_id, 'playlist_name': playlist_name, 'creator_id': author_id})
    if scope == 2 or not playlist: playlist = posts.find_one({'guild_id': guild_id, 'playlist_name': playlist_name})
    if scope == 3 or not playlist: playlist = posts.find_one({'playlist_name': playlist_name})
    if playlist: songs = [Song(*item) for item in playlist['songs']]
    return songs, playlist_name


def get_videos_from_playlist(playlist_id, return_title=False, to_play=False):
    f = {'part': 'snippet',  'playlistId': playlist_id, 'key': google_api_key, 'maxResults': 50}
    response = json.loads(requests.get(f'{youtube_api_url}playlistItems?{urlencode(f)}').text)
    if to_play:
        songs_dict = {item['snippet']['resourceId']['videoId']: item['snippet']['title'] for item in response['items']}
        video_ids = list(songs_dict.keys())
        durations = get_video_durations(video_ids).items()
        songs = [Song(songs_dict[video_id], video_id) for video_id, duration in durations if duration <= 1800]
    else:
        songs = [Song(item['snippet']['title'], item['snippet']['resourceId']['videoId']) for item in response['items']]
        
    if return_title:
        f = {'part': 'snippet',  'id': playlist_id, 'key': google_api_key}
        response = json.loads(requests.get(f'{youtube_api_url}playlists?{urlencode(f)}').text)
        return songs, response['items'][0]['snippet']['title']
    return songs
    

def get_video_titles(video_ids):
    video_ids = ','.join(video_ids)
    url = f'{youtube_api_url}videos?part=contentDetails&id={video_ids}&key={google_api_key}'
    search_response = json.loads(requests.get(url).text)['items']
    return [item['title'] for item in search_response]


def get_youtube_title(video_id):
    f = {'part': 'snippet',  'id': video_id, 'key': google_api_key}
    response = json.loads(requests.get(f'{youtube_api_url}videos?{urlencode(f)}').text)
    title = response['items'][0]['snippet']['title']
    return fix_youtube_title(title)


def get_related_video(video_id, done_queue):
    dq = done_queue[:20]  # songs have a possibility of repeating after 20 songs
    results = min(5 + len(dq), 50)
    f = {'part': 'id,snippet',  'maxResults': results, 'order': 'relevance', 'relatedToVideoId': video_id,
         'type': 'video', 'key': google_api_key}
    search_response = json.loads(requests.get(f'{youtube_api_url}search?{urlencode(f)}').text)
    # TODO: use get_video_durations(video_ids)
    for item in search_response['items']:
        title = item['snippet']['title']
        video_id = item['id']['videoId']
        related_song = Song(title, video_id)
        if related_song not in dq and get_video_duration(video_id) <= 1800:
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
    if opus.is_loaded():
        return True

    for opus_lib in opus_libs:
        try:
            opus.load_opus(opus_lib)
            return
        except OSError:
            pass

        raise RuntimeError('Could not load an opus lib. Tried %s' % (', '.join(opus_libs)))


# TODO: TURN GET TWEET INTO ONE FUNCTION

# def discord_search_twitter_user(text, redirect=False):
#     msg = '\n[Name | Screen name]```'
#     users = search_twitter_user(text)
#     for name, screenName in users:
#         msg += f'\n{name} | @{screenName}'
#     if redirect:
#         return "```Were you searching for a User?\nHere are some names:" + msg
#     return '```' + msg
#
#
# def get_tweet_from(user, quantity=1):
#     try:
#         statuses = twitter_api.user_timeline(user, count=quantity)
#         screen_name = twitter_api.get_user(user).screen_name
#         # f'https://twitter.com/{user}/status/{tweet.id_str}'
#         tweets = [f'https://twitter.com/{screen_name}/status/{status.id_str}' for status in statuses]
#         return tweets, screen_name
#     except tweepy.TweepError:
#         return ['NA'], 'TWITTER USER DOES NOT EXIST'
#
#
# def search_twitter_user(q, users_to_search=5):
#     q = twitter_api.search_users(q, perpage=users_to_search)
#     users = []
#     for i in range(users_to_search):
#         try:
#             user = q[i]
#             users.append((user.name, user.screen_name))
#         except IndexError:
#             break
#     return users
#
#
# def discord_get_tweet_from(text):
#     try:
#         p = text.index(' -')  # p: parameter
#         twitter_user = text[0:p]
#         num = int(text[p + 2:])
#         num = max(min(num, 3), 1)
#     except (ValueError, IndexError):
#         num = 1
#         twitter_user = text[0:]
#     if twitter_user.count(' ') > 0: return discord_search_twitter_user(twitter_user, redirect=True)
#     if not search_twitter_user(twitter_user): return 'NO USER FOUND, YOU MUST BE DYSGRAPHIC'
#     links, twitter_user = get_tweet_from(twitter_user, quantity=num)
#     msg = 'Here is/are the latest tweet(s)'
#     for index, link in enumerate(links):
#         if index > 0:
#             msg += '\n<' + link + '>'
#         else:
#             msg += '\n' + link
#     return msg


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


if __name__ == "__main__":
    # tests go here
    assert get_video_id('https://www.youtube.com/watch?v=JnIO6AQRS2k') == 'JnIO6AQRS2k'
    assert get_video_id('https:/test.ca') == None
    assert get_video_id('This is a test') == None
    assert get_video_id('youtube') == None
    assert get_video_duration('JnIO6AQRS2k') == 3682
    print('ALL TESTS PASSED')
