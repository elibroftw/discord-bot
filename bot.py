import time
from datetime import datetime

from discord.ext import commands
from funcs import *
import tictactoe
import asyncio
import os

bot = commands.Bot(command_prefix="!")
bot.command()
invitation_code = os.environ['INVITATION_CODE']
ttt_round = 0

players_in_game = []
tic_tac_toe_data: dict = {}
timers = [['[Beta]Tic-Tac-Toe(!ttt)', 0], ['[Alpha]Shift(!shift)', 0]]
with open('help.txt') as f: help_message = f.read()


@bot.event
async def on_ready():
    await bot.change_presence(game=discord.Game(name='Prison Break'))


@bot.event
async def on_member_join(member):
    server = member.server
    msg = f'Welcome inmate {member.mention} to the {server.name} server!\n'
    msg += 'Use !help for my functions'
    await bot.send_message(server, msg)


@bot.event
async def on_message(message):
    author = message.author
    if str(author) != 'El Chapo#2608': update_networth(str(author))
    if author == bot.user: print('am same user')
    if message.content.startswith('!RUN'): await bot.say('I GOT EXTRADITED! :(')
    elif message.content.lower().startswith('!run'):
        await bot.say('N o t  h y p e  e n o u g h')
    elif message.content.lower().startswith('!help'):
        await bot.send_message(message.author, help_message)
    await bot.process_commands(message)


@bot.command(pass_context=True)
async def hi(ctx):
    await bot.say("Hey there" + " " + ctx.message.author.name + "!")


@bot.command(pass_context=True)
async def test(ctx):
    if str(ctx.channel) == 'bot_testing':
        await bot.say('TEST\nI DID SOMETHING')


@bot.command(pass_context=True)
async def sleep(ctx):
    if ctx.message.author.top_role == 'Admin':
        try: secs = int(ctx.message.content[7:])
        except ValueError: secs = 5
        print(f'Sleeping for {secs} seconds')
        await asyncio.sleep(secs)
        await bot.say('Done sleeping')


@bot.command(pass_context=True, aliases=['bal'])
async def balance(ctx):
    await bot.say(check_networth(str(ctx.message.author)))


@bot.command(pass_context=True, aliases=['createrole'])
async def create_role(ctx):
    if str(ctx.message.author.top_role) == 'Admin':
        server = ctx.message.server
        role_name = ctx.message.content[13:]
        bot.create_role(server, name=role_name)  # TODO: Should I delete the await???
        await bot.say(f'Role {role_name} created')
        print(f'{ctx.message.author}created role {role_name}')


# TODO: delete_roll
@bot.command(pass_context=True)
async def add_role(ctx):
    if str(ctx.message.author.top_role) == 'Admin':
        mark = ctx.message.content.index(' ')
        server = ctx.message.server
        role_name = ctx.message.content[mark + 2:]
        role = discord.utils.get(server.roles, name=role_name)
        member = ctx.message.content[12:mark - 1]
        member = server.get_member(member)
        await bot.add_roles(member, role)
        print(f'{ctx.message.author} gave {member} role {role_name}')


@bot.command(pass_context=True)
async def delete_channel(ctx):
    if str(ctx.message.author.top_role) == 'Admin':
        channel = ctx.message.content[16:]
        server = ctx.message.server
        if ctx.message.content.count(', ') > 0:
            channels = channel.split(', ')
            for channel in channels:
                channel = discord.utils.get(bot.get_all_channels(), server__name=str(server), name=channel)
                await bot.delete_channel(channel)
            print(f'{ctx.message.author} deleted channels: {channels}')
        else:
            channel = discord.utils.get(bot.get_all_channels(), server__name=str(server), name=channel)
            await bot.delete_channel(channel)
            print(f'{ctx.message.author} deleted channel {channel}')


@bot.command(pass_context=True, aliases=['yt'])
async def youtube(ctx):
    try:
        text = ctx.message.content[ctx.message.content.index(' ') + 1:]
        await bot.say(youtube_search(text))
    except ValueError:
        await bot.say('ERROR: No search parameter given')


@bot.command(pass_context=True, aliases=['gettweet', 'get_tweet'])
async def twitter(ctx):
    # TODO: add --integer to define how many statuses, use regex
    # TODO: add a clamp (3 for this 10 for the next) so nobody can abuse the system
    msg = discord_get_tweet_from(ctx.message.content[ctx.message.content.index(' ')+1:])  # TODO: execpt ValueError
    await bot.say(msg)


@bot.command(pass_context=True, aliases=['searchuser' 'search_user'])
async def search_twitter_user(ctx):
    text = ctx.message.content[ctx.message.content.index(' ')+1:]  # TODO: except ValueError
    bot_message = discord_search_twitter_user(text)
    await bot.say(bot_message)
# search_users()


@bot.command(pass_context=True)
async def thank(ctx):
    await bot.say(f"You're welcome {ctx.message.author.mention}")


@bot.command(pass_context=True)
async def clear(ctx):
    server = ctx.message.channel.server
    moderator = discord.utils.get(server.roles, name='Moderator')
    if ctx.message.author.top_role >= moderator:
        await bot.say('Clearing messages...')
        await bot.change_presence(game=discord.Game(name='Clearing messages...'))
        number = 3
        if ctx.message.content[7:].isnumeric():  # len(user_msg) > 7 and
            if int(ctx.message.content[7:]) > 98: number = 100 - int(ctx.message.content[7:])
            number += int(ctx.message.content[7:]) - 1
        msg = []
        async for m in bot.logs_from(ctx.message.channel, limit=number):
            date = m.timestamp
            if (datetime.now() - date).days > 14:  # if older than 14: delete else add onto msg list
                await bot.delete_message(m)
            else: msg.append(m)
        await bot.delete_messages(msg)
    await bot.change_presence(game=discord.Game(name='Prison Break'))
    print(f'{ctx.message.author} cleared {number-2} message(s)')


