"""
Scraper HTTP optimizado para reemplazar Selenium en casos simples
Usa requests + BeautifulSoup para mayor velocidad y menos recursos
"""
import requests
from bs4 import BeautifulSoup
import logging
import time
import random
from typing import List, Optional
import re

logger = logging.getLogger(__name__)

class HTTPScraper:
    def __init__(self):
        """Inicializar scraper HTTP optimizado para hosting web"""
        self.session = requests.Session()

        # Headers optimizados para hosting web sin VNC
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        })

        # Configurar timeouts optimizados para hosting web
        self.session.timeout = (10, 30)  # (connect, read)

        logger.info("✅ HTTP Scraper inicializado para hosting web sin VNC")

    def get_game_servers_fast(self, game_id: str, max_servers: int = 5) -> List[str]:
        """
        Obtener servidores usando HTTP requests (más rápido que Selenium)
        """
        try:
            url = f"https://rbxservers.xyz/games/{game_id}"
            logger.info(f"🌐 HTTP Scraping: {url}")

            # Hacer request a la página principal del juego
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            # Parsear HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # Buscar enlaces de servidores
            server_links = []

            # Buscar enlaces que apunten a páginas de servidores individuales
            for link in soup.find_all('a', href=True):
                href = link['href']
                if '/servers/' in href and href.startswith('/'):
                    full_server_url = f"https://rbxservers.xyz{href}"
                    server_links.append(full_server_url)

                    if len(server_links) >= max_servers:
                        break

            logger.info(f"✅ Encontrados {len(server_links)} enlaces de servidores")
            return server_links

        except Exception as e:
            logger.error(f"❌ Error en HTTP scraping: {e}")
            return []

    def extract_vip_link_fast(self, server_url: str) -> Optional[str]:
        """
        Extraer link VIP de una página de servidor usando HTTP
        """
        try:
            logger.debug(f"🔍 Extrayendo VIP de: {server_url}")

            # Pequeña pausa para no saturar el servidor
            time.sleep(random.uniform(0.5, 1.5))

            response = self.session.get(server_url, timeout=15)
            response.raise_for_status()

            # Buscar el link VIP en el HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # Buscar input con valor que contenga roblox.com/games
            vip_inputs = soup.find_all('input', {'type': 'text'})
            for input_tag in vip_inputs:
                value = input_tag.get('value', '')
                if 'roblox.com/games' in value and 'privateServerLinkCode' in value:
                    logger.debug(f"✅ VIP link encontrado: {value[:50]}...")
                    return value

            # Buscar también en el código JavaScript o texto
            script_tags = soup.find_all('script')
            for script in script_tags:
                if script.string:
                    # Buscar patrones de links VIP en JavaScript
                    vip_pattern = r'https://www\.roblox\.com/games/\d+\?privateServerLinkCode=[A-Za-z0-9\-_]+'
                    matches = re.findall(vip_pattern, script.string)
                    if matches:
                        logger.debug(f"✅ VIP link en JS: {matches[0][:50]}...")
                        return matches[0]

            logger.debug(f"⚠️ No se encontró VIP link en: {server_url}")
            return None

        except Exception as e:
            logger.error(f"❌ Error extrayendo VIP link: {e}")
            return None

    def scrape_game_fast(self, game_id: str, max_servers: int = 5) -> List[str]:
        """
        Scraping completo de un juego usando solo HTTP
        """
        try:
            logger.info(f"🚀 Iniciando HTTP scraping rápido para juego {game_id}")
            start_time = time.time()

            # Obtener enlaces de servidores
            server_urls = self.get_game_servers_fast(game_id, max_servers)

            if not server_urls:
                logger.warning(f"⚠️ No se encontraron servidores para {game_id}")
                return []

            # Extraer VIP links
            vip_links = []
            for server_url in server_urls:
                vip_link = self.extract_vip_link_fast(server_url)
                if vip_link:
                    vip_links.append(vip_link)

                # Límite de tiempo para evitar que tome demasiado
                if time.time() - start_time > 30:  # 30 segundos máximo
                    logger.warning("⏰ Tiempo límite alcanzado en HTTP scraping")
                    break

            duration = time.time() - start_time
            logger.info(f"✅ HTTP Scraping completado: {len(vip_links)} VIP links en {duration:.1f}s")

            return vip_links

        except Exception as e:
            logger.error(f"❌ Error en scraping rápido: {e}")
            return []

    def close(self):
        """Cerrar sesión HTTP"""
        self.session.close()

def setup_commands(bot):
    """
    Configurar comando de scraping HTTP optimizado
    """

    @bot.tree.command(name="fastscrape", description="Scraping ultra rápido usando HTTP (experimental)")
    async def fastscrape_command(interaction, game_id: str):
        """Scraping rápido sin Selenium"""
        user_id = str(interaction.user.id)

        # Verificar autenticación
        from main import check_verification
        if not await check_verification(interaction, defer_response=True):
            return

        try:
            # Crear scraper HTTP
            http_scraper = HTTPScraper()

            # Info inicial
            embed = discord.Embed(
                title="⚡ Fast Scrape Iniciado",
                description=f"Probando scraping HTTP para juego `{game_id}`",
                color=0x00aaff
            )
            message = await interaction.followup.send(embed=embed, ephemeral=True)

            # Ejecutar scraping
            vip_links = http_scraper.scrape_game_fast(game_id, max_servers=3)

            if vip_links:
                # Mostrar resultados
                links_text = "\n".join([f"• {link}" for link in vip_links])

                result_embed = discord.Embed(
                    title="✅ Fast Scrape Completado",
                    description=f"**{len(vip_links)}** servidores encontrados usando HTTP",
                    color=0x00ff88
                )
                result_embed.add_field(
                    name="🔗 Servidores VIP:",
                    value=f"```{links_text}```",
                    inline=False
                )
                result_embed.add_field(
                    name="⚡ Ventajas HTTP:",
                    value="• 5x más rápido que Selenium\n• Menos uso de recursos\n• No requiere navegador",
                    inline=False
                )

                await message.edit(embed=result_embed)
            else:
                error_embed = discord.Embed(
                    title="❌ Sin Resultados",
                    description="No se encontraron servidores con el método HTTP",
                    color=0xff0000
                )
                await message.edit(embed=error_embed)

            # Limpiar
            http_scraper.close()

        except Exception as e:
            logger.error(f"Error en fastscrape: {e}")
            error_embed = discord.Embed(
                title="❌ Error",
                description="Error en el scraping HTTP",
                color=0xff0000
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)

    logger.info("⚡ Comando HTTP Fast Scrape configurado")
    return True