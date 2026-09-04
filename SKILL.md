---
name: bubble-timeline-config
description: Configure, extend, or audit Bubble Unity Timeline assets and their tPlot/tPlotStep/tPlotTimeLine integration, including Spine action selection, Director bindings, clip timing, segmented playback, UI or mining placement, and delivery QA. Use for Bubble Timeline配置、剧情演出、角色动作编排、Timeline分段续播 or repairing existing Plot Timeline resources; do not use for dialogue-only or event-only table work with no Timeline changes.
metadata:
  author: Bubble project
  version: "1.0.1"
---

# Bubble Timeline 配置

把自然语言演出需求转成可审查、可落地、可验证的 Unity Timeline、Director Prefab 和剧情配置。保留用户现有改动；未经授权不执行 SVN 操作。

## 用户使用说明

面向需求方的输入清单、可复制需求模板、确认流程和交付说明见 [USAGE.md](USAGE.md)。收到的信息不完整时，按该说明区分必须由用户确认的决策与可从项目读取的事实；不要要求用户重复提供可以在当前工程中可靠查到的信息。

## 每次任务先做

1. 定位 Bubble Unity 项目根目录。优先使用当前工作区中同时包含 `Assets/GameAssets`、`AGENTS.md` 的目录；当前常用目录为 `D:/Bubble/Code/BubteaHam_trunk`，但必须实际确认。
2. 完整读取项目根目录的 `AGENTS.md`、`Assets/GameAssets/Scripts/Game/Common/PlotSystem/README.md` 和 `Assets/Docs/ai/timeline-configuration-guide.md`。手册不存在或比目标资源旧时，重新审计当前代码与资源并报告差异。
3. 涉及 Spine 动作时，读取当前 `Spine/Character` 下的真实 `AnimationReferenceAsset`，并按需读取 `D:/Bubble/奶茶鼠角色规划与id列表.xlsx` 的 `角色动作列表`、`规划说明`、角色 ID 或敌人动作 Sheet。
4. 涉及 `tPlot`、`tPlotStep`、`tPlotTimeLine` 时，读取当前代码和正式源表 `D:/Bubble/策划/配置表/Table/J_剧情表_tPlot.xlsx`。源表存在时，不把生成物 `tTableRoot.asset` 当成正式编辑源。
5. 任务包含剧情、对白、事件或引导配置时，同时使用 `bubble-story-event-guide-config`；任务包含正式 Excel 配表时，同时遵守 `bubble-config-table-generator` 和当前电子表格工具要求。

## 工作模式

- 方案模式：用户要求设计、分析或给方案时，只输出分镜、资源映射、固定值和风险，不修改文件。
- 配置模式：用户明确要求创建或修改 Timeline 时，先完成“配置前审阅”，获得确认后再修改资源和源表。
- 审计模式：用户要求检查时，执行静态审计并说明哪些结论仍需 Unity 播放验证；不顺手修复未授权问题。

## 配置前审阅

修改前必须给用户一份简洁方案，至少包含：

| 项目 | 必须说明 |
|---|---|
| 需求分镜 | 每个关键时间点发生什么 |
| 角色资源 | 角色/皮肤 ID、资源族、SkeletonDataAsset、AnimationReferenceAsset、实际 `animationName` |
| 轨道 | 每个对象的 Animation、Activation、Spine、气泡或其他 Track |
| 时间 | Start、Duration、End、Loop、暂停点和总时长 |
| 运行配置 | Timeline 配置 ID、Director 路径、createWay、坐标/层级、endTime、点击、保留、黑屏 |
| 固定值 | 所有新增或修改的 ID、路径、坐标、时间、语言 ID 和固定映射及来源 |
| 风险 | 缺失资源、命名漂移、旧绑定、未确认时长和无法执行的验证 |

给每个关键输入标记来源：`S` 用户/策划明确值、`T` 当前项目事实、`D` 可验证推导、`A` AI 建议。`A` 类值不得冒充正式值。会改变演出结果的缺失值必须请求确认。

## 不可破坏的配置契约

