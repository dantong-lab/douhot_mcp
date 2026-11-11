# -*- coding: utf-8 -*-
"""测试signup_check GET参数风格 + 登录页/密码重置页的邮箱验证接口"""
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

ev("window.__r2=[];")
ev("""
var tests=[
  ['GET','/signup_check/email?value=826556165%40qq.com'],
  ['GET','/signup_check/email?value=test%40gmail.com']
];
tests.forEach(function(tt){
  var x=new XMLHttpRequest();
  x.open(tt[0],tt[1],true);
  x.setRequestHeader('X-Requested-With','XMLHttpRequest');
  x.onload=function(){
    var short=x.responseText.replace(/<[^>]+>/g,'').replace(/\\s+/g,' ').trim().slice(0,80);
    window.__r2.push(tt[1].slice(0,50)+' => '+x.status+' '+(short||'(empty=OK)'));
  };
  x.onerror=function(){window.__r2.push(tt[1]+' => ERR');};
  x.send();
});
""")
time.sleep(5)
print("GET风格:", ev("JSON.stringify(window.__r2,null,1)"))

# 关键测试：422的body里到底说什么错误（qq.com的）
ev("window.__body='';")
ev("""
var x3=new XMLHttpRequest();
x3.open('POST','/signup_check/email',true);
x3.setRequestHeader('X-Requested-With','XMLHttpRequest');
x3.onload=function(){window.__body=x3.responseText};
var fd3=new FormData();fd3.append('value','826556165@qq.com');
x3.send(fd3);
""")
time.sleep(4)
body = ev("window.__body") or ""
# 提取错误文本
import re

texts = re.findall(r">(?:Email|That|This|Address|address)[^<]{10,120}<", body)
print("422错误文本:", texts[:5])
# 或找 div class=error
m = re.search(r'class="[^"]*error[^"]*"[^>]*>([^<]{5,120})', body)
print("error div:", m.group(1) if m else None)
m2 = re.search(r"<p[^>]*>([^<]{10,150})</p>", body)
print("p标签:", m2.group(1) if m2 else None)

ws.close()
