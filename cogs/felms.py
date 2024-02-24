import random

import discord
from discord.ext import commands


phrases = [
    "Опять эта банда творит шизу...",
    "Аа... у нас тут есть некоторые люди, которые часто несут чушь.",
    "Но это не шутка... тут нет ничего от шутки.",
    "Ах-ох...",
    "Ну только не опять...",
    "Боже...",
    "Господи.",
    "Я не думаю, что это стоило писать сюда.",
    "Ща в мут отлетишь за странное поведение и капс.",
    "*тихое проявление недовольства*",
    "С меня уже хватит.",
    "Не хочу опять заходить в чат и обнаруживать, какой ужас в этот раз происходит здесь.",
    "Надоели мне твои выходки, у меня аж настроение испортилось.",
    "Вот и настроение пропало.",
    "Настроение паршивое вновь.",
    "Боже мой, хватит уже.",
    "Спасибо за испорченное на весь день настроение. ",
    "Настроение испорчено...",
    "Мне кажется, или это точно не нужно кидать в этот канал...",
    "А это тут при чём...",
    "А так... зачем это вообще...",
    "Можешь проверить все мои сообщения на сервере, если настолько делать нечего.",
    "Ну как обычно, нельзя нормально воспринять, нужно высмеять тут же. <:felms1:1205510982923980831>",
    "Что во мне такого особенного?... Я просто... испортился со временем <:blossombud_ugh:1146385811026214942> Проблем от меня уже больше, чем пользы... Порчу всем настроение своим присутствием..",
    "Моя психика уже рушится и я не могу воспринимать текстовый юмор практически ни в каком виде. <:felms1:1205510982923980831>",
    "Убедительная просьба прекратить спам упоминаниями. Заранее спасибо за понимание.",
    "Не споткнись по дороге 👋",
    "Вот это ты зря быканул. Такой наглости я не ожидал от вашей персоны.",
]


class Felms(commands.Cog, name="felms"):
    def __init__(self, bot):
        self.bot = bot
        self.enabled_on = [1193216540166856794, 1076117733428711434]

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.guild.id not in self.enabled_on:
            return
        if random.randint(1, 1000) < 999:
            return
        await message.channel.send(random.choice(phrases), delete_after=30)


def setup(bot):
    bot.add_cog(Felms(bot))
