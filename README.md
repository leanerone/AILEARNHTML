# EAP 工程师能力测评 · 维护指南

零依赖前端 + 轻量后端（FastAPI + SQLite）的测评网站：**每次测评记录进数据库，可随时复盘看趋势、错题回顾、前后对比。**

## 快速开始

```bat
:: 方式一：双击 start.bat（自动装依赖 + 起服务 + 开浏览器）

:: 方式二：手动
cd skill-assessment
pip install -r requirements.txt
python server.py
:: 打开 http://127.0.0.1:8090
```

> 直接双击 `index.html` 仍可做题（浏览器本地暂存），但没有数据库——「保存本次记录」和「复盘」页会提示先启动服务。

## 文件说明

| 文件 | 作用 | 需要改吗 |
|---|---|---|
| `questions.js` | **全部题目、答案、解析、自评项** | ★ 加题改题只动这里 |
| `index.html` | 页面样式 + 交互逻辑（含复盘页） | 一般不动 |
| `server.py` | FastAPI + SQLite 后端（保存/查询/批改回填/删除） | 一般不动 |
| `assessment.db` | SQLite 数据库（首次启动自动生成） | 备份 = 直接复制 |
| `start.bat` / `requirements.txt` | 一键启动 / Python 依赖 | — |
| `README.md` | 本指南 | — |

## 日常使用与复盘流程

1. **做题**：打开 `http://127.0.0.1:8090`，做完点「完成」
2. **保存**：点「保存本次记录」→ 存入 `assessment.db`（客观题分数自动计算）
3. **批改**：点「复制答卷」回到 ZCode 对话粘贴，我逐题批改简答题并给反馈
4. **复盘**：进「复盘」页——
   - **趋势图**：每次记录的客观题得分率（蓝线），批改后回填的总得分率（绿线）
   - **记录列表**：时间、得分、用时、完成度、题库版本
   - **点进某次详情**：各板块得分 + 与上一次的涨跌对比、客观题错题回顾（附 `questions.js` 里的答案解析）、简答题自查（你的回答 vs 参考要点）、当时的自评快照
   - **回填批改结果**：把最终正确数和备注填进详情页，绿线就有了
5. **数据备份**：复制 `assessment.db` 一个文件即可；想清零就删掉它，重启自动重建空库

## 如何新增一道题

打开 `questions.js`，在对应 `sections` 的 `questions` 数组里加一条对象，保存刷新即可（进度条分母自动 +1）：

```js
{
  id: "q34",                    // 全局唯一
  type: "single",               // 题型，见下表
  stem: "题干内容？",
  options: ["选项A", "选项B", "选项C", "选项D"],   // short 题写 null
  answer: "c",                  // 见下表
  reference: "答案解析——复盘页错题回顾和简答题自查都会显示它",
},
```

### 题型与 answer 写法

| type | 含义 | options | answer |
|---|---|---|---|
| `single` | 单选 | 必填数组，选项数不限 | 一个字母，如 `"c"`（从 a 数起） |
| `multi` | 多选 | 必填数组 | 字母连写按序，如 `"ac"` |
| `short` | 简答 | 写 `null` | 写 `null`，评分要点写进 `reference` |

### 其他维护操作

- **新增板块**：复制整个 `{ id, tab, name, intro, questions: [...] }` 块，改 `id`（如 `"s8"`）
- **改自评/偏好**：编辑 `selfAssessment` / `metaQuestions` 数组
- **发新版题库**：改 `meta.version` 和 `meta.updatedAt`——每次答卷都会带版本号，复盘时可对比不同版本

## 数据库结构（一般不用动）

- `attempts`：一次测评一行——时间、题库版本、用时、完成度、客观题得分、批改后最终分、完整答卷 JSON
- `attempt_sections`：每行一个板块的得分（复盘页按它画对比）
- 接口：`POST/GET /api/attempts`、`GET/PATCH/DELETE /api/attempts/{id}`，想导出全部历史可用 sqlite3 命令行或 DB 工具直接读 `assessment.db`

## 放到内网给同事用

把整个 `skill-assessment` 文件夹拷到内网服务器（Windows/Linux 都行），跑 `python server.py`，IIS/nginx 反代 `8090` 端口即可。数据库就在服务器上的 `assessment.db`，大家的记录集中存放。若多人使用，建议后续给 POST 加个"姓名/备注"字段——在 `questions.js` 的 `metaQuestions` 里加一题即可，无需改后端。
