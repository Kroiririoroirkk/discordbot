#!./bin/python
import asyncio

import discord
import youtube_dl

from discord.ext import commands

#Dice
from random import randint

#LaTeX
from latex import build_pdf
from pdf2image import convert_from_bytes
from io import BytesIO

#Config
from dotenv import load_dotenv
from os import getenv

# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ''
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}
ffmpeg_options = {
    'options': '-vn'
}
ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def join(self, ctx, *, channel: discord.VoiceChannel=None):
        """Joins a voice channel"""
        if ctx.author.voice:
            channel = channel or ctx.author.voice.channel
        if channel:
            if ctx.voice_client:
                await ctx.voice_client.move_to(channel)
            else:
                await channel.connect()

    @commands.command()
    async def play(self, ctx, *, query):
        """Plays a file from the local filesystem"""

        source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(query))
        ctx.voice_client.play(source, after=lambda e: print('Player error: %s' % e) if e else None)

        await ctx.send('Now playing: {}'.format(query))

    @commands.command()
    async def yt(self, ctx, *, url):
        """Plays from a url (almost anything youtube_dl supports)"""

        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop)
            ctx.voice_client.play(player, after=lambda e: print('Player error: %s' % e) if e else None)

        await ctx.send('Now playing: {}'.format(player.title))

    @commands.command()
    async def stream(self, ctx, *, url):
        """Streams from a url (same as yt, but doesn't predownload)"""

        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
            ctx.voice_client.play(player, after=lambda e: print('Player error: %s' % e) if e else None)

        await ctx.send('Now playing: {}'.format(player.title))

    @commands.command()
    async def volume(self, ctx, volume: int):
        """Changes the player's volume"""

        if ctx.voice_client is None:
            return await ctx.send("Not connected to a voice channel.")

        ctx.voice_client.source.volume = volume / 100
        await ctx.send("Changed volume to {}%".format(volume))

    @commands.command()
    async def stop(self, ctx):
        """Stops and disconnects the bot from voice"""

        await ctx.voice_client.disconnect()

    @play.before_invoke
    @yt.before_invoke
    @stream.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("You are not connected to a voice channel.")
                raise commands.CommandError("Author not connected to a voice channel.")
        elif ctx.voice_client.is_playing():
            ctx.voice_client.stop()

class Dice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def r(self, ctx, *, dice: str):
        if dice:
            try:
                [numDice,dieFaces] = map(int,dice.split('d'))
            except ValueError:
                try:
                    numDice = 1
                    dieFaces = int(dice)
                except ValueError:
                    await ctx.send('Invalid format!')
                    return
        else:
            numDice = 1
            dieFaces = 6
        if dieFaces >= 1:
            ns = [randint(1,dieFaces) for _ in range(numDice)]
            await ctx.send(','.join(map(str,ns)))
        else:
            await ctx.send('The dice must have at least one face!')

    @commands.command()
    async def rs(self, ctx, *, dice: str):
        if dice:
            try:
                [numDice,dieFaces] = map(int,dice.split('d'))
            except ValueError:
                try:
                    numDice = 1
                    dieFaces = int(dice)
                except ValueError:
                    await ctx.send('Invalid format!')
                    return
        else:
            numDice = 1
            dieFaces = 6
        if dieFaces >= 1:
            ns = [randint(1,dieFaces) for _ in range(numDice)]
            await ctx.send(','.join(map(str,ns)) + '|Σ=' + str(sum(ns)))
        else:
            await ctx.send('The dice must have at least one face!')

    @commands.command()
    async def rnc(self, ctx, *, dice: str):
        if dice:
            try:
                [numDice,dieFaces] = map(int,dice.split('d'))
            except ValueError:
                try:
                    numDice = 1
                    dieFaces = int(dice)
                except ValueError:
                    await ctx.send('Invalid format!')
                    return
        else:
            numDice = 1
            dieFaces = 6
        if dieFaces >= 1:
            ns = [randint(1,dieFaces) for _ in range(numDice)]
            await ctx.send(''.join(map(str,ns)))
        else:
            await ctx.send('The dice must have at least one face!')

