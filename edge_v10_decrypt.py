# -*- coding: utf-8 -*-
"""解密debug profile的v10密码（DPAPI user scope，本机可解）"""
import ctypes
import glob
import json
import os
import shutil
import sqlite3
import tempfile
import ctypes.wintypes as wt


class BLOB(ctypes.Structure):
    _fields_ = [("cbData", wt.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]


def dpapi_unprotect(data):
    buf = ctypes.create_string_buffer(data, len(data))
    bin_ = BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
    out = ctypes.c_void_p()
    out_len = wt.DWORD()
    ok = ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(bin_), None, None, None, None, 0, ctypes.byref(out))
    if not ok:
        raise OSError(ctypes.GetLastError())
    raw = ctypes.string_at(out, out_len.value)
    ctypes.windll.kernel32.LocalFree(out)
    return raw


src = r"C:/Users/QAXD/com_test/edge_debug_profile/Default/Login Data"
tmp = os.path.join(tempfile.gettempdir(), "dbg_ld3.db")
shutil.copy2(src, tmp)
con = sqlite3.connect(tmp)
rows = con.execute(
    "select origin_url, username_value, password_value from logins "
    "where origin_url like '%ptlogin2%' or origin_url like '%aq.qq.com%'"
).fetchall()
con.close()
os.remove(tmp)

out = []
for url, user, blob in rows:
    try:
        raw = blob[3:] if blob[:3] in (b"v10", b"v20") else blob
        plain = dpapi_unprotect(raw)
        out.append({"user": user, "pwd": plain.decode("utf-8", "replace"), "url": url[:50]})
    except Exception as e:
        out.append({"user": user, "err": str(e)[:80]})

print(json.dumps(out, ensure_ascii=False, indent=1))
with open(os.path.expandvars(r"%TEMP%/qq_pwd_dec.json"), "w") as f:
    json.dump(out, f, ensure_ascii=False)
