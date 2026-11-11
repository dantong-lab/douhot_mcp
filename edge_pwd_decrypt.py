# -*- coding: utf-8 -*-
"""解密Edge密码库中ptlogin2.qq.com的密码（本机DPAPI，仅本地使用）"""
import base64
import json
import os
import shutil
import sqlite3
import tempfile
import glob

import win32crypt

paths = glob.glob(os.path.expandvars(r"%LOCALAPPDATA%/Microsoft/Edge/User Data/*/Login Data"))
p = paths[0]
tmp = os.path.join(tempfile.gettempdir(), "ld_decrypt.db")
shutil.copy2(p, tmp)
con = sqlite3.connect(tmp)
rows = con.execute(
    "select origin_url, username_value, password_value from logins "
    "where origin_url like '%ptlogin2.qq.com%'"
).fetchall()
con.close()
os.remove(tmp)

out = []
for url, user, blob in rows:
    try:
        # v10/v20前缀: strip
        if blob[:3] in (b"v10", b"v20"):
            raw = blob[3:]
        else:
            raw = blob
        # DPAPI解密 (CryptUnprotectData, 无entropy)
        _, plain = win32crypt.CryptUnprotectData(raw, None, None, None, 0)
        out.append({"url": url, "user": user, "password": plain.decode("utf-8", "replace")})
    except Exception as e:
        out.append({"url": url, "user": user, "error": str(e)[:100]})

print(json.dumps(out, ensure_ascii=False, indent=1))
with open(os.path.expandvars(r"%TEMP%\qq_pwd_probe.json"), "w") as f:
    json.dump(out, f, ensure_ascii=False)
