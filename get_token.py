"""
Token 获取工具 (hosts劫持 + HTTPS反向代理)
用法: 管理员运行 python get_token.py
"""
import socket, ssl, threading, os, sys, re, subprocess, time, traceback
from datetime import datetime, timedelta, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CA_DIR = os.path.join(SCRIPT_DIR, ".ca")
CA_KEY = os.path.join(CA_DIR, "ca.key")
CA_CERT = os.path.join(CA_DIR, "ca.crt")
TOKEN_FILE = os.path.join(SCRIPT_DIR, "token.txt")
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")
HOSTS = r"C:\Windows\System32\drivers\etc\hosts"
TARGET = "wamusic.wahlap.net"
PORT = 443

found = threading.Event()
token = ""
roleid = ""
real_ip = ""
_cert_cache = None
DEBUG_LOG = os.path.join(SCRIPT_DIR, "debug_capture.log")

def log_debug(msg):
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    with open(DEBUG_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")


def gen_ca():
    if os.path.exists(CA_KEY) and os.path.exists(CA_CERT):
        return
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    os.makedirs(CA_DIR, exist_ok=True)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "CN"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "JubeatScorecard"),
        x509.NameAttribute(NameOID.COMMON_NAME, "Jubeat CA"),
    ])
    builder = (
        x509.CertificateBuilder()
        .subject_name(name).issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
    )
    # Subject Key Identifier
    ski = x509.SubjectKeyIdentifier.from_public_key(key.public_key())
    builder = builder.add_extension(ski, critical=False)
    # Authority Key Identifier (自签名: AKI = SKI)
    builder = builder.add_extension(
        x509.AuthorityKeyIdentifier.from_issuer_public_key(key.public_key()),
        critical=False,
    )
    cert = builder.sign(key, hashes.SHA256())
    with open(CA_KEY, "wb") as f: f.write(key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    with open(CA_CERT, "wb") as f: f.write(cert.public_bytes(serialization.Encoding.PEM))
    print("[CA] 证书已生成")


def check_ca_installed():
    try:
        r = subprocess.run(["certutil", "-verifystore", "Root", "Jubeat CA"],
                           capture_output=True, text=True)
        return r.returncode == 0
    except:
        return False


def remove_old_ca():
    """删除信任库中所有旧的 Jubeat CA 证书"""
    try:
        r = subprocess.run(
            ["certutil", "-delstore", "Root", "Jubeat CA"],
            capture_output=True, text=True,
        )
        # 不管成功失败都继续，可能本来就没有
        print("[CA] 已清理旧证书")
    except Exception as e:
        print(f"[CA] 清理旧证书异常: {e}")


def install_ca():
    try:
        r = subprocess.run(["certutil", "-addstore", "Root", CA_CERT],
                           capture_output=True, text=True)
        ok = r.returncode == 0 or "already" in (r.stdout + r.stderr).lower()
        if ok:
            print("[CA] 已安装到受信任根证书颁发机构")
        else:
            print(f"[CA] 安装失败: {r.stdout} {r.stderr}")
        return ok
    except Exception as e:
        print(f"[CA] 安装异常: {e}")
        return False


def get_host_cert():
    global _cert_cache
    if _cert_cache:
        return _cert_cache
    from cryptography import x509
    from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    with open(CA_KEY, "rb") as f: ca_key = serialization.load_pem_private_key(f.read(), password=None)
    with open(CA_CERT, "rb") as f: ca_cert = x509.load_pem_x509_certificate(f.read())
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    # 从 CA 证书提取 SKI 用于 AKI
    ca_ski = ca_cert.extensions.get_extension_for_class(x509.SubjectKeyIdentifier).value
    cert = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, TARGET)]))
        .issuer_name(ca_cert.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc) - timedelta(days=1))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),
            critical=False,
        )
        .add_extension(x509.SubjectAlternativeName([x509.DNSName(TARGET)]), critical=False)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_subject_key_identifier(ca_ski),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256())
    )
    kp = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    cp = cert.public_bytes(serialization.Encoding.PEM)
    _cert_cache = (kp, cp)
    return _cert_cache


