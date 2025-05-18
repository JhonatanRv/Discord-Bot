import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv

# Carrega as variáveis do .env (ex: TOKEN)
load_dotenv()

# Configuração dos intents necessários para o bot funcionar corretamente
intents = discord.Intents.default()
intents.messages = True  # Permite que o bot veja mensagens
intents.message_content = True  # Necessário para ler o conteúdo das mensagens

# Cria a instância do bot com prefixo $ e os intents configurados
bot = commands.Bot(command_prefix="$", intents=intents)

# Define uma classe que representa o Modal de entrada de dados do usuário
class GravarModal(discord.ui.Modal, title="Cadastro de Serviço"):
    # Campos do formulário (modal)
    titulo = discord.ui.TextInput(label="Título do Serviço", placeholder="Ex: Designer de Logo", max_length=100)
    nivel = discord.ui.TextInput(label="Nível do Serviço", placeholder="Ex: Iniciante / Avançado", max_length=50)
    descricao = discord.ui.TextInput(label="Descrição", style=discord.TextStyle.paragraph, placeholder="Descreva aqui...", max_length=300)
    pagamento = discord.ui.TextInput(label="Pagamento", placeholder="Ex: R$50 via Pix", max_length=100)

    # Função executada quando o usuário envia o modal
    async def on_submit(self, interaction: discord.Interaction):
        # Busca o canal de texto chamado "autorizar"
        canal_autorizar = discord.utils.get(interaction.guild.text_channels, name="autorizar")
        if not canal_autorizar:
            # Se o canal não for encontrado, avisa o usuário e encerra
            await interaction.response.send_message("Canal 'autorizar' não encontrado.", ephemeral=True)
            return

        # Cria o embed (mensagem formatada) com os dados informados pelo usuário
        embed = discord.Embed(title=self.titulo.value, color=discord.Color.blurple())
        embed.add_field(name="📊 Nível do Serviço", value=self.nivel.value, inline=False)
        embed.add_field(name="💼 Descrição", value=self.descricao.value, inline=False)
        embed.add_field(name="💸 Pagamento", value=self.pagamento.value, inline=False)
        embed.set_footer(text=f"Solicitado por {interaction.user}", icon_url=interaction.user.avatar.url)

        # Envia o embed no canal "autorizar"
        msg = await canal_autorizar.send(embed=embed)

        # Adiciona reações de aprovação e reprovação
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")

        # Responde ao usuário de forma privada que a solicitação foi enviada
        await interaction.response.send_message("Seu serviço foi enviado para autorização!", ephemeral=True)

        # Define a verificação para capturar a reação correta do moderador
        def check(reaction, user):
            return (
                user != bot.user and str(reaction.emoji) in ["✅", "❌"]
                and reaction.message.id == msg.id
            )

        try:
            # Aguarda uma reação por até 1 hora (3600 segundos)
            reaction, user = await bot.wait_for("reaction_add", timeout=3600, check=check)
            if str(reaction.emoji) == "✅":
                # Se aprovado, envia o embed para o canal "mensagens"
                canal_final = discord.utils.get(interaction.guild.text_channels, name="mensagens")
                if canal_final:
                    await canal_final.send(embed=embed)
                    await canal_autorizar.send(f"Aprovado por {user.mention} ✅")
            else:
                # Se recusado, apenas avisa no canal de autorização
                await canal_autorizar.send(f"Recusado por {user.mention} ❌")

        except asyncio.TimeoutError:
            # Se ninguém reagir dentro de 1 hora, avisa que expirou
            await canal_autorizar.send("Tempo esgotado para autorização.")

# Evento que roda quando o bot entra em funcionamento
@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")
    try:
        # Sincroniza os comandos de barra (slash) com o Discord
        synced = await bot.tree.sync()
        print(f"Comandos sincronizados: {len(synced)}")
    except Exception as e:
        print(e)

# Define o comando de barra "/gravar" que abre o modal para o usuário
@bot.tree.command(name="gravar", description="Registrar um novo serviço")
async def gravar(interaction: discord.Interaction):
    await interaction.response.send_modal(GravarModal())

# Executa o bot com o token do arquivo .env
bot.run(os.getenv("TOKEN"))
