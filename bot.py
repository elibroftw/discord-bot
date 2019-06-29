import asyncio
from copy import deepcopy
from contextlib import suppress
from datetime import datetime
import discord
from discord import FFmpegPCMAudio, PCMVolumeTransformer
from discord.ext import commands
import git
import json
import logging
import os
from subprocess import Popen
from pymongo import MongoClient
import tictactoe
from helpers import *

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)
bot = commands.Bot(command_prefix='!')
bot.remove_command('help')
bot.command()
load_opus_lib()

invitation_code = os.environ['INVITATION_CODE']
my_server_id = os.environ['SERVER_ID']
my_user_id = int(os.environ['MY_USER_ID'])

db_client = MongoClient('localhost', 27017)
db = db_client.discord_bot

players_in_game = []
tic_tac_toe_data = {}
ffmpeg_path = 'ffmpeg/bin/ffmpeg'
data_dict = {'downloads': {}}

if not os.path.exists('Music'):
    os.mkdir('Music')

with open('help.txt') as h:
    help_message = h.read()


def create_embed(title, description='', color=discord.Color.blue()):
    return discord.Embed(title=title, description=description, color=color)


def run_coro(coro: asyncio.coroutine):
    # e.g. coro = bot.change_presence(activity=discord.Game('Prison Break (!)'))
    fut = asyncio.run_coroutine_threadsafe(coro, bot.loop)
    return fut.result()


async def in_guild(ctx):
    if ctx.guild:
        return True
    return False


async def has_vc(ctx):
    if ctx.guild and ctx.guild.voice_client:
        return True
    return False


@bot.event
async def on_ready():
    print('Logged In')
    await bot.change_presence(activity=discord.Game('Prison Break (!)'))
    save = {'data_dict': {}}
    with suppress(FileNotFoundError):
        if os.path.exists('save.json'):
            with open('save.json') as f:
                save = json.load(f)
        os.remove('save.json')
    for guild_id, guild_data in save['data_dict'].items():
        # create a table for each guild_id
        channel_id = guild_data['voice_channel']
        if channel_id != 'False':
            voice_channel = bot.get_channel(channel_id)
            await voice_channel.connect()
        mq = guild_data['music'] = [Song(s['title'], s['video_id'], s['time_stamp']) for s in guild_data['music']]
        guild_data['done'] = [Song(s['title'], s['video_id'], s['time_stamp']) for s in guild_data['done']]
        # noinspection PyTypeChecker
        data_dict[int(guild_id)] = guild_data
        tc = bot.get_channel(guild_data['text_channel'])
        if channel_id != 'False' and mq and tc is not None and not guild_data['is_stopped']:
            m = await tc.send('Bot has been restarted, now resuming music', delete_after=2)
            ctx = await bot.get_context(m)
            await play_file(ctx, guild_data['music'][0].get_time_stamp())
    # https://discordpy.readthedocs.io/en/rewrite/ext/commands/api.html#discord.ext.commands.Bot.get_context
    for guild in bot.guilds:
        if guild.id not in data_dict:
            data_dict[guild.id] = {'music': [], 'done': [], 'is_stopped': False, 'volume': 0.2,
                                   'repeat': False, 'repeat_all': False, 'auto_play': False, 'skip_voters': [],
                                   'downloads': {}, 'invite': None, 'output': True, 'text_channel': None}


@bot.event
async def on_member_join(member):
    guild = member.guild
    msg = f'Welcome inmate {member.mention} to {guild}!\n'
    msg += 'Use !help for my functions'
    await member.send_message(member, msg)


@bot.event
async def on_message(message):
    author: discord.User = message.author
    if author != bot.user: update_net_worth(str(author))
    if message.content.startswith('!RUN'): await message.channel.send('I GOT EXTRADITED! :(')
    elif message.content.lower().startswith('!run'): await message.channel.send('N o t  h y p e  e n o u g h')
    else:
        with suppress(discord.ext.commands.errors.CommandNotFound): await bot.process_commands(message)


# noinspection PyUnusedLocal
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.errors.CommandNotFound): return
    if error == KeyboardInterrupt:
        await bot.logout()
        return
    raise error