def hosts_op(action):
    marker = "# jubeat-scorecard"
    entry = f"127.0.0.1 {TARGET} {marker}\n"
    try:
        with open(HOSTS, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"[hosts] 读取失败: {e}")
        log_debug(f"hosts read error: {e}")
        return
    old = [l for l in lines if marker not in l]
    new = old + ([entry] if action == "add" else [])
    if new != lines:
        try:
            with open(HOSTS, "w", encoding="utf-8") as f:
                f.writelines(new)
            # 验证写入
            with open(HOSTS, "r", encoding="utf-8") as f:
                verify = f.read()
            ok = (marker in verify) if action == "add" else (marker not in verify)
            subprocess.run(["ipconfig", "/flushdns"], capture_output=True)
            status = "OK" if ok else "FAIL"
            print(f"[hosts] {'劫持' if action=='add' else '恢复'} {TARGET} 写入{status}")
            log_debug(f"hosts {action} {status}")
        except PermissionError:
            print("[hosts] 权限不足，请以管理员身份运行")
            log_debug("hosts write PermissionError")
        except Exception as e:
            print(f"[hosts] 写入失败: {e}")
            log_debug(f"hosts write error: {e}")
    else:
        print(f"[hosts] {TARGET} 已{'劫持' if action=='add' else '恢复'}，无需修改")
        log_debug(f"hosts {action} skipped (no change needed)")


def recv_http(sock):
    data = b""
    sock.settimeout(10)
    while b"\r\n\r\n" not in data:
        d = sock.recv(4096)
        if not d: break
        data += d
    m = re.search(rb"Content-Length:\s*(\d+)", data)
    need = int(m.group(1)) if m else 0
    hdr_end = data.find(b"\r\n\r\n") + 4
    while len(data) - hdr_end < need:
        d = sock.recv(min(4096, need - (len(data) - hdr_end)))
        if not d: break
        data += d
    return data


def handle(client_sock):
    global token, roleid
    tk = os.path.join(CA_DIR, "_t.key")
    tc = os.path.join(CA_DIR, "_t.crt")
    try:
        kp, cp = get_host_cert()
        with open(tk, "wb") as f: f.write(kp)
        with open(tc, "wb") as f: f.write(cp)

        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(tc, tk)
        client = ctx.wrap_socket(client_sock, server_side=True)

        req = recv_http(client)
        if not req:
            log_debug("[SKIP] 空请求")
            return

        # === DEBUG: 打印请求摘要 ===
        req_preview = req[:800].decode("utf-8", errors="replace")
        print(f"\n[>>>] 收到请求 ({len(req)} bytes)")
        log_debug(f"REQUEST ({len(req)} bytes):\n{req.decode('utf-8', errors='replace')}")

        srv = socket.create_connection((real_ip, 443))
        srv = ssl.create_default_context().wrap_socket(srv, server_hostname=TARGET)
        srv.sendall(req)
        resp = recv_http(srv)
        srv.close()

        if resp:
            client.sendall(resp)
            # === DEBUG: 打印响应摘要 ===
            print(f"[<<<] 收到响应 ({len(resp)} bytes)")
            log_debug(f"RESPONSE ({len(resp)} bytes):\n{resp.decode('utf-8', errors='replace')}")
        else:
            log_debug("[SKIP] 空响应")
        client.close()

        # === 尝试多种 token 匹配模式 ===
        token_patterns = [
            rb'"access_token"\s*:\s*"([^"]+)"',
            rb'"token"\s*:\s*"([^"]+)"',
            rb'"accessToken"\s*:\s*"([^"]+)"',
            rb'"auth_token"\s*:\s*"([^"]+)"',
            rb'"jwt"\s*:\s*"([^"]+)"',
        ]
        for pat in token_patterns:
            m = re.search(pat, resp)
            if m:
                token = m.group(1).decode()
                found.set()
                print(f"\n[TOKEN] 匹配模式: {pat[:40].decode('utf-8', errors='replace')}...")
                print(f"[TOKEN] 值: {token}")
                log_debug(f"TOKEN captured: {token}")
                break
        else:
            # 没匹配到，但响应里有类似 token 的字段
            if resp and b"token" in resp.lower():
                # 打印前后 100 字符帮助定位
                idx = resp.lower().find(b"token")
                ctx_ = resp[max(0,idx-60):idx+120]
                log_debug(f"TOKEN context (not matched): ...{ctx_.decode('utf-8', errors='replace')}...")

        # === 尝试从请求和响应中匹配 roleid ===
        roleid_patterns = [
            rb'"(?:roleid|roleId|role_id|roleID)"\s*:\s*"?(\d+)"?',
            rb'"(?:playerid|playerId|player_id)"\s*:\s*"?(\d+)"?',
        ]
        for src_name, src_data in [("REQUEST", req), ("RESPONSE", resp)]:
            for pat in roleid_patterns:
                m = re.search(pat, src_data)
                if m:
                    rid = m.group(1).decode()
                    if not roleid:
                        roleid = rid
                    print(f"[ROLEID] 从{src_name}捕获: {rid}")
                    log_debug(f"ROLEID from {src_name}: {rid}")
                    break
            if roleid:
                break

    except ssl.SSLError as e:
        log_debug(f"SSL ERROR: {e}\n{traceback.format_exc()}")
        print(f"[SSL ERROR] {e}")
    except Exception as e:
        log_debug(f"ERROR: {e}\n{traceback.format_exc()}")
        print(f"[ERROR] {e}")
    finally:
        try: client_sock.close()
        except: pass
        for f in [tk, tc]:
            try: os.remove(f)
            except: pass


