#!/usr/bin/env python3
"""Proxy TLS local: escuta 127.0.0.1:8443 (HTTPS) e encaminha para http://vaultwarden:80.
Necessário porque o bw CLI 2026 exige HTTPS e o domínio público não resolve no container."""
import socket, ssl, threading, sys

LISTEN = ("127.0.0.1", 8443)
TARGET = ("vaultwarden", 80)
CERT = "/home/node/.openclaw/workspace/.bwproxy/cert.pem"
KEY = "/home/node/.openclaw/workspace/.bwproxy/key.pem"

ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ctx.load_cert_chain(CERT, KEY)

def pipe(src, dst):
    try:
        while True:
            data = src.recv(65536)
            if not data:
                break
            dst.sendall(data)
    except Exception:
        pass
    finally:
        try: dst.shutdown(socket.SHUT_WR)
        except Exception: pass

def handle(conn):
    try:
        up = socket.create_connection(TARGET, timeout=10)
        threading.Thread(target=pipe, args=(conn, up), daemon=True).start()
        pipe(up, conn)
    except Exception as e:
        sys.stderr.write(f"proxy error: {e}\n")
    finally:
        try: conn.close()
        except Exception: pass

srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind(LISTEN)
srv.listen(16)
sys.stderr.write(f"proxy TLS ouvindo em https://{LISTEN[0]}:{LISTEN[1]} -> http://{TARGET[0]}:{TARGET[1]}\n")
sys.stderr.flush()
while True:
    c, _ = srv.accept()
    try:
        tls = ctx.wrap_socket(c, server_side=True)
    except Exception:
        try: c.close()
        except Exception: pass
        continue
    threading.Thread(target=handle, args=(tls,), daemon=True).start()
