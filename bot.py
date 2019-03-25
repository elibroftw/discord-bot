import asyncio
import discord
import time
import tictactoe
from datetime import datetime
from discord.ext import commands
from discord.ext.commands.errors import CommandInvokeError
from funcs import *
from subprocess import run

bot = commands.Bot(command_prefix='!')
bot.command()

invitation_code = os.environ['INVITATION_CODE']
load_opus_lib()
ttt_round = 0
players_in_game = []
tic_tac_toe_data: dict = {}
timers = [['[Beta]Tic-Tac-Toe(!ttt)', 0]]
# timers_2 = {'[Beta]Tic-Tac-Toe(!ttt)': 0, '[Alpha]Shift(!shift)': 0}
music_queues = {}

with open('help.txt') as f: help_message = f.read()


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
    if author != bot.user: update_net_worth(str(author))
    if message.content.startswith('!RUN'):
        await message.channel.send('I GOT EXTRADITED! :(')
    elif message.content.lower().startswith('!run'):
        await message.send('N o t  h y p e  e n o u g h')
    elif message.content.lower().startswith('!help'):
        await author.send(help_message)
        await message.delete()
    else:
        await bot.process_commands(message)


@bot.command()
async def hi(ctx):
    await ctx.send("Hey there" + " " + ctx.message.author.name + "!")


@bot.command()
async def test(ctx):
    if str(ctx.message.channel) == 'bot_testing':
        await ctx.send('TEST\nI DID SOMETHING')


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
    await ctx.message.author.send(check_networth(str(ctx.message.author)))
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
async def youtube(ctx):
    try:
        text = ctx.message.content[ctx.message.content.index(' ') + 1:]
        await ctx.send(youtube_search(text))
    except ValueError:
        await ctx.send('ERROR: No search parameter given')


@bot.command()
async def exit(ctx):
    moderator = discord.utils.get(ctx.guild.roles, name='Moderator')
    if ctx.author.top_role >= moderator:
        quit()

@bot.command()
async def restart(ctx):
    moderator = discord.utils.get(ctx.guild.roles, name='Moderator')
    if ctx.author.top_role >= moderator:
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
    await ctx.send(f"You're welcome {ctx.message.author.mention}")


@bot.command()
async def clear(ctx):
    try:
        channel: discord.TextChannel = ctx.message.channel
        guild = channel.guild
        moderator = discord.utils.get(guild.roles, name='Moderator')
        ctx.message.author.top_role: discord.Role  # .top_role is Admin
        # print(ctx.message.author.top_role.position)  # printed 4
        if ctx.message.author.top_role >= moderator:
            # await ctx.send('Clearing messages...')
            await bot.change_presence(activity=discord.Game('Clearing messages...'))
            number = 3
            if ctx.message.content[7:].isnumeric():  # len(user_msg) > 7 and
                if int(ctx.message.content[7:]) > 98: number = 100 - int(ctx.message.content[7:])
                number += int(ctx.message.content[7:]) - 1
            messages = []
            async for m in channel.history(limit=number):
                date = m.created_at
                if (datetime.now() - date).days > 14:  # if older than 14: delete else add onto msg list
                    await m.delete()
                else:
                    messages.append(m)
            await channel.delete_messages(messages)
            print(f'{ctx.message.author} cleared {number - 2} message(s)')
        await bot.change_presence(activity=discord.Game('Prison Break'))
    except AttributeError: pass



# aliases=['shop', 'math', 'ban', 'remove_role', 'delete_role']
# @bot.command()
# async def todo():  # TODO
#     await ctx.send('This command still needs to be implemented!')


@bot.command(aliases=['eval'])
async def _eval(ctx):
    if str(ctx.message.author.top_role) == 'Admin':
        await ctx.send(str(eval(ctx.message.content[6:])))
        print(f'{ctx.message.author} used eval')


@bot.command(aliases=['invite', 'invitecode', 'invite_link', 'invitelink'])
async def invite_code(ctx):  # Todo: maybe get rid of channel=
    # await ctx.send(discord.Invite(channel=ctx.message.channel, code=invitation_code).url)
    await ctx.send(f'https://discord.gg/{invitation_code}')


@bot.command()
async def games(ctx):
    msg = 'We have:'
    for timer in timers:
        t = round(time.time() - timer[1])
        if t > 120:
            msg += f'\n{timer[0]}  `open`'
        else:
            msg += f'\n{timer[0]}  `{120 - t} seconds until free`'
    await ctx.send(msg)


