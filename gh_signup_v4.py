# -*- coding: utf-8 -*-
"""GitHub注册v4：确认form值后直接原生submit"""
import json
import time
import urllib.request

import websocket

CDP = "http://127.0.0.1:9222"

tabs = [t for t in json.loads(urllib.request.urlopen(CDP + "/json/list", timeout=10).read()) if t.get("type") == "page"]
t = [x for x in tabs if "github.com/signup" in (x.get("url") or "")][0]
ws = websocket.create_connection(t["webSocketDebuggerUrl"], timeout=35)
mid = [0]


def send(m, p=None):
    mid[0] += 1
    ws.send(json.dumps({"id": mid[0], "method": m, "params": p or {}}))
    while True:
        r = json.loads(ws.recv())
        if r.get("id") == mid[0]:
            return r


def ev(e):
    r = send("Runtime.evaluate", {"expression": e, "returnByValue": True})
    return r.get("result", {}).get("result", {}).get("value")


send("Runtime.enable")
send("Page.enable")

cur = ev("""JSON.stringify({
 e:(document.querySelector('#email')||{value:'?'}).value,
 p:(document.querySelector('#password')||{value:''}).value.length,
 u:(document.querySelector('#login')||{value:'?'}).value,
 c:(document.querySelector('[name=\"user_signup[country]\"]')||{value:'?'}).value
})""")
print("当前form值:", cur)

# 若email不是outlook的先改
if "outlook_860EE" not in str(cur):
    ev("""(function(){var s=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;
    var el=document.querySelector('#email');s.call(el,'outlook_860EE7291470254D@outlook.com');
    el.dispatchEvent(new Event('input',{bubbles:true}));return 'ok'})()""")
    time.sleep(0.5)

r = ev("""(function(){var f=[...document.querySelectorAll('form')].find(function(f){return f.method.toLowerCase()==='post'&&f.action.indexOf('/signup')>-1});f.submit();return 'posted'})()""")
print("submit:", r)

for i in range(18):
    time.sleep(2)
    try:
        url = ev("location.href") or ""
        body = ev("document.body.innerText") or ""
    except Exception:
        url, body = "(nav)", ""
    low = body.lower()
    if "verify" in low and ("launch" in low or "email" in low):
        print(f">>> VERIFY阶段 len={len(body)}:", repr(body[:250]))
        break
    if "could not be verified" in low:
        errs = [l for l in body.split("\n") if "verif" in l.lower()]
        print(">>> 拒绝:", errs[:1])
        break
    if "captcha" in low or "puzzle" in low:
        print(">>> CAPTCHA:", repr(body[:200]))
        break
    if i % 3 == 0:
        print(f"[{i}] {str(url)[:65]} len={len(body)}")

ws.close()
