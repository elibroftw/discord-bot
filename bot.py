import asyncio
from copy import deepcopy
from ctypes.wintypes import tagRECT
from datetime import datetime
import discord
from discord import FFmpegPCMAudio, PCMVolumeTransformer
from discord.ext import commands
from discord.ext.commands import has_permissions, Context, CommandNotFound, CheckFailure
import logging
from math import ceil
from random import shuffle, randint
import sys
import argparse

import tictactoe
from helpers import *
from investing import get_target_price, get_ticker_info, losers, winners, get_parsed_data, index_futures


# Check if script is already running
script = os.path.basename(__file__)
parser = argparse.ArgumentParser(description='Start the discord bot')
parser.add_argument('--prod', default=False, action='store_true')
parser.add_argument('--restarted', default=False, action='store_true')
parsed_args = parser.parse_args()
# in case restarted
if parsed_args.restarted:
    print('--restarted was passed')
    time.sleep(5)

try:
    os.remove('discord.log')
except OSError:
    print(f'Bot is already running!')
    sys.exit()
except FileNotFoundError: pass


logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)
bot = commands.Bot(command_prefix='!')
bot.remove_command('help')
bot.command()
load_opus_lib()

INVITATION_CODE = os.environ['invite_code']
MY_GUILD_ID = int(os.environ['guild_id'])
MY_USER_ID = int(os.environ['user_id'])
DEFAULT_ROLE = os.environ['default_role']
BLUE = discord.Color.blue()
TWITTER_BLUE = discord.Color(5631660)
STOCKS_GREEN = discord.Color.from_rgb(26, 197, 103)
STOCKS_RED = discord.Color.from_rgb(255, 51, 58)
STOCKS_YELLOW = discord.Color.from_rgb(255, 220, 72)
MOVERS_ETAS = {'DOW': '10 seconds', 'S&P500': '30 seconds', 'NASDAQ': '6 minutes',
               'NYSE': '6 minutes', 'NYSEARCA': '3 minutes', 'AMEX': '3 minutes',
               'US': '8 minutes', 'CA': '3 minutes', 'TSX': '3 minutes', 'ALL': '9 minutes'}
# LATEST_SORTED_INFO = {'market': [0.0, []]}
LATEST_SORTED_INFO = {}  # last update, sorted_info list
tic_tac_toe_data = {}
data_dict = {'downloads': {}}
with suppress(FileExistsError): os.mkdir('music')


# noinspection PyDeprecation
def run_coroutine(coroutine: asyncio.coroutine):
    # e.g. coroutine = bot.change_presence(activity=discord.Game('Prison Break (!)'))
    fut = asyncio.run_coroutine_threadsafe(coroutine, bot.loop)
    return fut.result()


def get_latest_sorted_info(of, market):
    global LATEST_SORTED_INFO
    if market not in LATEST_SORTED_INFO: LATEST_SORTED_INFO[market] = {of: [0.0, []]}
    elif of not in LATEST_SORTED_INFO[market]: LATEST_SORTED_INFO[market][of] = [0.0, []]
    if time.time() - LATEST_SORTED_INFO[market][of][0] > 120:  # update data every 2 minutes
        LATEST_SORTED_INFO[market][of][1] = get_parsed_data(of=of, market=market)
        LATEST_SORTED_INFO[market][of][0] = time.time()
    return LATEST_SORTED_INFO[market][of][1]


async def in_guild(ctx):
    return ctx.guild is not None


async def has_vc(ctx):
    if ctx.guild and ctx.guild.voice_client:
        return True
    return False


@bot.event
async def on_ready():
    print('Logged In')
    await bot.change_presence(activity=discord.Game('Prison Break (!)'))
    _save_dict = {'data_dict': {}}
    with suppress(FileNotFoundError, json.decoder.JSONDecodeError):
        if os.path.exists('save.json'):
            with open('save.json') as f:
                _save_dict = json.load(f)
        os.remove('save.json')
    for guild_id, v in _save_dict['data_dict'].items():
        if guild_id != 'downloads':
            mq = v['music'] = [Track(s['title'], s['video_id'], time_stamp=s['time_stamp']) for s in v['music']]
            v['done'] = [Track(s['title'], s['video_id'], time_stamp=s['time_stamp']) for s in v['done']]
            # noinspection PyTypeChecker
            data_dict[int(guild_id)] = v
            vc_id = v['voice_channel']
            if vc_id:
                voice_channel = bot.get_channel(vc_id)
                await voice_channel.connect()
                tc = bot.get_channel(v['text_channel'])
                if mq and tc is not None and not v['is_stopped']:
                    print('Resuming playback')
                    m = await tc.send('Bot has been restarted, now resuming music', delete_after=3)
                    ctx = await bot.get_context(m)
                    await play_file(ctx, v['music'][0].get_time_stamp())

    for guild in bot.guilds:
        if guild.id not in data_dict:
            data_dict[guild.id] = {'music': [], 'done': [], 'is_stopped': False, 'volume': 0.3,
                                   'repeat': False, 'repeat_all': False, 'auto_play': False, 'skip_voters': [],
                                   'invite': None, 'output': True, 'text_channel': None}


@bot.event
async def on_member_join(member):
    guild = member.guild
    msg = f'Welcome inmate {member.mention} to {guild}!\n'
    msg += 'Use !help for my functions'
    role = discord.utils.get(guild.roles, name=DEFAULT_ROLE)
    await member.add_roles(role)
    await member.send_message(member, msg)


@bot.event
async def on_message(message):
    author: discord.User = message.author
    if author != bot.user: update_net_worth(str(author))
    if message.content.startswith('!RUN'): await message.channel.send('I GOT EXTRADITED! :(')
    elif message.content.lower().startswith('!run'): await message.channel.send('N o t  h y p e  e n o u g h')
    else:
        with suppress(CommandNotFound): await bot.process_commands(message)


# noinspection PyUnusedLocal
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, (CommandNotFound, CheckFailure)): return
    if error == KeyboardInterrupt:
        await bot.logout()
        return
    raise error


@bot.command(name='help')
async def _help(ctx):
    await ctx.author.send('Check out my commands here: https://github.com/elibroftw/discord-bot/blob/master/README.md')


@bot.command(aliases=['source'])
async def about(ctx):
    ctx.author.send(f'Hi there. Thank you for inquiring about me. I was made by Elijah Lopez.\n'
                    'For more information visit https://github.com/elibroftw/discord-bot.\n'
                    f'Join my server at https://discord.gg/{INVITATION_CODE})')


def save_to_file():
    save_dict = {'save_time': str(datetime.now()), 'data_dict': {}}
    for guild in bot.guilds:
        voice_client = guild.voice_client
        guild_data = deepcopy(data_dict.get(guild.id, {}))
        if voice_client: guild_data['voice_channel'] = voice_client.channel.id
        else: guild_data['voice_channel'] = None
        mq = guild_data['music']
        guild_data['music'] = [s.to_dict() for s in mq]
        dq = guild_data['done']
        guild_data['done'] = [s.to_dict() for s in dq]
        # guild_data['next_up'] = [s.to_dict() for s in next_up_queue]
        save_dict['data_dict'][guild.id] = guild_data
    try:
        with open('save.json', 'w') as fp:
            json.dump(save_dict, fp, indent=4)
    except Exception as e:
        print('Error while writing to save.json', e)


@bot.command()
async def save(ctx):
    if ctx.author.id == MY_USER_ID:
        save_to_file()


@bot.command(name='exit', aliases=['quit'])
async def shutdown_bot(ctx, save_data=True):
    if ctx.author.id == MY_USER_ID:
        if save_data:
            await bot.change_presence(activity=discord.Game('Saving Data'))
            save_to_file()
        await bot.change_presence(activity=discord.Game('Leaving Voice Chats'))
        for voice_client in bot.voice_clients:
            if voice_client.is_playing() or voice_client.is_paused():
                no_after_play(data_dict[ctx.guild.id], voice_client)
            await voice_client.disconnect()
        await bot.change_presence(activity=discord.Game('Inactive'))
        print('Bot logged out')
        await bot.logout()


@bot.command()
async def restart(ctx, save_data=True):
    if ctx.author.id == MY_USER_ID:
        print('Restarting')
        if save_data:
            await bot.change_presence(activity=discord.Game('Saving Data'))
            save_to_file()
        await bot.change_presence(activity=discord.Game('Leaving Voice Chats'))
        for guild in bot.guilds:
            voice_client = guild.voice_client
            if voice_client:
                no_after_play(data_dict[guild.id], voice_client)
                await voice_client.disconnect()
        await bot.change_presence(activity=discord.Game('Restarting...'))
        # guild_data['next_up'] = [s.to_dict() for s in next_up_queue]
        if parsed_args.prod: subprocess.Popen('pythonw bot.py --prod --restarted')
        else: subprocess.Popen('python bot.py --restarted')
        await bot.logout()


