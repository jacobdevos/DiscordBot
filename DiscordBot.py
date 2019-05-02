import os

import discord
import requests

import MongoConstants
import MongoDb

client = discord.Client()
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
    lowercase_msg = message.content.lower()
    if lowercase_msg.startswith('register'):
        await register_user(message)
    elif lowercase_msg.startswith('unregister'):
        await unregister_user(message)


async def unregister_user(message):
    msgs = message.content.split()
    if len(msgs) == 2 and "#" not in msgs[1]:
        storage.remove(
            {MongoConstants.DISCORD_NAME_FIELD: message.author.name, MongoConstants.BNET_ID_FIELD: msgs[1]})
        await message.channel.send('Unregistered.')
    elif len(msgs) == 1:
        storage.remove({MongoConstants.DISCORD_NAME_FIELD: message.author.name})
        await message.channel.send('Unregistered.')


async def register_user(message):
    msgs = message.content.split()
    if len(msgs) == 2 and "#" not in msgs[1]:
        document = {MongoConstants.DISCORD_NAME_FIELD: message.author.name, MongoConstants.BNET_ID_FIELD: msgs[1]}
        if not storage.find_one(document):
            storage.insert_one(document)
        await message.channel.send('Registration complete.')

    else:
        await message.channel.send(
            'Registration failed please type "register <Battle Tag>". Replace the "#" character with a "-".')


@client.event
async def on_member_join(member):
    await get_text_channel(member).send('Hello {}!'.format(member.display_name))


async def get_text_channel(member):
    return member.guild.text_channels[0]


def format_login_response(name, stats):
    output = "[Battle.net Tag {}]. \nYour top heroes this season are:\n".format(stats["name"])
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
    text_channel = get_text_channel(member)
    if (
            before.channel is None or before.channel.name != "General") and after.channel is not None and after.channel.name == "General":
        result_set = get_battle_net_ids(member.name, storage)
        if result_set.count() == 0:
            await text_channel.send('Hello {}'.format(member.display_name))
        else:
            await text_channel.send("Welcome back {}.".format(member.name))
            for result in result_set:
                response = requests.get(
                    'https://ow-api.com/v1/stats/pc/us/{}/complete'.format(result[MongoConstants.BNET_ID_FIELD]))
                if response.ok:
                    await text_channel.send(format_login_response(member.name, response.json()))
                else:
                    await text_channel.send("Couldn't get stats for user Battle.net user '{}'. Response {}".format(
                        result, response))


def get_battle_net_ids(discordName, table):
    return table.find({MongoConstants.DISCORD_NAME_FIELD: discordName})


client.run(get_token())
