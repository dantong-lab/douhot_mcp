# -*- coding: utf-8 -*-
"""QQ一键登录：port 4301 + ptlogin2协议
流程: 1) iframe里导航到4301获取clientuin列表 2) 调pt.plogin.onekey触发
"""
import json
import time
import urllib.request

import websocket

CDP = "http://127.0.0.1:9222"

tabs = [t for t in json.loads(urllib.request.urlopen(CDP + "/json/list", timeout=10).read()) if t.get("type") == "page"]
t = [x for x in tabs if "wx.mail.qq.com" in (x.get("url") or "")][0]
ws = websocket.create_connection(t["webSocketDebuggerUrl"], timeout=40)
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
xl = [f for f in frames if "xlogin" in (f.get("url") or "")][0]
iw = send("Page.createIsolatedWorld", {"frameId": xl["id"], "worldName": "onekey", "grantUniveralAccess": True})
ctx = iw["result"]["executionContextId"]


def fe(expr, await_p=False, timeout=15):
    x = send("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": await_p})
    if "exceptionDetails" in x:
        return "EXC: " + json.dumps(x["exceptionDetails"])[:200]
    return x.get("result", {}).get("result", {}).get("value")


# 1. 探测4301 quick login服务（JSONP风格）
v = fe("""new Promise(function(res){
  var s=document.createElement('script');
  window.__ok=null;
  s.src='https://localhost.ptlogin2.qq.com:4301/pt_get_uins?callback=__ok&r=0.'+Date.now();
  s.onerror=function(){res('SCRIPT_ERR')};
  document.body.appendChild(s);
  setTimeout(function(){res('RESULT:'+(window.__ok||'null'))},5000);
})""", await_p=True)
print("4301 uins:", str(v)[:300])

# 2. 若拿到uins列表，调onekey登录
if "RESULT" in str(v) and "null" not in str(v):
    uins = str(v)
    print("检测到QQ客户端账号!")
    # pt.plogin.onekey(uin, sessionid, auto_login)
    r = fe("""(function(){
      try{
        var uin=Object.keys(window.__ok||{})[0]||window.__ok[0];
        pt.plogin.onekey(uin, 0, true);
        return 'onekey_fired:'+uin;
      }catch(e){return 'onekey_ERR:'+e.message}
    })()""")
    print("onekey:", r)
    time.sleep(4)
    # 检查父页面是否跳转
    top_url = fe("top.location.href")
    print("top url:", top_url)

ws.close()
