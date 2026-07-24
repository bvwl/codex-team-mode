# 在现有项目中接入 Team Mode

本文首先给出一套可以逐条发送给 Codex 的自然语言流程：从 GitHub 准备可信来源，分阶段安装 Agent 和 Skill，分析现有项目，最后提出具体开发需求。后半部分保留完整的审计规则、一次性安装提示词、升级和故障排查，供需要严格自动化或排查问题时使用。

多数用户应从“自然语言接入流程”开始，不需要先理解后面的 Git 树、哈希和冲突检查细节。推荐先做项目级接入；确认运行稳定后，再考虑个人级安装。

## 目录

- [接入后的目录结构](#接入后的目录结构)
- [自然语言接入流程：从 GitHub 到开始提需求](#自然语言接入流程从-github-到开始提需求)
- [接入前准备](#接入前准备)
- [兼容性与能力预检](#兼容性与能力预检)
- [高级方式：从本地仓库一次性接入](#高级方式从本地仓库一次性接入)
- [另一台机器：先从 GitHub 获取源仓库](#另一台机器先从-github-获取源仓库)
- [为目标项目生成 AGENTS.md](#为目标项目生成-agentsmd)
- [重启后验证 Skill 和 Agent](#重启后验证-skill-和-agent)
- [日常使用提示词](#日常使用提示词)
- [全栈开发提示词](#全栈开发提示词)
- [逆向分析提示词](#逆向分析提示词)
- [更新已接入的 Team Mode](#更新已接入的-team-mode)
- [个人级安装](#个人级安装)
- [故障排查](#故障排查)
- [最终检查清单](#最终检查清单)

## 接入后的目录结构

项目级接入完成后，目标项目应包含：

```text
your-project/
├── .agents/
│   └── skills/
│       └── team-mode/
│           ├── SKILL.md
│           ├── agents/openai.yaml
│           ├── references/
│           └── scripts/usage_by_model.py
├── .codex/
│   └── agents/
│       ├── Explorer.toml
│       ├── Executor.toml
│       ├── Complex Executor.toml
│       ├── Reviewer.toml
│       └── default.toml
└── AGENTS.md
```

三个配置面的职责不同：

- `.agents/skills/team-mode/`：可复用的 Team Mode 调度工作流。
- `.codex/agents/`：四个工作角色和一个派发哨兵的项目级配置。
- `AGENTS.md`：当前业务项目自己的目录、命令、工程规则和安全边界。

不要把三者合并成一个文件。

## 自然语言接入流程：从 GitHub 到开始提需求

不要一开始就让 Codex“创建一个叫 frontend 的 Agent”或直接粘贴一大段安装命令。当前 Team Mode 已经定义了四个工作角色；正常接入顺序是：

```text
从 GitHub 准备并审阅来源
→ 安装四个工作 Profile
→ 新建任务验证 Profile 选择器
→ 安装 default 哨兵和 Skill
→ 新建任务做最终验证
→ 只读分析现有项目
→ 提出具体开发需求
```

四个标准角色是 `Explorer`、`Executor`、`Complex Executor` 和 `Reviewer`。前端需求不需要预先创建 `frontend` Agent：简单、边界明确的前端修改可以交给 `Executor`，复杂但架构和验收标准已经明确的实现可以交给 `Complex Executor`。如果以后确实需要新的领域角色，应当作为 Team Mode 定制单独设计，同时修改 Skill 路由、Profile 清单和测试；只增加一个同名 TOML 不会自动扩展 Team Mode。

如果当前 Codex 任务提供任务创建与等待工具，推荐先使用下面的“AI 总控模式”：用户只发送一条总控提示词，由 AI 执行第 1～5 步并创建所需的新任务。后面的逐步提示词仍然保留，供工具不可用、发生阻塞或需要人工审计时使用。

### 推荐：让 AI 总控第 1～5 步

AI 可以替用户完成绝大多数操作，包括准备来源、检查 uv、安装文件、创建新的 Codex 任务、发送验证提示词、等待结果和汇总 trace。为了保留必要的安全边界，下面两件事仍可能需要用户亲自确认：

1. **信任 commit**：AI 可以检查和展示 remote、commit 与文件内容，但不能替用户作出“我信任这份代码”的安全决定。AI 必须暂停，等用户明确确认。
2. **严格只读权限**：AI 先检查任务创建工具的真实 Schema。如果该工具不能为新任务设置 sandbox/权限，AI 不能用提示词假装已经切换为只读；它必须让用户在最终验证任务的输入框下方点选 **Read-only**，然后只需回复“继续”。

把下面整段作为一条消息发送给 Codex。不要提前填写本地路径，也不要手工创建中间任务：

```text
请作为 Team Mode 项目接入总控，替我执行本文第 1～5 步。

目标：
- 完成来源审阅、两阶段项目级安装、跨任务运行时验证和最终审计。
- 不让我复制本地路径、commit、阶段提示词或手工创建中间任务。
- 只有“信任 commit”和工具无法代设的严格只读权限需要我确认。

开始前先做能力预检：
1. 检查当前任务是否具备查找项目、创建新任务、等待任务和读取任务结果的真实工具。
2. 检查任务创建工具的真实输入 Schema，确认它能否指定：
   - 当前保存的本地项目
   - local / 当前工作目录环境
   - sandbox 或权限模式
3. 新任务必须使用当前保存项目的 local 环境，直接复用当前工作目录。
   - 不创建 cloud task。
   - 不创建 projectless task。
   - 不创建隔离 worktree。
   - 原因是第一阶段安装的 .codex 和 .agents 文件可能尚未提交，默认分支 worktree 可能看不到它们。
4. 如果缺少创建或等待新任务的能力，停止自动编排，只告诉我一个当前必须手工完成的动作；不要假装已经刷新运行时。

总控流程：

阶段 A：准备并审阅来源
1. 在内部解析 PROJECT_ROOT、TEAM_MODE_SOURCE、UV_BIN 和 UV_PROJECT_DIR。
2. TEAM_MODE_SOURCE 使用 CODEX_HOME/sources/codex-team-mode。
3. 来源不存在时才允许 clone；已存在时不 pull、不 checkout、不 reset。
4. 检查预期 GitHub remote、完整 HEAD commit、工作区状态、安装树和 Profile。
5. 使用项目现有 uv 环境进行冻结、离线、不同步验证。
6. 报告候选完整 commit SHA 后暂停。
7. 明确问我是否信任该 commit；在我明确回复信任前不得安装。

阶段 B：第一阶段安装
1. 收到我的明确信任后，从受信 commit 的 Git blobs 安装四个工作 Profile：
   - Explorer
   - Executor
   - Complex Executor
   - Reviewer
2. 不安装 default.toml，不安装 Skill。
3. 冲突时零写入并一次性报告。
4. 安装并静态验证完成后，自动创建“Team Mode Profile 选择器验证”新任务。
5. 新任务必须使用独立的任务上下文；不得用 `spawn_agent`、`fork_turns` 或当前对话中的一条新消息冒充新任务。
6. 把本文第 3 步的只读验证要求作为新任务初始提示词，然后等待结果。

阶段 C：运行时选择器门槛
1. 从新任务的真实 spawn_agent Schema 判断是否存在 agent_type 或官方说明的等价 Profile 选择器。
2. 必须能明确选择：
   - Explorer
   - Executor
   - Complex Executor
   - Reviewer
3. 不得用 task_name、message、model、reasoning_effort 或模型自述代替。
4. 如果失败：
   - 停止全部后续安装。
   - 不安装 default.toml 或 Skill。
   - 报告失败任务、真实 Schema、项目是否可信和下一步。
5. 只有选择器门槛通过时才继续。

阶段 D：第二阶段安装
1. 重新核对来源 remote、HEAD、受信 commit 和工作区。
2. 从受信 commit 的 Git blobs 安装：
   - agents/default.toml → PROJECT_ROOT/.codex/agents/default.toml
   - 完整 skills/team-mode 树 → PROJECT_ROOT/.agents/skills/team-mode
3. 不覆盖不同内容，不修改四个工作 Profile、AGENTS.md 或业务代码。
4. 验证 Skill 文件树和五个 Profile。

阶段 E：最终激活验证
1. 自动创建“Team Mode 最终激活验证”新任务，仍使用当前保存项目的 local 环境。
2. 先让新任务只检查：
   - $team-mode 是否可发现
   - 五个 Profile 是否存在并可解析
   - spawn_agent 是否能选择四个工作 Profile
   - 父任务当前实际 sandbox
3. 在确认父任务严格 read-only 以前：
   - 不启动 Explorer。
   - 不联网。
   - 不写文件。
4. 如果任务创建工具可以明确设置 read-only，就直接使用该字段，并从 trace 复核。
5. 如果任务创建工具没有权限或 sandbox 字段：
   - 暂停最终动态验证。
   - 告诉我打开刚创建的最终验证任务。
   - 让我在输入框下方选择 Read-only，然后回复“继续”。
   - 不得把自然语言中的“只读”当作实际权限。
6. 严格只读确认后，只启动一个最小 Explorer：
   - agent_type="Explorer"
   - fork_turns="none"
   - 只读取项目根目录一级结构
   - 不联网、不写文件、不启动后代 Agent
7. 从真实 session trace 核对：
   - agent_role
   - model
   - effort
   - effective sandbox
   - depth
8. 运行 usage_by_model.py --task-id current --by-agent --by-session --audit-routing。
9. 等待最终验证任务完成，并在总控任务中汇总结果。

全程约束：
- 不删除文件。
- 不运行批量删除或递归删除。
- 不提交、不推送。
- 不修改业务代码、AGENTS.md、pyproject.toml、uv.lock 或 .venv。
- 不运行 uv sync、uv lock、uv python install。
- 不在任何门槛失败后继续下一阶段。
- 不根据子 Agent 自述判断运行时角色或权限。
- 每次创建新任务后都报告任务名称和状态。
```

#### AI 总控模式的预期交互

正常情况下，用户只需要参与下面两次：

```text
AI：来源已审阅，候选 commit 是 <完整 SHA>。是否明确信任并继续？
用户：我信任这个 commit，继续。

AI：最终验证任务已创建，但任务创建工具不能代设严格只读权限。
    请打开“Team Mode 最终激活验证”，在输入框下方选择 Read-only，然后回复“继续”。
用户：继续。
```

如果新任务默认已经是严格只读，第二次人工操作也可以省略。AI 必须以真实任务 Schema 和 trace 为准，不能仅根据默认配置或文字提示推断。

### 手工备用：逐步发送第 1～5 步

只有 AI 总控预检发现缺少任务创建/等待能力，或某个阶段需要用户排障时，才需要使用下面的逐步提示词。下面每个代码块都是一条独立消息；等上一条完成并检查结果后，再发送下一条，不要把所有消息一次性合并。

### 小白先看：什么叫“新建任务”

这里的“任务”是同一个项目中的一段独立对话。新任务会继续使用同一个项目目录，但不会沿用旧对话已经固定的运行时工具 Schema。安装新的 Skill 或 Agent Profile 后，必须真的打开一段新对话，不能只在原对话中发送“请重新开始”“刷新配置”或下一步提示词。

下面这些操作**不算**新建任务：

- 继续在当前输入框发送下一条消息。
- 在当前对话中输入“新建任务”或“重新加载配置”。
- 刷新当前消息页面后继续原对话。
- 使用“继续”“恢复”或 `/resume` 打开原对话。
- 打开不属于当前本地项目的 Quick chat。

#### Codex 桌面端：在同一个项目中新建任务

不同版本的按钮文字可能显示为 **New chat**、**新建任务**、**新建聊天**或 `+`，但操作目标相同：

1. 在左侧栏找到当前业务项目，确认项目名称或目录就是刚才安装 Team Mode 的项目。
2. 在该项目下点击 **New chat**、**新建任务**或 `+`。如果界面要求选择目录，仍然选择同一个业务项目。
3. 确认打开的是一个空白对话：旧任务的聊天记录不应出现在新对话正文中，左侧栏应出现一个新的聊天条目。
4. 不要用 **Quick chat** 代替 **New chat**。当前官方快捷键文档把它们列为两种不同操作；为了确保新任务仍附着到当前本地项目，应使用 **New chat**，并选择同一项目的 **Local** 环境。
5. 把下一步验证提示词粘贴到这个空白任务中，而不是回到旧任务继续发送。

如果左侧栏被隐藏，先展开左侧栏再操作。项目可以包含多个任务；“新建任务”不会复制项目文件，也不会创建新的 Git 仓库。参见 [ChatGPT desktop app commands](https://learn.chatgpt.com/docs/reference/commands.md) 和 [Codex environments](https://learn.chatgpt.com/docs/environments/modes.md)。

#### 怎样选择严格只读权限

最终激活验证会启动一个最小 Explorer。Explorer 的 TOML 虽然写了 `sandbox_mode = "read-only"`，但子 Agent 仍会继承父任务当前的实时权限，所以必须先把父任务设置为严格只读。

在 Codex 桌面端：

1. 找到消息输入框下方的权限或 sandbox 控件。
2. 选择明确标示为 **Read-only**、**只读**或说明“不能写入项目”的模式。
3. 不要把 **Ask for approval**、**Approve for me / Auto-review** 或 **Full access** 当成严格只读；它们控制审批方式，不一定把项目变成不可写。
4. 新建验证任务后，在发送第 5 步提示词前，再检查一次新任务输入框下方的权限模式。不要假设旧任务的选择一定会自动继承。
5. 先让 Codex 报告父任务的实际 sandbox；只有 trace 显示 `read-only` 才算通过。

OpenAI 当前文档说明，桌面端权限控件位于输入框下方，CLI 使用 `/permissions`；子 Agent 会继承父任务为当前操作选择的权限模式。参见 [Sandbox](https://learn.chatgpt.com/docs/sandboxing.md) 和 [Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents.md#approvals-and-sandbox-controls)。

如果桌面端没有提供明确的只读选项，不要猜。可以改用 Codex CLI：

```text
1. 从业务项目目录启动 Codex。
2. 输入 /permissions，选择 Read-only。
3. 输入 /new，创建同一项目中的新任务。
4. 粘贴本文第 3 步或第 5 步的验证提示词。
```

如果桌面端和 CLI 都不能选择只读权限，只能完成静态配置检查，不能宣称动态只读验证通过。

#### 完整操作案例：两次安装、两次新建任务

假设你已经在“任务 A”中完成来源审阅和第一阶段安装：

```text
任务 A
  第 1 步：审阅 GitHub 来源
  第 2 步：安装四个工作 Profile
  到这里停止，不要在任务 A 中继续第 3 步
```

接下来：

```text
新建任务 B（仍然选择同一个业务项目）
  发送第 3 步提示词
  检查真实 spawn_agent Schema

  如果没有 agent_type：
    立即停止
    不安装 default.toml
    不安装 Skill

  如果 agent_type 能选择四个工作 Profile：
    在任务 B 中执行第 4 步
    安装 default 哨兵和 Skill
```

第二阶段安装完成后：

```text
新建任务 C（仍然选择同一个业务项目）
  在任务 C 的输入框下方选择严格 Read-only
  发送第 5 步提示词
  先检查 Skill、五个 Profile、agent_type 和父任务 sandbox
  四项全部通过后，才允许启动最小 Explorer
```

可以用下面的现象快速定位问题：

| 现象 | 通常表示什么 | 应该怎么做 |
| --- | --- | --- |
| 文件存在，但 `spawn_agent` 没有 `agent_type` | 仍在旧任务，项目配置未加载，或当前任务环境没有该能力 | 重启 Codex 并在同一项目中新建任务；仍然缺失时停止动态验证 |
| `$team-mode` 可发现，但四个 Profile 不可选 | Skill 已加载，不代表 Agent Profile 已加载 | 检查项目信任状态和真实工具 Schema |
| trace 显示 `workspace-write` | 父任务不是严格只读 | 新建父任务后，在该任务中选择 Read-only 再发送验证提示词；不要只依赖 Explorer.toml |
| 左侧栏仍是原聊天记录，输入框继续原上下文 | 没有真正新建任务 | 回到项目，点击 New chat / 新建任务 / `+` |
| `usage_by_model.py` 仍报告原来的根 session | 验证仍发生在旧任务 | 新建任务后重新执行验证 |

### 本文采用的 uv 项目约定

Python 项目创建时统一使用 uv，并默认固定 Python 3.14：

```bash
uv python install 3.14
uv init myproject
cd myproject
uv python pin 3.14
uv venv
```

这些是“创建新业务项目”时执行一次的初始化命令，不属于 Team Mode 安装步骤。把 Team Mode 接入已经存在的项目时：

- 不重复运行 `uv init`、`uv python install`、`uv python pin` 或 `uv venv`。
- 读取现有 `.python-version`、`pyproject.toml`、`uv.lock` 和 `.venv`，以项目已经固定的版本和环境为准。
- 大多数项目会固定并解析为 Python 3.14；如果个别项目声明其他版本，以该项目自己的配置为准，但 Team Mode 管理脚本要求不低于 Python 3.11。
- 第三方依赖统一声明在 `pyproject.toml`，`uv.lock` 是由 uv 维护的锁定结果。
- 新增运行时依赖使用 `uv add <package>`，新增开发依赖使用 `uv add --dev <package>`，移除依赖使用 `uv remove <package>`。
- 不使用 `pip install`、`python -m pip` 或新建 `requirements.txt` 绕过 `pyproject.toml`。
- 不手工编辑 `uv.lock`。只有用户需求明确授权修改依赖时，才允许通过 uv 更新 `pyproject.toml`、`uv.lock` 和项目环境。
- Team Mode 的安装、静态验证和审计脚本不需要任何第三方包，因此只使用现有 uv 环境，并通过 `--frozen --no-sync --no-python-downloads --offline --no-env-file` 防止安装过程改变依赖状态。

### 第 1 步：让 Codex 从 GitHub 准备并审阅来源

先在 Codex 中打开真正要接入的业务项目，然后直接发送下面的消息。它不包含个人目录或必须手工替换的来源路径：Codex 会把来源仓库放在自己的统一源码缓存 `CODEX_HOME/sources/codex-team-mode`，不会放进业务项目或业务项目的同级目录。这里使用的是跨平台逻辑位置，macOS、Linux 和 Windows 都必须通过当前操作系统的原生路径规则解析，不能把斜杠、盘符或某台机器的用户目录硬编码进去。首次不存在时才从 GitHub 克隆，后续项目复用同一份来源。它不得扫描、列出或猜测其他用户目录，也不得在回复中显示用户主目录的完整绝对路径。

```text
我想把 GitHub 上的 Team Mode 接入当前项目。现在只准备和审阅安装来源，不安装 Skill 或 Agent，不修改当前项目，不启动子 Agent。

GitHub 仓库：
https://github.com/bvwl/codex-team-mode.git

请执行：
1. 在内部确认当前业务项目根目录并记为 PROJECT_ROOT；回复中只报告“已识别”或阻塞原因，不显示完整绝对路径。
2. 确定本地来源目录：
   - 如果我在当前任务中已经明确提供 TEAM_MODE_SOURCE，使用该路径。
   - 否则先解析 Codex 配置根目录：优先使用已经设置且非空的 CODEX_HOME；未设置时使用当前用户主目录下的 .codex。
   - macOS/Linux 的默认语义是 $HOME/.codex；Windows 的默认语义是 %USERPROFILE%\.codex。它们只是说明默认规则，不得直接作为未经展开的字符串传给文件或 Git 命令。
   - 使用当前运行时的原生路径 API 拼接 sources 和 codex-team-mode，规范化为绝对路径后记为 TEAM_MODE_SOURCE；不要手工拼接 / 或 \，不要假设盘符，也不要调用只适用于某一种 Shell 的变量展开语法。
   - TEAM_MODE_SOURCE 的跨平台逻辑位置记作 CODEX_HOME/sources/codex-team-mode。它必须位于业务项目之外，不得放入 PROJECT_ROOT 或 PROJECT_ROOT 的同级目录。
   - 在内部解析并保存真实绝对路径，供后续步骤复用；回复中只写逻辑位置 CODEX_HOME/sources/codex-team-mode，不显示用户主目录或完整绝对路径。
   - 不扫描、搜索或列出其他用户目录。
3. 检查 TEAM_MODE_SOURCE 是否已经存在：
   - 不存在：我授权你使用当前平台的原生文件 API，只创建缺失的 CODEX_HOME/sources 目录，并以独立参数把精确的 TEAM_MODE_SOURCE 路径传给 git clone，从上述 GitHub URL 克隆仓库。
   - 已存在且是 Git 仓库：不 pull、不 checkout、不 reset、不覆盖；只检查它是否为预期仓库。
   - 已存在但不是 Git 仓库、是符号链接或 Windows 重解析点，或者 remote 不是预期 URL：停止，不覆盖、不移动、不删除任何内容。
4. 报告来源仓库的 remote、完整 HEAD commit SHA 和完整工作区状态。
5. 检查 HEAD 中的 skills/team-mode、scripts/manage_profiles.py 和 agents/*.toml，说明它们分别会安装什么。
6. 检查当前任务真实的 spawn_agent 输入 Schema，列出全部字段；不要启动子 Agent。
7. 检查业务项目是否使用 uv：
   - 查找 pyproject.toml、uv.lock 和 .python-version，确定真实的 UV_PROJECT_DIR。
   - 在内部解析 uv 可执行文件的绝对路径并记为 UV_BIN，不在回复中显示完整路径。
   - 从 .python-version 和 pyproject.toml 的 requires-python 读取项目声明的 Python 版本。
   - 确认项目 uv 环境已经初始化，然后使用 uv run --project UV_PROJECT_DIR 执行 Python；不要让用户手工选择系统 Python。
   - 使用 --frozen、--no-sync、--no-python-downloads、--offline 和 --no-env-file，保证检查不会同步依赖、更新锁文件、下载 Python 或加载 .env。
   - 只检查现有环境，不运行 uv sync、uv lock、uv python install，也不创建 .venv。
   - 如果 uv 环境尚未初始化，报告缺失并等待我处理，不要回退到系统 Python。
   - 报告 uv 版本、项目环境是否已识别以及 uv run 实际解析的 Python 版本；UV_BIN、UV_PROJECT_DIR 和 Python 的完整路径只在任务内部保留。我的项目大多数会解析为 Python 3.14；以每个项目的真实声明和 uv 结果为准。
8. 最后只报告：
   - 当前项目是否已识别，不显示它的完整绝对路径
   - TEAM_MODE_SOURCE 的逻辑位置 CODEX_HOME/sources/codex-team-mode，不显示完整绝对路径
   - 来源状态：本次新克隆、此前已存在，或被冲突阻塞
   - remote
   - 候选完整 commit SHA
   - 工作区是否干净
   - spawn_agent 的真实字段
   - uv 版本，以及 UV_BIN 和 UV_PROJECT_DIR 是否已识别，不显示完整路径
   - uv run 实际解析的 Python 版本，不显示完整解释器路径
   - 需要我审阅和确认的事项

不要把检测到的 commit 自动视为我已经信任。等待我明确确认后再继续。
```

这一步只允许在统一源码缓存 `CODEX_HOME/sources/codex-team-mode` 不存在时使用平台原生路径规则创建其缺失的父目录并执行一次 Git clone，不允许修改业务项目，也不允许为了寻找旧克隆而扫描用户目录。使用统一缓存可以让多个业务项目复用同一份受审阅来源，并避免嵌套 Git 仓库、业务仓库污染和重复克隆。检查输出中的来源状态、remote、完整 commit SHA 和工作区状态。只有你确实审阅并信任该 commit 后，才继续。

第一步只有同时报告了明确的来源状态、逻辑位置 `CODEX_HOME/sources/codex-team-mode`、预期 remote、完整 commit SHA 和来源工作区状态，才算完成。如果任何一项是“未指定”或“未检查”，不要进入第二步；让 Codex 继续完成第一步的按需克隆或来源检查。Codex 必须在任务内部保留 `PROJECT_ROOT`、`TEAM_MODE_SOURCE`、`UV_BIN` 和 `UV_PROJECT_DIR` 的真实绝对路径供下一步使用，但不需要把这些隐私路径显示出来。

### 第 2 步：确认 commit，只安装四个工作 Profile

这里只需要把第一步报告的完整 commit SHA 填入下面的消息。真正需要用户作出的安全决定只有一项：是否审阅并信任这个 commit。`PROJECT_ROOT`、`TEAM_MODE_SOURCE`、`UV_BIN` 和 `UV_PROJECT_DIR` 由 Codex 复用第一步在任务内部解析的真实值，不要求用户复制或暴露本地路径；四个 Agent 的名称、模型和指令来自已确认 commit，也不需要用户重新定义。

```text
我已经审阅并信任下面这个 Team Mode 来源，允许开始第一阶段项目级安装。

EXPECTED_TEAM_MODE_REMOTE：
https://github.com/bvwl/codex-team-mode.git

EXPECTED_TEAM_MODE_COMMIT：
<已经审阅并信任的完整 40 位 commit SHA>

复用第一步在当前任务内部解析的 PROJECT_ROOT、TEAM_MODE_SOURCE、UV_BIN 和 UV_PROJECT_DIR，不要让我重新填写，也不要在回复中显示它们的完整绝对路径。如果当前任务没有保留其中任何一个值，停止安装并重新执行第一步，不要猜测路径。

第一阶段只安装四个工作 Profile：
- Explorer
- Executor
- Complex Executor
- Reviewer

要求：
1. 重新核对来源 remote、HEAD、完整工作区状态和 EXPECTED_TEAM_MODE_COMMIT。
2. 所有安装内容只能读取自该 commit 的 Git blob，不读取未跟踪、被忽略或未提交的工作树内容。
3. 安装目标仅限 PROJECT_ROOT/.codex/agents/ 下上述四个 TOML。
4. 不安装 default.toml。
5. 不安装 .agents/skills/team-mode。
6. 不修改 AGENTS.md 或业务代码。
7. 不覆盖内容不同的同名文件；发现冲突时保持零写入并一次性报告。
8. 不删除任何文件，不提交，不推送，不启动子 Agent。
9. 验证 UV_PROJECT_DIR 中存在 pyproject.toml 和 uv.lock，确认项目 uv 环境已经初始化，并运行：
   UV_BIN run --project UV_PROJECT_DIR --frozen --no-sync --no-python-downloads --offline --no-env-file python -I <检查命令>
10. uv run 实际解析的 Python 必须符合 .python-version 和 requires-python；项目声明或解析为 3.14 时直接使用 3.14，不得改用系统 3.11。
11. 不运行 uv sync、uv lock、uv python install，不创建或修改 .venv，不下载 Python，不修改 uv.lock 或业务依赖。
12. 写入前完成全部只读预检；只有来源、uv 项目环境、目标路径和项目可信状态都通过后才能写入。
13. 完成后解析四个 TOML，报告 name、model、model_reasoning_effort、sandbox_mode、安装路径和是否需要新建任务。
```

第一阶段故意不安装 `default.toml` 和 Skill。这样即使当前任务还没有显式 Profile 选择器，也不会让所有普通子 Agent 派发落入拒绝工作的哨兵，同时也不会让尚未就绪的 Skill 自动开始调度。

### 第 3 步：新建任务，验证四个工作 Profile

第一阶段成功后，在同一个业务项目中新建 Codex 任务，再发送：

如果不知道怎样新建任务，先按上面的“小白先看：什么叫‘新建任务’”完成桌面端或 CLI 操作。不要在完成第一阶段安装的旧任务中直接发送下面的提示词。

```text
请只读验证当前项目的四个 Team Mode 工作 Profile，不修改文件，不启动子 Agent。

1. 检查并解析：
   - .codex/agents/Explorer.toml
   - .codex/agents/Executor.toml
   - .codex/agents/Complex Executor.toml
   - .codex/agents/Reviewer.toml
2. 检查当前任务真实的 spawn_agent 输入 Schema，列出全部字段。
3. 验证是否存在能够明确选择自定义 Profile 的字段；当前预期字段名为 agent_type。
4. 验证该字段能否明确选择：
   - Explorer
   - Executor
   - Complex Executor
   - Reviewer
5. 不要用 task_name、message、model、reasoning_effort 或模型自述代替 Profile 选择器。
6. 如果四个 Profile 不能被明确选择，停止并报告“当前任务工具面尚未满足 Team Mode 激活条件”；不要安装 default.toml 或 Skill。
7. 如果全部可选，报告“可以进行第二阶段安装”，但本次仍不要写入。
```

能读到四个 TOML 不等于运行时已经加载它们。只有新任务的真实工具 Schema 能明确选择四个 Profile，才进入下一步。

### 第 4 步：安装 `default` 哨兵和 Team Mode Skill

第 3 步通过后，在同一任务中发送：

```text
四个 Team Mode 工作 Profile 已通过当前任务的运行时选择验证。现在执行第二阶段安装。

EXPECTED_TEAM_MODE_REMOTE：
https://github.com/bvwl/codex-team-mode.git

EXPECTED_TEAM_MODE_COMMIT：
<已经审阅并信任的完整 40 位 commit SHA>

在内部重新识别 PROJECT_ROOT、UV_BIN 和 UV_PROJECT_DIR，并把 TEAM_MODE_SOURCE 解析为 CODEX_HOME/sources/codex-team-mode。该来源必须已经存在；本阶段不 clone、不 pull、不 checkout、不 reset。不要让我填写本地路径，也不要在回复中显示完整绝对路径。任一值无法可靠解析时停止安装。

只允许安装：
1. EXPECTED_TEAM_MODE_COMMIT 中的 agents/default.toml
   → PROJECT_ROOT/.codex/agents/default.toml
2. EXPECTED_TEAM_MODE_COMMIT 中完整的 skills/team-mode Git 树
   → PROJECT_ROOT/.agents/skills/team-mode

要求：
- 再次核对 remote、HEAD、工作区状态和 commit。
- 内容只读取自该 commit 的 Git blob。
- 不覆盖内容不同的同名路径。
- 发现任一冲突时保持零写入并一次性报告。
- 不修改四个已经安装的工作 Profile、AGENTS.md 或业务代码。
- 使用 UV_BIN run --project UV_PROJECT_DIR --frozen --no-sync --no-python-downloads --offline --no-env-file python 做验证；不运行 uv sync、uv lock、uv python install，不创建或修改 .venv。
- 不删除文件，不提交，不推送，不启动子 Agent。
- 完成后验证 Skill 文件树和五个 Profile，并报告是否需要新建任务。
```

### 第 5 步：新建任务，做最终激活验证

第二阶段成功后再次新建任务，再发送：

新建任务后、发送下面的验证提示词前，还要在这个新任务中把父任务权限设置为严格只读。只在输入文字中写“不要修改文件”不等于切换了 sandbox；必须使用客户端权限控件或 CLI `/permissions`，并以 trace 中的实际 `read-only` 为准。

```text
请验证当前项目的 Team Mode 已完整激活。先只读验证，不修改业务文件。

1. 确认 $team-mode Skill 可发现。
2. 确认四个工作 Profile 和 default 哨兵都存在且能解析。
3. 确认 spawn_agent 能明确选择 Explorer、Executor、Complex Executor 和 Reviewer。
4. 先确认父任务处于严格只读权限模式。
5. 只有前四项都通过时，才启动一个最小 Explorer：
   - agent_type="Explorer"
   - fork_turns="none"
   - 只读取项目根目录一级结构
   - 不联网、不写文件、不启动后代 Agent
6. 从真实 session trace 核对 agent_role、model、effort、effective sandbox 和 depth，不依赖子 Agent 自述。
7. 运行 usage_by_model.py --audit-routing，并汇总所有验证结果。
8. 任一项失败时停止动态验证，准确报告失败层级和下一步。
```

如果当前任务仍然没有明确的 Profile 选择器，改变自然语言写法不能凭空增加这个运行时字段。此时保留四个工作 Profile 即可，不安装哨兵和 Skill，换到提供所需工具能力的 Codex 任务环境后再从第 3 步继续。

### 第 6 步：让 Team Mode 先分析现有项目

安装和激活验证完成后，不要立即要求它修改代码。先让它建立项目上下文：

```text
使用 $team-mode 对当前项目做一次只读项目分析，暂时不要修改任何文件。

目标：
- 让我知道这个项目是什么、怎样运行、怎样验证，以及后续开发需求应当提供哪些信息。

请分析：
1. 项目目录、主要模块和入口。
2. 前端、后端、数据库、任务队列、部署和基础设施的位置。
3. 语言、框架、包管理器、Python/Node 版本和锁文件。
   - Python 项目重点核对 uv 版本、.python-version、pyproject.toml、uv.lock、现有 .venv 和 uv run 实际解析的 Python。
   - 从 pyproject.toml 区分运行时依赖、开发依赖和依赖组，不从 pip freeze 或临时环境反推项目声明。
4. 已有的构建、启动、测试、Lint、格式化、类型检查和集成测试命令；Python 命令优先报告对应的 uv run 形式。
5. 配置文件、环境变量示例、生成文件、第三方代码和禁止修改区域。
6. 当前 AGENTS.md 已有规则；如果不存在，提出建议内容，但先不要创建。
7. 适合 Explorer、Executor、Complex Executor 和 Reviewer 的项目边界。
8. 仍需我确认的产品、架构、安全、数据和部署问题。

只在确有必要时使用最小数量的只读 Explorer。最终由主线程给出：
- 项目概览
- 可验证命令
- 风险和未知项
- 建议的 AGENTS.md 大纲
- 我以后提开发需求时应提供的信息
```

确认分析结果后，再使用本文后面的独立提示词创建或补充 `AGENTS.md`。

### 第 7 步：用自然语言提出真正的开发需求

提需求时不需要自己选择 Agent。描述目标、现状、边界和验收标准，让主线程决定是否需要 Team Mode：

```text
使用 $team-mode 完成下面的需求。先阅读当前项目的 AGENTS.md 和已有项目分析，再决定是否需要子 Agent；不要为了凑角色而派发。

需求目标：
<最终想得到什么>

当前行为：
<现在发生什么；如果是新功能，写“当前不存在”>

期望行为：
<用户完成什么操作后，应看到什么结果>

范围：
- 允许修改：<目录、模块或功能>
- 不允许修改：<接口、数据库、部署、其他页面等>
- 第三方依赖：<允许新增哪些依赖；不允许新增时明确写“不得修改 pyproject.toml、uv.lock 或项目环境”>

验收标准：
1. <可观察结果一>
2. <可观察结果二>
3. <必须通过的测试、构建或检查>

补充材料：
<设计图、接口文档、错误日志、样例数据或相关文件；没有则写“无”>

工作方式：
1. 先核对需求与项目现状，列出真正会影响实现的未知项。
2. 如果存在会改变产品、架构、安全或数据行为的关键选择，先问我，不要自行决定。
3. 范围明确后再给出简短实施计划并执行。
4. 只有需求明确授权时才能使用 uv add、uv add --dev 或 uv remove 修改依赖；不得直接使用 pip、手工编辑 uv.lock 或创建 requirements.txt。
5. 所有修改完成后使用项目的 uv 环境运行与改动匹配的验证。
6. 最终报告修改内容、pyproject.toml/uv.lock 是否变化、验证结果、残余风险和需要我手动确认的事项。
```

例如前端页面需求可以这样写：

```text
使用 $team-mode 在现有前端中增加“任务运行记录”页面。

当前行为：
项目已经有任务列表和 GET /api/tasks/{id}/runs 接口，但没有运行记录页面。

期望行为：
用户从任务详情点击“运行记录”后，能够看到开始时间、状态、耗时和错误摘要，并能按状态筛选。

范围：
- 允许修改 frontend 中的路由、页面、现有 API client 和对应测试。
- 不允许修改后端接口、数据库结构、认证和部署配置。
- 不新增第三方依赖，不修改 pyproject.toml、uv.lock 或项目 uv 环境。

验收标准：
1. 使用项目现有组件和样式体系。
2. 包含加载、空数据、错误和正常状态。
3. 键盘可以操作筛选控件，并有可读的无障碍标签。
4. 通过前端现有的类型检查、测试和构建。

先确认实际文件、接口类型和验证命令；确认范围后再实现。
```

## 接入前准备

接入前确认：

1. 当前 Codex 工作目录是目标项目根目录。Git 仓库以仓库根目录为准；非 Git 项目使用用户明确指定的项目目录，不因为缺少 `.git` 自动拒绝接入。
2. 目标项目已经被 Codex 标记为可信；不可信项目可能忽略项目级 `.codex/` 配置。如果当前客户端无法确认或设置可信状态，停止并让用户在客户端中完成信任确认。
3. 可以访问 Team Mode 的统一源码缓存：

   ```text
   CODEX_HOME/sources/codex-team-mode
   ```

   它位于 Codex 配置根目录中，不属于业务项目。若该路径不存在，按“第 1 步”从 GitHub 自动克隆；若已存在，只读核对，不自动更新。来源 GitHub 为：

   ```text
   https://github.com/bvwl/codex-team-mode
   ```

4. 如果业务项目使用 uv，记录包含 `pyproject.toml` 和 `uv.lock` 的真实项目目录，记为 `UV_PROJECT_DIR`。仓库根目录和 uv 项目目录可能不同，例如后端位于仓库的 `background/` 子目录。
5. 优先使用已经初始化的 uv 项目环境：
   - 记录 uv 版本和 uv 可执行文件的绝对路径，记为 `UV_BIN`。
   - 确认 `UV_PROJECT_DIR/.venv/` 或项目明确配置的 uv 环境已经存在。
   - 同时读取 `.python-version` 和 `pyproject.toml` 的 `requires-python`；把它们作为业务项目版本约束。
   - 统一通过 `UV_BIN run --project UV_PROJECT_DIR` 使用项目环境，不要求用户寻找或填写 Python 可执行文件。
   - 调用时同时使用 `--frozen --no-sync --no-python-downloads --offline --no-env-file`，防止同步依赖、更新锁文件、下载 Python 或读取 `.env`。
   - 检查 uv run 实际解析的 Python 路径和版本；版本必须不低于 3.11，并满足业务项目版本约束。
   - 项目声明或由 uv 解析为 Python 3.14 时，直接使用项目的 3.14 环境；不要为了满足管理脚本的最低版本而改用或创建 Python 3.11 环境。
   - 不要直接调用裸 `python` 或 `python3`，也不要回退到无关的系统 Python。
   - 接入流程不运行 `uv sync`、`uv lock` 或 `uv python install`，不创建或修改 `.venv`，不下载 Python，也不修改 `uv.lock` 或业务依赖。
   - 如果 uv 项目环境尚未初始化，停止安装并让用户先按项目自己的流程初始化；不要把环境初始化混入 Team Mode 安装。
   - 业务项目要求的 Python 版本可以高于管理脚本要求；uv 项目的 Python 3.14 环境可以直接运行只要求 Python 3.11+ 的管理脚本。
6. 安装过程中不得覆盖内容不同的同名文件，不得删除文件。
7. 管理脚本只使用 Python 标准库，不需要安装第三方 Python 包。
8. 本地源仓库应来自可信位置，并确认其 Git remote、commit 和工作区状态；源仓库有未提交修改时先停止检查。仅检查“文件存在”不能证明源码可信。

### 如何确认项目可信

项目可信状态由 Codex 客户端管理，不是仓库内某个文件能够自行设置的属性。不同 Codex 客户端和版本的入口可能不同，因此不要编造或修改未知的全局配置来绕过信任检查。

按以下顺序确认：

1. 从目标项目根目录打开 Codex。
2. 在当前客户端的项目安全、工作区信任或权限界面中确认该目录受信任；如果客户端显示信任提示，必须由用户确认。
3. 新建任务，检查是否出现“忽略项目级 `.codex/`”之类的警告。
4. 安装后再次新建任务，确认项目级自定义 Agent 名称可被运行时发现。能读取磁盘上的 TOML 不等于运行时已经加载它。
5. 如果客户端没有可见的信任状态，且运行时也不能证明项目级配置已加载，则把状态记为“无法确认”，停止写入 `.codex/`，由用户处理。

不存在适用于所有 Codex 客户端的通用“强制信任”命令。不要通过修改全局配置、跳过警告或仅凭模型自述把项目判定为可信。

## 兼容性与能力预检

Team Mode 依赖当前任务的 `spawn_agent` 工具提供明确的自定义 Profile 选择器；当前实现预期该字段名为 `agent_type`。Codex 的功能可能按客户端、渠道、任务后端或工作区逐步提供，因此不要把某个版本号写成永久可靠的最低版本门槛。`codex --version` 可用于记录环境，但真正的兼容性门禁是当前任务暴露的工具 Schema。

这里的结论只针对“当前任务工具面是否满足本 Team Mode 实现”，不要扩大成“整个 Codex 产品不支持自定义 Agent”。`task_name` 只是子任务标签，`message`、`model`、`reasoning_effort` 和模型自述也不能证明运行时加载了某个 Profile 的 `developer_instructions`、模型默认值或权限配置。

在安装前发送：

```text
请只做 Team Mode 兼容性预检，不修改任何文件，不启动子 Agent。

1. 如果当前环境能够获取 Codex 版本，报告版本；不能获取时标记为未知，不要猜测。
2. 检查当前任务暴露的 spawn_agent 工具输入 Schema。
3. 列出真实输入字段，并明确报告是否存在名为 agent_type 的自定义 Profile 选择字段。
4. 如果未来运行时改用其他有官方说明、能够明确选择自定义 Profile 的字段，报告真实字段名和证据；不要仅凭名称相似就推断它等价。
5. 如果不存在任何明确的 Profile 选择器，报告：
   “当前任务的 spawn_agent Schema 不满足本 Team Mode 实现的显式自定义 Profile 选择契约。”
6. 如果 agent_type 存在，报告它允许显式选择自定义 Profile；安装前不要求四个项目级名称已经出现在候选项中。
7. 不要用 task_name、message、model、reasoning_effort、普通子 Agent 名称或模型自述代替 Profile 选择器。
```

安装并新建任务后，第二道门禁要求运行时的明确 Profile 选择器能够选择 `Explorer`、`Executor`、`Complex Executor` 和 `Reviewer`。如果当前任务的真实工具 Schema 仍没有 `agent_type` 或经官方说明的等价选择字段，即使 TOML 文件存在、Codex 版本看起来较新，也不能宣称本 Team Mode 已经可以运行。

不要为了通过门禁而删除这项检查或把 `task_name` 当成角色。标准安装包含 `default.toml` 派发哨兵；如果运行时无法显式选择工作 Profile，绕过门禁安装哨兵可能使所有省略角色的子 Agent 派发都被拒绝。

### Python 与依赖预检

两个 Python 脚本都只依赖 Python 3.11+ 标准库，不需要 `pip install`。这里的 3.11 是最低兼容版本，不是建议把业务项目降到 3.11。每个项目都由 uv 决定自己的 Python；大多数项目可以是 3.14。不要让用户手工选择 Python 路径，先确认：

```text
UV_BIN=<uv 可执行文件绝对路径>
UV_PROJECT_DIR=<包含 pyproject.toml 和 uv.lock 的绝对路径>
```

确认项目 uv 环境已经初始化后运行：

```bash
<UV_BIN> run \
  --project <UV_PROJECT_DIR> \
  --frozen \
  --no-sync \
  --no-python-downloads \
  --offline \
  --no-env-file \
  python -I -c 'import sys, argparse, json, pathlib, tomllib; assert sys.version_info >= (3, 11), sys.version; print(sys.executable); print(sys.version)'
```

`-I` 使用隔离模式，避免当前项目、`PYTHONPATH` 或用户 site-packages 干扰标准库导入。命令失败时把 uv 环境记录为写入阻塞项；不要自动运行 `uv sync`、修改锁文件、安装包、创建虚拟环境或修改业务项目依赖。

## 高级方式：从本地仓库一次性接入

如果你需要把全部预检和安装授权合并成一条可审计消息，可以使用下面的高级提示词。多数用户应优先使用前面的分阶段自然语言流程。发送前必须把 `TEAM_MODE_SOURCE`、`EXPECTED_TEAM_MODE_COMMIT`、`UV_BIN` 和 `UV_PROJECT_DIR` 都替换成已经核对的真实值；不得把尖括号占位符原样发送。

### 一次性安装提示词

```text
请把 Team Mode 接入当前项目，并完成项目级 Agent 配置。

TEAM_MODE_SOURCE：
<填写第一步已经检查通过的来源仓库绝对路径>

EXPECTED_TEAM_MODE_REMOTE：
https://github.com/bvwl/codex-team-mode.git

EXPECTED_TEAM_MODE_COMMIT：
<填写已经审阅并信任的完整 commit SHA；不得留空>

UV_PROJECT_DIR：
<填写包含 pyproject.toml 和 uv.lock 的项目目录绝对路径>

UV_BIN：
<填写 uv 可执行文件的绝对路径>

安装模式：
严格运行时就绪模式

目标范围：
- 只允许修改当前项目。
- 不修改 ~/.codex、~/.agents 或其他项目。
- 不提交 Git，不推送远端。
- 不删除任何文件或目录。
- 不覆盖内容不同的同名文件。
- 不启动任何子 Agent。
- 所有写入必须等全部门禁通过后才能执行。
- 任一门禁失败时立即禁止写入，但继续完成不依赖失败项的安全只读预检，最后一次性汇总全部阻塞项。

请按以下顺序执行：

1. 确认目标项目根目录并输出绝对路径，记为 PROJECT_ROOT：
   - 如果当前目录在 Git 仓库中，使用 Git 仓库根目录。
   - 如果不是 Git 仓库，使用用户明确打开的当前项目目录。
   - 不因为缺少 .git 自动拒绝接入。
2. 确认项目已被 Codex 标记为可信。
   - 如果项目不可信或无法确认，把它记录为写入阻塞项。
   - 继续完成不依赖项目信任的安全只读检查，但不得写入 .codex、.agents 或 AGENTS.md。
3. 在任何写入前检查当前任务的 spawn_agent 工具输入 Schema：
   - 列出真实输入字段。
   - 必须存在能够明确选择自定义 Agent Profile 的字段；当前 Team Mode 预期字段名为 agent_type。
   - 如果未来运行时使用其他字段，只能在有官方说明且该字段确实能选择自定义 Profile 时视为等价，并报告字段名和证据。
   - 如果没有明确的 Profile 选择器，把下面内容记录为写入阻塞项：
     “当前任务的 spawn_agent Schema 不满足本 Team Mode 实现的显式自定义 Profile 选择契约。”
   - 不要把结论扩大成“整个 Codex 产品不支持自定义 Agent”。
   - 不用 Codex 版本号、task_name、message、model、reasoning_effort、普通子 Agent 名称或模型自述替代真实 Profile 选择器。
   - 即使这里出现阻塞，也继续后续安全只读预检，但不得进行任何写入。
4. 验证输入参数：
   - TEAM_MODE_SOURCE 必须是明确的绝对路径，不得保留占位符。
   - EXPECTED_TEAM_MODE_REMOTE 不得为空或保留占位符。
   - EXPECTED_TEAM_MODE_COMMIT 必须恰好是 40 个十六进制字符，不得使用短 SHA、分支名或尖括号占位符。
   - UV_PROJECT_DIR 必须是包含 pyproject.toml 和 uv.lock 的明确绝对路径。
   - UV_BIN 必须是 uv 可执行文件的明确绝对路径。
   - 读取 .python-version 和 pyproject.toml 的 requires-python；uv run 实际解析的 Python 必须满足业务项目声明。项目声明或解析为 3.14 时不得改用系统 3.11。
   - 参数无效时记录为写入阻塞项，但继续能够安全完成的只读检查。
   - 不得用检测到的 HEAD 自动替换 EXPECTED_TEAM_MODE_COMMIT；只能把 HEAD 作为候选值报告给用户审阅。
5. 检查 TEAM_MODE_SOURCE 的可信度：
   - 它必须是 Git 仓库。
   - 输出 git remote get-url origin、git rev-parse --verify HEAD 和 git status --porcelain=v1 --untracked-files=all。
   - origin 必须与 EXPECTED_TEAM_MODE_REMOTE 一致；只允许 URL 末尾是否带 .git 的规范化差异。
   - HEAD 必须与 EXPECTED_TEAM_MODE_COMMIT 完全一致。
   - git status --porcelain=v1 --untracked-files=all 必须为空。
   - 对 scripts 和 agents 运行 git ls-files --others --ignored --exclude-standard，结果必须为空，防止额外文件影响脚本导入或 Profile 源。
   - 单独列出 skills/team-mode 下被忽略或未跟踪的文件；它们可以作为本地缓存存在，但不得复制到目标。
   - 用 git ls-tree -r EXPECTED_TEAM_MODE_COMMIT 枚举整个 skills/team-mode 安装源；实际复制范围和内容必须只来自这个受版本控制的 commit 清单。
   - 检查 TEAM_MODE_SOURCE 本身及下面列出的安装源文件都不是符号链接。
   - 执行前审阅整个 skills/team-mode 树、scripts/manage_profiles.py 和五个 TOML 的当前 commit 内容；不得只检查文件存在。
   - 如果 commit 未签名，只能报告“已固定并审阅 commit”，不能宣称其签名可信。
   - 如果存在未提交修改、remote 或 commit 不符、来源不明、符号链接或路径超出授权范围，记录为写入阻塞项。
   - 不自动 pull、checkout、reset 或修改源仓库。
   - 如果 EXPECTED_TEAM_MODE_COMMIT 无效，仍然可以只读报告实际 HEAD、remote 和工作区状态，但不得执行或复制该来源中的代码。
6. 检查以下源文件是否存在并且是普通文件：
   - TEAM_MODE_SOURCE/skills/team-mode/SKILL.md
   - TEAM_MODE_SOURCE/scripts/manage_profiles.py
   - TEAM_MODE_SOURCE/skills/team-mode/references/profiles.json
   - TEAM_MODE_SOURCE/agents/Explorer.toml
   - TEAM_MODE_SOURCE/agents/Executor.toml
   - TEAM_MODE_SOURCE/agents/Complex Executor.toml
   - TEAM_MODE_SOURCE/agents/Reviewer.toml
   - TEAM_MODE_SOURCE/agents/default.toml
   - 缺失、不是普通文件或是符号链接时记录为写入阻塞项。
7. 使用明确指定的 UV_BIN 和 UV_PROJECT_DIR 检测项目 Python 和依赖：
   - 先报告 uv 版本，确认 UV_PROJECT_DIR 中存在 pyproject.toml 和 uv.lock，并确认 uv 项目环境已经初始化。
   - 使用 UV_BIN run --project UV_PROJECT_DIR --frozen --no-sync --no-python-downloads --offline --no-env-file python --version。
   - 再用同一 uv run 前缀执行 python -I，导入 sys、argparse、json、pathlib 和 tomllib，并输出 sys.executable 和 sys.version。
   - 如果版本低于 3.11、不满足项目声明的版本（例如项目要求 3.14）、路径不可执行或任一标准库导入失败，记录为写入阻塞项，并报告解释器路径和错误。
   - 不运行 uv sync、uv lock、uv python install，不创建或修改 .venv，不下载 Python，不修改 uv.lock，不自行安装、降级或切换到未经用户指定的 Python。
   - manage_profiles.py 只使用 Python 标准库，不安装第三方包。
8. 只有 TEAM_MODE_SOURCE 的可信度、源文件和 uv 项目环境检查都通过后，才允许执行来源中的 manage_profiles.py。先对当前项目执行无写入预检：
   UV_BIN run --project UV_PROJECT_DIR --frozen --no-sync --no-python-downloads --offline --no-env-file
   python -I TEAM_MODE_SOURCE/scripts/manage_profiles.py
   --scope project
   --project-root PROJECT_ROOT
   - 如果前置条件失败，不执行脚本，把“Profile 预检未执行”及原因写入报告；不得把未执行报告成通过。
9. 检查 Profile 预检结果：
   - 如果出现 conflict，把每个冲突文件记录为写入阻塞项。
   - 此时不得复制 Skill 或写入任何 Profile。
10. Skill 目标路径为：
   PROJECT_ROOT/.agents/skills/team-mode
11. 安装 Skill 前按下面的确定性规则执行只读目标检查：
   - 安装源以 git ls-tree -r EXPECTED_TEAM_MODE_COMMIT -- skills/team-mode 的结果为准，不以工作树目录遍历结果为准。
   - Git 树只允许普通文件和目录；发现符号链接或 gitlink 时记录为写入阻塞项。
   - 使用 lstat 语义检查目标根和每个目标路径项，不跟随符号链接。
   - 目标不存在时记为 missing；目标根或任一父级是符号链接时记为 conflict。
   - 枚举 Git 树和目标中的全部相对路径，包括点号开头的隐藏文件。
   - 使用 git show EXPECTED_TEAM_MODE_COMMIT:<path> 读取源 blob，并比较相对路径集合、每项类型和普通文件的 SHA-256；不能只比较文件名、大小或修改时间。
   - 目标中的额外文件、目录、符号链接或特殊文件都记为 conflict，不默认为项目定制。
   - 根据 git ls-tree 的 mode 检查 POSIX 可执行位；权限差异单独报告，不自动修改已经存在的目标。
   - 如果目标不存在，记录计划，但先完成所有冲突检查。
   - 任何类型、路径集合、内容或权限差异都记录为写入阻塞项并展示差异，不覆盖。
   - 不使用会清空或删除目标目录的同步参数。
12. 执行统一写入门禁：
    - 汇总此前发现的全部写入阻塞项。
    - 只有阻塞项数量为 0 时才允许继续写入；这也是我对本次安装的写入授权。
    - 只要存在任一阻塞项，不创建 .agents 或 .codex，不安装 Skill，不安装任何 Profile，不修改 AGENTS.md。
    - 特别不得在缺少明确 Profile 选择器时单独或强行安装 default.toml；否则无法显式选择角色的运行时可能让所有子 Agent 派发都落入拒绝工作的哨兵。
    - 阻塞时仍需一次性报告已完成的只读检查、全部阻塞项和未执行步骤。
13. 统一写入门禁通过后：
    - 如果 Skill 目标不存在，只按 EXPECTED_TEAM_MODE_COMMIT 的 Git 树逐项创建目录和普通文件。
    - 每个文件内容来自对应 git show blob；不复制工作树中的未跟踪、被忽略或缓存文件。
    - 使用排他创建，不覆盖安装期间新出现的同名路径；任一写入失败立即停止并报告部分状态。
    - 如果 Skill 已完全一致，不重复复制。
14. 执行项目级 Profile 安装：
   UV_BIN run --project UV_PROJECT_DIR --frozen --no-sync --no-python-downloads --offline --no-env-file
   python -I TEAM_MODE_SOURCE/scripts/manage_profiles.py
   --scope project
   --project-root PROJECT_ROOT
   --apply
15. 执行安装验证：
   UV_BIN run --project UV_PROJECT_DIR --frozen --no-sync --no-python-downloads --offline --no-env-file
   python -I TEAM_MODE_SOURCE/scripts/manage_profiles.py
   --scope project
   --project-root PROJECT_ROOT
   --verify
16. 解析五个 TOML，核对：
    - name
    - description
    - developer_instructions
    - model
    - model_reasoning_effort
    - sandbox_mode
17. 安装由 Skill 复制和 Profile 安装两个步骤组成，不是原子操作。
    - 任一步骤失败时，立即停止。
    - 报告已经成功写入的明确路径和未完成步骤。
    - 不通过删除文件回滚。
    - 修复阻塞后使用同一预检流程恢复。
18. 不要在本次安装任务里启动工作 Agent。
19. 本提示词不自动创建 AGENTS.md；安装完成后必须执行文档中的独立 AGENTS.md 配置提示词。
20. 完成后报告：
    - PROJECT_ROOT
    - 项目信任状态及证据
    - spawn_agent 的真实字段列表
    - 是否存在明确的自定义 Profile 选择器
    - 兼容性结论是否仅限于当前任务工具面
    - TEAM_MODE_SOURCE 的 remote、HEAD 和完整工作区状态
    - EXPECTED_TEAM_MODE_COMMIT 是否有效并与 HEAD 匹配
    - 实际使用的 Python 路径和版本
    - Skill 安装路径
    - Agent Profile 安装路径
    - 每个 Profile 的模型、effort 和 sandbox
    - 是否发现冲突
    - 全部写入阻塞项
    - 哪些只读预检已完成、哪些步骤未执行及原因
    - 是否发生任何写入
    - 是否处于部分安装状态
    - AGENTS.md 是否仍待配置
    - 是否需要重启 Codex或新建任务
    - 下一步只读验证提示词和审计命令
```

这段提示词只在统一写入门禁的阻塞项数量为零时授权写入当前项目内的 Skill 和 Profile。源仓库不可信、项目未受信任、缺少明确 Profile 选择器、参数仍是占位符、Python 不兼容或同名内容不同时，都必须保持零写入并一次性报告全部阻塞项，不能自行覆盖或只安装 `default.toml`。`AGENTS.md` 是下一步独立配置，不属于 `manage_profiles.py` 的安装结果。

## 另一台机器：自动准备统一源码缓存

在另一台机器上也使用 `CODEX_HOME/sources/codex-team-mode`，不要把来源仓库克隆进业务项目。推荐直接使用前面的“第 1 步”自然语言提示词：目标不存在时自动创建缺失的 `CODEX_HOME/sources` 并克隆，目标已存在时只读检查。提示词中的逻辑位置不依赖操作系统；执行时必须转换成平台原生绝对路径。

如果需要在 macOS 或 Linux 上手工执行，对应命令是：

```bash
team_mode_codex_home="${CODEX_HOME:-$HOME/.codex}"
mkdir -p "$team_mode_codex_home/sources"
git clone https://github.com/bvwl/codex-team-mode.git "$team_mode_codex_home/sources/codex-team-mode"
team_mode_source="$team_mode_codex_home/sources/codex-team-mode"
```

如果需要在 Windows PowerShell 上手工执行，对应命令是：

```powershell
$TeamModeCodexHome = if ($env:CODEX_HOME) {
    $env:CODEX_HOME
} else {
    Join-Path $env:USERPROFILE ".codex"
}
$TeamModeSources = Join-Path $TeamModeCodexHome "sources"
$TeamModeSource = Join-Path $TeamModeSources "codex-team-mode"
New-Item -ItemType Directory -Path $TeamModeSources -Force | Out-Null
git clone https://github.com/bvwl/codex-team-mode.git $TeamModeSource
```

以上命令仅用于目标确实不存在的首次克隆；如果目标已存在，不要再次运行 `git clone` 或用 `New-Item -Force` 处理目标仓库。自动流程在创建任何内容前还必须执行前述冲突检查。

不要在未审阅的浮动 `main` 上直接执行安装脚本。进入检出后，macOS/Linux 可以这样核对：

```bash
git -C "$team_mode_source" remote get-url origin
git -C "$team_mode_source" rev-parse --verify HEAD
git -C "$team_mode_source" status --porcelain=v1 --untracked-files=all
git -C "$team_mode_source" ls-files --others --ignored --exclude-standard -- scripts agents
git -C "$team_mode_source" ls-files --others --ignored --exclude-standard -- skills/team-mode
```

Windows PowerShell 使用同样的 Git 参数，只把路径变量写成 `$TeamModeSource`：

```powershell
git -C $TeamModeSource remote get-url origin
git -C $TeamModeSource rev-parse --verify HEAD
git -C $TeamModeSource status --porcelain=v1 --untracked-files=all
git -C $TeamModeSource ls-files --others --ignored --exclude-standard -- scripts agents
git -C $TeamModeSource ls-files --others --ignored --exclude-standard -- skills/team-mode
```

工作区状态和 `scripts agents` 的额外文件检查必须没有输出。最后一个命令用于列出 Skill 工作树缓存；它允许有输出，但这些路径不得安装。审阅该 commit 中的整个 `skills/team-mode/`、`scripts/manage_profiles.py` 和 `agents/*.toml`。记录完整 commit SHA；后续安装始终把它作为 `EXPECTED_TEAM_MODE_COMMIT`，不要只写分支名或短 SHA。若要升级，先审阅新 commit，再更新期望值。

然后使用上一节的“一次性安装提示词”，把 `TEAM_MODE_SOURCE` 指向内部解析后的统一缓存路径。公开文档和普通报告中只需写：

```text
CODEX_HOME/sources/codex-team-mode
```

也可以先在目标项目根目录尝试安装 Skill：

```bash
npx skills add bvwl/codex-team-mode
```

但 Skill 和自定义 Agent Profile 是两个配置面。即使 Skill 安装成功，仍要使用 `manage_profiles.py` 安装并验证 `.codex/agents/` 下的五个 Profile。

## 为目标项目生成 AGENTS.md

Team Mode 负责“如何分工”，但不知道目标项目真实的构建命令、目录边界和验收标准。安装完成后，发送下面的提示词，让 Codex 创建或补充项目根目录的 `AGENTS.md`。

```text
请阅读当前项目并完善项目根目录的 AGENTS.md，使其能够安全、稳定地配合 $team-mode 使用。

约束：
- 如果 AGENTS.md 已存在，保留原有规则，只补充缺失内容。
- 不修改业务代码。
- 不删除文件。
- 不提交 Git，不推送远端。
- 不猜测无法从项目中确认的命令；无法确认时标记为待补充。

请先只读识别：
1. 项目目录结构和主要模块。
2. 前端、后端、数据库、部署和基础设施位置。
3. 包管理器、Python 环境和锁文件。
   - Python 项目核对 uv、.python-version、pyproject.toml、uv.lock 和现有 .venv。
   - 记录 uv run 实际解析的 Python；多数项目使用 Python 3.14。
   - 从 pyproject.toml 读取第三方依赖和依赖组。
4. 构建、测试、Lint、格式化、类型检查和集成测试命令；Python 命令优先确认 uv run 形式。
5. 生成文件、第三方代码、样本、密钥和其他禁止修改区域。
6. 当前项目的安全、隐私和数据边界。

然后在 AGENTS.md 中明确：
1. 项目结构和关键入口。
2. 经过证据确认的验证命令。
3. 每种修改完成后必须运行哪些检查。
4. 同一个共享目标同时只允许一个写入 Agent。
5. 产品、架构、安全、授权和最终验收留在主线程。
6. 大型、可拆分任务可以使用 $team-mode。
7. 简单任务由主线程直接完成，不为了凑角色启动 Agent。
8. Explorer 和 Reviewer 只读。
9. Executor 只处理明确、局部、低风险并可确定性验证的修改。
10. Complex Executor 只在架构、范围、文件所有权和验收标准已经确定后使用。
11. 子 Agent 不得创建后代 Agent。
12. 不得扩大用户授权，不得自行提交、推送、发布或部署。
13. 项目初始化约定是 uv python install 3.14、uv init、uv python pin 3.14 和 uv venv；这些命令只用于新项目创建，不在已有项目任务中重复执行。
14. 第三方依赖以 pyproject.toml 为声明源，通过 uv add、uv add --dev 或 uv remove 管理；禁止直接使用 pip、创建 requirements.txt 或手工编辑 uv.lock。
15. 未经需求明确授权，不得修改 pyproject.toml、uv.lock 或项目 uv 环境；验证命令使用已经初始化的 uv 环境。

如果项目包含逆向分析，再补充：
1. 只分析明确授权的程序、协议、固件和样本。
2. 样本记录 SHA-256、来源、版本和分析日期。
3. 结论分为已确认事实、合理推断和待验证假设。
4. 静态分析记录工具版本、文件、函数、RVA 或偏移。
5. 未知可执行文件不得直接在宿主机运行。
6. 动态分析必须使用明确授权的隔离环境。
7. 未经授权不得联网、上传样本、外发反编译结果或使用真实凭据。
8. 发现异常网络、持久化或破坏行为时立即停止。

修改完成后：
- 展示 AGENTS.md 的差异。
- 列出仍需我确认的命令和规则。
```

## 重启后验证 Skill 和 Agent

项目级 Skill 或 Profile 新安装后，建议重启 Codex 或在目标项目中新建任务，再执行只读验证。

新建父任务后、发送验证提示词前，在该任务的权限或 sandbox 控件中选择严格只读模式。不要使用 `workspace-write`、`danger-full-access` 或等价的可写覆盖执行只读验证。若客户端不能显示或控制父任务权限，则不得声称已实现严格只读隔离；只能做静态配置检查，或先把项目放进用户认可的操作系统级只读容器/沙箱。

Profile 的 `read-only` 是默认配置，不能替代父线程实时权限或操作系统级隔离。运行时验证完成后，trace 中的 `effective sandbox` 必须是 `read-only`；否则验证失败。

### 完整验证提示词

```text
请验证当前项目的 Team Mode 安装，不修改任何业务文件。

验证范围：
1. 检查 .agents/skills/team-mode/SKILL.md 是否可发现。
2. 检查项目级 Agent Profile：
   - .codex/agents/Explorer.toml
   - .codex/agents/Executor.toml
   - .codex/agents/Complex Executor.toml
   - .codex/agents/Reviewer.toml
   - .codex/agents/default.toml
3. 解析 TOML 并与：
   .agents/skills/team-mode/references/profiles.json
   核对。
4. 检查当前运行时是否支持显式选择：
   - Explorer
   - Executor
   - Complex Executor
   - Reviewer
   - 依据当前任务真实 spawn_agent 工具 Schema 中的 agent_type 字段和候选值判断
   - 如果未来运行时使用其他有官方说明的等价 Profile 选择字段，报告真实字段名和证据
   - 不依据 Codex 版本号、task_name、message、model、reasoning_effort、配置文件存在或模型自述判断
5. 如果当前任务没有明确的自定义 Profile 选择器：
   - 不使用通用子 Agent 替代。
   - 不执行写入测试。
   - 报告“当前任务工具面不满足本 Team Mode 实现的显式 Profile 选择契约”，不要扩大成整个 Codex 产品不支持自定义 Agent。
   - 直接报告需要切换到提供该能力的任务环境，或在更新、重启 Codex 后新建任务重新验证。
6. 如果支持，启动一个最小的只读 Explorer：
   - 先确认父线程当前处于严格只读权限模式
   - fork_turns="none"
   - 只读取项目根目录一级结构
   - 不修改文件
   - 不联网
   - 不启动后代 Agent
7. 从本地 session trace 核对实际：
   - agent_role
   - model
   - effort
   - effective sandbox
   - depth
8. 使用 usage_by_model.py 的 --audit-routing 输出审计结果。
9. 如果本地 session trace 不存在、未保留或无权读取：
   - 不猜测运行时结果。
   - 报告审计不可用及具体原因。
   - 继续提供已经完成的静态 Profile 验证结果。
10. 报告配置值和实际运行值的差异。
```

### 项目级审计命令

uv 项目统一通过 uv run 使用已经初始化的项目环境；多数项目可以由 uv 解析为 Python 3.14：

```bash
<UV_BIN> run \
  --project <UV_PROJECT_DIR> \
  --frozen \
  --no-sync \
  --no-python-downloads \
  --offline \
  --no-env-file \
  python .agents/skills/team-mode/scripts/usage_by_model.py \
  --task-id current \
  --by-agent \
  --by-session \
  --audit-routing
```

不要为了运行审计脚本调用 `uv sync`、新建 `.venv`，也不要在 uv 环境缺失时悄悄回退到系统 `python3`。

审计结果重点关注：

- `unknown_agent_role`
- `model_mismatch`
- `effort_mismatch`
- `readonly_boundary_mismatch`
- `danger_full_access`
- `nested_subagent`
- `sandbox_unobserved`

TOML 中的 `sandbox_mode` 是 Profile 默认值。父线程的实时权限设置可能覆盖子 Agent，因此必须以 trace 中的实际 sandbox 为准。

`usage_by_model.py` 默认读取 `$CODEX_HOME/sessions`；未设置 `CODEX_HOME` 时读取 `~/.codex/sessions`。`--task-id current` 依赖当前 Codex 任务提供 `CODEX_THREAD_ID`。本地日志未保留、远程 session 不可用或环境变量缺失时，脚本会报告限制，不能把缺失数据当作验证通过。

## 日常使用提示词

安装验证完成后，用户不需要逐个指定 Agent。可以直接发送：

```text
使用 $team-mode 完成下面的任务。

选择够用的最小团队。
先明确目标、来源、允许修改范围、禁止事项、验证命令和停止条件。
尚未解决的用户意图、产品、架构、安全和授权决策留在主线程。
同一个共享目标只允许一个写入者。
子 Agent 不得创建后代 Agent。
最终由主线程检查真实来源、diff、产物和验证结果。

任务：
<填写任务>
```

### 只读调查

```text
使用 $team-mode 只读调查当前项目。

目标：
<填写需要查清的问题>

只使用 Explorer。
不要修改文件、配置、数据或外部状态。
返回带文件路径、符号、行号和置信度的证据。
区分已确认事实、推断和未知项。
主线程不要重复 Explorer 已完成的调查。
```

### 明确的局部修改

```text
使用 $team-mode 完成这个局部修改。

目标：
<填写修改目标>

允许修改：
<填写明确文件或目录>

禁止修改：
<填写边界>

必须验证：
<填写测试、Lint、构建或其他命令>

如果范围、验收标准或用户意图不清楚，留在主线程确认。
只有任务局部、低风险、可回滚且能确定性验证时才使用 Executor。
```

### 边界明确的复杂实现

```text
使用 $team-mode 完成这个多模块实现。

主线程先确定：
- 架构
- 接口契约
- 数据边界
- 文件所有权
- 回滚方式
- 验收标准
- 必须运行的检查

只有以上决策全部明确后，才可以使用 Complex Executor。
Complex Executor 不得自行改变产品目标或架构。
最终由主线程检查全部 diff 和验证输出。

任务：
<填写任务>
```

### 独立复审

```text
使用一个全新上下文的 Reviewer 检查下面这个具体风险。

Unresolved risk：
<只填写一个具体风险>

Evidence：
<填写精确文件、报告、日志或数据>

Checks already passed：
<填写已经通过的检查>

Do not repeat：
<填写不要重复的广泛验证>

Reviewer 只读，不生成补丁，不继承先前争论或预期结论。
返回按严重度排序的发现、证据、影响、最小修复方向和所需验证。
```

## 全栈开发提示词

```text
使用 $team-mode 完成下面的全栈任务。

任务：
<填写功能或缺陷>

执行要求：
1. 先让 Explorer 只读调查：
   - 前端入口、路由、组件和状态管理
   - API 客户端和接口契约
   - 后端路由、服务、模型和权限
   - 数据库 Schema、迁移和回滚
   - 现有测试和 CI 命令
2. 产品行为、API 契约、鉴权方案、数据库策略和最终验收留在主线程。
3. 明确前端、后端、数据库和测试的文件所有权。
4. 同一个共享文件或模块只允许一个写入者。
5. 局部修改使用 Executor。
6. 架构和验收标准已经明确的跨模块实现才使用 Complex Executor。
7. UI 结果需要浏览器、截图或真实交互验收，不能只用结构测试代替。
8. 鉴权、越权、数据一致性或迁移回滚只选择一个具体残余风险交给 Reviewer。
9. 最终由主线程运行并检查：
   - 前端测试、Lint 和构建
   - 后端测试和类型检查
   - 数据库迁移检查
   - 必要的集成测试
```

## 逆向分析提示词

下面的模板只适用于明确授权的目标。

```text
使用 $team-mode 完成这个授权范围内的逆向分析任务。

目标：
<样本、程序、协议或固件的绝对路径>

授权范围：
<说明所有权、测试授权或分析理由>

允许的分析：
<静态分析 / 受控动态分析 / 协议分析>

禁止事项：
- 未经授权不运行样本
- 不访问第三方系统
- 不上传或外发样本
- 不使用真实凭据
- 不修改目标系统或生产数据
- 不扩大分析范围

工作方式：
1. 默认从静态分析开始。
2. Explorer 只读收集：
   - SHA-256、文件格式、架构和版本
   - 导入、导出、字符串、节区和资源
   - 关键函数、调用关系、RVA 或偏移
   - 现有日志、流量、符号和文档
3. 每个结论必须标记为：
   - 已确认事实
   - 合理推断
   - 待验证假设
4. 每个结论记录：
   - Evidence
   - Confidence
   - Alternative explanation
   - Reproduction
   - Remaining uncertainty
5. 需要编写局部解析或转换脚本时，只有目标和测试样本明确后才使用 Executor。
6. 需要实现多阶段解析器、模拟器或兼容实现时，主线程必须先确定架构、输入输出、样本范围和确定性测试，之后才能使用 Complex Executor。
7. 如果需要动态分析但没有明确的隔离环境和授权，只返回实验方案，不实际执行。
8. Reviewer 只检查一个具体关键推断，例如：
   - 协议字段含义
   - 分页或状态机终止条件
   - 加密算法识别
   - 版本差异
9. 最终语义判断、授权判断和安全决策留在主线程。
```

未知或可能恶意的可执行文件不能仅依靠 Agent 的 `read-only` 指令隔离。动态执行需要真实的虚拟机、快照、容器、网络隔离和宿主机保护。

## 更新已接入的 Team Mode

当源仓库发布新版本后，在目标项目中发送：

```text
请更新当前项目已经接入的 Team Mode。

源仓库：
<TEAM_MODE_SOURCE 绝对路径>

目标项目：
<PROJECT_ROOT 绝对路径>

约束：
- 不删除文件。
- 不使用清空或镜像删除参数。
- 不覆盖当前项目中的定制内容。
- 不修改全局配置。
- 不提交 Git，不推送远端。

步骤：
1. 确认源仓库工作区干净，并报告当前 commit。
2. 比较：
   TEAM_MODE_SOURCE/skills/team-mode
   与：
   PROJECT_ROOT/.agents/skills/team-mode
3. 展示差异并区分：
   - 上游更新
   - 当前项目定制
   - 冲突
4. 如果目标没有任何项目定制且更新可以安全应用，先向我报告计划。
5. 如果存在定制或冲突，不覆盖，停止并等待我选择。
6. 对 Agent Profile 运行 manage_profiles.py 无写入预检。
7. 如果 Profile 内容不同，把差异展示给我，不直接替换。
8. 更新获得我确认后再执行。
9. 更新后执行 --verify、完整测试和 --audit-routing。
10. 报告更新前后 commit、文件差异和验证结果。
```

Profile 管理工具把内容不同的已安装文件视为冲突，这是有意的安全设计。升级 Profile 时应先审查差异，再决定是否替换。

## 个人级安装

当多个项目已经验证稳定后，可以考虑个人级安装：

```text
请把 Team Mode 安装为个人级 Skill 和 Agent Profile。

源仓库：
<TEAM_MODE_SOURCE 绝对路径>

目标：
- Skill：$HOME/.agents/skills/team-mode
- Agent Profile：$HOME/.codex/agents

我授权写入以上两个个人配置目录，但不授权删除任何文件。

要求：
1. 先做无写入预检。
2. 检查所有同名目标。
3. 不覆盖内容不同的文件。
4. 使用当前项目已经初始化的 uv 环境；大多数项目可以是 Python 3.14，3.11 只是管理脚本的最低兼容版本。
5. 使用 manage_profiles.py --scope personal。
6. 安装后执行 --verify。
7. 报告个人级 default.toml 对所有 Codex 项目的影响。
8. 告诉我如何通过可恢复移动只停用 default 哨兵，同时保留四个工作 Profile。
9. 不提交 Git，不推送远端。
```

个人级 `default.toml` 会影响所有 Codex 项目中遗漏或错误选择 Agent 类型的派发。首次使用建议保留项目级范围。

## 故障排查

### 项目不是 Git 仓库

Team Mode 的项目级 Skill 和 Profile 不要求业务项目必须使用 Git。让用户明确指定项目根目录，并从该目录打开 Codex。缺少 `.git` 时不要执行依赖 Git 根目录发现的命令，也不要擅自初始化仓库。

### 项目未被信任

如果 Codex 提示项目级 `.codex/` 被忽略，停止安装和运行时验证，让用户在当前 Codex 客户端的项目安全、工作区信任或权限界面中确认该目录可信。不同客户端的入口可能不同；不要猜测、修改未知全局配置或通过启动参数绕过信任检查。

确认信任后必须新建任务，并用两个结果形成闭环：

1. 不再出现项目级配置被忽略的警告。
2. 安装后的 `spawn_agent.agent_type` 或经官方说明的等价 Profile 选择字段能看到并选择四个项目级工作 Profile。

只有第一项、只能读取 TOML、或模型口头声称“已信任”，都不足以证明项目级 Agent 配置已经加载。

### 找不到 `$team-mode`

检查：

```text
<PROJECT_ROOT>/.agents/skills/team-mode/SKILL.md
```

然后：

1. 确认从项目根目录或其子目录打开 Codex。
2. 确认项目被标记为可信。
3. 新建 Codex 任务。
4. 仍未出现时重启 Codex。

### 找不到自定义 Agent

检查：

```text
<PROJECT_ROOT>/.codex/agents/
```

然后运行：

```bash
<UV_BIN> run \
  --project <UV_PROJECT_DIR> \
  --frozen \
  --no-sync \
  --no-python-downloads \
  --offline \
  --no-env-file \
  python -I <TEAM_MODE_SOURCE>/scripts/manage_profiles.py \
  --scope project \
  --project-root <PROJECT_ROOT> \
  --verify
```

先检查当前任务真实的 `spawn_agent` 工具输入 Schema。没有 `agent_type` 或经官方说明的等价 Profile 选择字段时，只能判定“当前任务工具面不满足本 Team Mode 实现的显式 Profile 选择契约”，不要扩大成整个 Codex 产品不支持自定义 Agent；有选择字段但缺少四个项目级名称时，项目配置未加载或当前任务不支持该配置。不要用通用 Agent、`task_name`、`message`、`model`、`reasoning_effort` 或同名提示词假装替代。切换到提供该能力的任务环境，或在更新、重启 Codex 后新建任务重新验证。

公开版本号不能稳定代表按客户端或工作区逐步提供的能力，因此本项目不声明一个容易过时的最低 Codex 版本。可以记录 `codex --version`，但只以当前任务的工具 Schema 和安装后的真实候选项作为通过标准。

### 安装出现 `conflict`

`conflict` 表示目标文件存在但内容与源模板不同。

正确处理：

1. 展示源文件和目标文件差异。
2. 确认差异是项目定制、旧版本还是意外修改。
3. 由用户决定保留、合并或替换。

不要：

- 自动覆盖。
- 删除目标后重新安装。
- 批量清空 `.codex/agents/`。

### 安装中途失败或只完成一部分

安装不是跨 `.agents/` 和 `.codex/` 两个目录的原子事务。不要通过删除已写入文件来伪造回滚；使用下表恢复：

| 当前状态 | 恢复方式 |
| --- | --- |
| Skill 完全一致，Profile 缺失 | 重新执行全部无写入预检；无冲突后运行 `manage_profiles.py --apply`，再 `--verify` |
| Profile 已验证，Skill 缺失 | 重新执行源码信任和 Skill 树比较；无冲突后只复制缺失的完整 Skill |
| Skill 或 Profile 内容不同 | 标记为 `conflict`，展示差异，由用户决定保留、合并或替换 |
| 文件存在但安装状态不明 | 先做静态验证和逐路径比较，不根据“文件存在”推断成功 |

每次恢复都必须重新核对源 remote、完整 commit SHA、干净工作区、Python 预检和全部目标冲突。恢复完成前报告“部分安装”，不要启动工作 Agent。

### Python 版本错误

uv 项目先检查项目声明和现有环境：

```bash
<UV_BIN> --version
<UV_BIN> run \
  --project <UV_PROJECT_DIR> \
  --frozen \
  --no-sync \
  --no-python-downloads \
  --offline \
  --no-env-file \
  python --version
```

同时核对 `UV_PROJECT_DIR/.python-version` 和 `UV_PROJECT_DIR/pyproject.toml` 中的 `requires-python`。uv run 实际解析的 Python 必须来自已经初始化的项目环境，版本不低于 3.11，并满足业务项目声明；项目声明或解析为 Python 3.14 时直接使用 3.14。不要运行 `uv sync`、`uv lock` 或 `uv python install` 来掩盖环境缺失，也不要为了 Team Mode 降级或另建 Python 3.11 环境。

### 审计出现 `subagent/unknown`

可能原因：

- 派发时遗漏了 `agent_type`。
- 运行时没有加载自定义 Profile。
- 正在执行唯一允许的 `default` 哨兵 onboarding 自检。

正常任务中出现该结果时，拒绝该子 Agent 的工作结果，修复 Profile 或运行时后再派发。

### 配置是只读，但实际 sandbox 可写

Profile 的 `sandbox_mode` 可能被父线程实时权限覆盖。应以任务 trace 和 `--audit-routing` 输出为准。需要真正的只读隔离时，先新建父任务，再在该任务的权限或 sandbox 控件中选择严格只读模式，然后发送验证提示词；不要保留 `workspace-write`、`danger-full-access` 或等价覆盖。如果客户端无法控制该权限，停止动态只读验证，或改用用户认可的操作系统级只读容器/沙箱。

### 找不到本地 session trace

默认检查：

```text
$CODEX_HOME/sessions
```

如果未设置 `CODEX_HOME`，检查：

```text
~/.codex/sessions
```

本地日志可能不包含临时或远程 session。`--task-id current` 还需要当前任务提供 `CODEX_THREAD_ID`。缺少日志或环境变量时，保留静态配置验证结果，并明确说明无法完成运行时模型、sandbox 和角色审计。

## 最终检查清单

接入完成后逐项确认：

- [ ] 当前项目被 Codex 信任。
- [ ] Team Mode 源仓库的 remote、commit 和工作区状态已经核对。
- [ ] `.agents/skills/team-mode/SKILL.md` 存在。
- [ ] `.codex/agents/` 下五个 TOML 存在。
- [ ] `manage_profiles.py --verify` 通过。
- [ ] Python 版本不低于 3.11。
- [ ] Python 项目通过 uv 管理，项目声明或解析为 Python 3.14 时实际使用 3.14。
- [ ] 第三方依赖以 `pyproject.toml` 为声明源，`uv.lock` 未被手工编辑，未使用 pip 或 requirements.txt 绕过 uv。
- [ ] 没有要求系统必须存在 `python3.11` 命令。
- [ ] `AGENTS.md` 包含真实构建和验证命令。
- [ ] 全栈项目明确前端、后端、数据库和集成测试边界。
- [ ] 逆向项目明确授权、样本、隔离和证据规则。
- [ ] 当前运行时能够显式选择四个工作 Agent。
- [ ] 只读验证前已经把父线程设置为严格只读权限。
- [ ] 最小只读 Explorer 验证成功。
- [ ] `--audit-routing` 没有未解释的错误。
- [ ] 本地 session trace 不可用时已经明确标注审计缺口。
- [ ] 简单任务不会为了凑流程启动子 Agent。
- [ ] 主线程保留架构、安全和最终验收。
- [ ] 没有修改全局配置、删除文件或覆盖冲突文件。
