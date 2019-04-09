import asyncio
# noinspection PyUnresolvedReferences
import time
from contextlib import suppress
from copy import deepcopy
from datetime import datetime

import discord
from discord import FFmpegPCMAudio, PCMVolumeTransformer
from discord.ext import commands
import os
# noinspection PyUnresolvedReferences
from pprint import pprint
from subprocess import run

import tictactoe
from helpers import youtube_download, youtube_search, get_related_video, get_video_id, get_video_title, load_opus_lib, \
    update_net_worth, check_net_worth, Song, get_video_duration

# TODO: make a website
bot = commands.Bot(command_prefix='!')
bot.command()

invitation_code = os.environ['INVITATION_CODE']
load_opus_lib()
ttt_round = 0
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
    for guild in bot.guilds:
        data_dict[guild] = {'music': [], 'done': [], 'is_stopped': False, 'volume': 1,
                            'repeat': False, 'repeat_all': False, 'auto_play': False, 'downloads': {}}
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
    elif message.content.lower().startswith('!help'):
        await author.send(help_message)
    else:
        await bot.process_commands(message)


@bot.command()
async def hi(ctx):
    await ctx.send("Hey there" + " " + ctx.message.author.name + "!")


@bot.command()
async def test():
    print(bot.commands)


@bot.command()
async def sleep(ctx):
    if ctx.message.author == 'eli#4591':
        try:
            secs = int(ctx.message.content[7:])
        except ValueError:
            secs = 5
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
    url = youtube_search(' '.join(ctx.message.content.split(' ')[1:]))
    await ctx.send(url)


@bot.command(name='exit', aliases=['quit'])
async def _exit(ctx):
    if str(ctx.author) == 'eli#4591':
        # voice_client: discord.VoiceClient = discord.utils.get(bot.voice_clients, guild=ctx.guild)
        for voice_client in bot.voice_clients:
            if voice_client: await voice_client.disconnect()
        quit()


@bot.command()
async def restart(ctx):
    if str(ctx.author) == 'eli#4591':
        # voice_client: discord.VoiceClient = discord.utils.get(bot.voice_clients, guild=ctx.guild)
        print('Restarting')
        for voice_client in bot.voice_clients:
            if voice_client:
                # if voice_client.is_playing():
                #     no_after_play(data_dict[ctx.guild], voice_client)
                await voice_client.disconnect()
                # await voice_client.connect()
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
#     text = ctx.message.content[ctx.message.content.index(' ') + 1:]  # TODO: except ValueError
#     bot_message = discord_search_twitter_user(text)
#     await ctx.send(bot_message)
# search_users()


@bot.command()
async def thank(ctx):
    await ctx.send(f"You're welcome {ctx.author.mention}")


@commands.has_permissions(manage_messages=True)
@bot.command()
async def clear(ctx):
    with suppress(AttributeError):
        channel: discord.TextChannel = ctx.channel
        if ctx.message.author.permissions_in(ctx.channel).manage_messages:
            # await ctx.send('Clearing messages...')
            await bot.change_presence(activity=discord.Game('Clearing messages...'))
            number = 3
            if ctx.message.content[7:].isnumeric():  # len(user_msg) > 7 and
                if int(ctx.message.content[7:]) > 98:
                    number = 100 - int(ctx.message.content[7:])
                number += int(ctx.message.content[7:]) - 1
            messages = []
            async for m in channel.history(limit=number):
                date = m.created_at
                # if older than 14: delete else add onto msg list
                if (datetime.now() - date).days > 14:
                    await m.delete()
                else:
                    messages.append(m)
            await channel.delete_messages(messages)
            print(f'{ctx.message.author} cleared {number - 2} message(s)')
        await bot.change_presence(activity=discord.Game('Prison Break (!)'))


@bot.command(name='eval')
async def _eval(ctx):
    if str(ctx.author) == 'eli#4591':
        await ctx.send(str(eval(ctx.message.content[6:])))
        print(f'{ctx.message.author} used eval')