@commands.has_permissions(manage_messages=True)
@bot.command()
async def clear(ctx, number: int = 1):
    await ctx.message.delete()
    with suppress(AttributeError):
        channel: discord.TextChannel = ctx.channel
        await bot.change_presence(activity=discord.Game('Clearing messages...'))
        if number > 100: number = 100
        messages = []
        async for m in channel.history(limit=number):
            date = m.created_at
            # delete if older than 14 else add onto msg list
            if (datetime.now() - date).days > 14: await m.delete()
            else: messages.append(m)
        await channel.delete_messages(messages)
        print(f'{ctx.message.author} cleared {number} messages')
    await bot.change_presence(activity=discord.Game('Prison Break (!)'))


@commands.check(in_guild)
@commands.has_permissions(ban_members=True)
@bot.command()
async def ban(ctx):
    author = ctx.author
    args = ctx.message.content.split()[1:]
    if args:
        name = ' '.join(args)
        user = discord.utils.get(ctx.guild.members, nick=name)
        if not user:
            user = discord.utils.get(ctx.guild.members, name=name)

        if user:
            def check_yn(waited_msg):
                correct_prereqs = waited_msg.channel == ctx.channel and author == waited_msg.author
                waited_msg = waited_msg.content.lower()
                bool_value = waited_msg in ('y', 'ye', 'yes', 'n', 'no', 'na', 'nah')
                return bool_value and correct_prereqs

            await ctx.guild.ban(user)
            await ctx.send(f'{user.mention} has been banished to the shadow realm.\nDo you want to undo the ban (Y/n)?')
            user_msg = await bot.wait_for('message', check=check_yn, timeout=60)
            if user_msg:
                await ctx.guild.unban(user)
                await ctx.send(f'{user.mention} has been unbanned')


@bot.command(name='eval')
async def _eval(ctx):
    if ctx.author.id == MY_USER_ID:
        await ctx.send(str(eval(ctx.message.content[6:])))
        print(f'{ctx.message.author} used eval')


@bot.command(aliases=['createrole'])
async def create_role(ctx):
    m = ctx.message
    if str(m.author.top_role) == 'Admin':
        role_name = m.content.split()
        if len(role_name) > 1:
            role_name = ' '.join(role_name[1:])
            guild: discord.guild = ctx.guild
            await guild.create_role(name=role_name)
            await ctx.send(f'Role {role_name} created')
            print(f'{m.author} created role {role_name}')


# @bot.command()
# async def delete_role(ctx):  # TODO
#     raise NotImplementedError


@bot.command(aliases=['addrole', 'giverole', 'give_role'])
@has_permissions(manage_roles=True)
async def add_role(ctx):
    message = ctx.message.content.split()[1:]
    if len(message) > 1:
        guild = ctx.guild

        member = message[-1]
        member = discord.utils.get(guild.members, name=member)
        if not member:
            member = discord.utils.get(guild.members, nick=member)

        role_name = ' '.join(message[:-1])
        role = discord.utils.get(guild.roles, name=role_name)

        if not member: await ctx.send('Member not found')
        elif not role: await ctx.send('That role could not be found')
        else:
            await member.add_roles(role)
            await ctx.send(f'{member} is now part of {role}')


# @bot.command()
# async def remove_role(ctx):  # TODO
#     raise NotImplementedError


# @bot.command()  # TODO:
# async def create_channel(ctx):
#     pass


@bot.command()
async def delete_channel(ctx):
    if str(ctx.message.author.top_role) == 'Admin':
        msg_content = ctx.message.content[16:]
        guild: discord.Guild = ctx.message.guild
        guild_channels = guild.channels
        if msg_content.count(', ') > 0:
            channels_to_delete = msg_content.split(', ')
            for channel_name in channels_to_delete:
                await discord.utils.get(guild_channels, name=channel_name).delete(reason='N/A')
            print(f'{ctx.message.author} deleted channels: {channels_to_delete}')
        else:
            await discord.utils.get(guild_channels, name=msg_content).delete(reason='N/A')
            print(f'{ctx.message.author} deleted channel {msg_content}')


@bot.command()
async def hi(ctx):
    await ctx.send(f'Hey there {ctx.message.author.name}!')


@bot.command()
async def sleep(ctx):
    if ctx.message.author.id == MY_USER_ID:
        try: secs = int(ctx.message.content[7:])
        except ValueError: secs = 5
        await asyncio.sleep(secs)
        await ctx.send('Done sleeping')


@bot.command(aliases=['bal'])
async def balance(ctx):
    await ctx.message.author.send(check_net_worth(str(ctx.message.author)))
    await ctx.message.delete()


@bot.command(aliases=['gettweet', 'get_tweet'])
async def twitter(ctx: Context):
    text = ctx.message.content[ctx.message.content.index(' ') + 1:]
    try:
        p = text.index(' --')  # p: parameter
        twitter_user = text[0:p]
        num = max(int(text[p + 3:]), 1)
    except (ValueError, IndexError):
        num = 1
        twitter_user = text[0:]
    try:
        try: twitter_user = twitter_get_screen_name(twitter_user)
        except tweepy.TweepError: twitter_user = twitter_search_user(twitter_user)[0][1]
        links_to_tweets = twitter_get_tweets(twitter_user, quantity=num)
        if num == 1:
            title = f'Latest tweet from @{twitter_user}'
        else:
            title = f'Latest tweets from @{twitter_user}'
        msg = ''
        for i, link in enumerate(links_to_tweets):
            if i == 0: msg += link
            else: msg += '\n<' + link + '>'
        embed = discord.Embed(title=title, description=msg, color=TWITTER_BLUE)
        await ctx.send(embed=embed)
    except IndexError:
        await ctx.send('Could not find the user specified')


@bot.command(aliases=['tu_search'])
async def search_twitter_user(ctx):
    text = ctx.message.content[ctx.message.content.index(' ') + 1:]
    users = twitter_search_user(text)
    msg = ''
    for name, screenName in users:
        msg += f'\n{name} | @{screenName}'
    embed = discord.Embed(title='Twitter Users [Display Name | Screen name]', description=msg,
                          color=TWITTER_BLUE)
    await ctx.send(embed=embed)


@bot.command(aliases=['yt'])
async def youtube(ctx):
    try: url = youtube_search(' '.join(ctx.message.content.split()[1:]))
    except IndexError: url = 'No Video Found'
    await ctx.send(url)


@bot.command()
async def thank(ctx):
    await ctx.send(f"You're welcome {ctx.author.mention}")


@bot.command(aliases=['invite', 'invitecode', 'invite_link', 'invitelink'])
async def invite_code(ctx):
    if ctx.guild.id == MY_GUILD_ID:
        await ctx.send(f'https://discord.gg/{INVITATION_CODE}')
    else:
        with suppress(IndexError):
            await ctx.send(ctx.guild.invites()[0].url)


@bot.command()
async def games(ctx):
    await ctx.send('We have: Tic-Tac-Toe (!ttt) and Shift (!shift)')


