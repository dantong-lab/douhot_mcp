# douhot-billboard MCP

抖音热点宝（douhot.douyin.com）视频榜单抓取 MCP 服务器 —— 把「低粉爆款/旅行风景」等垂类榜单拉取管线标准化为 MCP 工具，供 Hermes / Claude Desktop 等 MCP 宿主直接调用。

## 功能

| 工具 | 说明 |
|---|---|
| `get_video_billboard(sub_type, date_window, tags, page, page_size)` | 抓取视频榜单，自动落盘 JSON 并返回条目 |
| `list_recent_files()` | 列出已抓取的数据文件 |

**榜单类型（sub_type）**：1001 视频总榜 / 1002 低粉爆款 / 1003 高完播 / 1004 高涨粉 / 1005 高点赞
**时间窗（date_window）**：24=近1天，168=近7天
**垂类（tags）**：`["旅行风景"]` 等中文名（内置映射），或原生结构 `[{"value":629,"children":[{"value":62905}]}]` 直传

## 技术原理（签名复用法）

1. 通过本机 Edge 的 CDP 调试口（9222）操纵浏览器，复用已有**扫码登录态**（服务器自身不存任何 cookie）
2. 等榜单表格渲染完成
3. 从 `performance.getEntriesByType('resource')` 取**最后一条 `video_billboard` 请求 URL**——其自带 `msToken/X-Bogus/_signature` 完整签名
4. 在页面上下文内 `fetch(url, {body: 自定义JSON, credentials:'include'})`——**body 的 page/page_size/sub_type/date_window/tags 均可自由修改而签名仍有效**（2026-11-09 实测验证）

因此无需逆向签名算法、无需 UI 自动化点选垂类面板。

## 前置条件（必须）

1. **Edge 以调试模式启动**（CMD/PowerShell）：
   ```
   "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --remote-debugging-port=9222
   ```
2. 在该 Edge 窗口里打开 `douhot.douyin.com` 并**扫码登录**（分析页能看到榜单即算就绪）
3. Python 3.11+，`pip install -r requirements.txt`（fastmcp + websocket-client；刻意不用 playwright 规避 connect_over_cdp 偶发卡死）

## 安装与接入

```bash
cd douhot_mcp
pip install -r requirements.txt
```

**Hermes 接入**（`~/.hermes/config.yaml` 的 mcp 段或对应 mcpServers 配置）：

```json
{
  "mcpServers": {
    "douhot-billboard": {
      "command": "python",
      "args": ["C:\\Users\\QAXD\\com_test\\douhot_mcp\\server.py"]
    }
  }
}
```

**Claude Desktop 接入**（`claude_desktop_config.json`）：

```json
{
  "mcpServers": {
    "douhot-billboard": {
      "command": "python",
      "args": ["C:\\Users\\QAXD\\com_test\\douhot_mcp\\server.py"]
    }
  }
}
```

环境变量 `DOUHOT_CDP_HTTP` 可覆盖默认调试口地址（默认 `http://127.0.0.1:9222`）。

## 已知限制

- 依赖本机 Edge CDP 9222 + 已登录热点宝：未启动/未登录时工具会返回中文错误提示「请先启动Edge CDP 9222并登录douhot.douyin.com」
- 签名 URL 来自页面最近一次榜单请求：页面刚打开时偶尔需等首屏请求发出（服务器已内置等待+重试）；若签名过期，重试一次通常自愈
- 单标签页复用：并发调用同一时刻只应有一个（CDP evaluate 非线程安全设计，stdio 模式下单线程天然满足）
- 僵尸 tab（evaluate 全超时）会自动被跳过并新建 tab；极端情况手动关掉 douhot 的 Edge 标签页即可
- 垂类 ID 内置映射目前只有 旅行(629)/旅行风景(62905)；其他垂类请传原生结构，ID 可在页面垂类下拉的 DOM checkbox 上查看
- 低粉爆款榜 `total` 标 1000，但单垂类过滤后真实 total 会小很多（平台去重/下架导致），属正常现象

## 待验证

- （2026-11-11 已实测）Edge CDP 9222 在跑：`sub_type=1002, date_window=168, tags=旅行风景` 真实拉取通过，见 `data/` 目录落盘文件

## 数据来源与合规

数据来自抖音热点宝前台页面（登录用户可见的分析功能），仅供个人数据分析/选题参考，请勿高频抓取或商用转售。
