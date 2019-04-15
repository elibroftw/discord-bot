import asyncio
# noinspection PyUnresolvedReferences
import time
from contextlib import suppress
from copy import deepcopy
from datetime import datetime

import discord
from discord import FFmpegPCMAudio, PCMVolumeTransformer
from discord.ext import commands
import git
import logging
import os
# noinspection PyUnresolvedReferences
from pprint import pprint
from subprocess import run


import tictactoe
from helpers import youtube_download, youtube_search, get_related_video, get_video_id, get_youtube_title, \
    load_opus_lib, update_net_worth, check_net_worth, Song, get_video_duration, format_time_ffmpeg

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

players_in_game = []
tic_tac_toe_data = {}
ttt_games = {}
ffmpeg_path = 'ffmpeg/bin/ffmpeg'
data_dict = {'downloads': {}}

with open('help.txt') as f:
    help_message = f.read()


def create_embed(title, description='', color=discord.Color.blue()):
    return discord.Embed(title=title, description=description, color=color)


@bot.event
async def on_ready():
    # todo: send me a message and then delete it
    for guild in bot.guilds:
        data_dict[guild] = {'music': [], 'done': [], 'is_stopped': False, 'volume': 1, 'repeat': False,
                            'repeat_all': False, 'auto_play': False, 'downloads': {}, 'invite': None, 'output': True}
        # output means Now playing messages
    print('Logged In')
    await bot.change_presence(activity=discord.Game('Prison Break (!)'))


@bot.event
async def on_member_join(member):
    guild = member.guild
    msg = f'Welcome inmate {member.mention} to {guild}!\n'
    msg += 'Use !help for my functions'
    await member.send_message(member, msg)


@bot.event
async def on_message(message):
    author: discord.User = message.author
    if author != bot.user:
        update_net_worth(str(author))
    if message.content.startswith('!RUN'):
        await message.channel.send('I GOT EXTRADITED! :(')
    elif message.content.lower().startswith('!run'):
        await message.channel.send('N o t  h y p e  e n o u g h')
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
async def test():
    print(bot.commands)


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
    if str(ctx.author) == 'eli#4591':
        # voice_client: discord.VoiceClient = discord.utils.get(bot.voice_clients, guild=ctx.guild)
        for voice_client in bot.voice_clients:
            if voice_client: await voice_client.disconnect()
        await bot.logout()
        quit()
        quit()


@bot.command()
async def restart(ctx):
    if str(ctx.author) == 'eli#4591':
        # voice_client: discord.VoiceClient = discord.utils.get(bot.voice_clients, guild=ctx.guild)
        print('Restarting')
        await bot.change_presence(activity=discord.Game('Restarting...'))
        for voice_client in bot.voice_clients:
            if voice_client:
                # if voice_client.is_playing():
                #     no_after_play(data_dict[ctx.guild], voice_client)
                await voice_client.disconnect()
                # await voice_client.connect()
        g = git.cmd.Git(os.getcwd())
        g.pull()
        run('python bot.py')
        quit()


# @bot.command(, aliases=['gettweet', 'get_tweet'])
# async def twitter(ctx):
#     # TODO: add --integer to define how many statuses, use regex
#     # TODO: add a clamp (3 for this 10 for the next) so nobody can abuse the system
#     msg = discord_get_tweet_from(ctx.message.content[ctx.message.content.index(' ') + 1:])  # TODO: except ValueError
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
    with suppress(AttributeError):
        channel: discord.TextChannel = ctx.channel
        if ctx.message.author.permissions_in(ctx.channel).manage_messages:
            # await ctx.send('Clearing messages...')
            await bot.change_presence(activity=discord.Game('Clearing messages...'))
            if number > 99:
                number = 99
            messages = []
            async for m in channel.history(limit=number + 1):
                date = m.created_at
                # delete if older than 14 else add onto msg list
                if (datetime.now() - date).days > 14: await m.delete()
                else: messages.append(m)
            await channel.delete_messages(messages)
            print(f'{ctx.message.author} cleared {number + 1} messages')
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


