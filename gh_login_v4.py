# -*- coding: utf-8 -*-
"""GitHub登录v4：点Sign in→轮询结果（表单已填好）"""
import json
import time
import urllib.request

import websocket

CDP = "http://127.0.0.1:9222"
tabs = json.loads(urllib.request.urlopen(CDP + "/json/list", timeout=10).read())
gh = [t for t in tabs if "github.com" in (t.get("url") or "")]
t = gh[0]
ws = websocket.create_connection(t["webSocketDebuggerUrl"], timeout=25)
mid = [0]


def send(method, params=None):
    mid[0] += 1
    ws.send(json.dumps({"id": mid[0], "method": method, "params": params or {}}))
    while True:
        r = json.loads(ws.recv())
        if r.get("id") == mid[0]:
            return r


def ev(expr):
    r = send("Runtime.evaluate", {"expression": expr, "returnByValue": True})
    return r.get("result", {}).get("result", {}).get("value")


def click(x, y):
    for type_, btn in [("mousePressed", "left"), ("mouseReleased", "left")]:
        send("Input.dispatchMouseEvent", {
            "type": type_, "x": x, "y": y, "button": btn,
            "clickCount": 1, "pointerType": "mouse",
        })


send("Runtime.enable")
send("Page.enable")

# 确认表单还是填好的
u = ev("(document.querySelector('#login_field')||{}).value || ''")
p = ev("(document.querySelector('#password')||{}).value || ''")
print(f"pre-check: user_len={len(u)} pwd_len={len(p)}")
if not (u and p):
    # 再走一遍唤起流程
    click(507, 320)
    time.sleep(2.5)
    u = ev("(document.querySelector('#login_field')||{}).value || ''")
    p = ev("(document.querySelector('#password')||{}).value || ''")
    print(f"re-poke: user_len={len(u)} pwd_len={len(p)}")

# 点Sign in按钮 (y≈456)
click(507, 456)
print("clicked sign-in, polling...")

result = {}
for i in range(25):
    time.sleep(2)
    url = ev("location.href") or ""
    login = ev("(document.querySelector('meta[name=\"user-login\"]')||{}).content || null")
    otp = "/2fa" in url or bool(ev("document.querySelector('input[name=\"otp\"]')"))
    err = (ev("(document.querySelector('#js-flash-container')||{}).innerText || ''") or "").strip()
    if i % 2 == 0:
        print(f"[{i}] url={url[:75]} login={login} otp={otp} err={err[:60]!r}")
    if login and login != "null":
        result = {"ok": True, "login": login, "url": url}
        break
    if otp:
        result = {"ok": False, "needs_2fa": True, "url": url}
        break
    if "Incorrect" in err or "incorrect" in err.lower():
        result = {"ok": False, "error": err[:200], "url": url}
        break

if not result:
    result = {"ok": False, "url": ev("location.href"), "note": "timeout 50s no state change"}

print(json.dumps(result, ensure_ascii=False))
with open(r"C:\Users\QAXD\com_test\douhot_mcp\.gh_state.json", "w") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
ws.close()