@bot.command(name='help')
async def _help(ctx):
    # TODO: rich embed
    await ctx.author.send(help_message)


@bot.command()
async def hi(ctx):
    await ctx.send("Hey there" + " " + ctx.message.author.name + "!")


@bot.command()
async def test(ctx):
    print('test called')


@bot.command()
async def sleep(ctx):
    if ctx.message.author == 'eli#4591':
        try: secs = int(ctx.message.content[7:])
        except ValueError: secs = 5
        print(f'Sleeping for {secs} seconds')
        await asyncio.sleep(secs)
        await ctx.send('Done sleeping')


@bot.command(aliases=['bal'])
async def balance(ctx):
    await ctx.message.author.send(check_net_worth(str(ctx.message.author)))
    await ctx.message.delete()


@bot.command(aliases=['createrole'])
async def create_role(ctx):
    m = ctx.message
    if str(m.author.top_role) == 'Admin':
        role_name = m.content.split(' ')
        if len(role_name) > 1:
            role_name = ' '.join(role_name[1:])
            guild: discord.guild = ctx.guild
            await guild.create_role(guild, name=role_name)
            await ctx.send(f'Role {role_name} created')
            print(f'{m.author} created role {role_name}')


@bot.command()
async def add_role(ctx):
    m = ctx.message
    if str(m.author.top_role) == 'Admin':
        mark = m.content.index(' ')
        guild = ctx.guild
        role_name = m.content.split(' ')
        if len(role_name) > 1:
            role_name = ' '.join(role_name[1:])
            role = discord.utils.get(guild.roles, name=role_name)
            member = ctx.message.content[12:mark - 1]
            member = guild.get_member(member)
            await guild.add_roles(member, role)
            print(f'{ctx.message.author} gave {member} role {role_name}')


# @bot.command()
# async def delete_role(ctx):  # TODO
#     raise NotImplementedError


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


@bot.command(aliases=['yt'])
async def youtube(ctx):
    try:
        url = youtube_search(' '.join(ctx.message.content.split(' ')[1:]))
    except IndexError:
        url = 'No Video Found'
    await ctx.send(url)


@bot.command(name='exit', aliases=['quit'])
async def _exit(ctx):
    if ctx.author.id == my_user_id:
        await bot.change_presence(activity=discord.Game('Exiting...'))
        save_to_file()
        for voice_client in bot.voice_clients:
            if voice_client.is_playing() or voice_client.is_paused():
                no_after_play(data_dict[ctx.guild.id], voice_client)
            await voice_client.disconnect()
        await bot.logout()


def save_to_file():
    save = {'data_dict': {}}
    for guild in bot.guilds:
        voice_client = guild.voice_client
        guild_data = deepcopy(data_dict[guild.id])
        if voice_client: guild_data['voice_channel'] = voice_client.channel.id
        else: guild_data['voice_channel'] = 'False'
        mq = guild_data['music']
        guild_data['music'] = [s.to_dict() for s in mq]
        dq = guild_data['done']
        guild_data['done'] = [s.to_dict() for s in dq]
        # # guild_data['next_up'] = [s.to_dict() for s in next_up_queue]
        save['data_dict'][guild.id] = guild_data
    try:
        with open('save.json', 'w') as fp:
            json.dump(save, fp, indent=4)
    except Exception as e:
        print('save.json error', e)


@bot.command()
async def save():
    save_to_file()


@bot.command()
async def restart(ctx):
    if ctx.author.id == my_user_id:
        print('Restarting')
        await bot.change_presence(activity=discord.Game('Restarting...'))
        save_to_file()
        for guild in bot.guilds:
            voice_client = guild.voice_client
            if voice_client:
                no_after_play(data_dict[guild.id], voice_client)
                await voice_client.disconnect()
            # # guild_data['next_up'] = [s.to_dict() for s in next_up_queue]
        g = git.cmd.Git(os.getcwd())
        g.pull()
        Popen('python bot.py')
        await bot.logout()


