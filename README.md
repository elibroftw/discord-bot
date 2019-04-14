# Discord Bot
A discord bot (called El Chapo) I made using the discord.py module and is hosted on Repl.it (for now).

# Features
For a list of commands view bot.py

- Uses rewritten version (old_bot.py is the repl.it version)
- Tic-Tac-Toe (Impossible difficult setting, there is a bug)
- Youtube search
- Plays music (Working but adding features)
    - Summon (!summon, !play <query/youtube_url>)
    - Play or Add to queue (!play, !p)
    - Play next (adds the song to play right after, will rework this later !pn, !play_next)
    - Pause/Resume (!pause, !p, !resume)
    - Skip (!skip, !next, !s, !n)
    - Back (!back, !b, !previous, !prev)
    - Fast-forward (!ff <seconds=5>)
    - Rewind (!rw <seconds=5>)
    - Stop (!stop, !s, !end)
    - Autoplay (adds to the music queue when the queue is empty or has only the playing track; !auto_play, !ap)
    - View Upcoming tracks (!q)
    - View Recently Played (!dq)
    - Set volume (!volume, !v, prints volume if no int given)
        - !v 100  # this will set volume to 100/100
        - !v +20  # increase volume by 20
        - !v -20  # decrease volume by 20
        - !v +  # increase volume by 10
        - !v -  # decrease volume by 10
    - Leave (!leave, !disconnect, !unsummon, !desummon, !dismiss)
    

- Twitter search (going to rework this)
- Virtual currency (not done yet)
- Admin uses
    - clearing (!clear int)
    - Can clear up to 100 messages in chat (needs Admin obviously)
    - banning (!ban nick/username)
    - get creation date of user (!created_at, !create_date, query is optional)

# Future
- Set and get invite codes (currently only gets my invite code)
- repeat mode for music

Invitation [url](https://discordapp.com/oauth2/authorize?&client_id=282274755426385921&scope=bot&permissions=8).
DISCLAIMER: This bot has not been tested to be used on multiple servers
