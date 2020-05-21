import os
import random

import discord
import requests

import MongoConstants
import MongoDb

client = discord.Client()
storage = MongoDb.get_discord_mongo_table()
bot_channels = [("JakesBotTest", "General"), ("JTMoney", "Broverwatch")]
DEFAULT_COLOUR = 0x003366
HERO_COLOURS = {"ana": 0x718AB3, "bastion": 0x7C8F7B, "brigitte": 0xBE736E, "dVa": 0xED93C7, "doomfist": 815049,
                "genji": 0x97EF43, "hanzo": 0xb9b48a, "junkrat": 0xECBD53, "lucio": 0x85C952, "mccree": 0xAE595C,
                "mei": 0x6FACED, "mercy": 0xEBE8BB, "moira": 0x976BE2, "orisa": 0x468C43, "pharah": 0x3E7DCA,
                "reaper": 0x7D3E51, "reinhardt": 0x929DA3, "roadhog": 0xB68C52, "soldier76": 0x697794,
                "sombra": 0x7359BA, "symmetra": 0x8EBCCC, "torbjorn": 0xC0726E, "tracer": 0xD79342,
                "widowmaker": 0x9E6AA8, "winston": 0xA2A6BF, "zarya": 0xE77EB6, "zenyatta": 0xEDE582}

SR_STAT_JOINER = "    "
SR_EMOJI_SUFFIX = "  :  {}"
SR_EMOJI_COMBOS = [["shield", "crossed_swords", "medical_symbol"], ["fire_engine", "police_car", "ambulance"]]


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


def get_top_heroes_sorted(stats, max_number_of_heroes):
    top_heroes = stats["competitiveStats"]["topHeroes"]
    # prune the list so that only heroes which have been played 10 or more times are considered
    heroes_with_less_than_ten_games = []
    heroes_with_zero_games_played = []
    for key in top_heroes:
        try:
            games_played = int(stats["competitiveStats"]["careerStats"][key]["game"]["gamesPlayed"])
            if games_played < 10:
                heroes_with_less_than_ten_games.append(key)
                if games_played == 0:
                    heroes_with_zero_games_played.append(key)
        except KeyError as ke:
            print("failed to get games played for hero '{}' with error <{}>".format(key, str(ke)))
            heroes_with_less_than_ten_games.append(key)

    if len(heroes_with_less_than_ten_games) < len(top_heroes):
        for key in heroes_with_less_than_ten_games:
            del top_heroes[key]
    else:
        for key in heroes_with_zero_games_played:
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
        stats_embed = get_embedded_stats(response, uri)
        await text_channel.send(embed=stats_embed)
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


def get_random_dict_values(dict_of_dicts, num_of_values, filter_keys):
    random_stats = {}
    for i in range(0, num_of_values):
        key_value = None
        while key_value is None or key_value[1] is None or key_value[0] in filter_keys or key_value[
            0] in random_stats.keys():
            key_value = get_random_stat(dict_of_dicts)
        random_stats[key_value[0]] = key_value[1]

    return random_stats


def get_random_stat(stats_dict):
    keys = list(stats_dict.keys())
    key = keys[random.randint(0, len(keys) - 1)]
    value = stats_dict[key]
    if type(value) is not dict:
        return [key, value]
    else:
        return get_random_stat(value)


