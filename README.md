# AIM 2627 Python Coursework —— 哨兵 Sentry 控制模块

> **全部题目、规范、评分、提交见 [题面.pdf](题面.pdf)。** 本 README 只讲怎么把环境跑起来；没在这里出现的规格细节，一律以题面为准。

## 1. 环境要求

- Python 3.8+，仅标准库（不允许第三方运行时依赖）；
- 开发工具只需 `pytest`（测试）与 `autopep8`（风格，CI 会检查）；
- VS Code 打开仓库会推荐安装 `ms-python.autopep8` 插件（`.vscode/extensions.json`），保存即格式化即可过风格检查。

## 2. 快速开始

```bash
# 1. 用 GitHub 的 Use this template 创建你自己的仓库，然后 clone
git clone https://github.com/<你的用户名>/<你的仓库>.git
cd <你的仓库>   # 直接在 main 分支上开发

# 创建虚拟环境

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 2. 装依赖
python -m pip install pytest autopep8

# 3. 启用 AI 会话归档钩子（课程要求，见下方第 3 节）
python -m pip install 'agent-session-commit[pre-commit]==0.1.3' -i https://pypi.org/simple
agent-session-commit install --pre-commit   # 交互选择你的 AI 助手与会话目录

# 4. 跑测试（刚到手：全部 skip，CI 是绿的）
python -m pytest

# 5. 看演示
python main.py

# 6. 打开 题面.pdf 读题，开始实现 src/main/__init__.py 里的 TODO
```

## 3. AI 会话归档（pre-commit）

本课程允许使用 AI，提交的 commit 需要携带 AI 会话归档作为透明化记录：每次 `git commit` 后，钩子会把新增会话自动 amend 进同一个提交（`.agent-sessions/bundles/`），不产生额外的归档提交。支持 Claude Code、OpenAI Codex CLI、GitHub Copilot CLI、Qoder、ZCode、Trae、Tencent CodeBuddy 等（完整名单见 [AgentLedger](https://github.com/Gentle-Lijie/AgentLedger)）。

- 配置是仓库本地的：每个 clone 运行一次 `agent-session-commit install --pre-commit`，方向键选择 agent、确认其会话目录即可；
- 不想用 TUI 可手动配置：`git config --local agent-session.agent claude`、`git config --local agent-session.source "<会话目录>"`，然后 `python -m pip install 'pre-commit>=3.2.0' && pre-commit install`；
- 归档是普通 Git 内容且会推送到公开仓库——不要在 AI 会话里粘贴令牌等敏感信息；
- 换了 agent 或目录就重跑一次安装命令；卸载：从 `.pre-commit-config.yaml` 移除该条目后重跑 `pre-commit install`。

## 4. 本地开发循环

- **写代码**：全部作业在 `src/main/__init__.py`，按题面各题规范补全每个标有 TODO 的函数；注释里标注了对应的题面主题，推荐顺序 Q1 → Q6。
- **跑测试**：`python -m pytest` —— 可见测试是规格书的一部分，未实现的函数自动 skip，实现一个、对应测试亮一个。本地全绿 ≠ 满分（见题面）。
- **看演示**：`python main.py`（等价于 `PYTHONPATH=src python -m main`），随实现进度逐段点亮，不进测试。
- **Q6 自测**：`python tools/run_seeds.py --q6`（200 张固定地图统计），单 seed 渲染 `python tools/run_seeds.py --q6 --seed <N> --render`，Bonus 模式 `python tools/run_seeds.py --bonus`。

## 5. 仓库结构（哪些能改）

| 路径 | 说明 | 能否修改 |
|---|---|---|
| `src/main/__init__.py` | 你的全部作业（TODO 所在） | ✅ |
| `README.md` | 仅末尾两个"你来写"小节 | ✅ |
| `题面.pdf` | 题面（唯一规格说明） | ❌ 勿改 |
| `src/main/legacy_patrol.py` | Q7 模块（与主体同步发布，修复其缺陷） | Q7 时 ✅ |
| `.pre-commit-config.yaml` | AI 会话归档钩子配置 | ❌ 勿改 |
| `src/tests/`、`tools/`、`.github/`、`conftest.py`、`pytest.ini`、`main.py` | 测试与基础设施 | ❌ 勿改 |

CI 只允许修改 `src/main/**`、`README.md` 与 `.agent-sessions/**`（AI 会话归档）——其余文件改了直接红；autopep8 `--diff` 非空即败。提交方式（push、问卷、commit 粒度）见题面"提交与验收"一节。

## 6. Q7 缺陷分析与修复记录

模块 `src/main/legacy_patrol.py` 内共埋有 6 处缺陷，排查与修复说明如下：

1. **`total_route_meters` 单位换算缺失**
   - 现象：计算出的路线米数比真实值偏大 100 倍。
   - 原因：`segment_length_cm` 返回值为厘米，累加到 `distance_in_meters` 时未除以 100 进行米制单位换算。
   - 修复：对每段厘米值做整除 100 后累加。

2. **`calibrate` 空值异常**
   - 现象：传入空列表或全非正数列表时抛出 `TypeError: unsupported operand type(s) for -: 'int' and 'NoneType'`。
   - 原因：当样本无正数时 `first_positive` 返回 `None`，后续执行 `s - baseline` 产生类型错误。
   - 修复：检测到 `baseline is None` 时直接返回 0。

3. **`summarize_events` 边界条件偏移**
   - 现象：边界 `id == max_id` 的事件被漏统。
   - 原因：过滤条件误写为 `e["id"] < max_id`，违反 docstring 中“不超过 max_id”的契约。
   - 修复：将比较符修改为 `e["id"] <= max_id`。

4. **`log` 函数可变默认参数**
   - 现象：多次不传 `history` 调用时日志历史产生跨调用污染。
   - 原因：默认形参 `history=[]` 在函数定义期创建，为跨调用的单一共享可变对象。
   - 修复：改为 `history=None`，在函数体内判断并初始化为空列表。

5. **`run_legacy_sim` 循环终止条件反转**
   - 现象：初始高体力调用在第 0 轮即异常退出。
   - 原因：终止条件误写为 `if stamina > 20: break`，反转了“体力 <= 20 时终止”的语义。
   - 修复：修正为 `if stamina <= 20: break`。

6. **`run_legacy_sim` 轮次计数自增丢失**
   - 现象：体力充足时死循环无法退出。
   - 原因：历史提交误删了 `round_ += 1`，导致循环轮号恒为 0 且永远小于 `rounds`。
   - 修复：在 while 循环每轮迭代末尾恢复 `round_ += 1`。

## 7. 模块设计与脱困策略说明

- **Q4 贪心策略**：在四邻域中筛选严格减少曼哈顿距离的无障碍格，坐标差绝对值较大轴优先；无可选候选时保持当前朝向。
- **Q6 脱困规则**：当贪心陷入局部凹形障碍死角时，触发 BFS 局部寻路脱困模式，计算到达曼哈顿距离更小格子的最短逃逸路径并按队列执行，完全规避局部震荡；经 200 张随机地图验证达到 100% 成功率、0 碰撞且平均步数比 1.04。
- **Bonus BFS 最短路**：采用标准双端队列广度优先搜索，保证全局最优路径与终止性。
