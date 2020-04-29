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
    await member.guild.text_channels[0].send('Hello {}!'.format(member.display_name))


def format_login_response(name, stats):
    output = "[Battle.net Tag {}]. \nYour top heroes this season are:\n".format(stats["name"])
    raw_top_heroes = stats["competitiveStats"]["topHeroes"]
    raw_top_hero_keys = get_sorted_hero_keys(raw_top_heroes)

    for raw_top_hero_key in raw_top_hero_keys:
        output += "\t\t{}: Win percentage: {} | Games won: {} | Time played: {}\n".format(raw_top_hero_key.capitalize(),
                                                                                          raw_top_heroes[
                                                                                              raw_top_hero_key][
                                                                                              "winPercentage"],
                                                                                          raw_top_heroes[
                                                                                              raw_top_hero_key][
                                                                                              "gamesWon"],
                                                                                          raw_top_heroes[
                                                                                              raw_top_hero_key][
                                                                                              "timePlayed"])

    return output


def get_sorted_hero_keys(raw_top_heroes):
    delete = [key for key in raw_top_heroes if int(raw_top_heroes[key]["gamesWon"]) == 0]
    for key in delete:
        del raw_top_heroes[key]

    print("pruned heroes list: {}".format(raw_top_heroes))
    hero_keys = raw_top_heroes.keys()
    hero_keys = sorted(hero_keys, key=lambda key: int(raw_top_heroes[key]["winPercentage"]))
    hero_keys.reverse()
    return hero_keys


@client.event
async def on_voice_state_update(member, before, after):
    text_channel = member.guild.text_channels[0]
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
