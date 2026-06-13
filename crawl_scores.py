"""
拉取个人成绩数据 → best_scores.json
依赖: token.txt (由 get_token.py 生成)
用法: python crawl_scores.py
"""
import json, requests, hashlib, time, random, os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
API = "https://wamusic.wahlap.net/api/info/mp"
PROJECT = "jubeat_release"
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")
COVER_DIR = os.path.join(SCRIPT_DIR, ".cover_cache")


def load_config():
    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError("config.json 不存在，请先运行 get_token.py")
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def api_post(action, data, config):
    ts = int(time.time())
    nonce = random.randint(1, 100000)
    sign = hashlib.sha256(f"{config['token']}{ts}{nonce}".encode()).hexdigest()
    data["action"] = action
    data["project"] = PROJECT
    if "roleid" not in data:
        data["roleid"] = config.get("roleid", "")
    resp = requests.post(API, json=data, headers={
        "atk": json.dumps({"timestamp": ts, "nonce": nonce, "sign": sign}),
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 MicroMessenger/7.0.20.1781(0x6700143B) NetType/WIFI MiniProgramEnv/Windows WindowsWechat/WMPF",
        "Referer": "https://servicewechat.com/wx133c9dfee00bbfec/34/page-frame.html",
    }, proxies={"http": None, "https": None}, timeout=20)
    result = resp.json()
    if not result.get("ok"):
        raise Exception(f"API error: {result.get('msg') or result}")
    return result["data"]


def main():
    global CONFIG_FILE, COVER_DIR
    CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")
    COVER_DIR = os.path.join(SCRIPT_DIR, ".cover_cache")

    config = load_config()

    # 1. rating_info — 一次拿到 60 首 (30 PICKUP + 30 COMMON)
    print("拉取成绩列表...")
    info = api_post("rating_info", {}, config)
    songs = info.get("list_pickup", []) + info.get("list_common", [])
    total = len(songs)
    print(f"共 {total} 首 (PICKUP {len(info.get('list_pickup',[]))} + COMMON {len(info.get('list_common',[]))})")

    # 2. 逐首 music_detail 获取明细
    scores_out = []
    for i, s in enumerate(songs):
        sid = s["songId"]
        diff = s["diff"]
        isHard = s["isHard"]
        n = i + 1
        name = s.get("name", "")[:12]
        pct = n * 100 // total
        bar = "#" * (pct // 5) + "-" * (20 - pct // 5)
        print(f"\r  [{bar}] {pct}% ({n}/{total}) {name}", end="", flush=True)

        # 先用 rating_info 的数据做保底
        entry = {
            "songId": sid,
            "name": s.get("name", ""),
            "artist": s.get("artist", ""),
            "diff": diff,
            "lv": 0,
            "isHard": isHard,
            "isTwo": 1 if "[2]" in s.get("name","") or "[ 2 ]" in s.get("name","") else 0,
            "score": 0,
            "musicRate": 0,
            "rating": s["rating"],
            "grade": 0,
            "pic": s.get("pic", ""),
            "type": "pickup" if i < 30 else "common",
        }
        try:
            detail = api_post("music_detail", {"songId": sid, "diff": diff, "isHard": isHard}, config)
            ss = detail.get("song_score", {})
            if ss:
                entry.update({
                    "name": detail.get("name", entry["name"]),
                    "artist": detail.get("artist", entry["artist"]),
                    "lv": detail.get("lv", 0),
                    "isTwo": 1 if "[2]" in detail.get("name","") or "[ 2 ]" in detail.get("name","") else 0,
                    "score": ss.get("score", 0),
                    "musicRate": ss.get("musicRate", 0),
                    "grade": ss.get("grade", 0),
                    "pic": detail.get("pic", entry["pic"]),
                })
        except Exception:
            pass
        scores_out.append(entry)
        time.sleep(0.15)
    print()

    # 3. 下载封面 (文件名 = songId.png)
    print("下载歌曲封面...")
    os.makedirs(COVER_DIR, exist_ok=True)
    dl_headers = {
        "Referer": "https://wazone-file.wahlap.net/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    for s in scores_out:
        sid = s.get("songId", "")
        if not sid:
            continue
        path = os.path.join(COVER_DIR, f"{sid}.png")
        if os.path.exists(path):
            s["pic_local"] = f".cover_cache/{sid}.png"
            continue
        url = s.get("pic", "")
        if not url:
            continue
        try:
            r = requests.get(url, headers=dl_headers, proxies={"http": None, "https": None}, timeout=15)
            if r.status_code == 200:
                with open(path, "wb") as f:
                    f.write(r.content)
                s["pic_local"] = f".cover_cache/{sid}.png"
                print(f"\r  封面 {sid} OK", end="", flush=True)
        except Exception as e:
            print(f"\r  封面 {sid} {e}", flush=True)
    print()

    # 4. 玩家信息
    print("拉取玩家信息...")
    player = api_post("player_info", {"playerId": 0}, config)

    avatar_url = player.get("photo", "")
    avatar_path = os.path.join(SCRIPT_DIR, ".static/jubeat/avatar.png")
    if avatar_url and not os.path.exists(avatar_path):
        try:
            r = requests.get(avatar_url, proxies={"http": None, "https": None}, timeout=10)
            with open(avatar_path, "wb") as f:
                f.write(r.content)
        except:
            pass

    result = {
        "nickName": player.get("nickName", ""),
        "monikerName": player.get("monikerName", ""),
        "rating_name": info.get("rating_name", ""),
        "rating_lv": info.get("rating_lv", 1),
        "rating_value": info.get("rating_value", 0),
        "jubilityRank": player.get("jubilityRank", "?"),
        "photo": avatar_url,
        "lv": player.get("lv", 1),
        "exp": player.get("exp", 0),
        "expMax": player.get("expMax", 100),
        "scores": scores_out,
    }

    out = os.path.join(SCRIPT_DIR, "best_scores.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"best_scores.json ({len(scores_out)} 首) 已生成")


if __name__ == "__main__":
    main()
