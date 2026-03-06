# ayria 架构设计与可行性研究

## 1. 文档定位

本文档是 `ayria` 项目的第一版架构设计与可行性研究结果。
目标不是讨论概念，而是给工程团队一个可以直接拆任务、建仓、写代码的实施蓝图。

项目定位：

- `ayria` 是一个本地优先的桌面存在系统，不是普通聊天机器人。
- `ayria` 的核心体验是“打破第四面墙”：它不仅响应用户输入，还能理解当前桌面环境、用户正在看的内容、当前任务状态，并以角色化方式参与其中。
- `ayria` 是一个“本地桌面壳 + Python Agent Runtime + 本地模型 + 可选云端 fallback”的混合系统。

本文档覆盖：

- 目标与边界
- 系统总体架构
- 技术选型
- 目录结构
- 进程边界
- 模块职责
- 接口设计
- 数据结构
- 事件协议
- 模型接入策略
- 人格层设计
- 记忆系统设计
- 多层级协作设计
- 安全边界
- 迭代计划

## 2. 产品目标

### 2.1 核心目标

`ayria` 需要同时满足以下目标：

- 本地常驻
- 明显角色感和陪伴感
- 能看图和理解桌面截图
- 能读取当前上下文并做“环境感知式”互动
- 能调用工具
- 能在复杂任务上升级到更强模型
- 不因为人格化而破坏工具调用纪律

### 2.2 一句话定义

`ayria` 是一个以“桌面存在感”为核心的本地陪伴型 Agent 系统：
它持续观察用户的工作环境，形成世界状态，必要时主动插话、解释、提醒、协助或执行工具，并以人格化表达与用户互动。

### 2.3 非目标

以下内容不作为 v1 目标：

- 全自动电脑控制代理
- 无限制自主执行
- 复杂多 Agent 自由辩论系统
- 一开始就训练猫娘 LoRA
- 一开始就做语音对话全套闭环
- 一开始就做跨设备同步

## 3. 结论摘要

### 3.1 推荐架构结论

推荐采用以下架构：

- 前端桌面壳：`Tauri + TypeScript`
- 后端 Runtime：`Python 3.11+`
- 本地模型接入：
  - Windows/NVIDIA 优先 `Ollama`
  - macOS/Apple Silicon 优先 `MLX/MLX-VLM`，对外封装成 OpenAI-compatible 接口
- Agent 执行层：
  - 主调度器自研轻量事件驱动状态机
  - 复杂任务执行可嵌入 `PydanticAI`
- 人格策略：人格后置，不在主能力脑上直接挂 LoRA
- 复杂任务：云端 fallback，可选 OpenRouter/OpenAI-compatible provider

### 3.2 为什么不是“全 PydanticAI”

原因如下：

- `ayria` 的核心不是一次性 agent 调用，而是持续存在、环境感知、状态维持和时机控制。
- `PydanticAI` 适合做工具调用、结构化输出、复杂任务子代理。
- `PydanticAI` 不适合作为整个桌面存在系统的总框架。

因此：

- `PydanticAI` 可以用
- 但只应作为 Python runtime 内部的一个“任务执行子层”
- 不应主导整个系统边界设计

### 3.3 为什么要 `TypeScript + Python` 双层

- `TypeScript/Tauri` 更适合桌面壳、UI、面板、Web 技术栈和表现层
- `Python` 更适合本地 LLM 生态、MLX、Ollama、多模态、评测、记忆、Agent 实验
- 这两层边界清晰，长期维护成本最低

## 4. 总体架构

### 4.1 总体分层

系统拆成 6 层：

1. `Desktop Shell Layer`
2. `Presence Layer`
3. `Context Aggregation Layer`
4. `Agent Orchestration Layer`
5. `Model and Tool Layer`
6. `Memory and Storage Layer`

### 4.2 分层说明

#### 4.2.1 Desktop Shell Layer

职责：

