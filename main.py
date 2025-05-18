import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix="$", intents=intents)

class GravarModal(discord.ui.Modal, title="Cadastro de Serviço"):
    titulo = discord.ui.TextInput(label="Título do Serviço", placeholder="Ex: Designer de Logo", max_length=100)
    nivel = discord.ui.TextInput(label="Nível do Serviço", placeholder="Ex: Iniciante / Avançado", max_length=50)
    descricao = discord.ui.TextInput(label="Descrição", style=discord.TextStyle.paragraph, placeholder="Descreva aqui...", max_length=300)
    pagamento = discord.ui.TextInput(label="Pagamento", placeholder="Ex: R$50 via Pix", max_length=100)

    async def on_submit(self, interaction: discord.Interaction):
        # Canal de autorização
        canal_autorizar = discord.utils.get(interaction.guild.text_channels, name="autorizar")
        if not canal_autorizar:
            await interaction.response.send_message("Canal 'autorizar' não encontrado.", ephemeral=True)
            return

        # Montar o embed
        embed = discord.Embed(title=self.titulo.value, color=discord.Color.blurple())
        embed.add_field(name="📊 Nível do Serviço", value=self.nivel.value, inline=False)
        embed.add_field(name="💼 Descrição", value=self.descricao.value, inline=False)
        embed.add_field(name="💸 Pagamento", value=self.pagamento.value, inline=False)
        embed.set_footer(text=f"Solicitado por {interaction.user}", icon_url=interaction.user.avatar.url)

        msg = await canal_autorizar.send(embed=embed)

        await msg.add_reaction("✅")
        await msg.add_reaction("❌")

        await interaction.response.send_message("Seu serviço foi enviado para autorização!", ephemeral=True)

        def check(reaction, user):
            return (
                user != bot.user and str(reaction.emoji) in ["✅", "❌"]
                and reaction.message.id == msg.id
            )

        try:
            reaction, user = await bot.wait_for("reaction_add", timeout=3600, check=check)
            if str(reaction.emoji) == "✅":
                canal_final = discord.utils.get(interaction.guild.text_channels, name="mensagens")
                if canal_final:
                    await canal_final.send(embed=embed)
                    await canal_autorizar.send(f"Aprovado por {user.mention} ✅")
            else:
                await canal_autorizar.send(f"Recusado por {user.mention} ❌")

        except asyncio.TimeoutError:
            await canal_autorizar.send("Tempo esgotado para autorização.")

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Comandos sincronizados: {len(synced)}")
    except Exception as e:
        print(e)

@bot.tree.command(name="gravar", description="Registrar um novo serviço")
async def gravar(interaction: discord.Interaction):
    await interaction.response.send_modal(GravarModal())


load_dotenv()
bot.run(os.getenv("TOKEN"))