# @bot.command(, aliases=['gettweet', 'get_tweet'])
# async def twitter(ctx, statuses=1):
#     msg = discord_get_tweet_from(ctx.message.content[ctx.message.content.index(' ') + 1:])
#     await ctx.send(msg)
#
#
# @bot.command(, aliases=['searchuser' 'search_user'])
# async def search_twitter_user(ctx):
#     text = ctx.message.content[ctx.message.content.index(' ') + 1:]  #  except ValueError
#     bot_message = discord_search_twitter_user(text)
#     await ctx.send(bot_message)
# search_users()


@bot.command()
async def thank(ctx):
    await ctx.send(f"You're welcome {ctx.author.mention}")


@commands.has_permissions(manage_messages=True)
@bot.command()
async def clear(ctx, number: int = 1):
    await ctx.message.delete()
    with suppress(AttributeError):
        channel: discord.TextChannel = ctx.channel
        if ctx.message.author.permissions_in(ctx.channel).manage_messages:
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


@bot.command(name='eval')
async def _eval(ctx):
    if str(ctx.author) == 'eli#4591':
        await ctx.send(str(eval(ctx.message.content[6:])))
        print(f'{ctx.message.author} used eval')


@bot.command(aliases=['invite', 'invitecode', 'invite_link', 'invitelink'])
async def invite_code(ctx):
    # await ctx.send(discord.Invite(channel=ctx.message.channel, code=invitation_code).url)
    if ctx.guild.id == my_server_id:
        await ctx.send(f'https://discord.gg/{invitation_code}')
    else:
        with suppress(IndexError):
            await ctx.send(ctx.guild.invites()[0].url)


@bot.command()
async def games(ctx):
    await ctx.send('We have: Tic-Tac-Toe (!ttt) and Shift (!shift)')


@bot.command(aliases=['tic_tac_toe'])
async def ttt(ctx):
    # TODO: add different difficulties
    global players_in_game, tic_tac_toe_data
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
                            else:  # TODO: rich embed???
                                await author.send(f'Your Move{temp_msg}My Move{tempt}\nEnter your move (#)')
                            author_data['round'] += 1
            except asyncio.TimeoutError:
                author_data['in_game'] = False


@bot.command()
async def shift(ctx):
    await ctx.send('https://elibroftw.itch.io/shift')


@bot.command(aliases=['create_date', 'createdat', 'createdate'])
async def created_at(ctx):
    args = ctx.message.content.split(' ')
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


@bot.command()
@commands.check(in_guild)
async def dl_songs(ctx, playlist_link):  # TODO
    if ctx.author.id == my_user_id:
        pass
    # download songs in playlist in background


async def download_if_not_exists(ctx, title, video_id, in_background=False, play_next=False):
    """
    Checks if file corresponding to title and video_id exists
    If it doesn't exist, download it
    returns None if it exists, or discord.Message object of the downloading title if it doesn't
    """

    music_filepath = f'Music/{video_id}.mp3'
    m = None
    if not os.path.exists(music_filepath) and video_id not in data_dict['downloads']:
        m = await ctx.channel.send(f'Downloading `{title}`')

        if in_background:
            def callback(_):
                data_dict['downloads'].pop(video_id)
                if data_dict[ctx.guild.id]['music'][0].get_video_id() == video_id:
                    bot.loop.create_task(play_file(ctx))
                    bot.loop.create_task(m.edit(content=f'Downloaded `{title}`', delete_after=5))
                    return
                elif play_next: msg_content = f'Added `{title}` to next up'
                else: msg_content = f'Added `{title}` to the playing queue'
                bot.loop.create_task(m.edit(content=msg_content))

            result: asyncio.Future = bot.loop.run_in_executor(None, youtube_download, video_id)
            result.add_done_callback(callback)
            data_dict['downloads'][video_id] = (result, m)
        else: youtube_download(video_id)
    return m


async def download_related_video(ctx, auto_play_setting):
    if auto_play_setting:
        guild = ctx.guild
        guild_data = data_dict[guild.id]
        mq = guild_data['music']
        if len(mq) == 1:
            song = mq[0]
            related_title, related_video_id = get_related_video(song.get_video_id(),  guild_data['done'])[1:]
            mq.append(Song(related_title, related_video_id))
            related_m = await download_if_not_exists(ctx, related_title, related_video_id, in_background=True)
            related_msg_content = f'Added `{related_title}` to the playing queue'
            if not related_m: await ctx.send(related_msg_content)