@bot.command(aliases=['invite', 'invitecode', 'invite_link', 'invitelink'])
async def invite_code(ctx):
    # await ctx.send(discord.Invite(channel=ctx.message.channel, code=invitation_code).url)
    await ctx.send(f'https://discord.gg/{invitation_code}')


@bot.command()
async def games(ctx):
    await ctx.send('We have: Tic-Tac-Toe (!ttt) and Shift (!shift)')


@bot.command()
async def ttt(ctx):
    global ttt_round, players_in_game, tic_tac_toe_data
    author: discord.User = ctx.message.author
    # TODO: turn into DM game
    # print(message.author.top_role.is_everyone) checks if role is @everyone
    if ttt_games.get(author, False):
        await author.send('You are already in a game. To end a game do !end')
    else:
        msg = 'You have started a Tic-Tac-Toe game\nThe game will end after 2 minutes of' \
              'inactivity or if you enter !end\nWould you like to go first? [Y/n]'
        await author.send(msg)
        ttt_round = 0
        # TODO: do I really need username in dict??
        # TODO: replace game_over with in_game
        tic_tac_toe_data[author] = {'username': str(author), 'comp_moves': [], 'user_moves': [], 'danger': None,
                                    'danger2': None, 'game_over': False}
        user_msg, game_channel = True, author.dm_channel
        if not game_channel:
            await author.create_dm()

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

                if user_msg is not None:
                    user_msg = user_msg.content.lower()
                    if 'end' in user_msg:
                        tic_tac_toe_data[author]['game_over'] = True
                        await ctx.send_message(game_channel, 'You have ended your tic-tac-toe game')
                    else:
                        ttt_round = 1
                        temp_msg = tictactoe.greeting(tic_tac_toe_data[author], user_msg)  # msg is y or n
                        await ctx.send_message(game_channel, temp_msg)
            except asyncio.TimeoutError:
                tic_tac_toe_data[author]['game_over'] = True

        while not tic_tac_toe_data[author]['game_over']:
            try:
                user_msg = await bot.wait_for('message', timeout=120, check=check_digit)
                if user_msg is not None:
                    if 'end' in user_msg.content.lower():
                        tic_tac_toe_data[author]['game_over'] = True
                        await game_channel.send_message('You have ended your tic-tac-toe game')
                        continue
                    else:
                        player_move = int(user_msg.content)
                        temp_msg, d = tictactoe.valid_move(player_move, tic_tac_toe_data[author])
                        print(tic_tac_toe_data[author] == d)
                        tic_tac_toe_data[author] = d
                        if not temp_msg:
                            await game_channel.send_message('That was not a valid move')
                        else:
                            temp_msg += '\n'
                            tic_tac_toe_data[author]['user_moves'].append(player_move)
                            tempt = tictactoe.tic_tac_toe_move(ttt_round, tic_tac_toe_data[author])[0]
                            if tic_tac_toe_data[author]['game_over']:
                                print(tic_tac_toe_data[author]['game_over'])
                                tic_tac_toe_data[author]['game_over'] = True
                                if ttt_round == 5:
                                    await ctx.send(f'Your Move{temp_msg + tempt}')
                                else:
                                    await ctx.send(f'Your Move{temp_msg}My Move{tempt}')
                            else:  # TODO: rich embed???
                                await ctx.send(f'Your Move{temp_msg}My Move{tempt}\nEnter your move (#)')
                            ttt_round += 1
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


def get_yield(fut):
    d = yield from fut
    return d


async def download_if_not_exists(ctx, title, video_id, play_immediately=False, in_background=False, play_next=False):
    """
    Checks if file corresponding to title and video_id exists
    If it doesn't exist, download it
    returns None if it exists, or discord.Message object of the downloading title if it doesn't
    """

    music_filepath = f'Music/{video_id}.mp3'
    m = None
    if not os.path.exists(music_filepath) and video_id not in data_dict['downloads']:
        m = await ctx.channel.send(f'Downloading `{title}`')

        if in_background or play_immediately:
            def callback(_):
                if play_next: msg_content = f'Added `{title}` to next up'
                else: msg_content = f'Added `{title}` to the playing queue'
                bot.loop.create_task(m.edit(content=msg_content))
                data_dict['downloads'].pop(video_id)
                # todo: call play_file(ctx) if play_immediately and mq[0].title == title
                #   the latter in case some guy decides to call skip

            result: asyncio.Future = bot.loop.run_in_executor(None, youtube_download, video_id)
            result.add_done_callback(callback)

            data_dict['downloads'][video_id] = (result, m)
        else:
            youtube_download(video_id)
    return m


