# ═══════════════════════════════════════════════════════════════════════════
#   main.py — UNIFIED (web panel + bot worker + CLI)
# ═══════════════════════════════════════════════════════════════════════════

import os, sys, re, time, json, hmac, base64, uuid, random, math, struct
import socket, asyncio, threading, hashlib, subprocess, requests, aiohttp
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from protobuf_decoder.protobuf_decoder import Parser

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel

# ═══════════════════════════════════════════════════════════════════════════
#   SECTION 1 — REGION DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════
REGION_LIST = ["IND", "ID", "TH", "ME", "EUROPE", "VN", "BD", "PK", "TW",
               "RU", "NA", "SAC", "BR", "SG", "US"]

REGION_LANG = {"ME": "ar", "IND": "hi", "ID": "id", "VN": "vi", "TH": "th",
               "BD": "bn", "PK": "ur", "TW": "zh", "EUROPE": "fr", "RU": "ru",
               "NA": "na", "SAC": "es", "BR": "pt", "SG": "ms", "US": "us"}

REGION_GROUP = {
    "IND": "IND",
    "BR": "AMERICA", "US": "AMERICA", "NA": "AMERICA", "SAC": "AMERICA",
    "ID": "OTHERS",  "TH": "OTHERS",  "ME": "OTHERS",  "EUROPE": "OTHERS",
    "VN": "OTHERS",  "BD": "OTHERS",  "PK": "OTHERS",  "TW": "OTHERS",
    "RU": "OTHERS",  "SG": "OTHERS",
}

REGION_URLS = {
    "IND":     {"server": "https://loginbp.ppmainecoonghj.com/",
                "client": "https://client.ind.freefiremobile.com/"},
    "AMERICA": {"server": "https://loginbp.ppmainecoonghj.com/",
                "client": "https://client.us.freefiremobile.com/"},
    "OTHERS":  {"server": "https://loginbp.ppmainecoonghj.com/",
                "client": "https://loginbp.ppmainecoonghj.com/"},
}

# ═══════════════════════════════════════════════════════════════════════════
#   SECTION 2 — BOT CONFIG
# ═══════════════════════════════════════════════════════════════════════════
REGION               = "BD"
LANG                 = "bn"
LANG_CODE            = LANG
ACCOUNTS_FILE        = "squad_accounts.json"
DEVICES_FILE         = "device.json"
TOTAL_ACCOUNTS       = 4
SETTLE_AFTER_ALL_JOIN= 1.5
SQUAD_PLAYERS        = 4

FULL_STOP_SECONDS    = 5.0
MATCH_MAX_LIFETIME   = 700.0
MATCH_INFO_TIMEOUT   = 60.0

Play_Version = "1.132.1"
Ob_VeR       = "OB55"
LoGiN_UrL    = "https://loginbp.ppmainecoonghj.com/"

HARDCODED_CONFIG = {
    "latest_release_version": "OB55",
    "remote_version":         "1.132.9",
    "cdn_url":                "https://dl-bs.ggpolarbear.com/",
    "abhotupdate_cdn_url":    "https://dl-bs.ggpolarbear.com/",
    "client_ip":              "103.148.14.66",
    "vercfg_sign":            "c8e41b7a93f02d56e1a94c7b8203f5d1",
    "region":                 REGION, "lang": LANG, "country_code": REGION,
    "server_url":             "https://loginbp.ppmainecoonghj.com/",
    "client_url":             "https://clientbp.ppmainecoonghj.com/",
}

SERVER_URL   = REGION_URLS[REGION_GROUP.get(REGION, "OTHERS")]["server"]
CLIENT_URL   = REGION_URLS[REGION_GROUP.get(REGION, "OTHERS")]["client"]
ACCOUNT_FILE = "Account.json"

UDP_LOG_FILE = None
_LOGIN_LOCK  = asyncio.Lock()
CONTROL_FILE = "bot_control.json" # New control file

# ═══════════════════════════════════════════════════════════════════════════
#   SECTION 3 — CRYPTO KEYS
# ═══════════════════════════════════════════════════════════════════════════
KEY  = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
IV   = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])
Key, Iv = KEY, IV

_KEYSTREAM = bytes([
    0x30,0x30,0x30,0x32,0x30,0x31,0x37,0x30,0x30,0x30,0x30,0x30,0x32,0x30,0x31,0x37,
    0x30,0x30,0x30,0x30,0x30,0x32,0x30,0x31,0x37,0x30,0x30,0x30,0x30,0x30,0x32,0x30,
])

AUTH_AES_KEY = bytes([0x19, 0x47, 0xB9, 0x74, 0xD9, 0x73, 0xF3, 0x7F,
                      0x42, 0x06, 0x01, 0x38, 0x42, 0x00, 0x10, 0x30])
AUTH_AES_IV  = bytes([0x28, 0x7F, 0xCA, 0x7A, 0xF9, 0x67, 0xF3, 0x7A,
                      0x65, 0x02, 0x01, 0x10, 0x40, 0x40, 0x00, 0x30])
AUTH_CMD = 0x65
SESSION_HASH = "1ac4b80ecf0478a44203bf8fac6120f5"

# ═══════════════════════════════════════════════════════════════════════════
#   SECTION 4 — GARENA / DATADOME / PLAYSTORE CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════
APP_ID       = 100067
CLIENT_TYPE  = 2
SOURCE       = 2
SECRET       = "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3"
PASSWORD_RAW = "Eren"
PASSWORD     = hashlib.sha256(PASSWORD_RAW.encode()).hexdigest().upper()

GARENA_BASE  = "https://100067.connect.garena.com/api/v2/oauth"
REGISTER_URL = f"{GARENA_BASE}/guest:register"
GRANT_URL    = f"{GARENA_BASE}/guest/token:grant"

DATADOME_URL  = "https://datadome.garena.com/js/"
VER_URL_BASE  = "https://version.ggwhitehawk.com/live/ver.php"
PLAYSTORE_URL = "https://play.google.com/store/apps/details?id=com.dts.freefireth&hl=en&gl=US"

USER_AGENT_MSDK  = "GarenaMSDK/4.0.44(V2538 ;Android 16;en;US;app 1.132.1 2019121227;)"
USER_AGENT_UNITY = "UnityPlayer/2018.4.12f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)"
USER_AGENT_WEB   = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

MAX_WORKERS            = 10
MIN_REGISTER_INTERVAL  = 1.0
REGISTER_BACKOFF_START = 20.0
REGISTER_BACKOFF_MAX   = 180.0
REGISTER_MAX_RETRIES   = 12
DATADOME_MAX_RETRIES   = 4
VER_MAX_ATTEMPTS       = 3

CFG = {}
_total_target = 0
_success_count = 0
_failure_count = 0
_start_time = time.time()
_last_register_time = 0.0
_dd_session_cookie = None
_dd_expires_at = 0.0
_print_lock = threading.Lock()
_file_lock  = threading.Lock()
_gate_lock  = threading.Lock()
_dd_lock    = threading.Lock()
_count_lock = threading.Lock()

# ═══════════════════════════════════════════════════════════════════════════
#   SECTION 5 — COLORS, SYMBOLS, PROTOCOL TABLES
# ═══════════════════════════════════════════════════════════════════════════
R="\033[0m"; B="\033[1m"; D="\033[2m"; GR="\033[90m"; RD="\033[91m"
GN="\033[92m"; YL="\033[93m"; BL="\033[94m"; MG="\033[95m"; CY="\033[96m"; WH="\033[97m"

SYMBOLS = ["꧁","꧂","『","』","【","】","乂","么","メ","ツ","彡","々","〆","๛",
           "✿","❀","✧","✦","★","☆","✪","✯","✰","✮","⚡","☠","☣","☢",
           "♛","♚","♔","♕","♤","♠","♡","♥","♦","♣","∞","✓","✘","☯",
           "卍","۝","༒","༺","༻","⸸","⌁","ꨄ","࿐","ꪜ","ꫂ"]

PROTOCOL = {0:"NONE",1:"INIT",2:"HEARTBEAT",3:"MATCHMAKING",4:"STATS",5:"GROUP",
            6:"FRIEND",7:"MAIL",8:"INVENTORY",9:"BACKPACK",10:"ACTIVITY",11:"ACCOUNT",
            12:"CLAN",13:"PROFILE",14:"ROOM",15:"PRESENCE",16:"ELITEPASS",
            17:"RECONNECTION",18:"CHANNEL",19:"STORE",21:"PET",22:"MANUAL",
            23:"CHAMPIONSHIP",24:"ANTIADDICTION",25:"FRESH",26:"LINKAGE",27:"ATTENDANCE",
            28:"LIMITEDEVENT",29:"FFANTI",30:"CHAT",31:"CUP",32:"VIPCARD",34:"CREDITSCORE",
            35:"GAMESERVERMANAGER",36:"MINIGAME",37:"WORKSHOP",38:"CUSTOMEVENT",
            39:"ACHIEVEMENT",40:"GIN",41:"WEAPONPOWER",42:"CSRANKINGMATCH",
            43:"BRRANKINGMATCH",44:"OCCUPATION",45:"MODESTATS",46:"HIPPOINVENTORY",
            47:"PRIME",48:"TEAMTOPUP",49:"RELAYMART",50:"REMATCH",51:"GOOGLE_PLAY",
            52:"LBS",53:"SHAREDGACHA",54:"ESPORTS",55:"SOCIALHALL",
            101:"INITRANDOMMIN",150:"INITRANDOMMAX",
            151:"HEARTBEATRANDOMMIN",255:"HEARTBEATRANDOMMAX"}

GROUP_CMD = {0:"NONE",1:"CREATE",2:"INVITE",3:"INVITE_NTF",4:"ACCEPT",5:"REFUSE",
             6:"JOIN_NTF",7:"LEAVE",8:"LEAVE_NTF",9:"START",10:"START_NTF",11:"STOP",
             12:"STOP_NTF",13:"DISMISS_NTF",14:"GROUPINFO",15:"READY",16:"READY_NTF",
             17:"CHANGE",18:"CHANGE_NTF",19:"JOINROOM",20:"SPECTATEROOM",
             21:"SHOWEMOTE",22:"SHOWEMOTE_NTF",33:"JOIN",34:"JOINREQUEST_NTF",
             35:"KICKOUT",44:"ACCEPTJOIN_NTF",45:"START_ROOM_MATCHMAKING",
             46:"STOP_ROOM_MATCHMAKING",47:"START_ROOM_MATCHMAKING_NTF",
             48:"STOP_ROOM_MATCHMAKING_NTF",49:"CREATE_ROOM",55:"MIGRATE_GROUP",
             56:"MIGRATE_GROUP_NTF",57:"TRANSFER_LEADER",58:"TRANSFER_LEADER_NTF",
             102:"GROUP_NOTIFY_102"}
MATCHMAKING_CMD = {0:"NONE",1:"START",2:"CANCEL",3:"GROUPSTART",4:"GROUPCANCEL",
                   5:"MATCHMAKINGSUSS_NTF",6:"DROPMATCH",7:"GAMEOPENINGINFO",
                   8:"CHECKINGAMEPLAYER",9:"CLEARINGAMEPLAYER",10:"ANTIADDICTION_NTF",
                   11:"START_NTF",14:"STOP_NTF",15:"RANKING_BANNED",
                   16:"TEAMMATE_RANKING_BANNED",17:"CDT_HACKER_NTF",
                   18:"GETMATCHMAKINGINFO",19:"PUNISHINGAMEPLAYER",23:"SPECTATE"}
RECONNECTION_CMD = {0:"NONE",1:"RECONNECT",2:"TIMEOUT",3:"MATCHMAKINGSUSS_NTF",
                    4:"CANCEL",5:"GROUPINFO",6:"LEAVEMATCH_NTF"}
STATS_CMD = {0:"NONE",1:"MATCHSTATS_NTF",2:"UPDATEMMR_NTF"}
CMD_TABLES = {3:MATCHMAKING_CMD,4:STATS_CMD,5:GROUP_CMD,17:RECONNECTION_CMD}

UDP_CMD = {1:"UDP_HELLO",2:"UDP_ACK",3:"UDP_PING",4:"UDP_BYEBYE",5:"UDP_LONGTIMENOSEE",
           6:"MUDP_CONNECT_ACK",100:"RUDP_JOIN_MATCH",101:"RUDP_PLAYER_JOIN",
           102:"RUDP_PLAYER_QUIT",103:"RUDP_MATCH_END",107:"RUDP_DEAD",
           110:"RUDP_BATTLE_START",116:"RUDP_SYNC_SCENE_INFO",117:"RUDP_SAFE_ZONE",
           130:"RUDP_JOIN_MATCH_FINISHED",551:"RUDP_QUICK_CHAT",
           1901:"RUDP_GRI_SYNC",2000:"RUDP_SERVER_TIME",
           2001:"RUDP_MY_STATE",2012:"RUDP_OTHER_STATES",
           447:"RUDP_JOIN_MATCH_PREPARE",448:"RUDP_JOIN_MATCH_POST"}

LEAVE_REASONS = {0:"NORMAL",1:"OFFLINE",2:"DROPMATCH",3:"ALLJOINROOM",
                 4:"SOLOJOINROOM",5:"KICKOUT",6:"MERGEGROUP",7:"TIMEOUT"}

# ═══════════════════════════════════════════════════════════════════════════
#   SECTION 6 — LOG HELPERS & SHARED UTILITIES
# ═══════════════════════════════════════════════════════════════════════════
def _tag(i, n): return f"{i:>2}/{n}"

def step(tag, icon, msg, color=CY):
    with _print_lock:
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"{GR}{ts}{R} {color}{B}[{tag}]{R} {color}{icon}{R} {msg}", flush=True)

def ok(tag, msg):    step(tag, "✔", msg, GN)
def warn(tag, msg):  step(tag, "!", msg, YL)
def fail(tag, msg):  step(tag, "✘", msg, RD)
def info(tag, msg):  step(tag, "·", msg, GR)

def decorate_name(prefix, max_prefix_len=7):
    core  = prefix[:max_prefix_len]
    left  = ''.join(random.sample(SYMBOLS, 2))
    right = ''.join(random.sample(SYMBOLS, 2))
    return f"{left}{core}{right}"

def enc_aes(data): return AES.new(KEY, AES.MODE_CBC, IV).encrypt(pad(data, 16))
def dec_aes(data):
    try:    return unpad(AES.new(KEY, AES.MODE_CBC, IV).decrypt(data), 16)
    except ValueError: return AES.new(KEY, AES.MODE_CBC, IV).decrypt(data)