@bot.command(aliases=['tic_tac_toe'])
async def ttt(ctx):
    global tic_tac_toe_data
    author: discord.User = ctx.message.author
    if tic_tac_toe_data.get(author, {'in_game': False})['in_game']:
        await author.send('You are already in a game. To end a game enter !end')
    else:
        msg = 'You have started a Tic-Tac-Toe game\nThe game will end after 2 minutes of' \
              'inactivity or if you enter !end\nWould you like to go first? [Y/n]'
        await author.send(msg)
        author_data = tic_tac_toe_data[author] = {'comp_moves': [], 'user_moves': [], 'danger': None,
                                                  'danger2': None, 'in_game': True, 'round': 0}
        user_msg, game_channel = None, author.dm_channel

        def check_yn(waited_msg):
            correct_prereqs = waited_msg.channel == game_channel and author == waited_msg.author
            waited_msg = waited_msg.content.lower()
            bool_value = waited_msg in ('y', 'ye', 'yes', 'n', 'no', 'na', 'nah') or 'end' in waited_msg
            return bool_value and correct_prereqs

        def check_digit(waited_msg):
            correct_prereqs = waited_msg.channel == game_channel and author == waited_msg.author
            waited_msg = waited_msg.content
            return (waited_msg.isdigit() or 'end' in waited_msg.lower()) and correct_prereqs

        while user_msg is None and author_data['in_game']:
            try:
                user_msg = await bot.wait_for('message', timeout=120, check=check_yn)
                if user_msg:
                    user_msg = user_msg.content.lower()
                    if 'end' in user_msg:
                        author_data['in_game'] = False
                        await author.send('You have ended your tic-tac-toe game')
                    else:
                        author_data['round'] = 1
                        temp_msg = tictactoe.greeting(author_data, user_msg)  # msg is y or n
                        await author.send(temp_msg)
            except asyncio.TimeoutError:
                author_data['in_game'] = False
        while author_data['in_game']:
            try:
                user_msg = await bot.wait_for('message', timeout=120, check=check_digit)
                if user_msg is not None:
                    if 'end' in user_msg.content.lower():
                        author_data['in_game'] = False
                        await author.send('You have ended your tic-tac-toe game')
                    else:
                        player_move = int(user_msg.content)

                        temp_msg = tictactoe.valid_move(player_move, author_data)
                        if not temp_msg: await author.send('That was an invalid move')
                        else:
                            temp_msg += '\n'
                            tempt = tictactoe.tic_tac_toe_move(author_data)
                            if not author_data['in_game']:
                                if author_data['round'] == 5:
                                    await author.send(f'Your Move{temp_msg + tempt}')
                                else: await author.send(f'Your Move{temp_msg}My Move{tempt}')
                            else:
                                await author.send(f'Your Move{temp_msg}My Move{tempt}\nEnter your move (#)')
                            author_data['round'] += 1
            except asyncio.TimeoutError:
                author_data['in_game'] = False


@bot.command()
async def shift(ctx):
    await ctx.send('https://elibroftw.itch.io/shift')


@bot.command(aliases=['create_date', 'createdat', 'creation_date', 'date_created', 'discord_birth'])
async def created_at(ctx):
    args = ctx.message.content.split()
    if len(args) > 1:
        name = ' '.join(args[1:])
        user = discord.utils.get(ctx.guild.members, nick=name)
        if not user:
            user = discord.utils.get(ctx.guild.members, name=name)
    else:
        user = ctx.author
    try:
        await ctx.send(user.created_at)
    except AttributeError:
        await ctx.send(f'could not find that user in the server')


@commands.check(in_guild)
@bot.command()
async def summon(ctx):
    guild = ctx.guild
    author: discord.Member = ctx.author
    data_dict[guild.id]['text_channel'] = ctx.channel.id
    if not author.voice:
        return await discord.utils.get(guild.voice_channels, name='music').connect()
    else:
        voice_client: discord.VoiceClient = guild.voice_client
        channel: discord.VoiceChannel = author.voice.channel
        if not voice_client:
            vc = await channel.connect()
            return vc
        elif voice_client.channel != channel:
            return await voice_client.move_to(channel)
        return voice_client


def normalize_url(url):
    parsed = urlparse(url)
    return 'https://' + parsed.netloc + parsed.path


async def download_if_not_exists(ctx, track: Track, play_next=False):
    """
    Checks if file corresponding to title and video_id exists
    If it doesn't exist, download it
    returns None if it exists, or discord.Message object of the downloading title if it doesn't
    """
    title = track.title
    url_or_video_id = track.get_video_id()
    from_soundcloud = track.from_soundcloud
    music_filename = track.get_path()
    m = None
    if not os.path.exists(music_filename) and track not in data_dict['downloads']:
        m = await ctx.channel.send(f'Downloading `{title}`')

        def callback(future: asyncio.Future):
            exc = future.exception()
            music_queue = data_dict[ctx.guild.id]['music']
            latest_id = music_queue[0].get_video_id()
            if exc:
                if latest_id == url_or_video_id:
                    music_queue.pop(0)
                    bot.loop.create_task(play_file(ctx))
                else:
                    music_queue.remove(Track(title, url_or_video_id, from_soundcloud=from_soundcloud))
                new_content = f'Video `{title}` with id `{url_or_video_id}` was deleted'
                return bot.loop.create_task(m.edit(content=new_content, delete_after=5))
            data_dict['downloads'].pop(track)
            if from_soundcloud:
                info_dict = future.result()
                track.title = info_dict['title']
            if latest_id == url_or_video_id:
                bot.loop.create_task(m.edit(content=f'Downloaded `{title}`', delete_after=5))
                return bot.loop.create_task(play_file(ctx))
            if play_next: msg_content = f'Added `{title}` to next up'
            else: msg_content = f'Added `{title}` to the playing queue'
            bot.loop.create_task(m.edit(content=msg_content))
        outtmpl = music_filename if from_soundcloud else ''
        result: asyncio.Future = bot.loop.run_in_executor(None, ytdl, url_or_video_id, outtmpl)
        result.add_done_callback(callback)
        data_dict['downloads'][track] = [result, m]
    return m


async def download_related_video(ctx):
    # or the next video
    guild = ctx.guild
    guild_data = data_dict[guild.id]
    auto_play_setting = guild_data['auto_play']
    mq = guild_data['music']
    if len(mq) > 1:
        next_track = mq[1]
        await download_if_not_exists(ctx, next_track)
    if auto_play_setting and len(mq) == 1:
        track = mq[0]
        if not track.from_soundcloud:
            related_title, related_video_id = get_related_video(track.get_video_id(),  guild_data['done'])[1:]
            related_track = Track(related_title, related_video_id)
            mq.append(related_track)
            related_m = await download_if_not_exists(ctx, related_track)
            related_msg_content = f'Added `{related_title}` to the playing queue'
            if not related_m: await ctx.send(related_msg_content)


# @bot.command(aliases=['dls', 'dlt'])
# @commands.check(in_guild)
# async def download_track(ctx):
#     args = ctx.message.content.split()
#     # is_query = False
#     try:
#         index = 0 if len(args) == 1 else int(args[1])
#         guild = ctx.guild
#         guild_data = data_dict[guild.id]
#         if index >= 0:  que = guild_data['music']
#         else:
#             que = guild_data['done']
#             index = -index - 1
#         try: track = que[index]
#         except IndexError:
#             return await ctx.send('Invalid index argument')
#     except ValueError:
#         # is_query = True  # TODO
#         return
#     # if len(args) > 1 or is_query:
#     #     query = ' '.join(args[1:])
#     file = track.get_path()
#     NOTE: Firefox send is deprecated
#     url = ffsend.upload('https://send.firefox.com/', track.title + '.mp3', file)[0]
#     msg = await ctx.author.send('Uploading the track')
#     content = f'Here is the download link <{url}>. You can rename the file and set the metadata and album art ' \
#               '(Spotify API) using this metadata editor <https://github.com/elibroftw/mp3-editor>'
#     await msg.edit(content=content, file=file)


@bot.command(aliases=['mute'])
@commands.check(in_guild)
async def quiet(ctx):
    """ mute any music related output """
    guild_data = data_dict[ctx.guild.id]
    guild_data['output'] = not guild_data['output']


def create_audio_source(guild_data, track, start_at=0.0):
    filename = track.get_path()
    audio_source = FFmpegPCMAudio(filename, before_options=f'-nostdin -ss {format_time_ffmpeg(start_at)}',
                                  options='-vn -b:a 128k -af bass=g=2')
    audio_source = PCMVolumeTransformer(audio_source)
    audio_source.volume = guild_data['volume']
    return audio_source


