import tictactoe
from funcs import *
from helpMsg import help_message
import time
import asyncio
from datetime import datetime

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

client = discord.Client()

# *** CONSTANTS AND DECLARATIONS ***


# TODO: USE os.environ
invitation_code = os.environ['invitation_code']
ttt_round = 0
# numbertostr = {0: 'zero', 1: 'one', 2: 'two', 3: 'three', 4: 'four', 5: 'five'}
playersingame = []
tictactoe_data: dict = {}
timers = [['[Beta]Tic-Tac-Toe(!ttt)', 0], ['[Alpha]Shift(!shift)', 0]]


@client.event
async def on_ready():
    await client.change_presence(game=discord.Game(name='Prison Break'))


@client.event
async def on_member_join(member):
    server = member.server
    msg = f'Welcome inmate {member.mention} to the {server.name} server!'
    await client.send_message(member, 'Welcome to the SupaSpicy Server, here are my functions\n'+help_message)
    await client.send_message(server, msg)


@client.event
async def on_message(message):
    global ttt_round, playersingame, timers, tictactoe_data
    author = message.author
    user_msg = message.content
    # if message.author == client.user: return  # checks if the bot is replying to itself
    if str(author) != 'El Chapo#2608': update_networth(author)
    if user_msg.lower() == '!shop' or user_msg.lower() == '!math' or user_msg.lower() == '!eval':
        await client.send_message(message.channel, 'This command is in development!')
    if user_msg.startswith('!create_role ') and str(author.top_role) == 'Admin':
        server = message.server
        rolename = user_msg[13:]
        await client.create_role(server, name=rolename)
        await client.send_message(message.channel, f'Role {rolename} created')
    elif user_msg.startswith('!delete_channel ') and str(author.top_role) == 'Admin':
        channel = user_msg[16:]
        server = message.server
        if user_msg.count(', ') > 0:
            channels = channel.split(', ')
            for channel in channels:
                channel = discord.utils.get(client.get_all_channels(), server__name=str(server), name=channel)
                await client.delete_channel(channel)
        else:
            channel = discord.utils.get(client.get_all_channels(), server__name=str(server), name=channel)
            await client.delete_channel(channel)
    elif user_msg.startswith('!add_role ') and str(author.top_role) == 'Admin':
        mark = user_msg.index(' ')
        server = message.server
        rolename = user_msg[mark + 2:]
        role = discord.utils.get(server.roles, name=rolename)
        member = user_msg[12:mark-1]
        member = server.get_member(member)
        await client.add_roles(member, role)
    elif user_msg == '!balance' or user_msg == '!bal':
        await client.send_message(message.channel, check_networth(author))
        # counter = 0  # checks how many messages you have
        # tmp = await client.send_message(message.channel, 'Calculating Net Worth ...')
        # async for log in client.logs_from(message.channel, limit=1000000):
        #     if log.author == message.author: counter += 1
        # await client.edit_message(tmp, 'You have ${}'.format(counter))
        # await client.send_message(message.channel, 'Not as rich as me')
    elif user_msg.startswith('!test') and str(message.channel) == 'bot_testing':
        # async for x in client.logs_from(message.channel, limit=2):
        #     print(x.timestamp)
        await client.send_message(message.channel, 'TEST\nI DID SOMETHING')
    elif user_msg.startswith('!sleep') and str(message.author.top_role) == 'Admin':
        try: secs = int(user_msg[7:])
        except ValueError: secs = 5
        print(f'Sleeping for {secs} seconds')
        await asyncio.sleep(secs)
        await client.send_message(message.channel, 'Done sleeping')
    elif user_msg.startswith('!RUN'): await client.send_message(message.channel, 'Haha you have humour')
    elif user_msg.lower().startswith('!run'): await client.send_message(message.channel, 'N o t  h y p e  e n o u g h')
    elif user_msg.startswith('!yt '):
        msg = youtubesearch(user_msg)
        await client.send_message(message.channel, msg)
    elif user_msg.startswith('!youtube '):
        msg = youtubesearch(user_msg)
        await client.send_message(message.channel, msg)
    elif user_msg.lower().startswith('!gettweet '):
        msg = discord_get_tweet_from(user_msg[10:])
        await client.send_message(message.channel, msg)
        # TODO: add --integer to define how many statuses, use regex
        # TODO: add a clamp (3 for this 10 for the next) so nobody can abuse the system
    elif user_msg.lower().startswith('!twitter '):
        msg = discord_get_tweet_from(user_msg[9:])
        await client.send_message(message.channel, msg)
    elif user_msg.startswith('!searchuser '):
        text = user_msg[12:]
        msg = discord_search_twitter_user(text)
        await client.send_message(message.channel, msg)
    # search_users()
    elif user_msg.startswith('!thank'):
        await client.send_message(message.channel, f"You're welcome {author.mention}")
    elif user_msg.startswith('!clear'):
        server = message.channel.server
        moderator = discord.utils.get(server.roles, name='Moderator')
        if message.author.top_role >= moderator:
            await client.send_message(message.channel, 'Clearing messages...')
            number = 3
            if user_msg[7:].isnumeric():  # len(user_msg) > 7 and
                if int(user_msg[7:]) > 98: number = 100 - int(user_msg[7:])
                number += int(user_msg[7:]) - 1
            msg = []
            async for m in client.logs_from(message.channel, limit=number):
                date = m.timestamp
                if (datetime.now() - date).days > 14:  # if older than 14: delete else add onto msg list
                    await client.delete_message(m)
                    # await asyncio.sleep(0.1)
                else: msg.append(m)
            await client.delete_messages(msg)
    elif user_msg.startswith('!eval ') and str(
            message.author.top_role) == 'Admin':
        eval(user_msg[6:])
    elif user_msg.startswith('!invitecode') or user_msg.startswith('!invite') or user_msg.startswith('!invitelink'):
        await client.send_message(message.channel, discord.Invite(channel=message.channel, code=invitation_code).url)
    # TODO: Music command
    # TODO: elif user_msg.startswith('!music '):
    # TODO: BAN HAMMER
    # elif user_msg.startswith('!music'):
    #     server = message.channel.server
    #     # channel = discord.utils.get(client.get_all_channels(), server__name=str(server), name=channel)
    #     channel = discord.utils.get(server.channels, name='music', type=discord.ChannelType.voice)
    #     await client.join_voice_channel(channel)
    elif user_msg.lower() == '!games':
        msg = 'We have:'
        for timer in timers:
            t = round(time.time()-timer[1])
            if t > 120: msg += f'\n{timer[0]}  `open`'
            else: msg += f'\n{timer[0]}  `{120-t} seconds until free`'
        await client.send_message(message.channel, msg)
    elif user_msg.lower().startswith('!ttt'):
        # TODO: Make tic tac toe lobby's so that when a player starts a game in a lobby,
        #  only they are allowed to send messages to the channel
        # print(message.author.top_role.is_everyone) checks if role is @everyone
        if time.time() - timers[0][1] < 120:
            await client.send_message(message.channel, 'There is another tic-tac-toe game in progress')
        else:
            msg = 'You have started a Tic-Tac-Toe game\nGame can end after 2 minutes of ' \
                  'inactivity or if you do !end\nWould you like to go first?'  # Removed '(y/n)'
            await client.send_message(message.channel, msg)
            ttt_round = 0
            playersingame.clear()  # TODO: DELETE ANY DICTIONARY ENTRIES OF PLAYERS THAT AREN'T IN GAME
            tictactoe_data[author] = {'username': author, 'comp_moves': [], 'user_moves': [],
                                      'danger': None, 'danger2': None, 'game_over': False}
            playersingame.append(author)
            timers[0][1] = time.time()
            user_msg, in_game, game_channel = None, True, message.channel

            # TODO: Change the parameter name
            def check_yn(response_msg):
                correct_channel = response_msg.channel == game_channel
                response_msg = response_msg.content.lower()
                bool_value = response_msg == 'y' or response_msg == 'n' or response_msg == '!end'
                bool_value = bool_value or response_msg == 'yes' or response_msg == 'no'
                return bool_value and correct_channel

            def check_digit(response_msg):
                correct_channel = response_msg.channel == game_channel
                response_msg = response_msg.content
                return (response_msg.isdigit() or response_msg.lower() == '!end') and correct_channel

            while user_msg is None and in_game:
                if time.time() - timers[0][1] > 120 or not in_game: break
                user_msg = await client.wait_for_message(timeout=120, author=message.author, check=check_yn)
                if user_msg is not None:
                    user_msg = user_msg.content.lower()
                    if user_msg == '!end':
                        in_game = False
                        timers[0][1] = 0
                        playersingame.remove(author)
                        await client.send_message(game_channel, 'You have ended your tic-tac-toe game')
                        continue
                    timers[0][1] = time.time()
                    ttt_round = 1
                    tempmsg = tictactoe.greeting(tictactoe_data[author], user_msg)  # msg is y or n
                    await client.send_message(game_channel, tempmsg)
            while in_game:
                user_msg = await client.wait_for_message(timeout=120, author=message.author, check=check_digit)
                if user_msg is not None:
                    if user_msg.content.lower() == '!end':
                        in_game = False
                        timers[0][1] = 0
                        playersingame.remove(author)
                        await client.send_message(game_channel, 'You have ended your tic-tac-toe game')
                        continue
                    player_move = int(user_msg.content)
                    tempmsg, tictactoe_data[author] = tictactoe.validmove(player_move, tictactoe_data[author])
                    if not tempmsg:  # so ''
                        await client.send_message(game_channel, 'That was not a valid move')
                    else:
                        tempmsg += '\n'
                        tictactoe_data[author]['user_moves'].append(player_move)
                        tempt, win = tictactoe.tictactoe_move(ttt_round, tictactoe_data[author])
                        if tictactoe_data[author]['game_over']:
                            timers[0][1] = 0
                            # TODO: CLEAN ALL OF THIS UP
                            playersingame.remove(author)
                            in_game = False
                            if ttt_round == 5: await client.send_message(user_msg.channel, f'Your Move{tempmsg+tempt}')
                            else: await client.send_message(game_channel, f'Your Move{tempmsg}My Move{tempt}')
                        else:  # TODO: rich embed???
                            await client.send_message(game_channel, f'Your Move{tempmsg}My Move{tempt}\nEnter your '
                                                                    f'move (#)')
                            timers[0][1] = time.time()
                        ttt_round += 1
    elif user_msg.lower() == '!shift':
        await client.send_message(message.channel, 'https://elibroftw.itch.io/shift')
    elif user_msg.lower() == '!help':
        # TODO: ADD !help function that sends bot commands to the author that send the message
        await client.send_message(author, help_message)


client.run(os.environ['discord'])
