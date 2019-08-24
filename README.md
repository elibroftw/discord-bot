# Discord Bot (Works best self hosted)
A discord bot (called El Chapo) I made using the discord.py module and is self hosted. This bot is tailored towards being a custom bot for your server rather than one bot for a bunch of servers (music system is not meant to be used on more than the owners server). I am not liable for any illegal activities one conducts using my bot or my code.

# Features
For a list of commands view bot.py

- Uses rewritten version (old_bot.py is the repl.it version)
- Tic-Tac-Toe (Difficulty set to impossible)
- Youtube search
- Plays music (Working but adding features)
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
    - Remove song (!rm index)
    - Move song (!move <from> <to>)
    - Shuffle (!shuffle)
    - Clear queue (!cq)
    - Play from Playlist (!pp <playlist_name/url>)  // url untested
    - Save to playlist (!pp <playlist_name> <--s for shuffle>)
    - View playlist (!vp <playlist_name/url>)  // use --2/3 for different scopes
    - Load playlist (!lp <playlist_name/url>)  // adds songs to current queue
    - Delete playlist (!dp <playlist_name>)
    - Search playlist (!sp <playlist_name>)
        - All playlists can be used by other people using the bot
    - Set volume (!volume, !v)  // prints volume if no int given
        - !v 100  # this will set volume to 100/100
        - !v +20  # increase volume by 20
        - !v -20  # decrease volume by 20
        - !v +  # increase volume by 10
        - !v -  # decrease volume by 10
    - Leave Voice chat (!leave, !disconnect, !unsummon, !desummon, !dismiss)
    

- Twitter search (going to rework this)
- Virtual currency (not done yet)
- Admin uses
    - clearing (!clear int)
    - Can clear up to 100 messages in chat (needs Admin obviously)
    - Banning (!ban nick/username)
    - Get creation date of user (!created_at, !create_date, query is optional)

# Future
- Set and get invite codes (currently only gets my invite code)
- report user for bot abuse

# Installation
- Clone repoistory
- Have [MongoDB](https://www.mongodb.com/what-is-mongodb) installed
- Only tested on Windows
- pip install -r requirements.txt
- [Want to run on Windows boot?](https://medium.com/@elijahlopezz/python-and-background-tasks-4f70b4a2efd8) (OUTDATED)

[Test the bot](https://discordapp.com/oauth2/authorize?&client_id=282274755426385921&scope=bot&permissions=8).
DISCLAIMER: This bot is constantly under development and is self hosted.