# TODO: Sigh sound
@bot.command()
async def sigh():
    raise NotImplementedError


@bot.command()
async def set_music_chat():
    raise NotImplementedError


async def download_related_video(ctx, auto_play_setting):
    if auto_play_setting:
        guild = ctx.guild
        guild_data = data_dict[guild]
        upcoming_tracks, play_history = guild_data['music'], guild_data['done']
        if len(upcoming_tracks) == 1:
            related_url, related_title, related_video_id = get_related_video(upcoming_tracks[0].video_id, play_history)
            upcoming_tracks.append(Song(related_title, related_video_id))
            related_m = await download_if_not_exists(ctx, related_title, related_video_id, in_background=True)
            related_msg_content = f'Added `{related_title}` to the playing queue'
            if not related_m: await ctx.send(related_msg_content)


async def play_file(ctx):
    """Plays first (index=0) song in the music queue"""
    guild: discord.Guild = ctx.guild
    voice_client: discord.VoiceClient = guild.voice_client
    guild_data = data_dict[guild]
    upcoming_tracks = guild_data['music']
    play_history = guild_data['done']

    # TODO: use a db to determine which files get constantly used

    # noinspection PyUnusedLocal
    def after_play(error):
        mq = guild_data['music']
        ph = guild_data['done']
        if not error and not data_dict[guild]['is_stopped']:
            # pylint: disable=assignment-from-no-return
            if len(voice_client.channel.members) > 1:
                # mq = guild_data['music']
                # ph = guild_data['done']
                if not guild_data['repeat']:
                    last_song = mq.pop(0)
                    ph.insert(0, last_song)
                else:
                    last_song = mq[0]

                if guild_data['repeat_all']:
                    if not mq and ph:
                        mq = guild_data['music'] = ph[::-1]
                        ph.clear()

                setting = guild_data['auto_play']
                if mq or setting:
                    if setting and not mq:
                        url, next_title, next_video_id = get_related_video(last_song.video_id, ph)
                        next_m = run_coro(download_if_not_exists(ctx, next_title, next_video_id, in_background=False))
                        mq.append(Song(next_title, next_video_id))
                    else:  # if mq, check if the song is downloading # NOTE: was here last
                        next_result, next_m = data_dict['downloads'].get(video_id, (None, None))
                        if next_result:
                            run_coro(next_result)
                            data_dict['downloads'].pop(next_result)
                        else:
                            next_m = run_coro(download_if_not_exists(ctx, title, video_id, in_background=False))
                    next_song = mq[0]
                    next_title = next_song.title
                    next_music_filepath = f'Music/{next_song.video_id}.mp3'
                    next_audio_source = FFmpegPCMAudio(next_music_filepath, executable=ffmpeg_path)
                    next_audio_source = PCMVolumeTransformer(next_audio_source)
                    next_audio_source.volume = guild_data['volume']
                    voice_client.play(next_audio_source, after=after_play)
                    run_coro(bot.change_presence(activity=discord.Game(next_title)))
                    next_msg_content = f'Now playing `{next_title}`'
                    if next_m:
                        run_coro(next_m.edit(content=next_msg_content))
                    else:
                        run_coro(ctx.send(next_msg_content))

                    run_coro(download_related_video(ctx, setting))
                    # if setting and len(mq) == 1:
                    #     url, next_title, next_video_id = get_related_video(mq[0].video_id, ph)
                    #     mq.append(Song(next_title, next_video_id))
                    #     next_m = run_coro(download_if_not_exists(ctx, next_title, next_video_id, in_background=True))
                    #     next_msg_content = f'Added `{next_title}` to the playing queue'
                    #     if not next_m: run_coro(ctx.send(next_msg_content))

            else:
                run_coro(bot.change_presence(activity=discord.Game('Prison Break (!)')))
                if len(voice_client.channel.members) == 1: run_coro(voice_client.disconnect())

    if voice_client and upcoming_tracks:
        # TODO: account for auto_play
        song = upcoming_tracks[0]
        title = song.title
        video_id = song.video_id
        music_filepath = f'Music/{video_id}.mp3'
        result, m = data_dict['downloads'].get(video_id, (None, None))
        if result:
            await result
            return
        else:
            m = await download_if_not_exists(ctx, title, video_id, in_background=False)
        guild_data['is_stopped'] = False
        audio_source = FFmpegPCMAudio(music_filepath, executable=ffmpeg_path)
        audio_source = PCMVolumeTransformer(audio_source)
        audio_source.volume = guild_data['volume']
        voice_client.play(audio_source, after=after_play)
        msg_content = f'Now playing `{title}`'
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
        # if len(upcoming_tracks) == 1 and guild_data['auto_play']:
    #     related_url, related_title, related_video_id = get_related_video(upcoming_tracks[0].video_id, play_history)
    #     upcoming_tracks.append(Song(related_title, related_video_id))
    #     related_m = run_coro(download_if_not_exists(ctx, related_title, related_video_id, in_background=True))
    #     related_msg_content = f'Added `{related_title}` to the playing queue'
    #     if not related_m: run_coro(ctx.send(related_msg_content))


