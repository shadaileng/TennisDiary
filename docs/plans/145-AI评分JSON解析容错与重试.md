> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 145 |
> | 文档版本 | v1.0.0 |
> | 文档状态 | 🏁 已完成 |
> | 最后更新 | 2026-09-13 |
> | 对应功能/内容 | AI 评分 JSON 解析容错：json-repair 修复 + 单次重试 + 失败原始文本日志 |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-09-13 | v1.0.0 | 初版 |
>
> **关联文档**：[75-1：AI 评分代理接口](./75-1-AI评分代理接口.md) · [139：管线异常状态兜底与日志规范修正](./139-管线异常状态兜底与日志规范修正.md)

# 145 AI 评分 JSON 解析容错与重试

## 一、需求

### 1.1 故障现象

分析管线（`pipeline.py:268`）在 AI 评分步骤抛出 `JSONDecodeError`，导致整笔分析标记为 failed：

```
RuntimeError: AI: JSONDecodeError: Expecting ',' delimiter: line 13 column 27 (char 608)
```

根因：LLM 返回的 JSON 字符串中某处包含未转义引号或缺失逗号，导致 `json.loads` 失败。`extract_json` 当前逻辑为 **一次解析、失败即抛**，无修复或重试。

### 1.2 影响

- 用户上传视频后分析直接失败，需重新提交
- 无法从日志中看到 AI 原始响应文本，难以事后诊断
- LLM 输出随机性导致同类请求偶发成功、偶发失败

## 二、方案设计

### 2.1 架构决策

| # | 决策 | 理由 |
|---|------|------|
| D1 | 引入 `json-repair` 库修复 | 轻量纯 Python，可处理 LLM 常见的未转义引号、trailing comma、缺失逗号等；无需 C 扩展 |
| D2 | `analyze_swing` 失败后重试 1 次 | LLM 输出随机性，第二次大概率返回合法 JSON；重试成本可控（~3-5s） |
| D3 | 失败时记录原始 AI 文本 | 便于事后排查；使用 `logger.warning` 而非 `logger.error`（非致命） |
| D4 | 不改变管线 fail-fast 行为 | 重试仍失败则正常抛异常，由管线 139 的 `_force_fail` 兜底标记为 failed |

### 2.2 修改范围

| 文件 | 变更 |
|------|------|
| `server/pyproject.toml` | 添加 `json-repair` 依赖 |
| `server/app/services/ai_service.py` | `extract_json` 增加修复层 + 日志；`analyze_swing` 增加重试 |
| `server/tests/services/test_ai_service.py` | 新增 `extract_json` 单元测试（正常 / 可修复 / 不可修复） |

### 2.3 `extract_json` 改造

```python
def extract_json(text: str) -> dict:
    """从 AI 返回文本中提取 JSON 对象（容错修复 + 代码块剥离）"""
    # 1. 先尝试直接解析
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("AI 返回内容无法解析")
    raw = match.group(0)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # 2. json-repair 修复
    from json_repair import repair_json
    repaired = repair_json(raw, ensure_ascii=False)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass

    # 3. 记录原始文本后抛异常
    logger.warning("AI JSON 修复失败，原始文本前 500 字符: {}", text[:500])
    raise json.JSONDecodeError("AI 返回 JSON 无法修复", raw, 0)
```

### 2.4 `analyze_swing` 重试逻辑

```python
async def analyze_swing(...) -> dict:
    # ... 现有逻辑 ...
    text = await chat_vision(frames, prompt, ai_config, max_tokens=2500)
    try:
        report = extract_json(text)
    except (json.JSONDecodeError, ValueError):
        # 首次失败，重试一次
        logger.warning("AI JSON 首次解析失败，重试中...")
        text = await chat_vision(frames, prompt, ai_config, max_tokens=2500)
        report = extract_json(text)
    # ... 后续校验 ...
```

### 2.5 测试用例

| 用例 | 输入 | 预期 |
|------|------|------|
| 正常 JSON | 合法 JSON 字符串 | 直接返回 dict |
| 代码块包裹 | `` ```json\n{...}\n``` `` | 提取并解析成功 |
| 缺失逗号 | `{"a": 1 "b": 2}` | `json-repair` 修复后解析成功 |
| 未转义引号 | `{"summary": "他说"你好""}` | `json-repair` 修复后解析成功 |
| 不可修复 | 完全非法文本 | 抛出 `JSONDecodeError` |

## 三、实施步骤

| Step | 内容 | 涉及文件 |
|------|------|----------|
| 1 | `pyproject.toml` 添加 `json-repair` 依赖 + `uv sync` | `server/pyproject.toml` |
| 2 | `extract_json` 增加修复层 + 日志 | `server/app/services/ai_service.py` |
| 3 | `analyze_swing` 增加重试逻辑 | `server/app/services/ai_service.py` |
| 4 | 新增单元测试 | `server/tests/services/test_ai_service.py` |
| 5 | 运行 `ruff check` + `ruff format` + `pytest -m fast` 验证 | — |

## 四、验证要点

- [ ] `ruff check .` 无 error
- [ ] `ruff format .` 无变更
- [ ] `pytest -m fast` 全部通过
- [ ] 手动构造可修复 JSON → `extract_json` 修复成功
- [ ] 手动构造不可修复 JSON → 抛异常且日志含原始文本
