# -*- coding: utf-8 -*-
"""GitHub登录v5：getBoundingClientRect精确定位 + 真鼠标点击"""
import json
import time
import urllib.request

import websocket

CDP = "http://127.0.0.1:9222"
tabs = json.loads(urllib.request.urlopen(CDP + "/json/list", timeout=10).read())
gh = [t for t in tabs if ("github.com" in (t.get("url") or "")) or ("accounts.google" in (t.get("url") or ""))]
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
    send("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": x, "y": y, "pointerType": "mouse"})
    time.sleep(0.15)
    for type_ in ("mousePressed", "mouseReleased"):
        send("Input.dispatchMouseEvent", {
            "type": type_, "x": x, "y": y, "button": "left",
            "clickCount": 1, "pointerType": "mouse",
        })


def rect_center(sel):
    v = ev(f"""
    (() => {{
      const el = document.querySelector('{sel}');
      if (!el) return null;
      const r = el.getBoundingClientRect();
      return JSON.stringify([r.x + r.width/2, r.y + r.height/2]);
    }})()
    """)
    return json.loads(v) if v else None


send("Runtime.enable")
send("Page.enable")

# 1. 回登录页
ev('location.href="https://github.com/login"')
ok = False
for i in range(12):
    time.sleep(1.5)
    if ev("document.readyState") == "complete" and ev("!!document.querySelector('#login_field')"):
        ok = True
        break
print("login page ready:", ok, "| url:", ev("location.href")[:70])

# 2. 用DOM坐标真点用户名框 → 触发自动填充
c = rect_center("#login_field")
print("username rect center:", c)
if c:
    click(c[0], c[1])
    time.sleep(2.5)

u = ev("(document.querySelector('#login_field')||{}).value || ''")
p = ev("(document.querySelector('#password')||{}).value || ''")
print(f"after username click: user_len={len(u)} pwd_len={len(p)}")

# 3. 还没填就点密码框
if not (u and p):
    c = rect_center("#password")
    if c:
        click(c[0], c[1])
        time.sleep(2.5)
    u = ev("(document.querySelector('#login_field')||{}).value || ''")
    p = ev("(document.querySelector('#password')||{}).value || ''")
    print(f"after password click: user_len={len(u)} pwd_len={len(p)}")

# 4. 都填好了→点Sign in（同样DOM坐标）
if u and p:
    c = rect_center("input[type='submit'][name='commit']")
    print("signin rect center:", c)
    if c:
        click(c[0], c[1])
    print("submitted, polling...")
    result = {}
    for i in range(25):
        time.sleep(2)
        url = ev("location.href") or ""
        login = ev("(document.querySelector('meta[name=\"user-login\"]')||{}).content || null")
        otp = "/2fa" in url
        err = (ev("(document.querySelector('#js-flash-container')||{}).innerText || ''") or "").strip()
        if i % 2 == 0:
            print(f"[{i}] url={url[:70]} login={login} err={err[:60]!r}")
        if login and login != "null":
            result = {"ok": True, "login": login, "url": url}
            break
        if otp:
            result = {"ok": False, "needs_2fa": True, "url": url}
            break
        if err and ("incorrect" in err.lower()):
            result = {"ok": False, "error": err[:200], "url": url}
            break
    if not result:
        result = {"ok": False, "url": ev("location.href"), "note": "no state change 50s"}
else:
    result = {"ok": False, "error": "autofill never came"}

print(json.dumps(result, ensure_ascii=False))
with open(r"C:\Users\QAXD\com_test\douhot_mcp\.gh_state.json", "w") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
ws.close()