- 托盘
- 悬浮窗
- 对话面板
- 设置页
- 桌面叠加层
- 状态展示
- 用户授权入口

技术：

- `Tauri`
- `React`
- `TypeScript`
- `Zustand`
- `TanStack Query`

#### 4.2.2 Presence Layer

职责：

- 监听当前活跃窗口
- 周期性桌面截图
- 剪贴板变化监听
- 用户输入活跃度检测
- 空闲状态检测
- 触发“主动互动”的时机判断

说明：

这一层决定 `ayria` 是否真的“活在桌面里”。

#### 4.2.3 Context Aggregation Layer

职责：

- 收集窗口标题、应用名、URL、截图理解结果、最近对话、最近用户操作
- 形成统一世界状态 `WorldState`
- 做上下文压缩和摘要
- 提供“当前正在发生什么”的统一视图

#### 4.2.4 Agent Orchestration Layer

职责：

- 决定何时回复
- 决定是被动响应还是主动插话
- 决定用哪个模型
- 决定是否需要工具调用
- 决定能力脑和人格层的执行顺序
- 管理任务状态

#### 4.2.5 Model and Tool Layer

职责：

- 本地模型推理
- 云端 fallback
- 图片理解
- 搜索
- 文件读取
- MCP 工具调用
- 桌面工具调用

#### 4.2.6 Memory and Storage Layer

职责：

- 对话存储
- 用户画像
- 长期记忆
- 会话摘要
- 世界状态快照
- 模型配置
- 审计日志

## 5. 技术选型

## 5.1 前端和桌面壳

推荐：

- `Tauri 2`
- `React`
- `TypeScript`
- `Vite`
- `Zustand`
- `TanStack Query`
- `Tailwind CSS`

原因：

- 资源占用比 Electron 更合适
- 与 Rust/Tauri 的系统能力集成较自然
- UI 表达力足够强
- 后期可扩展为悬浮窗、快捷面板、桌宠化外观

## 5.2 Python Runtime

推荐：

- `Python 3.11+`
- `FastAPI`
- `uvicorn`
- `pydantic v2`
- `SQLAlchemy` 或 `sqlmodel`
- `SQLite`
- `httpx`
- `orjson`

原因：

- Python 生态适配本地 LLM 最好
- FastAPI 适合做 runtime server
- Pydantic 适合定义统一协议和结构化对象

## 5.3 Agent 层

推荐：

- 主调度：自研轻量 orchestrator
- 子代理执行：可选 `PydanticAI`

不推荐：

- 一开始就用 `LangGraph` 作为总调度器
- 一开始就用 `AutoGen` 作为总框架

原因：

- 你的系统是桌面状态机，不是工作流引擎
- 要求是实时响应和持续存在，不是复杂 DAG 编排

## 5.4 本地模型接入

推荐：

- 默认：`OpenAI-compatible` 抽象层
- Windows/NVIDIA：`Ollama`
- macOS：`MLX/MLX-VLM` 自建适配服务

说明：

所有模型服务统一收敛到一个协议：

- `/v1/chat/completions`
- `/v1/responses` 可选
- 图像输入统一为内容数组形式

这样前端和 orchestrator 不直接依赖具体推理后端。

## 5.5 模型推荐

v1 推荐候选：

- `Qwen3.5-4B`
- `Qwen3.5-9B`

对照候选：

- `Qwen2.5-VL-3B`
- `Qwen2.5-VL-7B`

推荐策略：

- 本地常驻首选 `Qwen3.5-4B`
- `Qwen3.5-9B` 作为更高能力配置项
- 不建议一开始就在主能力脑上叠人格 LoRA

## 6. 进程边界

`ayria` 至少拆成 3 个进程。

### 6.1 进程 A: desktop-app

职责：

- UI
- 设置
- 面板
- 用户交互
- 授权与提示
- 与 runtime 通信

技术：

- `Tauri + React`

### 6.2 进程 B: runtime-server

职责：

