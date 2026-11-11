# -*- coding: utf-8 -*-
"""MCP协议级验证：内存客户端连服务器，list_tools + 实际调用工具"""
import asyncio
import sys

sys.path.insert(0, r"C:\Users\QAXD\com_test\douhot_mcp")
from fastmcp import Client
import server


async def main():
    async with Client(server.mcp) as c:
        tools = await c.list_tools()
        print(f"MCP协议 list_tools: {len(tools)} 个")
        for t in tools:
            req = t.inputSchema.get("required", [])
            props = list(t.inputSchema.get("properties", {}).keys())
            print(f"- {t.name} | 必填={req} | 参数={props}")
        # 协议级实际调用（不碰CDP的轻工具）
        r = await c.call_tool("list_recent_files", {})
        print("\nlist_recent_files 协议调用 ->", r.data if hasattr(r, "data") else r)
        print("\n✅ MCP协议级验证通过")


asyncio.run(main())
