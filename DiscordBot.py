import os
import random

import discord
import requests

import MongoConstants
import MongoDb

client = discord.Client()
storage = MongoDb.get_discord_mongo_table()
bot_channels = [("JakesBotTest", "General"), ("JTMoney", "Broverwatch")]
PREVIOUS_STATISTICS_KEYS = {}


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


def get_formatted_stats(stats):
    random_stats = True
    top_heroes_stats_raw = stats["competitiveStats"]["topHeroes"]
    # get top 5 hero names
    top_hero_names = get_top_heroes_sorted(stats, 5)

    bnet_name = stats["name"]
    msg_output = "[Battle.net Tag {}]. \nYour top {} heroes this season are:\n".format(bnet_name,
                                                                                       len(top_hero_names))

    for top_hero in top_hero_names:

        if random_stats:
            hero_stats_dict = stats["competitiveStats"]["careerStats"][top_hero]

            random_user_statistics = get_random_dict_values(hero_stats_dict, 4, PREVIOUS_STATISTICS_KEYS[bnet_name])
            # add retrieved stats to filter
            print("previous_stats = {}, random_user_statistics = {}".format(PREVIOUS_STATISTICS_KEYS[bnet_name],
                                                                            random_user_statistics))
            PREVIOUS_STATISTICS_KEYS[bnet_name] = random_user_statistics.keys()

            values = format_stats_for_user_output_message(random_user_statistics)
            msg_output += "\t\t{}: {}\n".format(top_hero.capitalize(), values)
        else:
            games_played = stats["competitiveStats"]["careerStats"][top_hero]["game"]["gamesPlayed"]
            msg_output += "\t\t{}: Win percentage: {} | Games won: {} |  Games played: {} | Time played: {}\n".format(
                top_hero.capitalize(),
                top_heroes_stats_raw[
                    top_hero][
                    "winPercentage"],
                top_heroes_stats_raw[
                    top_hero][
                    "gamesWon"],
                games_played,
                top_heroes_stats_raw[
                    top_hero][
                    "timePlayed"])
    return msg_output


def format_stats_for_user_output_message(random_user_statistics):
    formatted_statistics = []
    for random_stat in random_user_statistics:
        formatted_statistics.append("{}: {}".format(str(random_stat[0]), str(random_stat[1])))
    values = " | ".join(formatted_statistics)
    return values


def get_top_heroes_sorted(stats, max_number_of_heroes):
    top_heroes = stats["competitiveStats"]["topHeroes"]
    # prune the list so that only heroes which have been played 10 or more times are considered
    delete = [key for key in top_heroes if
              int(stats["competitiveStats"]["careerStats"][key]["game"]["gamesPlayed"]) < 10]
    for key in delete:
        del top_heroes[key]

    # Sort list by highest win percentage
    hero_keys = top_heroes.keys()
    hero_keys = sorted(hero_keys, key=lambda key: int(top_heroes[key]["winPercentage"]))
    hero_keys.reverse()

    return hero_keys[:max_number_of_heroes]


@client.event
async def on_voice_state_update(member, before, after):
    text_channel = member.guild.text_channels[0]
    if is_stats_channel(before, after):
        result_set = get_battle_net_ids(member.name, storage)
        if result_set.count() > 0:
            await text_channel.send("Welcome back {}.".format(member.name))
            for result in result_set:
                bnet_user_name = result[MongoConstants.BNET_ID_FIELD]
                await post_bnet_stats(bnet_user_name, text_channel)


async def post_bnet_stats(bnet_user_name, text_channel):
    uri = 'https://ow-api.com/v1/stats/pc/us/{}/complete'.format(bnet_user_name.replace("#", "-"))
    response = http_get(uri)
    if response is not None:
        stats = get_formatted_stats(response)
        await text_channel.send(stats)
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
                break
    return stats_channel


def get_battle_net_ids(discord_name, table):
    return table.find({MongoConstants.DISCORD_NAME_FIELD: discord_name})


def get_random_dict_values(dict_of_dicts, num_of_values, key_filter_list):
    random_stats = {}
    for i in range(0, num_of_values):
        stat = None
        while stat is None or stat[1] is None or stat in key_filter_list or stat in random_stats:
            key, value = get_random_stat(dict_of_dicts)

        random_stats[key] = value

    return random_stats


def get_random_stat(stats_dict):
    keys = list(stats_dict.keys())
    key = keys[random.randint(0, len(keys) - 1)]
    value = stats_dict[key]
    if type(value) is not dict:
        return key, value
    else:
        return get_random_stat(value)


client.run(get_token())
