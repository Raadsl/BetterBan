import os, time
import discord
from discord.ext import commands, tasks
import sqlite3
import asyncio



async def create_embed(

    title="Command failed",
    description="You don't have permission to use this command",
    color=discord.Color.red(),
    **kwargs,
):
    """Returns an embed"""
    embed = discord.Embed(title=title, description=description, color=color, **kwargs)
    return embed