async def play_file(ctx, start_at=0):
    """Plays first (index=0) track in the music queue"""
    guild: discord.Guild = ctx.guild
    vc: discord.VoiceClient = guild.voice_client
    # noinspection PyTypeChecker
    guild_data = data_dict[guild.id]
    upcoming_tracks = guild_data['music']
    play_history = guild_data['done']
    if not upcoming_tracks and guild_data['repeat_all']:
        upcoming_tracks = guild_data['music'] = play_history[::-1]
        play_history.clear()
    elif not upcoming_tracks and guild_data['repeat']:
        upcoming_tracks.append(play_history.pop(0))

    def after_play(error):
        # noinspection PyTypeChecker
        if not error and not guild_data['is_stopped'] and not (vc.is_playing() or vc.is_paused()):
            mq = guild_data['music']
            dq = guild_data['done']
            guild_data['skip_voters'] = []

            if not guild_data['repeat']:
                last_track = mq.pop(0)
                dq.insert(0, last_track)
            else: last_track = mq[0]
            last_track.stop()

            if guild_data['repeat_all'] and not mq and dq:
                mq = guild_data['music'] = dq[::-1]
                dq.clear()

            if len(vc.channel.members) > 1:
                setting = guild_data['auto_play']
                if mq or setting:
                    if setting and not mq:
                        if not last_track.from_soundcloud:
                            next_title, next_video_id = get_related_video(last_track.get_video_id(), dq)[1:]
                            next_track = Track(next_title, next_video_id)
                            mq.append(next_track)
                            run_coroutine(download_if_not_exists(ctx, next_track))
                    else:  # if mq, check if the next track is downloading
                        next_track = mq[0]
                        next_title = next_track.title
                        next_result, next_m = data_dict['downloads'].get(next_track, (None, None))
                        if next_result:
                            # run_coroutine(next_result)
                            return
                        else:
                            # TODO test
                            next_m = run_coroutine(download_if_not_exists(ctx, next_track))
                        if next_m is None:
                            vc.play(create_audio_source(guild_data, next_track), after=after_play)
                            next_track.start(0)
                            next_time_stamp = next_track.get_time_stamp(True)
                            guild_data['is_stopped'] = False
                            if guild_data['output']:
                                next_msg_content = f'Now playing `{next_title}` {next_time_stamp}'
                                if next_m: run_coroutine(next_m.edit(content=next_msg_content))
                                elif not guild_data['repeat'] and not next_m: run_coroutine(ctx.send(next_msg_content))
                            run_coroutine(bot.change_presence(activity=discord.Game(next_title)))
                            run_coroutine(download_related_video(ctx))
            else:
                run_coroutine(bot.change_presence(activity=discord.Game('Prison Break (!)')))
                if len(vc.channel.members) == 1: run_coroutine(vc.disconnect())

    if vc and upcoming_tracks:
        track = upcoming_tracks[0]
        title = track.title
        result, m = data_dict['downloads'].get(track, (None, None))
        if result:
            # TODO: test?
            # await result
            return
        m = await download_if_not_exists(ctx, track)
        if m is None:
            audio_source = create_audio_source(guild_data, track, start_at=start_at)
            vc.play(audio_source, after=after_play)
            track.start(start_at)
            time_stamp = track.get_time_stamp(True)
            guild_data['is_stopped'] = False
            # guild_data['skip_voters'] = []
            if guild_data['output']:
                msg_content = f'Now playing `{title}` {time_stamp}'
                if m: await m.edit(content=msg_content)
                else:
                    temp_mq = deepcopy(upcoming_tracks)
                    temp_dq = deepcopy(play_history)
                    await ctx.send(msg_content)
                    if temp_mq != upcoming_tracks:
                        guild_data['music'] = deepcopy(temp_mq)
                        guild_data['done'] = deepcopy(temp_dq)
            await bot.change_presence(activity=discord.Game(title))
            await download_related_video(ctx)


@bot.command(aliases=['paly', 'p', 'P', 'pap', 'pn', 'play_next', 'playnext'])
@commands.check(in_guild)
async def play(ctx):
    guild = ctx.guild
    voice_client: discord.VoiceClient = guild.voice_client
    ctx_msg_content = ctx.message.content
    play_next = any([cmd in ctx_msg_content for cmd in ('pn', 'play_next', 'playnext')])
    guild_data = data_dict[guild.id]

    mq = guild_data['music']
    if voice_client is None: voice_client = await ctx.invoke(bot.get_command('summon'))
    url_or_query = ctx.message.content.split()
    if len(url_or_query) > 1:
        url_or_query = ' '.join(url_or_query[1:])
        video_id = extract_video_id(url_or_query)
        from_soundcloud = False
        # TODO: cleanup. Use query_to_tracks
        if video_id is not None:
            title = get_video_title(video_id)
            if get_video_duration(video_id) > 1800:
                await ctx.send('That track is too long! (> 30 minutes)')
                return
        elif url_or_query.startswith('https://www.youtube.com/playlist'):
            playlist_id = parse_qs(urlsplit(url_or_query).query)['list'][0]
            tracks = get_videos_from_playlist(playlist_id, return_title=True)[0]
            # tracks = get_videos_from_yt_playlist(url_or_query)[0]
            if tracks:
                mq.extend(tracks)
                await ctx.send('Tracks added to queue!')
            if len(tracks) == len(mq):
                await play_file(ctx)
            return
        elif 'soundcloud.com' in url_or_query:
            if 'sets' in url_or_query:
                return await ctx.send('Sound cloud playlists are not supported at the moment')
            from_soundcloud = True
            title = video_id = normalize_url(url_or_query)
        elif 'spotify.com' in url_or_query:
            tracks = spotify_to_youtube(url_or_query)
            if not tracks:
                # illegal Spotify link or empty playlist / album
                return await ctx.send('ERROR: No tracks found with for that Spotify link')
            elif len(tracks) == 1:
                title, video_id = tracks[0].title, tracks[0].get_video_id()
            else:
                mq.extend(tracks)
                await ctx.send('Tracks added to queue!')
                if len(tracks) == len(mq): await play_file(ctx)
                return
        else:
            try: title, video_id = youtube_search(url_or_query, return_info=True, limit_duration=True)[1:]
            except (ValueError, IndexError):
                return await ctx.send(f'No valid video found with query `{url_or_query}`')
        track = Track(title, video_id, from_soundcloud=from_soundcloud)

        # adding to queue
        if mq and play_next: mq.insert(1, track)
        else: mq.append(track)

        # download the track if something is playing
        if voice_client.is_playing() or voice_client.is_paused():
            # download if your not going to play the file
            m = await download_if_not_exists(ctx, track, play_next=play_next)
            if play_next: m_content = f'Added `{title}` to next up'
            else: m_content = f'Added `{title}` to the playing queue'
            if not m: await ctx.send(m_content)
        else: await play_file(ctx)  # download if need to and then play the track

    elif (voice_client.is_playing() or voice_client.is_paused()) and not play_next:
        await ctx.invoke(bot.get_command('pause'))
    elif mq: await play_file(ctx)
    if ctx_msg_content.startswith('!pap'):
        await ctx.invoke(bot.get_command('auto_play'))


@bot.command(aliases=['resume'])
@commands.check(in_guild)
async def pause(ctx):
    voice_client: discord.VoiceClient = ctx.guild.voice_client
    if voice_client:
        guild_data = data_dict[ctx.guild.id]
        track = guild_data['music'][0]
        if voice_client.is_paused():
            voice_client.resume()
            track.start()
            guild_data['is_stopped'] = False
            await bot.change_presence(activity=discord.Game(track.title))
        else:
            voice_client.pause()
            track.pause()
            guild_data['is_stopped'] = True
            await bot.change_presence(activity=discord.Game('Prison Break (!)'))


@bot.command(aliases=['ap', 'autoplay'])
@commands.check(in_guild)
async def auto_play(ctx, setting: bool = None):
    """Turns auto play on or off"""
    guild = ctx.guild
    guild_data = data_dict[guild.id]
    if setting is None: setting = not guild_data['auto_play']
    guild_data['auto_play'] = setting
    await ctx.send(f'Auto play set to {setting}')
    if setting:
        guild_data['repeat_all'] = False
        mq = guild_data['music']
        dq = guild_data['done']
        if not mq and dq:
            track_id = dq[0].get_video_id()
            title, video_id, = get_related_video(track_id, dq)[1:]
            mq.append(Track(title, video_id))
            await play_file(ctx)  # takes care of the download
        await download_related_video(ctx)


@bot.command(name='repeat', aliases=['r'])
@commands.check(in_guild)
async def _repeat(ctx, setting: bool = None):
    guild = ctx.guild
    voice_client: discord.VoiceClient = guild.voice_client
    guild_data = data_dict[guild.id]
    if setting is None: setting = not guild_data['repeat']
    data_dict[guild.id]['repeat'] = setting
    if setting:
        await ctx.send('Repeating the current track')
        if voice_client and not voice_client.is_playing() and not voice_client.is_paused():
            mq = data_dict[guild.id]['music']
            dq = data_dict[guild.id]['done']
            if not mq and dq:
                mq.append(dq.pop(0))
                await play_file(ctx)
    else:
        await ctx.send('Not repeating the current track')


@bot.command(name='repeat_all', aliases=['ra'])
@commands.check(in_guild)
async def _repeat_all(ctx, setting: bool = None):
    guild = ctx.guild
    voice_client: discord.VoiceClient = guild.voice_client
    guild_data = data_dict[guild.id]
    if setting is None: setting = not data_dict[guild.id]['repeat_all']
    data_dict[guild.id]['repeat_all'] = setting

    if setting:
        await ctx.send('Repeating all set to True')
        guild_data['auto_play'] = False
        if voice_client and not voice_client.is_playing() and not voice_client.is_paused():
            mq = guild_data['music']
            dq = guild_data['done']
            if not mq and dq:
                guild_data['music'] = dq[::-1]
                dq.clear()
                await play_file(ctx)
    else: await ctx.send('Repeating all set to False')