@bot.command()
async def ttt(ctx):
    global players_in_game, tic_tac_toe_data
    author: discord.User = ctx.message.author
    if ttt_games.get(author, False):
        await author.send('You are already in a game. To end a game enter !end')
    else:
        msg = 'You have started a Tic-Tac-Toe game\nThe game will end after 2 minutes of' \
              'inactivity or if you enter !end\nWould you like to go first? [Y/n]'
        await author.send(msg)
        # TODO: do I really need username in dict??
        # TODO: replace game_over with in_game
        tic_tac_toe_data[author] = {'username': str(author), 'comp_moves': [], 'user_moves': [], 'danger': None,
                                    'danger2': None, 'game_over': False, 'round': 0}
        user_msg, game_channel = None, author.dm_channel
        # TODO: Change the parameter name??

        def check_yn(waited_msg):
            correct_prereqs = waited_msg.channel == game_channel and author == waited_msg.author
            waited_msg = waited_msg.content.lower()
            bool_value = waited_msg in ('y', 'yes', 'no', 'n') or 'end' in waited_msg
            return bool_value and correct_prereqs

        def check_digit(waited_msg):
            correct_prereqs = waited_msg.channel == game_channel and ctx.message.author == waited_msg.author
            waited_msg = waited_msg.content
            return (waited_msg.isdigit() or 'end' in waited_msg.lower()) and correct_prereqs

        while user_msg is None and not tic_tac_toe_data[author]['game_over']:
            try:
                user_msg = await bot.wait_for('message', timeout=120, check=check_yn)
                if user_msg:
                    user_msg = user_msg.content.lower()
                    if 'end' in user_msg:
                        tic_tac_toe_data[author]['game_over'] = True
                        await author.send('You have ended your tic-tac-toe game')
                    else:
                        tic_tac_toe_data[author]['round'] = 1
                        temp_msg = tictactoe.greeting(tic_tac_toe_data[author], user_msg)  # msg is y or n
                        await author.send(temp_msg)
            except asyncio.TimeoutError:
                tic_tac_toe_data[author]['game_over'] = True
        # TODO: combine while statements
        while not tic_tac_toe_data[author]['game_over']:
            try:
                user_msg = await bot.wait_for('message', timeout=120, check=check_digit)
                if user_msg is not None:
                    if 'end' in user_msg.content.lower():
                        tic_tac_toe_data[author]['game_over'] = True
                        await author.send('You have ended your tic-tac-toe game')
                    else:
                        player_move = int(user_msg.content)
                        temp_msg, d = tictactoe.valid_move(player_move, tic_tac_toe_data[author])
                        tic_tac_toe_data[author] = d
                        if not temp_msg:
                            await author.send('That was an invalid move')
                        else:
                            temp_msg += '\n'
                            tic_tac_toe_data[author]['user_moves'].append(player_move)
                            tempt = tictactoe.tic_tac_toe_move(tic_tac_toe_data[author])[0]
                            if tic_tac_toe_data[author]['game_over']:
                                tic_tac_toe_data[author]['game_over'] = True
                                if tic_tac_toe_data[author]['round'] == 5:
                                    await author.send(f'Your Move{temp_msg + tempt}')
                                else:
                                    await author.send(f'Your Move{temp_msg}My Move{tempt}')
                            else:  # TODO: rich embed???
                                await author.send(f'Your Move{temp_msg}My Move{tempt}\nEnter your move (#)')
                            tic_tac_toe_data[author]['round'] += 1
            except asyncio.TimeoutError:
                tic_tac_toe_data[author]['game_over'] = True


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
    if not author.voice:
        return await discord.utils.get(guild.voice_channels, name='music').connect()
    else:
        voice_client: discord.VoiceClient = guild.voice_client
        channel: discord.VoiceChannel = author.voice.channel
        if not voice_client:
            vc = await channel.connect()
            return vc
        elif voice_client.channel != channel:
            # TODO: add a role lock?
            return await voice_client.move_to(channel)
        return voice_client


