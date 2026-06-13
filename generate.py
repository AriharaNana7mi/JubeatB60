"""
检查资源 → 生成 scorecard.html → 无头浏览器渲染 → 保存 PNG
用法: python generate.py
"""
import os, sys, json, base64, subprocess, threading
from http.server import HTTPServer, SimpleHTTPRequestHandler

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PNG = os.path.join(SCRIPT_DIR, "jubeat_scorecard.png")

STATIC_FILES = [
    ".static/fonts/LINESeedSans_A_Bd.otf",
    ".static/jubeat/avatar.png",
    ".static/jubeat/bg_icon.png",
    ".static/jubeat/exp_not_bg.png",
    ".static/jubeat/jubeat_progress.png",
    ".static/jubeat/center/player_jubility.png",
    ".static/jubeat/rating/moniker_1.png",
] + [
    f".static/jubeat/rating/jby_ttljby_gauge_{str(i).zfill(2)}.png" for i in range(11)
] + [
    f".grade_cache/grade_{n}.png" for n in ['e','d','c','b','a','s','ss','sss','exc']
]

done = threading.Event()


class Handler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/save":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            img = base64.b64decode(body["image"].split(",", 1)[1])
            os.makedirs(os.path.dirname(OUTPUT_PNG), exist_ok=True)
            with open(OUTPUT_PNG, "wb") as f:
                f.write(img)
            print(f"PNG: {OUTPUT_PNG} ({len(img)//1024}KB)")
            done.set()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")

    def log_message(self, format, *args):
        pass


def check_assets():
    missing = []
    for path in STATIC_FILES:
        if not os.path.exists(os.path.join(SCRIPT_DIR, path)):
            missing.append(path)
    if missing:
        print(f"[!] 缺失 {len(missing)} 个文件，请重新解压")
        for m in missing[:5]:
            print(f"    {m}")
        return False
    return True


def main():
    global OUTPUT_PNG
    OUTPUT_PNG = os.path.join(SCRIPT_DIR, "jubeat_scorecard.png")

    print("音乐魔方 B60 成绩单\n")

    if not check_assets():
        return 1

    if not os.path.exists(os.path.join(SCRIPT_DIR, "scorecard.html")):
        print("[!] scorecard.html 不存在")
        return 1

    # 启动 HTTP 服务
    os.chdir(SCRIPT_DIR)
    server = HTTPServer(("127.0.0.1", 8080), Handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    # 找浏览器
    browsers = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    exe = None
    for b in browsers:
        if os.path.exists(b):
            exe = b
            break

    if not exe:
        print("[!] 未找到 Edge/Chrome，打开浏览器手动下载...")
        import webbrowser
        webbrowser.open("http://127.0.0.1:8080/scorecard.html")
        input("按回车退出...")
        server.shutdown()
        return 1

    print("渲染中...")
    proc = subprocess.Popen([
        exe, "--headless=new", "--disable-gpu",
        "--window-size=1200,900",
        "http://127.0.0.1:8080/scorecard.html",
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if done.wait(timeout=30):
        print("完成!")
    else:
        print("[!] 超时")

    proc.kill()
    server.shutdown()

    return 0 if os.path.exists(OUTPUT_PNG) else 1


if __name__ == "__main__":
    sys.exit(main())
