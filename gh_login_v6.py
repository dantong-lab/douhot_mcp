# -*- coding: utf-8 -*-
"""GitHub登录v6：账号已创建(dantong-lab)，填用户名密码登录"""
import json
import time
import urllib.request

import websocket

CDP = "http://127.0.0.1:9222"
CREDS = json.load(open(r"C:/Users/QAXD/com_test/douhot_mcp/.gh_new_account.json"))
USER = CREDS["username"]
PASS = CREDS["password"]

tabs = [t for t in json.loads(urllib.request.urlopen(CDP + "/json/list", timeout=10).read()) if t.get("type") == "page"]
t = [x for x in tabs if "github.com/login" in (x.get("url") or "") or "account_verifications" in (x.get("url") or "")][0]
ws = websocket.create_connection(t["webSocketDebuggerUrl"], timeout=90)
mid = [0]


def sd(m, p=None):
    mid[0] += 1
    ws.send(json.dumps({"id": mid[0], "method": m, "params": p or {}}))
    while True:
        r = json.loads(ws.recv())
        if r.get("id") == mid[0]:
            return r


def ev(e, ap=False):
    r = sd("Runtime.evaluate", {"expression": e, "returnByValue": True, "awaitPromise": ap})
    if "exceptionDetails" in r:
        return "EXC:" + json.dumps(r["exceptionDetails"])[:250]
    v = r.get("result", {}).get("result", {})
    return v.get("value") if v.get("type") != "undefined" else None


sd("Page.enable")
# 确保在登录页
if "github.com/login" not in str(ev("location.href")):
    sd("Page.navigate", {"url": "https://github.com/login?new_signup=true"})
    time.sleep(6)

# 填用户名密码（React-safe setter）
r = ev(
    """(function(){
  var u=document.querySelector('#login_field');
  var p=document.querySelector('#password');
  var set=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;
  set.call(u,'%s'); u.dispatchEvent(new Event('input',{bubbles:true}));
  set.call(p,'%s'); p.dispatchEvent(new Event('input',{bubbles:true}));
  return 'u:'+u.value.length+'p:'+p.value.length;
})()"""
    % (USER, PASS)
)
print("fill:", r)
time.sleep(1)
# 点Sign in按钮
print("click:", ev(
    """(function(){
  var b=[...document.querySelectorAll('input[type=submit],button')].find(x=>/sign in/i.test(x.value||x.innerText||''));
  if(!b) return 'no-btn';
  b.click();
  return 'ok';
})()"""
))
time.sleep(8)
url = ev("location.href")
print("url:", url)
print("title:", ev("document.title"))
body = str(ev("document.body.innerText.slice(0,300)"))
print("body:", body)
ws.close()
