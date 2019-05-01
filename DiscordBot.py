import os

import discord

client = discord.Client()


@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))


def get_token():
    return os.environ.get('APITOKEN', 'none')


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('$hello'):
        if 'Member' in type(message.author):
            print("made it")
            await message.channel.send('Hello {}!'.format(message.author.display_name))
        else:
            await message.channel.send('Hello {}!'.format(message.author))


client.run(get_token())
