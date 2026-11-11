# -*- coding: utf-8 -*-
"""GitHub注册v1：填邮箱/密码/用户名→Create account→处理后续（可能CAPTCHA）"""
import json
import secrets
import time
import urllib.request

import websocket

CDP = "http://127.0.0.1:9222"
EMAIL = "outlook_860EE7291470254D@outlook.com"
USERNAME = "dantong-lab"
PASSWORD = "Md" + secrets.token_urlsafe(15) + "7k"

# 先存凭据到本地（安全：只存本地，不上传）
with open(r"C:\Users\QAXD\com_test\douhot_mcp\.gh_new_account.json", "w") as f:
    json.dump({"email": EMAIL, "username": USERNAME, "password": PASSWORD,
               "created": time.strftime("%Y-%m-%d %H:%M")}, f, indent=2)
print("credentials saved locally")

tabs = [t for t in json.loads(urllib.request.urlopen(CDP + "/json/list", timeout=10).read()) if t.get("type") == "page"]
t = [x for x in tabs if "github.com/signup" in (x.get("url") or "")][0]
ws = websocket.create_connection(t["webSocketDebuggerUrl"], timeout=30)
mid = [0]


def send(m, p=None):
    mid[0] += 1
    ws.send(json.dumps({"id": mid[0], "method": m, "params": p or {}}))
    while True:
        x = json.loads(ws.recv())
        if x.get("id") == mid[0]:
            return x


def ev(e):
    x = send("Runtime.evaluate", {"expression": e, "returnByValue": True})
    return x.get("result", {}).get("result", {}).get("value")


def rect_center(sel):
    v = ev(f'''(()=>{{const el=document.querySelector('{sel}');if(!el)return null;const r=el.getBoundingClientRect();return JSON.stringify([r.x+r.width/2,r.y+r.height/2])}})()''')
    return json.loads(v) if v else None


def real_type(sel, text):
    """点击输入框+逐键真实输入（触发GitHub前端校验）"""
    c = rect_center(sel)
    if not c:
        return False
    send("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": c[0], "y": c[1], "pointerType": "mouse"})
    time.sleep(0.12)
    for tp in ("mousePressed", "mouseReleased"):
        send("Input.dispatchMouseEvent", {"type": tp, "x": c[0], "y": c[1], "button": "left", "clickCount": 1, "pointerType": "mouse"})
    time.sleep(0.3)
    send("Input.insertText", {"text": text})
    time.sleep(0.5)
    return True


send("Page.enable")
send("Runtime.enable")

r1 = real_type("#email", EMAIL)
r2 = real_type("#password", PASSWORD)
r3 = real_type("#login", USERNAME)
print(f"filled: email={r1} pwd={r2} login={r3}")
time.sleep(1)

# 校验值+前端校验提示
vals = ev('''JSON.stringify({email:document.querySelector("#email").value.length,pwd:document.querySelector("#password").value.length,login:document.querySelector("#login").value})''')
print("values:", vals)
errs = ev('''JSON.stringify([...document.querySelectorAll("[class*=error],[role=alert]")].filter(e=>e.offsetWidth>0).map(e=>e.innerText.slice(0,60)))''')
print("inline errors:", errs)

# 点Create account
c = ev('''(()=>{const b=[...document.querySelectorAll("button")].find(e=>(e.innerText||"").includes("Create account"));if(!b)return null;const r=b.getBoundingClientRect();return JSON.stringify([r.x+r.width/2,r.y+r.height/2])})()''')
print("create btn:", c)
if c:
    cx, cy = json.loads(c)
    send("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": cx, "y": cy, "pointerType": "mouse"})
    time.sleep(0.15)
    for tp in ("mousePressed", "mouseReleased"):
        send("Input.dispatchMouseEvent", {"type": tp, "x": cx, "y": cy, "button": "left", "clickCount": 1, "pointerType": "mouse"})
    print("clicked create account, polling...")
    state = {}
    for i in range(15):
        time.sleep(2)
        try:
            url = ev("location.href") or ""
        except Exception:
            url = "(nav)"
        body_len = ev('(document.body.innerText||"").length') or 0
        body = (ev("document.body.innerText") or "")
        print(f"[{i}] url={str(url)[:60]} len={body_len}")
        low = body.lower()
        if "verify your email" in low or "check your email" in low:
            state = {"stage": "email_verification", "url": url}
            break
        if "captcha" in low or "puzzle" in low or "验证" in body:
            state = {"stage": "captcha", "url": url, "body_snip": body[:200]}
            break
        if "create your free account" in low and body_len > 100 and i > 3:
            state = {"stage": "still_form", "url": url, "errs": errs}
            break
    print("STAGE:", json.dumps(state, ensure_ascii=False)[:400])

ws.close()