def no_after_play(guild_data, voice_client):
    if voice_client and voice_client.is_playing() or voice_client.is_paused():
        guild_data['is_stopped'] = True
        guild_data['music'][0].stop()
        voice_client.stop()


@bot.command(aliases=['next', 'n', 'N', 'sk'])
@commands.check(in_guild)
async def skip(ctx, times=1):
    guild = ctx.guild
    voice_client: discord.VoiceClient = guild.voice_client
    if voice_client:
        guild_data = data_dict[guild.id]
        mq = guild_data['music']
        dq: list = guild_data['done']
        guild_data['repeat'] = False
        no_after_play(guild_data, voice_client)
        if len(mq) > 1:
            times = min(times, len(mq) - 1)
            guild_data['done'] = mq[:times][::-1] + dq
            guild_data['music'] = mq[times:]
            await play_file(ctx)
        elif len(mq) == 1:
            dq.insert(0, mq.pop(0))
            if guild_data['repeat_all']:
                times = min(times - 1, len(dq) - 2)
                guild_data['music'] = dq[:-times][::-1]
                guild_data['done'] = dq[-times:]
                await play_file(ctx)


@bot.command(aliases=['back', 'b', 'prev', 'go_back', 'gb'])
@commands.check(in_guild)
async def previous(ctx, times=1):
    guild = ctx.guild
    voice_client: discord.VoiceClient = guild.voice_client
    if voice_client:
        guild_data = data_dict[guild.id]
        mq = guild_data['music']
        dq = guild_data['done']
        guild_data['repeat'] = False
        no_after_play(guild_data, voice_client)
        if dq:
            times = min(times, len(dq))
            guild_data['music'] = dq[:times][::-1] + mq
            guild_data['done'] = dq[times:]
            await play_file(ctx)
        elif mq and guild_data['repeat_all']:
            times = min(len(mq) - 1, times)
            dq += mq[:-times][::-1]
            guild_data['music'] = mq[-times:]
            await play_file(ctx)


@bot.command(aliases=['rm'])
@commands.check(in_guild)
async def remove(ctx, position: int = 0):
    guild = ctx.guild
    guild_data = data_dict[guild.id]
    mq = guild_data['music']
    dq = guild_data['done']
    voice_client: discord.VoiceClient = guild.voice_client
    with suppress(IndexError):
        if position < 0: removed_track = dq.pop(-position - 1)
        elif position > 0: removed_track = mq.pop(position)
        else:
            no_after_play(guild_data, voice_client)
            removed_track = mq.pop(0)
        await ctx.send(f'Removed `{removed_track.title}`')
        if position == 0: await play_file(ctx)


@bot.command()
@commands.check(in_guild)
async def move(ctx, _from: int, _to: int):
    guild_data = data_dict[ctx.guild.id]
    if 0 in (_from, _to) or _from == _to: return
    if 0 < _from < _to and _to > 0: _to += 1
    elif _to < _from < 0: _to -= 1
    if _from > 0: from_queue = guild_data['music']
    else:
        from_queue = guild_data['done']
        _from = -_from - 1
    try: track = from_queue[_from]
    except IndexError: return
    if _to > 0: to_queue: list = guild_data['music']
    else:
        to_queue = guild_data['done']
        _to = -_to - 1
    to_queue.insert(_to, track)
    if to_queue == from_queue and _to < _from: _from += 1
    from_queue.pop(_from)


@bot.command(aliases=['sm', 'shuffle'])
@commands.check(in_guild)
async def shuffle_music(ctx):
    guild = ctx.guild
    guild_data = data_dict[guild.id]
    voice_client = guild.voice_client
    track_playing = voice_client.is_playing() or voice_client.is_paused()
    current_track = guild_data['music'][0]

    shuffled_tracks = guild_data['music'] + guild_data['done']
    shuffle(shuffled_tracks)

    if track_playing:
        shuffled_tracks.remove(current_track)
        shuffled_tracks = [current_track] + shuffled_tracks

    guild_data['music'] = shuffled_tracks
    guild_data['done'].clear()
    await ctx.send('Shuffled music!')


@bot.command(aliases=['cq', 'clearque', 'clear_q', 'clear_que', 'clearq', 'clearqueue', 'queue_clear', 'queueclear'])
@commands.check(in_guild)
async def clear_queue(ctx):
    guild = ctx.guild
    moderator = discord.utils.get(guild.roles, name='Moderator')
    if ctx.author.top_role >= moderator:
        voice_client: discord.VoiceClient = guild.voice_client
        mq = data_dict[guild.id]['music']
        dq = data_dict[guild.id]['done']
        if voice_client.is_playing() or voice_client.is_paused():
            data_dict[guild.id]['music'] = mq[0:1]
        else: mq.clear()
        dq.clear()
        await ctx.send('Cleared music queue')


@bot.command(aliases=['music_queue', 'mq', 'nu', 'queue', 'que', 'q'])
@commands.check(in_guild)
async def next_up(ctx, page=1):
    # TODO: add reaction emoticons
    guild = ctx.guild
    guild_data = data_dict[guild.id]
    mq = guild_data['music']
    if mq:
        page = abs(page)
        mq_length = len(mq)
        max_pages = ceil(mq_length / 10)
        title = f"Music Queue [{mq_length} Track{'s' if mq_length > 1 else ''} | Page {page} of {max_pages}]"
        if guild_data['auto_play']: title += ' | Auto-play Enabled'
        if guild_data['repeat_all']: title += ' | Repeat All Enabled'
        if guild_data['repeat']: title += ' | Repeat Track Enabled}'
        msg = ''
        i = 10 * (page - 1)
        for track in mq[i:10 * page]:
            if i == 0:
                status = track.get_length()
                if status == 'DOWNLOADING':
                    msg += f'`DOWNLOADING` {track.title}'
                else:
                    status = track.status
                    msg += f'`{status}` {track.title} `{track.get_time_stamp(True)}`'

            else: msg += f'\n`{i}.` {track.title} `[{track.get_length(True)}]`'
            i += 1

        if mq_length > i:
            msg += '\n...'

        embed = discord.Embed(title=title, description=msg, color=BLUE)
        await ctx.send(embed=embed)
    else: await ctx.send(embed=discord.Embed(title='Music Queue is empty', description='', color=BLUE))


@bot.command(name='recently_played', aliases=['done_queue', 'dq', 'rp'])
@commands.check(in_guild)
async def _recently_played(ctx, page=1):
    # TODO: add reaction emoticons
    guild = ctx.guild
    dq = data_dict[guild.id]['done']
    if dq:
        page = abs(page)
        dq_length = len(dq)
        title = f"Recently Played [{dq_length} Track{'s' if dq_length > 1 else ''} | Page {page}]"
        msg = ''

        i = 10 * (page - 1)
        for track in dq[i:i + 10]:
            i += 1
            msg += f'\n`-{i}` {track.title} `{track.get_length(True)}`'

        if dq_length > i:
            msg += '\n...'

        await ctx.send(embed=discord.Embed(title=title, description=msg, color=BLUE))
    else: await ctx.send('Recently Played is empty, were you looking for !play_history?')


@bot.command(aliases=['start_at', 'st'])
@commands.check(in_guild)
async def skip_to(ctx, seconds: int):
    guild = ctx.guild
    voice_client = guild.voice_client
    if voice_client.is_playing() or voice_client.is_paused():
        no_after_play(data_dict[guild.id], voice_client)
        await play_file(ctx, seconds)


@bot.command(aliases=['ff', 'fwd'])
@commands.check(in_guild)
async def fast_forward(ctx, seconds: int = 5):
    guild = ctx.guild
    voice_client = guild.voice_client
    if voice_client.is_playing() or voice_client.is_paused():
        guild_data = data_dict[guild.id]
        current_track = guild_data['music'][0]
        start_at = current_track.get_time_stamp() + seconds
        start_at = min(current_track.get_length(), start_at)
        no_after_play(guild_data, voice_client)
        await play_file(ctx, start_at)


@bot.command(aliases=['rwd', 'rw'])
@commands.check(in_guild)
async def rewind(ctx, seconds: int = 5):
    guild = ctx.guild
    voice_client = guild.voice_client
    if voice_client.is_playing() or voice_client.is_paused():
        guild_data = data_dict[guild.id]
        start_at = guild_data['music'][0].get_time_stamp() - seconds
        start_at = max(0, start_at)
        no_after_play(guild_data, voice_client)
        await play_file(ctx, int(start_at))


