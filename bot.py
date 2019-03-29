import asyncio
import copy
import os
from datetime import datetime
from pprint import pprint
from subprocess import run

import discord
from discord import FFmpegPCMAudio
from discord.ext import commands

import tictactoe
from helpers import youtube_download, youtube_search, get_related_video, get_video_id, get_video_title, load_opus_lib, \
    update_net_worth, check_net_worth, Song, get_video_duration

bot = commands.Bot(command_prefix='!')
bot.command()

invitation_code = os.environ['INVITATION_CODE']
load_opus_lib()
ttt_round = 0
players_in_game = []
tic_tac_toe_data: dict = {}
ttt_games = {}
ffmpeg_path = 'ffmpeg/bin/ffmpeg'
mqs = music_queues = {}
auto_play_dict = {}
play_next_dict = {}
is_stopped = {}

with open('help.txt') as f:
    help_message = f.read()


@bot.event
async def on_ready():
    print('Logged In')
    await bot.change_presence(activity=discord.Game('Prison Break'))


@bot.event
async def on_member_join(member):
    server = member.server
    msg = f'Welcome inmate {member.mention} to the {server.name} server!\n'
    # await bot.send_message(server, msg)
    msg += 'Use !help for my functions'
    await member.send_message(member, msg)  # untested


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
async def test(ctx, say_something=False):
    if say_something:
        await ctx.send('yoooo')
    else:
        await ctx.send('broo')


@bot.command()
async def sleep(ctx):
    if ctx.message.author.top_role == 'Admin':
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


# TODO: delete_role
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
async def youtube(ctx, query=None):
    if query: await ctx.send(youtube_search(query))
    # else: await ctx.send('ERROR: No search parameter given')


@bot.command(name='exit', aliases=['quit'])
async def _exit(ctx):
    if str(ctx.author) == 'eli#4591':
        voice_client: discord.VoiceClient = discord.utils.get(bot.voice_clients, guild=ctx.guild)
        if voice_client: await voice_client.disconnect()
        quit()


@bot.command()
async def restart(ctx):
    if str(ctx.author) == 'eli#4591':
        voice_client: discord.VoiceClient = discord.utils.get(bot.voice_clients, guild=ctx.guild)
        if voice_client: await voice_client.disconnect()
        print('Restarting')
        run('python bot.py')
        quit()


# @bot.command(, aliases=['gettweet', 'get_tweet'])
# async def twitter(ctx):
#     # TODO: add --integer to define how many statuses, use regex
#     # TODO: add a clamp (3 for this 10 for the next) so nobody can abuse the system
#     msg = discord_get_tweet_from(ctx.message.content[ctx.message.content.index(' ') + 1:])  # TODO: execpt ValueError
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


@bot.command()
async def clear(ctx):
    try:
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
        await bot.change_presence(activity=discord.Game('Prison Break'))
    except AttributeError:
        pass