- 事件聚合
- 世界状态维护
- 任务编排
- 模型路由
- 记忆系统
- 工具调用

技术：

- `FastAPI`

### 6.3 进程 C: model-provider(s)

职责：

- 具体模型推理

实例：

- `ollama serve`
- `mlx adapter server`
- 可选云端 OpenAI-compatible provider

### 6.4 进程通信

推荐：

- `desktop-app <-> runtime-server`: `WebSocket + HTTP`
- `runtime-server <-> model-provider`: `HTTP`
- `runtime-server <-> system watcher`: 同进程或本地 IPC

## 7. 目录结构

建议从一开始就做 monorepo。

```text
ayria/
  README.md
  docs/
    architecture/
      ayria-architecture-v1.md
      event-protocol.md
      api-contracts.md
      prompt-policy.md
    product/
      prd.md
      interaction-principles.md
  apps/
    desktop/
      src/
        app/
        components/
        features/
          chat/
          presence/
          settings/
          memory/
        lib/
          api/
          ws/
          store/
        pages/
        styles/
      src-tauri/
        src/
          commands/
          permissions/
          platform/
        tauri.conf.json
      package.json
    runtime/
      pyproject.toml
      app/
        main.py
        api/
          routes/
            health.py
            chat.py
            events.py
            tasks.py
            memory.py
            config.py
            providers.py
        core/
          config.py
          logging.py
          lifecycle.py
        domain/
          models/
            message.py
            event.py
            world_state.py
            task.py
            memory.py
            tool.py
          services/
            orchestrator.py
            presence_service.py
            context_service.py
            memory_service.py
            task_service.py
            persona_service.py
            routing_service.py
        providers/
          llm/
            base.py
            ollama_provider.py
            mlx_provider.py
            cloud_provider.py
          vision/
            screenshot_analyzer.py
          tools/
            registry.py
            web_search.py
            file_reader.py
            desktop_snapshot.py
            clipboard_tool.py
            mcp_bridge.py
        agents/
          capability_agent.py
          persona_rewriter_agent.py
          proactive_agent.py
          evaluator_agent.py
        prompts/
          system/
            capability.md
            persona.md
            proactive.md
          templates/
            screenshot_analysis.md
            web_search.md
        infra/
          db/
            models.py
            session.py
            migrations/
          repositories/
            message_repo.py
            memory_repo.py
            world_state_repo.py
            task_repo.py
        tests/
          unit/
          integration/
          eval/
            datasets/
            cases/
    model-adapters/
      mlx-openai-adapter/
        app.py
        README.md
  packages/
    shared-schema/
      src/
        events.ts
        api.ts
        world-state.ts
      package.json
  scripts/
    dev/
    setup/
  .github/
    workflows/
```

## 8. 核心模块职责

## 8.1 desktop-app

### 8.1.1 UI 模块

路径：`apps/desktop/src/features/chat`

职责：

- 聊天面板
- 多段消息渲染
- 工具调用过程展示
- 图像分析结果展示
- 主动消息展示

### 8.1.2 Presence UI 模块

路径：`apps/desktop/src/features/presence`

职责：

- 当前状态显示
- 当前活跃应用
- “ayria 正在看什么”
- 是否主动观察中
- 是否处于安静模式

### 8.1.3 Settings 模块

路径：`apps/desktop/src/features/settings`

职责：

- 模型配置
- provider 配置
- 主动程度设置
- 隐私设置
- 黑名单应用列表
- 截图采样策略

## 8.2 runtime-server

### 8.2.1 Orchestrator

路径：`apps/runtime/app/domain/services/orchestrator.py`

职责：

- 接收用户消息或环境事件
- 合并上下文
- 选择响应策略
- 调用能力脑
- 调用人格层
- 产出结果事件

### 8.2.2 Presence Service

路径：`apps/runtime/app/domain/services/presence_service.py`

职责：

