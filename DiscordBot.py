import os

import discord
import requests
import pprint

client = discord.Client()
overwatch_dictionary = {}

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
        if isinstance(message.author, discord.member.Member):
            await message.channel.send('Hello {}!'.format(message.author.display_name))
        else:
            await message.channel.send('Hello {}!'.format(message.author))
    elif message.content.startswith('register'):
        msgs = message.content.split()
        if len(msgs) == 2:
            overwatch_dictionary[message.author.name] = msgs[1]

@client.event
async def on_member_join(member):
    await member.guild.text_channels[0].send('Hello {}!'.format(member.display_name))


@client.event
async def on_voice_state_update(member, before, after):
    if before.channel is None or (before.channel.name != "General" and after.channel.name == "General"):
        text_channel = member.guild.text_channels[0]
        await text_channel.send('Hello {}'.format(member.display_name))
        print(member.name)
        print(overwatch_dictionary)
        if member.name in overwatch_dictionary:
            response = requests.get(
                'https://ow-api.com/v1/stats/pc/us/{}/profile'.format(overwatch_dictionary[member.name]))
            if response.ok:
                string_response = response.json()['competitiveStats']
                await text_channel.send('Stats {}'.format(string_response))
            else:
                await text_channel.send("Couldn't get stats for user Battle.net user '{}'. Response {}".format(
                    overwatch_dictionary[member.name], response))


client.run(get_token())



