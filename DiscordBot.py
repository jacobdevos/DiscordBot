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
        if isinstance(message.author, discord.member.Member):
            await message.channel.send('Hello {}!'.format(message.author.display_name))
        else:
            await message.channel.send('Hello {}!'.format(message.author))


@client.event
async def on_member_join(member):
    await member.guild.text_channels[0].send('Hello {}!'.format(member.display_name))


@client.event
async def on_voice_state_update(member, before, after):
    print('voice update recieved: {},{},{}'.format(member, before, after))
    if before.channel is None or before.channel.name is not "General" and after.channel.name is "General":
        await member.guild.text_channels[0].send('Hello {}'.format(member.display_name))

client.run(get_token())