@bot.command(aliases=['mute'])
@commands.check(in_guild)
async def quiet(ctx):
    guild_data = data_dict[ctx.guild.id]
    guild_data['output'] = not guild_data['output']


def create_audio_source(guild_data, song, start_at=0.0):
    # -af silenceremove=start_periods=1:stop_periods=1:detection=peak
    music_filepath = f'Music/{song.get_video_id()}.mp3'
    start_at = max(0.0, start_at)
    start_at = min(song.get_length(), start_at)
    audio_source = FFmpegPCMAudio(music_filepath, executable=ffmpeg_path,
                                  before_options=f'-nostdin -ss {format_time_ffmpeg(start_at)}',
                                  options='-vn -b:a 128k')
    audio_source = PCMVolumeTransformer(audio_source)
    audio_source.volume = guild_data['volume']
    return audio_source


async def play_file(ctx, start_at=0):
    """Plays first (index=0) song in the music queue"""

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
                last_song = mq.pop(0)
                dq.insert(0, last_song)
            else: last_song = mq[0]
            last_song.stop()

            if guild_data['repeat_all'] and not mq and dq:
                mq = guild_data['music'] = dq[::-1]
                dq.clear()

            if len(vc.channel.members) > 1:
                setting = guild_data['auto_play']
                if mq or setting:
                    if setting and not mq:
                        next_title, next_video_id = get_related_video(last_song.get_video_id(), dq)[1:]
                        next_song = Song(next_title, next_video_id)
                        next_m = run_coro(download_if_not_exists(ctx, next_title, next_video_id, in_background=False))
                        mq.append(next_song)
                    else:  # if mq, check if the next song is downloading
                        next_song = mq[0]
                        next_video_id = next_song.get_video_id()
                        next_title = next_song.title
                        next_result, next_m = data_dict['downloads'].get(next_video_id, (None, None))
                        if next_result: run_coro(next_result)
                        else:
                            coro = download_if_not_exists(ctx, next_title, next_video_id, in_background=False)
                            next_m = run_coro(coro)
                    vc.play(create_audio_source(guild_data, next_song), after=after_play)
                    next_song.start(0)
                    next_time_stamp = next_song.get_time_stamp(True)
                    guild_data['is_stopped'] = False
                    if guild_data['output']:
                        next_msg_content = f'Now playing `{next_title}` {next_time_stamp}'
                        if not guild_data['repeat'] and not next_m: run_coro(ctx.send(next_msg_content))
                        if next_m: run_coro(next_m.edit(content=next_msg_content))
                    run_coro(bot.change_presence(activity=discord.Game(next_title)))
                    run_coro(download_related_video(ctx, setting))
            else:
                run_coro(bot.change_presence(activity=discord.Game('Prison Break (!)')))
                if len(vc.channel.members) == 1: run_coro(vc.disconnect())

    if vc and upcoming_tracks:
        song = upcoming_tracks[0]
        title = song.title
        video_id = song.get_video_id()
        result, m = data_dict['downloads'].get(video_id, (None, None))
        if result:
            await result
            return
        else: m = await download_if_not_exists(ctx, title, video_id, in_background=False)
        audio_source = create_audio_source(guild_data, song, start_at=start_at)

        vc.play(audio_source, after=after_play)
        song.start(start_at)
        time_stamp = song.get_time_stamp(True)
        guild_data['is_stopped'] = False
        guild_data['skip_voters'] = []
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
        await download_related_video(ctx, guild_data['auto_play'])


@bot.command(aliases=['dl'])
async def download(ctx):  # TODO: download url/query
    pass


@bot.command(aliases=['dls'])
@commands.check(in_guild)
async def download_song(ctx, index=0):
    guild = ctx.guild
    guild_data = data_dict[guild.id]

    if index >= 0: q = guild_data['music']
    else:
        q = guild_data['done']
        index = -index - 1
    with suppress(IndexError):
        song = q[index]
        filename = f'Music/{song.get_video_id()}.mp3'
        with open(filename, 'rb') as fp:
            file = discord.File(fp, filename=f'{file_friendly_title(song.title)}.mp3')
        content = 'Here is the mp3 file. You can rename the file and use my mp3 editor ' \
                  '<https://github.com/elibroftw/mp3-editor> to set the metadata and album art (needs spotify api) '
        await ctx.author.send(content=content, file=file)


