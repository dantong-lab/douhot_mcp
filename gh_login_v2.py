# -*- coding: utf-8 -*-
"""GitHub登录v2：刷新登录页→等自动填充→点Sign in→轮询结果"""
import json
import time
import urllib.request

import websocket

CDP = "http://127.0.0.1:9222"
tabs = json.loads(urllib.request.urlopen(CDP + "/json/list", timeout=10).read())
gh = [t for t in tabs if "github.com" in (t.get("url") or "")]
t = gh[0]
ws = websocket.create_connection(t["webSocketDebuggerUrl"], timeout=20)
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


send("Runtime.enable")
send("Page.enable")

# 1. 强制刷新登录页（带return_to直达）
ev('location.href="https://github.com/login?return_to=https%3A%2F%2Fgithub.com%2Fsettings%2Fprofile"')
filled = False
for i in range(15):
    time.sleep(1.5)
    if ev("document.readyState") == "complete":
        u = ev("(document.querySelector('#login_field')||{}).value || ''")
        p = ev("(document.querySelector('#password')||{}).value || ''")
        if u and p:
            filled = True
            print(f"autofill ready (t={i}): user_len={len(u)} pwd_len={len(p)}")
            break
        if i == 5:
            # 自动填充没来，点一下用户名框触发
            ev("document.querySelector('#login_field').focus()")
            print("poked username field at t=5")
if not filled:
    u = ev("(document.querySelector('#login_field')||{}).value || ''")
    p = ev("(document.querySelector('#password')||{}).value || ''")
    print(f"autofill status: user_len={len(u)} pwd_len={len(p)}")

# 2. 点击Sign in
r = ev("""
(() => {
  const btn = document.querySelector('input[type="submit"][name="commit"]');
  if (btn) { btn.click(); return 'CLICKED'; }
  return 'NOT_FOUND';
})()
""")
print("submit:", r)

# 3. 轮询结果
final = {}
for i in range(25):
    time.sleep(1.5)
    url = ev("location.href")
    login = ev("(document.querySelector('meta[name=\"user-login\"]')||{}).content || null")
    err = ev("(document.querySelector('#js-flash-container')||{}).innerText || ''")
    otp = ev("location.href.includes('/2fa')")
    if i % 2 == 0:
        print(f"[{i}] url={url[:75]} login={login} otp={otp} err={(err or '').strip()[:60]!r}")
    if login and login != "null":
        break
    if otp:
        break

final = {
    "url": ev("location.href"),
    "login": ev("(document.querySelector('meta[name=\"user-login\"]')||{}).content || null"),
    "needs_2fa": ev("location.href.includes('/2fa')"),
    "flash": (ev("(document.querySelector('#js-flash-container')||{}).innerText || ''") or "").strip()[:200],
}
print(json.dumps(final, ensure_ascii=False))
with open(r"C:\Users\QAXD\com_test\douhot_mcp\.gh_state.json", "w") as f:
    json.dump(final, f, ensure_ascii=False, indent=2)
ws.close()
