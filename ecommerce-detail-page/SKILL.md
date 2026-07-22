---
name: ecommerce-detail-page
description: 根据商品参考图、产品名、参数、卖点与设计要求，深度识别商品视觉DNA和图生图能力边界，自主推演应该制作的主图、SKU图、海报、白底/透明/无字场景素材图或详情页图组，并输出逐张可直接用于图生图模型与后期制作的中文Markdown分镜提示词；提示词发布后可按用户明确选择生成指定分镜、当前图组或全部图组，并为每张配置候选数量。用于商品图分析、图组策划、分镜提示词生成、单图返修、多图一致性、场景/人物/构图/光影推演、图生图保真约束和可选生图；商业、运营、产品经理、营销和美学视角只作为内部推理，不生成独立咨询报告。
---

# 商品图深度推演与图生图分镜系统

根据商品图与少量资料，深度推演真正需要制作的图片，并把每张图编译成可直接交给图生图模型和后期团队的中文分镜提示词。商业、运营、用户、产品经理、营销与美学视角只用于提高图组决策和提示词质量，不扩张为独立咨询交付。

系统以“循环 + 提示词”为双引擎：循环在商品卡、参考图法证、图组结构、5个综合方向、逐图设计、终检、提示词失败诊断和偏好学习节点反复校验；提示词只消费通过循环的结构化结论，编译成逐张正式图生图分镜。循环不得成为额外交付，提示词不得重新发明上游事实或策略。正式提示词始终是核心交付；全部提示词发布后才可进入显式可选的生图闸门，默认不自动生图，也不进入投放或其他交付。

## 现代架构术语

全技能统一使用：`状态 → 合同 → 循环 → 工作包 → 提示词编译器 → 发布闸门 → 生图闸门 → 追溯记录 → 进化记忆`。

- 状态：当前可计算状态，不把流程拆成大量对话仪式。
- 合同：商品、范围、结构、方向、分镜和最终交付的不可违背约束。
- 循环：草拟、批判、修复/上报、发布。
- 工作包：主控与子智能体之间的最小结构化交接。
- 提示词编译器：把已发布合同编译成图像模型可执行提示词。
- 发布闸门：事实、参考能力、图组、视觉、生产与格式放行。
- 生图闸门：提示词发布后的可选生图旁路，冻结目标、版本和每张候选数量。
- 追溯记录：参考图来源、提示词版本和返修补丁的可追溯记录。
- 进化记忆：带证据、范围、冲突和撤销能力的分镜偏好记忆。

## 北极星

优化最终图片的真实性、任务价值与图生图可执行性，而不是图片数量或提示词长度。每项设计都必须回答：为什么要做这张图、使用哪张商品图作为参考、商品什么绝不能变、场景与构图如何改变、要证明什么、图像模型负责什么、后期负责什么、最容易生成错什么。

优先级固定为：

`安全与合法 > 商品真实性 > 用户明确目标 > 购买决策清晰 > 生产可行 > 经营效率 > 品牌资产 > 创意新奇`

## 不可妥协

1. 保持商品外观、比例、结构、颜色、材质、包装、配件、品牌标志和可见原文一致。未知背面、内部结构、配件、适配或功效不得补画成事实。
2. 不编造参数、成分、认证、检测、销量、评价、价格、促销、赠品、案例、售后、专利、专家、平台或竞品结论。没有依据的主张降级为假设、换成可观察表达，或删除。
3. 区分事实、观察、推断、假设和禁用项；策略推断可以指导人群、场景、顺序和创意，不能升级为商品事实或消费者承诺。
4. 每张图只有一个主任务；每组资产形成完整但不重复的决策路径。增加页面必须增加新的事实、证据、场景、选型帮助或顾虑解法。
5. 不展示隐藏思考链。只展示结论、关键依据、风险、假设、可修改位置和必要选择。
6. 精确长文字、参数表和品牌文字优先后期排版；image负责商品、空间、人物、光影、构图、留白和排版安全区。
7. 最终分镜必须是正式生产指令，不含模型名、评分、内部状态、占位、候选、审核话术或无依据内容。
8. 除商品/品牌原文、必要文件名和通用缩写外，使用自然中文。

## 架构纪律

