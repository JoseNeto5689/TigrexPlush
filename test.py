import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
import json
import re
import time

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept-Language": "en-US,en;q=0.9"
}

def limpa_url_youtube(url: str) -> str:
    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        if "v" in params and params["v"]:
            return f"https://www.youtube.com/watch?v={params['v'][0]}"
        if parsed.netloc.endswith("youtu.be"):
            vid = parsed.path.lstrip("/")
            if vid:
                return f"https://www.youtube.com/watch?v={vid}"
    except Exception:
        pass
    return url

def _extract_ytinitialdata_from_html(html_text: str):
    """
    Procura por ytInitialData robustamente: tenta vários padrões e usa balanceamento
    de chaves para extrair um JSON válido.
    Retorna dict ou None.
    """
    # possíveis markers que precedem o JSON
    markers = [
        "ytInitialData =",
        "window[\"ytInitialData\"] =",
        "window['ytInitialData'] =",
        "var ytInitialData =",
        "ytInitialData:"
    ]
    for m in markers:
        idx = html_text.find(m)
        if idx == -1:
            continue
        # localizar o primeiro '{' após o marker
        start = html_text.find("{", idx)
        if start == -1:
            continue
        # balancear chaves para extrair o objeto inteiro
        i = start
        depth = 0
        in_string = False
        esc = False
        while i < len(html_text):
            ch = html_text[i]
            if ch == '"' and not esc:
                in_string = not in_string
            if not in_string:
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        candidate = html_text[start:i+1]
                        try:
                            return json.loads(candidate)
                        except Exception:
                            break  # se falhar, tentar próximo marker/ponto
            esc = (ch == "\\" and not esc)
            i += 1
    return None

def _find_related_from_initialdata(data):
    """
    Tenta vários caminhos dentro do JSON para achar vídeos relacionados.
    Retorna lista de dicts com keys possivelmente 'videoId' e 'lengthSeconds'.
    """
    candidates = []

    # caminhos conhecidos onde relacionados podem estar
    paths = [
        ["contents","twoColumnWatchNextResults","secondaryResults","secondaryResults","results"],
        ["contents","twoColumnWatchNextResults","secondaryResults","secondaryResults","results"],
        ["contents","twoColumnWatchNextResults","secondaryResults","results"],
        ["contents","twoColumnWatchNextResults","secondaryResults"],
    ]

    def walk(obj, path):
        cur = obj
        try:
            for p in path:
                cur = cur[p]
            return cur
        except Exception:
            return None

    for p in paths:
        chunk = walk(data, p)
        if not chunk:
            continue
        # chunk costuma ser lista de items; buscamos compactVideoRenderer / videoRenderer / compactVideoRenderer
        for item in chunk:
            if not isinstance(item, dict):
                continue
            # possíveis renderers
            vr = None
            for key in ("compactVideoRenderer","videoRenderer","compact_renderer","playlistVideoRenderer"):
                if key in item:
                    vr = item.get(key)
                    break
            if not vr:
                # em alguns casos o objeto está aninhado
                for k,v in item.items():
                    if isinstance(v, dict) and ("videoId" in v or "lengthText" in v):
                        vr = v
                        break
            if not vr or not isinstance(vr, dict):
                continue
            vid = vr.get("videoId")
            # length pode estar em lengthText -> simpleText ou in seconds
            length = None
            if "lengthText" in vr:
                lt = vr["lengthText"]
                if isinstance(lt, dict):
                    # procurar simpleText
                    length_str = lt.get("simpleText") or ""
                else:
                    length_str = str(lt)
                # converter "mm:ss" ou "hh:mm:ss" para segundos
                if length_str:
                    parts = [int(x) for x in length_str.strip().split(":") if x.isdigit() or x.isnumeric()]
                    if parts:
                        # mm:ss -> parts[-2], parts[-1]
                        sec = 0
                        mul = 1
                        for part in reversed(parts):
                            sec += part * mul
                            mul *= 60
                        length = sec
            else:
                # às vezes há lengthSeconds
                if "lengthSeconds" in vr:
                    try:
                        length = int(vr.get("lengthSeconds"))
                    except Exception:
                        length = None
            if vid:
                candidates.append({"videoId": vid, "lengthSeconds": length})
    return candidates

def _extract_related_with_requests(video_id: str):
    """
    Pega página do YouTube e extrai relacionados via ytInitialData fallback.
    Retorna lista de ids.
    """
    url = f"https://www.youtube.com/watch?v={video_id}"
    r = requests.get(url, headers=HEADERS, timeout=10)
    text = r.text
    # tentar extração robusta
    data = _extract_ytinitialdata_from_html(text)
    if not data:
        return []
    items = _find_related_from_initialdata(data)
    return items

