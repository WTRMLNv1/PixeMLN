# functions\pixelaAPI.py
# Encapsulate Pixela HTTP interactions and retry logic
# NOTE: This file is not used yet; planned for a future feature to import data from pixela into the local JSON store.
# -----------------------------------------------------------------------------------------
import requests
import time


def fetch_with_retry(url, headers=None, max_retries=5, delay=1):
    """Fetch JSON with retries for 503 or Pixela "isRejected" responses."""
    for attempt in range(max_retries):
        resp = requests.get(url, headers=headers)
        if resp.status_code == 503:
            time.sleep(delay)
            continue
        try:
            j = resp.json()
            if j.get("isRejected"):
                time.sleep(delay)
                continue
            return j
        except Exception:
            return None
    return None


def fetch_pixels(username, graph_id, token, with_body=True, max_retries=5, delay=2):
    """Return a dict mapping date-string (YYYYMMDD) -> int(quantity), or None on failure."""
    headers = {"X-USER-TOKEN": token}
    url = f"https://pixe.la/v1/users/{username}/graphs/{graph_id}/pixels"
    if with_body:
        url += "?withBody=true"

    data = fetch_with_retry(url, headers=headers, max_retries=max_retries, delay=delay)
    if not data:
        return None

    pixels = {}
    for entry in data.get("pixels", []):
        d = entry.get("date")
        try:
            q = int(entry.get("quantity", 0))
        except Exception:
            q = 0
        pixels[d] = q

    return pixels

print(fetch_pixels())
