# -*- coding: utf-8 -*-
"""抖音热点宝(douhot.douyin.com)榜单抓取 MCP 服务器（stdio 模式）

原理（签名复用法，2026-11-09 实测验证）：
  1. 通过本机 Edge CDP 9222 打开热点宝榜单页（复用浏览器已有登录态）
  2. 等表格渲染完成（body.innerText 含「排名」+「新增播放量」）
  3. 从 performance.getEntriesByType('resource') 取最后一条 video_billboard 请求 URL
     —— 该 URL 自带 msToken/X-Bogus/_signature 完整签名
  4. 在页面上下文里 fetch(url, {body: 自定义JSON, credentials:'include'})
     —— body 的 page/page_size/sub_type/date_window/tags 均可自由修改，签名仍然有效

坑位（全部遵守，详见 skill: douhot-billboard-scrape）：
  - CDP Runtime.evaluate 返回双层嵌套，真值在 msg['result']['result']['value']
  - Playwright connect_over_cdp 偶发初始化卡死 → 用原生 websocket-client 直连
  - 僵尸 tab（evaluate 全超时）→ 关掉重建新 tab
  - 垂类参数名是 tags（不是 category/tag_id）
"""
import json
import os
import time
import datetime

import websocket  # websocket-client

from fastmcp import FastMCP

mcp = FastMCP("douhot-billboard")

CDP_HTTP = os.environ.get("DOUHOT_CDP_HTTP", "http://127.0.0.1:9222")
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# 已知垂类ID（2026-11-09 从下拉面板DOM实测；其他垂类可在页面DOM里看checkbox对应值）
CATEGORY_MAP = {
    "旅行": 629,
    "旅行风景": 62905,
}
# 旅行风景的完整 tags 结构
TAG_TRAVEL_SCENERY = [{"value": 629, "children": [{"value": 62905}]}]

CDP_ERR = "请先启动Edge CDP 9222并登录douhot.douyin.com（启动命令见README）"

SUB_TYPE_NAMES = {1001: "视频总榜", 1002: "低粉爆款", 1003: "高完播", 1004: "高涨粉", 1005: "高点赞"}


# ---------------------------------------------------------------- CDP 底座
class CdpPage:
    """原生 websocket-client 直连单个页面 target（绕开 Playwright 卡死坑）"""

    def __init__(self, ws_url: str):
        self.ws = websocket.create_connection(ws_url, timeout=30)
        self.i = 0

    def cmd(self, method: str, params: dict | None = None, timeout: int = 30):
        self.i += 1
        mid = self.i
        self.ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                self.ws.settimeout(max(0.5, deadline - time.time()))
                msg = json.loads(self.ws.recv())
            except websocket.WebSocketTimeoutException:
                break
            if msg.get("id") == mid:
                return msg.get("result", {})
        return {"__err": "timeout"}

    def eval(self, expr: str, timeout: int = 30):
        """Runtime.evaluate；真值在 result['result']['value']（双层嵌套，勿只解一层）"""
        return self.cmd(
            "Runtime.evaluate",
            {"expression": expr, "awaitPromise": True, "returnByValue": True},
            timeout,
        )


def _eval_value(pg: CdpPage, expr: str, timeout: int = 30):
    st = pg.eval(expr, timeout)
    if "__err" in st:
        raise RuntimeError(f"CDP evaluate 超时（疑似僵尸tab）：{expr[:80]}")
    inner = st.get("result", {})
    return inner.get("value") if isinstance(inner, dict) else None


