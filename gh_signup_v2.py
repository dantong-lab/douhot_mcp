# -*- coding: utf-8 -*-
"""GitHub注册v2：补密码+选国家+提交"""
import json
import time
import urllib.request

import websocket

CDP = "http://127.0.0.1:9222"
acct = json.load(open(r"C:\Users\QAXD\com_test\douhot_mcp\.gh_new_account.json"))
PASSWORD = acct["password"]

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


def click(x, y):
    send("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": x, "y": y, "pointerType": "mouse"})
    time.sleep(0.15)
    for tp in ("mousePressed", "mouseReleased"):
        send("Input.dispatchMouseEvent", {"type": tp, "x": x, "y": y, "button": "left", "clickCount": 1, "pointerType": "mouse"})


send("Page.enable")
send("Runtime.enable")

# 1. 补密码（真点击+insertText）
c = json.loads(ev('''(()=>{const el=document.querySelector("#password");const r=el.getBoundingClientRect();return JSON.stringify([r.x+r.width/2,r.y+r.height/2])})()'''))
click(c[0], c[1])
time.sleep(0.3)
send("Input.insertText", {"text": PASSWORD})
time.sleep(0.8)
print("password len:", ev('document.querySelector("#password").value.length'))

# 2. 国家下拉：先看是不是原生select
is_native = ev('!!document.querySelector("select")')
print("native select:", is_native)
if is_native:
    ev('''(()=>{const s=document.querySelector("select");const opt=[...s.options].find(o=>o.text.includes("United States"));if(opt){s.value=opt.value;s.dispatchEvent(new Event("change",{bubbles:true}));}})()''')
else:
    # 自定义下拉：点击展开
    c = json.loads(ev('''(()=>{const el=document.querySelector("#country-dropdown-pan,[class*=country]");if(!el)return null;const r=el.getBoundingClientRect();return JSON.stringify([r.x+r.width/2,r.y+r.height/2])})()'''))
    print("country dropdown pos:", c)
    if c:
        click(c[0], c[1])
        time.sleep(1.5)
        # 找列表项 United States
        item = ev('''(()=>{const els=[...document.querySelectorAll("[role=option],li,[class*=item]")];const t=els.find(e=>(e.innerText||"").trim().startsWith("United States"));if(!t)return null;const r=t.getBoundingClientRect();return JSON.stringify([r.x+r.width/2,r.y+r.height/2])})()''')
        print("US item pos:", item)
        if item:
            ix, iy = json.loads(item)
            click(ix, iy)
            time.sleep(1)

print("country now:", ev('(document.querySelector("#country-dropdown-pan,[class*=country]")||{innerText:"?"}).innerText.slice(0,40)'))

# 3. 提交
r = ev('''(()=>{const f=[...document.querySelectorAll("form")].find(f=>f.method.toLowerCase()==="post"&&f.action.includes("/signup"));if(!f)return "no_form";f.submit();return "submitted"})()''')
print("submit:", r)

for i in range(15):
    time.sleep(2)
    try:
        url = ev("location.href") or ""
        body = ev("document.body.innerText") or ""
    except Exception:
        url, body = "(nav)", ""
    bl = len(body)
    low = body.lower()
    marker = ""
    if "verify your email" in low or "check your inbox" in low:
        marker = "EMAIL_VERIFY_STAGE"
    elif "captcha" in low or "puzzle" in low:
        marker = "CAPTCHA_STAGE"
    elif "can't be blank" in low or "could not be verified" in low:
        marker = "REJECTED: " + next((l for l in body.split("\n") if "blank" in l.lower() or "verif" in l.lower()), "?")[:80]
    if marker:
        print(f"[{i}] {marker}")
        if marker.startswith(("EMAIL", "CAPTCHA")):
            break
    elif i % 3 == 0:
        print(f"[{i}] url={str(url)[:55]} len={bl}")

ws.close()
