# music-presence/discord-moderation-bot

Simple bot for scoped moderation commands.

## Features

- Delete all messages of a user within a certain time frame and quarantine them with `/moddelmsg`. This only allows moderators to delete recent messages instead of having to give permission to freely delete any messages in the server
- Restrict access of quarantined users by removing and assigning a dedicated role with custom permissions
- Get notified in a dedicated channel of any new moderation events
- Unquarantine members again with `/modunquarantine`
- Automatically delete messages that match custom regular expressions

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