def main():
    global real_ip, TOKEN_FILE, CONFIG_FILE, DEBUG_LOG, CA_DIR, CA_KEY, CA_CERT
    # 重新计算所有基于 SCRIPT_DIR 的路径 (main.py 可能已修改 SCRIPT_DIR)
    TOKEN_FILE = os.path.join(SCRIPT_DIR, "token.txt")
    CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")
    DEBUG_LOG = os.path.join(SCRIPT_DIR, "debug_capture.log")
    CA_DIR = os.path.join(SCRIPT_DIR, ".ca")
    CA_KEY = os.path.join(CA_DIR, "ca.key")
    CA_CERT = os.path.join(CA_DIR, "ca.crt")

    print("=" * 45)
    print("  音乐魔方 Token 获取")
    print("=" * 45)

    # 清空上次的调试日志
    with open(DEBUG_LOG, "w", encoding="utf-8") as f:
        f.write(f"=== {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 开始捕获 ===\n")
    print(f"[DEBUG] 调试日志: {DEBUG_LOG}")

    # 清理可能残留的旧证书（.ca/ 目录重建后旧证书已不匹配）
    remove_old_ca()

    gen_ca()
    if not check_ca_installed():
        print("\n  首次使用需安装CA证书...")
        if not install_ca():
            print(f"\n  请手动安装证书: 双击 {CA_CERT}")
            print("  → 本地计算机 → 受信任的根证书颁发机构")
            print("  安装完成后按回车继续...")
            input()

    try:
        real_ip = socket.getaddrinfo(TARGET, 443, socket.AF_INET, socket.SOCK_STREAM)[0][4][0]
    except Exception as e:
        print(f"[ERROR] DNS解析失败: {e}")
        return 1

    try:
        hosts_op("add")
    except PermissionError:
        print("[ERROR] 请以管理员身份运行")
        return 1

    print(f"\n  请打开微信 → 音游街 → 音乐魔方")
    print("  (已打开的话，先关闭再重新打开)")
    print("  等待捕获... Ctrl+C 退出\n")

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        srv.bind(("0.0.0.0", PORT))
    except OSError:
        print(f"[ERROR] 端口{PORT}被占用, 请关闭占用程序后重试")
        hosts_op("restore")
        return 1
    srv.listen(10)
    srv.settimeout(1)

    try:
        while not found.is_set():
            try:
                c, _ = srv.accept()
                threading.Thread(target=handle, args=(c,), daemon=True).start()
            except socket.timeout:
                continue
    except KeyboardInterrupt:
        pass
    finally:
        srv.close()
        hosts_op("restore")

    if token:
        with open(TOKEN_FILE, "w") as f: f.write(token)
        import json as _json
        config = {}
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f: config = _json.load(f)
        config["token"] = token
        if roleid:
            config["roleid"] = roleid
        with open(CONFIG_FILE, "w") as f: _json.dump(config, f, indent=2)
        print(f"\n[完成] token → {TOKEN_FILE}")
        if roleid:
            print(f"       roleid → {roleid}")
        log_debug(f"FINAL token={token} roleid={roleid}")
        return 0
    else:
        print(f"\n[失败] 未捕获到token")
        print(f"[DEBUG] 查看原始数据: {DEBUG_LOG}")
        # 尝试从日志里搜索任何可疑字段
        if os.path.exists(DEBUG_LOG):
            with open(DEBUG_LOG, "r", encoding="utf-8") as f:
                content = f.read()
            for kw in ["token", "auth", "jwt", "sign", "key", "secret", "roleid", "player"]:
                if kw in content.lower():
                    idx = content.lower().find(kw)
                    print(f"[DEBUG] 发现关键字 '{kw}' 在日志偏移 {idx} 附近")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        hosts_op("restore")
