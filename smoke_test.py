# -*- coding: utf-8 -*-
"""冒烟测试：import级 + 工具schema + 工具函数单元级 + 真实拉取"""
import asyncio
import json
import sys

sys.path.insert(0, r"C:\Users\QAXD\com_test\douhot_mcp")

print("== 1. import级 ==")
import server  # noqa
print("server.py import OK; CDP_HTTP =", server.CDP_HTTP)

print("\n== 2. fastmcp 工具注册/schema ==")
mcp = server.mcp
tools = asyncio.run(mcp.get_tools()) if hasattr(mcp, "get_tools") else None
if tools is None:
    tm = getattr(mcp, "_tool_manager", None)
    tools = {t.name: t for t in tm.list_tools()} if tm else {}
for name, t in tools.items():
    schema = getattr(t, "parameters", None) or getattr(t, "inputSchema", None)
    print(f"- {name}: schema_keys={list((schema or {}).keys())}")
    if name == "get_video_billboard" and schema:
        props = schema.get("properties", {})
        print(f"  参数: {list(props.keys())}")

print("\n== 3. _resolve_tags 单元级 ==")
print("None ->", server._resolve_tags(None))
print("[旅行风景] ->", json.dumps(server._resolve_tags(["旅行风景"]), ensure_ascii=False))
print("[原生dict] ->", json.dumps(server._resolve_tags([{"value": 629, "children": [{"value": 62905}]}]), ensure_ascii=False))
try:
    server._resolve_tags(["不存在的垂类"])
    print("未知垂类: 未抛错(不符合预期)")
except ValueError as e:
    print("未知垂类 -> ValueError OK:", str(e)[:60])

print("\n== 4. 真实拉取 sub_type=1002, date_window=168, tags=旅行风景 ==")
try:
    r = server.get_video_billboard.__wrapped__(sub_type=1002, date_window=168, tags=["旅行风景"], page=1, page_size=10) \
        if hasattr(server.get_video_billboard, "__wrapped__") else None
    if r is None:
        # 装饰器可能返回原函数或Tool对象，两种都试
        f = server.get_video_billboard
        f = getattr(f, "fn", f)
        r = f(sub_type=1002, date_window=168, tags=["旅行风景"], page=1, page_size=10)
    items = r.get("items", [])
    print(f"code={r.get('code')} total={r.get('total')} count={r.get('count')}")
    print("落盘:", r.get("saved_to"))
    for it in items[:3]:
        print(f"  #{it.get('rank', '?')} {str(it.get('item_title'))[:30]} | {it.get('nick_name')} | 粉丝{it.get('fans_cnt')} 播放{it.get('play_cnt')} 分{it.get('score')}")
    print("\nlist_recent_files:")
    f2 = getattr(server.list_recent_files, "fn", server.list_recent_files)
    for x in f2()[:3]:
        print(" ", x["file"], x["size_bytes"], "B")
    print("\n✅ 冒烟测试全部通过")
except Exception as e:
    import traceback
    traceback.print_exc()
    print("\n❌ 真实拉取失败（CDP/登录态问题）:", e)
