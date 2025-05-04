from __future__ import annotations
import io, json, os, re, sys, requests
from datetime import datetime
from pathlib import Path
from PIL import Image
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(usecwd=True), override=True)

CLIENT_ID = os.getenv("TWITCH_CLIENT_ID") or os.getenv("CLIENT_ID")
ACCESS_TOKEN = os.getenv("TWITCH_OAUTH_TOKEN") or os.getenv("ACCESS_TOKEN")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")


def _fetch_app_token() -> str:
    if not CLIENT_ID or not CLIENT_SECRET:
        raise RuntimeError("Need CLIENT_ID and CLIENT_SECRET to fetch a token")
    url = "https://id.twitch.tv/oauth2/token"
    params = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "client_credentials",
    }
    r = requests.post(url, params=params, timeout=30)
    r.raise_for_status()
    tok = r.json()["access_token"]
    return tok


if not ACCESS_TOKEN:
    print("[init] No ACCESS_TOKEN found – requesting a fresh App token…")
    try:
        ACCESS_TOKEN = _fetch_app_token()
        print("[init] Got new token ✓")
    except Exception as ex:
        print(f"[init] Token fetch FAILED: {ex}", file=sys.stderr)

BASE_DIR = Path(r"D:\Archiver\persons\MichiMochievee\twitch\emotes")
DIR_7TV = BASE_DIR / "7tv"
DIR_TWITCH = BASE_DIR / "official"

SEVENTV_USER_ID = "01HVVN0NE800000R4ZCT3E1978"
BROADCASTER_ID = "1057785822"

THUMB_SIZE, PREVIEW_SIZE, GRID_COLS = 96, 256, 8

SAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


def norm(name: str) -> str:
    clean = SAFE_CHARS.sub("_", name).strip("_")
    return clean or "emote"


def _utc() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _save_meta(folder: Path, items: list[dict]) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "metadata.json").write_text(json.dumps(items, indent=2), "utf-8")


def fetch_7tv_emotes():
    import requests

    DIR_7TV.mkdir(parents=True, exist_ok=True)

    user = requests.get(f"https://7tv.io/v3/users/{SEVENTV_USER_ID}", timeout=30).json()
    es = next(
        (
            c["emote_set"]
            for c in user.get("connections", [])
            if c.get("platform") == "TWITCH" and "emote_set" in c
        ),
        None,
    )
    if not es:
        raise RuntimeError("No 7TV Twitch set")

    added = same = failed = 0
    meta = []

    for emo in es.get("emotes", []):
        name = emo["name"]
        eid = emo["id"]
        url = f"https:{emo['data']['host']['url']}/4x.webp"
        fp = DIR_7TV / f"{eid}_{norm(name)}.webp"

        if fp.exists():
            same += 1
        else:
            try:
                fp.write_bytes(requests.get(url, timeout=30).content)
                added += 1
            except Exception as ex:
                failed += 1
                print(f"[7TV]  !! {name}: {ex}", file=sys.stderr)
                continue

        meta.append(
            {
                "name": name,
                "id": eid,
                "source": "7tv",
                "owner": emo["data"].get("owner", {}).get("display_name", "unknown"),
                "animated": emo["data"].get("animated", False),
                "created_at": emo["data"].get("created_at"),
                "tags": emo["data"].get("tags", []),
                "path": str(fp),
                "downloaded_at": _utc(),
            }
        )

    _save_meta(DIR_7TV, meta)
    return meta, added, same, failed


def _helix(endpoint: str, params: dict | None = None) -> dict:
    if not CLIENT_ID or not ACCESS_TOKEN:
        raise RuntimeError("CLIENT_ID or ACCESS_TOKEN missing")
    h = {"Client-ID": CLIENT_ID, "Authorization": f"Bearer {ACCESS_TOKEN}"}
    r = requests.get(
        f"https://api.twitch.tv/helix/{endpoint}", headers=h, params=params, timeout=30
    )
    r.raise_for_status()
    return r.json()


def fetch_twitch_emotes():
    def png_url(eid):
        return f"https://static-cdn.jtvnw.net/emoticons/v2/{eid}/default/dark/3.0"

    DIR_TWITCH.mkdir(parents=True, exist_ok=True)

    glb = _helix("chat/emotes/global")["data"]
    chn = _helix("chat/emotes", {"broadcaster_id": BROADCASTER_ID})["data"]
    all_e = glb + chn

    added = same = failed = 0
    meta = []

    for e in all_e:
        name, eid = e["name"], e["id"]
        fp = DIR_TWITCH / f"{eid}_{norm(name)}.webp"

        if fp.exists():
            same += 1
        else:
            try:
                png = requests.get(png_url(eid), timeout=30).content
                img = Image.open(io.BytesIO(png)).convert("RGBA")
                img.save(fp, "WEBP")
                added += 1
            except Exception as ex:
                failed += 1
                print(f"[Twitch] !! {name}: {ex}", file=sys.stderr)
                continue

        meta.append(
            {
                "name": name,
                "id": eid,
                "source": "official",
                "owner": "Twitch",
                "animated": False,
                "created_at": None,
                "tags": [],
                "path": str(fp),
                "downloaded_at": _utc(),
            }
        )

    _save_meta(DIR_TWITCH, meta)
    return meta, added, same, failed
