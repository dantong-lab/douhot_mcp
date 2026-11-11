# -*- coding: utf-8 -*-
"""GitHub注册v5：重新填表+提交（美国IP，QQ邮箱）→ 到launch code页填53389066"""
import json
import time
import urllib.request

import websocket

CDP = "http://127.0.0.1:9222"
EMAIL = "826556165@qq.com"
USERNAME = "dantong-lab"
PASSWORD = "MdKFEeyzXD8ihLngQrwdYW7k"
CODE = "53389066"


def get_tab():
    tabs = [t for t in json.loads(urllib.request.urlopen(CDP + '/json/list', timeout=10).read())
            if t.get('type') == 'page']
    return [x for x in tabs if 'github.com/signup' in (x.get('url') or '')][0]


ws = websocket.create_connection(get_tab()['webSocketDebuggerUrl'], timeout=60)
mid = [0]


def sd(m, p=None):
    mid[0] += 1
    ws.send(json.dumps({'id': mid[0], 'method': m, 'params': p or {}}))
    while True:
        r = json.loads(ws.recv())
        if r.get('id') == mid[0]:
            return r


def ev(e, ap=False):
    r = sd('Runtime.evaluate', {'expression': e, 'returnByValue': True, 'awaitPromise': ap})
    if 'exceptionDetails' in r:
        return 'EXC:' + json.dumps(r['exceptionDetails'])[:150]
    v = r.get('result', {}).get('result', {})
    return v.get('value') if v.get('type') != 'undefined' else None


def type_like(sel, text):
    """React友好输入：native setter + input事件"""
    return ev(f'''(function(){{
  var el=document.querySelector('{sel}');
  if(!el) return 'NO_EL';
  el.focus();
  var proto=el.tagName==='TEXTAREA'?HTMLTextAreaElement.prototype:HTMLInputElement.prototype;
  var setter=Object.getOwnPropertyDescriptor(proto,'value').set;
  setter.call(el,'');
  el.dispatchEvent(new Event('input',{{bubbles:true}}));
  setter.call(el,'{text}');
  el.dispatchEvent(new Event('input',{{bubbles:true}}));
  el.dispatchEvent(new Event('change',{{bubbles:true}}));
  el.dispatchEvent(new Event('blur',{{bubbles:true}}));
  return 'OK:'+el.value.slice(0,30);
}})()''')


# Step1: 填邮箱
print('email:', type_like('#email', EMAIL))
time.sleep(1.5)
# Step2: 点Continue
print('continue:', ev('''(function(){
  var btns=[...document.querySelectorAll('button')].filter(b=>/continue/i.test(b.innerText));
  if(btns.length){btns[0].click();return 'clicked'}
  return 'no-btn';
})()'''))
time.sleep(2.5)
# Step3: 填密码
print('password:', type_like('#password', PASSWORD))
time.sleep(1.5)
# Step4: 填用户名
print('username:', type_like('#login', USERNAME))
time.sleep(3)
# Step5: 勾选邮箱优惠（可选）+ 提交
print('submit:', ev('''(function(){
  var btns=[...document.querySelectorAll('button')].filter(b=>/create account|continue/i.test(b.innerText));
  if(btns.length){btns[btns.length-1].click();return 'clicked:'+btns[btns.length-1].innerText}
  var f=document.querySelector('form');
  if(f){f.submit();return 'form-submit'}
  return 'no-btn';
})()'''))
time.sleep(4)
# 看落点
r = ev('document.body.innerText.slice(0,300)')
print('--- 页面落点 ---')
print(r)
ws.close()