@bot.command(aliases=['paly', 'p', 'P', 'pap', 'pn', 'play_next', 'playnext'])
async def play(ctx):
    # TODO: rename done queue to recently played
    # TODO: rename music_queue to next up
    # TODO: add repeat play option
    # TODO: time remaining command + song length command
    # TODO: download option
    guild = ctx.guild
    voice_client: discord.VoiceClient = guild.voice_client
    ctx_msg_content = ctx.message.content
    play_next = any([cmd in ctx_msg_content for cmd in ('pn', 'play_next', 'playnext')])
    guild_data = data_dict[guild]
    mq = guild_data['music']
    if voice_client is None:
        voice_client = await bot.get_command('summon').callback(ctx)
        # voice_client = guild.voice_client
    url_or_query = ctx.message.content.split()
    if len(url_or_query) > 1:
        url_or_query = ' '.join(url_or_query[1:])
        if url_or_query.startswith('https://'):
            # TODO: playlist support
            url = url_or_query
            video_id = get_video_id(url)
            title = get_video_title(video_id)
            if get_video_duration(video_id) > 600:
                await ctx.send('That song is too long! (> 10 minutes)')
                return
        else:  # get url
            try:
                url, title, video_id = youtube_search(url_or_query, return_info=True, limit_duration=True)
            except ValueError:
                await ctx.send(f'No valid video found with query `{url_or_query}`')
                return
        song = Song(title, video_id)

        # adding to queue
        if mq and play_next:
            mq.insert(1, song)
        else:
            mq.append(song)

        # download the song if something is already being played
        if voice_client.is_playing() or voice_client.is_paused():
            # download if your not going to play the file
            m = await download_if_not_exists(ctx, title, video_id, in_background=True, play_next=play_next)
            if play_next:  m_content = f'Added `{title}` to next up'
            else: m_content = f'Added `{title}` to the playing queue'
            if not m: await ctx.send(m_content)
        else:
            await play_file(ctx)  # download if need to and then play the song

    elif (voice_client.is_playing() or voice_client.is_paused()) and not play_next:
        await bot.get_command('pause').callback(ctx)
    elif mq:
        await play_file(ctx)
    if ctx_msg_content.startswith('!pap'):
        await bot.get_command('auto_play').callback(ctx)


