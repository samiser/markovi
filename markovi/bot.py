import asyncio
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
    async def scan(ctx: commands.Context, limit: int = 10000):
        """Scan messages in this channel. Use !scan <number> to set limit."""
        if not ctx.guild:
            await ctx.send('This command only works in servers.')
            return

        guild_id = str(ctx.guild.id)
        count = 0
        batch_size = 100
        processed = 0

        status_msg = await ctx.send(f'Scanning up to {limit} messages...')

        async for msg in ctx.channel.history(limit=limit):
            if not msg.author.bot and not msg.content.startswith(('-', 's?', '!')):
                count += 1
                m.parse_message(guild_id, str(msg.author.id), msg.content)

            processed += 1
            if processed % batch_size == 0:
                await status_msg.edit(content=f'Scanned {processed} messages ({count} indexed)...')
                await asyncio.sleep(1)

        await status_msg.edit(content=f'Done! Scanned {processed} messages, indexed {count}.')

    @bot.command()
    async def scanall(ctx: commands.Context, limit_per_channel: int = 5000):
        """Scan all text channels in the server. Use !scanall <limit> to set per-channel limit."""
        if not ctx.guild:
            await ctx.send('This command only works in servers.')
            return

        guild_id = str(ctx.guild.id)
        total_count = 0
        total_processed = 0
        channels_scanned = 0

        text_channels = [ch for ch in ctx.guild.channels if isinstance(ch, discord.TextChannel)]
        status_msg = await ctx.send(f'Scanning {len(text_channels)} channels ({limit_per_channel} msgs each)...')

        for channel in text_channels:
            try:
                channel_count = 0
                async for msg in channel.history(limit=limit_per_channel):
                    if not msg.author.bot and not msg.content.startswith(('-', 's?', '!')):
                        total_count += 1
                        channel_count += 1
                        m.parse_message(guild_id, str(msg.author.id), msg.content)
                    total_processed += 1

                channels_scanned += 1
                await status_msg.edit(
                    content=f'Scanned {channels_scanned}/{len(text_channels)} channels. '
                    f'#{channel.name}: {channel_count} indexed. Total: {total_count}'
                )
                await asyncio.sleep(2)
            except discord.Forbidden:
                channels_scanned += 1
                await status_msg.edit(
                    content=f'Scanned {channels_scanned}/{len(text_channels)} channels. '
                    f'#{channel.name}: no access. Total: {total_count}'
                )

        await status_msg.edit(
            content=f'Done! Scanned {channels_scanned} channels, {total_processed} messages, indexed {total_count}.'
        )

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