def _open_douhot_tab(sub_type: int, date_window: int) -> CdpPage:
    """优先复用已打开的热点宝tab，否则开新tab导航过去"""
    try:
        import urllib.request

        tabs = json.loads(urllib.request.urlopen(f"{CDP_HTTP}/json", timeout=8).read())
    except Exception as e:
        raise RuntimeError(f"{CDP_ERR} —— 连接失败：{e}")

    url = (
        "https://douhot.douyin.com/square/hotspot"
        f"?active_tab=hotspot_video&date_window={date_window}&sub_type={sub_type}"
    )
    existing = [t for t in tabs if t.get("type") == "page" and "douhot.douyin.com" in (t.get("url") or "")]
    if existing:
        pg = CdpPage(existing[0]["webSocketDebuggerUrl"])
        # 探活：能 evaluate 说明 tab 没僵尸
        try:
            if _eval_value(pg, "1+1", timeout=8) == 2:
                if "square/hotspot" not in (existing[0].get("url") or ""):
                    pg.cmd("Page.navigate", {"url": url}, timeout=30)
                    time.sleep(2)
                return pg
        except Exception:
            pass  # 僵尸tab → 走重建
    # 开新 tab
    ver = json.loads(urllib.request.urlopen(f"{CDP_HTTP}/json/version", timeout=8).read())
    bws = websocket.create_connection(ver["webSocketDebuggerUrl"], timeout=15)
    bws.send(json.dumps({"id": 1, "method": "Target.createTarget", "params": {"url": url}}))
    deadline = time.time() + 15
    tid = None
    while time.time() < deadline:
        try:
            bws.settimeout(max(0.5, deadline - time.time()))
            msg = json.loads(bws.recv())
            if msg.get("id") == 1:
                tid = msg.get("result", {}).get("targetId")
                break
        except websocket.WebSocketTimeoutException:
            break
    bws.close()
    if not tid:
        raise RuntimeError(f"{CDP_ERR} —— 创建tab失败")
    time.sleep(1.5)
    tabs = json.loads(urllib.request.urlopen(f"{CDP_HTTP}/json", timeout=8).read())
    ws_url = next(t["webSocketDebuggerUrl"] for t in tabs if t.get("id") == tid)
    return CdpPage(ws_url)


def _wait_table_ready(pg: CdpPage, tries: int = 14) -> bool:
    """页面渲染判定 = body.innerText 含「排名」+「新增播放量」"""
    for _ in range(tries):
        time.sleep(2.5)
        try:
            ok = _eval_value(
                pg,
                "(() => document.body.innerText.includes('排名') && document.body.innerText.includes('新增播放量'))()",
                timeout=12,
            )
            if ok is True:
                return True
        except Exception:
            return False
    return False


def _signed_billboard_url(pg: CdpPage) -> str:
    url = _eval_value(
        pg,
        "(() => { const es = performance.getEntriesByType('resource').map(e=>e.name)"
        ".filter(u=>u.includes('video_billboard')); return es.length ? es[es.length-1] : null; })()",
        timeout=15,
    )
    if not url:
        # 等一等再试（首屏请求可能刚发出）
        time.sleep(4)
        url = _eval_value(
            pg,
            "(() => { const es = performance.getEntriesByType('resource').map(e=>e.name)"
            ".filter(u=>u.includes('video_billboard')); return es.length ? es[es.length-1] : null; })()",
            timeout=15,
        )
    if not url:
        raise RuntimeError("页面已渲染但没抓到 video_billboard 签名请求，请刷新热点宝页面后重试")
    return url


_FETCH_JS = """async (body) => {
    const es = performance.getEntriesByType('resource').map(e=>e.name).filter(u=>u.includes('video_billboard'));
    const url = es[es.length-1];
    const resp = await fetch(url, {method:'POST', headers:{'content-type':'application/json'},
        body: JSON.stringify(body), credentials:'include'});
    const j = await resp.json();
    return {code: j.code, msg: j.msg || '',
        total: j.data && j.data.page ? j.data.page.total : null,
        objs: j.data && j.data.objs ? j.data.objs : []};
}"""


def _resolve_tags(tags) -> list | None:
    """tags 支持 ['旅行风景'] 这类中文名，或原生结构 [{'value':629,...}] 直传"""
    if not tags:
        return None
    out = []
    for t in tags:
        if isinstance(t, str):
            if t == "旅行风景":
                out.extend(TAG_TRAVEL_SCENERY)
            elif t in CATEGORY_MAP:
                out.append({"value": CATEGORY_MAP[t]})
            else:
                raise ValueError(
                    f"未知垂类名「{t}」。内置支持：{list(CATEGORY_MAP.keys())}；"
                    "其他垂类请传原生结构 [{'value': 垂类id, 'children': [{'value': 子垂类id}]}]"
                    "（id 可在热点宝页面垂类下拉的 DOM checkbox 上看到）"
                )
        else:
            out.append(t)  # dict/list 原生结构直通
    return out


