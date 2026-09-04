# Bubble Timeline Config

面向 Bubble Unity 项目的 Timeline 配置与审计 Skill。

它帮助 AI 根据项目代码、已有 Timeline、Spine 角色动作、角色动作规划表和剧情配置规律，完成：

- 剧情演出分镜与动作资源选择
- Unity Timeline、Director Prefab、Spine Track 和绑定配置
- `tPlot`、`tPlotStep`、`tPlotTimeLine` 联动检查
- 分段续播、暂停点、气泡和多角色演出设计
- Timeline 静态审计与 Unity 播放验证清单

## 使用

在支持 Codex Skill 的环境中调用：

```text
使用 $bubble-timeline-config。
请先阅读 USAGE.md，根据我的剧情需求给出配置前审阅方案。
```

具体需要提供什么信息，请查看 [USAGE.md](USAGE.md)；执行规则和技术约束请查看 [SKILL.md](SKILL.md)。

## 目录

- `SKILL.md`：Skill 执行规则
- `USAGE.md`：需求方使用说明和需求模板
- `agents/openai.yaml`：Skill 展示和默认调用提示
- `scripts/audit_timeline.py`：Timeline 静态审计脚本

本 Skill 面向 Bubble 项目使用，项目路径、资源路径和动作规划表以实际工程为准。未经确认的 ID、坐标、时间、语言 ID 和资源替代方案不得直接视为正式配置。
