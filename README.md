# music-presence/discord-moderation-bot

Simple bot for scoped moderation commands.

`moddelmsg` deletes messages only within a certain time frame.

## Setup

```sh
$ python3 -m venv venv
$ source venv/bin/activate
(venv) $ pip install -r requirements.txt
(venv) $ cp .env.example .env
# Add your bot token to .env
(venv) $ cp config.example.yaml config.yaml
# Configure each command
(venv) $ python bot.py
```

## Deploy

```sh
$ docker compose up -d --build
```
