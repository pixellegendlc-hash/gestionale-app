"""
db.py — Livello database GitHub
Tutte le operazioni di lettura/scrittura sui file JSON e foto.
"""
import os, json, base64, requests
from functools import lru_cache

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_OWNER = os.environ.get("GITHUB_OWNER", "")
GITHUB_REPO  = os.environ.get("GITHUB_REPO",  "")

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

BASE_URL = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents"

_cache: dict = {}

# ─────────────────────────────────────────
# JSON FILES
# ─────────────────────────────────────────
def read(filename: str, default=None):
    if default is None:
        default = []
    if filename in _cache:
        return _cache[filename]["data"], _cache[filename]["sha"]
    r = requests.get(f"{BASE_URL}/{filename}", headers=HEADERS, timeout=10)
    if r.status_code == 404:
        return default, None
    if r.status_code != 200:
        return default, None
    body = r.json()
    data = json.loads(base64.b64decode(body["content"]).decode("utf-8"))
    _cache[filename] = {"data": data, "sha": body["sha"]}
    return data, body["sha"]

def write(filename: str, data) -> bool:
    _, sha = read(filename)
    payload = {
        "message": f"update {filename}",
        "content": base64.b64encode(
            json.dumps(data, indent=2, ensure_ascii=False).encode()
        ).decode()
    }
    if sha:
        payload["sha"] = sha
    r = requests.put(f"{BASE_URL}/{filename}", headers=HEADERS, json=payload, timeout=15)
    if r.status_code in (200, 201):
        _cache[filename] = {"data": data, "sha": r.json()["content"]["sha"]}
        return True
    print(f"Write error {filename}: {r.status_code} {r.text}")
    return False

def invalidate(filename: str):
    _cache.pop(filename, None)

def invalidate_all():
    _cache.clear()

# ─────────────────────────────────────────
# PHOTO FILES
# ─────────────────────────────────────────
def list_photos(group: str = None) -> list:
    path = f"{BASE_URL}/photos"
    if group:
        path = f"{BASE_URL}/photos/{group}"
    r = requests.get(path, headers=HEADERS, timeout=10)
    if r.status_code != 200:
        return []
    items = r.json()
    photos = []
    for item in items:
        if item["type"] == "file" and any(
            item["name"].lower().endswith(ext)
            for ext in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")
        ):
            photos.append({
                "name":    item["name"],
                "path":    item["path"],
                "sha":     item["sha"],
                "size":    item.get("size", 0),
                "group":   group or "Tutte",
                "download_url": item.get("download_url", "")
            })
        elif item["type"] == "dir":
            # subfolder = group
            photos.extend(list_photos(item["name"]))
    return photos

def list_groups() -> list:
    r = requests.get(f"{BASE_URL}/photos", headers=HEADERS, timeout=10)
    if r.status_code != 200:
        return []
    return ["Tutte"] + [
        item["name"] for item in r.json()
        if item["type"] == "dir"
    ]

def upload_photo(filename: str, content_b64: str, group: str = None) -> bool:
    path = f"photos/{group}/{filename}" if group else f"photos/{filename}"
    payload = {
        "message": f"upload photo {filename}",
        "content": content_b64
    }
    r = requests.put(f"{BASE_URL}/{path}", headers=HEADERS, json=payload, timeout=30)
    return r.status_code in (200, 201)

def delete_photo(photo_path: str, sha: str) -> bool:
    payload = {"message": f"delete {photo_path}", "sha": sha}
    r = requests.delete(f"{BASE_URL}/{photo_path}", headers=HEADERS, json=payload, timeout=10)
    return r.status_code == 200

def create_group(group_name: str) -> bool:
    """Crea un gruppo (cartella) mettendoci un .gitkeep"""
    payload = {
        "message": f"create group {group_name}",
        "content": base64.b64encode(b"").decode()
    }
    r = requests.put(
        f"{BASE_URL}/photos/{group_name}/.gitkeep",
        headers=HEADERS, json=payload, timeout=10
    )
    return r.status_code in (200, 201)
