from flask import Flask
from threading import Thread
from requests import get
from time import sleep

app = Flask(__name__)


@app.route('/')
def home():
    return 'Bot is live'


def run():
    app.run(host='0.0.0.0', port=8080)


def get_urls():
    while True:
        for url in 'https://discordbot--elilopez.repl.co/', 'https://elijahlopez.herokuapp.com':
            get(url)
        sleep(1000)


def keep_alive():
    Thread(target=run).start()
    Thread(target=get_urls).start()
