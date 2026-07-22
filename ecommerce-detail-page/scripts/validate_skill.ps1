param(
    [string]$SkillRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = 'Stop'
$failures = [System.Collections.Generic.List[string]]::new()

function Add-Failure([string]$Message) {
    $failures.Add($Message)
}

function Require-File([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) {
        Add-Failure "缺少必需文件：$Path"
        return $false
    }
    return $true
}

function Require-Pattern([string]$Path, [string]$Pattern, [string]$Description) {
    if (-not (Require-File $Path)) { return }
    $content = Get-Content -Raw -Encoding UTF8 -LiteralPath $Path
    if ($content -notmatch $Pattern) {
        Add-Failure "行为契约缺失：$Description"
    }
}

function Require-JsonFields($Object, [string[]]$Fields, [string]$Description) {
    if ($null -eq $Object) {
        Add-Failure "JSON结构缺失：$Description"
        return
    }
    $propertyNames = @($Object.PSObject.Properties.Name)
    foreach ($field in $Fields) {
        if ($propertyNames -notcontains $field) {
            Add-Failure "JSON字段缺失：$Description -> $field"
        }
    }
}

$skillRootPath = (Resolve-Path -LiteralPath $SkillRoot).Path
$referencesPath = Join-Path $skillRootPath 'references'
$skillPath = Join-Path $skillRootPath 'SKILL.md'
$agentPath = Join-Path $skillRootPath 'agents\openai.yaml'
$storyboardPath = Join-Path $referencesPath 'storyboard-template.md'
$renderPath = Join-Path $referencesPath 'render-gate.md'
$canvasPath = Join-Path $referencesPath 'canvas-system.md'
$repairPath = Join-Path $referencesPath 'repair-engine.md'

$requiredReferences = @(
    'execution-engine.md', 'interaction-engine.md', 'next-action-engine.md',
    'loop-control.md', 'reasoning-engine.md', 'demand-opportunity-system.md',
    'asset-portfolio-system.md', 'strategic-intelligence.md',
    'multi-agent-orchestration.md', 'product-analysis.md',
    'reference-image-reasoning.md', 'product-dossier.md',
    'production-methods.md', 'prompt-orchestration.md',
    'frame-confirmation.md', 'canvas-system.md', 'storyboard-template.md', 'final-checklist.md',
    'render-gate.md', 'persistence-evolution.md', 'test-scenarios.md'
)

Require-File $skillPath | Out-Null
Require-File $agentPath | Out-Null
foreach ($name in $requiredReferences) {
    Require-File (Join-Path $referencesPath $name) | Out-Null
}

if (Test-Path -LiteralPath $skillPath) {
    $skillText = Get-Content -Raw -Encoding UTF8 -LiteralPath $skillPath
    $skillLineCount = (Get-Content -Encoding UTF8 -LiteralPath $skillPath).Count
    if ($skillLineCount -ge 500) {
        Add-Failure "SKILL.md过长：当前$skillLineCount行，必须少于500行。"
    }
    if ($skillText -notmatch '(?s)^---\s*\r?\nname:\s*ecommerce-detail-page\s*\r?\ndescription:.+?\r?\n---') {
        Add-Failure 'SKILL.md 前置元数据无效或字段顺序异常。'
    }

    foreach ($referenceFile in Get-ChildItem -File -Filter '*.md' -LiteralPath $referencesPath) {
        if (-not $skillText.Contains($referenceFile.Name)) {
            Add-Failure "发现未被SKILL.md声明的参考文件：$($referenceFile.Name)"
        }
        $referenceLines = Get-Content -Encoding UTF8 -LiteralPath $referenceFile.FullName
        if ($referenceLines.Count -gt 100 -and -not (($referenceLines | Select-Object -First 20) -match '^## 目录$')) {
            Add-Failure "超过100行的参考文件缺少顶部目录：$($referenceFile.Name)"
        }
    }
}

$textFiles = @(Get-ChildItem -Recurse -File -LiteralPath $skillRootPath |
    Where-Object { $_.Extension -in '.md', '.yaml', '.yml' })
$repositoryReadmePath = Join-Path (Split-Path -Parent $skillRootPath) 'README.md'
if (Test-Path -LiteralPath $repositoryReadmePath) {
    $textFiles += Get-Item -LiteralPath $repositoryReadmePath
    Require-Pattern $repositoryReadmePath 'TC-nnn / PC-nnn / RC-nnn / SC-nnn / ST-nnn / DC-nnn / FS-nnn / FR-nnn / PR-nnn' 'README合同版本顺序'
    Require-Pattern $repositoryReadmePath 'storyboard_id \+ frame_release_version \+ prompt_release_version \+ release_pair \+ source_artifact_id \+ render_variant' 'README生图结果完整追溯记录'
    Require-Pattern $repositoryReadmePath '候选图的明确选择或否定.*学习快照.*最终学习封包' 'README说明候选反馈后的学习收口'
}
$referencePattern = [string]::Concat([char]96, '(?:references/)?([A-Za-z0-9-]+[.]md)', [char]96)
$obsoleteProcessPatterns = @(
    @{ Pattern = '事实锁'; Label = '事实锁' },
    @{ Pattern = '输出锁'; Label = '输出锁' },
    @{ Pattern = '数量锁'; Label = '数量锁' },
    @{ Pattern = '平台锁'; Label = '平台锁' },
    @{ Pattern = '结构锁'; Label = '结构锁' },
    @{ Pattern = '方案锁|综合方案锁|策略锁'; Label = '方案/策略锁' },
    @{ Pattern = '营销锁'; Label = '营销锁' },
    @{ Pattern = '运营锁'; Label = '运营锁' },
    @{ Pattern = '文案战略锁'; Label = '文案战略锁' },
    @{ Pattern = '画布锁|分组锁定'; Label = '画布/分组锁' },
    @{ Pattern = '场景锁|视觉锁|制作锁|字体锁|风格锁|活动风格锁'; Label = '视觉生产锁' },
    @{ Pattern = '空间一致性锁|人物与活动一致性锁|组件锁|共享锁'; Label = '组级一致性锁' },
    @{ Pattern = '预算锁|确认锁|单图锁|反馈锁|自动跳过字段锁'; Label = '流程控制锁' },
    @{ Pattern = '主体锁'; Label = '主体锁' },
    @{ Pattern = '产品锁(?!定)'; Label = '产品锁（非生产术语“产品锁定”）' },
    @{ Pattern = 'preference-lock|旧锁兼容|兼容视图'; Label = '旧兼容层' },
    @{ Pattern = 'confirmation_status|released=true'; Label = '第二套状态字段' },
    @{ Pattern = '\b(?:Frame Slot Contract|Frame Draft Artifact|Pre-Slot Layout Draft|Prompt Compiler|Release Store|Scope Contract|Structure Contract|Direction Contract|Reference Contract|Product Contract|Task Contract|Prompt Contract|Frame Contract|Work Packet|Render Gate|Release Gate|Evolution Memory|Preference Delta Loop|Memory Record|Minimal Prompt Patch|Storyboard Read|Anti-default)\b'; Label = '可中文化的旧英文架构术语' }
)

foreach ($file in $textFiles) {
    $text = Get-Content -Raw -Encoding UTF8 -LiteralPath $file.FullName
    foreach ($match in [regex]::Matches($text, $referencePattern)) {
        $reference = $match.Groups[1].Value
        if (-not (Test-Path -LiteralPath (Join-Path $referencesPath $reference))) {
            Add-Failure "失效引用：$($file.Name) -> $reference"
        }
    }
    if ($text.Contains('img-2.0')) {
        Add-Failure "发现旧生图术语：$($file.FullName)"
    }
    if ($text -match 'image图生图|image\s+提示词') {
        Add-Failure "发现可中文化的image提示词术语：$($file.FullName)"
    }
    foreach ($obsolete in $obsoleteProcessPatterns) {
        if ($text -match $obsolete.Pattern) {
            Add-Failure "发现旧流程语义：$($file.FullName) -> $($obsolete.Label)"
        }
    }
    foreach ($stalePhrase in @(
        ('生图请求不扩展' + 'Skill'),
        ('不进入图片生成、候选数量配置' + '或执行菜单'),
        ('图片生成应交由外部工具' + '或独立任务'),
        ('正式提示词Release' + '即完成')
    )) {
        if ($text.Contains($stalePhrase)) {
            Add-Failure "发现与生图闸门冲突的陈旧合同：$($file.FullName) -> $stalePhrase"
        }
    }
}

Require-Pattern $skillPath '商业、运营、产品经理、营销和美学视角只作为内部推理' '专业视角仅供内部推演'
Require-Pattern $skillPath '商品卡确认.*范围确认.*多图结构.*5个综合方向.*逐图' '固定主链在入口可发现'
Require-Pattern $skillPath '状态.*合同.*循环.*工作包.*提示词编译器.*发布闸门.*生图闸门.*追溯记录.*进化记忆' '现代架构术语完整'
Require-Pattern $skillPath '正式提示词始终是核心交付.*默认不自动生图' '提示词优先且生图默认关闭'
Require-Pattern $skillPath '分镜合同与提示词合同以同一`release_pair`和分镜草案`source_artifact_id`' '入口声明FR/PR共同来源产物'
Require-Pattern $skillPath '加载纪律' '最小相关加载纪律'
Require-Pattern $skillPath '只加载能直接改变当前范围、结构、方向、分镜、提示词或生图字段' '加载必须映射分镜字段'
Require-Pattern $skillPath 'test-scenarios\.md.*只用于维护与回归验证，正常分镜任务禁止加载' '行为测试不得进入正常任务上下文'

foreach ($runtimePath in @(
    $skillPath,
    (Join-Path $referencesPath 'asset-portfolio-system.md'),
    (Join-Path $referencesPath 'execution-engine.md'),
    (Join-Path $referencesPath 'loop-control.md'),
    (Join-Path $referencesPath 'multi-agent-orchestration.md')
)) {
    if (Test-Path -LiteralPath $runtimePath) {
        $runtimeText = Get-Content -Raw -Encoding UTF8 -LiteralPath $runtimePath
        if ($runtimeText.Contains('README')) {
            Add-Failure "运行时合同不得依赖仓库README：$runtimePath"
        }
    }
}

$executionPath = Join-Path $referencesPath 'execution-engine.md'
Require-Pattern $executionPath '商品信息确认闸门' '商品卡闸门'
Require-Pattern $executionPath '输出对象确认闸门' '输出对象闸门'
Require-Pattern $executionPath '结构选择闸门' '结构闸门'
Require-Pattern $executionPath '综合方案选择闸门' '固定5方案闸门'
Require-Pattern $executionPath '逐图提交规则' '逐图确认或自动内审'
Require-Pattern $executionPath '学习是全程旁路' '进化记忆不得成为主链闸门'
Require-Pattern $executionPath '(?s)contract_id.*contract_type.*contract_version.*status.*owner.*parent_versions.*source_trace' '统一合同版本信封'
Require-Pattern $executionPath 'TC-001/PC-001/RC-001/SC-001/ST-001/DC-001/FS-001/FR-001/PR-001' '合同版本命名空间与依赖顺序'
Require-Pattern $executionPath ([regex]::Escape('任务（TC） → 商品（PC） → 参考图（RC） → 范围（SC） → 结构（ST） → 方向（DC） → 分镜槽位（FS） → 分镜发布（FR）+ 提示词发布（PR） → 进化记忆')) '分镜槽位到FR/PR原子配对依赖'
Require-Pattern $executionPath '分镜草案是分镜槽位已`RELEASED`后才物化的不可变产物，不是合同' '分镜草案不得成为待发布合同'
Require-Pattern $executionPath '(?s)release_pair:.*frame: FR-001.*prompt: PR-001' 'FR/PR配对版本字段'
Require-Pattern $executionPath 'source_artifact_id: frame-draft-001' 'FR/PR共同来源产物字段'
Require-Pattern $executionPath '分镜合同与提示词合同的`parent_versions`.*不把尚未发布的分镜合同作为提示词父依赖' '提示词不得依赖未发布分镜'
Require-Pattern $executionPath '分镜草案是分镜槽位已`RELEASED`后才物化.*分镜槽位/FS' '分镜草案必须绑定已放行分镜槽位'
Require-Pattern $executionPath '槽位前布局草案.*不得作为提示词输入' '槽位前草案不得进入提示词编译器'
Require-Pattern $executionPath '任何返修都创建新 FR/PR 配对，禁止单边升级' '返修保持FR/PR原子配对'
Require-Pattern $executionPath '任务/商品/参考图/范围/结构/方向/分镜槽位/分镜/提示词所需的合同版本信封' '下游版本接口包含分镜槽位'
Require-Pattern $executionPath '简单生产任务可压缩.*不表示跳过合同' '简单任务只压缩分析而不绕过合同'
Require-Pattern $executionPath '最终聚合与学习快照.*可增量合并，不提前封包' '提示词交付只生成学习快照'
Require-Pattern $executionPath '学习收口.*ACCEPTED/CANCELLED.*最终学习包' '生图终态后完成学习收口'

$loopPath = Join-Path $referencesPath 'loop-control.md'
Require-Pattern $loopPath '循环阶段名`RELEASE`不等于合同已`RELEASED`' '循环发布阶段与合同发布状态分离'
Require-Pattern $loopPath '分镜合同与提示词候选原子转换为`status: RELEASED`' '分镜与提示词原子发布'
Require-Pattern $loopPath 'release_pair: \{frame: FR-nnn, prompt: PR-nnn\}' '提示词闸门写入FR/PR配对'
Require-Pattern $loopPath '配对版本一致且父版本仍为当前版本' '提示词最终消费当前配对版本'
if (Test-Path -LiteralPath $loopPath) {
    $loopText = Get-Content -Raw -Encoding UTF8 -LiteralPath $loopPath
    if ($loopText.Contains('released=true')) {
        Add-Failure '循环不得继续使用released=true第二套状态。'
    }
}

$productDossierPath = Join-Path $referencesPath 'product-dossier.md'
Require-Pattern $productDossierPath '"contract_version": "PC-001"' '商品合同版本'
Require-Pattern $productDossierPath 'contract_version: PC-nnn.*status: RELEASED' '商品合同发布接口'
if (Test-Path -LiteralPath $productDossierPath) {
    $productDossierText = Get-Content -Raw -Encoding UTF8 -LiteralPath $productDossierPath
    if ($productDossierText.Contains('confirmation_status')) {
        Add-Failure '商品合同不得继续使用confirmation_status第二套状态。'
    }
}

$reasoningPath = Join-Path $referencesPath 'reasoning-engine.md'
Require-Pattern $reasoningPath '模块唯一职责' '推演模块单一职责'
Require-Pattern $reasoningPath '需求预判阶段' '商品卡后先做需求预判'
Require-Pattern $reasoningPath '五个综合方向阶段' '结构合同后固定5个方向'
Require-Pattern $reasoningPath '深度推演门' '约束、因果、反事实与红队门'
Require-Pattern $reasoningPath '分镜任务解读' '任务先形成分镜任务解读'
foreach ($dial in @(
    'FIDELITY_STRICTNESS', 'EVIDENCE_STRICTNESS', 'VISUAL_VARIANCE',
    'INFORMATION_DENSITY', 'SCENE_REALISM', 'CONVERSION_DIRECTNESS',
    'COPY_DENSITY'
)) {
    Require-Pattern $reasoningPath ([regex]::Escape($dial)) "推演旋钮$dial"
}

$multiAgentPath = Join-Path $referencesPath 'multi-agent-orchestration.md'
Require-Pattern $multiAgentPath '阶段准入与禁止越权' '子智能体阶段准入'
Require-Pattern $multiAgentPath 'S1 商品卡草案' '商品法证阶段边界'
Require-Pattern $multiAgentPath 'S2 需求预判' '需求预判阶段边界'
Require-Pattern $multiAgentPath 'S5 方向已确认/分镜编排' '提示词编译阶段边界'
Require-Pattern $multiAgentPath '只有主控可以' '确认与交付仅由主控处理'
Require-Pattern $multiAgentPath '(?s)preference_events.*event_id' '偏好智能体输出结构化事件'
Require-Pattern $multiAgentPath '生成-审查' '生成与审查编排拓扑'
Require-Pattern $multiAgentPath '结果诊断' '生图结果诊断拓扑'
Require-Pattern $multiAgentPath '记忆双控制' '偏好捕获与仲裁双控制'
Require-Pattern $multiAgentPath 'J\. 提示词对抗审查智能体' 'J角色提示词对抗审查'
Require-Pattern $multiAgentPath 'K\. 生图结果审计智能体' 'K角色生图结果审计'
Require-Pattern $multiAgentPath 'L\. 进化仲裁智能体' 'L角色进化仲裁'
Require-Pattern $multiAgentPath '(?s)parent_packet_id.*stage_token.*role_id.*input_contract_versions.*artifact_version.*decision_scope' '不可变版本工作包合同'
Require-Pattern $multiAgentPath 'S5 方向已确认/分镜编排.*G不得消费槽位前草案或提前编译提示词' 'S5禁止无分镜槽位编译提示词'
Require-Pattern $multiAgentPath 'S6 提示词与逐图放行.*分镜槽位合同为`RELEASED`.*提示词：PENDING' 'S6只消费已放行分镜槽位'
Require-Pattern $multiAgentPath '顺序流水.*分镜草案产物.*分镜/提示词发布配对' '顺序拓扑避免分镜/提示词循环依赖'
Require-Pattern $multiAgentPath 'S6 提示词与逐图放行.*release_pair.*分镜：PENDING \+ 提示词：PENDING' 'S6产生原子FR/PR候选对'
Require-Pattern $multiAgentPath 'S6 提示词与逐图放行.*source_artifact_id.*用旧草案套当前版本信封' 'S6绑定并校验分镜草案来源'
Require-Pattern $multiAgentPath '(?s)强创意全套.*S1：.*S2：.*S3：.*S4：.*S5：.*S6：.*不得跨过 SC/ST/DC/FS' '强创意拓扑服从全阶段令牌'
Require-Pattern $multiAgentPath 'S8 可选生图.*release_pair.*source_artifact_id.*不得拼接错配 FR/PR' '生图审计绑定原子配对与来源草案'

$referencePath = Join-Path $referencesPath 'reference-image-reasoning.md'
Require-Pattern $referencePath '稳定编号' '参考图稳定索引'
Require-Pattern $referencePath '视觉DNA' '商品视觉DNA'
Require-Pattern $referencePath 'P0.*P4' '参考图总体能力分级'
Require-Pattern $referencePath '能力轴' '逐能力轴校验'
Require-Pattern $referencePath '身份母图' '身份参考图职责'
Require-Pattern $referencePath '(?s)锁定层.*重建层.*生成层' '图生图三层边界'
Require-Pattern $referencePath '多SKU' '多SKU防串图'
Require-Pattern $referencePath 'contract_version: RC-nnn' '参考图合同版本接口'

$promptPath = Join-Path $referencesPath 'prompt-orchestration.md'
Require-Pattern $promptPath '图组级不变量|图组不变量' '图组不变量'
Require-Pattern $promptPath '逐张变量|单张变量' '逐张变量'
Require-Pattern $promptPath '身份母图' '提示词明确身份母图'
Require-Pattern $promptPath '视角.*母图|主参考图' '提示词明确视角参考图'
Require-Pattern $promptPath '锁定层' '提示词锁定层'
Require-Pattern $promptPath '重建与生成层|重建层' '提示词重建/生成层'
Require-Pattern $promptPath '未知背面|未知面' '未知视角保护'
Require-Pattern $promptPath '画面文字白名单只有两类' '画面文字白名单'
Require-Pattern $promptPath '动态负面提示词' '逐图动态负面提示词'
Require-Pattern $promptPath '编译红队' '提示词发布前红队'
Require-Pattern $promptPath '分镜偏好覆盖层' '提示词编译接入偏好覆盖层'
Require-Pattern $promptPath '撤销、失效、陈旧候选、E0、静默采用' '无效偏好不得注入提示词'
Require-Pattern $promptPath '结构、图组排序与单图职责偏好只能在 ST/DC/FS 发布前.*提示词编译器必须忽略`structure`目标' '结构偏好只在合同发布前生效'
Require-Pattern $promptPath 'contract_version: PR-nnn' '提示词合同版本接口'
Require-Pattern $promptPath '提示词与从同一分镜草案派生的分镜合同先同时为`PENDING`.*两者才可原子转为`RELEASED`' '提示词状态与分镜原子发布'
Require-Pattern $promptPath '提示词不得把未发布分镜合同列为父版本' '提示词父依赖无循环'
Require-Pattern $promptPath 'source_artifact_id.*不得把旧草案内容包装成指向当前父版本的新信封' '提示词绑定真实分镜草案来源'
if (Test-Path -LiteralPath $promptPath) {
    $promptText = Get-Content -Raw -Encoding UTF8 -LiteralPath $promptPath
    if ($promptText -match '(?m)^\|\s*structure\s*\|') {
        Add-Failure '提示词编译偏好覆盖层不得继续声明structure字段。'
    }
}

$framePath = Join-Path $referencesPath 'frame-confirmation.md'
Require-Pattern $framePath '分镜槽位合同' '逐图分镜槽位合同'
Require-Pattern $framePath 'contract_version: FS-001' '分镜槽位合同版本'
Require-Pattern $framePath '分镜合同版本信封.*FR-nnn' '分镜合同版本接口'
Require-Pattern $framePath 'DRAFT / PENDING / RELEASED / INVALIDATED / BLOCKED' '分镜规范状态'
Require-Pattern $framePath '分镜合同与提示词为`RELEASED`并写入发布库|分镜与提示词已原子写入发布库' '分镜确认原子发布'
Require-Pattern $framePath '分镜草案承载.*没有`contract_version`或合同`status`' '分镜草案是非合同产物'
Require-Pattern $framePath '不把`PENDING`分镜列为提示词父版本' '分镜/提示词依赖无循环'
Require-Pattern $framePath 'release_pair: \{frame: FR-nnn, prompt: PR-nnn\}' '分镜/提示词共同配对版本'
Require-Pattern $framePath '分镜槽位通过内部闸门并为`RELEASED`后，物化.*分镜草案产物' '分镜草案物化顺序'
Require-Pattern $framePath '槽位前布局草案.*不得进入提示词编译器' '槽位前草案不可编译'
Require-Pattern $framePath '相同`release_pair:.*source_artifact_id`.*草案未`STALE`|来源草案未`STALE`' '分镜/提示词绑定当前分镜草案'
Require-Pattern $framePath '主图、SKU图、海报、产品素材图和详情页都必须先取得已发布结构合同与方向合同' '产品素材图不得绕过结构与方向合同'
Require-Pattern $framePath 'parent_versions: \{task: TC-001, product: PC-001, reference: RC-001, scope: SC-001, structure: ST-001, direction: DC-001\}' '分镜槽位示例绑定完整上游版本'
if (Test-Path -LiteralPath $framePath) {
    $frameText = Get-Content -Raw -Encoding UTF8 -LiteralPath $framePath
    if ($frameText -match '产品素材图.*决定是否需要方向合同') {
        Add-Failure '产品素材图仍存在可绕过方向合同的陈旧例外。'
    }
}

Require-Pattern $canvasPath '只删除比例/尺寸子项.*仍保留`画布与槽位`' '未知画布只删除比例尺寸子项'
Require-Pattern $canvasPath '最终分镜都必须保留`画布与槽位`中的产品锚点' '分镜槽位强制字段始终保留'
foreach ($canvasContractPath in @($canvasPath, $framePath, $repairPath, (Join-Path $referencesPath 'test-scenarios.md'))) {
    if (Test-Path -LiteralPath $canvasContractPath) {
        $canvasContractText = Get-Content -Raw -Encoding UTF8 -LiteralPath $canvasContractPath
        foreach ($staleCanvasRule in @(
            '最终分镜不写画布字段', '省略画布字段', '删除该组所有画布字段',
            '最终模板删除画布字段', '每张不出现画布字段', '所有详情页分镜删除画布字段'
        )) {
            if ($canvasContractText.Contains($staleCanvasRule)) {
                Add-Failure "发现会删除强制分镜槽位的陈旧画布合同：$canvasContractPath -> $staleCanvasRule"
            }
        }
    }
}

$interactionPath = Join-Path $referencesPath 'interaction-engine.md'
Require-Pattern $interactionPath '范围合同版本信封.*SC-nnn' '范围合同版本接口'

$structurePath = Join-Path $referencesPath 'structure-selection.md'
Require-Pattern $structurePath '结构合同版本信封.*ST-nnn' '结构合同版本接口'

Require-Pattern $reasoningPath '方向合同信封.*DC-nnn' '方向合同版本接口'

$visualPath = Join-Path $referencesPath 'visual-system.md'
Require-Pattern $visualPath '反默认化纪律' '电商视觉反默认化纪律'
Require-Pattern $visualPath '品牌.*任务.*证据.*生产' '反默认化上下文覆盖依据'

if (Test-Path -LiteralPath $storyboardPath) {
    $storyboard = Get-Content -Raw -Encoding UTF8 -LiteralPath $storyboardPath
    if ($storyboard -match '第\s*[XN]\s*张') {
        Add-Failure '分镜模板包含占位页码。'
    }

    foreach ($field in @(
        '参考图索引', '## 第1张：', '输出对象：', '成图任务：',
        '画布与槽位：',
        '身份母图：', '主参考图：', '产品锁定：', '允许变化：',
        '视角与事实边界：', '最终画面：', '镜头与构图：',
        '光影、材质与色彩：', '生产与后期：',
        '图生图提示词：', '动态负面提示词：'
    )) {
        if (-not $storyboard.Contains($field)) {
            Add-Failure "分镜模板缺少关键字段：$field"
        }
    }

    if ($storyboard -notmatch '没有已`RELEASED`的分镜槽位合同时阻塞提示词编译与最终交付') {
        Add-Failure '分镜模板没有阻止缺失分镜槽位合同的交付。'
    }

    $sourceBlock = [regex]::Match($storyboard, '(?s)````markdown\r?\n(?<body>.*?)\r?\n````')
    if (-not $sourceBlock.Success) {
        Add-Failure '无法定位最终分镜Markdown源码模板。'
    }
    else {
        $body = $sourceBlock.Groups['body'].Value
        foreach ($term in @(
            'A/B', '评分', '评估', '候选方案', '测试计划', '多智能体报告',
            '待确认', '占位页码', '生图闸门', '生图请求', '暂不生图',
            '指定分镜', '当前图组全部', '全部图组', '候选数量', 'candidate_count'
        )) {
            if ($body.Contains($term)) {
                Add-Failure "最终分镜模板泄漏非生产内容：$term"
            }
        }
    }
}

$checklistPath = Join-Path $referencesPath 'final-checklist.md'
Require-Pattern $checklistPath '参考图索引' '最终放行检查参考图索引'
Require-Pattern $checklistPath '能力轴全部通过' '最终放行逐能力轴检查'
Require-Pattern $checklistPath '锁定层、重建层和生成层' '最终放行三层边界'
Require-Pattern $checklistPath '商业/运营/营销建议|运营/营销建议' '最终只交付分镜提示词'
Require-Pattern $checklistPath 'Q0-Q3 发布严重度' 'Q0-Q3发布严重度'
Require-Pattern $checklistPath 'P0-P4.*只表示参考图生产能力' 'P级与Q级职责分离'
Require-Pattern $checklistPath 'Q0.*Q1.*Q2.*Q3' 'Q0-Q3完整放行规则'
Require-Pattern $checklistPath 'TC/PC/RC/SC/ST/DC-nnn.*状态均为`RELEASED`' '最终闸门校验全链当前状态'
Require-Pattern $checklistPath 'FS-nnn.*parent_versions.*当前上游版本' '最终闸门校验分镜槽位父版本'
Require-Pattern $checklistPath 'FR-nnn.*PR-nnn.*release_pair.*原子提交' '最终闸门校验FR/PR原子配对'
Require-Pattern $checklistPath 'parent_versions/input_contract_versions.*INVALIDATED/STALE' '最终闸门拒绝陈旧父版本'
Require-Pattern $checklistPath 'source_artifact_id.*分镜草案.*未`STALE`.*input_contract_versions.*当前 FS' '最终闸门校验分镜草案来源版本'
Require-Pattern $checklistPath 'storyboard_id \+ frame_release_version \+ prompt_release_version \+ release_pair \+ source_artifact_id \+ candidate_count' '生图目标冻结原子配对与来源草案'

Require-Pattern $renderPath '默认停在提示词交付，不自动生图' '生图闸门默认关闭'
foreach ($renderState in @(
    'NOT_OFFERED', 'OFFERED', 'CONFIGURED', 'GENERATING', 'REVIEWED',
    'ACCEPTED', 'PATCH_REQUIRED', 'FAILED', 'INVALIDATED', 'CANCELLED'
)) {
    Require-Pattern $renderPath ([regex]::Escape($renderState)) "生图状态$renderState"
}
Require-Pattern $renderPath 'OFFERED -> CONFIGURED \| CANCELLED' '生图选择或取消分支'
Require-Pattern $renderPath 'CONFIGURED -> GENERATING \| INVALIDATED \| CANCELLED' '生图配置版本失效分支'
Require-Pattern $renderPath 'REVIEWED -> ACCEPTED \| PATCH_REQUIRED \| INVALIDATED \| CANCELLED' '生图审阅状态失效或取消分支'
Require-Pattern $renderPath 'FAILED -> CONFIGURED \| INVALIDATED \| CANCELLED' '生图失败状态失效或取消分支'
Require-Pattern $renderPath 'selected_frames/current_group/all_groups' '生图范围合同'
Require-Pattern $renderPath 'candidate_count' '逐张候选数量合同'
Require-Pattern $renderPath 'release_pair: \{frame: FR-003, prompt: PR-004\}' '生图请求冻结FR/PR原子配对'
Require-Pattern $renderPath 'source_artifact_id: frame-draft-002' '生图请求冻结分镜草案来源'
Require-Pattern $renderPath 'release_pair\.frame/prompt.*分别等于.*frame_release_version/prompt_release_version.*共同.*source_artifact_id.*未`STALE`' '生图执行前校验配对版本与来源草案'
Require-Pattern $renderPath 'storyboard_id \+ frame_release_version \+ prompt_release_version \+ release_pair \+ source_artifact_id \+ render_variant' '生图结果完整追溯记录'
Require-Pattern $renderPath '提示词发布版本统一使用`PR-001`' '提示词发布独立版本命名空间'
Require-Pattern $renderPath '任一提示词或分镜发布版本更新后.*旧版本绑定.*INVALIDATED' '提示词版本更新使旧生图请求失效'
Require-Pattern $renderPath '单个候选偶发失败不自动证明提示词错误' '随机候选不自动修改提示词'
Require-Pattern $renderPath '结果诊断循环' '生图结果诊断循环'
Require-Pattern $renderPath '最小提示词补丁' '生图最小提示词返修'
Require-Pattern $renderPath '原 `frame_release_version \+ prompt_release_version \+ release_pair`' '补丁记录旧FR/PR配对'
Require-Pattern $renderPath '新 `frame_release_version \+ prompt_release_version \+ release_pair`' '补丁记录新FR/PR配对'
Require-Pattern $renderPath '不允许单边升级 PR.*旧 FR/PR 同步转为`INVALIDATED`' '补丁原子替换FR/PR配对'
Require-Pattern $renderPath '候选数量.*不进入长期偏好|数量选择不得强化进化记忆' '候选数量不进入进化记忆'
Require-Pattern $renderPath '有效候选反馈先增量合并.*ACCEPTED/CANCELLED.*最终学习包' '候选反馈在生图终态后收口学习包'
if (Test-Path -LiteralPath $renderPath) {
    $renderText = Get-Content -Raw -Encoding UTF8 -LiteralPath $renderPath
    if ($renderText -match 'prompt_release_version:\s*P[0-9]+\b') {
        Add-Failure '提示词发布版本不得复用P0-P4参考能力命名空间。'
    }
}

$operationPath = Join-Path $referencesPath 'operation-review.md'
Require-Pattern $operationPath '默认不向用户输出A/B测试建议|默认只作内部评估' '运营与测试默认不对外交付'

Require-Pattern $repairPath '任何修改都必须创建新的原子 FR/PR 配对' '返修入口保持FR/PR配对'
Require-Pattern $repairPath '只改提示词时也复制未变化的分镜正文到新 FR' '仅提示词返修也创建新FR'
Require-Pattern $repairPath '只修改.*比例/尺寸子项.*不删除产品锚点' '返修不删除强制分镜槽位'
Require-Pattern $repairPath '旧/新 FR 与 PR 版本.*旧/新`release_pair`' '返修输出版本追溯记录'

$memoryPath = Join-Path $referencesPath 'persistence-evolution.md'
Require-Pattern $memoryPath '新任务先读当前输入，再读同范围记忆' '任务开始读取适用偏好'
Require-Pattern $memoryPath '不覆盖新商品参考图和事实' '偏好不覆盖商品事实'
Require-Pattern $memoryPath '只有最终采用项与有效修复' '只有采用结果可强化'
Require-Pattern $memoryPath '(?s)本轮输入.*当前任务.*商品/SKU.*品牌/系列.*用户通用' '偏好五级核心范围'
Require-Pattern $memoryPath '(?s)event_id.*raw_feedback.*action.*dimension.*persistence_authorized' '结构化偏好事件合同'
Require-Pattern $memoryPath '静默、自动模式.*不强化' '静默与自动采用不得强化'
Require-Pattern $memoryPath '两个独立任务.*E2' 'E2需要跨任务重复确认'
Require-Pattern $memoryPath '记忆文件存在不代表自动获得写入授权' '捕获与持久化授权分离'
Require-Pattern $memoryPath '商品事实/安全 > 当前明确要求 > 更窄作用范围' '偏好冲突优先级'
Require-Pattern $memoryPath 'stale.*revoked|revoked.*stale' '偏好衰减与撤销状态'
Require-Pattern $memoryPath '偏好差异循环' '偏好差异学习循环'
Require-Pattern $memoryPath 'OBSERVE.*DIFF.*ATTRIBUTE.*SCOPE.*VERIFY.*PROMOTE.*SUPPRESS.*EXPIRE' '偏好差异状态机'
Require-Pattern $memoryPath '选中与未选候选共有的属性不能成为偏好证据' '共有属性不得错误归因'
Require-Pattern $memoryPath '"status": "candidate/active/suppressed/revoked/stale"' '记忆记录包含stale状态'
Require-Pattern $memoryPath '提示词交付时.*学习快照.*ACCEPTED/CANCELLED.*最终学习包' '偏好学习在可选生图后最终收口'
Require-Pattern $memoryPath '只有`persistence_authorized: true`.*授权来源、范围与时间可追溯' '持久化必须保留授权证据'
if (Test-Path -LiteralPath $memoryPath) {
    $memoryText = Get-Content -Raw -Encoding UTF8 -LiteralPath $memoryPath
    $requiredMemoryFields = @(
        'memory_id', 'rule', 'polarity', 'scope', 'scope_qualifier', 'scope_key',
        'created_at', 'updated_at', 'evidence_level', 'confidence', 'source_trace',
        'attribution', 'verification_count', 'last_validated', 'prompt_targets',
        'supersedes', 'conflicts_with', 'exceptions', 'invalidation', 'decay', 'status',
        'persistence_authorized', 'authorization_scope', 'authorization_trace',
        'authorized_at', 'revoked_at', 'revocation_trace'
    )

    $memoryContractMatch = [regex]::Match(
        $memoryText,
        '(?s)## 记忆记录合同.*?```json\r?\n(?<body>.*?)\r?\n```'
    )
    if (-not $memoryContractMatch.Success) {
        Add-Failure '无法定位可解析的记忆记录合同JSON。'
    }
    else {
        try {
            $memoryContract = $memoryContractMatch.Groups['body'].Value | ConvertFrom-Json
            Require-JsonFields $memoryContract $requiredMemoryFields '记忆记录合同'
        }
        catch {
            Add-Failure "记忆记录合同JSON无效：$($_.Exception.Message)"
        }
    }

    $persistenceMatch = [regex]::Match(
        $memoryText,
        '(?s)持久化文件使用一个可解析的完整 JSON 记录库.*?```json\r?\n(?<body>.*?)\r?\n```'
    )
    if (-not $persistenceMatch.Success) {
        Add-Failure '无法定位可解析的持久化记忆JSON模板。'
    }
    else {
        try {
            $persistenceTemplate = $persistenceMatch.Groups['body'].Value | ConvertFrom-Json
            Require-JsonFields $persistenceTemplate @('schema_version', 'updated_at', 'records') '持久化记忆根对象'
            if ($null -eq $persistenceTemplate.records -or @($persistenceTemplate.records).Count -eq 0) {
                Add-Failure '持久化记忆JSON模板缺少完整records示例。'
            }
            else {
                Require-JsonFields @($persistenceTemplate.records)[0] $requiredMemoryFields '持久化记忆记录'
            }
        }
        catch {
            Add-Failure "持久化记忆JSON模板无效：$($_.Exception.Message)"
        }
    }
}

$nextActionPath = Join-Path $referencesPath 'next-action-engine.md'
Require-Pattern $nextActionPath '正式提示词交付后停止本模块.*render-gate\.md' '交付后停止通用菜单'
Require-Pattern $nextActionPath '正式提示词交付后不得再显示本菜单，只能.*生图闸门选择' '交付后只显示生图闸门'

$operationModelsPath = Join-Path $referencesPath 'ecommerce-operation-models.md'
Require-Pattern $operationModelsPath '仅用户已明确纳入输出范围时转成单变量正式分镜.*不得在源码块外附加测试变量或建议' 'A/B仅可转为已授权正式分镜'
if (Test-Path -LiteralPath $operationModelsPath) {
    $operationModelsText = Get-Content -Raw -Encoding UTF8 -LiteralPath $operationModelsPath
    if ($operationModelsText.Contains('最终源码块外给可测试变量')) {
        Add-Failure '经营模块仍要求在正式源码块外输出A/B变量。'
    }
}

if (Test-Path -LiteralPath $agentPath) {
    $agentText = Get-Content -Raw -Encoding UTF8 -LiteralPath $agentPath
    if ($agentText -notmatch '\$ecommerce-detail-page') {
        Add-Failure 'agents/openai.yaml 的默认提示词未显式调用技能。'
    }
    $shortDescriptionMatch = [regex]::Match($agentText, 'short_description:\s*"(?<value>[^"]+)"')
    if (-not $shortDescriptionMatch.Success) {
        Add-Failure 'agents/openai.yaml 缺少short_description。'
    }
    else {
        $shortDescriptionLength = $shortDescriptionMatch.Groups['value'].Value.Length
        if ($shortDescriptionLength -lt 25 -or $shortDescriptionLength -gt 64) {
            Add-Failure "agents/openai.yaml 的short_description长度必须为25到64字符：当前$shortDescriptionLength。"
        }
    }
}

$scenarioPath = Join-Path $referencesPath 'test-scenarios.md'
if (Test-Path -LiteralPath $scenarioPath) {
    $scenarioCount = (Select-String -Path $scenarioPath -Pattern '^### ' -Encoding UTF8).Count
    if ($scenarioCount -lt 100) {
        Add-Failure "行为测试场景不足：当前$scenarioCount，至少需要100。"
    }
    $scenarioText = Get-Content -Raw -Encoding UTF8 -LiteralPath $scenarioPath
    foreach ($scenarioTerm in @(
        '多SKU', '未知新视角轴', '身份母图', '多智能体分镜推演', '偏好',
        '自动模式', '主控唯一最终分镜', '提示词优先且默认不自动生图',
        '生图指定分镜', '暂不生图终止生图流程', '生图当前图组全部', '生图全部图组',
        '每张不同候选数量', '提示词版本更新使旧生图请求失效',
        '最小提示词补丁保持 FR/PR 原子配对',
        '随机失败不自动改提示词', '分镜任务解读先于模板',
        '七个推演旋钮映射到分镜', '反套路边界的上下文覆盖',
        '分镜槽位合同先发布后编译', '未知画布仍保留分镜槽位',
        '分镜草案不是合同以避免循环依赖', 'Q0-Q3与P0-P4分离',
        'J角色提示词对抗审查', 'K角色生图结果审计',
        'L角色进化仲裁', '偏好差异循环只学习真实差异',
        '不相关模块不加载', '合同版本全链贯通',
        '最终闸门拒绝陈旧父版本与错配发布', '最终闸门拒绝陈旧分镜草案伪装',
        '生图审阅与失败状态可失效',
        '提示词交付后只显示生图闸门',
        '产品素材图仍建立方向合同', '强创意全套服从阶段令牌',
        '生图拒绝错配配对与陈旧来源', '编译期偏好不得改结构',
        '候选反馈后最终学习收口', '持久化记录保留撤销与授权证据'
    )) {
        if (-not $scenarioText.Contains($scenarioTerm)) {
            Add-Failure "行为测试缺少高风险主题：$scenarioTerm"
        }
    }
}

if ($failures.Count -gt 0) {
    Write-Host "验证失败，共 $($failures.Count) 项：" -ForegroundColor Red
    $failures | ForEach-Object { Write-Host "- $_" -ForegroundColor Red }
    exit 1
}

Write-Host '验证通过：现代状态/合同/循环架构、商品图推演、J-K-L多智能体、提示词发布、可选生图闸门、最终分镜与偏好差异进化合同均有效。' -ForegroundColor Green