def run_coro(coro: asyncio.coroutine):
    # e.g. coro = bot.change_presence(activity=discord.Game('Prison Break (!)'))
    fut = asyncio.run_coroutine_threadsafe(coro, bot.loop)
    return fut.result()


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
                if data_dict[ctx.guild]['music'][0].get_video_id() == video_id:
                    bot.loop.create_task(play_file(ctx))
                    bot.loop.create_task(m.delete())
                    return
                elif play_next: msg_content = f'Added `{title}` to next up'
                else: msg_content = f'Added `{title}` to the playing queue'
                bot.loop.create_task(m.edit(content=msg_content))

            result: asyncio.Future = bot.loop.run_in_executor(None, youtube_download, video_id)
            result.add_done_callback(callback)
            data_dict['downloads'][video_id] = (result, m)
        else:
            youtube_download(video_id)
    return m


async def download_related_video(ctx, auto_play_setting):
    if auto_play_setting:
        guild = ctx.guild
        guild_data = data_dict[guild]
        mq = guild_data['music']
        if len(mq) == 1:
            song = mq[0]
            related_title, related_video_id = get_related_video(song.get_video_id(),  guild_data['done'])[1:]
            mq.append(Song(related_title, related_video_id))
            related_m = await download_if_not_exists(ctx, related_title, related_video_id, in_background=True)
            related_msg_content = f'Added `{related_title}` to the playing queue'
            if not related_m: await ctx.send(related_msg_content)


async def in_guild(ctx):
    if ctx.guild:
        return True
    return False


async def has_vc(ctx):
    if ctx.guild and ctx.guild.voice_client:
        return True
    return False


@bot.command(aliases=['mute'])
@commands.check(in_guild)
async def quiet(ctx):
    guild_data = data_dict[ctx.guild]
    guild_data['output'] = not guild_data['output']


