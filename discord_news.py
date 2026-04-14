import os
import time
import feedparser
from discord_webhook import DiscordWebhook, DiscordEmbed
from dotenv import load_dotenv
from datetime import datetime

# Carrega variáveis do arquivo .env
load_dotenv()

# ===== CONFIGURAÇÕES =====
RSS_FEED_URL = os.getenv("RSS_FEED_URL")
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# Filtros (palavras que você quer monitorar)
# PALAVRAS_CHAVE = [
#     "fed", "federal reserve", "powell",
#     "bitcoin", "btc", "ethereum", "eth", "crypto",
#     "brasil", "brazil", "bcb", "copom", "selic",
#     "juros", "interest rate", "inflation", "cpi"
# ]

PALAVRAS_CHAVE = [
   "BREAKING"
]

# Configurações de execução
ARQUIVO_CONTROLE = "noticias_enviadas.txt"
TEMPO_ESPERA = 30  # segundos entre verificações

# ===== FUNÇÕES =====
def carregar_noticias_enviadas():
    """Carrega o histórico de notícias já enviadas"""
    try:
        with open(ARQUIVO_CONTROLE, 'r', encoding='utf-8') as f:
            return set(line.strip() for line in f if line.strip())
    except FileNotFoundError:
        return set()

def salvar_noticia_enviada(link):
    """Registra uma notícia como enviada"""
    with open(ARQUIVO_CONTROLE, 'a', encoding='utf-8') as f:
        f.write(f"{link}\n")

def extrair_dominio(url):
    """Extrai o domínio de uma URL para exibição"""
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc
    except:
        return "financialjuice.com"

def enviar_para_discord(titulo, link, data_publicacao=None):
    """Envia a notícia formatada via webhook do Discord"""
    
    webhook = DiscordWebhook(url=WEBHOOK_URL, rate_limit_retry=True)
    
    # Cria embed do Discord
    embed = DiscordEmbed(
        title=titulo,
        description=f"[Clique para ler a notícia completa]({link})",
        color="03b2f8"  # Azul
    )
    
    # Informações adicionais
    embed.set_author(
        name="Financial Juice",
        url="https://financialjuice.com/",
        icon_url="https://financialjuice.com/favicon.ico"
    )
    
    # Adiciona fonte
    embed.add_embed_field(
        name="Fonte",
        value=extrair_dominio(link),
        inline=True
    )
    
    # Data de publicação (se disponível)
    if data_publicacao:
        embed.add_embed_field(
            name="Publicado em",
            value=data_publicacao.strftime("%d/%m/%Y %H:%M"),
            inline=True
        )
    
    embed.set_timestamp()
    embed.set_footer(text="Monitor RSS • Financial Juice")
    
    webhook.add_embed(embed)
    
    try:
        response = webhook.execute()
        if response.status_code == 200:
            return True
        else:
            print(f"❌ Erro Discord: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Erro ao enviar: {e}")
        return False

def processar_feed():
    """Processa o feed RSS e envia notícias relevantes"""
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 Verificando feed...")
    
    # Carrega histórico
    enviadas = carregar_noticias_enviadas()
    
    # Parse do RSS
    try:
        feed = feedparser.parse(RSS_FEED_URL)
    except Exception as e:
        print(f"❌ Erro ao acessar feed: {e}")
        return 0
    
    if feed.bozo:  # Erro no parse
        print(f"⚠️ Aviso: Feed mal formatado - {feed.bozo_exception}")
        return 0
    
    if not feed.entries:
        print("ℹ️ Nenhuma entrada encontrada no feed")
        return 0
    
    enviadas_agora = 0
    
    for entry in feed.entries[:20]:  # Limita a 20 mais recentes
        titulo = entry.title
        link = entry.link
        
        # Verifica se já foi enviada
        if link in enviadas:
            continue
        
        # Filtro por palavras-chave (case-insensitive)
        titulo_lower = titulo.lower()
        if any(palavra in titulo_lower for palavra in PALAVRAS_CHAVE):
            
            # Extrai data se disponível
            data_pub = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                from time import mktime
                data_pub = datetime.fromtimestamp(mktime(entry.published_parsed))
            
            print(f"  📰 {titulo[:80]}...")
            
            # Envia para Discord
            if enviar_para_discord(titulo, link, data_pub):
                salvar_noticia_enviada(link)
                enviadas.add(link)
                enviadas_agora += 1
                print(f"  ✅ Enviada com sucesso!")
            else:
                print(f"  ❌ Falha no envio")
            
            # Pequena pausa para não sobrecarregar
            time.sleep(1)
    
    return enviadas_agora

def main():
    """Loop principal"""
    print("=" * 50)
    print("🤖 BOT FINANCIAL JUICE INICIADO")
    print("=" * 50)
    print(f"📡 Monitorando: {RSS_FEED_URL}")
    print(f"🎯 Palavras-chave: {len(PALAVRAS_CHAVE)} configuradas")
    print(f"⏱️ Intervalo: {TEMPO_ESPERA} segundos")
    print("=" * 50)
    
    if not WEBHOOK_URL:
        print("❌ ERRO: Webhook do Discord não configurado!")
        print("   Verifique o arquivo .env")
        return
    
    # Contador de ciclos
    ciclo = 1
    
    while True:
        try:
            enviadas = processar_feed()
            
            if enviadas > 0:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ {enviadas} notícia(s) enviada(s)")
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ℹ️ Nenhuma notícia nova relevante")
            
            ciclo += 1
            print(f"⏳ Próxima verificação em {TEMPO_ESPERA} segundos...")
            time.sleep(TEMPO_ESPERA)
            
        except KeyboardInterrupt:
            print("\n👋 Bot interrompido pelo usuário")
            break
        except Exception as e:
            print(f"❌ Erro inesperado: {e}")
            print(f"⏳ Reiniciando em {TEMPO_ESPERA} segundos...")
            time.sleep(TEMPO_ESPERA)

if __name__ == "__main__":
    main()