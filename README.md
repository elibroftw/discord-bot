# Discord Bot (Works best self hosted)
A discord bot (called El Chapo) I made for my personal server.
Rather than having a sole purpose, this bot is aimed at doing all the tasks I want it to do. I made it for a singular
server so it may not work for multiple servers (regarding the music playing features).

# Features
For more info, view [bot.py](../master/bot.py)

- Admin uses
    - Clear chat (!clear int)
        - Can clear up to 100 messages in chat (at the moment)
    - Ban (!ban nick/username)
    - Get creation date of user (!created_at <user=YOU>)
- Anonymous Messaging Service
    - Send a dm to a user (!dm <user/nick> <message>) // send it to the bot
    - Reply to a dm (!re <thread_id> <message>)
    - Enable anonymous messages (!enable)
    - Disable anonymous messages (!disable)
    - Toggle status (!anontoggle, !anon)  // Future replacement
    - See if you are opted in or out of the messages (!anonstatus)
- Listen to Music
    - Summon (!summon, !play <query/youtube_url>)
    - Play or Add to queue (!play, !p)
    - Play next (adds the song to play right after, will rework this later !pn, !play_next)
    - Pause/Resume (!pause, !p, !resume)
    - Skip (!skip, !next, !n)
    - Go Back (!back, !b, !previous, !prev)
    - Fast forward (!ff <seconds=5>)
    - Rewind (!rw <seconds=5>)
    - Skip to (!st <seconds>)
    - Stop (!stop, !s, !end)
    - Autoplay (adds to the music queue when the queue is empty or has only the playing track; !auto_play, !ap)
    - Repeat Options (!repeat, !repeat_all)
    - View Now Playing (!np)
    - View Upcoming tracks (!q)
    - View Recently Played (!dq)
    - Remove song (!rm <index>)
    - Move song (!move <from> <to>)
    - Shuffle (!shuffle)
    - Clear queue (!cq)
    - Play from Playlist (!pp <playlist_name/url> [--s])  // use --s for shuffle
    - Save to playlist (!sa <playlist_name>)
    - View playlist (!vp <playlist_name/url>)  // use --2/3 for different scopes
    - Search playlists (!sp [--page 1] [--query query])  // alphabetically sorted
    - Load playlist (!lp <playlist_name/url>)  // adds songs to current queue
    - Delete playlist (!dp <playlist_name>)
    - Set volume (!volume, !v)  // prints volume if no int given
        - !v 100  # this will set volume to 100/100
        - !v +20  # increase volume by 20
        - !v -20  # decrease volume by 20
        - !v +  # increase volume by 10
        - !v -  # decrease volume by 10
    - Leave Voice chat (!leave, !disconnect, !unsummon, !desummon, !dismiss)
- Investing Tools
    - Get the price of a stock (!stock <ticker>)
    - Add shares to portfolio (!buy <ticker> <cost_per_share> <shares> <commission_fee=0>)
    - Remove shares from portfolio (!sell <ticker> <price_per_share> <shares> <commission_fee=0>)
    - View your portfolio (!holdings <to_dm=False>)
    - Get a copy of your portfolio/transactions (!dlholdings <to_dm=True>)
    - Get top movers (!movers <market='ALL'> <of='day'> <show=5>)
    - Get top winners (!gainers <market='ALL'> <of='day'> <show=5>)
    - Get top losers (!losers <market='ALL'> <of='day'> <show=5>)
- Games (!games)
    - Tic-Tac-Toe (Difficulty is impossible)
        - Use !ttt to start a match
    - Shift (!shift)
        - A game my friend and I made (sends a link to the chat)
- Youtube Search
    - Search for a video (!yt, !youtube)
    - See "Listen to Music" for playing songs from YouTube
- Twitter (DISABLED; Rework pending)
    - Get the latest tweet from a user (!twitter <user>)
    - Search for a twitter user (!tu_search <query>)

# Future
- Set and get invite codes (currently only gets my invite code)
- report user for bot abuse

# Installation
Note that this bot has only been tested on Windows
1. Clone the repository
2. Have [MongoDB Community 4.2.X](https://www.mongodb.com/download-center/community) installed
3. Have [FFmpeg](https://www.ffmpeg.org/download.html) accessible in PATH
4. Do `pip install -r requirements.txt` in the terminal of the current directory
5. If you want to run on Windows boot, import and edit "Discord Bot.xml" in Task Scheduler OR
6. Click [here](https://medium.com/@elijahlopezz/python-and-background-tasks-4f70b4a2efd8) to start from scratch

[Test the bot yourself](https://discordapp.com/oauth2/authorize?&client_id=282274755426385921&scope=bot&permissions=8).
WARNING: bot is not always online