- 处理窗口变化
- 处理截图事件
- 处理剪贴板变化
- 处理空闲/唤醒事件
- 形成 Presence 状态

### 8.2.3 Context Service

路径：`apps/runtime/app/domain/services/context_service.py`

职责：

- 维护 `WorldState`
- 生成模型输入上下文
- 做窗口摘要、截图摘要、对话摘要
- 控制上下文长度

### 8.2.4 Persona Service

路径：`apps/runtime/app/domain/services/persona_service.py`

职责：

- 在能力结果基础上进行人格化表达改写
- 根据场景决定人格浓度
- 在工具结果场景下降低卖萌强度

### 8.2.5 Routing Service

路径：`apps/runtime/app/domain/services/routing_service.py`

职责：

- 选择本地小模型还是高能力模型
- 选择是否走云端 fallback
- 选择是否需要视觉分析子流程

### 8.2.6 Memory Service

路径：`apps/runtime/app/domain/services/memory_service.py`

职责：

- 抽取长期记忆
- 读取用户偏好
- 维护短期会话摘要
- 决定哪些信息可以长期保存

## 9. 多层级协作架构

本系统不建议做“多个 agent 平等互聊”。
推荐的是“分层协作”。

### 9.1 协作层级

#### 层级 1: Presence Controller

职责：

- 决定是否介入
- 决定触发哪类任务
- 控制主动度

#### 层级 2: Capability Agent

职责：

- 做事实判断
- 做截图分析
- 做工具调用
- 做结构化输出

#### 层级 3: Persona Rewriter

职责：

- 把能力结果转成猫娘陪伴表达
- 调整语气和互动方式

#### 层级 4: Evaluator

职责：

- 可选
- 检查输出是否越界
- 检查是否泄露不该提及的环境信息
- 检查主动发言是否打扰用户

### 9.2 调用顺序

标准消息流：

1. 用户输入或环境事件进入
2. `Presence Controller` 判断是否需要响应
3. `Context Service` 构建世界状态
4. `Capability Agent` 生成结构化结果
5. 如有需要调用工具
6. `Persona Rewriter` 改写结果
7. `Evaluator` 做最终检查
8. 下发到桌面 UI

### 9.3 为什么不建议“双脑互相聊天”

原因：

- 成本高
- 延迟高
- 调试复杂
- 不利于本地 4B/9B 机器约束
- 很容易变成工程噱头

推荐模式：

- 单能力脑
- 单人格改写层
- 必要时增加一个轻量 evaluator

## 10. 人格策略

### 10.1 总原则

- 人格后置
- 事实优先
- 在工具输出场景中降低角色化浓度
- 在陪伴对话场景中提高角色化浓度

### 10.2 人格层不直接控制工具调用

原因：

- 避免函数调用混乱
- 避免结构化输出退化
- 避免截图描述不客观

### 10.3 人格强度档位

建议设置 4 档：

- `off`
- `light`
- `normal`
- `immersive`

### 10.4 人格改写输入输出协议

输入：

- 能力层原始结果
- 当前场景类型
- 角色强度设置
- 用户偏好

输出：

- 最终展示文本
- 表情/动作建议
- 是否适合主动追问

## 11. 世界状态模型

路径：`apps/runtime/app/domain/models/world_state.py`

推荐定义：

```python
from pydantic import BaseModel
from typing import List, Optional, Literal

class ActiveWindow(BaseModel):
    app_name: str
    window_title: str
    url: Optional[str] = None
    bundle_id: Optional[str] = None

class ClipboardState(BaseModel):
    text_preview: Optional[str] = None
    updated_at: str

class ScreenshotSummary(BaseModel):
    image_id: str
    summary: str
    detected_entities: List[str]
    scene_type: Literal["code", "browser", "document", "chat", "image", "desktop", "unknown"]
    confidence: float

class PresenceState(BaseModel):
    mode: Literal["idle", "observing", "chatting", "busy", "sleeping"]
    user_active: bool
    last_user_input_at: str
    proactive_allowed: bool

class WorldState(BaseModel):
    active_window: ActiveWindow
    clipboard: Optional[ClipboardState] = None
    recent_screenshots: List[ScreenshotSummary] = []
    recent_messages: List[str] = []
    current_task_hint: Optional[str] = None
    presence: PresenceState
    user_goal_summary: Optional[str] = None
```