@bot.command(aliases=['resume'])
async def pause(ctx):
    voice_client: discord.VoiceClient = ctx.guild.voice_client
    if voice_client:
        await bot.change_presence(activity=discord.Game('Prison Break (!)'))
        if voice_client.is_paused():
            voice_client.resume()
        else:
            voice_client.pause()


@bot.command(name='auto_play', aliases=['ap', 'autoplay'])
async def _auto_play(ctx, setting: bool = None):
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
            song_id = dq[0].video_id
            url, title, video_id, = get_related_video(song_id, dq)
            mq.append(Song(title, video_id))
            await play_file(ctx)  # takes care of the download
        if len(mq) == 1:
            song_id = mq[0].video_id
            url, title, video_id, = get_related_video(song_id, dq)
            mq.append(Song(title, video_id))
            m = await download_if_not_exists(ctx, title, video_id, in_background=True)
            msg_content = f'Added `{title}` to the playing queue'
            if not m: await ctx.send(msg_content)


@bot.command(name='repeat', aliases=['r'])
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
async def _repeat_all(ctx, setting: bool = None):
    guild = ctx.guild
    voice_client: discord.VoiceClient = guild.voice_client
    guild_data = data_dict[guild]
    if setting is None:
        setting = not data_dict[guild]['repeat_all']
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
    else:
        await ctx.send('Repeating all set to False')


def no_after_play(guild_data, voice_client):
    if voice_client and voice_client.is_playing():
        guild_data['is_stopped'] = True
        voice_client.stop()
        guild_data['is_stopped'] = False


@bot.command(aliases=['next', 'n', 'sk'])
async def skip(ctx, times=1):
    # TODO: make it a partial democracy but mods and admins can bypass it
    guild = ctx.guild
    voice_client: discord.VoiceClient = guild.voice_client
    if voice_client:
        guild_data = data_dict[guild]
        mq = guild_data['music']
        dq = guild_data['done']
        if mq:
            with suppress(IndexError):
                for _ in range(times): dq.insert(0, mq.pop(0))
            no_after_play(guild_data, voice_client)
            if not mq and guild_data['repeat_all']:
                guild_data['music'] = dq[::-1]
                dq.clear()
            await play_file(ctx)


@bot.command(aliases=['back', 'b', 'prev', 'go_back', 'gb'])
async def previous(ctx, times=1):
    # TODO: make it a partial democracy but mods and admins can bypass it
    guild = ctx.guild
    voice_client: discord.VoiceClient = guild.voice_client
    if voice_client:
        guild_data = data_dict[guild]
        mq = guild_data['music']
        ph = guild_data['done']
        if ph:
            with suppress(IndexError):
                for _ in range(times): mq.insert(0, ph.pop(0))
            no_after_play(guild_data, voice_client)
            await play_file(ctx)


@bot.command(aliases=['music_queue', 'mq', 'nu', 'queue', 'que', 'q'])
async def next_up(ctx):
    guild = ctx.guild
    guild_data = data_dict[guild]
    mq = guild_data['music']
    if mq:
        title = 'MUSIC QUEUE'  # :musical_note:
        if guild_data['auto_play']: title += ' | AUTO PLAY ENABLED'
        if guild_data['repeat_all']: title += ' | REPEAT ALL ENABLED'
        if guild_data['repeat']: title += ' | REPEAT SONG ENABLED}'
        msg = ''
        for i, song in enumerate(mq):
            if i == 10:
                msg += '\n...'
                break
            msg += f'\n`{i}.` {song.title}' if i > 0 else f'\nPlaying {song.title}'
        embed = create_embed(title, description=msg)
        await ctx.send(embed=embed)
        # await ctx.send(title + msg)
    else:
        # await ctx.send('MUSIC QUEUE IS EMPTY')
        await ctx.send(embed=create_embed('MUSIC QUEUE IS EMPTY'))


