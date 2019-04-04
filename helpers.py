from __future__ import unicode_literals

import glob
import smtplib
import socket
import ssl
import sys
from collections import namedtuple, OrderedDict
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
from pprint import pprint

import requests
from discord import opus
# import tweepy
import re
import os
import json
# noinspection PyPackageRequirements
from googleapiclient.discovery import build
from urllib.parse import urlparse, parse_qs, urlencode
import youtube_dl

logger = logging.getLogger()
logger.setLevel(logging.ERROR)
Song = namedtuple('Song', ('title', 'video_id'))

try: google_api_key = os.environ['google']
except KeyError:
    from environs import Env

    env = Env()
    env.read_env()
    google_api_key = os.environ['google']


youtube_API = build('youtube', 'v3', developerKey=google_api_key, cache_discovery=False)

if not os.path.exists('Music'):
    os.mkdir('Music')


def yt_time(duration="P1W2DT6H21M32S"):
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
#
# twitter_api = tweepy.API(twitter_auth)


# def rich_embed(title, url, image, icon, desc, author='', colour=discord.Color.red()):
#     embed = discord.Embed(url=url, title=title, color=colour, description=desc)
#     embed.set_thumbnail(url=icon)
#     embed.set_image(url=image)
#     author_icon = 'https://cdn.discordapp.com/avatars/282274755426385921/fa592e14d10668e80e981b7e1066746a.webp?size=256'
#     if author != '': embed.set_author(name=author, url=url, icon_url=author_icon)
#     return embed

def fix_youtube_title(title):
    return title.replace('&quot;', '\'').replace('&amp;', '&').replace(
        '/', '_').replace('?', '').replace(':', ' -').replace('&#39;', "'").replace(' || ', '_')


def youtube_search(text, return_info=False, limit_duration=False, duration_limit=600):
    # if broken, compare this with https://repl.it/@elilopez/DiscordBot
    if text in ('maagnolia', 'magnolia') and return_info:
        text = 'magnolia (Audio)'
    # icon = 'https://cdn4.iconfinder.com/data/icons/social-media-icons-the-circle-set/48/youtube_circle-512.png'
    p = re.compile('--[1-4][0-9]|--[1-2]')
    try:
        re_result = p.search(text)
        results = int(re_result.group()[2:])
    except AttributeError: results = 1
    p = re.compile('--channel|--playlist')  # defaults to video so I removed --video
    try:
        re_result = p.search(text)
        kind = re_result.group()[2:]
    except AttributeError: kind = 'video'
    try: text = text[text.index(' '):text.index('--')]
    except ValueError: pass
    # pylint: disable=no-member
    try:
        search_response = youtube_API.search().list(part='id,snippet', maxResults=min(results + 5, 50),
                                                    order='relevance', q=text, type=kind,
                                                    ).execute()
    except (ssl.SSLError, AttributeError, socket.timeout, ConnectionAbortedError):
        print('error with youtube service, line 111')
        api_url = 'https://www.googleapis.com/youtube/v3/'
        f = {'part': 'id,snippet', 'maxResults': min(results + 5, 50), 'order': 'relevance',
             'q': text, 'type': kind, 'key': google_api_key}
        query_string = urlencode(f)
        r = requests.get(f'{api_url}search?{query_string}')
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
                # print(f'https://www.youtube.com/watch?v={video_id}')
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
    # pylint: disable=no-member
    search_response = youtube_API.videos().list(part='contentDetails,snippet', id=video_id).execute()
    item = search_response.get('items', [])[0]
    is_live = item['snippet']['liveBroadcastContent'] == 'live'
    return 2088000 if is_live else yt_time(item['contentDetails']['duration'])


def get_video_durations(video_ids):
    video_ids = ','.join(video_ids)
    # pylint: disable=no-member
    search_response = youtube_API.videos().list(part='contentDetails', id=video_ids).execute()
    # url = f'https://www.googleapis.com/youtube/v3/videos?part=contentDetails&id={video_ids}&key={google_api_key}'
    # r = requests.get(url)
    # search_response = json.loads(r.text)
    return_dict = {}
    for item in search_response.get('items', []):
        return_dict[item['id']] = yt_time(item['contentDetails']['duration'])
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


def youtube_download(url_or_video_id):
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        # 'outtmpl': 'Music/%(title)s - %(id)s.%(ext)s',
        'outtmpl': 'Music/%(id)s.%(ext)s',
        'external_downloader': 'aria2c',
        'external_downloader_args': '-c -j 3 -x 3 -s 3 -k 1M',
        # https://aria2.github.io/manual/en/html/aria2c.html#options
        'ffmpeg_location': 'ffmpeg\\bin',
        # 'verbose': True,
        'quiet': True,
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


def get_video_title(video_id):
    # pylint: disable=no-member
    response = youtube_API.videos().list(part='snippet', id=video_id).execute()
    title = response['items'][0]['snippet']['title']
    return title
    # return fix_youtube_title(title)  # NOTE: file friendly title


def get_related_video(video_id, done_queue):
    dq = done_queue[:10]  # NOTE: safe to repeat after 10 songs?
    results = min(5 + len(dq), 50)
    # pylint: disable=no-member
    try:
        search_response = youtube_API.search().list(part='id,snippet',  maxResults=results,
                                                    order='relevance', relatedToVideoId=video_id, type='video'
                                                    ).execute()
    except (ssl.SSLError, AttributeError, socket.timeout, ConnectionAbortedError):
        api_url = 'https://www.googleapis.com/youtube/v3/'
        f = {'part': 'id,snippet',  'maxResults': results, 'order': 'relevance', 'relatedToVideoId': video_id,
             'type': 'video', 'key': google_api_key}
        query_string = urlencode(f)
        r = requests.get(f'{api_url}search?{query_string}')
        search_response = json.loads(r.text)
        print('error with youtube service, line 262')
    related_song = dq[0] if dq else Song('', '')
    i = 0
    while related_song in dq or related_song == Song('', '') or get_video_duration(related_song.video_id) > 600:
        search_result = search_response['items'][i]
        title = search_result['snippet']['title']
        video_id = search_result['id']['videoId']
        related_song = Song(title, video_id)
        i += 1
    url = f'https://www.youtube.com/watch?v={video_id}'
    # noinspection PyUnboundLocalVariable
    return url, fix_youtube_title(title), video_id


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
    message = 'Hey, this is just a test'
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


if __name__ == "__main__":
    # print(get_related_video('PczuoZJ-PtM'))
    # vid_id = 'QnccxyatrD0'
    vid_id = get_video_id(youtube_search('Adam K & Soha Twilight'))
    youtube_download(vid_id)
    # a, b, c = youtube_search('The grand sound livestream', return_info=True, limit_duration=True)
    # print(youtube_search('slow'))
    # youtube_download(youtube_search('Slow'))
    # print(get_video_title(vid_id))