## 12. 核心数据模型

## 12.1 Message

路径：`apps/runtime/app/domain/models/message.py`

```python
from pydantic import BaseModel
from typing import Literal, Optional, List

class MessagePart(BaseModel):
    type: Literal["text", "image", "tool_result"]
    text: Optional[str] = None
    image_url: Optional[str] = None
    tool_name: Optional[str] = None
    payload: Optional[dict] = None

class ChatMessage(BaseModel):
    id: str
    role: Literal["user", "assistant", "system", "tool"]
    source: Literal["ui", "proactive", "tool", "memory", "system"]
    parts: List[MessagePart]
    created_at: str
```

## 12.2 Task

路径：`apps/runtime/app/domain/models/task.py`

```python
from pydantic import BaseModel
from typing import Literal, Optional

class Task(BaseModel):
    id: str
    type: Literal[
        "chat_reply",
        "proactive_observation",
        "screenshot_analysis",
        "web_search",
        "memory_extract",
        "tool_call",
        "reflection",
    ]
    status: Literal["queued", "running", "awaiting_user", "completed", "failed", "cancelled"]
    priority: int
    trigger_event_id: Optional[str] = None
    input_payload: dict
    output_payload: Optional[dict] = None
    created_at: str
    updated_at: str
```

## 12.3 Memory Item

路径：`apps/runtime/app/domain/models/memory.py`

```python
from pydantic import BaseModel
from typing import Literal, List

class MemoryItem(BaseModel):
    id: str
    kind: Literal["preference", "fact", "relationship", "habit", "task_context"]
    content: str
    tags: List[str] = []
    salience: float
    created_at: str
    last_used_at: str
```

## 13. 事件协议

系统内统一用事件驱动。

### 13.1 事件类型

建议放在：

- `packages/shared-schema/src/events.ts`
- `apps/runtime/app/domain/models/event.py`

核心事件：

- `window.changed`
- `clipboard.changed`
- `screenshot.captured`
- `user.message.received`
- `user.idle`
- `user.returned`
- `task.created`
- `task.updated`
- `assistant.message.created`
- `assistant.proactive.suggested`
- `tool.called`
- `tool.result`
- `memory.extracted`
- `config.updated`

### 13.2 Event 结构

```python
from pydantic import BaseModel
from typing import Literal

class DomainEvent(BaseModel):
    id: str
    type: str
    source: Literal["desktop", "runtime", "system", "tool", "model"]
    timestamp: str
    payload: dict
```

### 13.3 WebSocket 消息格式

桌面端和 runtime 通信用统一 envelope。

```json
{
  "type": "assistant.message.created",
  "requestId": "req_123",
  "timestamp": "2026-03-06T15:00:00Z",
  "payload": {
    "message": {
      "id": "msg_123",
      "role": "assistant",
      "source": "proactive",
      "parts": [
        { "type": "text", "text": "我看到你在看这段代码了，要我帮你解释一下吗？" }
      ]
    }
  }
}
```

## 14. API 设计

runtime server 提供两类接口：

- HTTP API
- WebSocket Stream

## 14.1 HTTP API 路由规划

### 14.1.1 健康检查

- `GET /api/v1/health`
- `GET /api/v1/health/providers`

### 14.1.2 聊天

- `POST /api/v1/chat/send`
- `POST /api/v1/chat/retry`
- `GET /api/v1/chat/history`

### 14.1.3 事件输入

- `POST /api/v1/events/window-changed`
- `POST /api/v1/events/clipboard-changed`
- `POST /api/v1/events/screenshot-captured`
- `POST /api/v1/events/user-idle`
- `POST /api/v1/events/user-returned`