- `tPlotTimeLine.timeLinePath` 指向 `DirectorXXXX.prefab`，不指向 `.playable`。
- Director Prefab 的 `PlayableDirector.m_PlayableAsset` 必须指向目标 TimelineAsset；`m_SceneBindings` 的 Track GUID 和 fileID 必须属于当前 Timeline。
- Spine Clip 绑定 `AnimationReferenceAsset`。真实动作以其 `animationName + SkeletonDataAsset` 为准，不以文件名、Clip `m_DisplayName` 或 Excel 规划名为准。
- 不跨 SkeletonDataAsset 复用同名动作。角色专用 `{动作名}_{角色ID}` 变体在 Timeline 中必须显式选择，不能假设 `SpineAnimator` 会自动回退。
- 60 FPS Timeline 优先使用帧边界。`endTime` 是 Timeline 的绝对毫秒时间点，不是本段时长；现有规则为 `ceil(frame / 60 * 1000)`。
- 分段续播使用同一个 Director 路径；中间段 `closeToDelete = 1`，后续 `endTime` 必须严格增大或最终为 0，最终段通常 `closeToDelete = 0`。首次创建后不要给续播段重复黑屏。
- 角色移动时，Transform 位移与 walk/run Spine Clip 同起同止；角色可见期间无意的动作空档用合适的 idle 填充。
- Activation 覆盖完整可见区间，并跨过需要保持画面的分段暂停点。
- 持续状态可循环；状态切换、受击、解锁、结果等一次性动作通常不循环。不要机械复制 `tSpineAnimKey.repet`，以本段剧情语义和真实动作表现为准。
- 不根据配置主键数字推导业务语义，不自动发明 ID、坐标、路径、语言 ID、动作资源或正式时长。
- 不直接手改正式导出数据来代替源 Excel 配置，不执行未经授权的 SVN add/commit/revert 等操作。

## 动作和时间决策

先在 `timeline-configuration-guide.md` 中按需求类型查找最接近样本：

- 普通入场/离场：walk 或 run + Transform，结束切 idle。
- 跌落/眩晕：`cm_fall01 → cm_fall02 → 可选 sit → idle`。
- 发现/惊讶：`idle → shock → idle/移动/功能动作`。
- 解锁：`idle → unlock → 短 idle → 后续反应`。
- 挖掘/维修/使用道具：到位 → 短 idle → dig/repair/use → 结果或 idle → 离开。
- 偷懒：开始段 → 循环段 → 结束段；是否省略开始段必须由镜头初态支持。
- 多角色：先建立全局剧情关键点，再分别排每个角色的三轨组合。
- UI 与对白穿插：在目标 UI 出现前的关键帧暂停，执行对话后从同一 Director 继续。
- 气泡：时长服从配音、文本和演出。项目现有 2 秒样本不构成统一字速标准。

现有 Clip 时长只是样本，不是 Spine 原始时长。移动、idle、循环操作的 Duration 由剧情阶段决定；一次性动作优先保持 TimeScale 为 1 和 ClipIn 为 0，确需裁切或同步时说明理由。

## 实施要求

1. 选择最接近的正式样本；复制后重新检查名称、GUID、Track fileID、SceneBindings 和资源路径，不能只改文件名。
2. 每个角色建立清晰的 Track 分组，绑定到正确对象。不要手工臆造 Unity fileID 或资源 GUID。
3. 新增资源必须有对应 `.meta`；保留项目要求的文本换行和编码。
4. 需要配置表时，在源 Excel 的正确 Sheet 中按现有协议、ID 段、样式和 END 规则生成可审查副本或按相关 Skill 的流程处理，再通过项目导表流程生成运行时数据。
5. 如果当前环境不能安全编辑 Unity 序列化资源，交付可执行分镜和逐项 Inspector 配置清单，并明确阻塞点；不要生成看似完整但无法绑定的 YAML。

## 静态审计

修改前后运行。优先通过 `load_workspace_dependencies` 获取工作区 bundled Python；不要假设 Windows 的 `python`/`py` 别名可用：

```powershell
& '<bundled-python>' scripts/audit_timeline.py --project-root <Bubble Unity项目根目录>
```

只检查一个 Timeline 或目录：

```powershell
& '<bundled-python>' scripts/audit_timeline.py --project-root <项目根目录> --timeline Assets/GameAssets/WorkDir/PackedResources/Timeline/PlotXXXX
```

脚本非零退出表示发现错误。全项目审计可能包含与本次无关的历史问题；只修复用户授权范围内的问题，并把其余问题列为既有风险。

静态审计至少覆盖：

- Timeline/Director 路径和 PlayableAsset 引用。
- 缺失 AnimationReferenceAsset GUID。
- 当前 PlayableAsset 没有有效 SceneBinding、绑定到旧 Timeline 或 value 为空。
- `tPlotStep` 引用了不存在的 `tPlotTimeLine`。
- 同一路径分段的 `endTime` 未递增。

## Unity 验证

静态检查不能证明视觉表现正确。可用 Unity 时验证：

- 骨骼、皮肤、动作和朝向正确。
- 移动无滑步，Clip 没有非预期裁切或混合。
- Activation 无闪现或残留。
- 暂停点精确，对话后从原时间续播。
- 完整播放、点击关闭、跳过和异常中断后都能恢复输入并正确清理。

未执行 Unity 播放时，交付成熟度必须写“静态配置完成，待 Unity 播放验证”，不能写“已完全验证”。

## 交付

最终输出：

- 修改文件和绝对路径。
- 最终分镜表：对象、动作资源、Start、Duration、End、Loop 和绑定。
- `tPlotTimeLine` 与剧情步骤配置摘要。
- 固定值及 S/T/D/A 来源。
- 静态审计结果、既有风险和本次新增问题。
- Unity 播放验证结果或明确的待验证清单。