@bot.command(aliases=['np', 'currently_playing', 'cp'])
@commands.check(in_guild)
async def now_playing(ctx):
    guild = ctx.guild
    mq = data_dict[guild.id]['music']
    track = mq[0]
    embed = discord.Embed(title=track.title, url=f'https://www.youtube.com/watch?v={track.get_video_id()}',
                          description=track.get_time_stamp(True), color=0xff0000)
    embed.set_author(name='Now Playing')
    await ctx.send(embed=embed)
    # https://cog-creators.github.io/discord-embed-sandbox/


@bot.command(aliases=['desummon', 'disconnect', 'unsummon', 'dismiss', 'd'])
@commands.check(in_guild)
async def leave(ctx):
    guild = ctx.guild
    voice_client: discord.VoiceClient = guild.voice_client
    if voice_client:
        await voice_client.disconnect()
        guild_data = data_dict[guild.id]
        guild_data['music'].clear()
        guild_data['auto_play'] = False
        await ctx.send('Stopped playing music and cleared the music queue')


@bot.command(aliases=['s', 'end'])
@commands.check(in_guild)
async def stop(ctx):
    guild = ctx.guild
    voice_client: discord.VoiceClient = guild.voice_client
    guild_data = data_dict[guild.id]
    no_after_play(guild_data, voice_client)


@bot.command()
@commands.check(in_guild)
async def fix(ctx):
    guild = ctx.message.channel.guild
    await ctx.invoke(bot.get_command('summon'))
    voice_client: discord.VoiceClient = guild.voice_client
    await voice_client.disconnect()
    await ctx.invoke(bot.get_command('summon'))


@bot.command(aliases=['set_volume', 'sv', 'v'])
@commands.check(in_guild)
async def volume(ctx):
    guild = ctx.guild
    vc: discord.VoiceClient = guild.voice_client
    if vc:
        args = ctx.message.content.split()
        if len(args) == 2:
            try:
                arg = args[1]
                if arg.startswith('+'):
                    if arg[1:]: amount = vc.source.volume + float(arg[1:]) / 100
                    else: amount = vc.source.volume + 0.1
                elif arg.startswith('-'):
                    if arg[1:]: amount = vc.source.volume - float(arg[1:]) / 100
                    else: amount = vc.source.volume - 0.1
                else: amount = float(args[1]) / 100
                amount = max(0.0, amount)
                amount = min(1.0, amount)
                amount = round(amount, 2)
                vc.source.volume = amount
                data_dict[guild.id]['volume'] = amount
            except ValueError: await ctx.send('Invalid argument', delete_after=5)
            except AttributeError: await ctx.send('Nothing is playing at the moment', delete_after=5)
        else: await ctx.send(f'{vc.source.volume * 100}%')


@bot.command(aliases=['sa'])
@commands.check(in_guild)
async def save_as(ctx):
    playlist_name = ' '.join(ctx.message.content.split()[1:])
    if playlist_name:
        author_id = ctx.author.id
        guild_id = ctx.guild.id
        mq = data_dict[guild_id]['music']
        dq = data_dict[guild_id]['done']
        temp = dq[::-1] + mq
        track_ids = [(track.title, track.get_video_id()) for track in temp]
        document = {'guild_id': ctx.guild.id, 'playlist_name': playlist_name,
                    'creator_id': author_id, 'tracks': track_ids, 'type': 'playlist'}
        look_for = {'playlist_name': playlist_name, 'creator_id': author_id}
        result = playlists_coll.replace_one(look_for, document, upsert=True)
        if result.upserted_id: await ctx.send(f'Successfully created playlist `{playlist_name}`!')
        else: await ctx.send(f'Successfully updated playlist `{playlist_name}`!')


# for example, --creator <name/id>
# and also !pp <post_id>
@bot.command(aliases=['pp', 'sp'])
@commands.check(in_guild)
async def play_playlist(ctx):
    split_content = ctx.message.content.split()
    key_word = split_content[0]
    playlist_name = ' '.join(split_content[1:])
    if playlist_name:
        guild_id = ctx.guild.id
        playlist_name = playlist_name.replace(' --s', '--s')
        parsed_out_name = playlist_name.replace('--s', '')
        tracks = get_tracks_from_playlist(parsed_out_name, guild_id, ctx.author.id, to_play=True)[0]
        if tracks:
            voice_client = ctx.guild.voice_client
            if voice_client is None: voice_client = await ctx.invoke(bot.get_command('summon'))
            guild_data = data_dict[guild_id]
            no_after_play(guild_data, voice_client)
            if parsed_out_name != playlist_name or key_word == '!sp': shuffle(tracks)
            guild_data['music'] = tracks
            guild_data['done'].clear()
            await play_file(ctx)
        else: await ctx.send('No playlist found with that name')


@bot.command(aliases=['lp', 'load_pl', 'load', 'l'])
@commands.check(in_guild)
async def load_playlist(ctx):
    playlist_name = ' '.join(ctx.message.content.split()[1:])
    if playlist_name:
        tracks = get_tracks_from_playlist(playlist_name, ctx.guild.id, ctx.author.id)[0]
        if tracks:
            data_dict[ctx.guild.id]['music'].extend(tracks)
            await ctx.send('Tracks added to queue!')
        else: await ctx.send('No playlist found with that name')


@bot.command(aliases=['vp'])
@commands.check(in_guild)
async def view_playlist(ctx):
    playlist_name = ' '.join(ctx.message.content.split()[1:])
    if playlist_name:
        tracks, playlist_name = get_tracks_from_playlist(playlist_name, ctx.guild.id, ctx.author.id)
        if tracks:
            pl_length = len(tracks)
            msg = ''
            for i, track in enumerate(tracks[:10]):
                msg += f'\n`{i + 1}.` {track.title}'
            if pl_length > 10: msg += '\n...'
            title = f"PLAYLIST {playlist_name} | {pl_length} Track{'s' if pl_length > 1 else ''}"
            await ctx.send(embed=discord.Embed(title=title, description=msg, color=BLUE))
        else: await ctx.send('No playlist found with that name')


@bot.command(aliases=['bp'])
@commands.check(in_guild)
async def browse_playlists(ctx, page=1):
    # 10 playlists per page
    all_playlists = sorted(get_all_playlists(), key=lambda p: p['playlist_name'])
    max_pages = ceil(len(all_playlists) / 10)
    if page > max_pages: page = max_pages
    playlists = all_playlists[10 * (page - 1): 10 * page]
    members = bot.get_all_members()
    # formatted_playlists = []
    msg = ''
    temp_creators = {}
    for playlist in playlists:
        creator_id = playlist['creator_id']
        if creator_id not in temp_creators:
            creator = discord.utils.find(lambda m: m.id == creator_id, members)
            if creator is None: creator = 'Unknown'
            temp_creators[creator_id] = creator
        msg += f"`{playlist['playlist_name']}` by {temp_creators[creator_id]}\n"
    msg.strip()
    embed = discord.Embed(title=f'PLAYLISTS INDEX | Page {page} of {max_pages}', description=msg, color=BLUE)
    await ctx.send(embed=embed)


@bot.command(aliases=['delete_pl', 'dp'])
async def delete_playlist(ctx):
    playlist_name = ' '.join(ctx.message.content.split()[1:])
    if playlist_name:
        r = playlists_coll.delete_one({'playlist_name': playlist_name, 'creator_id': ctx.author.id})
        if r.deleted_count: await ctx.send(f'Deleted playlist `{playlist_name}``')
        else: await ctx.send(f'No playlist found with that name')


@bot.command(aliases=['mp'])
async def my_playlists(ctx):
    result = playlists_coll.find({'creator_id': ctx.author.id})
    msg = ''
    for playlist in result:
        number = len(playlist['tracks'])
        if number == 1: msg += f"\n`{playlist['playlist_name']}` - 1 Track"
        else: msg += f"\n`{playlist['playlist_name']}` - {number} Tracks"
    await ctx.send(embed=discord.Embed(title=f'You have {result.count()} playlists', description=msg, color=BLUE))


@bot.command()
async def has_nick(ctx):
    await ctx.send(discord.utils.get(ctx.guild.members, nick=ctx.message.content.split()[1]))


# The following code is modified version of https://github.com/LaughingLove/anon-bot
#  A project that I contributed to
# modifications: supporting mongoDB + removal of reporting tool and stored messages


