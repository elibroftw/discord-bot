from __future__ import unicode_literals
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
from discord import opus
# import tweepy
import re
import os
from googleapiclient import discovery
from urllib.parse import urlparse
import youtube_dl

logger = logging.getLogger()
logger.setLevel(logging.ERROR)

try:
    google_api_key = os.environ['google']
except KeyError:
    from environs import Env

    env = Env()
    env.read_env()
    google_api_key = os.environ['google']
youtube = discovery.build('youtube', 'v3', developerKey=google_api_key, cache_discovery=False)


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


def youtube_search(text):
    # icon = 'https://cdn4.iconfinder.com/data/icons/social-media-icons-the-circle-set/48/youtube_circle-512.png'
    p = re.compile('--[1-4][0-9]|--[1-2]')
    try:
        re_result = p.search(text)
        result = int(re_result.group()[2:])
    except AttributeError:
        result = 1
    p = re.compile('--channel|--playlist')  # defaults to video so I removed --video
    try:
        re_result = p.search(text)
        kind = re_result.group()[2:]
    except AttributeError:
        kind = 'video'
    try:
        text = text[text.index(' '):text.index('--')]
    except ValueError:
        pass
    # region = 'Canada'
    if kind == 'channel':
        search_response = youtube.search().list(q=text, part="id,snippet", maxResults=result + 20,
                                                order='relevance').execute()
    search_response = youtube.search().list(q=text, part="id,snippet", maxResults=result + 2,
                                            order='relevance').execute()
    videos, channels, playlists = [], [], []
    # Add each result to the appropriate list, and then display the lists of
    # matching videos, channels, and playlists.
    # TODO: CHANNEL SEARCH DOES NOT WORK
    for search_result in search_response.get('items', []):
        # print(search_result['id']['kind'])
        if search_result['id']['kind'] == 'youtube#video':
            title = search_result['snippet']['title']
            video_id = search_result['id']['videoId']
            desc = search_result['snippet']['description'][:160]
            videos.append([title, video_id, desc])
            # videos.append([title, id, desc])
        elif search_result['id']['kind'] == 'youtube#channel':
            channels.append([f'{search_result["snippet"]["title"]}', f'{search_result["id"]["channelId"]}'])
        elif search_result['id']['kind'] == 'youtube#playlist':
            playlists.append([f'{search_result["snippet"]["title"]}', f'{search_result["id"]["playlistId"]}'])
    title, video_id, desc = None, None, None
    channel_id = None
    playlist_id = None
    if kind == 'video':
        while result > 0:
            try:
                title, video_id, desc = videos[result - 1]
                break
            except IndexError:
                result -= 1
    elif kind == 'channel':
        while result > 0:
            try:
                channel_id = channels[result - 1][1]
                break
            except IndexError:
                result -= 1
    else:
        while result > 0:
            try:
                playlist_id = playlists[result - 1][1]
                print(playlist_id)
                break
            except IndexError:
                result -= 1
    if kind == 'video' and title is None:
        url = f'No {kind} found'
    elif kind == 'video':
        url = f'https://www.youtube.com/watch?v={video_id}'
    elif kind == 'channel' and channel_id is None:
        url = f'No {kind} found'
    elif kind == 'channel':
        url = f'https://www.youtube.com/channel/{channel_id}'
    elif kind == 'playlist' and playlist_id is None:
        url = f'No {kind} found'
    else:
        url = f'https://www.youtube.com/playlist?list={playlist_id}'
    return url
    # image = f'https://img.youtube.com/vi/{video_id}/mqdefault.jpg'
    # desc = '`Click title to go to video`\n' + desc
    # embed = richembed(title, url, image, icon, desc)
    # return True, embed


ydl_opts = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
}


def youtube_download(url):
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


def check_networth(author: str):  # use a database
    return f'You have ${os.environ[author]}\nNot as rich as me'


def update_net_worth(author: str):
    try:
        os.environ[author] = str(int(os.environ[author]) + 1)
    except KeyError:
        os.environ[author] = '1'


OPUS_LIBS = ['libopus-0.x86.dll', 'libopus-0.x64.dll', 'libopus-0.dll', 'libopus.so.0', 'libopus.0.dylib']


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


def send_email(recipient, name=''):  # TODO: for later
    password = os.environ['PASSWORD']
    my_address = os.environ['EMAIL']
    s = smtplib.SMTP('smtp.gmail.com', 587)
    s.starttls()
    s.login(my_address, password)
    msg = MIMEMultipart()
    message = 'Hey, this is just a test'
    msg['From'] = my_address
    msg['To'] = recipient
    msg['Subject'] = 'EMAIL TEST FROM DISCORD BOT'  # TODO: change this
    msg.attach(MIMEText(message, 'plain'))
    s.send_message(msg)
    s.quit()


def video_id(url):
    """
    Examples:
    - http://youtu.be/SA2iWivDJiE
    - http://www.youtube.com/watch?v=_oPAwA_Udwc&feature=feedu
    - http://www.youtube.com/embed/SA2iWivDJiE
    - http://www.youtube.com/v/SA2iWivDJiE?version=3&amp;hl=en_US
    """
    o = urlparse(url)
    if o.netloc == 'youtu.be':
        return o.path[1:]
    elif o.netloc in ('www.youtube.com', 'youtube.com'):
        if o.path == '/watch':
            id_index = o.query.index('v=')
            return o.query[id_index + 2:id_index + 13]
        elif o.path[:7] == '/embed/':
            return o.path.split('/')[2]
        elif o.path[:3] == '/v/':
            return o.path.split('/')[2]
    return None  # fail?