@bot.command(aliases=['eval'])
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
        # TODO: remove username from dict
        # TODO: replace game_over with in_game
        tic_tac_toe_data[author] = {'username': str(author), 'comp_moves': [], 'user_moves': [], 'danger': None,
                                    'danger2': None, 'game_over': False}
        user_msg, game_channel = True, author.dm_channel
        if not game_channel:
            await author.create_dm()
        # TODO: Change the parameter name??

        def check_yn(m):
            correct_prereqs = m.channel == game_channel and author == m.author
            m = m.content.lower()
            bool_value = m in ('y', 'yes', 'no', 'n', '!end')
            return bool_value and correct_prereqs

        def check_digit(m):
            correct_prereqs = m.channel == game_channel and ctx.message.author == m.author
            m = m.content
            return (m.isdigit() or m.lower() == '!end') and correct_prereqs

        while user_msg is None and not tic_tac_toe_data[author]['game_over']:
            try:
                user_msg = await bot.wait_for('message', timeout=120, check=check_yn)

                if user_msg is not None:
                    user_msg = user_msg.content.lower()
                    if user_msg == '!end':
                        tic_tac_toe_data[author]['game_over'] = True
                        await ctx.send_message(game_channel, 'You have ended your tic-tac-toe game')
                    else:
                        ttt_round = 1
                        temp_msg = tictactoe.greeting(tic_tac_toe_data[author], user_msg)  # msg is y or n
                        await ctx.send_message(game_channel, temp_msg)
            except asyncio.TimeoutError: tic_tac_toe_data[author]['game_over'] = True

        while not tic_tac_toe_data[author]['game_over']:
            try:
                user_msg = await bot.wait_for('message', timeout=120, check=check_digit)
                if user_msg is not None:
                    if user_msg.content.lower() == '!end':
                        tic_tac_toe_data[author]['game_over'] = True
                        await game_channel.send_message('You have ended your tic-tac-toe game')
                        continue
                    else:
                        player_move = int(user_msg.content)
                        temp_msg, d = tictactoe.valid_move(player_move, tic_tac_toe_data[author])
                        print(tic_tac_toe_data[author] == d)
                        tic_tac_toe_data[author] = d
                        if not temp_msg: await game_channel.send_message('That was not a valid move')
                        else:
                            temp_msg += '\n'
                            tic_tac_toe_data[author]['user_moves'].append(player_move)
                            tempt = tictactoe.tic_tac_toe_move(ttt_round, tic_tac_toe_data[author])[0]
                            if tic_tac_toe_data[author]['game_over']:
                                print(tic_tac_toe_data[author]['game_over'])
                                tic_tac_toe_data[author]['game_over'] = True
                                if ttt_round == 5: await ctx.send(f'Your Move{temp_msg + tempt}')
                                else: await ctx.send(f'Your Move{temp_msg}My Move{tempt}')
                            else:  # TODO: rich embed???
                                await ctx.send(f'Your Move{temp_msg}My Move{tempt}\nEnter your move (#)')
                            ttt_round += 1
            except asyncio.TimeoutError: tic_tac_toe_data[author]['game_over'] = True


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
    try: await ctx.send(user.created_at)
    except AttributeError: await ctx.send(f'could not find that user in the server')


@bot.command()
async def summon(ctx):
    guild = ctx.message.channel.guild
    author: discord.Member = ctx.message.author
    if not author.voice:
        await discord.utils.get(guild.voice_channels, name='music').connect()
    else:
        voice_client: discord.VoiceClient = discord.utils.get(
            bot.voice_clients, guild=guild)
        channel: discord.VoiceChannel = author.voice.channel
        if not voice_client:
            await channel.connect()
        elif voice_client.channel != channel:
            # TODO: add a role lock?
            await voice_client.move_to(channel)


def run_coro(coro):
    # e.g. coro = bot.change_presence(activity=discord.Game('Prison Break'))
    fut = asyncio.run_coroutine_threadsafe(coro, bot.loop)
    return fut.result()


async def download_if_not_exists(ctx, title, video_id):
    """
    Checks if file corresponding to title and video_id exists
    If it doesn't exist, download it
    returns None if it exists, or discord.Message object of the downloading title if it doesn't
    """
    music_filepath = f'Music/{title} - {video_id}.mp3'
    if not os.path.exists(music_filepath):
        m: discord.Message = await ctx.channel.send(f'Downloading `{title}`')
        youtube_download(f'https://www.youtube.com/watch?v={video_id}')
        return m
    return None


# TODO: Sigh sound
@bot.command()
async def sigh():
    raise NotImplementedError


@bot.command()
async def set_music_chat():
    raise NotImplementedError


@bot.command(aliases=['music_queue', 'mq', 'nu'])
async def next_up(ctx):
    # TODO: rich embed?
    guild = ctx.guild
    try:
        music_queue = music_queues[guild]['music_queue']
        if music_queue:
            msg = 'MUSIC QUEUE | AUTO PLAY ENABLED' if auto_play_dict.get(guild, False) \
                else 'MUSIC QUEUE | AUTO PLAY DISABLED'
            for i, song in enumerate(music_queue):
                if i == 10:
                    msg += '\n...'
                    break
                msg += f'\n{i} `{song.title}`' if i > 0 else f'\nCurrently Playing `{song.title}`'
            await ctx.send(msg)
    except KeyError: music_queues[guild] = {'music_queue': [], 'done_queue': []}