async def play_file(ctx, start_at=0):
    """Plays first (index=0) song in the music queue"""

    guild: discord.Guild = ctx.guild
    voice_client: discord.VoiceClient = guild.voice_client
    # noinspection PyTypeChecker
    guild_data = data_dict[guild]
    upcoming_tracks = guild_data['music']
    play_history = guild_data['done']
    if not upcoming_tracks and guild_data['repeat_all']:
        guild_data['music'] = play_history[::-1]
        play_history.clear()
    elif not upcoming_tracks and guild_data['repeat']:
        upcoming_tracks.append(play_history.pop(0))

    def after_play(error):
        # noinspection PyTypeChecker
        if not error and not data_dict[guild]['is_stopped']:
            mq = guild_data['music']
            dq = guild_data['done']
            # pylint: disable=assignment-from-no-return
            if len(voice_client.channel.members) > 1:
                # mq = guild_data['music']
                # ph = guild_data['done']
                if not guild_data['repeat']:
                    last_song = mq.pop(0)
                    dq.insert(0, last_song)
                else:
                    last_song = mq[0]

                if guild_data['repeat_all']:
                    if not mq and dq:
                        mq = guild_data['music'] = dq[::-1]
                        dq.clear()

                setting = guild_data['auto_play']
                if mq or setting:
                    if setting and not mq:
                        next_title, next_video_id = get_related_video(last_song.get_video_id(), dq)[1:]
                        next_m = run_coro(download_if_not_exists(ctx, next_title, next_video_id, in_background=False))
                        mq.append(Song(next_title, next_video_id))
                    else:  # if mq, check if the song is downloading # NOTE: was here last
                        next_result, next_m = data_dict['downloads'].get(video_id, (None, None))
                        if next_result:
                            run_coro(next_result)
                            data_dict['downloads'].pop(next_result)
                        else:
                            next_m = run_coro(download_if_not_exists(ctx, title, video_id, in_background=False))
                    next_song: Song = mq[0]
                    next_title = next_song.title
                    next_music_filepath = f'Music/{next_song.get_video_id()}.mp3'
                    next_audio_source = FFmpegPCMAudio(next_music_filepath, executable=ffmpeg_path,
                                                       before_options="-nostdin",
                                                       options="-vn -b:a 128k")
                    next_audio_source = PCMVolumeTransformer(next_audio_source)
                    next_audio_source.volume = guild_data['volume']
                    voice_client.play(next_audio_source, after=after_play)
                    next_song.start(0)
                    run_coro(bot.change_presence(activity=discord.Game(next_title)))
                    next_time_stamp = next_song.get_time_stamp(True)
                    if guild_data['output']:
                        next_msg_content = f'Now playing `{next_title}` {next_time_stamp}'
                        if not guild_data['repeat'] and not next_m: run_coro(ctx.send(next_msg_content))
                        if next_m: run_coro(next_m.edit(content=next_msg_content))
                    run_coro(download_related_video(ctx, setting))
            else:
                run_coro(bot.change_presence(activity=discord.Game('Prison Break (!)')))
                if len(voice_client.channel.members) == 1: run_coro(voice_client.disconnect())

    if voice_client and upcoming_tracks:
        song = upcoming_tracks[0]
        title = song.title
        video_id = song.get_video_id()
        music_filepath = f'Music/{video_id}.mp3'
        result, m = data_dict['downloads'].get(video_id, (None, None))
        if result:
            await result
            return
        else:
            m = await download_if_not_exists(ctx, title, video_id, in_background=False)
        guild_data['is_stopped'] = False
        # -af silenceremove=start_periods=1:stop_periods=1:detection=peak
        start_at = max(0, start_at)
        start_at = min(song.get_length(), start_at)
        audio_source = FFmpegPCMAudio(music_filepath, executable=ffmpeg_path,
                                      before_options=f'-nostdin -ss {format_time_ffmpeg(start_at)}',
                                      options='-vn -b:a 128k')
        audio_source = PCMVolumeTransformer(audio_source)
        audio_source.volume = guild_data['volume']
        voice_client.play(audio_source, after=after_play)
        song.start(start_at)
        time_stamp = song.get_time_stamp(True)
        if guild_data['output']:
            msg_content = f'Now playing `{title}` {time_stamp}'
            if m:
                await m.edit(content=msg_content)
            else:
                temp_mq = deepcopy(upcoming_tracks)
                temp_dq = deepcopy(play_history)
                await ctx.send(msg_content)
                if temp_mq != upcoming_tracks:
                    guild_data['music'] = deepcopy(temp_mq)
                    guild_data['done'] = deepcopy(temp_dq)
        await bot.change_presence(activity=discord.Game(title))
        await download_related_video(ctx, guild_data['auto_play'])


@bot.command(aliases=['paly', 'p', 'P', 'pap', 'pn', 'play_next', 'playnext'])
@commands.check(in_guild)
async def play(ctx):
    # TODO: add repeat play option
    # TODO: time remaining command + song length command
    # TODO: download option, rename file, add metadata and album art and then send it to user in dm.
    #   Download video as mp3 if the file does not exist.
    # TODO: use a db to determine which files get constantly queued (db should be title: video_id, times_queued)
    guild = ctx.guild
    voice_client: discord.VoiceClient = guild.voice_client
    ctx_msg_content = ctx.message.content
    play_next = any([cmd in ctx_msg_content for cmd in ('pn', 'play_next', 'playnext')])
    guild_data = data_dict[guild]
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
        song = data_dict[ctx.guild]['music'][0]
        await bot.change_presence(activity=discord.Game('Prison Break (!)'))
        if voice_client.is_paused():
            voice_client.resume()
            song.start()
        else:
            voice_client.pause()
            song.pause()


@bot.command(aliases=['ap', 'autoplay'])
@commands.check(in_guild)
async def auto_play(ctx, setting: bool = None):
    """Turns auto play on or off"""
    guild = ctx.guild
    guild_data = data_dict[guild]
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
    guild_data = data_dict[guild]
    if setting is None: setting = not guild_data['repeat']
    data_dict[guild]['repeat'] = setting
    if setting:
        await ctx.send('Repeating song set to True')
        if voice_client and not voice_client.is_playing() and not voice_client.is_paused():
            mq = data_dict[guild]['music']
            dq = data_dict[guild]['done']
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
    guild_data = data_dict[guild]
    if setting is None: setting = not data_dict[guild]['repeat_all']
    data_dict[guild]['repeat_all'] = setting

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


