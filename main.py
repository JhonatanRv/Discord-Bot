import os
import discord
from discord.ext import commands
from discord.ui import Modal, TextInput, View, Button
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("Token do bot não encontrado no .env")

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="/", intents=intents)

ATENDENTE_ROLE_ID = 1374061806599012403
LIDER_ROLE_ID = 1373862477502349444
COLABORADORES_CHANNEL_ID = 1373159967091064994
LIDERES_CHANNEL_ID = 1373856968854343750

FUNCAO_ROLES = {
    "Front-end": 1374062295180640447,
    "Back-end": 1374062345180942686,
    "UI/UX": 1374062382585741312
}

demanda_counter = 0
demandas_abertas = {}

class Demanda:
    def __init__(self, titulo, data_entrega, tipo_servico, contato_cliente, autor_id):
        global demanda_counter
        demanda_counter += 1
        self.id = demanda_counter
        self.titulo = titulo
        self.data_entrega = data_entrega
        self.tipo_servico = tipo_servico
        self.contato_cliente = contato_cliente
        self.autor_id = autor_id
        self.lider_id = None
        self.colaboradores = []
        self.roles_necessarias = []
        self.quantidade_necessaria = 0
        self.mensagem_colaboradores = None
        self.chat_criado = False

class GravarModal(Modal, title="Registro de Demanda"):
    def __init__(self):
        super().__init__()
        self.titulo = TextInput(label="Título do Serviço", placeholder="Ex: Site institucional", style=discord.TextStyle.short, max_length=100)
        self.data_entrega = TextInput(label="Data de Entrega", placeholder="Ex: 25/05/2025", style=discord.TextStyle.short, max_length=50)
        self.tipo_servico = TextInput(label="Tipo do Serviço", placeholder="Ex: Desenvolvimento Web", style=discord.TextStyle.short, max_length=100)
        self.contato = TextInput(label="Contato do Cliente", placeholder="Ex: WhatsApp, Discord, Email", style=discord.TextStyle.paragraph, max_length=200)
        self.add_item(self.titulo)
        self.add_item(self.data_entrega)
        self.add_item(self.tipo_servico)
        self.add_item(self.contato)

    async def on_submit(self, interaction: discord.Interaction):
        if not any(role.id == ATENDENTE_ROLE_ID for role in interaction.user.roles):
            return await interaction.response.send_message("Apenas atendentes podem usar este comando.", ephemeral=True)

        demanda = Demanda(
            titulo=self.titulo.value,
            data_entrega=self.data_entrega.value,
            tipo_servico=self.tipo_servico.value,
            contato_cliente=self.contato.value,
            autor_id=interaction.user.id
        )
        demandas_abertas[demanda.id] = demanda

        lideres_channel = interaction.guild.get_channel(LIDERES_CHANNEL_ID)
        if not isinstance(lideres_channel, discord.TextChannel):
            return await interaction.response.send_message("Canal de líderes não encontrado ou inválido.", ephemeral=True)

        view = View()

        async def aceitar_callback(i: discord.Interaction):
            if not any(role.id == LIDER_ROLE_ID for role in i.user.roles):
                return await i.response.send_message("Apenas líderes podem aceitar demandas.", ephemeral=True)

            demanda.lider_id = i.user.id
            view.clear_items()
            await i.message.edit(content=f"Demanda **{demanda.titulo}** aceita por {i.user.mention}", view=None)

            view_roles = View()

            for funcao in FUNCAO_ROLES:
                button = Button(label=funcao, style=discord.ButtonStyle.primary)

                async def role_callback(inter: discord.Interaction, func=funcao):
                    if func in demanda.roles_necessarias:
                        demanda.roles_necessarias.remove(func)
                    else:
                        demanda.roles_necessarias.append(func)
                    await inter.response.defer()

                button.callback = lambda inter, f=funcao: role_callback(inter, f)
                view_roles.add_item(button)

            confirmar_button = Button(label="Confirmar", style=discord.ButtonStyle.success)

            async def confirmar_roles_callback(inter: discord.Interaction):
                await inter.response.send_message("Quantos colaboradores são necessários no total? (1-10)", ephemeral=True)

                def check(msg):
                    return msg.author == inter.user and msg.channel == inter.channel and msg.content.isdigit()

                try:
                    msg = await bot.wait_for("message", timeout=30, check=check)
                    demanda.quantidade_necessaria = int(msg.content)
                    await iniciar_busca_colaboradores(demanda, inter.guild)
                except:
                    await inter.followup.send("Tempo esgotado para resposta. Demanda cancelada.", ephemeral=True)

            confirmar_button.callback = confirmar_roles_callback
            view_roles.add_item(confirmar_button)

            await i.response.send_message("Selecione as funções dos colaboradores necessários:", view=view_roles, ephemeral=True)

        aceitar_button = Button(label="Aceitar Demanda", style=discord.ButtonStyle.success)
        aceitar_button.callback = aceitar_callback
        view.add_item(aceitar_button)

        await lideres_channel.send(
            f"Nova demanda criada por {interaction.user.mention}\n"
            f"**Título:** {demanda.titulo}\n"
            f"**Entrega:** {demanda.data_entrega}\n"
            f"**Tipo:** {demanda.tipo_servico}\n"
            f"**Contato:** {demanda.contato_cliente}",
            view=view
        )

        await interaction.response.send_message(f"Demanda **{demanda.titulo}** registrada com sucesso!", ephemeral=True)