@bot.command(aliases=['paly', 'p', 'P', 'pap', 'pn', 'play_next', 'playnext'])
@commands.check(in_guild)
async def play(ctx):
    # TODO: use a db to determine which files get constantly queued (db should be title: video_id, times_queued)
    #   if I make a public bot
    guild = ctx.guild
    voice_client: discord.VoiceClient = guild.voice_client
    ctx_msg_content = ctx.message.content
    play_next = any([cmd in ctx_msg_content for cmd in ('pn', 'play_next', 'playnext')])
    guild_data = data_dict[guild.id]

    mq = guild_data['music']
    if voice_client is None:
        voice_client = await bot.get_command('summon').callback(ctx)
    url_or_query = ctx.message.content.split()
    if len(url_or_query) > 1:
        url_or_query = ' '.join(url_or_query[1:])
        if url_or_query.startswith('https://y'):
            # TODO: playlist support
            url = url_or_query
            video_id = get_video_id(url)
            title = get_youtube_title(video_id)
            if get_video_duration(video_id) > 600:
                await ctx.send('That song is too long! (> 10 minutes)')
                return
        else:  # get url
            try: url, title, video_id = youtube_search(url_or_query, return_info=True, limit_duration=True)
            except (ValueError, IndexError):
                await ctx.send(f'No valid video found with query `{url_or_query}`')
                return
        song = Song(title, video_id)

        # adding to queue
        if mq and play_next: mq.insert(1, song)
        else: mq.append(song)

        # download the song if something is playing
        if voice_client.is_playing() or voice_client.is_paused():
            # download if your not going to play the file
            m = await download_if_not_exists(ctx, title, video_id, in_background=True, play_next=play_next)
            if play_next: m_content = f'Added `{title}` to next up'
            else: m_content = f'Added `{title}` to the playing queue'
            if not m: await ctx.send(m_content)
        else: await play_file(ctx)  # download if need to and then play the song

    elif (voice_client.is_playing() or voice_client.is_paused()) and not play_next:
        await bot.get_command('pause').callback(ctx)
    elif mq: await play_file(ctx)
    if ctx_msg_content.startswith('!pap'):
        await bot.get_command('auto_play').callback(ctx)


@bot.command(aliases=['resume'])
@commands.check(in_guild)
async def pause(ctx):
    voice_client: discord.VoiceClient = ctx.guild.voice_client
    if voice_client:
        song = data_dict[ctx.guild.id]['music'][0]
        if voice_client.is_paused():
            voice_client.resume()
            song.start()
            await bot.change_presence(activity=discord.Game(song.title))
        else:
            voice_client.pause()
            song.pause()
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
            song_id = dq[0].get_video_id()
            title, video_id, = get_related_video(song_id, dq)[1:]
            mq.append(Song(title, video_id))
            await play_file(ctx)  # takes care of the download
        await download_related_video(ctx, True)


