from flask import Flask, render_template
from waitress import serve
from threading import Thread

data = {
  "avatar": "https://cdn.discordapp.com/avatars/975814318199287898/7b3484aa1da5bc515bcad19c7fbacbab.png?size=1024",
  "guilds": 5,
  "invite": "https://discord.com/api/oauth2/authorize?client_id=975814318199287898&permissions=1101927573574&redirect_uri=https%3A%2F%2Fbban.raadsel.tech%2Finvited&scope=bot"
}


app = Flask(__name__)

@app.route('/')
def home():
    return render_template("index.html", data = data)

@app.route('/invited')
def invited():
    return render_template("invited.html", data = data)


def run():
  serve(app, host="0.0.0.0", port=8080)

def start():  
    t = Thread(target=run)
    t.start()