### 14.1.4 任务管理

- `GET /api/v1/tasks`
- `GET /api/v1/tasks/{task_id}`
- `POST /api/v1/tasks/{task_id}/cancel`

### 14.1.5 记忆

- `GET /api/v1/memory/items`
- `POST /api/v1/memory/items`
- `DELETE /api/v1/memory/items/{memory_id}`

### 14.1.6 配置

- `GET /api/v1/config`
- `PUT /api/v1/config`
- `GET /api/v1/providers`
- `PUT /api/v1/providers/default`

### 14.1.7 调试

- `GET /api/v1/world-state`
- `GET /api/v1/debug/recent-events`
- `POST /api/v1/debug/run-screenshot-analysis`

## 14.2 关键接口定义

### 14.2.1 `POST /api/v1/chat/send`

请求：

```json
{
  "message": {
    "text": "帮我看看这个页面在说什么",
    "images": ["file:///tmp/capture.png"]
  },
  "client_context": {
    "activeWindowId": "window_123",
    "allowProactive": true
  }
}
```

响应：

```json
{
  "requestId": "req_123",
  "taskId": "task_123",
  "status": "accepted"
}
```

### 14.2.2 `POST /api/v1/events/screenshot-captured`

请求：

```json
{
  "imagePath": "/tmp/ayria/screenshot_001.png",
  "capturedAt": "2026-03-06T15:10:00Z",
  "activeWindow": {
    "appName": "Cursor",
    "windowTitle": "ayria-architecture-v1.md",
    "url": null
  }
}
```

响应：

```json
{
  "eventId": "evt_123",
  "accepted": true
}
```

### 14.2.3 `GET /api/v1/world-state`

响应：

```json
{
  "activeWindow": {
    "appName": "Chrome",
    "windowTitle": "GitHub - moeru-ai/airi",
    "url": "https://github.com/moeru-ai/airi"
  },
  "presence": {
    "mode": "observing",
    "userActive": true,
    "proactiveAllowed": true
  },
  "currentTaskHint": "用户在研究桌面存在系统架构"
}
```

## 14.3 WebSocket 规划

连接：

- `GET /api/v1/ws`

桌面端订阅：

- assistant message
- task status
- presence update
- world state patch
- tool execution events

建议消息类型：

- `presence.updated`
- `world_state.patched`
- `assistant.message.created`
- `assistant.typing`
- `task.updated`
- `tool.called`
- `tool.result`
- `debug.log`

## 15. 模型路由设计

路径：`apps/runtime/app/domain/services/routing_service.py`

### 15.1 模型角色

推荐定义三个逻辑角色：

- `capability_model`
- `persona_model`
- `fallback_model`

### 15.2 默认路由

#### 简单聊天

- 优先本地 `capability_model`
- 不调用工具
- 结果交给 `persona_model` 或同模型轻改写

#### 截图分析

- 优先本地视觉模型
- 输出结构化摘要
- 再交给人格层改写

#### 搜网/工具调用

- 优先本地能力模型
- 如果任务过复杂或多步失败，转云端 `fallback_model`

#### 主动观察

- 用小上下文、低频触发
- 输出应该短、轻、不打扰

### 15.3 路由输入

- 任务类型
- 是否含图像
- 当前上下文长度
- 本地模型健康状态
- 用户配置
- 最近失败次数

### 15.4 路由输出

```python
class RouteDecision(BaseModel):
    provider: str
    model: str
    use_tools: bool
    use_persona_rewrite: bool
    timeout_seconds: int
    reason: str
```

## 16. 工具系统设计

路径：`apps/runtime/app/providers/tools`

### 16.1 工具分类

v1 工具只做 5 类：

- `web_search`
- `read_file`
- `desktop_snapshot`
- `clipboard_read`
- `memory_lookup`

### 16.2 工具注册器