class Cool(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command('AmICool?')
    async def cool(self, ctx):
        await ctx.send('Verily, you are cool!')

def latexify(txt, paper_width=200, paper_height=100, margin=5):
    latex = ('\\documentclass{article}\n'
             '\\usepackage[paperwidth=' + str(paper_width) + 'pt,'
                 'paperheight=' + str(paper_height) + 'pt,'
                 'margin=' + str(margin) + 'pt]'
                 '{geometry}\n'
             '\\usepackage{xcolor}\n'
             '\\usepackage{graphicx}\n'
             '\\usepackage{amsmath}\n'
             '\\usepackage{mhchem}\n'
             '\\usepackage{siunitx}\n'
             '\\begin{document}\n'
             '\\noindent ' + txt + '\n'
             '\\end{document}\n')
    pdf = build_pdf(latex, ['-no-shell-escape'])
    imgs = convert_from_bytes(pdf.readb())
    files = []
    for i, img in enumerate(imgs):
        with BytesIO() as f:
            img.save(f, "PNG")
            f.seek(0)
            files.append(discord.File(f, f'LaTeX{i}.png'))
    return files

class Latex(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.is_owner()
    async def latex(self, ctx, *, msg: str):
        latex_files = latexify(msg)
        await ctx.send(files=latex_files)

from datetime import date
import calendar

class Schedule(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def schedule(self, ctx):
        await ctx.send("""Here you go!
Block 1: 7:35-8:45
Block 2: 8:48-9:58
Lunch: 10:01-11:19
Block 3: 11:22-12:32
Block 4: 12:35-1:45
Block 5: 1:50-3:05

Wednesday clubs
A: 12:18-1:03
B: 1:06-1:51
C: 1:54-2:29""")

    @commands.command()
    async def schedule_old2(self, ctx):
        day = calendar.day_name[date.today().weekday()]
        schedule = """
\\begin{center}
\\begin{tabular}{c|c|c|c|c|c}
&Monday&Tuesday&Wednesday&Thursday&Friday\\\\
\\hline
&&7:30-7:50 Office Hours&&&7:30-7:50 Office Hours\\\\
\\hline
Block One&7:35-8:55 A in-person&7:50-8:50&&7:35-8:55 B in-person&7:50-8:50\\\\
\\hline
Block Two&9:00-10:20 A in-person&9:00-10:00&&9:00-10:20 B in-person&9:00-10:00\\\\
\\hline
Lunch&10:20-11:20&10:00-11:00&12:18-1:03 Club A&10:20-11:20&10:00-11:00\\\\
\\hline
Block Three&11:20-12:20&11:00-12:20 A in-person&1:06-1:51 Club B&11:20-12:20&11:00-12:20 B in-person\\\\
\\hline
Block Four&12:30-1:30&12:25-1:45 A in-person&1:54-2:29 Club C&12:30-1:30&12:25-1:45 B in-person\\\\
\\hline
Block Five&1:45-3:05&1:55-3:15 A in-person&Office Hours&1:45-3:05&1:55-3:15 B in-person
\\end{tabular}
\\end{center}
"""
        latex_files = latexify(schedule, paper_width=700, paper_height=150)
        await ctx.send(f"Today is {day}!", files=latex_files)

    @commands.command()
    async def schedule_old(self, ctx):
        await ctx.send("""
Before school: 7:35-8:30
Block 1: 8:40-9:40
Block 2: 9:50-10:50
Lunch: 10:50-12
Block 3: 12-1
Block 4: 1:10-2:10
Block 5: 2:20-3:15
""")

class PictureAutoreply(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def racism(self, ctx):
        await ctx.send("https://atemptingvegan.files.wordpress.com/2012/04/pickle1.jpg")

    @commands.command()
    async def nationalism(self, ctx):
        await ctx.send("https://images.lillianvernon.com/catalog/product/LPGUM07/lpgum07.jpg")

    @commands.command()
    async def discrimination(self, ctx):
        await ctx.send("https://logos.textgiraffe.com/logos/logo-name/Junior-designstyle-colors-m.png")

    @commands.command()
    async def discrimnation(self, ctx):
        await ctx.send("http://popnamer.com/wp-content/uploads/2013/07/letters-spelling-out-the-word-Seniors.-with-people-standing-at-each-letter19151.jpg")

    @commands.command()
    async def revolution(self, ctx):
        await ctx.send("http://cdn.sparkfun.com/assets/d/6/5/6/a/5112ed4ece395f2f2a000003.gif")

    @commands.command()
    async def moderate(self, ctx):
        await ctx.send("Now deleting sam's last 10 messages... Please wait patiently...")

class Core(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.is_owner()
    async def eval(self, ctx, *, command: str):
        await ctx.send(eval(command))

    @commands.command()
    @commands.is_owner()
    async def evalAwait(self, ctx, *, command: str):
        await eval(command)

    @commands.command()
    @commands.is_owner()
    async def say(self, ctx, *, msg: str):
        await ctx.send(msg)

    @commands.command()
    @commands.is_owner()
    async def logout(self, ctx):
        await ctx.send('Logging out!')
        await bot.logout()

# ----------

load_dotenv()

OWNER = int(getenv("OWNER"))
TOKEN = getenv("TOKEN")

# ----------

bot = commands.Bot(command_prefix='!',
                   description='Bot',
                   owner_id=OWNER)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} ({bot.user.id})')
    print('------')

bot.add_cog(Music(bot))
bot.add_cog(Dice(bot))
bot.add_cog(Cool(bot))
bot.add_cog(Latex(bot))
bot.add_cog(Schedule(bot))
bot.add_cog(PictureAutoreply(bot))
bot.add_cog(Core(bot))

bot.run(TOKEN)

