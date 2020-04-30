import os
import random

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


def get_formatted_stats(stats, battle_net_tag):
    top_heroes_stats_raw = stats["competitiveStats"]["topHeroes"]
    # get top 5 hero names
    top_hero_names = get_top_heroes_sorted(top_heroes_stats_raw, 5)

    output = "[Battle.net Tag {}]. \nYour top {} heroes this season are:\n".format(stats["name"], len(top_hero_names))
    for raw_top_hero_key in top_hero_names:
        hero_stats = http_get(
            "https://ow-api.com/v1/stats/pc/us/{battle_tag}/heroes/{hero}".format(
                battle_tag=battle_net_tag.replace("#", "-"),
                hero=raw_top_hero_key))
        if hero_stats is not None:
            hero_stats_dict = hero_stats["competitiveStats"]["careerStats"][raw_top_hero_key]
            print('hero stats = {}'.format(hero_stats_dict))
            values = " | ".join(get_random_dict_values(hero_stats_dict, 4))
            output += "\t\t{}: {}\n".format(raw_top_hero_key.capitalize(), values)


        # if hero_stats is not None:
        #     games_played = hero_stats["competitiveStats"]["careerStats"][raw_top_hero_key]["game"]["gamesPlayed"]
        #     print('games played: {}'.format(games_played))
        #     output += "\t\t{}: Win percentage: {} | Games won: {} |  Games played: {} | Time played: {}\n".format(
        #         raw_top_hero_key.capitalize(),
        #         top_heroes_stats_raw[
        #             raw_top_hero_key][
        #             "winPercentage"],
        #         top_heroes_stats_raw[
        #             raw_top_hero_key][
        #             "gamesWon"],
        #         games_played,
        #         top_heroes_stats_raw[
        #             raw_top_hero_key][
        #             "timePlayed"])

        else:
            output += "\t\t{}: Win percentage: {} | Games won: {} | Time played: {}\n".format(
                raw_top_hero_key.capitalize(),
                top_heroes_stats_raw[
                    raw_top_hero_key][
                    "winPercentage"],
                top_heroes_stats_raw[
                    raw_top_hero_key][
                    "gamesWon"],
                top_heroes_stats_raw[
                    raw_top_hero_key][
                    "timePlayed"])

    return output


def get_top_heroes_sorted(raw_top_heroes, max_number_of_heroes):
    # prune the list for any `0 gamesWon` values
    delete = [key for key in raw_top_heroes if int(raw_top_heroes[key]["gamesWon"]) < 10]
    for key in delete:
        del raw_top_heroes[key]

    # Sort list by highest win percentage
    hero_keys = raw_top_heroes.keys()
    hero_keys = sorted(hero_keys, key=lambda key: int(raw_top_heroes[key]["winPercentage"]))
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
                uri = 'https://ow-api.com/v1/stats/pc/us/{}/complete'.format(bnet_user_name.replace("#", "-"))
                response = http_get(uri)
                if response is not None:
                    stats = get_formatted_stats(response, bnet_user_name)
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
                break;
    return stats_channel


def get_battle_net_ids(discordName, table):
    return table.find({MongoConstants.DISCORD_NAME_FIELD: discordName})


def get_random_dict_values(dict_of_dicts, num_of_values):
    random_values = []
    for i in range(0, num_of_values):
        random_stat = get_random_stat(dict_of_dicts)
        while random_stat in random_values:
            random_stat = get_random_stat(dict_of_dicts)
        random_values.append(get_random_stat(dict_of_dicts))
    print('random values <{}>'.format(random_values))
    return random_values


def get_random_stat(stats_dict):
    keys = list(stats_dict.keys())
    print('keys={}'.format(keys))
    print('stats_dict={}'.format(stats_dict))
    key = keys[random.randint(0, len(keys) - 1)]
    value = stats_dict[key]
    if type(value) is not dict:
        return key, value
    else:
        get_random_stat(value)


client.run(get_token())
