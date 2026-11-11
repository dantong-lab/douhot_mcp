# -*- coding: utf-8 -*-
"""GitHub登录v3：真实鼠标点击输入框触发Edge自动填充"""
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
    for type_, btn, cnt in [("mousePressed", "left", 1), ("mouseReleased", "left", 1)]:
        send("Input.dispatchMouseEvent", {
            "type": type_, "x": x, "y": y, "button": btn,
            "clickCount": cnt, "pointerType": "mouse",
        })


send("Runtime.enable")
send("Page.enable")

# 当前URL确认（应在login?return_to=...）
print("url:", ev("location.href")[:80])

# 坐标从首截图：username(507,320) password(507,400) signin(507,456)
# 页面若被复用布局一致。先视口尺寸确认
vw = ev("window.innerWidth"), ev("window.innerHeight")
print("viewport:", vw)

# 1. 真点用户名框
click(507, 320)
time.sleep(2.5)
u = ev("(document.querySelector('#login_field')||{}).value || ''")
print("after click username:", "filled" if u else "empty")

# 2. 若还没填，真点密码框
if not u:
    click(507, 400)
    time.sleep(2.5)
    u = ev("(document.querySelector('#login_field')||{}).value || ''")
    p = ev("(document.querySelector('#password')||{}).value || ''")
    print(f"after click password: user={'filled' if u else 'empty'} pwd={'filled' if p else 'empty'}")

# 3. 再等一拍读最终状态
time.sleep(2)
u = ev("(document.querySelector('#login_field')||{}).value || ''")
p = ev("(document.querySelector('#password')||{}).value || ''")
print(f"final: user_len={len(u)} pwd_len={len(p)}")
print(json.dumps({"filled": bool(u and p)}, ensure_ascii=False))
ws.close()