@bot.command(aliases=['next', 'n', 'sk'])
@commands.check(in_guild)
async def skip(ctx, times=1):
    # TODO: make it a partial democracy but mods and admins can bypass it
    guild = ctx.guild
    voice_client: discord.VoiceClient = guild.voice_client
    if voice_client:
        guild_data = data_dict[guild]
        mq = guild_data['music']
        dq = guild_data['done']
        if mq:
            no_after_play(guild_data, voice_client)
            for _ in range(min(times, len(mq))): dq.insert(0, mq.pop(0))
            await play_file(ctx)


@bot.command(aliases=['back', 'b', 'prev', 'go_back', 'gb'])
@commands.check(in_guild)
async def previous(ctx, times=1):
    # TODO: make it a partial democracy but mods and admins can bypass it
    # note: there is a bug when times > 1
    guild = ctx.guild
    voice_client: discord.VoiceClient = guild.voice_client
    if voice_client:
        guild_data = data_dict[guild]
        mq = guild_data['music']
        dq = guild_data['done']
        if dq:
            no_after_play(guild_data, voice_client)
            for _ in range(min(times, len(dq))): mq.insert(0, dq.pop(0))
            await play_file(ctx)


@bot.command()
@commands.check(in_guild)
async def remove(ctx, position: int = 0):
    guild = ctx.guild
    guild_data = data_dict[guild]
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


@bot.command(aliases=['cq', 'clearque', 'clear_q', 'clear_que', 'clearq', 'clearqueue', 'queue_clear', 'queueclear'])
@commands.check(in_guild)
async def clear_queue(ctx):
    guild = ctx.guild
    moderator = discord.utils.get(guild.roles, name='Moderator')
    if ctx.author.top_role >= moderator:
        voice_client: discord.VoiceClient = guild.voice_client
        mq = data_dict[guild]['music']
        if voice_client.is_playing() or voice_client.is_paused():
            data_dict[guild]['music'] = mq[0:1]
        else: mq.clear()
        await ctx.send('Cleared music queue')


@bot.command(aliases=['music_queue', 'mq', 'nu', 'queue', 'que', 'q'])
@commands.check(in_guild)
async def next_up(ctx):
    guild = ctx.guild
    guild_data = data_dict[guild]
    mq = guild_data['music']
    if mq:
        title = f'MUSIC QUEUE [{len(mq)} Songs]'
        if guild_data['auto_play']: title += ' | AUTO PLAY ENABLED'
        if guild_data['repeat_all']: title += ' | REPEAT ALL ENABLED'
        if guild_data['repeat']: title += ' | REPEAT SONG ENABLED}'
        msg = ''
        for i, song in enumerate(mq):
            if i == 10:
                msg += '\n...'
                break
            if i > 0: msg += f'\n`{i}.` {song.title} `[{song.get_length(True)}]`'
            else: msg += f'\n`Playing` {song.title} `{song.get_time_stamp(True)}`'
        embed = create_embed(title, description=msg)
        await ctx.send(embed=embed)
    else: await ctx.send(embed=create_embed('MUSIC QUEUE IS EMPTY'))


@bot.command(name='recently_played', aliases=['done_queue', 'dq', 'rp'])
@commands.check(in_guild)
async def _recently_played(ctx):
    # TODO: make a play_history list that never gets modified and takes in a parameter page_number
    guild = ctx.guild
    dq = data_dict[guild]['done']
    if dq:
        title = f'RECENTLY PLAYED [{len(dq)} Songs]'
        msg = ''
        for i, song in enumerate(dq):
            if i == 10:
                msg += '\n...'
                break
            msg += f'\n`-{i + 1}` {song.title} `{song.get_length(True)}`'
        embed = create_embed(title, description=msg)
        await ctx.send(embed=embed)
    else: await ctx.send('RECENTLY PLAYED IS EMPTY, were you looking for !play_history?')