路径：`apps/runtime/app/providers/tools/registry.py`

职责：

- 统一注册工具
- 暴露 schema
- 管理超时和权限
- 提供工具执行审计

### 16.3 MCP Bridge

路径：`apps/runtime/app/providers/tools/mcp_bridge.py`

职责：

- 把 MCP server 暴露给 runtime 内部工具层
- 统一封装为本地 ToolSpec
- 未来可接入 `filesystem`, `browser`, `grep_app`, `context7`

### 16.4 ToolSpec 建议

```python
class ToolSpec(BaseModel):
    name: str
    description: str
    input_schema: dict
    requires_confirmation: bool = False
    timeout_seconds: int = 20
```

## 17. 截图和阅读机制

这是 `ayria` 的关键体验。

### 17.1 截图采样策略

v1 建议：

- 默认不做全时高频截图
- 只在以下情况采样：
  - 用户主动提问并附带当前上下文
  - 活跃窗口明显变化
  - 用户停留超过阈值
  - 用户显式触发“看看我现在在看什么”

### 17.2 桌面阅读流程

1. 桌面壳检测到窗口变化
2. Presence 层判断是否需要采样
3. 采样后调用 screenshot analyzer
4. 生成 `ScreenshotSummary`
5. 更新 `WorldState`
6. 决定是否主动发出一句话

### 17.3 主动打断规则

推荐规则：

- 不在用户高频输入时插话
- 不在全屏游戏时插话
- 不在黑名单应用时采样
- 同类主动提示设置冷却时间
- 默认只给“轻提示”，不长篇输出

## 18. 记忆系统设计

### 18.1 记忆分层

- `short-term`: 最近消息和最近世界状态
- `episodic`: 某次任务、某次互动、某次上下文摘要
- `long-term`: 用户偏好、关系事实、风格偏好

### 18.2 数据库存储

v1 直接用 `SQLite`。

表建议：

- `messages`
- `tasks`
- `events`
- `world_state_snapshots`
- `memory_items`
- `settings`
- `provider_configs`

### 18.3 记忆抽取时机

- 对话结束后
- 某任务完成后
- 用户显式说“记住这个”
- evaluator 判定为高价值信息时

### 18.4 不该记住的内容

- 临时敏感窗口内容
- 密码、验证码、token
- 金融敏感数据
- 黑名单应用截图内容

## 19. 配置系统设计

路径：`apps/runtime/app/core/config.py`

### 19.1 配置项

推荐配置模型：

```python
class AppConfig(BaseModel):
    default_provider: str
    capability_model: str
    persona_model: str | None
    fallback_provider: str | None
    fallback_model: str | None
    proactive_enabled: bool
    proactive_cooldown_seconds: int
    screenshot_enabled: bool
    screenshot_interval_seconds: int
    blacklisted_apps: list[str]
    persona_intensity: str
    memory_enabled: bool
```

### 19.2 存储位置

- 桌面端缓存一份 UI state
- runtime 持久化一份系统配置

## 20. 安全与隐私

### 20.1 总原则

- 默认本地优先
- 默认少存储
- 默认不自动执行危险动作
- 默认对敏感应用禁看

### 20.2 需要明确授权的动作

- 读取指定文件
- 调用外部网络搜索
- 使用云端模型发送截图
- 桌面自动操作

### 20.3 黑名单应用

默认黑名单建议：

- 密码管理器
- 银行和支付应用
- 系统设置中的敏感页面

## 21. 迭代计划

## 21.1 v0.1 骨架验证

目标：

- 桌面壳跑起来
- runtime server 跑起来
- 聊天 API 跑起来
- Ollama 模型联通
- 用户发消息得到回复

验收标准：

- 文本对话可用
- 本地模型可切换
- 聊天历史可持久化

## 21.2 v0.2 环境感知

目标：

- 活跃窗口检测
- 截图采样
- 基础 screenshot summary
- world state 页面

验收标准：

