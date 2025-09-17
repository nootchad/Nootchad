# -*- coding: utf-8 -*-
import logging

from discord.ext import commands
from discord.ext.commands import Bot, Cog

from .config import Config

log = logging.getLogger(__name__)


class BaseCog(Cog):
    """Cog base para todos los cogs"""

    def __init__(self, bot: Bot):
        self.bot = bot
        self.config = Config()


class Marketplace(BaseCog):
    """Modulo de Marketplace para el bot"""

    def __init__(self, bot: Bot):
        super().__init__(bot)

    @commands.command(name="asset")
    async def asset(self, ctx: commands.Context, *, query: str):
        """
        Comando /asset render - Obtener datos 3D de un asset en archivo ZIP
        """
        await ctx.send("Aquí iría la lógica para obtener datos 3D de un asset.")


def setup(bot: Bot):
    bot.add_cog(Marketplace(bot))