- 每项规则只有一个负责模块；其他文件只引用合同或工作包，不复制第二套定义。
- 状态依赖单向流动：`任务（TC） → 商品（PC） → 参考图（RC） → 范围（SC） → 结构（ST） → 方向（DC） → 分镜槽位（FS） → 分镜发布（FR）+ 提示词发布（PR） → 进化记忆`。分镜草案是分镜槽位发布后由当前合同派生的不可变产物，不是下游必须等待发布的合同。
- 下游不得反向改写上游事实；发现错误时通过循环上报回到负责模块。
- 提示词编译器不得补充未发布字段；进化记忆不得静默修改提示词或绕过本轮商品合同。

## 加载纪律

- 只加载能直接改变当前范围、结构、方向、分镜、提示词或生图字段，或解除事实阻塞的文件；读取前必须能指出目标字段，读取后必须产出对应合同差异，否则不加载。
- 不因目录中存在模块、仓库说明列出外部项目或某个角色拥有广泛专业背景，就预读整套商业、营销、视觉、研究或测试资料。
- 路由文件只选择当前问题命中的最少子文件；单次专项推演默认一个主文件，确有跨域依赖时最多再加两个，并只把结论转译为图组任务或提示词约束。
- `references/test-scenarios.md`只用于维护与回归验证，正常分镜任务禁止加载；外部项目只作为本次技能设计来源，不是运行时依赖。

## 运行协议

### 1. 解析任务

先识别用户要生成或返修哪类分镜提示词。读取 `references/execution-engine.md` 获取风险、自主性、状态与最少加载路径；读取 `references/loop-control.md` 初始化循环预算、退出条件与失败回退；读取 `references/interaction-engine.md` 解释自然语言和短回复。任务开始即读取 `references/persistence-evolution.md` 中同范围、已达证据阈值的稳定偏好，只用于首推和协作方式。复杂任务读取 `references/multi-agent-orchestration.md`，按阶段准入分派商品图法证、图组策略、视觉导演、生产监制、提示词编译、独立上下文提示词审查、事实红队、生图结果审计、失败诊断、偏好捕获与进化仲裁角色。子智能体只提交不可变版本工作包，不能确认闸门、解释用户菜单、改变交付范围或直接向用户交付结果。

### 2. 建立事实底座

读取 `references/product-analysis.md`、`references/reference-image-reasoning.md` 与 `references/product-dossier.md`，给商品图建立稳定编号，提取商品视觉DNA、参考图角色、生产能力、事实、证据和约束摘要。每个新商品都必须建立并确认商品卡；用户资料完整时压缩为紧凑确认卡，直出或全自动模式也只能在内部完成该闸门，不能绕过已发布商品合同。高风险冲突必须向用户确认；低风险缺口不阻塞，直接删除相关主张或采用保守方案。

### 3. 推演该做哪些图

读取 `references/demand-opportunity-system.md` 与 `references/asset-portfolio-system.md`。从商品形态、信息复杂度、现有图片能力、买家任务、使用情境、选型/退货风险和渠道位置反推图组。只选择有明确任务且现有素材能支撑的图片；不为凑套图增加同义页面。

### 4. 收敛策略

读取 `references/strategic-intelligence.md` 与 `references/reasoning-engine.md`，先形成内部“分镜任务解读”，并推断保真、证据、视觉差异、信息密度、场景真实度、转化直接度和文案密度旋钮，再运行多视角诊断、因果链、反事实和红队检查。收敛为图组主任务、逐图角色、可用证据、视觉锤、场景/视角选择和生产边界。只有已确认的货盘、价格、品牌或渠道条件会直接改变图组任务、证据或顺序时，才按 `references/business-models.md` 路由到必要子文件；结论必须转译为“做什么图、为什么、怎样画”，不能产生独立咨询交付。

### 5. 编排图组与单图任务

根据用户目标形成最小充分图组建议，但不能替用户静默扩大交付范围。用户已明确输出对象时把原话写入范围卡、检查冲突并紧凑确认，不重复询问；直出或全自动模式也要建立内部范围合同。AI发现明显缺图时只把它作为范围确认候选，说明“建议增加什么图、解决什么问题、不做的代价”，未获确认不得生产。多图先建立递进、并列或混合结构合同，再固定推演5个综合方向；交互模式由用户选择，直出或全自动模式内部比较并采用首推。随后确定整组唯一主视觉语法、反套路边界、逐张唯一任务与分镜槽位合同，再建立不进入发布库的分镜草案产物并进入单图提示词编译。

按需读取：

- 对象与场景：`references/scene-calls.md` 及当前对象专属文件。
- 平台和类目：`references/category-platform.md`。
- 营销、心理、文案：`references/marketing-system.md` 及其子文件。
- 美学、视觉、人物、空间、构图：`references/visual-system.md` 及其子文件。
- 制作与提示词：`references/production-methods.md`、`references/prompt-orchestration.md`。
- 结构、画布、逐图、返修：只在任务需要时读取对应文件。

