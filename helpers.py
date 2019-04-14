from __future__ import unicode_literals

import glob
import smtplib
from collections import OrderedDict
from contextlib import suppress
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
# noinspection PyUnresolvedReferences
from pprint import pprint
# noinspection PyUnresolvedReferences
from time import time

import requests
from discord import opus
# import tweepy
import re
import os
import json
from urllib.parse import urlparse, parse_qs, urlencode
import youtube_dl
from mutagen.mp3 import MP3


class Song:
    _time_stamp = 0
    start_time = None
    status = 'NOT_PLAYING'
    length = None

    def __init__(self, title, video_id):
        self.title = title
        self._video_id = video_id

    def __hash__(self):
        return hash(self._video_id)

    def __repr__(self):
        return 'Song(' + str({'title': self.title, 'video_id': self._video_id,
                              'length': self.get_length(), 'status': self.status,
                              'time_stamp': self.get_time_stamp(), 'start_time': self.start_time}) + ')'

    def __str__(self):
        return 'Song(' + str({'title': self.title, 'video_id': self._video_id}) + ')'

    def __eq__(self, other):
        return self.__class__ == other.__class__ and other.video_id == self._video_id

    def start(self, start_at=_time_stamp):
        self.status = 'PLAYING'
        self.start_time = time() - start_at

    def play(self):
        self.start()

    def pause(self):
        self.status = 'PAUSED'
        self._time_stamp = time() - self.start_time

    def stop(self):
        self.status = 'NOT_PLAYING'
        self._time_stamp = 0

    def get_time_stamp(self, string=False):
        if self.status == 'PLAYING':
            self._time_stamp = time() - self.start_time
        if string:
            temp = round(self._time_stamp)
            minutes = temp // 60
            seconds = temp % 60
            if minutes < 10: minutes = f'0{minutes}'
            if seconds < 10: seconds = f'0{seconds}'
            return f'[{minutes}:{seconds} - {self.get_length(True)}]'
        return self._time_stamp

    def set_time_stamp(self, seconds):
        self._time_stamp = seconds

    def fwd(self, seconds):
        self.start_time -= seconds

    def rwd(self, seconds):
        self.start_time += seconds

    def get_status(self):
        return self.status

    def get_length(self, string=False):
        if self.length is None:
            audio = MP3(f'Music/{self._video_id}.mp3')
            self.length = audio.info.length
        if string:
            temp = round(self.length)
            minutes = temp // 60
            seconds = temp % 60
            if minutes < 10: minutes = f'0{minutes}'
            if seconds < 10: seconds = f'0{seconds}'
            return f'{minutes}:{seconds}'
        return self.length

    def get_video_id(self):
        return self._video_id


try: google_api_key = os.environ['google']
except KeyError:
    from environs import Env

    env = Env()
    env.read_env()
    google_api_key = os.environ['google']


youtube_api_url = 'https://www.googleapis.com/youtube/v3/'

if not os.path.exists('Music'):
    os.mkdir('Music')


def iso_8061_to_seconds(duration="P1W2DT6H21M32S"):
    """
    Converts YouTube duration (ISO 8061)
    into Seconds

    see http://en.wikipedia.org/wiki/ISO_8601#Durations
    """
    iso_8601 = re.compile(
        'P'  # designates a period
        '(?:(?P<years>\d+)Y)?'  # years
        '(?:(?P<months>\d+)M)?'  # months
        '(?:(?P<weeks>\d+)W)?'  # weeks
        '(?:(?P<days>\d+)D)?'  # days
        '(?:T'  # time part must begin with a T
        '(?:(?P<hours>\d+)H)?'  # hours
        '(?:(?P<minutes>\d+)M)?'  # minutes
        '(?:(?P<seconds>\d+)S)?'  # seconds
        ')?')  # end of time part
    # Convert regex matches into a short list of time units
    units = list(iso_8601.match(duration).groups()[-3:])
    # Put list in ascending order & remove 'None' types
    units = list(reversed([int(x) if x is not None else 0 for x in units]))
    # Do the maths
    return sum([x * 60 ** units.index(x) for x in units])

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
        # print(search_result['id']['kind'])
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
    is_live = item['snippet']['liveBroadcastContent'] == 'live'
    return 2088000 if is_live else iso_8061_to_seconds(item['contentDetails']['duration'])


def get_video_durations(video_ids):
    video_ids = ','.join(video_ids)
    url = f'{youtube_api_url}videos?part=contentDetails&id={video_ids}&key={google_api_key}'
    search_response = json.loads(requests.get(url).text)
    return_dict = {}
    for item in search_response.get('items', []):
        return_dict[item['id']] = iso_8061_to_seconds(item['contentDetails']['duration'])
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
        # TODO: detect then remove silence
        # TODO: save files as video_id.mp3 cus fiend titles are a mess to deal with
        # info_dict = ydl.extract_info(url_or_video_id, download=False)
        # pprint(info_dict)
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
    for item in search_response['items']:
        title = item['snippet']['title']
        video_id = item['id']['videoId']
        related_song = Song(title, video_id)
        if related_song not in dq and get_video_duration(video_id) <= 600:
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


def send_email(recipient, name='', subject=''):  # TODO: for later
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
    # tests go below here
    # url, title, video_id = youtube_search('Magnolia', return_info=True)
    # url = youtube_search('Magnolia')
    # a = get_related_video(video_id, [])
    # youtube_download(url, verbose=True)
    pass
