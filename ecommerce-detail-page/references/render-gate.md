# 可选生图闸门

本文件只负责在全部正式分镜提示词完成发布后，按用户明确选择调用当前环境可用的图片生成能力。它是可选旁路，不是提示词编译器的一部分；默认停在提示词交付，不自动生图，也不把候选数量写回商品、图组或提示词合同。

## 目录

`不可变边界` / `状态机` / `提示词交付后的选择` / `生图请求合同` / `执行与追溯` / `结果诊断循环` / `最小提示词补丁` / `进化边界` / `输出接口`

## 不可变边界

1. 先完整交付已发布的逐张分镜提示词，再提供生图选项；禁止边写提示词边生成。
2. 没有用户明确选择时保持 `NOT_OFFERED` 或 `OFFERED`，不得自动调用生图工具。
3. 只能生成已发布的分镜；草案、待确认、失效或被补丁替换的版本不得生成。
4. 生图范围和候选数量是当前生图请求，不是正式分镜字段，也不是长期偏好。
5. 每个目标必须冻结 FR/PR 的`release_pair`与共同`source_artifact_id`；执行前解析两个发布信封和来源草案，任何版本、配对、来源或当前状态不一致都使请求进入`INVALIDATED`。
6. 生图结果不能反向篡改已发布的 FR/PR。发现问题时先诊断，再创建可追溯的最小提示词补丁和新的原子 FR/PR 配对。
7. 没有可用生图工具时仍完整交付提示词，并说明当前环境不能执行生图；不得伪造结果或改变核心交付。

## 状态机

```text
NOT_OFFERED -> OFFERED
OFFERED -> CONFIGURED | CANCELLED
CONFIGURED -> GENERATING | INVALIDATED | CANCELLED
GENERATING -> REVIEWED | FAILED | INVALIDATED | CANCELLED
REVIEWED -> ACCEPTED | PATCH_REQUIRED | INVALIDATED | CANCELLED
PATCH_REQUIRED -> CONFIGURED | INVALIDATED | CANCELLED
FAILED -> CONFIGURED | INVALIDATED | CANCELLED
```

- `NOT_OFFERED`：提示词尚未全部发布，或用户尚未看到正式分镜。
- `OFFERED`：正式分镜已交付，已提供生图范围选择，尚未配置。
- `CONFIGURED`：用户已明确选择范围和每张候选数量。
- `GENERATING`：正在按冻结版本逐张生成。
- `REVIEWED`：结果已与对应分镜/提示词合同核对。
- `ACCEPTED`：结果通过审计且用户接受，或用户明确结束已完成的生成任务。
- `PATCH_REQUIRED`：结果暴露可定位的提示词、参考图、生产或上游问题。
- `FAILED`：工具、配额或执行环境失败，尚未证明提示词有错；可重配后重试或结束。
- `INVALIDATED`：绑定的提示词/分镜版本或目标已变化，旧请求不得继续执行。
- `CANCELLED`：用户选择暂不生图、取消尚未接受的请求或不再重试；提示词发布版本保持有效。

任一提示词或分镜发布版本更新后，与旧版本绑定且尚未进入`ACCEPTED/CANCELLED`终态的生图请求立即转为`INVALIDATED`；这包括`CONFIGURED/GENERATING/REVIEWED/PATCH_REQUIRED/FAILED`。必须创建新请求并重新绑定版本，不得原地替换版本继续执行；已`ACCEPTED/CANCELLED`的历史请求只保留追溯记录，不改写状态。

## 提示词交付后的选择

只在正式 Markdown 分镜源码块之外提供紧凑选项：

0. **暂不生图**：把当前生图状态设为`CANCELLED`，保留提示词发布版本，结束本次任务。
1. **指定分镜**：用户给出一个或多个真实分镜编号。
2. **当前图组全部**：生成刚交付的当前对象/图组。
3. **全部图组**：生成本轮全部已发布图组。
4. **自定义数量**：在所选范围内为每张分别设置候选数。

若用户在原始请求中已经明确“提示词完成后生成全部、每张 N 张”，提示词发布后可直接把该明确要求映射为`CONFIGURED`，但仍必须先展示/交付正式提示词，再开始生成。不得从含糊的“做图”“出图”推断候选数量。

## 生图请求合同

