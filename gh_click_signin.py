# -*- coding: utf-8 -*-
"""GitHub登录页：CDP点击Sign in，轮询登录结果"""
import json
import time
import urllib.request

import websocket

CDP = "http://127.0.0.1:9222"
tabs = json.loads(urllib.request.urlopen(CDP + "/json/list", timeout=10).read())
gh = [t for t in tabs if "github.com" in (t.get("url") or "")]
t = gh[0]
print("tab:", t["url"])
ws = websocket.create_connection(t["webSocketDebuggerUrl"], timeout=20)
mid = [0]


def send(method, params=None):
    mid[0] += 1
    ws.send(json.dumps({"id": mid[0], "method": method, "params": params or {}}))
    while True:
        r = json.loads(ws.recv())
        if r.get("id") == mid[0]:
            return r


def eval_js(expr):
    r = send("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": True})
    res = r.get("result", {}).get("result", {})
    return res.get("value")


send("Runtime.enable")
send("Page.enable")

# 找Sign in按钮并点击
found = eval_js("""
(() => {
  const btn = document.querySelector('input[type="submit"][name="commit"]') ||
              document.querySelector('button[type="submit"]');
  if (btn) { btn.click(); return btn.tagName + '|' + (btn.value || btn.textContent); }
  return 'NOT_FOUND';
})()
""")
print("click:", found)

# 轮询结果（最多30s）：URL变化 + user-login meta
result = None
for i in range(20):
    time.sleep(1.5)
    url = eval_js("location.href")
    login = eval_js("(document.querySelector('meta[name=\"user-login\"]')||{}).content || null")
    flash = eval_js("(document.querySelector('.flash-error, .flash-warn')||{}).textContent || null")
    if i % 3 == 0 or login:
        print(f"[{i}] url={url[:70]} login={login} flash={(flash or '')[:80]}")
    if login and login != "null":
        result = login
        break
    if url and "/session" not in url and "/login" not in url and "github.com" in url:
        # 跳离登录页（可能2FA或直接登录成功）
        if i >= 5:
            pass  # 继续观察

url = eval_js("location.href")
login = eval_js("(document.querySelector('meta[name=\"user-login\"]')||{}).content || null")
err = eval_js("(document.querySelector('#js-flash-container, .flash-error')||{}).textContent || ''")
twofa = eval_js("location.href.includes('/2fa') || !!document.querySelector('input[name=\"otp\"]')")
out = {"final_url": url, "login": login, "error": (err or "").strip()[:200], "needs_2fa": twofa}
print(json.dumps(out, ensure_ascii=False))
with open(r"C:\Users\QAXD\com_test\douhot_mcp\.gh_state.json", "w") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
ws.close()
