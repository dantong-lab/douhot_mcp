# -*- coding: utf-8 -*-
"""GitHub注册v3：美国IP + Outlook邮箱 + 完整填表(真键盘事件) + 提交"""
import json
import time
import urllib.request

import websocket

CDP = "http://127.0.0.1:9222"
OUTLOOK_EMAIL = "outlook_860EE7291470254D@outlook.com"

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


def real_click(x, y):
    send("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": x, "y": y, "pointerType": "mouse"})
    time.sleep(0.15)
    for tp in ("mousePressed", "mouseReleased"):
        send("Input.dispatchMouseEvent", {"type": tp, "x": x, "y": y, "button": "left", "clickCount": 1, "pointerType": "mouse"})


def real_type(sel, text):
    c = rect_center(sel)
    if not c:
        return False
    real_click(c[0], c[1])
    time.sleep(0.3)
    send("Input.insertText", {"text": text})
    time.sleep(0.6)
    return True


send("Page.enable")
send("Runtime.enable")

# 填三字段
r1 = real_type("#email", OUTLOOK_EMAIL)
r2 = real_type("#password", "MdKFEeyzXD8ihLngQrwdYW7k")
r3 = real_type("#login", "dantong-lab")
print("filled:", r1, r2, r3)
time.sleep(1)
print("values:", ev('JSON.stringify({e:document.querySelector("#email").value,p:document.querySelector("#password").value.length,u:document.querySelector("#login").value})'))

# 国家下拉（自定义）：点开再点United States
try:
    c = rect_center("#country-dropdown-pan") or rect_center("#country-dropdown")
except Exception:
    c = None
# 找含Country的按钮
if not c:
    v = ev('''(()=>{const b=[...document.querySelectorAll("button")].find(e=>(e.innerText||"").includes("Country")||(e.innerText||"").includes("United States"));if(!b)return null;const r=b.getBoundingClientRect();return JSON.stringify([r.x+r.width/2,r.y+r.height/2])})()''')
    c = json.loads(v) if v else None
print("country dropdown:", c)
if c:
    real_click(c[0], c[1])
    time.sleep(1.5)
    # 列表项（在视口内的）
    item = ev('''(()=>{const els=[...document.querySelectorAll("[role=option],li,div")];const t=els.filter(e=>(e.innerText||"").trim()==="United States of America"&&e.offsetWidth>0&&e.offsetHeight>10&&e.offsetHeight<80);if(!t.length)return null;const r=t[t.length-1].getBoundingClientRect();return JSON.stringify([r.x+r.width/2,r.y+r.height/2])})()''')
    print("US item:", item)
    if item:
        ix, iy = json.loads(item)
        real_click(ix, iy)
        time.sleep(1)
        print("country now:", ev('''(document.querySelector("#country-dropdown-pan")||{innerText:"?"}).innerText.slice(0,50)'''))

# 勾选marketing可选，跳过
# 提交：等按钮enabled
for attempt in range(6):
    st = ev('''(()=>{const b=[...document.querySelectorAll("button")].find(e=>(e.innerText||"").includes("Create account"));return JSON.stringify({d:b.disabled})})()''')
    d = json.loads(st).get("d", True)
    print(f"btn disabled={d} (attempt {attempt})")
    if not d:
        break
    time.sleep(1.5)

# 点击提交
c = ev('''(()=>{const b=[...document.querySelectorAll("button")].find(e=>(e.innerText||"").includes("Create account"));const r=b.getBoundingClientRect();return JSON.stringify([r.x+r.width/2,r.y+r.height/2])})()''')
cx, cy = json.loads(c)
real_click(cx, cy)
print("clicked create account")

# 轮询结果
for i in range(18):
    time.sleep(2)
    try:
        url = ev("location.href") or ""
        body = ev("document.body.innerText") or ""
    except Exception:
        url, body = "(nav)", ""
    low = body.lower()
    if "verify" in low and ("email" in low or "launch" in low):
        print(f"[{i}] EMAIL VERIFY STAGE:", repr(body[:200]))
        break
    if "could not be verified" in low or "invalid" in low:
        errs = [l for l in body.split("\n") if "verif" in l.lower() or "invalid" in l.lower()]
        print(f"[{i}] REJECTED:", errs[:2])
        break
    if "captcha" in low or "puzzle" in low:
        print(f"[{i}] CAPTCHA:", repr(body[:200]))
        break
    if i % 3 == 0:
        print(f"[{i}] url={str(url)[:60]} len={len(body)}")

ws.close()