def _fetch_billboard(sub_type: int, date_window: int, tags, page: int, page_size: int) -> dict:
    pg = _open_douhot_tab(sub_type, date_window)
    try:
        if not _wait_table_ready(pg):
            raise RuntimeError("热点宝页面渲染超时：请确认已在 Edge 里扫码登录 douhot.douyin.com，且页面能正常打开")
        _signed_billboard_url(pg)  # 确认签名 URL 存在
        body = {
            "page": page,
            "page_size": page_size,
            "date_window": date_window,
            "sub_type": sub_type,
            "tag_version": "v2",
        }
        rt = _resolve_tags(tags)
        if rt:
            body["tags"] = rt
        v = _eval_value(pg, f"({_FETCH_JS})({json.dumps(body, ensure_ascii=False)})", timeout=40)
        if not v or v.get("code") != 0:
            raise RuntimeError(f"热点宝API返回异常：{json.dumps(v, ensure_ascii=False)[:200]}（签名可能过期，重试一次通常自愈）")
        return v
    finally:
        try:
            pg.ws.close()
        except Exception:
            pass


def _save_result(v: dict, meta: dict) -> str:
    os.makedirs(DATA_DIR, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = "_".join(str(t.get("value")) for t in (meta.get("tags_resolved") or [])) or "all"
    path = os.path.join(DATA_DIR, f"douhot_{meta['sub_type']}_{meta['date_window']}_{slug}_{ts}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "result": v}, f, ensure_ascii=False, indent=1)
    return path


# ---------------------------------------------------------------- MCP 工具
@mcp.tool
def get_video_billboard(
    sub_type: int = 1002,
    date_window: int = 168,
    tags: list | None = None,
    page: int = 1,
    page_size: int = 30,
) -> dict:
    """抓取抖音热点宝视频榜单。

    Args:
        sub_type: 榜单类型 1001=视频总榜 1002=低粉爆款 1003=高完播 1004=高涨粉 1005=高点赞
        date_window: 时间窗 24=近1天 168=近7天
        tags: 垂类过滤，如 ["旅行风景"]；None=不限垂类
        page: 页码（从1开始）
        page_size: 每页条数（上限100）

    Returns:
        {code, total, count, items:[{item_id,item_title,nick_name,fans_cnt,play_cnt,score,...}], saved_to}
    """
    if page_size > 100:
        page_size = 100
    v = _fetch_billboard(sub_type, date_window, tags, page, page_size)
    tags_resolved = _resolve_tags(tags)
    meta = {
        "sub_type": sub_type,
        "sub_type_name": SUB_TYPE_NAMES.get(sub_type, str(sub_type)),
        "date_window": date_window,
        "tags": tags,
        "tags_resolved": tags_resolved or [],
        "page": page,
        "page_size": page_size,
        "fetched_at": datetime.datetime.now().isoformat(timespec="seconds"),
    }
    saved = _save_result(v, meta)
    return {
        "code": v["code"],
        "total": v.get("total"),
        "count": len(v.get("objs", [])),
        "items": v.get("objs", []),
        "saved_to": saved,
    }


@mcp.tool
def list_recent_files() -> list:
    """列出本服务器已抓取保存的榜单数据文件（data/ 目录，按时间倒序）。"""
    if not os.path.isdir(DATA_DIR):
        return []
    out = []
    for fn in sorted(os.listdir(DATA_DIR), reverse=True):
        if not fn.endswith(".json"):
            continue
        p = os.path.join(DATA_DIR, fn)
        out.append({"file": fn, "size_bytes": os.path.getsize(p),
                    "mtime": datetime.datetime.fromtimestamp(os.path.getmtime(p)).isoformat(timespec="seconds")})
    return out


if __name__ == "__main__":
    mcp.run()  # stdio