@bot.command()
async def ttt(ctx):
    global ttt_round, players_in_game, tic_tac_toe_data, timers
    author = str(ctx.message.author)
    # TODO: Make tic tac toe lobby's so that when a player starts a game in a lobby,
    #  only they are allowed to send messages to the channel
    # print(message.author.top_role.is_everyone) checks if role is @everyone
    if time.time() - timers[0][1] < 120:
        await ctx.send('There is another tic-tac-toe game in progress')
    else:
        msg = 'You have started a Tic-Tac-Toe game\nThe game will end after 2 minutes of' \
              'inactivity or if you enter !end\nWould you like to go first? [Y/n]'
        await ctx.send(msg)
        ttt_round = 0
        players_in_game.clear()  # TODO: DELETE ANY DICTIONARY ENTRIES OF PLAYERS THAT AREN'T IN GAME
        tic_tac_toe_data[author] = {'username': author, 'comp_moves': [], 'user_moves': [], 'danger': None,
                                    'danger2': None, 'game_over': False}
        players_in_game.append(author)
        timers[0][1] = time.time()
        user_msg, in_game, game_channel = None, True, ctx.message.channel

        # TODO: Change the parameter name
        def check_yn(m):
            correct_prereqs = m.channel == game_channel and ctx.message.author == m.author
            m = m.content.lower()
            bool_value = m in ('y', 'yes', 'no', 'n', '!end')
            return bool_value and correct_prereqs

        def check_digit(m):
            correct_prereqs = m.channel == game_channel and ctx.message.author == m.author
            m = m.content
            return (m.isdigit() or m.lower() == '!end') and correct_prereqs

        while user_msg is None and in_game:
            if time.time() - timers[0][1] > 120 or not in_game: break
            user_msg = await ctx.wait_for_message(timeout=120, author=ctx.message.author, check=check_yn)
            if user_msg is not None:
                user_msg = user_msg.content.lower()
                if user_msg == '!end':
                    in_game = False
                    timers[0][1] = 0
                    players_in_game.remove(author)
                    await ctx.send_message(game_channel, 'You have ended your tic-tac-toe game')
                    continue
                timers[0][1] = time.time()
                ttt_round = 1
                temp_msg = tictactoe.greeting(tic_tac_toe_data[author], user_msg)  # msg is y or n
                await ctx.send_message(game_channel, temp_msg)
        while in_game:
            user_msg = await bot.wait_for('message', timeout=120, check=check_digit)
            if user_msg is not None:
                if user_msg.content.lower() == '!end':
                    in_game = False
                    timers[0][1] = 0
                    players_in_game.remove(author)
                    await game_channel.send_message('You have ended your tic-tac-toe game')
                    continue
                player_move = int(user_msg.content)
                temp_msg, tic_tac_toe_data[author] = tictactoe.valid_move(player_move, tic_tac_toe_data[author])
                if not temp_msg:  # so ''
                    await game_channel.send_message('That was not a valid move')
                else:
                    temp_msg += '\n'
                    tic_tac_toe_data[author]['user_moves'].append(player_move)
                    tempt, win = tictactoe.tic_tac_toe_move(ttt_round, tic_tac_toe_data[author])
                    if tic_tac_toe_data[author]['game_over']:
                        timers[0][1] = 0
                        # TODO: CLEAN ALL OF THIS UP
                        players_in_game.remove(author)
                        in_game = False
                        if ttt_round == 5:
                            await ctx.send(f'Your Move{temp_msg + tempt}')
                        else:
                            await ctx.send(f'Your Move{temp_msg}My Move{tempt}')
                    else:  # TODO: rich embed???
                        await ctx.send(f'Your Move{temp_msg}My Move{tempt}\nEnter your move (#)')
                        timers[0][1] = time.time()
                    ttt_round += 1


@bot.command()
async def shift(ctx):
    await ctx.send('https://elibroftw.itch.io/shift')


@bot.command(aliases=['create_date'])
async def created_at(ctx):
    args = ctx.message.content.split(' ')
    if len(args) > 1:
        user = discord.utils.get(ctx.guild.members, name=' '.join(args[1:]))
    else:
        user = ctx.author
    try: await ctx.send(user.created_at)
    except CommandInvokeError:
        await ctx.send(f'could not find that user in the server')