@bot.command(aliases=['DM', 'Dm', 'msg', 'MSG'])
async def dm(ctx):
    args = ctx.message.content.split()
    if len(args) > 2:
        receiver, message = args[1], ' '.join(args[2:])
        # checks if a user id was supplied
        if receiver.isdigit(): receiver = discord.utils.get(bot.users, id=receiver)
        else:
            # nope, user is a string. check if it includes a discriminator for accuracy
            # remove any @ if there is one
            receiver = receiver.replace('@', '')
            if '#' in receiver: receiver = discord.utils.get(bot.users, name=receiver[:-5], discriminator=receiver[-4:])
            else:
                temp = receiver
                receiver = discord.utils.get(bot.users, name=receiver)
                if receiver is None:
                    for guild in bot.guilds:
                        if ctx.author in guild.members:
                            receiver = discord.utils.get(guild.members, nick=temp)
                            break

        # search for user by name, returns first match, people can use at their own digestion
        if receiver:
            receiver_id = receiver.id
            # check if user has anonymous messaging enabled
            user_settings = dm_coll.find_one({'user_id': receiver_id, 'type': 'user_settings'})
            if user_settings: allows_messages = user_settings['allows_messages']
            else:
                dm_coll.insert_one({'user_id': receiver_id, 'type': 'user_settings', 'allows_messages': True})
                allows_messages = True
            if allows_messages:
                sender_id = ctx.author.id
                message_thread = dm_coll.find_one({'sender': sender_id, 'receiver': receiver_id})
                if message_thread: thread_id = message_thread['thread_id']
                else:
                    thread_id = 0
                    message_thread = True
                while message_thread is not None:
                    thread_id = randint(0, 16777215)
                    message_thread = dm_coll.find_one({'thread_id': thread_id, 'type': 'message_thread'})
                dm_coll.insert_one({'thread_id': thread_id, 'sender': sender_id, 'receiver': receiver_id,
                                    'type': 'message_thread'})
                thread_id_color = discord.Color(thread_id)
                thread_id = str(thread_id)
                embed = discord.Embed(title='Message Received :mailbox_with_mail:', color=thread_id_color,
                                      description=f'Reply with `!reply {thread_id} <msg>`')
                embed.add_field(name='Thread ID:', value=thread_id, inline=True)
                embed.add_field(name='Message:', value=message, inline=True)
                await receiver.send(embed=embed)
                embed = discord.Embed(title='Message Sent :airplane:', color=thread_id_color)
                embed.add_field(name='To:', value=str(receiver))
                embed.add_field(name='Thread ID:', value=thread_id)
                await ctx.author.send(embed=embed)
            else:
                await ctx.author.send(f'{receiver.name} is not accepting anonymous messages at this time.')
        else:
            await ctx.author.send(f'A user with that name could not be found. Names are case sensitive.')
    else:
        await ctx.send('You must have at least 2 arguments! Refer to !help for more information.')
    if not isinstance(ctx.channel, discord.DMChannel):
        await ctx.author.send(f'TIP: use `!dm` in a DM chat with me')
        await ctx.message.delete()


@bot.command(aliases=['re', 'RE'])
async def reply(ctx):
    if isinstance(ctx.channel, discord.DMChannel):
        args = ctx.message.content.split()
        if len(args) > 2:
            thread_id, message = int(args[1]), ' '.join(args[2:])
            user = ctx.author
            message_thread = dm_coll.find_one({'thread_id': thread_id, 'type': 'message_thread'})
            if message_thread:
                receiver_id = message_thread['receiver']
                if receiver_id == user.id:
                    embed_title = f'{user} replied to your message!'
                    receiver_id = message_thread['sender']
                else:
                    embed_title = 'You got another message'
                # received_embed_color = 0x267d28
                # receipt_embed_color = 0x2ecc71
                thread_id_color = discord.Color(thread_id)
                embed = discord.Embed(title=embed_title, color=thread_id_color,
                                      description=f'Use `!reply {thread_id} <msg>` to respond')
                embed.add_field(name='Thread ID:', value=str(thread_id), inline=True)
                embed.add_field(name='Message:', value=message, inline=True)
                receiver = bot.get_user(receiver_id)
                await receiver.send(embed=embed)
                await ctx.author.send('Reply sent! :airplane:')
            else:
                await ctx.author.send(f'Unknown message thread!')
        else:
            await ctx.author.send(
                "You must have at least 2 arguments in your command! Refer to !help for more information.")
    else:
        await ctx.author.send(f'TIP: use `!dm` in a DM chat with me')
        await ctx.message.delete()


@bot.command(aliases=['enable', 'enablemessages'])
async def enable_messages(ctx):
    user_id = ctx.author.id
    dm_coll.update_one({'user_id': user_id, 'type': 'user_settings'}, {'$set', {'allows_messages': True}}, upsert=True)
    await ctx.send('Anonymous messaging has been **ENABLED**')


@bot.command(aliases=['disable', 'disablemessages'])
async def disable_messages(ctx):
    user_id = ctx.author.id
    dm_coll.update_one({'user_id': user_id, 'type': 'user_settings'}, {'$set', {'allows_messages': False}}, upsert=True)
    await ctx.send('Anonymous messaging has been **DISABLED**')


@bot.command(aliases=['anonstatus'])
async def anon_status(ctx):
    user_id = ctx.author.id
    user_settings = dm_coll.find_one({'user_id': user_id, 'type': 'user_settings'})
    if user_settings: allows_messages = user_settings['allows_messages']
    else:
        dm_coll.insert_one({'user_id': user_id, 'type': 'user_settings', 'allows_messages': True})
        allows_messages = True
    setting = '**ENABLED**' if allows_messages else '**DISABLED**'
    await ctx.send(f'Anonymous messaging is {setting}')
# END of modified code


# Investing
@bot.command(aliases=['ticker', 'get_ticker', 'stock', 'stock_info', 'get_stock'])
async def ticker_info(ctx, ticker: str):

    def _get_ticker_info():
        nonlocal ticker
        ticker = ticker.replace('$', '').upper()
        m = run_coroutine(ctx.send(f'Getting stock info of {ticker}'))
        _ticker_info = get_ticker_info(ticker)
        if _ticker_info['change'] < 0:
            embed_color = STOCKS_RED  # red
            _ticker_info['change'] = f'{_ticker_info["change"]} ({_ticker_info["percent_change"]}%)'
        elif _ticker_info['change'] > 0:
            embed_color = STOCKS_GREEN
            _ticker_info['change'] = f'+{_ticker_info["change"]} (+{_ticker_info["percent_change"]}%)'
        else:
            embed_color = discord.Color.light_grey()
            _ticker_info['change'] = f'{_ticker_info["change"]} ({_ticker_info["percent_change"]}%)'
        hour = _ticker_info['timestamp'].strftime('%I')
        if hour[0] == '0': hour = hour[1]
        timestamp = _ticker_info['timestamp'].strftime(f'%B %d {hour}:%M%p %Z')
        embed = discord.Embed(title=_ticker_info['name'] + f' ({ticker})', color=embed_color)
        embed.set_footer(text=f'Last updated: {timestamp}')
        embed.add_field(name='Last Price:', value=_ticker_info['price'], inline=True)
        embed.add_field(name='Last Close:', value=_ticker_info['last_close_price'], inline=True)
        embed.add_field(name='Change:', value=_ticker_info['change'], inline=True)
        run_coroutine(m.edit(embed=embed))
    bot.loop.run_in_executor(None, _get_ticker_info)


# noinspection PyTypeChecker
@bot.command(aliases=['buy_stock', 'hold_stock', 'buystock'])
async def buy(ctx, ticker, cost_per_share: float, shares_purchased: int, commission_fee=0.0):
    ticker = ticker.replace('$', '').upper()
    portfolio = portfolio_coll.find_one({'user': ctx.author.id})
    cost = shares_purchased * cost_per_share + commission_fee
    today = str(datetime.today().date())
    if portfolio is None:
        portfolio = {'user': ctx.author.id,
                     'holdings': {},
                     'realized_gains': 0, 'ledger': []}
    if ticker not in portfolio['holdings']:
        portfolio['holdings'][ticker] = {'total_shares': 0, 'average_cost': 0, 'purchases': {}}
    ticker_holdings = portfolio['holdings'][ticker]
    price_key = str(cost_per_share).replace('.', ',')  # keys in MongoDB can't contain '.' :/
    try:
        todays_purchases = ticker_holdings['purchases'][today]
        try: todays_purchases[price_key] += shares_purchased
        except KeyError: todays_purchases[price_key] = shares_purchased
    except KeyError:
        ticker_holdings['purchases'][today] = {price_key: shares_purchased}
    new_total = ticker_holdings['total_shares'] + shares_purchased
    new_avg_cost = (ticker_holdings['average_cost'] * ticker_holdings['total_shares'] + cost) / new_total
    ticker_holdings['average_cost'] = new_avg_cost
    ticker_holdings['total_shares'] = new_total
    portfolio['realized_gains'] -= commission_fee
    portfolio['ledger'].append({today: {'ticker': ticker, 'shares': shares_purchased, 'action': 'buy',
                                        'price': cost_per_share, 'commission_fee': commission_fee}})
    portfolio_coll.replace_one({'user': ctx.author.id}, portfolio, upsert=True)
    await ctx.send('Shares added to portfolio')