def get_related_music(youtube_url: str, max_length_seconds=600) -> str:
    """
    Tenta encontrar um vídeo relacionado diferente do original.
    max_length_seconds: se não None, prefere vídeos com duração <= esse valor (padrão 600s = 10min).
    Retorna URL YouTube (sempre).
    """
    clean = limpa_url_youtube(youtube_url)
    parsed = urlparse(clean)
    params = parse_qs(parsed.query)
    video_id = params.get("v", [""])[0]
    if not video_id:
        return clean

    # 1) tentar via yt-dlp (mais confiável) se estiver instalado
    try:
        import yt_dlp
        ydl_opts = {"quiet": True, "skip_download": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
            except Exception:
                info = None

        related_candidates = []
        if info:
            # tentar campos diferentes que yt-dlp pode expor
            # 'related' ou 'related_videos' ou 'entries' ou 'recommendations'
            possible = []
            for key in ("related_videos","related","recommendations","entries","entries"):
                if key in info and info[key]:
                    possible.append(info[key])
            # also check player_response
            pr = info.get("player_response") or info.get("player_response_raw")
            if isinstance(pr, str):
                try:
                    prj = json.loads(pr)
                    # navegar prj for recommendations? tentaremos
                    possible.append(prj.get("recommendations") or prj)
                except Exception:
                    pass
            elif isinstance(pr, dict):
                possible.append(pr)

            # normalize to list of dicts with id and duration
            for block in possible:
                if not block:
                    continue
                # block could be list of dicts
                if isinstance(block, dict):
                    # try to extract 'videoId' keys inside nested dicts
                    # flatten
                    for v in block.values():
                        if isinstance(v, list):
                            for it in v:
                                if isinstance(it, dict):
                                    vid = it.get("id") or it.get("videoId") or it.get("video_id") or it.get("videoId")
                                    dur = it.get("duration") or it.get("length_seconds") or it.get("lengthSeconds") or it.get("duration_seconds")
                                    if vid:
                                        try:
                                            dur_int = int(dur) if dur else None
                                        except Exception:
                                            dur_int = None
                                        related_candidates.append({"videoId": vid, "lengthSeconds": dur_int})
                elif isinstance(block, list):
                    for it in block:
                        if not isinstance(it, dict):
                            continue
                        vid = it.get("id") or it.get("videoId") or it.get("video_id") or it.get("videoId")
                        dur = it.get("duration") or it.get("length_seconds") or it.get("lengthSeconds")
                        if not vid:
                            # sometimes nested under 'compactVideoRenderer'
                            for key in ("compactVideoRenderer","videoRenderer","playlistVideoRenderer"):
                                if key in it and isinstance(it[key], dict):
                                    vr = it[key]
                                    vid = vid or vr.get("videoId")
                                    # try lengthText
                                    if "lengthText" in vr:
                                        lt = vr["lengthText"]
                                        if isinstance(lt, dict):
                                            length_str = lt.get("simpleText") or ""
                                        else:
                                            length_str = str(lt)
                                        # parse mm:ss
                                        if length_str:
                                            parts = [int(x) for x in re.findall(r"\d+", length_str)]
                                            sec = 0
                                            mul = 1
                                            for part in reversed(parts):
                                                sec += part * mul
                                                mul *= 60
                                            dur = sec
                        try:
                            dur_int = int(dur) if dur else None
                        except Exception:
                            dur_int = None
                        if vid:
                            related_candidates.append({"videoId": vid, "lengthSeconds": dur_int})

        # filtrar e retornar primeiro válido
        seen = set()
        for cand in related_candidates:
            vid = cand.get("videoId")
            if not vid or vid == video_id or vid in seen:
                continue
            seen.add(vid)
            length = cand.get("lengthSeconds")
            if max_length_seconds and length is not None:
                if length <= max_length_seconds:
                    return f"https://www.youtube.com/watch?v={vid}"
                else:
                    continue
            else:
                return f"https://www.youtube.com/watch?v={vid}"
    except ImportError:
        # não tem yt-dlp, seguimos para fallback
        pass
    except Exception:
        # qualquer erro em yt-dlp, seguimos para fallback
        pass

    # 2) fallback robusto: extrair do HTML/ytInitialData
    try:
        items = _extract_related_with_requests(video_id)
        # items: list of dicts {'videoId':..., 'lengthSeconds':...}
        seen = set()
        for it in items:
            vid = it.get("videoId")
            if not vid or vid == video_id or vid in seen:
                continue
            seen.add(vid)
            length = it.get("lengthSeconds")
            if max_length_seconds and length is not None:
                if length <= max_length_seconds:
                    return f"https://www.youtube.com/watch?v={vid}"
                else:
                    continue
            else:
                return f"https://www.youtube.com/watch?v={vid}"
    except Exception:
        pass

    # 3) fallback final: tentar pegar qualquer href watch?v= diferente presente na página
    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        r = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "watch?v=" in href:
                candidate = href if href.startswith("http") else ("https://www.youtube.com" + href)
                parsed_c = urlparse(candidate)
                params_c = parse_qs(parsed_c.query)
                vid_c = params_c.get("v", [""])[0]
                if vid_c and vid_c != video_id:
                    return f"https://www.youtube.com/watch?v={vid_c}"
    except Exception:
        pass

    # tudo falhou → retorna original limpo
    return limpa_url_youtube(youtube_url)


# Exemplo de uso:
if __name__ == "__main__":
    test = "https://www.youtube.com/watch?v=KK3KXAECte4"
    print("Relacionado:", get_related_music(test))
