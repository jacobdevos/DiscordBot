import os
import sqlite3
from sqlite3 import Error

import discord
import requests

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
    elif message.content.lower().startswith('register'):
        msgs = message.content.split()
        if len(msgs) == 2 and "#" not in msgs[1]:
            overwatch_dictionary[message.author.name] = msgs[1]
            await message.channel.send('Registration complete.')
        else:
            await message.channel.send(
                'Registration failed please type "register <Battle Tag>". Replace the "#" character with a "-".')

@client.event
async def on_member_join(member):
    await member.guild.text_channels[0].send('Hello {}!'.format(member.display_name))


def format_login_response(name, stats):
    output = "Welcome back {} [Battle.net Tag {}]. \nYour top heroes this season are:\n".format(name, stats["name"])
    top_heroes = stats["competitiveStats"]["topHeroes"]
    for x in top_heroes:
        output += "\t\t{}: Win percentage: {} | games won: {} | time played: {}\n".format(x.capitalize(),
                                                                                          top_heroes[x][
                                                                                              "winPercentage"],
                                                                                          top_heroes[x]["gamesWon"],
                                                                                          top_heroes[x]["timePlayed"])

    return output


@client.event
async def on_voice_state_update(member, before, after):
    text_channel = member.guild.text_channels[0]
    if (
            before.channel is None or before.channel.name != "General") and after.channel is not None and after.channel.name == "General":
        if member.name not in overwatch_dictionary:
            await text_channel.send('Hello {}'.format(member.display_name))
        else:

            response = requests.get(
                'https://ow-api.com/v1/stats/pc/us/{}/complete'.format(overwatch_dictionary[member.name]))
            if response.ok:
                await text_channel.send(format_login_response(member.name, response.json()))
            else:
                await text_channel.send("Couldn't get stats for user Battle.net user '{}'. Response {}".format(
                    overwatch_dictionary[member.name], response))

client.run(get_token())
