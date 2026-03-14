import time, aiohttp, json, os
CFG = json.load(open(os.path.join(os.path.dirname(__file__),"..","config.json"),"r",encoding="utf-8"))

_cache = {"ltc_eur": (0.0, 0.0), "ltc_rates": ({}, 0.0)}
STATE_PATH = os.path.join(os.path.dirname(__file__), "state.json")

def _load_state():
    if not os.path.exists(STATE_PATH): return {}
    try: return json.load(open(STATE_PATH,"r",encoding="utf-8"))
    except Exception: return {}

def _save_state(obj: dict):
    try: json.dump(obj, open(STATE_PATH,"w",encoding="utf-8"))
    except Exception: pass

async def ltc_eur()->float:
    now = time.time(); val, exp = _cache.get("ltc_eur",(0.0,0.0))
    if now < exp and val>0: return val
    url = "https://api.coingecko.com/api/v3/simple/price?ids=litecoin&vs_currencies=eur"
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=10) as r:
                data = await r.json(); rate = float(data["litecoin"]["eur"])
    except Exception:
        rate = float(CFG["payments"]["pricing"].get("fallback_ltc_eur", 80.0))
    ttl = int(CFG["payments"]["pricing"].get("cache_seconds", 90))
    _cache["ltc_eur"] = (rate, now+ttl)
    st = _load_state(); st["last_ltc_eur"] = rate; _save_state(st)
    return rate

async def ltc_rates(codes: list[str] | tuple[str, ...] = ("eur", "usd")) -> dict[str, float]:
    """Fetch LTC rates for given fiat codes (cached)."""
    now = time.time(); cached, exp = _cache.get("ltc_rates", ({}, 0.0))
    if now < exp and cached:
        return cached
    vs = ",".join(codes)
    url = f"https://api.coingecko.com/api/v3/simple/price?ids=litecoin&vs_currencies={vs}"
    rates: dict[str, float] = {}
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=10) as r:
                data = await r.json()
                for code in codes:
                    if code in data.get("litecoin", {}):
                        rates[code] = float(data["litecoin"][code])
    except Exception:
        pass
    if not rates:
        # Fallback to last known EUR and mirror to others
        fallback = float(CFG["payments"]["pricing"].get("fallback_ltc_eur", 80.0))
        rates = {c: fallback for c in codes}
    ttl = int(CFG["payments"]["pricing"].get("cache_seconds", 90))
    _cache["ltc_rates"] = (rates, now + ttl)
    st = _load_state(); st["last_ltc_rates"] = rates; _save_state(st)
    return rates

def last_ltc_price()->float|None:
    st = _load_state(); return st.get("last_ltc_eur")
