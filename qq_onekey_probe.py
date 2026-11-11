# -*- coding: utf-8 -*-
"""QQ快速登录探测：localhost.ptlogin2.qq.com:4300端口+pt.plogin API"""
import json
import time
import urllib.request

import websocket

CDP = "http://127.0.0.1:9222"

tabs = [t for t in json.loads(urllib.request.urlopen(CDP + "/json/list", timeout=10).read()) if t.get("type") == "page"]
t = [x for x in tabs if "wx.mail.qq.com" in (x.get("url") or "")][0]
ws = websocket.create_connection(t["webSocketDebuggerUrl"], timeout=35)
mid = [0]


def send(m, p=None):
    mid[0] += 1
    ws.send(json.dumps({"id": mid[0], "method": m, "params": p or {}}))
    while True:
        r = json.loads(ws.recv())
        if r.get("id") == mid[0]:
            return r


send("Runtime.enable")
send("Page.enable")

ft = send("Page.getFrameTree", {})
frames = []


def walk(n, acc):
    f = n.get("frame", {})
    acc.append(f)
    for c in n.get("childFrames", []) or []:
        walk(c, acc)


walk(ft.get("result", {}).get("frameTree", {}), frames)
xl = [f for f in frames if "xlogin" in (f.get("url") or "")]
if not xl:
    print("NO_XLOGIN_FRAME")
    raise SystemExit
xl = xl[0]
iw = send("Page.createIsolatedWorld", {"frameId": xl["id"], "worldName": "probe5", "grantUniveralAccess": True})
ctx = iw["result"]["executionContextId"]


def fe(expr, await_p=False):
    x = send("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": await_p})
    if "exceptionDetails" in x:
        return "EXC: " + json.dumps(x["exceptionDetails"])[:150]
    return x.get("result", {}).get("result", {}).get("value")


# 1. 4300端口探测（await promise）
v = fe("""new Promise(function(res){
  var img=new Image();
  var ok=false;
  img.onload=function(){res('4300_IMG_OK')};
  img.onerror=function(){res('4300_IMG_ERR_but_port_alive?')};
  setTimeout(function(){res('4300_TIMEOUT')},4000);
  img.src='https://localhost.ptlogin2.qq.com:4300/ptget_1?0.1';
})""", await_p=True)
print("4300探测:", v)

# 2. pt对象方法
print("pt.plogin keys:", fe("Object.keys((typeof pt!=='undefined'&&pt.plogin)||{}).slice(0,40).join(',')"))
print("onekey相关:", fe("Object.keys((typeof pt!=='undefined'&&pt.plogin)||{}).filter(function(k){return /onekey|qlogin|avatar|client/i.test(k)}).join(',')"))

# 3. 直接调onekey数据接口
v2 = fe("""new Promise(function(res){
  var x=new XMLHttpRequest();
  x.open('GET','https://localhost.ptlogin2.qq.com:4300/pt_get_st?clientuin=&r=0.'+Date.now(),true);
  x.timeout=4000;
  x.onload=function(){res('GET_ST:'+x.status+':'+x.responseText.slice(0,120))};
  x.onerror=function(){res('GET_ST_ERR')};
  x.ontimeout=function(){res('GET_ST_TIMEOUT')};
  x.send();
})""", await_p=True)
print("pt_get_st:", v2)

ws.close()