@bot.command(name='repeat', aliases=['r'])
@commands.check(in_guild)
async def _repeat(ctx, setting: bool = None):
    guild = ctx.guild
    voice_client: discord.VoiceClient = guild.voice_client
    guild_data = data_dict[guild.id]
    if setting is None: setting = not guild_data['repeat']
    data_dict[guild.id]['repeat'] = setting
    if setting:
        await ctx.send('Repeating song set to True')
        if voice_client and not voice_client.is_playing() and not voice_client.is_paused():
            mq = data_dict[guild.id]['music']
            dq = data_dict[guild.id]['done']
            if not mq and dq:
                mq.append(dq.pop(0))
                await play_file(ctx)
    else:
        await ctx.send('Repeating song set to False')


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
        dq = guild_data['done']
        guild_data['repeat'] = False
        if mq:
            no_after_play(guild_data, voice_client)
            times = min(times, len(mq))
            # TODO: if times > len(mq) see if repeat_all is enabled
            # guild_data['done'] = reversed(mq[:times]) + dq
            # guild_data['music'] = mq[times:]
            for _ in range(times): dq.insert(0, mq.pop(0))
            await play_file(ctx)
        # if dq and guild_data['repeat_all']:
        #     pass


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
        if dq:
            no_after_play(guild_data, voice_client)
            times = min(times, len(dq))
            # TODO: if times > len(dq) see if repeat_all is enabled
            # data_dict['music'] = reversed(dq[:times]) + mq  # todo: test this
            # data_dict['done'] = dq[times:]
            for _ in range(times): mq.insert(0, dq.pop(0))
            await play_file(ctx)
        elif mq and guild_data['repeat_all']:
            dq += reversed(mq[:-times])
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
        if position < 0: dq.pop(-position - 1)
        elif position > 0: mq.pop(position)
        else:
            no_after_play(guild_data, voice_client)
            mq.pop(0)
            await play_file(ctx)


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
    try: song = from_queue[_from]
    except IndexError: return
    if _to > 0: to_queue: list = guild_data['music']
    else:
        to_queue = guild_data['done']
        _to = -_to - 1
    to_queue.insert(_to, song)
    if to_queue == from_queue and _to < _from: _from += 1
    from_queue.pop(_from)


@bot.command(aliases=['cq', 'clearque', 'clear_q', 'clear_que', 'clearq', 'clearqueue', 'queue_clear', 'queueclear'])
@commands.check(in_guild)
async def clear_queue(ctx):
    guild = ctx.guild
    moderator = discord.utils.get(guild.roles, name='Moderator')
    if ctx.author.top_role >= moderator:
        voice_client: discord.VoiceClient = guild.voice_client
        mq = data_dict[guild.id]['music']
        if voice_client.is_playing() or voice_client.is_paused():
            data_dict[guild.id]['music'] = mq[0:1]
        else: mq.clear()
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
        title = f'MUSIC QUEUE [{mq_length} Song(s) | Page {page}]'
        if guild_data['auto_play']: title += ' | AUTO PLAY ENABLED'
        if guild_data['repeat_all']: title += ' | REPEAT ALL ENABLED'
        if guild_data['repeat']: title += ' | REPEAT SONG ENABLED}'
        msg = ''
        i = 10 * (page - 1)
        for song in mq[i:10 * page]:
            if i == 0: msg += f'\n`Playing` {song.title} `{song.get_time_stamp(True)}`'
            else: msg += f'\n`{i}.` {song.title} `[{song.get_length(True)}]`'
            i += 1

        if mq_length > i:
            msg += '\n...'

        embed = create_embed(title, description=msg)
        await ctx.send(embed=embed)
    else: await ctx.send(embed=create_embed('MUSIC QUEUE IS EMPTY'))


@bot.command(name='recently_played', aliases=['done_queue', 'dq', 'rp'])
@commands.check(in_guild)
async def _recently_played(ctx, page=1):
    # TODO: add reaction emoticons
    guild = ctx.guild
    dq = data_dict[guild.id]['done']
    if dq:
        page = abs(page)
        title = f'RECENTLY PLAYED [{len(dq)} Song(s) | Page {page}]'
        msg = ''

        i = 10 * (page - 1)
        for song in dq[i:i + 10]:
            i += 1
            msg += f'\n`-{i}` {song.title} `{song.get_length(True)}`'

        if len(dq) > i:
            msg += '\n...'

        embed = create_embed(title, description=msg)
        await ctx.send(embed=embed)
    else: await ctx.send('RECENTLY PLAYED IS EMPTY, were you looking for !play_history?')


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
        start_at = guild_data['music'][0].get_time_stamp() + seconds
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
        no_after_play(guild_data, voice_client)
        await play_file(ctx, start_at)


