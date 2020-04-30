import os

import discord
import requests

import MongoConstants
import MongoDb

client = discord.Client()
storage = MongoDb.get_discord_mongo_table()
bot_channels = [("JakesBotTest", "General"), ("JTMoney", "Broverwatch")]


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
        msgs = message.content.split()
        if len(msgs) == 2:
            discord_user_name = message.author.name
            battlenet_id = msgs[1]
            await register_user(discord_user_name, battlenet_id)
            await message.channel.send('Registration complete.')
        else:
            await message.channel.send(
                'Registration failed please type "register <Battle Tag>".')
    elif lowercase_msg.startswith('unregister'):
        msgs = message.content.split()
        if len(msgs) == 2:
            storage.remove(
                {MongoConstants.DISCORD_NAME_FIELD: message.author.name,
                 MongoConstants.BNET_ID_FIELD: msgs[1]})
            await message.channel.send('Unregistered.')
        elif len(msgs) == 1:
            storage.remove({MongoConstants.DISCORD_NAME_FIELD: message.author.name})
            await message.channel.send('Unregistered.')


async def register_user(discord_user_name, battle_net_id):
    document = {MongoConstants.DISCORD_NAME_FIELD: discord_user_name, MongoConstants.BNET_ID_FIELD: battle_net_id}
    if not storage.find_one(document):
        storage.insert_one(document)


@client.event
async def on_member_join(member):
    await member.guild.text_channels[0].send('Hello {}!'.format(member.display_name))


def format_login_response(stats, battle_net_tag):
    output = "[Battle.net Tag {}]. \nYour top 5 heroes this season are:\n".format(stats["name"])
    raw_top_heroes = stats["competitiveStats"]["topHeroes"]
    print("topHeroes: {}".format(raw_top_heroes))
    raw_top_hero_keys = get_sorted_hero_keys(raw_top_heroes)

    # Get top 5 heroes.
    for raw_top_hero_key in raw_top_hero_keys[:5]:
        hero_stats = http_get(
            "https://ow-api.com/v1/stats/pc/us/{battle_tag}/heroes/{hero}".format(
                battle_tag=battle_net_tag.replace("#", "-"),
                hero=raw_top_hero_key))

        if hero_stats is not None:
            games_played = hero_stats["competitiveStats"]["games"]["won"]
            output += "\t\t{}: Win percentage: {} | Games won: {} |  Games played: {} | Time played: {}\n".format(
                raw_top_hero_key.capitalize(),
                raw_top_heroes[
                    raw_top_hero_key][
                    "winPercentage"],
                raw_top_heroes[
                    raw_top_hero_key][
                    "gamesWon"],
                games_played,
                raw_top_heroes[
                    raw_top_hero_key][
                    "timePlayed"])
        else:
            output += "\t\t{}: Win percentage: {} | Games won: {} | Time played: {}\n".format(
                raw_top_hero_key.capitalize(),
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
    # prune the list for any `0 gamesWon` values
    delete = [key for key in raw_top_heroes if int(raw_top_heroes[key]["gamesWon"]) < 10]
    for key in delete:
        del raw_top_heroes[key]

    # Sort list by highest win percentage
    hero_keys = raw_top_heroes.keys()
    hero_keys = sorted(hero_keys, key=lambda key: int(raw_top_heroes[key]["winPercentage"]))
    hero_keys.reverse()
    return hero_keys


@client.event
async def on_voice_state_update(member, before, after):
    text_channel = member.guild.text_channels[0]
    if is_stats_channel(before, after):
        result_set = get_battle_net_ids(member.name, storage)
        if result_set.count() > 0:
            await text_channel.send("Welcome back {}.".format(member.name))
            for result in result_set:
                bnet_user_name = result[MongoConstants.BNET_ID_FIELD]
                uri = 'https://ow-api.com/v1/stats/pc/us/{}/complete'.format(bnet_user_name.replace("#", "-"))
                response = http_get(uri)
                if response is not None:
                    await text_channel.send(format_login_response(response, bnet_user_name))
                else:
                    await text_channel.send("Couldn't get stats for user Battle.net user '{}'. Response {}".format(
                        bnet_user_name, response))


def http_get(uri):
    response = requests.get(uri)
    if response.ok:
        return response.json()
    else:
        print("http get request on uri {} failed with <{}>".format(uri, response))
        return None


def is_stats_channel(before_channel, after_channel):
    stats_channel = False
    # if the voice channel changed and this isn't some other voice state update
    if after_channel.channel is not None and (before_channel.channel is None or \
                                              before_channel.channel.name is not after_channel.channel.name):
        for entry in bot_channels:
            if after_channel.channel.guild.name == entry[0] and after_channel.channel.name == entry[1]:
                stats_channel = True
                break;
    return stats_channel


def get_battle_net_ids(discordName, table):
    return table.find({MongoConstants.DISCORD_NAME_FIELD: discordName})


client.run(get_token())