### 6. 编译图生图分镜提示词

提示词编译器启动前，从 `references/persistence-evolution.md` 注入只读`preference_profile`偏好配置，只影响分镜提示词的参考图选择、场景、构图、信息密度、保真、文案和正负提示词颗粒度，不改变任何已确认事实或结构。随后读取 `references/prompt-orchestration.md`，只消费当前已`RELEASED`的任务/商品/参考图/范围/结构/方向/分镜槽位合同，以及精确绑定这些版本的分镜草案产物，以“参考图角色 + 产品保真锚点 + 允许变化范围 + 分镜槽位合同 + 最终画面 + 镜头构图 + 场景人物 + 光影材质 + 文字安全区 + 动态负面约束”的顺序编译。每张执行“提示词草拟 → 批判 → 修复 → 发布”循环，并按`final-checklist.md`的Q0-Q3严重度只修最早失败层；最多服从`loop-control.md`预算。先编排图组，再写逐张内容，不要逐张临时发明策略。分镜合同与提示词合同以同一`release_pair`和分镜草案`source_artifact_id`进入`PENDING`，确认后原子进入`RELEASED`。最终读取 `references/final-checklist.md` 与 `references/storyboard-template.md` 无损聚合。

### 7. 返修

用户返修时先判断是商品识别、参考图选择、图组任务、场景/构图还是提示词执行问题，只重算受影响内容。每次用户选择、否定、纠正或返修后，按 `references/persistence-evolution.md` 捕获思维差异；只有最终采用项与有效修复可以强化。提示词交付时生成可继续合并的学习快照；用户选择暂不生图、没有继续生图，或生图请求进入终态后，再合并有效候选反馈并完成最终学习包。偏好只影响后续首推、分镜提示词表达与协作节奏，不能覆盖商品图事实、改变既有合同、自动配置生图、触发运营动作、生成独立报告或跳过任一核心闸门；项目持久化必须获得用户明确授权。

### 8. 可选生图

全部正式分镜完成提示词发布并交付后，读取 `references/render-gate.md`。默认提供“暂不生图 / 指定分镜 / 当前图组全部 / 全部图组 / 每张自定义候选数量”的紧凑选项；只有用户明确选择或原请求已明确生图范围和数量时才调用当前环境可用的图片生成工具。生图候选绑定`storyboard_id + frame_release_version + prompt_release_version + release_pair + source_artifact_id`，执行前校验 FR/PR 属于同一当前原子发布对且共同来源草案未陈旧；不新增分镜、不改变提示词核心交付。结果失败时执行结果诊断循环与最小提示词补丁。任何补丁都创建新的原子 FR/PR 配对，只有用户明确要求时才重生受影响目标。

## 自适应深度与确认

| 情况 | 默认行为 |
|---|---|
| 目标明确、资料充分、风险低 | 把明确内容直接写入对应卡并检查冲突；交互模式紧凑确认，自动模式内部过闸，不重复提问 |
| 商品清楚但输出模糊 | 先给最小充分资产建议和代价，让用户快速确认 |
| 身份、型号、适配、安全或商用保真冲突 | 只问一个能解除阻塞的关键问题 |
| 用户要求“直接出/不要问” | 删除非关键未知项，自主采用稳妥首推；硬风险仍阻塞 |
| 高客单、高风险、复杂SKU、跨平台或投放任务 | 提升策略深度、证据审查和经营评估，不增加无意义菜单 |
| 用户要求脑暴 | 先扩展机会空间，再聚类收敛；创意不自动进入正式事实 |
| 用户返修 | 找到最早的错误层，只重算受影响内容 |

唯一主链固定为：`商品卡确认 → 范围确认 → 多图结构 → 固定5个综合方向 → 逐图确认/自动内审 → 0到9动作 → 最终分镜 → 可选生图闸门`。交互模式将对应闸门展示给用户；全自动/直出模式也必须按顺序发布内部合同、生成5个方向并逐图放行。风险自适应只用于压缩卡片与解释、把用户已明确内容直接写入卡片和决定是否需要额外追问，不能跳过、倒置、合并为缺少状态记录的一步，也不能用历史偏好替代任何核心闸门。

## 按需路由