def get_embedded_stats(stats, stats_uri):
    # get top 5 hero names
    top_hero_names = get_top_heroes_sorted(stats, 5)

    if len(top_hero_names) > 0:
        top_hero_name = top_hero_names[0]
    else:
        top_hero_name = None

    hero_stats_discord_embed = discord.Embed(color=get_hero_colour(top_hero_name))

    hero_stats_discord_embed.title = "[BattleTag {}]".format(stats["name"])

    [tank_sr, dps_sr, heal_sr] = get_sr(stats)
    msg_output = get_formatted_sr(tank_sr, dps_sr, heal_sr)
    number_of_top_heroes = len(top_hero_names)
    if number_of_top_heroes > 0:
        msg_output += "\n\nYour top {} heroes this season are:\n".format(
            len(top_hero_names))
    else:
        max_sr_role, max_sr_value = get_max_sr(stats)

        msg_output = "\n{} is your best role with {} SR.\n".format(
            max_sr_role.capitalize(), max_sr_value)

    for top_hero in top_hero_names:
        hero_stats_dict = stats["competitiveStats"]["careerStats"][top_hero]
        win_percentage = get_win_percentage(stats, top_hero)
        games_played = get_games_played(stats, top_hero)
        random_stats = get_random_dict_values(hero_stats_dict, 4, filter_keys=["winPercentage", "gamesPlayed"])

        list_of_str_fmt_stats = []
        for random_stat in random_stats.keys():
            list_of_str_fmt_stats.append(
                "{}: {}".format(un_camel_case(str(random_stat)), str(random_stats[random_stat])))

        values = "\n".join(list_of_str_fmt_stats)
        hero_stats_discord_embed.add_field(
            name="{hero_name} ({win_percentage} of {games_played})".format(hero_name=top_hero.capitalize(),
                                                                           win_percentage=win_percentage,
                                                                           games_played=games_played),
            value=values,
            inline=False)

    hero_stats_discord_embed.url = stats_uri
    hero_stats_discord_embed.description = msg_output
    # TODO: I don't like the way the timezone looks, maybe Pet does or ROB ASKS ME FOR IT
    # hero_stats_discord_embed.timestamp = datetime.datetime.now(pytz.timezone("Canada/Eastern"))
    player_icon_url = stats["icon"]
    if player_icon_url is not None:
        hero_stats_discord_embed.set_thumbnail(url=player_icon_url)

    return hero_stats_discord_embed


def get_games_played(stats, top_hero):
    games_played = 0
    try:
        games_played = stats["competitiveStats"]["careerStats"][top_hero]["game"]["gamesPlayed"]
    except KeyError as ke:
        print("games played not found: <{}>".format(ke))
    return games_played


def get_win_percentage(stats, top_hero):
    win_percentage = "0%"
    try:
        win_percentage = stats["competitiveStats"]["careerStats"][top_hero]["game"]["winPercentage"]
    except KeyError as ke:
        print("win percentage not found: <{}>".format(ke))
    return win_percentage


def get_max_sr(stats):
    ratings = stats["ratings"]
    max_sr = 0
    role = "unknown"
    if ratings is not None:
        for item in ratings:
            if "level" in item.keys():
                level = item["level"]
                if max_sr <= level:
                    role = item["role"]
                    max_sr = level

    return role, max_sr


def get_hero_colour(name):
    message_colour = DEFAULT_COLOUR
    if name is not None and name in HERO_COLOURS.keys():
        message_colour = HERO_COLOURS[name]
    else:
        print("Hero colour not found for hero {}, default {} used".format(name, message_colour))
    return message_colour


def un_camel_case(camel_cased_string, space_before_numbers=True):
    output_string = ""
    for i in range(0, len(camel_cased_string)):
        if i == 0:
            output_string += camel_cased_string[0].upper()
        elif camel_cased_string[i].isupper() or (
                space_before_numbers is True and camel_cased_string[i].isnumeric() and not camel_cased_string[
            i - 1].isnumeric()):
            output_string += " {}".format(camel_cased_string[i].lower())
        else:
            output_string += camel_cased_string[i]
    return output_string


def get_sr(stats):
    """Returns a list of SR in this order [TANK_SR, DAMAGE_SR, SUPPORT_SR"""
    sr = [None, None, None]
    ratings = stats["ratings"]
    index_lookup = {"tank": 0, "damage": 1, "support": 2}
    if ratings is not None:
        for item in ratings:
            if "level" in item.keys():
                role = item["role"]
                sr[index_lookup[role]] = item["level"]
    return sr


def get_formatted_sr(tank, dps, heal):
    str_builder = get_random_sr_fmt_string()
    no_value = ":question:"
    return str_builder.format(get_value_or_default(tank, no_value), get_value_or_default(dps, no_value),
                              get_value_or_default(heal, no_value))


def get_value_or_default(value, default):
    return value if value is not None else default


def get_random_sr_fmt_string():
    emoji_choice = SR_EMOJI_COMBOS[random.randint(0, len(SR_EMOJI_COMBOS) - 1)]
    emoji_value_pairs = map(lambda x: ":" + x + ":" + SR_EMOJI_SUFFIX, emoji_choice)
    return SR_STAT_JOINER.join(emoji_value_pairs)


client.run(get_token())
