import os
import random
import re

import discord
from discord.ext import commands

from .markovboi import MarkovBoi


def create_bot(redis_url: str = "redis://localhost:6379/0") -> commands.Bot:
    m = MarkovBoi(redis_url)

    intents = discord.Intents.default()
    intents.message_content = True
    intents.messages = True

    bot = commands.Bot(command_prefix='!', intents=intents)

    @bot.event
    async def on_ready():
        print(f'{bot.user} is in the house!!')

    @bot.event
    async def on_message(message: discord.Message):
        if message.author.bot:
            return

        if not message.guild:
            return

        guild_id = str(message.guild.id)

        print(f"[{message.guild.name}] {message.author}: {message.content}")

        m.parse_message(guild_id, str(message.author.id), message.content)

        await bot.process_commands(message)

        if random.randint(1, 100) < 5:
            await message.channel.send(m.gen_message(guild_id, None))

    @bot.command()
    async def scan(ctx: commands.Context):
        """Scan the last 10,000 messages in this channel and index them."""
        if not ctx.guild:
            await ctx.send('This command only works in servers.')
            return

        guild_id = str(ctx.guild.id)
        count = 0

        async for msg in ctx.channel.history(limit=10000):
            if not msg.author.bot and not msg.content.startswith(('-', 's?', '!')):
                count += 1
                m.parse_message(guild_id, str(msg.author.id), msg.content)

        await ctx.send(f'Last {count} messages in this channel scanned and indexed.')

    @bot.command()
    async def copy(ctx: commands.Context, user: str = None, *, seed: str = None):
        """Generate a message mimicking a user. Use 'all' for server-wide generation."""
        if not ctx.guild:
            await ctx.send('This command only works in servers.')
            return

        guild_id = str(ctx.guild.id)

        if user and user.lower() == 'all':
            user_id = None
        elif user:
            match = re.search(r'\d{17,19}', user)
            if match:
                user_id = match.group()
            else:
                await ctx.send('**error:** first arg must be a valid user mention/ID or "all"')
                return
        else:
            user_id = str(ctx.author.id)

        result = m.gen_message(guild_id, user_id, seed)
        await ctx.send(result)

    return bot


def main():
    token = os.environ.get('DISCORD_TOKEN')
    if not token:
        print("Error: DISCORD_TOKEN environment variable not set")
        print("Set it with: export DISCORD_TOKEN='your-bot-token'")
        raise SystemExit(1)

    redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

    bot = create_bot(redis_url)
    bot.run(token)


if __name__ == '__main__':
    main()
