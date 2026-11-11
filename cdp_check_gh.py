# -*- coding: utf-8 -*-
"""CDP驱动：开GitHub标签页，探测登录态"""
import json
import time
import urllib.request

import websocket  # websocket-client

CDP = "http://127.0.0.1:9222"


def http_json(method, path):
    req = urllib.request.Request(CDP + path, method=method)
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())


# 1. 开新tab到github.com
tab = http_json("PUT", "/json/new?https://github.com")
ws_url = tab["webSocketDebuggerUrl"]
target_id = tab["id"]
print("tab opened:", tab["url"])

ws = websocket.create_connection(ws_url, timeout=15)
msg_id = 0


def send(method, params=None):
    global msg_id
    msg_id += 1
    ws.send(json.dumps({"id": msg_id, "method": method, "params": params or {}}))
    while True:
        m = json.loads(ws.recv())
        if m.get("id") == msg_id:
            return m.get("result", {})


def eval_js(expr):
    r = send("Runtime.evaluate", {"expression": expr, "returnByValue": True})
    return r.get("result", {}).get("value")


send("Runtime.enable")
send("Page.enable")

# 2. 等加载完，轮询登录态
login = None
for i in range(20):
    time.sleep(1.5)
    state = eval_js("document.readyState")
    if state == "complete":
        login = eval_js(
            "(document.querySelector('meta[name=\"user-login\"]')||{}).content || null"
        )
        avatar = eval_js("!!document.querySelector('img.avatar')")
        title = eval_js("document.title")
        if login or avatar or i >= 6:
            print("readyState:", state, "| title:", title)
            print("user-login meta:", login, "| avatar:", avatar)
            break

# 3. 探测结果落盘给下一步用
state = {
    "target_id": target_id,
    "ws_url": ws_url,
    "logged_in": bool(login and login != "null"),
    "login_name": login,
}
with open(r"C:\Users\QAXD\com_test\douhot_mcp\.gh_state.json", "w") as f:
    json.dump(state, f, ensure_ascii=False, indent=2)
print(json.dumps(state, ensure_ascii=False))
ws.close()
