# JMGo MetaCognition

**面向具身智能与机器人的离线认知骨架**  
*An offline-first cognitive skeleton for embodied agents and robots.*

> 生符号元认知 AI，脱离稠密参数，以事态子图自主归纳世界规则，驱动可控多模态理解与结构化文生图。

[![License](https://img.shields.io/badge/license-AGPL--3.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB.svg)](pyproject.toml)
[![Status](https://img.shields.io/badge/status-early%20preview-orange.svg)](CHANGELOG.md)

> 让机器人先“想清楚”，再动。  
> 感知 → 意图 → 规划 → 行动 → 校验，全程可离线、可解释、可中断。

---

## 这是什么

JMGo MetaCognition 是一个**可进化的认知骨架**，不是大模型，也不是电机驱动。

它把机器人/具身智能体的一次任务拆成一条可观测的闭环：

```
传感器 / 用户指令
        │
        ▼
  ① 感知适配（开放层：相机、麦克风、激光、ROS 2 topic）
        │
        ▼
  ② 意图与主体（核心：谁、要什么、约束是什么）
        │
        ▼
  ③ 规划与检索（核心：需要哪些信息、怎么取证、先做什么）
        │
        ▼
  ④ 推演与合成（核心：从证据推出结论，而不是背答案）
        │
        ▼
  ⑤ 校验与安全闸（核心：口径、单位、年份、主体、风险）
        │
        ▼
  ⑥ 行动适配（开放层：机械臂、底盘、语音、屏幕、ROS 2 action）
```

每一步都有结构化输入/输出和审计轨迹，出问题时能定位到“哪一步、凭什么”。

## 为什么是机器人方向

机器人不缺“生成”，缺的是**在不确定环境里可解释地做决定**：

- **离线优先**：工厂、园区、家庭场景经常没有稳定外网；认知闭环不能依赖云。
- **可解释**：为什么抓这个杯子、为什么先开门、为什么放弃，必须能说出来。
- **可中断**：执行前有校验闸，执行中有预算与超时，异常可回退。
- **可组合**：感知/执行是开放插件，认知核心保持稳定，换硬件不用重写大脑。
- **安全边界**：核心只输出“建议动作 + 依据 + 风险”，执行层保留最终否决权。

## 自我演化 + 基础情绪（都不影响执行）

这两块都在闭源核心内，但行为边界是公开契约。

### 自我演化：演化规则与经验，不改源码

```
反馈 / 经验 → 样本 → 归纳 → 新规则 / 词条 / 权重 → 版本化 → 可回滚
```

- **离线**：不需要云端训练，数据留在本机。
- **可审计**：每次演化带来源、diff、版本号；可回滚到上一版。
- **不改代码**：演化的是规则、经验、词表与权重，不是可执行源码。
- **对机器人**：任务策略越用越稳；执行层的限速/急停/否决权不变。

### 基础情绪：沙盘自我情绪，硬隔离

推理**结束后**，核心评估的是“这次产物怎么样”，不是用户情绪：

- 状态：`valence / arousal / trigger / 衰减`；
- 白名单作用：只影响**语气、质量标注、日志**；
- **不参与**：句法、实体、意图、派发、检索、证据、校验、动作；
- 不识别用户情绪；失败样本进入学习池，但**不带情绪数值**。

一句话：情绪是“自检信号”，不是“决策变量”；演化是“经验复利”，不是“自改代码”。

## 它不是什么

- ❌ 不是端到端大模型，不替代 VLA / 扩散策略。
- ❌ 不是实时运动控制器，不直接生成关节力矩。
- ❌ 不是云端服务，不需要联网激活或心跳。
- ❌ 不是用户情绪识别，也不拿情绪影响执行。
- ❌ 不是自修改代码；演化只发生在规则/经验/词表层。
- ❌ 不是“通用人工智能”，它是一个**工程化的认知中间层**。

## 开闭边界（Open Core）

| 层 | 内容 | 许可 |
|---|---|---|
| **开放框架** | 认知循环、插件协议、ROS 2/传感器/执行器适配、CLI/HTTP 壳、文档、示例、契约测试 | AGPL-3.0-or-later |
| **闭源核心** | 骨架编排、底层法则、基础词汇/账本、推演引擎、合成引擎、安全引擎 | Proprietary（二进制 wheel） |

开放的是**怎么接**，闭源的是**怎么想**。  
没有核心时，框架仍可运行（`NullCore`），并给出明确安装提示；装上核心后自动切换。

> 为什么核心不开源：它是长期迭代的推理/取证/合成资产。框架与接口保持开放，保证可集成、可替换、可审计。

## 快速开始

```bash
git clone https://github.com/heihei6661/JMGo-SI.git
cd jmgo-cognition
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

先跑一个“没有核心”的闭环，确认框架可用：

```bash
python -m jmgo_cognition.cli "把桌上的杯子拿过来"
```

输出会包含每一步的结构化 trace，并提示：

```
[core] jmgo_core not installed — running NullCore (framework demo only)
```

安装核心（二选一）：

**A. 公开二进制（推荐，别人可直接用）**

```bash
bash scripts/install_core.sh          # macOS / Linux
# Windows:
pwsh scripts/install_core.ps1
```

装到 `~/.jmgo/bin/jmgo_core`，框架会自动发现；也可用 `JMGO_CORE_BIN=/path/to/jmgo_core` 指定。

**B. 私有 wheel（授权客户）**

```bash
pip install jmgo_core-0.1.0-cp312-cp312-macosx_11_0_arm64.whl
```

然后：

```bash
python -m jmgo_cognition.cli "把桌上的杯子拿过来"
```

动作层不依赖核心，可直接看“任务→动作→安全→人话”的闭环：

```bash
python -m jmgo_cognition.embodied --demo "把桌上的杯子拿过来"
```

## 五个稳定接口

框架只通过这五个入口调用核心，全部是 JSON 可序列化数据：

```python
core.version() -> {"version": "...", "capabilities": ["self-evolution", "self-emotion", ...]}
core.plan(query, ctx) -> {"queries": [...], "slots": {...}}
core.retrieve(plan, ctx) -> {"items": [{"title": ..., "snippet": ..., "source": ...}]}
core.reason(query, evidence, ctx) -> {"answer": ..., "status": ..., "basis": [...]}
core.verify(answer, ctx) -> {"ok": bool, "reasons": [...]}
```

另有**可选**的只读能力 `reflect()`：推理结束后返回沙盘自我情绪/质量标注；框架只记录，不改变答案、校验或动作。
详见 [docs/api-contract.md](docs/api-contract.md)。接口用语义版本管理；框架不 import 核心内部模块。

## 从认知到动作：三层

只有认知会“很呆”——它知道要做什么，但不会把任务拆开、不会生成平滑动作、也不会讲人话。动作层补上这三件事：

### ① 任务拆解公理（`task_axiom.py`）

不枚举任务类型，按**前置条件链**展开：

```
定位 → 接近 → 准备 → 执行 → 校验 → 交付/返回
```

上下文已满足的前置条件会跳过，「校验」永远保留；非物理任务返回 `applicable=False`，交回对话层。

`把桌上的杯子拿过来` → 定位杯子 → 到位 → 抓取 → 校验 → 送到交付点。

### ② 通用扩散公理（`diffusion.py`）

`DiffusionSampler` 对任意 `T×D` 计划做退火去噪：给定能量负梯度与约束投影，即可采样。
2D 轨迹只是它的一个特例（`DiffusionPlanner`）。安全闸检查碰撞、步长、边界、终点容差、有限性。

真实学习策略（LeRobot / 自训 Diffusion Policy）实现 `ActionPolicy.sample()` 即可替换；
`CallablePolicy` 负责包一层并校验形状。

### ③ 文本渲染层（`render.py`）

把“步骤 + 动作块 + 安全结论 + 缺口”讲成人话，不贴 JSON/数组，并明确：

> 以上是计划，尚未执行；执行层保留限幅与急停。

效果：

```
把「把桌上的杯子拿过来」拆成 4 步（按前置条件排序）：
1. 移动到可操作「杯子」的位姿
2. 抓取「杯子」
3. 确认「杯子」状态符合预期
4. 把「杯子」送到「用户/交付点」
动作块：21 个增量，最大步长 0.40 m；安全闸通过（无碰撞、不越界、终点在容差内）。
以上是计划，尚未执行；执行层保留限幅与急停。
```

### 串起来（`embodied.py`）

```
任务文本 → 拆解 → 扩散 → 安全闸 → 渲染
```

```python
from jmgo_cognition import run_task
r = run_task("把桌上的杯子拿过来", {"start": [0, 0], "goal": [6, 4], ...})
print(r["text"])
```

诚实说明：默认采样器是 **training-free** 的，不是训练好的 DP；它的价值是先把闭环跑通。
有演示数据/权重后，直接换成学习策略，拆解层与渲染层不变。

## 接入机器人

### ROS 2（推荐）

`examples/ros2_bridge.py` 给出了最小桥接：

- 订阅 `/perception/objects`、`/perception/asr`、`/odom`
- 调用 `run_loop()` 得到“建议动作 + 依据”
- 发布 `/cognition/decision`，由执行层（Nav2 / MoveIt / 自定义 action）决定是否执行

框架**不直接发控制指令**；执行层保留最终否决权和急停。

### 自定义硬件

实现两个协议即可：

```python
class SensorAdapter(Protocol):
    def read(self) -> dict: ...

class ActuatorAdapter(Protocol):
    def execute(self, action: dict) -> dict: ...
```

示例见 [examples/minimal_agent.py](examples/minimal_agent.py) 与 [docs/robot-integration.md](docs/robot-integration.md)。

## 目录结构

```
jmgo_cognition/        开放框架（本仓库）
  api.py              核心接口 + NullCore + 加载器
  loop.py             感知→意图→规划→行动→校验 的编排
  cli.py              命令行入口
  task_axiom.py       任务拆解公理（前置条件链）
  diffusion.py        通用扩散公理（T×D 计划 + 安全闸）
  render.py           文本渲染层（步骤/缺口/安全结论）
  embodied.py         动作闭环（拆解→扩散→安全闸→渲染）
  plugins/            传感器/执行器/插件协议与示例
docs/                 架构、接口、规则 DSL、词表 schema、安全
examples/             最小 agent、ROS 2 桥接
tests/                契约测试（无核心也能跑）
```

## 路线图

- [x] v0.1 框架、接口、NullCore、契约测试
- [ ] v0.2 ROS 2 适配器与安全闸示例
- [x] v0.2 动作层：任务拆解公理 + 通用扩散 + 文本渲染 + 安全闸
- [ ] v0.3 规则 DSL 与词表导入格式
- [ ] v0.4 多模态感知适配（视觉/语音/激光）
- [ ] v0.4 自我演化工具链（版本化查看/回滚）与 `reflect()` 示例（核心能力已在，开放层补工具）
- [ ] v1.0 稳定 ABI 与核心 wheel 发布

## 安全与隐私

- 默认**不联网、不上报、不激活**；核心检查只在启动时做一次本地校验。
- 核心若检测到被篡改，只会**停用/销毁核心自身**，不触碰用户数据、日志与项目文件。
- 漏洞请按 [SECURITY.md](SECURITY.md) 私下报告，不要开公开 issue。

## 贡献

欢迎插件、适配器、文档、示例和契约测试。请先读 [CONTRIBUTING.md](CONTRIBUTING.md) 与 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)。

## 联系

**成都维舜骅呈科技有限公司**  
邮箱：2690325118@qq.com  
仓库：[github.com/heihei6661/JMGo-SI](https://github.com/heihei6661/JMGo-SI)

## 许可与商用

- **框架代码**：[AGPL-3.0-or-later](LICENSE)（开源；衍生分发与网络服务需履行 AGPL 义务）
- **核心二进制 `jmgo_core`**：专有许可，不在 AGPL 范围内，见 [NOTICE](NOTICE)
- **商用/闭源部署**（商业产品、托管服务、随硬件分发、内部商业系统等）：
  需获得**商业授权**，见 [COMMERCIAL.md](COMMERCIAL.md)；
  联系：成都维舜骅呈科技有限公司 · 2690325118@qq.com
- 第三方数据（UD 树库、GeoNames、zhconv 等）遵循各自许可

> 若你选择遵守 AGPL-3.0（公开衍生源码/网络服务源码），可无需商业授权使用框架；
> 不能遵守 AGPL 的商业使用，必须取得书面商业授权。核心二进制始终需要授权。

---

**English abstract.** JMGo MetaCognition is an offline-first, explainable cognitive skeleton for embodied agents. It exposes a stable five-call core API (plan / retrieve / reason / verify / version) and keeps perception and actuation as open adapters. The framework is AGPL-3.0-or-later; the reasoning core ships as a proprietary binary. No cloud dependency, no telemetry, no runtime license heartbeat.