@bot.command(name='recently_played', aliases=['done_queue', 'dq', 'rp'])
async def _recently_played(ctx):
    # TODO: rich embed?
    guild = ctx.guild
    try:
        done_queue = music_queues[guild]['done_queue']
        if done_queue:
            msg = 'RECENTLY PLAYED'
            for i, song in enumerate(done_queue):
                if i == 10:
                    msg += '\n...'
                    break
                msg += f'\n-{i + 1} `{song.title}`'
            await ctx.send(msg)
    except KeyError: music_queues[guild] = {'music_queue': [], 'done_queue': []}


async def play_file(ctx):
    """Plays first (index=0) song in music queue"""
    guild = ctx.guild
    voice_client: discord.VoiceClient = discord.utils.get(bot.voice_clients, guild=guild)
    music_queue = music_queues[guild]['music_queue']
    done_queue = music_queues[guild]['done_queue']
    # TODO: use a db to determine which files get constantly used

    # noinspection PyUnusedLocal
    def after_play(error):
        # TODO: account for repeat=True
        if not error and not is_stopped.get(guild, False):
            # pylint: disable=assignment-from-no-return
            last_song = music_queue.pop(0)
            done_queue.insert(0, last_song)
            setting = auto_play_dict.get(guild, False)

            if music_queue or setting and len(voice_client.channel.members) > 1:
                if setting and not music_queue:
                    url, title, video_id = get_related_video(last_song.video_id, done_queue)
                    m = run_coro(download_if_not_exists(ctx, title, video_id))
                    music_queue.append(Song(title, video_id))
                else: m = None
                next_song = music_queue[0]
                next_title = next_song.title
                next_music_filepath = f'Music/{next_title} - {next_song.video_id}.mp3'
                voice_client.play(FFmpegPCMAudio(next_music_filepath, executable=ffmpeg_path), after=after_play)
                run_coro(bot.change_presence(activity=discord.Game(next_title)))

                msg_content = f'Now playing `{next_title}`'
                if m: run_coro(m.edit(content=msg_content))
                else: run_coro(ctx.send(msg_content))

                if setting and len(music_queue) == 1:
                    url, title, video_id = get_related_video(music_queue[0].video_id, done_queue)
                    m = run_coro(download_if_not_exists(ctx, title, video_id))
                    music_queue.append(Song(title, video_id))
                    msg_content = f'Added `{title}` to the queue'
                    if m: run_coro(m.edit(content=msg_content))
                    else: run_coro(ctx.send(msg_content))
            else:
                run_coro(bot.change_presence(activity=discord.Game('Prison Break')))
                if len(voice_client.channel.members) == 1: run_coro(voice_client.disconnect())

    if music_queue:
        song = music_queue[0]
        title = song.title
        video_id = song.video_id
        music_filepath = f'Music/{title} - {video_id}.mp3'
        m = await download_if_not_exists(ctx, title, video_id)
        is_stopped[guild] = False
        voice_client.play(FFmpegPCMAudio(music_filepath, executable=ffmpeg_path), after=after_play)
        msg_content = f'Now playing `{title}`'
        if m: await m.edit(content=msg_content)
        else:
            temp_mq = copy.deepcopy(music_queue)
            temp_dq = copy.deepcopy(done_queue)
            await ctx.send(msg_content)
            if temp_mq != music_queue:
                music_queue = music_queues[guild]['music_queue'] = copy.deepcopy(temp_mq)
                done_queue = music_queues[guild]['done_queue'] = copy.deepcopy(temp_dq)
        await bot.change_presence(activity=discord.Game(title))


