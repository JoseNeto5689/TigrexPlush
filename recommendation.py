import requests
from bs4 import BeautifulSoup
import json
import re

from urllib.parse import urlparse, parse_qs

def limpa_url_youtube(url: str) -> str:
    parsed = urlparse(url)
    params = parse_qs(parsed.query)

    # mantém somente o parâmetro "v"
    if "v" in params:
        video_id = params["v"][0]
        return f"https://www.youtube.com/watch?v={video_id}"
    
    # se a URL não tiver "v", retorna original
    return url


def get_youtube_recommendations(url: str):
    """
    Recebe a URL de um vídeo do YouTube e retorna uma lista de vídeos recomendados.
    """

    # Baixa o HTML da página
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Erro ao acessar a URL: {response.status_code}")

    html = response.text

    # O YouTube guarda informações em um JSON enorme no HTML
    # Procuramos por "ytInitialData"
    match = re.search(r"var ytInitialData = ({.*?});", html)
    if not match:
        raise Exception("Não foi possível localizar o ytInitialData no HTML.")

    data_json = match.group(1)
    data = json.loads(data_json)

    # Caminho até os vídeos recomendados
    items = (
        data["contents"]["twoColumnWatchNextResults"]["secondaryResults"]
        ["secondaryResults"]["results"]
    )   
    url = items[0]["lockupViewModel"]["rendererContext"]["commandContext"]["onTap"]["innertubeCommand"]["commandMetadata"]["webCommandMetadata"]["url"]
    title = items[0]["lockupViewModel"]["metadata"]["lockupMetadataViewModel"]["title"]["content"]
    return {"title": title, "url": limpa_url_youtube(f"https://www.youtube.com/{url}")}


print(get_youtube_recommendations("https://www.youtube.com/watch?v=0FCvzsVlXpQ"))