def sign_body(body): return hmac.new(SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()

def encode_open_id(open_id):
    return bytes(ord(open_id[i]) ^ _KEYSTREAM[i % len(_KEYSTREAM)] for i in range(len(open_id)))

def decode_jwt_payload(token):
    try:
        parts = token.split(".")
        if len(parts) != 3: return {}
        p2 = parts[1] + "=" * (-len(parts[1]) % 4)
        return json.loads(base64.urlsafe_b64decode(p2))
    except Exception:
        return {}

def enc_varint(v):
    out = bytearray()
    while True:
        b = v & 0x7F; v >>= 7
        out.append(b | (0x80 if v else 0))
        if not v: return bytes(out)

def read_varint(data, off):
    v, s = 0, 0
    while True:
        b = data[off]; off += 1
        v |= (b & 0x7F) << s
        if not (b & 0x80): return v, off
        s += 7

def ptag(f, wt): return enc_varint((f << 3) | wt)
def f_vint(f, n): return ptag(f, 0) + enc_varint(n)
def f_bytes(f, b): return ptag(f, 2) + enc_varint(len(b)) + b
def f_str(f, s):
    b = s.encode("utf-8"); return ptag(f, 2) + enc_varint(len(b)) + b

def parse_proto(data):
    fields = {}; i = 0
    while i < len(data):
        try: key, i = read_varint(data, i)
        except Exception: break
        fn, wt = key >> 3, key & 7
        try:
            if wt == 0:
                v, i = read_varint(data, i)
                fields.setdefault(fn, []).append(("varint", v))
            elif wt == 1:
                v = int.from_bytes(data[i:i+8], "little"); i += 8
                fields.setdefault(fn, []).append(("u64", v))
            elif wt == 2:
                ln, i = read_varint(data, i)
                raw = data[i:i+ln]; i += ln
                s_ok = False
                try:
                    s = raw.decode("utf-8")
                    if s.isprintable():
                        fields.setdefault(fn, []).append(("string", s)); s_ok = True
                except UnicodeDecodeError: pass
                if not s_ok:
                    fields.setdefault(fn, []).append(("bytes", raw.hex()))
            elif wt == 5:
                v = int.from_bytes(data[i:i+4], "little"); i += 4
                fields.setdefault(fn, []).append(("u32", v))
            else: break
        except Exception: break
    return fields

def first_value(fields, field_num, want_kind=None):
    for kind, v in fields.get(field_num, []):
        if want_kind is None or kind == want_kind: return v
    return None

def _to_bytes(v):
    if isinstance(v, bytes): return v
    if isinstance(v, str):
        try: return bytes.fromhex(v)
        except ValueError: return v.encode()
    if v is None: raise ValueError("cannot convert None")
    return bytes(v)

def _rbyte(region):
    reg = str(region or "BD").upper()
    if reg == "BD":  return 0x19
    if reg == "IND": return 0x14
    return 0x15

# ═══════════════════════════════════════════════════════════════════════════
#   SECTION 7 — ACCOUNT CREATION
# ═══════════════════════════════════════════════════════════════════════════
def _wait_register_slot(tag):
    global _last_register_time
    while True:
        with _gate_lock:
            now = time.time()
            wait = MIN_REGISTER_INTERVAL - (now - _last_register_time)
            if wait <= 0:
                _last_register_time = now; return
        time.sleep(min(wait, 0.5))

def get_play_store_version():
    headers = {"User-Agent": USER_AGENT_WEB, "Accept-Language": "en-US,en;q=0.9"}
    html = requests.get(PLAYSTORE_URL, headers=headers, timeout=15).text
    versions = re.findall(r"\b(1\.\d{1,3}\.\d{1,3})\b", html)
    if not versions: raise RuntimeError("no version on playstore page")
    real = [v for v in versions if v != "1.000.000"]
    return (real or versions)[-1]

def fetch_ver_config(initial_version):
    version = initial_version; last = None
    for attempt in range(1, VER_MAX_ATTEMPTS + 1):
        url = (f"{VER_URL_BASE}?version={version}"
               f"&lang={LANG_CODE}&device=android&channel=3rd_party&appstore=thirdparty"
               f"&region={REGION}&whitelist_version=1.7.0&whitelist_sp_version=1.0.0"
               f"&device_name=vivo%20V2538"
               f"&device_CPU=ARM64%20FP%20ASIMD%20AES"
               f"&device_GPU=Adreno%20%28TM%29%20722"
               f"&device_mem=7282")
        try: cfg = requests.get(url, timeout=15).json()
        except Exception as e:
            last = e; time.sleep(1.0 * attempt); continue
        if cfg.get("code") == 0:
            cfg["region"] = REGION; cfg["lang"] = LANG_CODE; cfg["country_code"] = REGION
            cfg["server_url"] = SERVER_URL; cfg["client_url"] = CLIENT_URL
            return cfg
        if cfg.get("remote_version"): version = cfg["remote_version"]
        last = cfg; time.sleep(1.0 * attempt)
    raise RuntimeError(f"ver.php failed: {last}")

def get_datadome(tag, force=False):
    global _dd_session_cookie, _dd_expires_at
    with _dd_lock:
        now = time.time()
        if not force and _dd_session_cookie and _dd_expires_at > now:
            return _dd_session_cookie
        headers = {
            "User-Agent": USER_AGENT_WEB, "Content-Type": "application/x-www-form-urlencoded",
            "Referer": "https://sso.garena.com/universal/register?locale=en-SG",
            "Origin": "https://sso.garena.com",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
        }
        payload = {
            "jsType":"le","eventCounters":'{"mousemove":1,"click":1,"keydown":11}',
            "ddk":"AE3F04AD3F0D3A462481A337485081",
            "Referer":"https://sso.garena.com/universal/register?locale=en-SG",
            "request":"/universal/register?locale=en-SG",
            "responsePage":"origin","ddv":"5.7.0",
        }
        last = None
        for attempt in range(1, DATADOME_MAX_RETRIES + 1):
            try:
                r = requests.post(DATADOME_URL, data=payload, headers=headers, timeout=15)
                r.raise_for_status(); result = r.json()
            except Exception as e:
                last = e; time.sleep(1.5 * attempt); continue
            if result.get("status") == 200 and result.get("cookie"):
                for part in result["cookie"].split(";"):
                    if "datadome=" in part:
                        dd = part.replace("datadome=", "").strip()
                        if dd:
                            _dd_session_cookie = dd
                            _dd_expires_at = now + 300.0
                            ok(tag, f"{D}datadome{R} {GN}acquired{R} {GR}({len(dd)} chars){R}")
                            return dd
            last = result; time.sleep(1.5 * attempt)
        raise RuntimeError(f"DataDome failed: {last}")

def guest_register(tag, device_id, max_retries=REGISTER_MAX_RETRIES):
    payload = {"app_id": APP_ID, "client_type": CLIENT_TYPE,
               "password": PASSWORD, "source": SOURCE}
    body = json.dumps(payload, separators=(",", ":"))
    last_err = None
    for attempt in range(1, max_retries + 1):
        _wait_register_slot(tag)
        datadome = get_datadome(tag, force=(attempt > 1 and attempt % 3 == 0))
        headers = {
            "User-Agent": USER_AGENT_MSDK,
            "Authorization": f"Signature {sign_body(body)}",
            "Cookie": f"datadome={datadome}",
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
        }
        try:
            r = requests.post(REGISTER_URL, data=body, headers=headers, timeout=25)
            data = r.json()
        except Exception as e:
            last_err = e; warn(tag, f"register net-err ({attempt}/{max_retries})")
            time.sleep(2.0 * attempt); continue
        code = data.get("code")
        if code == 0:
            uid = data["data"]["uid"]
            ok(tag, f"register {D}uid{R}={WH}{uid}{R}"); return uid
        if code in (1006, 1005):
            wait = min(REGISTER_BACKOFF_START * (2 ** (attempt - 1)), REGISTER_BACKOFF_MAX)
            warn(tag, f"register {code} cooling {YL}{wait:.0f}s{R} ({attempt}/{max_retries})")
            last_err = data; time.sleep(wait); continue
        raise RuntimeError(f"guest:register failed: {data}")
    raise RuntimeError(f"guest:register gave up: {last_err}")

def guest_token(tag, uid, device_id):
    payload = {
        "client_id": APP_ID, "client_secret": SECRET, "client_type": CLIENT_TYPE,
        "device_id": device_id, "password": PASSWORD,
        "response_type": "token", "uid": uid,
    }
    body = json.dumps(payload, separators=(",", ":"))
    datadome = get_datadome(tag)
    headers = {
        "User-Agent": USER_AGENT_MSDK, "Cookie": f"datadome={datadome}",
        "Accept": "application/json",
        "Content-Type": "application/json; charset=utf-8",
    }
    r = requests.post(GRANT_URL, data=body, headers=headers, timeout=20)
    data = r.json()
    if data.get("code") != 0:
        raise RuntimeError(f"guest/token:grant failed: {data}")
    tokens = data["data"]
    ok(tag, f"token    {D}open_id{R}={WH}{tokens['open_id'][:16]}…{R}  "
           f"{D}platform{R}={tokens.get('platform')}")
    return tokens

def generate_nickname(tag, open_id, cfg):
    url = cfg["server_url"].rstrip("/") + "/GenerateNickname"
    body = f_bytes(2, encode_open_id(open_id))
    headers = {
        "User-Agent": USER_AGENT_UNITY, "Accept": "*/*", "Accept-Encoding": "deflate, gzip",
        "Authorization": "Bearer", "X-GA": "v1 1",
        "X-GA-SV": str(int(time.time())),
        "ReleaseVersion": cfg["latest_release_version"],
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Unity-Version": "2018.4.12f1",
    }
    r = requests.post(url, data=enc_aes(body), headers=headers, timeout=20)
    fields = parse_proto(r.content); nickname = None; payload = None
    for kind, v in fields.get(1, []):
        if kind == "string": nickname = v; break
        if kind == "bytes":  payload = bytes.fromhex(v)
    if nickname is None and payload is not None:
        decoded = bytes(b ^ _KEYSTREAM[i % len(_KEYSTREAM)] for i, b in enumerate(payload))
        nickname = "".join(chr(b) for b in decoded if 0x20 <= b <= 0x7E)
    if not nickname: raise RuntimeError(f"Nickname not found: {r.content.hex()}")
    ok(tag, f"name     {MG}{nickname}{R}")
    return nickname

def major_register(tag, open_id, access_token, name, cfg):
    url = cfg["server_url"].rstrip("/") + "/MajorRegister"
    body  = f_str(1, name)
    body += f_str(2, access_token)
    body += f_str(3, open_id)
    body += f_vint(5, 102000007)
    body += f_vint(6, 4)
    body += f_vint(7, 1)
    body += f_vint(13, 1)
    body += f_bytes(14, encode_open_id(open_id))
    body += f_str(15, LANG_CODE)
    body += f_vint(16, 2)
    body += f_str(22, PASSWORD)
    headers = {
        "User-Agent": USER_AGENT_UNITY, "Accept": "*/*", "Accept-Encoding": "deflate, gzip",
        "Authorization": "Bearer", "X-GA": "v1 1",
        "X-GA-SV": str(int(time.time())),
        "ReleaseVersion": cfg["latest_release_version"],
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Unity-Version": "2018.4.12f1",
    }
    r = requests.post(url, data=enc_aes(body), headers=headers, timeout=20)
    fields = parse_proto(r.content)
    if first_value(fields, 1, "varint") != 1:
        raise RuntimeError(f"MajorRegister failed: {fields}")
    ok(tag, f"register {GN}game-account created{R}")

def build_major_login(open_id, access_token, cfg, platform, region=None):
    remote_version = cfg["remote_version"]; country = cfg["country_code"]
    cdn_url = cfg["cdn_url"]; abhot_cdn = cfg["abhotupdate_cdn_url"]
    client_ip = cfg["client_ip"]; vercfg_sign = cfg["vercfg_sign"]
    cdn_hash = hashlib.md5(f"{open_id}{time.time_ns()}".encode()).hexdigest()
    cdn_blob = f"{cdn_url}|{abhot_cdn}|{cdn_hash}"
    sig_base64 = ("KqsHTwFsNrz71lqUGAjS+qIySSj2KOGy6RrHPlpy6KkAVaY7JOEtuPh7yc+7ruAa8IoJQdj5KVD"
                  "vnuda+C89owjNtP1VCdBI3Q591QXRXy8qF6s/")
    b  = b""
    b += f_str(3, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    b += f_str(4, "free fire"); b += f_vint(5, 1)
    b += f_str(7, remote_version)
    b += f_str(8, "Android OS 16 / API-36 (BP2A.250605.031.A3_V000L1/compiler260320183556)")
    b += f_str(9, "Handheld"); b += f_str(11, "CarrierDataNetwork")
    b += f_vint(12, 1637); b += f_vint(13, 750); b += f_str(14, "440")
    b += f_str(15, "ARM64 FP ASIMD AES | 5606 | 8"); b += f_vint(16, 7282)
    b += f_str(17, "Adreno (TM) 722")
    b += f_str(18, "OpenGL ES 3.2 V@0800.69.2 (GIT@4659378004, I7f7aee143c, 1773055375) (Date:03/09/26)")
    b += f_str(19, "Google|c15d0cbb-0f10-4ad4-a960-739ca3891a93")
    b += f_str(20, client_ip); b += f_str(21, LANG_CODE); b += f_str(22, open_id)
    b += f_str(23, str(platform)); b += f_str(24, "Handheld"); b += f_str(25, "vivo V2538")
    if region is not None: b += f_str(26, region)
    b += f_str(29, access_token); b += f_vint(30, 1); b += f_str(42, "4G")
    b += f_str(57, SESSION_HASH); b += f_vint(60, 223554); b += f_vint(61, 100654)
    b += f_vint(62, 4465); b += f_vint(64, 100782); b += f_vint(65, 223554)
    b += f_vint(66, 100782); b += f_vint(67, 223554); b += f_vint(70, 4); b += f_vint(73, 1)
    b += f_str(74, "/data/app/~~Hl4pq6GoyauPV457pS4N8g==/com.dts.freefireth-mRT8MtqxsyyrZkxcQBSRAA==/lib/arm64")
    b += f_vint(76, 1)
    b += f_str(77, "066a589fa3f5658377634fe7b1d88556|/data/app/~~Hl4pq6GoyauPV457pS4N8g==/com.dts.freefireth-mRT8MtqxsyyrZkxcQBSRAA==/base.apk")
    b += f_vint(78, 6); b += f_vint(79, 2); b += f_str(81, "64"); b += f_str(83, "2019121227")
    b += f_vint(85, 3); b += f_str(86, "OpenGLES2"); b += f_vint(87, 8191)
    b += f_vint(88, platform); b += f_vint(92, 40843); b += f_str(93, "3rd_party")
    b += f_str(94, sig_base64); b += f_vint(95, 111207)
    b += f_str(96, '{"cur_rate":[60,90,120],"support_etc2":false}')
    b += f_vint(97, 1); b += f_vint(98, 1); b += f_str(99, str(platform))
    b += f_str(100, str(platform)); b += f_str(102, "42531243535e0e0531")
    b += f_vint(104, 84750); b += f_vint(105, 1)
    b += f_str(106, cdn_blob); b += f_str(107, vercfg_sign)
    return b

def major_login(tag, open_id, access_token, cfg, platform, region=None):
    url = cfg["server_url"].rstrip("/") + "/MajorLogin"
    plain = build_major_login(open_id, access_token, cfg, platform, region=region)
    headers = {
        "User-Agent": USER_AGENT_UNITY, "Accept": "*/*", "Accept-Encoding": "deflate, gzip",
        "Authorization": "Bearer", "X-GA": "v1 1",
        "X-GA-SV": str(int(time.time())),
        "ReleaseVersion": cfg["latest_release_version"],
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Unity-Version": "2018.4.12f1",
    }
    r = requests.post(url, data=enc_aes(plain), headers=headers, timeout=20)
    if r.status_code != 200: raise RuntimeError(f"MajorLogin HTTP {r.status_code}")
    attempts = [("plain", parse_proto(r.content))]
    if len(r.content) > 64: attempts.append(("plain[64:]", parse_proto(r.content[64:])))
    try: attempts.append(("dec", parse_proto(dec_aes(r.content))))
    except Exception: pass
    if len(r.content) > 64:
        try: attempts.append(("dec[64:]", parse_proto(dec_aes(r.content[64:]))))
        except Exception: pass
    fields = {}
    for _, f in attempts:
        if 8 in f or 22 in f: fields = f; break
    account_id = first_value(fields, 1, "varint")
    jwt        = first_value(fields, 8, "string")
    game_url   = first_value(fields, 10, "string")
    region_from_jwt = None
    payload = decode_jwt_payload(jwt) if jwt else {}
    if payload:
        region_from_jwt = payload.get("noti_region") or payload.get("lock_region")
    if (not jwt) or account_id is None or (isinstance(account_id, int) and account_id < 10_000_000):
        raise RuntimeError("MajorLogin implausible result")
    ok(tag, f"login    {D}id{R}={WH}{account_id}{R}  {D}jwt_region{R}={CY}{region_from_jwt or '—'}{R}")
    return {"account_id": account_id, "jwt": jwt, "game_url": game_url,
            "region": region_from_jwt or region, "fields": fields}

def choose_region(tag, jwt, cfg, region):
    url = cfg["server_url"].rstrip("/") + "/ChooseRegion"
    body = f_str(1, region)
    headers = {
        "User-Agent": USER_AGENT_UNITY, "Accept": "*/*", "Accept-Encoding": "deflate, gzip",
        "Authorization": f"Bearer {jwt}", "X-GA": "v1 1",
        "X-GA-SV": str(int(time.time())),
        "ReleaseVersion": cfg["latest_release_version"],
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Unity-Version": "2018.4.12f1",
    }
    r = requests.post(url, data=enc_aes(body), headers=headers, timeout=20)
    if r.status_code != 200: raise RuntimeError(f"ChooseRegion HTTP {r.status_code}")
    fields = parse_proto(r.content)
    confirmed = first_value(fields, 1, "string")
    if not confirmed:
        for alt in (2, 3, 4):
            confirmed = first_value(fields, alt, "string")
            if confirmed: break
    if not confirmed: raise RuntimeError("ChooseRegion returned no region")
    ok(tag, f"lock     {D}region{R}={MG}{confirmed}{R}")
    return confirmed

def build_get_login_data(open_id, access_token, cfg, platform, jwt):
    remote_version = cfg["remote_version"]; country = cfg["country_code"]
    cdn_url = cfg["cdn_url"]; abhot_cdn = cfg["abhotupdate_cdn_url"]
    client_ip = cfg["client_ip"]; vercfg_sign = cfg["vercfg_sign"]
    cdn_hash = hashlib.md5(f"{open_id}{time.time_ns()}".encode()).hexdigest()
    cdn_blob = f"{cdn_url}|{abhot_cdn}|{cdn_hash}"
    sig_base64 = ("KqsHTwFsNrz71lqUGAjS+qIySSj2KOGy6RrHPlpy6KkAVaY7JOEtuPh7yc+7ruAa8IoJQdj5KVD"
                  "vnuda+C89owjNtP1VCdBI3Q591QXRXy8qF6s/")
    b  = b""
    b += f_str(3, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    b += f_str(4, "free fire"); b += f_vint(5, 1)
    b += f_str(7, remote_version)
    b += f_str(8, "Android OS 16 / API-36 (BP2A.250605.031.A3_V000L1/compiler260320183556)")
    b += f_str(9, "Handheld"); b += f_str(11, "CarrierDataNetwork")
    b += f_vint(12, 1637); b += f_vint(13, 750); b += f_str(14, "440")
    b += f_str(15, "ARM64 FP ASIMD AES | 5606 | 8"); b += f_vint(16, 7282)
    b += f_str(17, "Adreno (TM) 722")
    b += f_str(18, "OpenGL ES 3.2 V@0800.69.2 (GIT@4659378004, I7f7aee143c, 1773055375) (Date:03/09/26)")
    b += f_str(19, "Google|c15d0cbb-0f10-4ad4-a960-739ca3891a93")
    b += f_str(20, client_ip); b += f_str(21, LANG_CODE); b += f_str(22, open_id)
    b += f_str(23, str(platform)); b += f_str(24, "Handheld"); b += f_str(25, "vivo V2538")
    b += f_str(26, country); b += f_str(29, access_token); b += f_vint(30, 1)
    b += f_str(42, "4G"); b += f_str(57, SESSION_HASH); b += f_vint(60, 223554)
    b += f_vint(61, 100654); b += f_vint(62, 4465); b += f_vint(64, 100782)
    b += f_vint(65, 223554); b += f_vint(66, 100782); b += f_vint(67, 223554)
    b += f_vint(70, 4); b += f_vint(73, 1)
    b += f_str(74, "/data/app/~~Hl4pq6GoyauPV457pS4N8g==/com.dts.freefireth-mRT8MtqxsyyrZkxcQBSRAA==/lib/arm64")
    b += f_vint(76, 1)
    b += f_str(77, "066a589fa3f5658377634fe7b1d88556|/data/app/~~Hl4pq6GoyauPV457pS4N8g==/com.dts.freefireth-mRT8MtqxsyyrZkxcQBSRAA==/base.apk")
    b += f_vint(78, 6); b += f_vint(79, 2); b += f_str(81, "64"); b += f_str(83, "2019121227")
    b += f_vint(85, 3); b += f_str(86, "OpenGLES2"); b += f_vint(87, 8191)
    b += f_vint(88, platform); b += f_vint(92, 40843); b += f_str(93, "3rd_party")
    b += f_str(94, sig_base64); b += f_vint(95, 111207)
    b += f_str(96, '{"cur_rate":[60,90,120],"support_etc2":false}')
    b += f_vint(97, 1); b += f_vint(98, 1); b += f_str(99, str(platform))
    b += f_str(100, str(platform)); b += f_str(102, "42531243535e0e0531")
    b += f_vint(104, 84750); b += f_vint(105, 1)
    b += f_str(106, cdn_blob); b += f_str(107, vercfg_sign); b += f_str(108, jwt)
    return b

def _decode_session_blob(field_63_hex):
    try:
        raw = bytes.fromhex(field_63_hex); sub = parse_proto(raw)
        b64 = first_value(sub, 10, "string")
        if not b64: return {}
        padded = b64 + "=" * (-len(b64) % 4)
        return json.loads(base64.b64decode(padded))
    except Exception: return {}

def get_login_data(tag, open_id, access_token, cfg, platform, jwt):
    plain = build_get_login_data(open_id, access_token, cfg, platform, jwt)
    login_url = cfg["client_url"].rstrip("/") + "/GetLoginData"
    headers = {
        "User-Agent": USER_AGENT_UNITY, "Accept": "*/*", "Accept-Encoding": "deflate, gzip",
        "Authorization": f"Bearer {jwt}", "X-GA": "v1 1",
        "X-GA-SV": str(int(time.time())),
        "ReleaseVersion": cfg["latest_release_version"],
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Unity-Version": "2018.4.12f1",
    }
    r = requests.post(login_url, data=enc_aes(plain), headers=headers, timeout=20)
    if r.status_code != 200: raise RuntimeError(f"GetLoginData HTTP {r.status_code}")
    fields = parse_proto(r.content)
    account_id  = first_value(fields, 1,  "varint")
    region      = first_value(fields, 3,  "string")
    nickname    = first_value(fields, 4,  "string")
    game_server = first_value(fields, 14, "string")
    event_url   = first_value(fields, 16, "string")
    chat_server = first_value(fields, 32, "string")
    session = {}
    nested_63 = first_value(fields, 63, "bytes")
    if nested_63: session = _decode_session_blob(nested_63)
    ok(tag, f"data     {D}game{R}={CY}{game_server}{R}  {D}chat{R}={CY}{chat_server}{R}")
    return {"account_id": account_id, "region": region, "nickname": nickname,
            "game_server": game_server, "chat_server": chat_server,
            "event_url": event_url, "session": session}

def load_accounts_file():
    if not os.path.exists(ACCOUNT_FILE): return []
    try:
        with open(ACCOUNT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception: return []

def save_accounts_file(accounts):
    with open(ACCOUNT_FILE, "w", encoding="utf-8") as f:
        json.dump(accounts, f, indent=2, ensure_ascii=False)

def append_account_file(account):
    with _file_lock:
        accounts = load_accounts_file()
        accounts.append(account)
        save_accounts_file(accounts)

def print_account_block(idx, total, account, elapsed):
    with _print_lock:
        print()
        print(f"  {GN}{B}┌─ ACCOUNT {idx}/{total} ─ CREATED ──────────────────────────────┐{R}")
        print(f"  {GN}│{R}  {D}uid        {R}  {WH}{account['uid']}{R}")
        print(f"  {GN}│{R}  {D}name       {R}  {MG}{account['name']}{R}")
        print(f"  {GN}│{R}  {D}ingame_id  {R}  {WH}{account['ingame_id']}{R}")
        print(f"  {GN}│{R}  {D}region     {R}  {CY}{account['region']}{R}")
        print(f"  {GN}│{R}  {D}open_id    {R}  {GR}{account['open_id']}{R}")
        print(f"  {GN}│{R}  {D}pass       {R}  {GR}{account['pass']}{R}")
        print(f"  {GN}│{R}  {D}time       {R}  {GR}{elapsed:.2f}s{R}")
        print(f"  {GN}{B}└──────────────────────────────────────────────────────────┘{R}")
        print()

def create_one_account(index, total, cfg, custom_name=None):
    tag = _tag(index, total); t0 = time.time()
    time.sleep(random.uniform(0.05, 0.5))
    try:
        device_id = "02-" + str(uuid.uuid4())
        uid = guest_register(tag, device_id)
        tokens = guest_token(tag, uid, device_id)
        open_id      = tokens["open_id"]
        access_token = tokens["access_token"]
        platform     = int(tokens.get("platform", tokens.get("main_active_platform", 4)) or 4)
        if custom_name:
            nickname = decorate_name(custom_name); ok(tag, f"name     {MG}{nickname}{R}")
        else:
            nickname = generate_nickname(tag, open_id, cfg)
        major_register(tag, open_id, access_token, nickname, cfg)
        login = major_login(tag, open_id, access_token, cfg, platform, region=REGION)
        payload  = decode_jwt_payload(login["jwt"]) if login.get("jwt") else {}
        lock_reg = (payload.get("lock_region") or "").upper()
        if lock_reg != REGION:
            info(tag, f"lock     {D}current{R}={YL}{lock_reg or '—'}{R} → requesting {MG}{REGION}{R}")
            confirmed = choose_region(tag, login["jwt"], cfg, REGION)
            cfg_r = {**cfg, "country_code": confirmed, "region": confirmed}
            login = major_login(tag, open_id, access_token, cfg_r, platform, region=confirmed)
            confirmed_region = confirmed
        else:
            confirmed_region = lock_reg; cfg_r = cfg
        ld = get_login_data(tag, open_id, access_token, cfg_r, platform, login["jwt"])
        account = {
            "uid": uid, "pass": PASSWORD, "name": nickname,
            "ingame_id": login.get("account_id"),
            "region": ld.get("region") or confirmed_region or REGION,
            "open_id": open_id, "access_token": access_token,
            "refresh_token": tokens.get("refresh_token"),
            "jwt": login.get("jwt"),
            "game_server": ld.get("game_server"),
            "chat_server": ld.get("chat_server"),
            "session_key":   (ld.get("session") or {}).get("key"),
            "session_nonce": (ld.get("session") or {}).get("nonce"),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        append_account_file(account)
        global _success_count
        with _count_lock:
            _success_count += 1; done = _success_count
        print_account_block(done, total, account, time.time() - t0)
        return account
    except Exception as e:
        global _failure_count
        with _count_lock:
            _failure_count += 1; done = _failure_count
        fail(tag, f"{RD}FAILED{R} ({done}/{total}) {D}{e}{R}")
        return None

# ═══════════════════════════════════════════════════════════════════════════
#   SECTION 8 — DEVICE GENERATOR
# ═══════════════════════════════════════════════════════════════════════════
_DEVICE_CACHE = {}
_DEVICE_BRANDS = [
    ("Samsung", ["SM-A125F", "SM-A225F", "SM-G998B", "SM-S911B", "SM-A546E", "SM-M156B", "SM-A256E"]),
    ("Xiaomi", ["2201122G", "2201123G", "22101316G", "23021RAAEG", "2312DRA50G"]),
    ("Poco", ["M2102J20SG", "2207117BPG", "23122PCD1G", "23049PCD8G", "2312DRAABC"]),
    ("Vivo", ["V2203", "V2311", "V2312", "V2324", "V2309"]),
    ("Realme", ["RMX3834", "RMX3741", "RMX3780", "RMX3630", "RMX3710"]),
    ("OnePlus", ["CPH2451", "CPH2581", "CPH2573", "CPH2569", "CPH2447"]),
    ("Oppo", ["CPH2477", "CPH2557", "CPH2527", "CPH2487", "CPH2609"]),
    ("Infinix", ["X6819", "X6837", "X6816", "X6850"]),
]
_DEVICE_GPUS = ["Adreno (TM) 660","Adreno (TM) 730","Adreno (TM) 740","Adreno (TM) 619",
                "Adreno (TM) 725","Adreno (TM) 710","Adreno (TM) 695","Adreno (TM) 610",
                "Mali-G68","Mali-G57","Mali-G76","Mali-G52","Mali-G610","Mali-G710"]
_DEVICE_OS = ["Android OS 12 / API-31","Android OS 13 / API-33","Android OS 14 / API-34"]

def _generate_new_device():
    brand, models = random.choice(_DEVICE_BRANDS)
    return {
        "unique_device_id": f"Google|{uuid.uuid4()}",
        "brand": brand, "model": random.choice(models),
        "gpu_renderer": random.choice(_DEVICE_GPUS),
        "system_software": random.choice(_DEVICE_OS),
        "screen_width": random.choice([1080, 1220, 1264]),
        "screen_height": random.choice([2340, 2400, 2412, 2712]),
        "screen_dpi": str(random.randint(380, 450)),
        "memory": random.choice([4096, 6144, 8192, 12288]),
        "processor_details": f"ARM64 FP ASIMD AES VMH | {random.randint(2200, 3400)} | {random.randint(8, 12)}",
        "client_ip": f"{random.randint(27, 205)}.{random.randint(10, 250)}.{random.randint(10, 250)}.{random.randint(10, 250)}",
    }

def get_device_for_account(account_id):
    global _DEVICE_CACHE
    k = str(account_id)
    if k not in _DEVICE_CACHE:
        print(f"[Device] Auto-generating device profile for UID: {k}")
        _DEVICE_CACHE[k] = _generate_new_device()
    return _DEVICE_CACHE[k]

# ═══════════════════════════════════════════════════════════════════════════
#   SECTION 9 — UDP / PROTOBUF HELPERS
# ═══════════════════════════════════════════════════════════════════════════
async def EnC_PacKeT(HeX, K, V):
    return AES.new(K, AES.MODE_CBC, V).encrypt(pad(bytes.fromhex(HeX), 16)).hex()

async def EnC_Vr(N):
    if N < 0: return b''
    H = []
    while True:
        b = N & 0x7F; N >>= 7
        if N: b |= 0x80
        H.append(b)
        if not N: break
    return bytes(H)

async def CrEaTe_VarianT(fn, value):
    fh = (fn << 3) | 0
    return await EnC_Vr(fh) + await EnC_Vr(value)

async def CrEaTe_LenGTh(fn, value):
    fh = (fn << 3) | 2
    ev = value.encode() if isinstance(value, str) else value
    return await EnC_Vr(fh) + await EnC_Vr(len(ev)) + ev

async def CrEaTe_ProTo(fields):
    packet = bytearray()
    for field, value in fields.items():
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    nested = await CrEaTe_ProTo(item)
                    packet.extend(await CrEaTe_LenGTh(field, nested))
                elif isinstance(item, int):
                    packet.extend(await CrEaTe_VarianT(field, item))
                elif isinstance(item, (str, bytes)):
                    packet.extend(await CrEaTe_LenGTh(field, item))
        elif isinstance(value, dict):
            nested_packet = await CrEaTe_ProTo(value)
            packet.extend(await CrEaTe_LenGTh(field, nested_packet))
        elif isinstance(value, int):
            packet.extend(await CrEaTe_VarianT(field, value))
        elif isinstance(value, (str, bytes)):
            packet.extend(await CrEaTe_LenGTh(field, value))
    return packet

async def DecodE_HeX(H):
    R = hex(H); F = str(R)[2:]
    return ("0" + F) if len(F) == 1 else F

async def Fix_PackEt(parsed_results):
    result_dict = {}
    for result in parsed_results:
        wt = result.wire_type
        if wt == "varint": value = result.data
        elif wt == "string": value = result.data
        elif wt == "bytes":
            v = result.data
            value = v.hex() if isinstance(v, (bytes, bytearray)) else v
        elif wt == "length_delimited":
            try: value = await Fix_PackEt(result.data.results)
            except Exception: value = str(result.data)
        else: value = result.data
        result_dict[str(result.field)] = value
    return result_dict

async def DeCode_PackEt(input_text):
    try: return await Fix_PackEt(Parser().parse(input_text))
    except Exception: return None

async def GeneRaTePk(Pk, N, K, V):
    PkEnc = await EnC_PacKeT(Pk, K, V)
    _ = await DecodE_HeX(int(len(PkEnc) // 2))
    if   len(_) == 2: HeadEr = N + "000000"
    elif len(_) == 3: HeadEr = N + "00000"
    elif len(_) == 4: HeadEr = N + "0000"
    elif len(_) == 5: HeadEr = N + "000"
    else: print('ErroR => GeneRatinG ThE PacKeT !! ')
    return bytes.fromhex(HeadEr + _ + PkEnc)

def _udp_log(line):
    if UDP_LOG_FILE is None: return
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    try:
        with open(UDP_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {line}\n")
    except Exception: pass

def udp_log_print(line):
    print(line); _udp_log(line)

def _auth_region_byte(region):
    reg = str(region or "BD").upper()
    if reg == "BD":  return 0x19
    if reg == "IND": return 0x14
    return 0x15

def build_auth_datagram(token, account_id):
    payload = token.encode("utf-8") if isinstance(token, str) else token
    p = 16 - (len(payload) % 16)
    data = AES.new(AUTH_AES_KEY, AES.MODE_CBC, AUTH_AES_IV).encrypt(payload + bytes([p]) * p)
    out = bytearray()
    out.append(AUTH_CMD & 0xFF); out.append(_auth_region_byte(REGION) & 0xFF)
    out += struct.pack(">Q", int(account_id) & 0xFFFFFFFFFFFFFFFF)
    out += struct.pack(">I", int(time.time()) & 0xFFFFFFFF)
    out += struct.pack(">i", len(data)); out += data
    return bytes(out)

def _extract_leave_info(decoded):
    if not isinstance(decoded, dict): return None, "UNKNOWN"
    data = decoded.get("5", {})
    if not isinstance(data, dict): return None, "UNKNOWN"
    lid = data.get("1")
    if isinstance(lid, dict): lid = lid.get("data")
    reason = data.get("2")
    if isinstance(reason, dict): reason = reason.get("data")
    rname = LEAVE_REASONS.get(reason, f"UNKNOWN_{reason}") if isinstance(reason, int) else \
            (f"UNKNOWN_{reason}" if reason is not None else "UNKNOWN")
    return lid, rname

def describe(ptype, cmd):
    p = PROTOCOL.get(ptype, f"UNKNOWN_{ptype}")
    if isinstance(cmd, int):
        return f"{p}/{CMD_TABLES.get(ptype, {}).get(cmd, f'CMD_{cmd}')}"
    return p

def udp_cmd_name(cmd): return UDP_CMD.get(cmd, f"CMD_{cmd}")

def _idc_entries():
    reg = REGION.upper()
    return [{1:"IDC1",2:75,3:reg},{1:"IDC2",2:123,3:reg}]

def _vi(n):
    out = bytearray()
    while True:
        b = n & 0x7F; n >>= 7
        if n: out.append(b | 0x80)
        else: out.append(b); break
    return bytes(out)

def _one(field, v):
    if isinstance(v, dict):
        body = _pb(v); return _vi((field << 3) | 2) + _vi(len(body)) + body
    if isinstance(v, int): return _vi(field << 3) + _vi(v)
    if isinstance(v, (str, bytes)):
        b = v.encode() if isinstance(v, str) else v
        return _vi((field << 3) | 2) + _vi(len(b)) + b
    raise TypeError(type(v))

def _pb(fields):
    out = bytearray()
    for f, v in fields.items():
        if isinstance(v, list):
            for it in v: out += _one(f, it)
        else: out += _one(f, v)
    return bytes(out)

def _br_frame(ptype, region, proto, key, iv):
    enc = AES.new(key, AES.MODE_CBC, iv).encrypt(pad(proto, 16))
    return bytes([ptype, _rbyte(region)]) + len(enc).to_bytes(4, "big") + enc

def _br_idc(reg, pings=(75, 123)):
    return [{1:"IDC1",2:pings[0],3:reg},{1:"IDC2",2:pings[1],3:reg}]

_C_S1 = "0200044B122D3B02010000000000000000000000000000E3172CED00"
_C_14_1 = b"\x32" + bytes([len(_C_S1)]) + _C_S1.encode() + b"\x30\x30" * 3
_C_14_3 = bytes.fromhex(
    "7e585c521207074f5d030c5c545104570455070f0a555a085201095701025b560601545606010f07100802487d5c4043481e07"
    "1f081a1709034c0757787500566b45627e7a6548407565577a700e7708627a047e7e041005447b5d655070547e437c607f7656"
    "5675704e5877525b5a5b515662410a105f5c5a4c1e637f1c7147430b4f6c557778605b67416b50635850500056575e005a7606"
    "057005067e0c15060045455e56447a665a6672694b5046524b057b79427c715560577b575f0a120e4b470e631b536262186b0f"
    "73406359475343795c481d7918564b47790c13054d1d714b5d75451740515f7e586d414e40595a03000e654e0741507a091b08"
    "4c6668777b1c4c676517505d6e7a4c4e7d7c791f5269057f42440207041005004d7e5c5977037d4a631f560255026b7a647e6b"
    "0007015503746353500e1a0048701a0153626506774f18065e0558610457421856007313771b60010b140745554d7f50477d68"
    "770662600646696876026242541c4a49037f74750a1204074f487402135059457f517b415266604a434506064e79004c5a7b4f"
    "700d14044a58454a5a7c5e5f5b764354425e1267735041537d6041180a6d694305")
_C_14_7 = bytes.fromhex("1d02474b420204030506171d677c716374687d5f557051565753")
_C_14_11 = b"\x03" + (
    "bbSQ69i8H3F5AdV2KyoVlWj2cgPtsEL3Pi8QcWkc/NJiGxtxXsmeZDDwFPKPbvd56sULGeaD3qha9S6hKIkIb3oXVAAFErlI76uU2p2AqNdJyaucxz1ba5ecHPCBohQR6E5Y1UzpsgpxutURpI8pbqY0tCpeL1bOT+F5UaysgFmTeoIalHxxEYPQx7OVJHElCV5el0vpIs98JSA3nB8FWin6ckz5Fd0sG4n2g0B7OUOvcreqilCT737xI24wPxLdidSr1AJ2MK0/m3ugV1iqzPXhttKyvfmMNVY8DoXBBUcYt3vpK7mgbnietrOqJIbJC3O4ygX6IWl/hkp+ngsjfeOZSornpzFnxM/kkqZgZjVOweXe61FRU6JsGSeTeY63kqA/mbCPfdwodSYJE2hXfVJofxRG1644gFPYRkCPUjJazd2l9WAh9kd86kYbjphbxwz55ciWvZ3sDJR11W96ezyxJPhJPD8FQoQVmno6BP4e7QI1xe+h35bkS1epZq6K6xUP5YtHFvqbhARMNQKUYYzXQWRFMNL1JgAeMJNO0+eCPL57+RXzRKtlgM/rVsIWhNw8Oo9SdP+7wsGrMK+HIOJaF1apAXNRQ9mCqxI="
).encode()

# ═══════════════════════════════════════════════════════════════════════════
#   SECTION 10 — SQUAD PACKETS
# ═══════════════════════════════════════════════════════════════════════════
def br_create_squad_pkt(region, client_version, key, iv):
    reg = str(region or "BD").upper()
    f = {1: 1, 2: {
        2: b"\x01", 3: 1, 4: SQUAD_PLAYERS - 1, 5: "en",
        8: _br_idc(reg), 9: 2,
        10: bytes.fromhex("01090a0b12191a202729"), 11: 1, 13: 1,
        14: {1: _C_14_1, 2: 40, 3: _C_14_3, 4: "w\\Z]", 6: 12, 7: _C_14_7,
             8: client_version or "1.132.9", 9: 6, 10: 2, 11: _C_14_11},
        19: 329, 21: bytes.fromhex("374f521955"),
        24: [{1: 3, 2: 360},{1: 4, 2: 391},{1: 5, 2: 156},
             {1: 29, 2: 204},{1: 22, 2: 118},{1: 14, 2: 139},{1: 21}],
        30: ("https://dl-bd-production.freefiremobile.com/"
             "2832022628717E276054_7104117490_107_1767713981_0"),
    }}
    return _br_frame(0x05, reg, _pb(f), key, iv)

def br_join_team_pkt(code, region, client_version, key, iv):
    reg = str(region or "BD").upper()
    field9 = {1: _C_14_1, 2: 40, 3: _C_14_3, 4: "w\\Z]", 6: 12, 7: _C_14_7,
              8: client_version or "1.132.9", 9: 6, 10: 2, 11: _C_14_11}
    f = {1: 4, 2: {
        4: bytes.fromhex("01090a0b121619201d2729"),
        5: str(code), 6: 6, 8: 1, 9: field9,
        11: _br_idc(reg, (99, 136)), 13: "en",
        16: bytes.fromhex("374f521955"),
        20: [{1: 3, 2: 360},{1: 4, 2: 391},{1: 5, 2: 156},
             {1: 29, 2: 204},{1: 22, 2: 118},{1: 14, 2: 139},{1: 21}],
        27: {1: 2, 2: 4}}}
    return _br_frame(0x05, reg, _pb(f), key, iv)

def br_start_squad_pkt(uid, region, key, iv):
    reg = str(region or "BD").upper()
    return _br_frame(0x05, reg, _pb({1: 9, 2: {1: int(uid), 7: _br_idc(reg)}}), key, iv)

async def send_op31(group_id, region, key, iv):
    fields = {1: 31, 2: {1: int(group_id)}}
    pkt = f"05{_rbyte(region):02x}"
    return await GeneRaTePk((await CrEaTe_ProTo(fields)).hex(), pkt, key, iv)

async def build_auth_packet(account_id, token, server_time, key, iv, region=REGION, typ="OnLine"):
    uid_hex = f"{int(account_id):016x}"; ts_hex = f"{int(server_time):08x}"
    enc = AES.new(key, AES.MODE_CBC, iv).encrypt(pad(token.encode(), 16)).hex()
    enc_len = f"{len(enc) // 2:08x}"
    reg = str(region).upper()
    if reg == "BD":     pre_on, pre_chat = "7119", "9219"
    elif reg == "IND":  pre_on, pre_chat = "7114", "9214"
    else:               pre_on, pre_chat = "7115", "9215"
    if typ == "OnLine":
        return bytes.fromhex(pre_on + uid_hex + ts_hex + "00000000" + enc_len + enc)
    return bytes.fromhex(pre_chat + uid_hex + ts_hex + enc_len + enc)

async def send_keep_alive(region=REGION):
    reg = str(region).upper()
    return bytes.fromhex("0219" if reg == "BD" else ("0214" if reg == "IND" else "0215"))

# ═══════════════════════════════════════════════════════════════════════════
#   SECTION 11 — UDP CRYPTO (TEA + CRC7)
# ═══════════════════════════════════════════════════════════════════════════
CRC7_TABLE = bytes([
    0,9,18,27,36,45,54,63,72,65,90,83,108,101,126,119,25,16,11,2,61,52,47,38,
    81,88,67,74,117,124,103,110,50,59,32,41,22,31,4,13,122,115,104,97,94,87,
    76,69,43,34,57,48,15,6,29,20,99,106,113,120,71,78,85,92,100,109,118,127,
    64,73,82,91,44,37,62,55,8,1,26,19,125,116,111,102,89,80,75,66,53,60,39,
    46,17,24,3,10,86,95,68,77,114,123,96,105,30,23,12,5,58,51,40,33,79,70,
    93,84,107,98,121,112,7,14,21,28,35,42,49,56,65,72,83,90,101,108,119,126,
    9,0,27,18,45,36,63,54,88,81,74,67,124,117,110,103,16,25,2,11,52,61,38,
    47,115,122,97,104,87,94,69,76,59,50,41,32,31,22,13,4,106,99,120,113,78,
    71,92,85,34,43,48,57,6,15,20,29,37,44,55,62,1,8,19,26,109,100,127,118,73,
    64,91,82,60,53,46,39,24,17,10,3,116,125,102,111,80,89,66,75,23,30,5,12,
    51,58,33,40,95,86,77,68,123,114,105,96,14,7,28,21,42,35,56,49,70,79,84,
    93,98,107,112,121,
])
_DELTA = 0x9E3779B9; _ROUNDS = 16
_FIELD_SIZES = {0:1, 1:2, 2:2, 3:1, 4:2}
_FIELD_NAMES = {0:"sendOption", 1:"cmd", 2:"orderId", 3:"flags", 4:"length"}

def optimize_udp_socket(sock):
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 262144)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 262144)
    except Exception: pass

async def crc7_buff(crc, buf):
    c = crc & 0x7F
    for b in buf: c = CRC7_TABLE[((2 * (c & 0xFF)) ^ (b & 0xFF)) & 0xFF] & 0x7F
    return c & 0x7F

async def tea_enc(v0, v1, k0, k1, k2, k3):
    s = 0
    for _ in range(_ROUNDS):
        s = (s + _DELTA) & 0xFFFFFFFF
        v0 = (v0 + (((((v1 << 4) & 0xFFFFFFFF) + k0) & 0xFFFFFFFF ^ ((v1 + s) & 0xFFFFFFFF) ^ (((v1 >> 5) + k1) & 0xFFFFFFFF)))) & 0xFFFFFFFF
        v1 = (v1 + (((((v0 << 4) & 0xFFFFFFFF) + k2) & 0xFFFFFFFF ^ ((v0 + s) & 0xFFFFFFFF) ^ (((v0 >> 5) + k3) & 0xFFFFFFFF)))) & 0xFFFFFFFF
    return v0, v1

async def tea_dec(v0, v1, k0, k1, k2, k3):
    s = (_DELTA * _ROUNDS) & 0xFFFFFFFF
    for _ in range(_ROUNDS):
        v1 = (v1 - (((((v0 << 4) & 0xFFFFFFFF) + k2) & 0xFFFFFFFF ^ ((v0 + s) & 0xFFFFFFFF) ^ (((v0 >> 5) + k3) & 0xFFFFFFFF)))) & 0xFFFFFFFF
        v0 = (v0 - (((((v1 << 4) & 0xFFFFFFFF) + k0) & 0xFFFFFFFF ^ ((v1 + s) & 0xFFFFFFFF) ^ (((v1 >> 5) + k1) & 0xFFFFFFFF)))) & 0xFFFFFFFF
        s = (s - _DELTA) & 0xFFFFFFFF
    return v0, v1

async def tea_cbc_encrypt(padded, key_bytes):
    k0,k1,k2,k3 = (struct.unpack_from("<I", key_bytes, o)[0] for o in (0,4,8,12))
    out = bytearray(len(padded))
    prev_cipher = bytearray(8); prev_intermediate = bytearray(8)
    for i in range(0, len(padded), 8):
        xored = bytearray(8)
        for j in range(8): xored[j] = padded[i+j] ^ prev_cipher[j]
        e0, e1 = await tea_enc(struct.unpack_from("<I", xored, 0)[0],
                               struct.unpack_from("<I", xored, 4)[0], k0,k1,k2,k3)
        enc = bytearray(8)
        struct.pack_into("<I", enc, 0, e0); struct.pack_into("<I", enc, 4, e1)
        for j in range(8): out[i+j] = enc[j] ^ prev_intermediate[j]
        prev_cipher[:] = out[i:i+8]; prev_intermediate[:] = xored
        if i % 64 == 0: await asyncio.sleep(0)
    return bytes(out)

async def tea_cbc_decrypt(body, key_bytes):
    k0,k1,k2,k3 = (struct.unpack_from("<I", key_bytes, o)[0] for o in (0,4,8,12))
    out = bytearray(len(body))
    prev_intermediate = bytearray(8); prev_cipher = bytearray(8)
    xored = bytearray(8); dec = bytearray(8)
    for i in range(0, len(body), 8):
        for j in range(8): xored[j] = body[i+j] ^ prev_intermediate[j]
        d0, d1 = await tea_dec(struct.unpack_from("<I", xored, 0)[0],
                               struct.unpack_from("<I", xored, 4)[0], k0,k1,k2,k3)
        struct.pack_into("<I", dec, 0, d0); struct.pack_into("<I", dec, 4, d1)
        for j in range(8): out[i+j] = dec[j] ^ prev_cipher[j]
        prev_cipher[:] = body[i:i+8]; prev_intermediate[:] = dec
        if i % 64 == 0: await asyncio.sleep(0)
    return bytes(out)

async def build_padded(content):
    pad_len = (8 - (len(content) + 10) % 8) % 8
    return bytes([pad_len, 0, 0]) + b"\x00" * pad_len + content + b"\x00" * 7

async def oicq_unpad(padded):
    if not padded or len(padded) < 8: return None
    if not all(padded[-1-i] == 0 for i in range(7)): return None
    pad_len = padded[0] & 0x07
    s = 3 + pad_len; e = len(padded) - 7
    return padded[s:e] if s < e else b""

async def encode_header(layout, so, cmd, oid, flags, length, k, v80):
    out = bytearray()
    for code in layout:
        value = {0:so,1:cmd,2:oid,3:flags,4:length}[code]
        if _FIELD_SIZES[code] == 1: out.append((value & 0xFF) ^ k)
        else:
            v = ((value & 0xFFFF) ^ v80) & 0xFFFF
            out.append(v & 0xFF); out.append((v >> 8) & 0xFF)
    return bytes(out)

async def layouts_from_mask(mask):
    s = str(mask).strip()
    try: ru = [int(c) for c in s]
    except ValueError: ru = [0, 1, 2, 3, 4]
    if sorted(ru) != [0, 1, 2, 3, 4]: ru = [0, 1, 2, 3, 4]
    return ru, [c for c in ru if c != 2]

async def build_packet(msg_key, layout, so, cmd, oid, flags, content, key, encrypted=True):
    k = key[0]; v80 = ((k << 8) | k) & 0xFFFF
    body = await tea_cbc_encrypt(await build_padded(content), key) if encrypted else content
    hdr = bytearray([msg_key, 0])
    for code in layout:
        value = {0:so,1:cmd,2:oid,3:flags,4:len(body)}[code]
        if _FIELD_SIZES[code] == 1: hdr.append((value & 0xFF) ^ k)
        else:
            v = ((value & 0xFFFF) ^ v80) & 0xFFFF
            hdr.append(v & 0xFF); hdr.append((v >> 8) & 0xFF)
    packet = bytearray(hdr + body)
    packet[1] = await crc7_buff(0, bytes(packet[2:])) & 0x7F
    return bytes(packet)

async def build_hello_packet(text, key, layout):
    data = text.encode("utf-8")[:25]
    content = len(data).to_bytes(4, "little") + data + b"\x00" * 9
    k = key[0]; v80 = ((k << 8) | k) & 0xFFFF
    layout = [int(c) for c in str(layout).strip()]
    enc_body = await tea_cbc_encrypt(await build_padded(content), key)
    header_bytes = await encode_header(layout, 1, 1, 0, 1, len(enc_body), k, v80)
    packet = bytearray([0x63, 0x00]) + header_bytes + enc_body
    packet[1] = await crc7_buff(0, bytes(packet[2:])) & 0x7F
    return bytes(packet).hex()

def _put_varint(out, v):
    v = int(v)
    while v >= 0x80:
        out.append((v & 0x7F) | 0x80); v >>= 7
    out.append(v & 0x7F)

def _put_zigvarint(out, v):
    z = (int(v) << 1) ^ (int(v) >> 63)
    _put_varint(out, z & 0xFFFFFFFFFFFFFFFF)

def _put_float_bits(out, f):
    bits = struct.unpack("<I", struct.pack("<f", float(f)))[0]
    _put_varint(out, bits)

def _put_string(out, s):
    raw = s.encode("utf-8") if isinstance(s, str) else s
    _put_zigvarint(out, len(raw)); out += raw

def _rd_varint(b, p):
    v = i = 0
    while True:
        c = b[p + i]
        v |= (c & 0x7F) << (7 * i); i += 1
        if not c & 0x80: return v, p + i

def _zag(v): return (v >> 1) ^ -(v & 1)

# ═══════════════════════════════════════════════════════════════════════════
#   SECTION 12 — JOIN / MATCH STARTUP
# ═══════════════════════════════════════════════════════════════════════════
HDR_RELIABLE = 10; UDP_HEAD_AND_ENCRY_SIZE = 40; MTU_LIMIT = 1300
_SALT_LEN, _ZERO_LEN = 2, 7

def _tea_encrypt_len(n):
    t = 1 + _SALT_LEN + n + _ZERO_LEN; r = t % 8
    return t + (8 - r if r else 0)

def _dg_size(token_len, reliable=True):
    zv = bytearray(); _put_zigvarint(zv, token_len)
    body = len(zv) + token_len
    return (HDR_RELIABLE if reliable else 8) + _tea_encrypt_len(body)

def split_token_bytes(token_bytes):
    n = len(token_bytes); raw = int(n * 0.85); p1 = raw - (raw % 40)
    while UDP_HEAD_AND_ENCRY_SIZE + _dg_size(p1) > MTU_LIMIT and p1 > 40:
        p1 -= 40
    return token_bytes[:p1], token_bytes[p1:]

def build_join_info_head(account_id, game_mode=15, match_mode=1, map_id=1,
                         country="BD", client_version="1.132.9",
                         client_version_code="2019121229",
                         client_url=("csoversea.stronghold.freefiremobile.com;"
                                     "0.0.0.0;34.126.76.45;34.87.177.14;"
                                     "34.87.170.230;35.185.183.57"),
                         room_id=0, match_id=0,
                         drift_bottle_owner_id=0, drift_bottle_owner_name="",
                         enable_antihack_tick=1, friend_count=0,
                         client_ip="", client_fingerprint="",
                         session_tag=0, is_emulator=1):
    room = int(match_id or room_id)
    b = bytearray()
    _put_varint(b, int(account_id)); _put_varint(b, room)
    b.append(1); b.append(int(game_mode) & 0xFF)
    _put_varint(b, room); b.append(int(map_id) & 0xFF)
    b.append(0); _put_varint(b, 0); _put_varint(b, 0); b.append(0)
    b.append(int(is_emulator) & 0xFF)
    b.append(0); b.append(1); b.append(2); b.append(3)
    b.append(int(enable_antihack_tick) & 0xFF); b.append(1)
    _put_string(b, country); _put_varint(b, 0)
    b.append(1); b.append(2); b.append(0); b.append(1); b.append(0); b.append(0); b.append(4)
    _put_string(b, client_version); _put_string(b, client_version_code)
    _put_string(b, client_url)
    b.append(0); b.append(0); _put_varint(b, int(friend_count)); b.append(0)
    _put_varint(b, int(drift_bottle_owner_id)); _put_string(b, drift_bottle_owner_name or "")
    b.append(1); _put_string(b, ""); _put_string(b, "")
    b.append(0); _put_varint(b, 0); _put_varint(b, 0)
    b.append(0); b.append(0); b.append(0); _put_varint(b, 0); _put_string(b, "")
    _put_varint(b, 0); b.append(0); b.append(1); b.append(0); b.append(0)
    _put_varint(b, 0); _put_varint(b, 0); b.append(0); b.append(1)
    _put_string(b, ""); _put_varint(b, 0)
    b.append(0); b.append(0); b.append(0)
    b.append(int(match_mode) & 0xFF); b.append(0)
    _put_varint(b, int(session_tag)); b.append(2); b.append(0)
    _put_string(b, client_ip or ""); _put_string(b, client_fingerprint or "")
    return bytes(b)

def build_join_post_body(account_id, token_part2, **kw):
    body = bytearray(); body += build_join_info_head(account_id, **kw)
    _put_string(body, token_part2); return bytes(body)

async def build_join_match_startup(join_token, udp_key, match_code, account_id, block_val,
                                   server_ip="", region="BD",
                                   client_version="1.132.9",
                                   client_version_code="2019121229",
                                   access_token="", match_id=0, country="BD",
                                   map_id=1, game_mode=15, match_mode=1):
    join_token = join_token.strip()
    udp_key_b  = bytes.fromhex(udp_key)
    match_code = [int(c) for c in str(match_code).strip()]
    enc_token  = join_token.encode("utf-8") if isinstance(join_token, str) else join_token
    part1, part2 = split_token_bytes(enc_token)
    prepare_body = bytearray(); _put_string(prepare_body, part1)
    prepare_pkt  = (await build_packet(0x5E, match_code, 2, 447, 0, 1,
                                       bytes(prepare_body), udp_key_b)).hex()
    post_body = build_join_post_body(
        account_id, part2, game_mode=game_mode, match_mode=match_mode, map_id=map_id,
        country=country, client_version=client_version,
        client_version_code=client_version_code,
        match_id=int(match_id or block_val),
        client_ip=server_ip.split(":")[0] if server_ip else "")
    post_pkt = await build_packet(0x5A, match_code, 2, 448, 1, 1, post_body, udp_key_b)
    return [prepare_pkt], post_pkt.hex()

async def decode_packet(packet, key, mask=None):
    import itertools
    data = bytes(packet) if isinstance(packet, bytes) else bytes.fromhex(packet)
    if len(data) < 8: return None
    k = key[0]; v80 = ((k << 8) | k) & 0xFFFF
    crc_ok = (data[1] & 0x7F) == await crc7_buff(0, data[2:])
    if mask:
        ru, nr = await layouts_from_mask(mask)
        layouts = [("RUDP", ru), ("nonRUDP", nr)]
    else:
        layouts = [("RUDP", list(p)) for p in itertools.permutations([0,1,2,3,4])]
        layouts += [("nonRUDP", list(p)) for p in itertools.permutations([0,1,3,4])]
    cands = []
    for kind, layout in layouts:
        off = 2; f = {}; ok_ = True
        for code in layout:
            size = _FIELD_SIZES[code]
            if off + size > len(data): ok_ = False; break
            f[_FIELD_NAMES[code]] = (data[off] ^ k) if size == 1 else \
                ((data[off] | (data[off+1] << 8)) ^ v80) & 0xFFFF
            off += size
        if not ok_: continue
        if f["flags"] > 7 or f["sendOption"] > 7: continue
        if f["length"] != len(data) - off: continue
        body = data[off:off+f["length"]]; content = None
        if f["flags"] & 1:
            if len(body) < 8 or len(body) % 8 != 0: continue
            content = await oicq_unpad(await tea_cbc_decrypt(body, key))
            if content is None: continue
        else: content = body
        score = (1 if crc_ok else 0) + (1 if content is not None else 0)
        cands.append({"kind":kind,"layout":layout,"headerLen":off,"msgKey":data[0],
                      "cmd":f["cmd"],"flags":f["flags"],"sendOrder":f["sendOption"],
                      "orderId":f.get("orderId"),"length":f["length"],
                      "content":content,"crcOk":crc_ok,"score":score})
    if not cands: return None
    cands.sort(key=lambda c: c["score"], reverse=True)
    return cands[0]

# ═══════════════════════════════════════════════════════════════════════════
#   SECTION 13 — MOVEMENT & STATE
# ═══════════════════════════════════════════════════════════════════════════
SEND_HZ           = 20.0
MOVE_INTERVAL     = 2.0 / SEND_HZ
WALK_SPEED        = 5150.0
STEP_PER_TICK     = WALK_SPEED / SEND_HZ
ZONE_RADIUS_SCALE = 1000.0

CMD_PLAYER_JOIN   = 101
CMD_MATCH_END     = 103
CMD_DEAD          = 107
CMD_SAFE_ZONE     = 117
CMD_SERVER_TIME   = 2000
CMD_MY_STATE      = 2001
CMD_OTHER_STATES  = 2012
CMD_QUICK_CHAT    = 551
CMD_GRI_SYNC      = 1901

PHASE_PREPARE = 1; PHASE_FIGHT = 3
POSE_STANDING = 0; POSE_DASHING = 2

def build_player_state_upload(player_id, pos, rot, tdir, vel, aim_float,
                              server_time, physx_state=0, physx_pose=0,
                              platform=0, low_grav=0, ping=0,
                              jump=0, slide=0, custom=0,
                              crouch=0, vehicle=0, fast_run=0,
                              emote=0, shoot=0):
    o = bytearray(); _put_varint(o, int(player_id))
    _put_zigvarint(o, pos[0]); _put_zigvarint(o, pos[1]); _put_zigvarint(o, pos[2])
    _put_zigvarint(o, rot[0]); _put_zigvarint(o, rot[1]); _put_zigvarint(o, rot[2])
    _put_zigvarint(o, tdir[0]); _put_zigvarint(o, tdir[1])
    _put_zigvarint(o, vel[0]); _put_zigvarint(o, vel[1]); _put_zigvarint(o, vel[2])
    o.append(physx_state & 0xFF); o.append(physx_pose & 0xFF)
    _put_float_bits(o, aim_float[0]); _put_float_bits(o, aim_float[1]); _put_float_bits(o, aim_float[2])
    _put_varint(o, platform); o.append(1 if low_grav else 0)
    _put_varint(o, ping); o.append(jump & 0xFF); _put_varint(o, slide)
    custom_packed = ((int(crouch)&0x01) | ((int(vehicle)&0x01)<<1) |
                     ((int(fast_run)&0x01)<<2) | ((int(emote)&0x0F)<<3) |
                     ((int(shoot)&0x01)<<7)) & 0xFF
    o.append(custom_packed)
    _put_varint(o, server_time & 0xFFFFFFFF)
    return bytes(o)

def parse_player_join(body):
    if body is None or len(body) < 4: return None
    try:
        p = 0
        user_id, p = _rd_varint(body, p)
        _samo,    p = _rd_varint(body, p)
        player_id, p = _rd_varint(body, p)
        raw_len,  p = _rd_varint(body, p)
        n = _zag(raw_len); name = body[p:p + n].decode("utf-8", "replace")
    except (IndexError, ValueError): return None
    return user_id, player_id, name

def decode_my_state(body):
    if body is None or len(body) < 6: return None
    try:
        p = 0
        _mt, p = _rd_varint(body, p); _cnt, p = _rd_varint(body, p); p += 1
        x, p = _rd_varint(body, p); y, p = _rd_varint(body, p); z, p = _rd_varint(body, p)
    except (IndexError, ValueError): return None
    return (_zag(x), _zag(y), _zag(z))

def decode_server_time(body):
    if not body: return None
    try:
        tick, p = _rd_varint(body, 0)
        phase = body[p] if p < len(body) else 0
    except (IndexError, ValueError): return None
    return tick, phase

def parse_gri_block(body):
    if body is None or len(body) < 2: return {}
    try: block_len = struct.unpack_from("<H", body, 0)[0]
    except struct.error: return {}
    p = 2; end = min(2 + block_len, len(body)); fields = {}
    while p < end:
        fid = body[p]; p += 1
        if p >= end: break
        try: v, p = _rd_varint(body, p)
        except (IndexError, ValueError): break
        fields[fid] = v
    return fields

def get_match_phase(body):
    fields = parse_gri_block(body)
    if 3 not in fields: return None
    value = fields[3]
    if value < 0x10000: return None
    return (value >> 16) & 0xFFFF, fields.get(2), 0, 0

class MovementState:
    def __init__(self, account_id):
        self.account_id = int(account_id)
        self.my_id = None; self.my_short = None
        self.my_pos = None; self.server_pos = None
        self.phase = None
        self.server_tick = None; self.tick_local = None
        self.tick_rate = 30.0; self.alive = True
        self.joined_at = None; self.blocked = 0; self.yaw = 0.0
    def set_identity(self, full_id):
        self.my_id = int(full_id); self.my_short = self.my_id & 0xFF
        if self.joined_at is None: self.joined_at = time.time()
    def seed_my_pos(self, pos):
        self.server_pos = pos
        if self.my_pos is None: self.my_pos = pos
        else:
            dx = pos[0] - self.my_pos[0]; dz = pos[2] - self.my_pos[2]
            if math.sqrt(dx*dx + dz*dz) > 2000.0: self.my_pos = pos
            else: self.my_pos = (self.my_pos[0], pos[1], self.my_pos[2])
    def sync_clock(self, tick, now):
        if self.server_tick is not None and self.tick_local is not None:
            dt = now - self.tick_local; dtick = tick - self.server_tick
            if dt > 0.5 and 0 < dtick < 10000:
                self.tick_rate = self.tick_rate * 0.7 + (dtick / dt) * 0.3
        self.server_tick = tick; self.tick_local = now
    def server_time(self, now):
        if self.server_tick is None:
            if self.joined_at is None: return 0
            return int((now - self.joined_at) * 1000.0) & 0xFFFFFFFF
        elapsed = now - self.tick_local
        ticks = self.server_tick + elapsed * self.tick_rate
        return int(ticks * 1000.0 / self.tick_rate) & 0xFFFFFFFF

# --- Manual Control Integration ---
def read_control():
    try:
        p = Path(CONTROL_FILE)
        if p.exists():
            return json.loads(p.read_text())
    except Exception: pass
    return None

class MovementPlanner:
    def __init__(self, step=STEP_PER_TICK):
        self.step = float(step)
        self._last_yaw = random.uniform(0, 360)
        self._action_timer = 0
        self._skill1 = 0
        self._skill_cooldown = 5.0
    def next_yaw(self): return self._last_yaw
    def plan(self, st, now):
        if st.my_pos is None or st.my_id is None: return None
        my = st.my_pos; new_y = int(my[1])
        
        ctrl = read_control()
        if ctrl:
            action = ctrl.get("action", "auto")
            if action == "stop":
                return (int(my[0]), new_y, int(my[2])), 0, False
            elif action == "move":
                yaw = ctrl.get("yaw", 0)
                rad = math.radians(yaw); dx = math.sin(rad); dz = math.cos(rad)
                self._last_yaw = yaw
                return (int(my[0] + dx*self.step), new_y, int(my[2] + dz*self.step)), self.step, True

        self._skill_cooldown -= MOVE_INTERVAL
        if self._skill_cooldown <= 0:
            self._skill1 = 1; self._skill_cooldown = random.uniform(4.0, 8.0)
        else: self._skill1 = 0
        self._action_timer -= MOVE_INTERVAL
        if self._action_timer <= 0:
            self._last_yaw = random.uniform(0, 360)
            self._action_timer = random.uniform(2.0, 4.0)
        rad = math.radians(self._last_yaw); dx = math.sin(rad); dz = math.cos(rad)
        return (int(my[0] + dx*self.step), new_y, int(my[2] + dz*self.step)), self.step, True

def _build_position_body(player_id, old_pos, new_pos, aim_yaw, server_time, moving, planner=None):
    dx = new_pos[0] - old_pos[0]; dz = new_pos[2] - old_pos[2]
    dist = math.sqrt(dx*dx + dz*dz)
    if dist >= 1: ux, uz = dx/dist, dz/dist
    else: ux = math.sin(math.radians(aim_yaw)); uz = math.cos(math.radians(aim_yaw))
    vel = (int(ux * 515), 0, int(uz * 515))
    rot = (int(ux * 100), 0, int(uz * 100))
    tdir = (int(ux * 100), int(uz * 100))
    aim = (ux, 0.0, uz)
    pose = 2 if moving else 0
    shoot = 1 if (planner and getattr(planner, "_skill1", 0)) else 0
    return build_player_state_upload(
        player_id, new_pos, rot, tdir, vel, aim, server_time,
        physx_state=0, physx_pose=pose, ping=90,
        jump=0, slide=0, custom=0, crouch=0, vehicle=0, fast_run=0, shoot=shoot)

def dispatch_incoming(cmd, body, st, tag, verbose=False):
    if body is None: return
    if cmd == CMD_PLAYER_JOIN:
        info_p = parse_player_join(body)
        if info_p is None: return
        uid, full_id, name = info_p
        if uid == st.account_id: st.set_identity(full_id)
    elif cmd == CMD_MY_STATE:
        pos = decode_my_state(body)
        if pos is not None: st.seed_my_pos(pos)
    elif cmd == CMD_SERVER_TIME:
        parsed = decode_server_time(body)
        if parsed is not None: st.sync_clock(parsed[0], time.time())
    elif cmd == CMD_GRI_SYNC:
        parsed = get_match_phase(body)
        if parsed is not None: st.phase = parsed[0]
    elif cmd == CMD_DEAD:
        try: pid, _ = _rd_varint(body, 0)
        except (IndexError, ValueError): return
        if st.my_id is not None and pid == st.my_id: st.alive = False

async def movement_loop(sock, remote_addr, udp_key_b, match_code, state, stop_event, tag):
    planner = MovementPlanner()
    nr = (await layouts_from_mask(match_code))[1]
    loop = asyncio.get_event_loop(); next_tick = time.time()
    while not stop_event.is_set():
        now = time.time()
        if now < next_tick:
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=next_tick - now); break
            except asyncio.TimeoutError: pass
            continue
        next_tick += MOVE_INTERVAL
        if next_tick < now: next_tick = now + MOVE_INTERVAL
        if not state.alive or state.my_id is None: continue
        planned = planner.plan(state, now)
        if planned is None: continue
        new_pos, dist, moving = planned
        old_pos = state.my_pos; state.my_pos = new_pos
        body = _build_position_body(state.my_id, old_pos, new_pos, planner.next_yaw(),
                                    state.server_time(now), moving, planner=planner)
        pkt = await build_packet(random.randint(0x60, 0x7F), nr, 0, CMD_MY_STATE, None, 1,
                                 body, udp_key_b, encrypted=True)
        try: await loop.sock_sendto(sock, pkt, remote_addr)
        except Exception: pass

# ═══════════════════════════════════════════════════════════════════════════
#   SECTION 14 — PLAY_GAME (UDP session)
# ═══════════════════════════════════════════════════════════════════════════
async def play_game(server_ip_port, prepare_packets, post_packet, udp_key, match_code,
                    account_id, player_region, client_version, tag="[?]",
                    account_jwt="", sleep_ms=0):
    match_start = time.time()
    ping_task = afk_task = hello_task = sock = None
    ping_stop = asyncio.Event(); afk_stop = asyncio.Event()
    state = MovementState(account_id); reason = "ended"
    try:
        ip, port = server_ip_port.split(":"); port = int(port)
        resolved_ip = socket.gethostbyname(ip)
        loop = asyncio.get_event_loop()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        optimize_udp_socket(sock); sock.setblocking(False)
        udp_key_b = bytes.fromhex(udp_key)
        remote = (resolved_ip, port)
        gap = sleep_ms / 1000.0 if sleep_ms else 0.02
        if account_jwt:
            await loop.sock_sendto(sock, build_auth_datagram(account_jwt, account_id), remote)
        hello_hex = await build_hello_packet(f"{account_id}_2585", udp_key_b, match_code)
        hello_bytes = bytes.fromhex(hello_hex)
        await loop.sock_sendto(sock, hello_bytes, remote)
        udp_log_print(f"{tag} UDP connected  remote={resolved_ip}:{port}")
        ack_state = "waiting_for_hello_reply"
        startup_sent = False; local_closed = False
        send_lock = asyncio.Lock()
        nr = (await layouts_from_mask(match_code))[1]

        async def ka_loop():
            pklist = [0x66,0x6D,0x69,0x6C,0x6B,0x6E,0x6F,0x70]; i = 0
            while not ping_stop.is_set():
                if ack_state != "waiting_for_hello_reply": break
                try: await asyncio.wait_for(ping_stop.wait(), timeout=0.1)
                except asyncio.TimeoutError: pass
            while not ping_stop.is_set():
                pk = pklist[i % len(pklist)]
                cnt = int(time.time()*1000) & 0xFFFFFFFF
                pkt = await build_packet(pk, nr, 0, 3, None, 0,
                                         cnt.to_bytes(4,"little") + b"\x00\x00\x00",
                                         udp_key_b, encrypted=False)
                try: await loop.sock_sendto(sock, pkt, remote)
                except Exception: pass
                i += 1
                try: await asyncio.wait_for(ping_stop.wait(), timeout=3.0)
                except asyncio.TimeoutError: pass

        async def hello_retry_loop():
            for _ in range(8):
                if ping_stop.is_set() or ack_state != "waiting_for_hello_reply": return
                try: await asyncio.wait_for(ping_stop.wait(), timeout=0.8)
                except asyncio.TimeoutError: pass
                if ping_stop.is_set() or ack_state != "waiting_for_hello_reply": return
                try: await loop.sock_sendto(sock, hello_bytes, remote)
                except Exception: pass

        ping_task = asyncio.create_task(ka_loop())
        hello_task = asyncio.create_task(hello_retry_loop())
        afk_task = asyncio.create_task(movement_loop(sock, remote, udp_key_b,
                                                     match_code, state, afk_stop, tag))
        last_activity = time.time()

        async def send_join_match():
            nonlocal ack_state, startup_sent
            if startup_sent: return
            async with send_lock:
                if startup_sent: return
                for p in prepare_packets:
                    await loop.sock_sendto(sock, bytes.fromhex(p), remote)
                    await asyncio.sleep(gap)
                await asyncio.sleep(gap)
                await loop.sock_sendto(sock, bytes.fromhex(post_packet), remote)
                startup_sent = True; ack_state = "startup_sent"
                udp_log_print(f"{tag} → PREPARE+POST sent")

        while not local_closed:
            if time.time() - match_start > MATCH_MAX_LIFETIME:
                reason = "ended"; break
            try:
                resp, sa = await asyncio.wait_for(loop.sock_recvfrom(sock, 65535), timeout=1.5)
                if resp:
                    last_activity = time.time()
                    frame = await decode_packet(resp, udp_key_b, match_code)
                    if frame:
                        cmd = frame.get('cmd'); oid = frame.get('orderId')
                        msg_key = frame.get('msgKey', 0); content = frame.get('content')
                        if msg_key < 100 and oid is not None:
                            da = await build_packet(0x68, nr, 0, 2, None, 1,
                                                    ((oid + 1) & 0xFFFF).to_bytes(2, "little"),
                                                    udp_key_b)
                            await loop.sock_sendto(sock, da, sa)
                        if cmd == 1:
                            if ack_state == "waiting_for_hello_reply":
                                ack_state = "ready_to_send_startup"
                        elif cmd == 3:
                            c = content or b""
                            cnt = c[:4] if len(c) >= 4 else c
                            rp = await build_packet(0x6D, nr, 0, 3, None, 0,
                                                    cnt + b"\x00\x00\x00", udp_key_b,
                                                    encrypted=False)
                            await loop.sock_sendto(sock, rp, sa)
                        elif cmd == 130:
                            udp_log_print(f"{tag}   ✅ JOIN_MATCH_FINISHED — in game")
                        elif cmd == 103:
                            udp_log_print(f"{tag}   🏁 MATCH_END received")
                            local_closed = True; reason = "ended"
                        dispatch_incoming(cmd, content, state, tag)
            except asyncio.TimeoutError: pass
            except Exception as e:
                udp_log_print(f"{tag} UDP err: {e}")
                await asyncio.sleep(0.5)
            if ack_state == "ready_to_send_startup" and not startup_sent:
                await send_join_match()
            elif ack_state == "startup_sent" and (time.time() - last_activity) > 30:
                reason = "ended"; break
    except Exception as e:
        udp_log_print(f"{tag} UDP err: {e}"); reason = "error"
    finally:
        ping_stop.set(); afk_stop.set()
        for t in (ping_task, hello_task, afk_task):
            if t: t.cancel()
        if sock:
            try: sock.close()
            except Exception: pass
        udp_log_print(f"{tag} UDP closed  reason={reason}")
    return reason

# ═══════════════════════════════════════════════════════════════════════════
#   SECTION 15 — ACCOUNT LOGIN (bridge to gameplay)
# ═══════════════════════════════════════════════════════════════════════════
GUEST_TOKEN_URL     = "https://100067.connect.garena.com/oauth/guest/token/grant"
GUEST_CLIENT_SECRET = "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3"
GUEST_CLIENT_ID     = "100067"

_UA_VERSIONS = ['4.0.18P6','4.0.19P7','4.0.20P1','4.1.0P3','4.1.5P2','4.2.1P8',
                '4.2.3P1','5.0.1B2','5.0.2P4','5.1.0P1','5.2.0B1','5.2.5P3',
                '5.3.0B1','5.3.2P2','5.4.0P1','5.4.3B2','5.5.0P1','5.5.2P3']
_UA_MODELS = ['SM-A125F','SM-A225F','SM-A325M','SM-A515F','SM-A725F','SM-M215F',
              'SM-M325FV','Redmi 9A','Redmi 9C','POCO M3','POCO M4 Pro','RMX2185',
              'RMX3085','moto g(9) play','CPH2239','V2027','OnePlus Nord','ASUS_Z01QD']
_UA_ANDROIDS = ['9','10','11','12','13','14']
_UA_LANGS = ['en-US','bn-BD','hi-IN','id-ID']
_UA_COUNTRY = ['BGD','IND','IDN']

def _rand_ua():
    return (f"GarenaMSDK/{random.choice(_UA_VERSIONS)}"
            f"({random.choice(_UA_MODELS)};Android {random.choice(_UA_ANDROIDS)};"
            f"{random.choice(_UA_LANGS)};{random.choice(_UA_COUNTRY)};)")

async def get_guest_token(uid, password, max_retries=6):
    headers = {
        "Host": "100067.connect.garena.com",
        "User-Agent": _rand_ua(),
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "close",
    }
    data = {"uid": uid, "password": password, "response_type": "token", "client_type": "2",
            "client_secret": GUEST_CLIENT_SECRET, "client_id": GUEST_CLIENT_ID}
    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(GUEST_TOKEN_URL, headers=headers, data=data) as r:
                    if r.status != 200:
                        last_err = f"HTTP {r.status}: {(await r.text())[:120]}"
                        await asyncio.sleep(min(2.0 * attempt, 10.0)); continue
                    j = await r.json()
                    oid = j.get("open_id"); tok = j.get("access_token")
                    plat = j.get("platform", 4)
                    if oid and tok: return oid, tok, int(plat or 4)
                    last_err = f"missing fields: {j}"
        except Exception as e: last_err = str(e)
        await asyncio.sleep(min(2.0 * attempt, 10.0))
    raise RuntimeError(f"guest token grant failed: {last_err}")

def load_generated_accounts(path=ACCOUNTS_FILE):
    if not os.path.exists(path): return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list): return []
        out = []
        for rec in data:
            if not isinstance(rec, dict): continue
            if not rec.get("uid") or not (rec.get("pass") or rec.get("password")): continue
            out.append(rec)
        return out
    except Exception as e:
        print(f"[!] failed to read {path}: {e}"); return []

async def login_new_account(rec, cfg, tag, max_retries=6):
    uid = rec["uid"]
    password = rec.get("pass") or rec.get("password")
    open_id = rec.get("open_id"); access_token = rec.get("access_token")
    platform = rec.get("platform")
    if not open_id or not access_token:
        open_id, access_token, platform = await get_guest_token(uid, password)
        rec["open_id"] = open_id; rec["access_token"] = access_token; rec["platform"] = platform
    platform = int(platform or 4)
    login = None; last_err = None
    async with _LOGIN_LOCK:
        for attempt in range(1, max_retries + 1):
            try:
                login = await asyncio.to_thread(major_login, tag, open_id,
                                                access_token, cfg, platform, REGION)
                break
            except Exception as e:
                last_err = e; await asyncio.sleep(min(2.0 * attempt, 15.0))
        if login is None:
            raise RuntimeError(f"{tag} major_login gave up: {last_err}")
    payload = decode_jwt_payload(login["jwt"]) if login.get("jwt") else {}
    lock_reg = (payload.get("lock_region") or "").upper()
    cfg_use = cfg
    if lock_reg and lock_reg != REGION:
        print(f"{tag} ⚠ lock_region={lock_reg} — binding to JWT region")
        confirmed = await asyncio.to_thread(choose_region, tag, login["jwt"], cfg, lock_reg)
        cfg_use = {**cfg, "country_code": confirmed, "region": confirmed}
        login = await asyncio.to_thread(major_login, tag, open_id, access_token,
                                        cfg_use, platform, confirmed)
    ld = await asyncio.to_thread(get_login_data, tag, open_id, access_token,
                                 cfg_use, platform, login["jwt"])
    fields = login["fields"]
    ts      = first_value(fields, 21, "varint")
    key_raw = first_value(fields, 22, "bytes") or first_value(fields, 22, "string")
    iv_raw  = first_value(fields, 23, "bytes") or first_value(fields, 23, "string")
    if ts is None or key_raw is None or iv_raw is None:
        raise RuntimeError(f"{tag} missing key/iv/ts")
    print(f"{tag} login ok id={login['account_id']} online={ld['game_server']} "
          f"lock_region={lock_reg or REGION}")
    return {"tag": tag, "uid": uid, "ingame_id": login["account_id"],
            "open_id": open_id, "access_token": access_token, "jwt": login["jwt"],
            "key": _to_bytes(key_raw), "iv": _to_bytes(iv_raw), "ts": ts,
            "game_server": ld["game_server"], "chat_server": ld["chat_server"],
            "server_url": login.get("game_url"), "name": rec.get("name", "?"),
            "cfg": cfg_use, "lock_region": lock_reg or REGION}

# ═══════════════════════════════════════════════════════════════════════════
#   SECTION 16 — SQUAD LOOPS (master / slave)
# ═══════════════════════════════════════════════════════════════════════════
def collect_all_ints(obj, out):
    if isinstance(obj, dict):
        if "data" in obj and isinstance(obj["data"], int): out.add(obj["data"])
        for v in obj.values(): collect_all_ints(v, out)
    elif isinstance(obj, list):
        for x in obj: collect_all_ints(x, out)
    elif isinstance(obj, int): out.add(obj)

def _match_info_from_frame(ptype, cmd, decoded):
    if not isinstance(decoded, dict): return None
    is_matchmaking = (ptype == 0x03 and cmd == 5)
    is_reconnect   = (ptype == 0x11 and cmd == 3)
    if not (is_matchmaking or is_reconnect): return None
    r5 = decoded.get("5") or {}
    if not isinstance(r5, dict): return None
    def _u(v): return v.get("data") if isinstance(v, dict) else v
    ip_port = _u(r5.get("2")); udp_key = _u(r5.get("3"))
    token   = _u(r5.get("4")); mcode   = _u(r5.get("42"))
    if not (isinstance(ip_port, str) and ":" in ip_port): return None
    if isinstance(udp_key, str):
        try: bytes.fromhex(udp_key)
        except ValueError: return None
    else: return None
    if token is None: return None
    if isinstance(token, bytes): token = token.decode("utf-8", "ignore")
    if not isinstance(token, str): return None
    if mcode is None: return None
    mcode = str(mcode)
    if not mcode.isdigit(): return None
    r5_clean = dict(r5)
    r5_clean["2"] = ip_port; r5_clean["3"] = udp_key
    r5_clean["4"] = token; r5_clean["42"] = mcode
    return r5_clean

async def slave_loop(acct, holder, match_infos, stop_evt):
    tag = acct["tag"]
    ip, port = acct["game_server"].split(":")
    key, iv = acct["key"], acct["iv"]
    jwt = acct["jwt"]; ingame_id = int(acct["ingame_id"]); ts = acct["ts"]
    region = acct.get("lock_region", REGION)
    auth_online = await build_auth_packet(ingame_id, jwt, ts, key, iv, region, "OnLine")
    ka_bytes = await send_keep_alive(region)
    remote_version = acct["cfg"].get("remote_version", Play_Version)
    try:
        reader, writer = await asyncio.open_connection(ip, int(port))
        writer.write(auth_online); await writer.drain()
        writer.write(ka_bytes); await writer.drain()
        print(f"{tag} ONLINE auth sent  id={ingame_id}")
        ka_stop = asyncio.Event()
        async def ka_loop():
            while not ka_stop.is_set():
                try:
                    await asyncio.sleep(15)
                    writer.write(ka_bytes); await writer.drain()
                except Exception: return
        ka_task = asyncio.create_task(ka_loop())
        print(f"{tag} waiting for master team code…")
        try: await asyncio.wait_for(holder["team_code_ready"].wait(), 60)
        except asyncio.TimeoutError:
            print(f"{tag} timeout waiting for team code"); return
        team_code = holder["team_code"]
        j = br_join_team_pkt(team_code, region, remote_version, key, iv)
        writer.write(j); await writer.drain()
        print(f"{tag} 📡 JOIN sent  code={team_code!r}")
        joined = False; join_sent_at = time.time(); buf = bytearray()
        while not stop_evt.is_set():
            try: chunk = await asyncio.wait_for(reader.read(65536), timeout=1.0)
            except asyncio.TimeoutError: chunk = None
            except Exception: break
            if chunk:
                buf.extend(chunk)
                while len(buf) >= 5:
                    ptype = buf[0]; plen = int.from_bytes(buf[1:5], "big")
                    if plen > 100_000 or len(buf) < 5 + plen: break
                    payload = bytes(buf[5:5+plen]); del buf[:5+plen]
                    decoded = None
                    try: decoded = await DeCode_PackEt(payload.hex())
                    except Exception: pass
                    cmd = decoded.get("4") if isinstance(decoded, dict) else None
                    if ptype == 0x05 and plen >= 200 and not joined:
                        joined = True
                        holder["slave_joined"].add(ingame_id)
                        print(f"{tag} ✅ joined squad")
                    if ptype == 0x05 and isinstance(decoded, dict) and cmd == 10:
                        print(f"{tag} ✅ START_NTF")
                    minfo = _match_info_from_frame(ptype, cmd, decoded)
                    if minfo is not None:
                        match_infos[tag] = minfo; joined = True
                        holder["slave_joined"].add(ingame_id)
                        print(f"{tag} ⚡ MATCH info  server={minfo['2']}")
            if not joined and time.time() - join_sent_at > 6:
                joined = True
                holder["slave_joined"].add(ingame_id)
                print(f"{tag} ✅ assumed joined")
        ka_stop.set(); ka_task.cancel()
        writer.close()
        try: await writer.wait_closed()
        except Exception: pass
    except Exception as e:
        print(f"{tag} conn err: {e}")

async def master_loop(acct, slave_ids, holder, match_infos, start_evt, stop_evt):
    tag = acct["tag"]
    ip, port = acct["game_server"].split(":")
    key, iv = acct["key"], acct["iv"]
    jwt = acct["jwt"]; ingame_id = int(acct["ingame_id"]); ts = acct["ts"]
    region = acct.get("lock_region", REGION)
    slave_set = {int(x) for x in slave_ids}
    remote_version = acct["cfg"].get("remote_version", Play_Version)
    auth_online = await build_auth_packet(ingame_id, jwt, ts, key, iv, region, "OnLine")
    ka_bytes = await send_keep_alive(region)
    reader, writer = await asyncio.open_connection(ip, int(port))
    writer.write(auth_online); await writer.drain()
    writer.write(ka_bytes); await writer.drain()
    print(f"{tag} ONLINE auth sent  id={ingame_id}")
    ka_stop = asyncio.Event()
    async def ka_loop():
        while not ka_stop.is_set():
            try:
                await asyncio.sleep(15)
                writer.write(ka_bytes); await writer.drain()
            except Exception: return
    ka_task = asyncio.create_task(ka_loop())
    await asyncio.sleep(1.0)
    writer.write(br_create_squad_pkt(region, remote_version, key, iv)); await writer.drain()
    print(f"{tag} 📡 CREATE SQUAD sent")
    created = False; op31_sent = False; buf = bytearray(); start_sent_flag = False
    try:
        while not stop_evt.is_set():
            if start_evt.is_set() and not start_sent_flag:
                if holder["team_code"] and created and holder["slave_joined"] >= slave_set:
                    s = br_start_squad_pkt(ingame_id, region, key, iv)
                    try:
                        writer.write(s); await writer.drain()
                        start_sent_flag = True; start_evt.clear()
                        print(f"{tag} 📡 START sent (team full)")
                    except Exception as e: print(f"{tag} start err: {e}")
            try: chunk = await asyncio.wait_for(reader.read(65536), timeout=1.0)
            except asyncio.TimeoutError: chunk = None
            except Exception as e:
                print(f"{tag} read err: {e}"); break
            if chunk:
                buf.extend(chunk)
                while len(buf) >= 5:
                    ptype = buf[0]; plen = int.from_bytes(buf[1:5], "big")
                    if plen > 100_000 or len(buf) < 5 + plen: break
                    payload = bytes(buf[5:5+plen]); del buf[:5+plen]
                    decoded = None
                    try: decoded = await DeCode_PackEt(payload.hex())
                    except Exception: pass
                    cmd = decoded.get("4") if isinstance(decoded, dict) else None
                    if ptype == 0x05 and isinstance(decoded, dict):
                        data = decoded.get("5", {})
                        if cmd == 1 and not created and plen >= 100:
                            gid = None
                            if isinstance(data, dict):
                                g = data.get("1")
                                if isinstance(g, dict): g = g.get("data")
                                if isinstance(g, int): gid = g
                            top_g = decoded.get("1")
                            if isinstance(top_g, dict): top_g = top_g.get("data")
                            if gid is None and isinstance(top_g, int): gid = top_g
                            created = True; holder["group_id"] = gid
                            print(f"{tag} ✅ CREATE_NTF  group_id={gid}")
                        elif cmd == 32 and not holder["team_code"]:
                            tc_val = None
                            if isinstance(data, dict):
                                t = data.get("1")
                                if isinstance(t, dict): t = t.get("data")
                                if isinstance(t, (str, int)): tc_val = str(t)
                            if tc_val is None:
                                t = decoded.get("1")
                                if isinstance(t, dict): t = t.get("data")
                                if isinstance(t, (str, int)): tc_val = str(t)
                            if tc_val:
                                holder["team_code"] = tc_val
                                holder["team_code_ready"].set()
                                print(f"{tag} ✅ GETGROUPCODE  team_code={tc_val!r}")
                        if created and not op31_sent and holder["group_id"]:
                            op31_sent = True
                            try:
                                p31 = await send_op31(holder["group_id"], region, key, iv)
                                writer.write(p31); await writer.drain()
                            except Exception: pass
                        if cmd == 6:
                            found = set(); collect_all_ints(decoded, found)
                            newj = found & slave_set
                            if newj:
                                print(f"{tag} ✅ JOIN_NTF  seen={sorted(newj)}")
                                holder["slave_joined"] |= newj
                        elif cmd == 10: print(f"{tag} ✅ START_NTF")
                        elif cmd == 13:
                            print(f"{tag} ⚠ DISMISS_NTF")
                            holder["team_code_ready"].clear(); holder["team_code"] = None
                            created = False; op31_sent = False; start_sent_flag = False
                    minfo = _match_info_from_frame(ptype, cmd, decoded)
                    if minfo is not None:
                        match_infos[tag] = minfo
                        print(f"{tag} ⚡ MATCH info  server={minfo['2']}")
                    if ptype == 0x03 and cmd == 14:
                        print(f"{tag} ⚠ MATCHMAKING STOP_NTF")
    finally:
        ka_stop.set(); ka_task.cancel()
        writer.close()
        try: await writer.wait_closed()
        except Exception: pass

# ═══════════════════════════════════════════════════════════════════════════
#   SECTION 17 — BOT GAMEPLAY ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════════
def setup_app_region():
    global LANG_CODE, ACCOUNT_FILE, SERVER_URL, CLIENT_URL
    LANG_CODE = LANG
    ACCOUNT_FILE = f"{REGION}_Account.json"
    grp = REGION_GROUP.get(REGION, REGION)
    if grp in REGION_URLS:
        SERVER_URL = REGION_URLS[grp]["server"]
        CLIENT_URL = REGION_URLS[grp]["client"]

async def main():
    if UDP_LOG_FILE is not None:
        try:
            with open(UDP_LOG_FILE, "w", encoding="utf-8") as f:
                f.write(f"# UDP log — run at {datetime.now().isoformat()}\n")
        except Exception: pass

    setup_app_region()
    cfg = dict(HARDCODED_CONFIG)

    # Clear old control file
    try:
        if os.path.exists(CONTROL_FILE): os.remove(CONTROL_FILE)
    except: pass

    raw_records = load_generated_accounts()

    selected_file = "selected_accounts.json"
    if os.path.exists(selected_file):
        try:
            with open(selected_file, "r", encoding="utf-8") as f:
                selected_uids = {str(u) for u in json.load(f)}
            before = len(raw_records)
            raw_records = [r for r in raw_records if str(r.get("uid")) in selected_uids]
            print(f"[*] Web panel filter: {len(raw_records)}/{before} accounts selected")
        except Exception as e:
            print(f"[!] selected_accounts.json read fail: {e}")

    if len(raw_records) < 2:
        print(f"[!] {ACCOUNTS_FILE} has {len(raw_records)} accounts, need ≥2")
        sys.exit(1)
    if len(raw_records) > TOTAL_ACCOUNTS:
        print(f"[*] more than {TOTAL_ACCOUNTS} records — using first {TOTAL_ACCOUNTS}")
        raw_records = raw_records[:TOTAL_ACCOUNTS]
    records = raw_records

    print(f"[*] using {len(records)} account(s)")
    print(f"[*] REGION={REGION}")

    accounts = []
    for i, rec in enumerate(records):
        tag = "[M]" if i == 0 else f"[S{i}]"
        try:
            acct = await login_new_account(rec, cfg, tag)
            dev = get_device_for_account(acct["ingame_id"])
            print(f"[+] {tag} assigned device: {dev['brand']} {dev['model']}")
            accounts.append(acct)
        except Exception as e:
            print(f"{tag} login failed: {e}"); sys.exit(1)
        await asyncio.sleep(1.5)

    master = accounts[0]; slaves = accounts[1:]
    slave_ids = {int(s["ingame_id"]) for s in slaves}
    print()
    print(f"[*] master [M] id={master['ingame_id']} region={master['lock_region']}")
    for s in slaves:
        print(f"[*] slave  {s['tag']} id={s['ingame_id']} region={s['lock_region']}")
    print()

    holder = {"group_id": None, "team_code": None,
              "team_code_ready": asyncio.Event(),
              "slave_joined": set(), "master_id": None}
    match_infos = {}; stop_evt = asyncio.Event(); start_evt = asyncio.Event()

    slave_tasks = [asyncio.create_task(
        slave_loop(s, holder, match_infos, stop_evt)) for s in slaves]
    await asyncio.sleep(2.0)
    master_task = asyncio.create_task(
        master_loop(master, list(slave_ids), holder, match_infos, start_evt, stop_evt))

    expected_tags = [a["tag"] for a in accounts]
    print(f"\n{'═'*60}\n[*] SINGLE ROUND — will exit after match\n{'═'*60}")

    print(f"[*] waiting for team to fill ({len(slave_ids)+1} players)…")
    t0 = time.time()
    while time.time() - t0 < 60:
        if holder["slave_joined"] >= slave_ids and holder["team_code"]: break
        if stop_evt.is_set(): break
        await asyncio.sleep(0.5)
    print(f"[*] team full: slaves={sorted(holder['slave_joined'])} code={holder['team_code']}")
    start_evt.set()

    print(f"[*] waiting for MATCH info from {expected_tags}…")
    deadline = time.time() + MATCH_INFO_TIMEOUT
    while time.time() < deadline:
        if all(t in match_infos for t in expected_tags): break
        if stop_evt.is_set(): break
        await asyncio.sleep(0.5)

    missing = [t for t in expected_tags if t not in match_infos]
    if missing:
        print(f"[!] no MATCH info for {missing} — exiting")
        stop_evt.set()
        for t in slave_tasks + [master_task]: t.cancel()
        await asyncio.gather(*slave_tasks, *[master_task], return_exceptions=True)
        return

    print(f"[*] all MATCH info received — joining UDP")
    udp_tasks = []
    for a in accounts:
        r5 = match_infos[a["tag"]]
        server_ip_port = r5["2"]; udp_key = r5["3"]
        join_token = r5["4"]; match_code = r5["42"]
        def _u(v): return v.get("data") if isinstance(v, dict) else v
        real_match_id   = _u(r5.get("1") or 0) or 0
        real_map_id     = _u(r5.get("6") or 1) or 1
        real_game_mode  = _u(r5.get("7") or 15) or 15
        real_match_mode = _u(r5.get("8") or 1) or 1
        real_sleep_ms   = _u(r5.get("5") or 0) or 0
        print(f"[+] {a['tag']} server={server_ip_port} code={match_code}")
        prepare_packets, post_packet = await build_join_match_startup(
            join_token, udp_key, match_code,
            int(a["ingame_id"]), real_match_id,
            server_ip=server_ip_port, region=a.get("lock_region", REGION),
            client_version=a["cfg"].get("remote_version", Play_Version),
            client_version_code="2019121229", access_token=a["access_token"],
            match_id=real_match_id, country="BD",
            map_id=real_map_id, game_mode=real_game_mode, match_mode=real_match_mode)
        udp_tasks.append(asyncio.create_task(play_game(
            server_ip_port, prepare_packets, post_packet, udp_key, match_code,
            int(a["ingame_id"]), a.get("lock_region", REGION),
            a["cfg"].get("remote_version", Play_Version),
            tag=a["tag"], account_jwt=join_token, sleep_ms=real_sleep_ms)))

    try:
        results = await asyncio.gather(*udp_tasks, return_exceptions=True)
        print(f"\n[*] match ended — results={results}")
    except Exception as e:
        print(f"[*] gather err: {e}")

    stop_evt.set()
    for t in slave_tasks + [master_task]: t.cancel()
    await asyncio.gather(*slave_tasks, *[master_task], return_exceptions=True)
    print(f"\n{'█'*60}\n[*] MATCH DONE — waiting 5s to restart...\n{'█'*60}\n")

# ═══════════════════════════════════════════════════════════════════════════
#   SECTION 18 — VERSION UPDATER
# ═══════════════════════════════════════════════════════════════════════════
def get_freefire_update_info():
    url = "https://play.google.com/store/apps/details?id=com.dts.freefireth&hl=ar&gl=DZ"
    headers = {"User-Agent": USER_AGENT_WEB}
    response = requests.get(url, headers=headers); response.raise_for_status()
    versions = re.findall(r"\b(1\.\d{1,3}\.\d{1,3})\b", response.text)
    if not versions: raise Exception("No version found")
    return versions[-1]

def GeT_OB(PlAy_VerSioN):
    UrL = (f"https://version.ggwhitehawk.com/live/ver.php?version={PlAy_VerSioN}"
           f"&lang=en&device=android&channel=3rd_party&appstore=thirdparty&region=IND"
           f"&whitelist_version=1.7.0&whitelist_sp_version=1.0.0"
           f"&device_name=vivo%20V2538&device_CPU=ARM64%20FP%20ASIMD%20AES"
           f"&device_GPU=Adreno%20%28TM%29%20722&device_mem=7282")
    ReSp = requests.get(UrL); ReSp = ReSp.json()
    return ReSp.get("latest_release_version"), ReSp.get("server_url")

def update_versions():
    PlAy_VeR = get_freefire_update_info()
    Ob_VeR_new, LoGiN_UrL_new = GeT_OB(PlAy_VeR)
    if not PlAy_VeR: print("no version found"); return
    with open(__file__, "r") as f: lines = f.readlines()
    with open(__file__, "w") as f:
        for line in lines:
            if   line.lstrip().startswith("Play_Version ="):
                f.write(f'Play_Version = "{PlAy_VeR}"\n')
            elif line.lstrip().startswith("Ob_VeR ="):
                f.write(f'Ob_VeR = "{Ob_VeR_new}"\n')
            elif line.lstrip().startswith("LoGiN_UrL ="):
                f.write(f'LoGiN_UrL = "{LoGiN_UrL_new}"\n')
            else:
                f.write(line)
    print(f"✅ Version updated: Play_Version={PlAy_VeR}  Ob_VeR={Ob_VeR_new}")

# ═══════════════════════════════════════════════════════════════════════════
#   SECTION 19 — WEB PANEL (FastAPI + Live Monitoring)
# ═══════════════════════════════════════════════════════════════════════════
BASE_DIR          = Path(__file__).parent.resolve()
WEB_ACCOUNTS_FILE = BASE_DIR / "squad_accounts.json"
WEB_SELECTED_FILE = BASE_DIR / "selected_accounts.json"
WEB_LOG_FILE      = BASE_DIR / "bot.log"
INDEX_FILE        = BASE_DIR / "index.html"

app = FastAPI(title="Bot Squad Panel")
_worker_process    = None
_worker_log_handle = None
_worker_started_at = None
_worker_log_thread = None

_ANSI_RE = re.compile(r'\x1b\[[0-9;]*m')

def _web_load_accounts():
    if not WEB_ACCOUNTS_FILE.exists(): return []
    try: return json.loads(WEB_ACCOUNTS_FILE.read_text(encoding="utf-8"))
    except Exception: return []

def _web_save_accounts(a):
    WEB_ACCOUNTS_FILE.write_text(
        json.dumps(a, indent=2, ensure_ascii=False), encoding="utf-8")

def _web_is_running():
    return _worker_process is not None and _worker_process.poll() is None

def _web_load_selected():
    if not WEB_SELECTED_FILE.exists(): return []
    try: return [str(x) for x in json.loads(WEB_SELECTED_FILE.read_text(encoding="utf-8"))]
    except Exception: return []

def _web_read_log():
    if not WEB_LOG_FILE.exists(): return ""
    try: return _ANSI_RE.sub("", WEB_LOG_FILE.read_text(encoding="utf-8", errors="replace"))
    except Exception: return ""

def _worker_log_reader(process, log_handle):
    # Reads logs from subprocess, prints to Termux AND writes to file
    for line in iter(process.stdout.readline, b''):
        text = line.decode('utf-8', errors='replace')
        log_handle.write(text)
        log_handle.flush()
        # Prints to terminal live
        print(text, end='', flush=True)

_BOT_STAGES = [
    ("login failed",           "error",  "login failed",  "red"),
    ("login ok",               "online", "logged in",     "blue"),
    ("assigned device",        "online", "logging in",    "blue"),
    ("ONLINE auth sent",       "online", "online",        "cyan"),
    ("joined squad",           "squad",  "in squad",      "yellow"),
    ("assumed joined",         "squad",  "in squad",      "yellow"),
    ("START_NTF",              "match",  "match starting", "orange"),
    ("MATCH info",             "match",  "match found",   "orange"),
    ("UDP connected",          "game",   "in match",      "purple"),
    ("JOIN_MATCH_FINISHED",    "game",   "playing",       "green"),
    ("MATCH_END",              "ended",  "match ended",   "gray"),
    ("UDP closed",             "ended",  "closed",        "gray"),
]

def _web_get_bot_status():
    selected = _web_load_selected()
    acc_map  = {str(a.get("uid")): a for a in _web_load_accounts()}
    log_lines = _web_read_log().split("\n")

    bots = []
    for i, uid in enumerate(selected):
        uid = str(uid)
        tag = "M" if i == 0 else f"S{i}"
        acc = acc_map.get(uid, {})
        bots.append({
            "uid": uid, "tag": tag,
            "name": acc.get("name", uid),
            "ingame_id": acc.get("ingame_id", ""),
            "status": "idle", "stage": "waiting", "color": "gray",
            "server": "", "match_code": "",
        })
    if not bots: return []

    for line in log_lines:
        if not line.strip(): continue
        for bot in bots:
            tag_pat = f"[{bot['tag']}]"
            if tag_pat not in line: continue
            low = line.lower()
            for kw, status, label, color in _BOT_STAGES:
                if kw.lower() in low:
                    if bot["status"] == "ended" and status not in ("online", "game"):
                        if status != "error": continue
                    bot["status"] = status
                    bot["stage"]  = label
                    bot["color"]  = color
            
            m = re.search(r'login ok id=(\d+)', line)
            if m: bot["ingame_id"] = m.group(1)
            
            m = re.search(r'online=([\d\.]+:\d+)', line)
            if m: bot["server"] = m.group(1)
            
            m = re.search(r'server=([\d\.]+:\d+)', line)
            if m: bot["server"] = m.group(1)
            
            m = re.search(r'code=(\d+)', line)
            if m: bot["match_code"] = m.group(1)

    return bots


def _web_get_match_info():
    log_lines = _web_read_log().split("\n")
    match = {"server": "", "code": "", "running": False, "started_at": None}
    for line in log_lines:
        m = re.search(r'server=([\d\.]+:\d+)\s+code=(\d+)', line)
        if m:
            match["server"] = m.group(1)
            match["code"]   = m.group(2)
            match["running"] = True
        if "MATCH_END received" in line or "MATCH DONE" in line:
            match["running"] = False
    return match

@app.get("/")
def index():
    if not INDEX_FILE.exists():
        return PlainTextResponse(
            f"index.html not found.\nExpected at: {INDEX_FILE}", status_code=404)
    return FileResponse(INDEX_FILE)

@app.get("/api/accounts")
def api_accounts():
    return _web_load_accounts()

class NewAccount(BaseModel):
    uid: str
    password: str
    name: str = ""

@app.post("/api/accounts")
def api_add_account(a: NewAccount):
    if not a.uid.strip() or not a.password.strip():
        raise HTTPException(400, "UID ও Password দুটোই দরকার")
    accts = _web_load_accounts()
    if any(str(x.get("uid")) == a.uid.strip() for x in accts):
        raise HTTPException(400, "এই UID আগেই আছে")
    accts.append({"uid": a.uid.strip(), "pass": a.password.strip(),
                  "name": a.name.strip() or a.uid.strip()})
    _web_save_accounts(accts)
    return {"ok": True, "count": len(accts)}

@app.delete("/api/accounts/{uid}")
def api_del_account(uid: str):
    new = [x for x in _web_load_accounts() if str(x.get("uid")) != uid]
    _web_save_accounts(new)
    return {"ok": True, "count": len(new)}

class StartReq(BaseModel):
    uids: list

@app.post("/api/start")
def api_start(r: StartReq):
    global _worker_process, _worker_log_handle, _worker_started_at, _worker_log_thread
    if _web_is_running():
        raise HTTPException(400, "বট ইতিমধ্যে চলছে")
    if len(r.uids) < 2:
        raise HTTPException(400, "কমপক্ষে ২টা বট লাগবে")
    if len(r.uids) > 4:
        raise HTTPException(400, "সর্বোচ্চ ৪টা বট")
    valid = {str(x.get("uid")) for x in _web_load_accounts()}
    chosen = [u for u in r.uids if str(u) in valid]
    if len(chosen) < 2:
        raise HTTPException(400, "বাছাই করা UID খুঁজে পাওয়া যায়নি")

    WEB_SELECTED_FILE.write_text(json.dumps(chosen), encoding="utf-8")
    WEB_LOG_FILE.write_text("", encoding="utf-8")
    _worker_log_handle = open(WEB_LOG_FILE, "w", encoding="utf-8", buffering=1)
    _worker_started_at = time.time()

    _worker_process = subprocess.Popen(
        [sys.executable, "-u", str(Path(__file__).resolve()), "_worker"],
        cwd=str(BASE_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )
    
    # Start reading logs in background to show in Termux
    _worker_log_thread = threading.Thread(
        target=_worker_log_reader, 
        args=(_worker_process, _worker_log_handle),
        daemon=True
    )
    _worker_log_thread.start()

    return {"ok": True, "pid": _worker_process.pid,
            "count": len(chosen), "started_at": _worker_started_at}

@app.post("/api/stop")
def api_stop():
    global _worker_process, _worker_log_handle, _worker_started_at
    if _worker_process and _worker_process.poll() is None:
        _worker_process.terminate()
        try: _worker_process.wait(timeout=8)
        except subprocess.TimeoutExpired: _worker_process.kill()
    _worker_process = None
    _worker_started_at = None
    if _worker_log_handle:
        try: _worker_log_handle.close()
        except Exception: pass
        _worker_log_handle = None
    if WEB_SELECTED_FILE.exists():
        try: WEB_SELECTED_FILE.unlink()
        except Exception: pass
    if os.path.exists(CONTROL_FILE):
        try: os.remove(CONTROL_FILE)
        except: pass
    return {"ok": True}

@app.post("/api/control")
async def api_control(cmd: dict):
    # Save control commands to file
    try:
        Path(CONTROL_FILE).write_text(json.dumps(cmd))
        return {"ok": True}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/api/status")
def api_status():
    return {
        "running": _web_is_running(),
        "pid": _worker_process.pid if _web_is_running() else None,
        "started_at": _worker_started_at if _web_is_running() else None,
    }

@app.get("/api/bots")
def api_bots():
    return {
        "bots": _web_get_bot_status(),
        "match": _web_get_match_info(),
        "running": _web_is_running(),
        "started_at": _worker_started_at,
    }

@app.get("/api/log", response_class=PlainTextResponse)
def api_log():
    try:
        d = _web_read_log()
        return "\n".join(d.splitlines()[-500:])
    except Exception:
        return ""


def start_web_panel():
    import uvicorn
    import os

    PORT = int(os.environ.get("PORT", 8080))

    print(f"{CY}{B}╔══════════════════════════════════════════════════════════════════╗{R}")
    print(f"{CY}{B}║{R}  {WH}{B}🎮  BOT SQUAD  ·  WEB PANEL{R}")
    print(f"{CY}{B}╠══════════════════════════════════════════════════════════════════╣{R}")
    print(f"{CY}{B}║{R}  {D}local{R}    →  {GN}http://localhost:{PORT}{R}")
    print(f"{CY}{B}║{R}  {D}host{R}     →  {GN}http://0.0.0.0:{PORT}{R}")
    print(f"{CY}{B}║{R}  {D}index{R}    →  {GR}{INDEX_FILE}{R}")
    print(f"{CY}{B}╚══════════════════════════════════════════════════════════════════╝{R}")
    print()

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PORT,
        log_level="warning"
    )

# ═══════════════════════════════════════════════════════════════════════════
#   SECTION 20 — ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    args = sys.argv[1:]

    if "_worker" in args:
        while True:
            try:
                asyncio.run(main())
            except KeyboardInterrupt:
                print("\n[*] Stopped by user. Exiting.")
                break
            except Exception as e:
                print(f"\n[!] Round error: {e}")

            print("[*] Waiting 5s before next match...")
            time.sleep(5)

    elif "cli" in args:
        while True:
            try:
                asyncio.run(main())
            except KeyboardInterrupt:
                print("\n[*] Stopped by user. Exiting.")
                sys.exit(0)
            except Exception as e:
                print(f"\n[!] Round error: {e}")

            print("[*] Waiting 5s before next match...")
            time.sleep(5)

    elif "create" in args:
        create_accounts_cli()

    elif "update-versions" in args or "update" in args:
        update_versions()

    else:
        start_web_panel()