@bot.command(aliases=['sell_stock', 'sellstock'])
async def sell(ctx, ticker, price_per_share: float, shares_sold: int, commission_fee=0.0):
    ticker = ticker.replace('$', '').upper()
    portfolio = portfolio_coll.find_one({'user': ctx.author.id})
    if portfolio is not None:
        with suppress(KeyError, AssertionError):
            ticker_holdings = portfolio['holdings'][ticker]
            assert ticker_holdings['total_shares'] >= shares_sold
            ticker_holdings['total_shares'] -= shares_sold
            purchases = []
            for date in ticker_holdings['purchases']:
                for pair in ticker_holdings['purchases'][date].items():
                    pair = list(pair) + [date]
                    pair[0] = pair[0].replace(',', '.')
                    purchases.append(list(pair) + [date])
            purchases.sort(key=lambda item: float(item[0]))
            cost = commission_fee
            i = 0
            shares_sold_copy = shares_sold
            while shares_sold > 0:
                shares_at_price = purchases[i][1]
                if shares_at_price > shares_sold:
                    purchases[i][1] -= shares_sold
                    cost += shares_sold * float(purchases[i][0])
                    shares_sold = 0
                else:
                    shares_sold -= shares_at_price
                    cost += shares_at_price * float(purchases[i][0])
                    purchases[i][1] = 0
                    i += 1
            total_cost = 0
            for purchase in purchases:
                if purchase[1] == 0:  # pop the purchase if there are no more shares at that price
                    ticker_holdings['purchases'][purchase[2]].pop(purchase[0].replace('.', ','))
                    if not ticker_holdings['purchases'][purchase[2]]:
                        ticker_holdings['purchases'].pop(purchase[2])
                else:  # modify purchase with new number of shares
                    total_cost += float(purchase[0]) * purchase[1]
                    ticker_holdings['purchases'][purchase[2]][purchase[0].replace('.', ',')] = purchase[1]
            if ticker_holdings['total_shares']:
                ticker_holdings['average_cost'] = total_cost/ticker_holdings['total_shares']
            else:
                portfolio['holdings'].pop(ticker)
            portfolio['realized_gains'] += (shares_sold_copy * price_per_share - cost)
            today = str(datetime.today().date())

            portfolio['ledger'].append({today: {'ticker': ticker, 'shares': shares_sold_copy, 'action': 'sell',
                                                'price': price_per_share, 'commission_fee': commission_fee}})
            portfolio_coll.replace_one({'user': ctx.author.id}, portfolio)
            await ctx.send('Shares removed to portfolio')


# @bot.command(aliases=['portfolio'])
# async def holdings(ctx: Context, to_dm=False):  # TODO
#     await ctx.send('Feature coming soon')


# @bot.command(aliases=['download_holdings', 'dlportf', 'xportf'])
# async def download_portfolio(ctx: Context, to_dm=True):  # TODO
#     # export to a csv or xlxs file
#     # use firefox send
#     # send in a DM channel by default
#     await ctx.send('Feature coming soon')


@bot.command()
async def transactions_template(ctx):
    await ctx.send('https://1drv.ms/x/s!AnQNFW1ohAx2hpEjhlgHkbvcaPLy2Q?e=jZCsn3')


@bot.command(aliases=['gainers', 'winners', 'top_gainers'])
async def command_winners(ctx, market='ALL', of='day', show=5, sorted_info: list = None):
    def _winners():
        nonlocal market, show, sorted_info
        market = market.upper()
        eta = MOVERS_ETAS.get(market, '?')
        if sorted_info is None:
            m = run_coroutine(ctx.send(f'Calculating Top Winners for {market} (ETA. {eta})'))
            sorted_info = get_latest_sorted_info(of, market)
        else: m = None
        winners_list = winners(sorted_info=sorted_info, of=of, show=show, market=market)
        show = len(winners_list)
        msg = ''
        for i, winner in enumerate(winners_list):
            if i != 0: msg += '\n'
            ticker = winner[0]
            open_close = f'[{round(winner[1]["Start"], 2)}, {round(winner[1]["End"], 2)}]'
            percent_change = str(round(winner[1]["Percent Change"] * 100, 2)) + '%'
            msg += f'{ticker}\t{open_close}\t{percent_change}'
        embed = discord.Embed(title=f'{market} Top {show} Winners ({of})', description=msg, color=STOCKS_GREEN)
        if m is None: run_coroutine(ctx.send(embed=embed))
        else: run_coroutine(m.edit(content='', embed=embed))
    bot.loop.run_in_executor(None, _winners)


@bot.command(aliases=['losers', 'top_losers'])
async def command_losers(ctx: Context, market='ALL', of='day', show=5, sorted_info: list = None):
    def _losers():
        nonlocal market, show, sorted_info
        market = market.upper()
        eta = MOVERS_ETAS.get(market, '?')

        if sorted_info is None:
            m = run_coroutine(ctx.send(f'Calculating Top Losers for {market} (ETA. {eta})'))
            sorted_info = get_latest_sorted_info(of, market)
        else: m = None
        losers_list = losers(sorted_info=sorted_info, of=of, show=show, market=market)
        show = len(losers_list)
        msg = ''
        for i, loser in enumerate(losers_list):
            if i != 0: msg += '\n'
            ticker = loser[0]
            open_close = f'[{round(loser[1]["Start"], 2)}, {round(loser[1]["End"], 2)}]'
            percent_change = str(round(loser[1]["Percent Change"] * 100, 2)) + '%'
            msg += f'{ticker}    {open_close}    {percent_change}'
        embed = discord.Embed(title=f'{market} Top {show} Losers ({of})', description=msg, color=STOCKS_RED)
        if m is None: run_coroutine(ctx.send(embed=embed))
        else: run_coroutine(m.edit(content='', embed=embed))
    bot.loop.run_in_executor(None, _losers)


@bot.command(aliases=['top_movers', 'gainers&losers', 'gainers_and_losers', 'gainers_&_losers'])
async def movers(ctx: Context, market='ALL', of='day', show=5):
    # TODO: hyperlinks and better formatting and optimize multiple calls
    def _movers():
        nonlocal market
        market = market.upper()
        eta = MOVERS_ETAS.get(market, '?')
        m = run_coroutine(ctx.send(f'Calculating top movers for {market} (ETA. {eta})'))
        sorted_info = get_latest_sorted_info(of, market)
        run_coroutine(m.delete())
        run_coroutine(ctx.invoke(bot.get_command('gainers'), market, of, show, sorted_info))
        run_coroutine(ctx.invoke(bot.get_command('losers'), market, of, show, sorted_info))
    bot.loop.run_in_executor(None, _movers)


@bot.command()
async def futures(ctx):
    def _futures():
        m = run_coroutine(ctx.send('Getting futures data'))
        futures_data = index_futures()
        important_futures = ['S&P 500', 'DOW JONES 30', 'NASDAQ', 'RUSSELL 2000']
        return_msg = ''
        for future in important_futures:
            data = futures_data[future]
            price = data['price']
            change = data['change']
            percent_change = data['percent_change']
            return_msg += f'\n**{future}**: *price* = {price}; *change* = {change} ({percent_change})'
        run_coroutine(m.edit(content=return_msg))
    bot.loop.run_in_executor(None, _futures)


@bot.command(aliases=['tp'])
async def target_price(ctx, ticker: str):
    def _get_target_price():
        nonlocal ticker
        ticker = ticker.replace('$', '').upper()
        m = run_coroutine(ctx.send(f'Getting target prices for {ticker}'))
        target_prices = get_target_price(ticker)
        price = target_prices[3]
        eps_ttm = target_prices[4]
        if price > target_prices[0]: color = STOCKS_RED
        elif price < target_prices[0]: color = STOCKS_GREEN
        else: color = STOCKS_YELLOW
        title = f'{ticker} Target Prices'
        embed = discord.Embed(title=title, color=color)
        embed.add_field(name='Avg', value=target_prices[0])
        embed.add_field(name='Low', value=target_prices[1])
        embed.add_field(name='High', value=target_prices[2])
        embed.add_field(name='Price', value=price)
        embed.add_field(name='EPS (TTM)', value=eps_ttm)
        run_coroutine(m.edit(content='', embed=embed))
    bot.loop.run_in_executor(None, _get_target_price)

# END of Investing

print('Backing up database')
backup_db()
print('Starting bot')
bot.run(os.environ['DISCORD'])
# useful: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html