@bot.command(aliases=['paly', 'p', 'P', 'queue', 'que', 'q', 'pap', 'pn', 'play_next', 'playnext'])
async def play(ctx):
    # TODO: rename done queue to recently played
    # TODO: rename music_queue to next up
    # TODO: add repeat play option
    # TODO: playlist support
    # TODO: time remaining command + song length command
    # TODO: make a dict of guild keys with values being text channels for the music-commands???
    guild = ctx.guild
    voice_client: discord.VoiceClient = discord.utils.get(bot.voice_clients, guild=guild)
    ctx_msg_content = ctx.message.content
    play_next = any([cmd in ctx_msg_content for cmd in ('pn', 'play_next', 'playnext')])
    if voice_client is None:
        await bot.get_command('summon').callback(ctx)
        voice_client: discord.VoiceClient = discord.utils.get(bot.voice_clients, guild=guild)
    url_or_query = ctx.message.content.split(' ')
    if len(url_or_query) > 1:
        url_or_query = ' '.join(url_or_query[1:])
    if url_or_query and type(url_or_query) != list:
        if url_or_query.startswith('https://'):
            url = url_or_query
            video_id = get_video_id(url)
            title = get_video_title(video_id)
            if get_video_duration(video_id) > 600:
                await ctx.send('That song is too long! (> 10 minutes)')
                return
        else:  # get url
            url, title, video_id = youtube_search(url_or_query, return_info=True, limit_duration=True)
        song = Song(title, video_id)
        # music_file = f'Music/{title} - {video_id}.mp3'

        # download if it does not exist
        m = await download_if_not_exists(ctx, title, video_id)

        # adding to queue
        if guild in music_queues:
            mq = music_queues[guild]['music_queue']
            if mq and play_next: mq.insert(1, song)
            else: mq.append(song)
        else: music_queues[guild] = {'music_queue': [song], 'done_queue': []}

        # play song if nothing is playing
        if voice_client.is_playing():
            m_content = f'Added `{title}` to the queue'
            if not m: await ctx.send(m_content)
        else:
            await play_file(ctx)
            m_content = f'Now playing `{title}`'

        if m: await m.edit(content=m_content)
    else:
        if (voice_client.is_playing() or voice_client.is_paused()) and not play_next:
            await bot.get_command('pause').callback(ctx)
        else: await play_file(ctx)
    if ctx_msg_content.startswith('!pap'):
        await bot.get_command('auto_play').callback(ctx)


@bot.command(aliases=['resume'])
async def pause(ctx):
    voice_client: discord.VoiceClient = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice_client:
        if voice_client.is_paused(): voice_client.resume()
        else: voice_client.pause()


@bot.command(aliases=['ap', 'autoplay'])
async def auto_play(ctx):
    """Turns auto play on or off"""
    guild = ctx.guild
    setting = not auto_play_dict.get(guild, False)
    auto_play_dict[guild] = setting
    await ctx.send(f'Auto play set to {setting}')
    if setting:
        # TODO: if argument given add to queue
        mq = music_queues[guild]['music_queue']
        dq = music_queues[guild]['done_queue']
        if not mq and dq:
            song_id = dq[0].video_id
            url, title, video_id, = get_related_video(song_id, dq)
            mq.append(Song(title, video_id))
            await play_file(ctx)  # takes care of the download
        if len(mq) == 1:
            song_id = mq[0].video_id
            url, title, video_id, = get_related_video(song_id, dq)
            # do on separate thread ???s
            m = await download_if_not_exists(ctx, title, video_id)
            mq.append(Song(title, video_id))
            msg_content = f'Added `{title}` to the queue'
            if m: await m.edit(content=msg_content)
            else: await ctx.send(msg_content)


@bot.command(aliases=['next', 'n', 'sk'])
async def skip(ctx):
    guild = ctx.guild
    voice_client: discord.VoiceClient = discord.utils.get(bot.voice_clients, guild=guild)
    if guild not in music_queues: music_queues[guild] = {'music_queue': [], 'done_queue': []}
    mq = music_queues[guild]['music_queue']
    dq = music_queues[guild]['done_queue']
    if voice_client:
        if voice_client.is_playing(): voice_client.stop()  # after_play runs
        elif mq:
            dq.insert(0, mq.pop(0))
            await play_file(ctx)