@bot.command(aliases=['np', 'currently_playing', 'cp'])
@commands.check(in_guild)
async def now_playing(ctx):
    guild = ctx.guild
    mq = data_dict[guild.id]['music']
    song = mq[0]
    embed = discord.Embed(title=song.title, url=f'https://www.youtube.com/watch?v={song.get_video_id()}',
                          description=song.get_time_stamp(True), color=0x0080ff)
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
        await ctx.send('Stopped playing music, music queue has been emptied')


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
    await bot.get_command('summon').callback(ctx)
    voice_client: discord.VoiceClient = guild.voice_client
    await voice_client.disconnect()
    await bot.get_command('summon').callback(ctx)


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
                amount = round(amount, 4)
                vc.source.volume = amount
                data_dict[guild.id]['volume'] = amount
            except ValueError: await ctx.send('Invalid argument', delete_after=5)
        else: await ctx.send(f'{vc.source.volume * 100}%')



@bot.command(aliases=['sa'])
@commands.check(in_guild)
async def save_as(ctx):
    playlist_name = ' '.join(ctx.message.content.split()[1:])
    if playlist_name:
        author_id = ctx.author.id
        guild_id = ctx.guild.id
        posts = db.posts
        playlist = posts.find_one({'guild_id': guild_id, 'playlist_name': playlist_name})
        mq = data_dict[guild_id]['music']
        dq = data_dict[guild_id]['done']
        temp = dq[::-1] + mq
        song_ids = [(song.title, song.get_video_id()) for song in temp]
        post = {'guild_id': ctx.guild.id, 'playlist_name': playlist_name, 'creator_id': author_id, 'songs': song_ids}
        old_post = posts.find_one_and_update({'playlist_name': playlist_name, 'creator_id': author_id}, {'$set': post}, upsert=True)
        if old_post: await ctx.send(f'Succesfully updated playlist "{playlist_name}"')
        else: await ctx.send(f'Succesfully created playlist "{playlist_name}"!')


# TODO: test if invalid playlist id is given
@bot.command(aliases=['lp', 'load_pl', 'load', 'l'])
@commands.check(in_guild)
async def load_playlist(ctx):
    # TODO: maybe include search youtube playlist?
    # TODO: check duration length either here or in play_file?
    playlist_name = ' '.join(ctx.message.content.split()[1:])
    if playlist_name:
        songs = get_songs_from_playlist(playlist_name, ctx.guild.id, ctx.author.id)[0]
        if songs:
            data_dict[ctx.guild.id]['music'].extend(songs)
            await ctx.send('Songs added to queue!')
        else: await ctx.send('No playlist found with that name')


@bot.command(aliases=['vp'])
@commands.check(in_guild)
async def view_playlist(ctx):
    playlist_name = ' '.join(ctx.message.content.split()[1:])
    if playlist_name:
        songs, playlist_name = get_songs_from_playlist(playlist_name, ctx.guild.id, ctx.author.id)
        if songs:
            pl_length = len(songs)
            msg = ''
            for i, song in enumerate(songs[:10]):
                msg += f'\n`{i + 1}.` {song.title}'
            if pl_length > 10: msg += '\n...'
            embed = create_embed(f'PLAYLIST "{playlist_name}" | {pl_length} Song(s)', description=msg)
            await ctx.send(embed=embed)
        else: await ctx.send('No playlist found with that name')


@bot.command(aliases=['delete_pl', 'dp'])
@commands.check(in_guild)
async def delete_playlist(ctx):
    playlist_name = ' '.join(ctx.message.content.split()[1:])
    if playlist_name:
        posts = db.posts
        r = posts.delete_one({'playlist_name': playlist_name, 'creator_id': ctx.author.id})
        print(r)
        await ctx.send(f'Deleted your playlist "{playlist_name}"')


@bot.command()
@commands.check(in_guild)
async def ban(ctx):
    author = ctx.author
    args = ctx.message.content.split(' ')
    if author.guild_permissions.ban_members and len(args) > 1:
        name = ' '.join(args[1:])
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


@bot.command(aliases=['source'])
async def about(ctx):
    ctx.author.send(f'Hi there. Thank you for inquiring about me. I was made by Elijah Lopez.\n'
                    'For more information visit https://github.com/elibroftw/discord-bot.\n'
                    f'Join my server at https://discord.gg/{invitation_code})')




bot.run(os.environ['DISCORD'])

# TODO: 'shop', 'math', 'ban', 'remove_role', 'delete_role'