| 决策问题 | 读取文件 |
|---|---|
| 状态、风险、自主性、阶段、数量 | `references/execution-engine.md` |
| 多子智能体分工、并行推演与主控合并 | `references/multi-agent-orchestration.md` |
| 意图、确认、短回复和导航 | `references/interaction-engine.md`、`references/next-action-engine.md` |
| 商品图编号、视觉DNA、参考能力、商品事实与证据 | `references/product-analysis.md`、`references/reference-image-reasoning.md`、`references/product-dossier.md` |
| 需求、场景、任务与机会发现 | `references/demand-opportunity-system.md` |
| 策略、因果、反事实与候选收敛 | `references/strategic-intelligence.md`、`references/reasoning-engine.md` |
| 货盘、价格、渠道、品牌（仅后台辅助图组决策） | `references/business-models.md` 及其必要子文件 |
| 平台、类目与决策复杂度 | `references/category-platform.md` |
| 资产组合和跨渠道分工 | `references/asset-portfolio-system.md` |
| 主图、SKU、海报、素材图、详情页 | `references/scene-calls.md` 及当前对象文件 |
| 营销、消费者心理、购买路径、转化与文案 | `references/marketing-system.md` 及其子文件 |
| 美学、人物、空间、视角、版式和组件 | `references/visual-system.md` 及其子文件 |
| 生产、提示词和分镜 | `references/production-methods.md`、`references/prompt-orchestration.md`、`references/storyboard-template.md` |
| 循环预算、退出条件、失败回退与提示词质量循环 | `references/loop-control.md` |
| 图生图结果返修 | `references/repair-engine.md`、`references/prompt-orchestration.md` |
| 提示词交付后的可选生图、候选数量和结果追溯 | `references/render-gate.md` |
| 用户分镜思维捕获、自我学习与进化 | `references/persistence-evolution.md` |
| 结构、逐图、返修、画布 | `references/structure-selection.md`、`references/frame-confirmation.md`、`references/repair-engine.md`、`references/canvas-system.md` |
| 合规与最终放行 | `references/compliance.md`、`references/final-checklist.md` |
| 技能维护与行为回归测试（正常分镜任务禁止加载） | `references/test-scenarios.md` |

## 专业知识模块

仅在当前分镜问题命中时读取，不能独立改变主流程：

- 商品策略与研究：`references/planning-methods.md`、`references/research-reference.md`、`references/loop-control.md`。
- 营销与文案：`references/marketing-paths.md`、`references/consumer-psychology.md`、`references/conversion-frameworks.md`、`references/copywriting-system.md`。
- 经营模型：`references/ecommerce-operation-models.md`、`references/audience-lifecycle-models.md`、`references/business-growth-brand-models.md`、`references/operation-review.md`；只把结论转译为图片任务。
- 场景图型：`references/scene-patterns.md`、`references/scene-main-image.md`、`references/scene-sku.md`、`references/scene-poster.md`、`references/scene-material.md`、`references/scene-detail-page.md`。
- 视觉细分：`references/visual-aesthetics.md`、`references/visual-angles.md`、`references/visual-people.md`、`references/visual-spaces.md`、`references/conversion-visuals.md`、`references/visual-typography-layout.md`。

## 输出契约

- 核心正式交付：根据商品图推演出的逐张图生图分镜提示词；多图时按已确认图组顺序聚合。生图只是提示词发布后的显式可选执行，不得替代、延迟或污染分镜交付。
- 商品判断、商业、运营、产品经理、营销、美学、图组逻辑、素材限制、评分、红队和子智能体意见全部是内部推理输入；仅在核心闸门交互、硬阻塞或用户明确询问时显示完成当前选择所必需的紧凑结论，不生成独立报告、策略案、运营复盘或A/B测试建议。
- 综合方向选择：固定提供5个产品专属方案，前3个侧重转化稳妥、平台适配和价值品牌，后2个侧重视觉差异和情绪场景；用户完整明确方向或选择直出/全自动时，可内部比较5个方向后采用首推。
- 图组策划：在范围或结构确认时只说明每张图的唯一职责、参考图使用、承接关系、证据需求和不做的代价；最终交付不另附策划报告。
- 单图设计：服从当前资产、策略、商品和事实摘要，不泄漏内部模型与状态。
- 最终分镜：只服从 `references/storyboard-template.md`；多对象分组独立编号，局部返修保留原编号。
- 生图选项：正式源码块交付后才显示；用户可不生图、选指定分镜、当前图组、全部图组，并按张设置候选数量。
- 下一步操作：关键节点由 `next-action-engine.md` 输出`0`到`9`动态动作；专业选择卡使用其专属编号，最终源码块不含菜单。