@bot.command(aliases=['shop', 'math', 'music', 'ban'])
async def todo():  # TODO
    await bot.say('This command still needs to be implemented!')


@bot.command(pass_context=True, aliases=['eval'])
async def _eval(ctx):
    if str(ctx.message.author.top_role) == 'Admin':
        await bot.say(str(eval(ctx.message.content[6:])))
        print(f'{ctx.message.author} used eval')


@bot.command(pass_context=True, aliases=['invite', 'invitecode', 'invite_link', 'invitelink'])
async def invite_code(ctx):  # Todo: maybe get rid of channel=
    await bot.say(discord.Invite(channel=ctx.message.channel, code=invitation_code).url)


@bot.command()
async def games():
    msg = 'We have:'
    for timer in timers:
        t = round(time.time() - timer[1])
        if t > 120:
            msg += f'\n{timer[0]}  `open`'
        else:
            msg += f'\n{timer[0]}  `{120-t} seconds until free`'
    await bot.say(msg)


@bot.command(pass_context=True)
async def ttt(ctx):
    global ttt_round, players_in_game, tic_tac_toe_data, timers
    author = str(ctx.message.author)
    # TODO: Make tic tac toe lobby's so that when a player starts a game in a lobby,
    #  only they are allowed to send messages to the channel
    # print(message.author.top_role.is_everyone) checks if role is @everyone
    if time.time() - timers[0][1] < 120:
        await bot.say('There is another tic-tac-toe game in progress')
    else:
        msg = 'You have started a Tic-Tac-Toe game\nGame can end after 2 minutes of ' \
              'inactivity or if you do !end\nWould you like to go first?'  # Removed '(y/n)'
        await bot.say(msg)
        ttt_round = 0
        players_in_game.clear()  # TODO: DELETE ANY DICTIONARY ENTRIES OF PLAYERS THAT AREN'T IN GAME
        tic_tac_toe_data[author] = {'username': author, 'comp_moves': [], 'user_moves': [], 'danger': None,
                                    'danger2': None, 'game_over': False}
        players_in_game.append(author)
        timers[0][1] = time.time()
        user_msg, in_game, game_channel = None, True, ctx.message.channel

        # TODO: Change the parameter name
        def check_yn(response_msg):
            correct_channel = response_msg.channel == game_channel
            response_msg = response_msg.content.lower()
            bool_value = response_msg in ('y', 'yes', 'no', 'n', '!end')
            return bool_value and correct_channel

        def check_digit(response_msg):
            correct_channel = response_msg.channel == game_channel
            response_msg = response_msg.content
            return (response_msg.isdigit() or response_msg.lower() == '!end') and correct_channel

        while user_msg is None and in_game:
            if time.time() - timers[0][1] > 120 or not in_game: break
            user_msg = await bot.wait_for_message(timeout=120, author=ctx.message.author, check=check_yn)
            if user_msg is not None:
                user_msg = user_msg.content.lower()
                if user_msg == '!end':
                    in_game = False
                    timers[0][1] = 0
                    players_in_game.remove(author)
                    await bot.send_message(game_channel, 'You have ended your tic-tac-toe game')
                    continue
                timers[0][1] = time.time()
                ttt_round = 1
                temp_msg = tictactoe.greeting(tic_tac_toe_data[author], user_msg)  # msg is y or n
                await bot.send_message(game_channel, temp_msg)
        while in_game:
            user_msg = await bot.wait_for_message(timeout=120, author=ctx.message.author, check=check_digit)
            if user_msg is not None:
                if user_msg.content.lower() == '!end':
                    in_game = False
                    timers[0][1] = 0
                    players_in_game.remove(author)
                    await bot.send_message(game_channel, 'You have ended your tic-tac-toe game')
                    continue
                player_move = int(user_msg.content)
                temp_msg, tic_tac_toe_data[author] = tictactoe.valid_move(player_move, tic_tac_toe_data[author])
                if not temp_msg:  # so ''
                    await bot.send_message(game_channel, 'That was not a valid move')
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
                            await bot.say(f'Your Move{temp_msg+tempt}')
                        else:
                            await bot.say(f'Your Move{temp_msg}My Move{tempt}')
                    else:  # TODO: rich embed???
                        await bot.say(f'Your Move{temp_msg}My Move{tempt}\nEnter your move (#)')
                        timers[0][1] = time.time()
                    ttt_round += 1


@bot.command()
async def shift():
    await bot.say('https://elibroftw.itch.io/shift')


# @bot.command(pass_context=True)
# async def _help(ctx):
#     await bot.send_message(ctx.message.author, help_message)


# @bot.command(pass_context=True)
# async def music(ctx):
#     server = ctx.message.channel.server
#  #     channel = discord.utils.get(bot.get_all_channels(), server__name=str(server), name=channel)
    # channel = discord.utils.get(server.channels, name='music', type=discord.ChannelType.voice)
    # await bot.join_voice_channel(channel)


bot.run(os.environ['discord'])