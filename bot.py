import time
from datetime import datetime
import discord
from discord.ext import commands
from funcs import *
from keep_alive import keep_alive
import tictactoe
import asyncio

bot = commands.Bot(command_prefix='!')
bot.command()
invitation_code = os.environ['INVITATION_CODE']
ttt_round = 0

players_in_game = []
tic_tac_toe_data: dict = {}
timers = [['[Beta]Tic-Tac-Toe(!ttt)', 0], ['[Alpha]Shift(!shift)', 0]]
# timers_2 = {'[Beta]Tic-Tac-Toe(!ttt)': 0, '[Alpha]Shift(!shift)': 0}
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
        await message.channnel.send('I GOT EXTRADITED! :(')
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
    if str(ctx.message.author.top_role) == 'Admin':
        server = ctx.message.server
        role_name = ctx.message.content[13:]
        guild: discord.guild = ctx.guild
        await guild.create_role(server, name=role_name)
        await ctx.send(f'Role {role_name} created')
        print(f'{ctx.message.author} created role {role_name}')


# TODO: delete_role
@bot.command()
async def add_role(ctx):
    if str(ctx.message.author.top_role) == 'Admin':
        mark = ctx.message.content.index(' ')
        guild = ctx.guild
        role_name = ctx.message.content[mark + 2:]
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
    channel: discord.TextChannel = ctx.message.channel
    guild = channel.guild
    moderator = discord.utils.get(guild.roles, name='Moderator')
    ctx.message.author.top_role: discord.Role  # .top_role is Admin
    print(ctx.message.author.top_role.position)
    if ctx.message.author.top_role >= moderator:
        await ctx.send('Clearing messages...')
        await bot.change_presence(activity=discord.Game('Clearing messages...'))
        number = 3
        if ctx.message.content[7:].isnumeric():  # len(user_msg) > 7 and
            if int(ctx.message.content[7:]) > 98: number = 100 - int(ctx.message.content[7:])
            number += int(ctx.message.content[7:]) - 1
        messages = []
        async for m in channel.history(limit=number):
            m: discord.Message
            date = m.created_at
            if (datetime.now() - date).days > 14:  # if older than 14: delete else add onto msg list
                await m.delete()
            else:
                messages.append(m)
        await channel.delete_messages(messages)
        print(f'{ctx.message.author} cleared {number - 2} message(s)')
    await bot.change_presence(activity=discord.Game('Prison Break'))


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


@bot.command()
async def summon(ctx):
    guild = ctx.message.channel.guild
    author: discord.Member = ctx.message.author
    if not author.voice:
        channel = discord.utils.get(guild.channels, name='music', type=discord.VoiceChannel)
    else:
        channel = author.voice.channel
    await channel.connect()


@bot.command()
async def play(ctx):
    voice_client: discord.VoiceClient = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    url_or_query = ctx.message.content[5:]
    if url_or_query:
        if url_or_query.startswith('https://'):
            pass
        else:  # query
            url = youtube_search(url_or_query)
            youtube_download(url)
            # download and the play


@bot.command(alias=['stop', 'unsummon', 'disconnect'])
async def leave(ctx):
    # clear query
    voice_client: discord.VoiceClient = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    await voice_client.disconnect()
    # voice_client.channel

keep_alive()
bot.run(os.environ['discord'])
