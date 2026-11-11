# -*- coding: utf-8 -*-
"""测试GitHub signup_check对各邮箱域名的接受度"""
import json
import time
import urllib.request

import websocket

CDP = "http://127.0.0.1:9222"

tabs = [t for t in json.loads(urllib.request.urlopen(CDP + "/json/list", timeout=10).read()) if t.get("type") == "page"]
gits = [t for t in tabs if "github.com/signup" in (t.get("url") or "")]
t = gits[0]
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

ev("window.__r=[];")
ev("""
var emails=['826556165@qq.com','outlook_860EE7291470254D@outlook.com','liuchanghui@outlook.com'];
emails.forEach(function(em){
  var x=new XMLHttpRequest();
  x.open('POST','/signup_check/email',true);
  x.setRequestHeader('X-Requested-With','XMLHttpRequest');
  x.onload=function(){
    var short=x.responseText.replace(/<[^>]+>/g,'').trim().slice(0,60);
    window.__r.push(em.slice(0,20)+' => '+x.status+' '+(short||'(empty=OK)'));
  };
  x.onerror=function(){window.__r.push(em.slice(0,20)+' => ERR');};
  var fd=new FormData();fd.append('value',em);
  x.send(fd);
});
""")
time.sleep(5)
print(ev("JSON.stringify(window.__r,null,1)"))
ws.close()