@bot.command(aliases=['back', 'b', 'prev', 'go_back', 'gb'])
async def previous(ctx, times=1):
    guild = ctx.guild
    voice_client: discord.VoiceClient = discord.utils.get(bot.voice_clients, guild=guild)
    if voice_client:

        music_queue: list = music_queues[guild]['music_queue']
        done_queue = music_queues[guild]['done_queue']
        if done_queue:
            try:
                for i in range(times):
                    song = done_queue.pop(0)
                    music_queue.insert(0, song)
            except IndexError: pass
            if voice_client.is_playing():
                is_stopped[guild] = True
                voice_client.stop()
                is_stopped[guild] = False
            await play_file(ctx)


@bot.command(aliases=['cq', 'clearque', 'clear_q', 'clear_que', 'clearq', 'clearqueue'])
async def clear_queue(ctx):
    guild = ctx.guild
    moderator = discord.utils.get(guild.roles, name='Moderator')
    if ctx.author.top_role >= moderator:
        music_queues[guild]['music_queue'].clear()


# TODO: fast forward
@bot.command(aliases=['ff', 'fast-forward', 'fast'])
async def fast_forward(ctx):
    raise NotImplementedError


@bot.command(aliases=['np', 'currently_playing', 'cp'])
async def now_playing(ctx):
    guild = ctx.guild
    try:
        music_queue = music_queues[guild]['music_queue']
        await ctx.send(f'Currently playing `{music_queue[0].title}`')
    except KeyError: music_queues[guild] = {'music_queue': [], 'done_queue': []}


@bot.command(aliases=['desummon', 'disconnect', 'unsummon', 'dismiss', 'l', 'd'])
async def leave(ctx):
    # clear music queue
    guild = ctx.guild
    if guild in music_queues: music_queues[guild]['music_queue'] = []
    else: music_queues[guild] = {'music_queue': [], 'done_queue': []}
    auto_play_dict[guild] = False
    voice_client: discord.VoiceClient = discord.utils.get(bot.voice_clients, guild=guild)
    if voice_client: await voice_client.disconnect()
    await ctx.send('Stopped playing music, music que has been emptied')


@bot.command(aliases=['end'])
async def stop(ctx):
    guild = ctx.guild
    is_stopped[guild] = True
    voice_client: discord.VoiceClient = discord.utils.get(bot.voice_clients, guild=guild)
    if voice_client and voice_client.is_playing(): voice_client.stop()


@bot.command()
async def fix(ctx):
    guild = ctx.message.channel.guild
    await bot.get_command('summon').callback(ctx)
    voice_client: discord.VoiceClient = discord.utils.get(
        bot.voice_clients, guild=guild)
    await voice_client.disconnect()
    await bot.get_command('summon').callback(ctx)


@bot.command()
async def source(ctx):
    await ctx.send('https://github.com/elibroftw/discord-bot')


@bot.command()
async def ban(ctx):

    if ctx.author.guild_permissions.ban_members:
        args = ctx.message.content.split(' ')
        if len(args) > 1:
            name = ' '.join(args[1:])
            user = discord.utils.get(ctx.guild.members, nick=name)
            if not user:
                user = discord.utils.get(ctx.guild.members, name=name)
            await ctx.guild.ban(user)

# @bot.command(aliases=['set_volume', 'sv')
# async def volume(ctx):
#     pass
    # voice_client: discord.VoiceClient = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    # if voice_client:
    #     amount = ctx.message.content[8:]
    #     voice_client.volume

    # discord.PCMVolumeTransformer
    # https://discordpy.readthedocs.io/en/rewrite/api.html#discord.PCMVolumeTransformer


@bot.command()
async def about(ctx):
    ctx.author.send(f'Hi there. Thank you for wanting to know more about me. I was made by Elijah Lopez.\n'
                    'For more information visit https://github.com/elibroftw/discord-bot.\n'
                    'Join my server at https://discord.gg/{invitation_code})')
bot.run(os.environ['discord'])

# TODO: 'shop', 'math', 'ban', 'remove_role', 'delete_role'