@bot.command()
async def summon(ctx):
    guild = ctx.message.channel.guild
    author: discord.Member = ctx.message.author
    if not author.voice:
        await discord.utils.get(guild.voice_channels, name='music').connect()
    else:
        voice_client: discord.VoiceClient = discord.utils.get(bot.voice_clients, guild=guild)
        channel: discord.VoiceChannel = author.voice.channel
        if not voice_client:
            await channel.connect()
        elif voice_client.channel != channel:
            # TODO: add a role lock?
            await voice_client.move_to(channel)
            

@bot.command(aliases=['paly', 'queue', 'que', 'p'])
async def play(ctx):
    guild = ctx.guild
    voice_client: discord.VoiceClient = discord.utils.get(bot.voice_clients, guild=guild)
    if voice_client is None:
        command = bot.get_command('summon')
        await command.callback(ctx)
        voice_client: discord.VoiceClient = discord.utils.get(bot.voice_clients, guild=guild)
    url_or_query = ctx.message.content.split(' ')
    if len(url_or_query) > 1:
        url_or_query = ' '.join(url_or_query[1:])
    if url_or_query:
        # get url
        if url_or_query.startswith('https://'):
            url = url_or_query
        else:  # query
            url = youtube_search(url_or_query)
        music_file = f'Music/{video_id(url)}.mp3'
        # download if it does not exist
        # use a db to determine which files get constantly used
        if not os.path.exists(music_file):
            m = await ctx.message.channel.send(f'Downloading song...')
            youtube_download(url)
            await m.delete()

        # playing time
        audio_source = discord.FFmpegPCMAudio(music_file, executable='ffmpeg/bin/ffmpeg')
        if guild in music_queues:
            music_queues[guild].append(audio_source)
        else:
            music_queues[guild] = [audio_source]
        music_queue = music_queues[guild]
        # print('added song to queue')

        async def next_song(error):
            music_queues[guild].pop(0)
            mq = music_queues[guild]
            if mq:
                # await bot.change_presence(activity=discord.Game('NAME OF VIDEO'))
                voice_client.play(music_queue[0], after=next_song)
            else:
                await bot.change_presence(activity=discord.Game('Prison Break'))

        if not voice_client.is_playing():
            voice_client.play(audio_source, after=next_song)
            # await bot.change_presence(activity=discord.Game('NAME OF VIDEO'))
            
    else:
        if voice_client.is_paused():
            voice_client.resume()
            


@bot.command()
async def skip(ctx):
    guild = ctx.guild
    voice_client: discord.VoiceClient = discord.utils.get(bot.voice_clients, guild=guild)
    if voice_client and music_queues[guild]:
        print('Skipped')
        music_queues[guild].pop(0)
        music_queue = music_queues[guild]
        if music_queue:
            def next_song(error):
                music_queues[guild].pop(0)
                mq = music_queues[guild]
                if mq:
                    # await bot.change_presence(activity=discord.Game('NAME OF VIDEO'))
                    voice_client.play(music_queue[0], after=next_song)
            voice_client.stop()  # maybe change to voice_client.source = music_queue[0]
            voice_client.play(music_queue[0], after=next_song)
            # await bot.change_presence(activity=discord.Game('NAME OF VIDEO'))


@bot.command(aliases=['back'])
async def previous(ctx):
    pass


@bot.command()
async def pause(ctx):
    voice_client: discord.VoiceClient = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice_client.is_paused():
        voice_client.resume()
    else:
        voice_client.pause()


@bot.command()
async def resume(ctx):
    voice_client: discord.VoiceClient = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice_client:
        if voice_client.is_paused():
            voice_client.resume()
        else:
            voice_client.pause()


@bot.command(aliases=['desummon', 'disconnect', 'unsummon', 'dismiss'])
async def leave(ctx):
    # clear query
    music_queues[ctx.guild] = []
    voice_client: discord.VoiceClient = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice_client:
        await voice_client.disconnect()


@bot.command()
async def stop(ctx):
    voice_client: discord.VoiceClient = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice_client:
        if voice_client.is_playing():
            guild = ctx.guild
            music_queues[guild].pop(0)
            voice_client.stop()


@bot.command()
async def volume(ctx):
    voice_client: discord.VoiceClient = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    # if voice_client:
    #     amount = ctx.message.content[8:]
    #     voice_client.volume

    # discord.PCMVolumeTransformer
    # https://discordpy.readthedocs.io/en/rewrite/api.html#discord.PCMVolumeTransformer


bot.run(os.environ['discord'])
