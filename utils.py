import yt_dlp


def get_video_info(video_url: str):
    ydl_options = {
            "format": "bestaudio[abr<=96]/bestaudio",
            "noplaylist": True,
            "youtube_include_dash_manifest": False,
            "youtube_include_hls_manifest": False,
            "extractor_args": {"youtube": "player_client=mweb" },
        }

    with yt_dlp.YoutubeDL(ydl_options) as ydl:
        info = ydl.extract_info(video_url, download=False)
        
        title = info.get("title", "Sem título")
        url = info.get("url", video_url)  

        return {"title": title, "url": url}

import sqlite3
import json
from typing import Any, Optional

class LocalStorage:
    def __init__(self, db_name: str = "localstorage.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self._create_table()

    def _create_table(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS storage (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        self.conn.commit()

    def set_item(self, key: str, value: Any):
        """Salva ou atualiza um valor. Valores complexos são convertidos em JSON."""
        value_json = json.dumps(value)
        self.cursor.execute("""
            INSERT INTO storage (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
        """, (key, value_json))
        self.conn.commit()

    def get_item(self, key: str) -> Optional[Any]:
        """Retorna o valor correspondente à chave ou None se não existir."""
        self.cursor.execute("SELECT value FROM storage WHERE key = ?", (key,))
        result = self.cursor.fetchone()
        if result is None:
            return None
        return json.loads(result[0])

    def remove_item(self, key: str):
        """Remove uma chave do armazenamento."""
        self.cursor.execute("DELETE FROM storage WHERE key = ?", (key,))
        self.conn.commit()

    def clear(self):
        """Limpa todos os dados do armazenamento."""
        self.cursor.execute("DELETE FROM storage")
        self.conn.commit()

    def keys(self):
        """Retorna todas as chaves salvas."""
        self.cursor.execute("SELECT key FROM storage")
        return [row[0] for row in self.cursor.fetchall()]

    def __del__(self):
        self.conn.close()

# ===== Exemplo de uso =====
if __name__ == "__main__":
    storage = LocalStorage()

    playlist = storage.get_item("overdose")
    playlist.append({"title": "New Song", "url": "http://example.com/newsong"})
    storage.set_item("overdose", playlist)
    print(storage.get_item("overdose"))

