import os

import discord
import requests

import MongoDb

client = discord.Client()
overwatch_dictionary = {}
storage = MongoDb.get_discord_mongo_table()
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
            discord_user_key = message.author.name
            battlenet_id_value = msgs[1]
            overwatch_dictionary[discord_user_key] = battlenet_id_value
            document = {discord_user_key: battlenet_id_value}
            if not storage.find_one(document):
                storage.insert_one(document)
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
        output += "\t\t{}: Win percentage: {} | Games won: {} | Time played: {}\n".format(x.capitalize(),
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
        bnetids = get_battle_net_ids(member.name, storage)
        if bnetids.count() == 0:
            await text_channel.send('Hello {}'.format(member.display_name))
        else:
            for bnetid in bnetids:
                response = requests.get(
                    'https://ow-api.com/v1/stats/pc/us/{}/complete'.format(bnetid))
                if response.ok:
                    await text_channel.send(format_login_response(member.name, response.json()))
                else:
                    await text_channel.send("Couldn't get stats for user Battle.net user '{}'. Response {}".format(
                        bnetid, response))


def get_battle_net_ids(discordName, table):
    return table.find({'discordName': discordName})

client.run(get_token())
