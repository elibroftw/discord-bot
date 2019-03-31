import time
import os
from datetime import datetime

from discord.ext import commands
from helpers import *
from keep_alive import keep_alive
import tictactoe
import asyncio

bot = commands.Bot(command_prefix="!")
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
    await bot.change_presence(game=discord.Game(name='Prison Break'))


@bot.event
async def on_member_join(member):
    server = member.server
    msg = f'Welcome inmate {member.mention} to the {server.name} server!\n'
    # await bot.send_message(server, msg)
    msg += 'Use !help for my functions'
    await bot.send_message(member, msg)  # untested


@bot.event
async def on_message(message):
    author = message.author
    if author != bot.user: update_net_worth(str(author))
    if message.content.startswith('!RUN'):
        await bot.say(message.channel, 'I GOT EXTRADITED! :(')
    elif message.content.lower().startswith('!run'):
        await bot.say(message.channel, 'N o t  h y p e  e n o u g h')
    elif message.content.lower().startswith('!help'):
        await bot.send_message(message.author, help_message)
        await bot.delete_message(message)
    else:
        await bot.process_commands(message)


@bot.command(pass_context=True)
async def hi(ctx):
    await bot.say("Hey there" + " " + ctx.message.author.name + "!")


@bot.command(pass_context=True)
async def test(ctx):
    if str(ctx.message.channel) == 'bot-testing':
        await bot.send_message(ctx.message.channel, 'TEST\nI DID SOMETHING')


@bot.command(pass_context=True)
async def sleep(ctx):
    if ctx.message.author.top_role == 'Admin':
        try:
            secs = int(ctx.message.content[7:])
        except ValueError:
            secs = 5
        print(f'Sleeping for {secs} seconds')
        await asyncio.sleep(secs)
        await bot.say('Done sleeping')


@bot.command(pass_context=True, aliases=['bal'])
async def balance(ctx):
    await bot.send_message(ctx.message.author, check_net_worth(str(ctx.message.author)))
    await bot.delete_message(ctx.message)


@bot.command(pass_context=True, aliases=['createrole'])
async def create_role(ctx):
    if str(ctx.message.author.top_role) == 'Admin':
        server = ctx.message.server
        role_name = ctx.message.content[13:]
        await bot.create_role(server, name=role_name)
        await bot.say(f'Role {role_name} created')
        print(f'{ctx.message.author} created role {role_name}')


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
    text = ctx.message.content[ctx.message.content.index(' ') + 1:]
    redirect = False
    msg = '\n[Name | Screen name]```'
    users = search_twitter_user(text)
    for name, screenName in users:
        msg += f'\n{name} | @{screenName}'
    if redirect:
        msg = "```Were you searching for a User?\nHere are some names:" + msg
    msg = '```' + msg
    await bot.say(msg)


@bot.command(pass_context=True, aliases=['searchuser' 'search_user'])
async def search_twitter_user(ctx):
    text = ctx.message.content[ctx.message.content.index(' ') + 1:]  # except ValueError
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
    print(ctx.message.author.top_role.position)  # .top_role is Admin
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
            else:
                msg.append(m)
        await bot.delete_messages(msg)
    await bot.change_presence(game=discord.Game(name='Prison Break'))
    print(f'{ctx.message.author} cleared {number-2} message(s)')


@bot.command(aliases=['shop', 'math', 'ban', 'remove_role', 'delete_role'])
async def todo():
    await bot.say('This command still needs to be implemented!')


@bot.command(pass_context=True, aliases=['eval'])
async def _eval(ctx):
    if str(ctx.message.author.top_role) == 'Admin':
        await bot.say(str(eval(ctx.message.content[6:])))
        print(f'{ctx.message.author} used eval')


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
    if time.time() - timers[0][1] < 120:
        await bot.say('There is another tic-tac-toe game in progress')
    else:
        msg = 'You have started a Tic-Tac-Toe game\nThe game will end after 2 minutes of' \
              'inactivity or if you enter !end\nWould you like to go first? [Y/n]'
        await bot.say(msg)
        ttt_round = 0
        players_in_game.clear()
        tic_tac_toe_data[author] = {'username': author, 'comp_moves': [], 'user_moves': [], 'danger': None,
                                    'danger2': None, 'game_over': False}
        players_in_game.append(author)
        timers[0][1] = time.time()
        user_msg, in_game, game_channel = None, True, ctx.message.channel

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
                        players_in_game.remove(author)
                        in_game = False
                        if ttt_round == 5:
                            await bot.say(f'Your Move{temp_msg+tempt}')
                        else:
                            await bot.say(f'Your Move{temp_msg}My Move{tempt}')
                    else:
                        await bot.say(f'Your Move{temp_msg}My Move{tempt}\nEnter your move (#)')
                        timers[0][1] = time.time()
                    ttt_round += 1


@bot.command()
async def shift():
    await bot.say('https://elibroftw.itch.io/shift')


# @bot.command(pass_context=True)
# async def _help(ctx):
#     await bot.send_message(ctx.message.author, help_message)


@bot.command(pass_context=True, aliases=['play_music'])
async def music(ctx):
    server = ctx.message.channel.server
    #  channel = discord.utils.get(bot.get_all_channels(), server__name=str(server), name=channel)
    channel = discord.utils.get(server.channels, name='music', type=discord.ChannelType.voice)
    await bot.join_voice_channel(channel)


@bot.command(pass_context=True)
async def play(ctx):
    pass
    # search_query = ctx.message[6:]


@bot.command(pass_context=True)
async def pause(ctx):
    pass
    # search_query = ctx.message[6:]


@bot.command(pass_context=True)
async def stop(ctx):
    pass
    # search_query = ctx.message[6:]

@bot.command(pass_context=True, aliases=['playnext'])
async def play_next(ctx):
    pass
    # search_query = ctx.message[6:]

@bot.command(pass_context=True)
async def queue(ctx):
    pass
    # search_query = ctx.message[6:]

@bot.command(pass_context=True)
async def skip(ctx):
    pass
    # search_query = ctx.message[6:]

@bot.command(pass_context=True)
async def restart(ctx):
    pass
    # search_query = ctx.message[6:]


@bot.command(pass_context=True)
async def loop(ctx):
    pass
    # search_query = ctx.message[6:]


keep_alive()
bot.run(os.environ['discord'])