@bot.command()
@commands.check(in_guild)
async def skip_to(ctx, seconds: int):
    guild = ctx.guild
    voice_client = guild.voice_client
    if voice_client.is_playing() or voice_client.is_paused():
        no_after_play(data_dict[guild], voice_client)
        await play_file(ctx, seconds)


@bot.command(aliases=['ff', 'fwd'])
@commands.check(in_guild)
async def fast_forward(ctx, seconds: int = 5):  # TODO
    # raise NotImplementedError
    guild = ctx.guild
    voice_client = guild.voice_client
    if voice_client.is_playing() or voice_client.is_paused():
        guild_data = data_dict[guild]
        no_after_play(guild_data, voice_client)
        song = guild_data['music'][0]
        await play_file(ctx, song.get_time_stamp() + seconds)


@bot.command(aliases=['rwd', 'rw'])
@commands.check(in_guild)
async def rewind(ctx, seconds: int = 5):
    guild = ctx.guild
    voice_client = guild.voice_client
    if voice_client.is_playing() or voice_client.is_paused():
        guild_data = data_dict[guild]
        no_after_play(guild_data, voice_client)
        song = guild_data['music'][0]
        await play_file(ctx, song.get_time_stamp() - seconds)


@bot.command(aliases=['np', 'currently_playing', 'cp'])
@commands.check(in_guild)
async def now_playing(ctx, send_link=False):
    guild = ctx.guild
    mq = data_dict[guild]['music']
    song = mq[0]
    await ctx.send(f'`{song.title}` {song.get_time_stamp(True)}')
    if send_link:
        await ctx.send(f'https://www.youtube.com/watch?v={song.get_video_id()}')


@bot.command(aliases=['desummon', 'disconnect', 'unsummon', 'dismiss', 'd'])
@commands.check(in_guild)
async def leave(ctx):
    # clear music queue
    guild = ctx.guild
    voice_client: discord.VoiceClient = guild.voice_client
    if voice_client:
        await voice_client.disconnect()
        guild_data = data_dict[guild]
        guild_data['music'].clear()
        guild_data['auto_play'] = False
        await ctx.send('Stopped playing music, music que has been emptied')


@bot.command(aliases=['s', 'end'])
@commands.check(in_guild)
async def stop(ctx):
    guild = ctx.guild
    voice_client: discord.VoiceClient = guild.voice_client
    if voice_client and voice_client.is_playing():
        guild_data = data_dict[guild]
        guild_data['is_stopped'] = True
        guild_data['music'][0].stop()
        voice_client.stop()


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
                amount = max(0, amount)
                amount = min(1, amount)
                vc.source.volume = amount
                data_dict[guild]['volume'] = amount
            except ValueError: await ctx.send('Invalid argument', delete_after=5)
        else: await ctx.send(f'{vc.source.volume * 100}%')


@bot.command()
async def source(ctx):
    await ctx.send('https://github.com/elibroftw/discord-bot')


@bot.command()
async def ban(ctx):
    # TODO: add are you sure
    if ctx.author.guild_permissions.ban_members:
        args = ctx.message.content.split(' ')
        if len(args) > 1:
            name = ' '.join(args[1:])
            user = discord.utils.get(ctx.guild.members, nick=name)
            if not user:
                user = discord.utils.get(ctx.guild.members, name=name)
            await ctx.guild.ban(user)


@bot.command()
async def about(ctx):
    ctx.author.send(f'Hi there. Thank you for wanting to know more about me. I was made by Elijah Lopez.\n'
                    'For more information visit https://github.com/elibroftw/discord-bot.\n'
                    f'Join my server at https://discord.gg/{invitation_code})')


bot.run(os.environ['DISCORD'])

# TODO: 'shop', 'math', 'ban', 'remove_role', 'delete_role'