```yaml
render_request_id: stable-id
scope: selected_frames/current_group/all_groups
targets:
  - storyboard_id: 主图-02
    frame_release_version: FR-003
    prompt_release_version: PR-004
    release_pair: {frame: FR-003, prompt: PR-004}
    source_artifact_id: frame-draft-002
    candidate_count: 3
status: CONFIGURED
requested_by: 当前用户明确指令
created_at: ISO-8601
```

- `storyboard_id` 使用最终分镜真实编号，不能创建新页码。
- `release_pair.frame/prompt`必须分别等于`frame_release_version/prompt_release_version`；FR与PR信封必须都为当前`RELEASED`、记录相同`release_pair`，并共同记录同一`source_artifact_id`，来源草案未`STALE`且仍绑定当前输入合同。任一条件不成立时拒绝执行并把请求标为`INVALIDATED`，不得拼接两个独立发布版本。
- `candidate_count` 必须是每张明确数量；统一数量可展开到每个 target。
- 未指定数量时只询问一次最小必要问题，或在用户允许自主决定时采用每张 1 张的保守默认。
- 配额、工具或环境限制导致无法完成时，只缩小生图执行或请求用户裁决，不修改已交付提示词。

## 执行与追溯

按目标逐张调用当前环境正式提供的图片生成工具。每个结果使用：

`storyboard_id + frame_release_version + prompt_release_version + release_pair + source_artifact_id + render_variant`

例如：`主图-02 + FR-003 + PR-004 + {FR-003,PR-004} + frame-draft-002 + v1`。候选只是生图候选，不是新分镜，也不改变图组数量。提示词发布版本统一使用`PR-001`、`PR-002`等命名，避免与参考图能力`P0-P4`混淆。

工具输入只能使用该分镜的已发布提示词、负面约束、被明确支持的参考图和当前生图请求；不得把内部评分、角色争论、进化记忆原文或其他分镜提示词混入调用。

## 结果诊断循环

每张结果执行：

`RESULT -> COMPARE -> DIAGNOSE -> ACCEPT | MINIMAL PATCH -> OPTIONAL RERENDER`

按最早失败层比较：

1. 商品/SKU身份与真实像素层。
2. 几何、视角、材质、颜色、文字、包装和配件。
3. 尺度、人物接触、遮挡、重力、阴影和场景物理。
4. 单图任务、图组角色、构图、信息安全区和视觉连续性。
5. 提示词指令冲突、歧义、负面过载或工具能力不匹配。

背景正确而商品失败时保留背景与构图，只修商品层或切换真实商品合成；单个候选偶发失败不自动证明提示词错误。只有可重复、可定位的问题才创建补丁。

## 最小提示词补丁

补丁必须记录：

- 对应 `storyboard_id`。
- 原 `frame_release_version + prompt_release_version + release_pair`。
- 失败证据与最早失败层。
- 保留不变的分镜正文与提示词片段。
- 只替换的最小片段。
- 新 `frame_release_version + prompt_release_version + release_pair`。
- 受影响的旧生图候选。

“最小”只表示语义修改最小，不允许单边升级 PR。仅修改提示词的补丁必须把未改变的分镜正文复制到新 FR，让新 FR 与新 PR 以同一`release_pair`先进入`PENDING`，确认或自动内审后原子`RELEASED`；此时旧 FR/PR 同步转为`INVALIDATED`并保留追溯记录。若新配对未完整提交，旧配对保持当前状态且不得部分替换。补丁发布后，如用户要求重生，只重新生成受影响分镜和明确数量；不得默认重跑整组。

## 进化边界

- 候选数量只属于当前生图请求，不进入长期偏好；“这次每张生成 4 张”不构成分镜审美或协作偏好。
- 用户从候选中明确选择或明确否定某种构图、场景、人物、保真或提示词表达时，个人偏好学习角色可按 `persistence-evolution.md` 记录相应分镜信号。
- 用户没有评价的候选、随机差异、工具故障和数量选择不得强化进化记忆。
- 每次有效候选反馈先增量合并到本轮学习快照；用户暂不生图、明确结束，或请求进入`ACCEPTED/CANCELLED`后刷新最终学习包。若用户以后恢复同一任务的生图，新增反馈继续按来源追溯增量合并，不覆盖先前事件。

## 输出接口

向主控返回：生图状态、目标编号、冻结的分镜/提示词发布版本、`release_pair`、`source_artifact_id`、每张候选数量、配对与来源校验结果、结果追溯、已接受候选、失败层、最小补丁、新旧`release_pair`与是否需要用户重新选择。生图日志不得进入正式分镜源码块。