- 系统能知道用户当前大概在看什么
- 用户可在调试页看到世界状态

## 21.3 v0.3 主动存在感

目标：

- idle 检测
- 窗口变化触发
- 主动轻提示
- 冷却机制

验收标准：

- 主动消息不明显打扰
- 插话与当前场景相关

## 21.4 v0.4 工具和搜索

目标：

- web search
- clipboard 工具
- file reader
- MCP bridge 初版

验收标准：

- 能做轻量工具调用
- 工具过程可视化

## 21.5 v0.5 人格后置

目标：

- persona rewriter 上线
- persona intensity 上线
- 在聊天和工具任务中使用不同人格强度

验收标准：

- 角色感明显提升
- 不破坏结构化输出

## 21.6 v0.6 云端 fallback

目标：

- 复杂任务升级
- 云端 provider 接入
- 用户可配置哪些任务允许出云

验收标准：

- 本地失败后可回退
- 用户知道哪些内容被发送到云端

## 22. 任务拆分建议

建议按以下 Epic 建任务：

### Epic 1: 项目骨架

- monorepo 初始化
- desktop-app 初始化
- runtime-server 初始化
- shared-schema 初始化

### Epic 2: Chat 基础链路

- `/chat/send`
- WS 推送
- 消息存储
- 基础 UI

### Epic 3: Presence 基础链路

- 活跃窗口监听
- screenshot capture
- world state 存储

### Epic 4: Model Provider 抽象

- provider base
- ollama provider
- mlx provider
- cloud provider

### Epic 5: Tool 系统

- registry
- web search
- file reader
- clipboard
- MCP bridge

### Epic 6: Persona 系统

- persona prompt
- persona rewrite pipeline
- persona intensity setting

### Epic 7: Memory 系统

- memory item schema
- extraction pipeline
- lookup pipeline

### Epic 8: 安全与设置

- 黑名单应用
- 云端授权
- 隐私设置

## 23. 是否使用 LoRA

结论：v1 不建议。

原因：

- 风险大于收益
- 会影响工具纪律和视觉客观性
- 现阶段最大价值不在模型微调，而在系统架构和上下文设计

推荐顺序：

1. prompt + persona rewrite
2. 调整 world state 和 prompt policy
3. 观察是否仍缺少角色感
4. 再考虑人格层专用 LoRA

禁止项：

- 不要给主能力脑直接上强人格 LoRA
- 不要一开始做 tool-calling LoRA

## 24. 最终建议

最终建议如下：

- 把 `ayria` 明确定义为桌面存在系统，而不是聊天机器人项目
- 架构上采用 `Tauri + TypeScript` 外壳与 `Python runtime` 分离
- Runtime 内以自研 orchestrator 为主，`PydanticAI` 作为复杂任务执行子层
- 本地模型首选 `Qwen3.5-4B`，把 `Qwen3.5-9B` 作为更高配置项
- 人格后置，不在 v1 上 LoRA
- 把重点放在：
  - 世界状态
  - 事件驱动
  - 环境阅读
  - 主动时机控制
  - 安全边界

## 25. 附录：最小可运行链路

v1 的最小链路应当是：

1. 用户在桌面端输入一句话
2. desktop-app 调 `POST /api/v1/chat/send`
3. runtime 创建任务
4. orchestrator 收集最近消息和当前 world state
5. capability model 生成回答
6. persona rewriter 做轻度人格化
7. runtime 通过 WS 推 `assistant.message.created`
8. UI 渲染结果

环境感知链路应当是：

1. desktop-app 或 watcher 检测到窗口变化
2. 调 `POST /api/v1/events/window-changed`
3. 满足条件后采样截图
4. 调 `POST /api/v1/events/screenshot-captured`
5. runtime 调视觉模型生成摘要
6. world state 更新
7. 若满足主动规则，则发一个轻提示

这两条链路打通后，`ayria` 就已经具备了“本地桌面存在系统”的最小核心价值。