async def iniciar_busca_colaboradores(demanda: Demanda, guild: discord.Guild):
    canal = guild.get_channel(COLABORADORES_CHANNEL_ID)
    if not isinstance(canal, discord.TextChannel):
        return

    view = View()

    for funcao in demanda.roles_necessarias:
        botao = Button(label=funcao, style=discord.ButtonStyle.primary)

        async def callback(inter: discord.Interaction, f=funcao):
            if inter.user.id in demanda.colaboradores:
                return await inter.response.send_message("Você já está participando dessa demanda.", ephemeral=True)

            if not any(role.id == FUNCAO_ROLES[f] for role in inter.user.roles):
                return await inter.response.send_message(f"Você não tem o cargo necessário para se inscrever como {f}.", ephemeral=True)

            demanda.colaboradores.append(inter.user.id)
            await inter.response.send_message(f"Você foi adicionado à demanda **{demanda.titulo}** como **{f}**.", ephemeral=True)

            if len(demanda.colaboradores) >= demanda.quantidade_necessaria and not demanda.chat_criado:
                demanda.chat_criado = True  # <- Marcado imediatamente para evitar duplicação

                categoria = discord.utils.get(guild.categories, name="Demandas")
                if not categoria:
                    categoria = await guild.create_category("Demandas")

                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(view_channel=False),
                }

                lider = guild.get_member(demanda.lider_id)
                if lider:
                    overwrites[lider] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

                for uid in demanda.colaboradores:
                    membro = guild.get_member(uid)
                    if membro:
                        overwrites[membro] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

                nome_formatado = demanda.titulo.lower().replace(" ", "-")[:80]
                canal_chat = await guild.create_text_channel(nome_formatado, category=categoria, overwrites=overwrites)
                await canal_chat.send(f"Bem-vindos à demanda **{demanda.titulo}**! Organizem-se aqui.")

                if demanda.mensagem_colaboradores:
                    await demanda.mensagem_colaboradores.edit(content=f"Demanda **{demanda.titulo}** concluída! Chat criado.", view=None)

        botao.callback = callback
        view.add_item(botao)

    embed = discord.Embed(
        title=f"Nova Demanda: {demanda.titulo}",
        description=(
            f"**Tipo de Serviço:** {demanda.tipo_servico}\n"
            f"**Data de Entrega:** {demanda.data_entrega}\n"
            f"**Contato do Cliente:** {demanda.contato_cliente}\n"
            f"**Funções Necessárias:** {', '.join(demanda.roles_necessarias)}\n\n"
            "Clique em um dos botões abaixo para participar!"
        ),
        color=discord.Color.blue()
    )
    embed.set_footer(text="Assim que o número necessário de colaboradores for atingido, um canal será criado.")

    mensagem = await canal.send(embed=embed, view=view)
    demanda.mensagem_colaboradores = mensagem

@bot.tree.command(name="gravar", description="Registrar nova demanda")
async def gravar(interaction: discord.Interaction):
    await interaction.response.send_modal(GravarModal())

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}!")
    try:
        synced = await bot.tree.sync()
        print(f"Comandos sincronizados: {len(synced)}")
    except Exception as e:
        print(f"Erro ao sincronizar comandos: {e}")

bot.run(TOKEN)