@bot.command(name='recently_played', aliases=['done_queue', 'dq', 'rp'])
async def _recently_played(ctx):
    # TODO: make a play_history list that never gets modified and takes in a parameter page_number
    guild = ctx.guild
    dq = data_dict[guild]['done']
    if dq:
        title = 'RECENTLY PLAYED'
        msg = ''
        for i, song in enumerate(dq):
            if i == 10:
                msg += '\n...'
                break
            msg += f'\n-{i + 1} `{song.title}`'
        embed = create_embed(title, description=msg)
        await ctx.send(embed=embed)
        await ctx.send(msg)
    else:
        await ctx.send('RECENTLY PLAYED IS EMPTY, were you looking for !play_history?')


@bot.command()
async def remove(ctx, position: int = 0):
    guild = ctx.guild
    guild_data = data_dict[guild]
    mq = guild_data['music']
    dq = guild_data['done']
    voice_client: discord.VoiceClient = guild.voice_client
    with suppress(IndexError):
        if position < 0:
            dq.pop(-position - 1)
        elif position > 0:
            mq.pop(position)
        else:
            no_after_play(guild_data, voice_client)
            mq.pop(0)


@bot.command(aliases=['cq', 'clearque', 'clear_q', 'clear_que', 'clearq', 'clearqueue', 'queue_clear', 'queueclear'])
async def clear_queue(ctx):
    guild = ctx.guild
    moderator = discord.utils.get(guild.roles, name='Moderator')
    if ctx.author.top_role >= moderator:
        data_dict[guild]['music'].clear()
        await ctx.send('Cleared music queue')


# @bot.command(aliases=['ff', 'fast-forward', 'fast'])
# async def fast_forward(ctx):  # TODO
#     raise NotImplementedError


@bot.command(aliases=['np', 'currently_playing', 'cp'])
async def now_playing(ctx):
    guild = ctx.guild
    mq = data_dict[guild]['music']
    embed = create_embed('Currently Playing', 'https://www.youtube.com/watch?v={mq[0].video_id}', discord.Color.red())
    await ctx.send(f'Currently playing: https://www.youtube.com/watch?v={mq[0].video_id}')
    await ctx.send(embed=embed)


@bot.command(aliases=['desummon', 'disconnect', 'unsummon', 'dismiss', 'd'])
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


@bot.command(aliases=['end'])
async def stop(ctx):
    guild = ctx.guild
    voice_client: discord.VoiceClient = guild.voice_client
    if voice_client and voice_client.is_playing():
        data_dict[guild]['is_stopped'] = True
        voice_client.stop()


@bot.command()
async def fix(ctx):
    guild = ctx.message.channel.guild
    await bot.get_command('summon').callback(ctx)
    voice_client: discord.VoiceClient = guild.voice_client
    await voice_client.disconnect()
    await bot.get_command('summon').callback(ctx)


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


@bot.command(aliases=['set_volume', 'sv', 'v'])
async def volume(ctx):
    guild = ctx.guild
    vc: discord.VoiceClient = guild.voice_client
    if vc:
        args = ctx.message.content.split(' ')
        if len(args) == 2:
            try:
                arg = args[1]
                if arg.startswith('+'):
                    if arg[1:]: amount = vc.source.volume + float(arg[1:])/100
                    else: amount = vc.source.volume + 0.1
                elif arg.startswith('-'):
                    if arg[1:]: amount = vc.source.volume - float(arg[1:]) / 100
                    else: amount = vc.source.volume - 0.1
                else:
                    amount = float(args[1]) / 100
                # noinspection PyTypeChecker
                amount = max(0, amount)
                amount = min(1, amount)
                vc.source.volume = amount
                data_dict[guild]['volume'] = amount
            except ValueError:
                await ctx.send('Invalid argument')
        else:
            await ctx.send(vc.source.volume)


@bot.command()
async def about(ctx):
    ctx.author.send(f'Hi there. Thank you for wanting to know more about me. I was made by Elijah Lopez.\n'
                    'For more information visit https://github.com/elibroftw/discord-bot.\n'
                    'Join my server at https://discord.gg/{invitation_code})')


bot.run(os.environ['discord'])

# TODO: 'shop', 'math', 'ban', 'remove_role', 'delete_role'
