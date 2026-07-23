$ErrorActionPreference = 'Stop'

$skillRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

$requiredFiles = @(
    'SKILL.md'
    'agents/openai.yaml'
    'references/product-and-reference.md'
    'references/prebuild-and-product-card.md'
    'references/category-adaptation.md'
    'references/confirmation-workflow.md'
    'references/image-type-index.md'
    'references/image-set-planning.md'
    'references/output-objects.md'
    'references/visual-direction.md'
    'references/prompt-writing.md'
    'references/enhancements.md'
    'references/preference-learning.md'
    'references/render-and-repair.md'
    'references/safety-and-quality.md'
    'references/storyboard-template.md'
    'scripts/validate_storyboard.py'
    'tests/test_validate_storyboard.py'
    'tests/fixtures/valid_storyboard.md'
)

$expectedReferences = @(
    'enhancements.md'
    'image-set-planning.md'
    'image-type-index.md'
    'output-objects.md'
    'preference-learning.md'
    'product-and-reference.md'
    'prebuild-and-product-card.md'
    'category-adaptation.md'
    'confirmation-workflow.md'
    'prompt-writing.md'
    'render-and-repair.md'
    'safety-and-quality.md'
    'storyboard-template.md'
    'visual-direction.md'
)

foreach ($relativePath in $requiredFiles) {
    $fullPath = Join-Path $skillRoot $relativePath
    if (-not (Test-Path -LiteralPath $fullPath -PathType Leaf)) {
        throw "缺少必需文件：$relativePath"
    }
}

$actualReferences = @(
    Get-ChildItem -LiteralPath (Join-Path $skillRoot 'references') -File |
        Sort-Object Name |
        Select-Object -ExpandProperty Name
)
$referenceDiff = Compare-Object -ReferenceObject $expectedReferences -DifferenceObject $actualReferences
if ($referenceDiff) {
    $details = ($referenceDiff | ForEach-Object { "$($_.SideIndicator) $($_.InputObject)" }) -join '；'
    throw "参考文件清单存在缺失或多余内容：$details"
}

$skillText = Get-Content -Raw -Encoding UTF8 (Join-Path $skillRoot 'SKILL.md')
foreach ($referenceName in $expectedReferences) {
    if ($skillText -notmatch [regex]::Escape("references/$referenceName")) {
        throw "SKILL.md 未按需路由到：references/$referenceName"
    }
}

foreach ($behavior in @(
    '识别商品主体',
    'AI预构建',
    '编号建议/手动纠正',
    '商品卡（待确认）',
    '用户确认',
    '已确认商品卡',
    '设计需求预判与输出范围',
    '多图结构',
    '固定5个综合方向',
    '逐图确认/内部自动复核',
    '2-1`到`2-10',
    '不视为商品卡确认',
    '可选生图',
    '超过80分',
    '写实视图确认',
    '序列号',
    '真实存在、与当前任务有关且缺少同SKU直接证据',
    '用户决策六维',
    '商品决策特征',
    '主图、SKU图、海报和详情页',
    '证据观察 → 问题建模 → 发散候选 → 跨域组合 → 反证淘汰 → 收敛排序 → 阶段落位 → 缺口回看',
    '静态图型库不能代替主动推演',
    '事实与安全使用必要硬边界，创意与探索使用正向目标、可变空间和成功标准',
    '正式交付不添加参考图索引',
    '数字权益或服务商品',
    '其他SKU默认不作为生成参考输入',
    '不能把“以商品卡为准”留给看不到商品卡的生图模型'
)) {
    if ($skillText -notmatch [regex]::Escape($behavior)) {
        throw "SKILL.md 缺少核心行为：$behavior"
    }
}

$mainChain = @(
    '商品卡（待确认）',
    '用户确认',
    '已确认商品卡',
    '设计需求预判与输出范围',
    '多图结构',
    '固定5个综合方向',
    '图组编排',
    '逐图确认/内部自动复核',
    '最终分镜',
    '可选生图'
)
$chainStart = $skillText.IndexOf('`识别商品主体', [StringComparison]::Ordinal)
if ($chainStart -lt 0) {
    throw 'SKILL.md 未找到唯一工作主线'
}
$lastIndex = $chainStart
foreach ($step in $mainChain) {
    $index = $skillText.IndexOf($step, $chainStart, [StringComparison]::Ordinal)
    if ($index -lt 0 -or $index -le $lastIndex) {
        throw "SKILL.md 主链顺序不完整或倒置：$step"
    }
    $lastIndex = $index
}

$prebuildText = Get-Content -Raw -Encoding UTF8 (Join-Path $skillRoot 'references/prebuild-and-product-card.md')
foreach ($behavior in @(
    '识别主体 → AI预构建 → 编号建议 → 用户选择或纠正 → 商品卡（待确认） → 用户确认 → 已确认商品卡',
    '可见几何确定性30%',
    '81–100分（严格超过80分）',
    '写实视图确认',
    '不等同于商品卡确认',
    '不能替用户自动确认写实视图',
    '确认商品卡',
    '不视为商品卡确认'
)) {
    if ($prebuildText -notmatch [regex]::Escape($behavior)) {
        throw "预构建参考文件缺少核心规则：$behavior"
    }
}

$workflowText = Get-Content -Raw -Encoding UTF8 (Join-Path $skillRoot 'references/confirmation-workflow.md')
foreach ($behavior in @(
    '设计需求预判卡',
    '1. 递进式主次',
    '2. 等量并列',
    '3. 混合结构',
    '固定五个综合方向',
    '确认本张并继续',
    '2-1',
    '2-10',
    '剩余自动完成',
    '摘要只作透明记录，不等待再次回复',
    '同一轮直接进入结构首推',
    '候选图片数量'
)) {
    if ($workflowText -notmatch [regex]::Escape($behavior)) {
        throw "确认工作流缺少核心行为：$behavior"
    }
}

$planningText = Get-Content -Raw -Encoding UTF8 (Join-Path $skillRoot 'references/image-set-planning.md')
if ($planningText -notmatch [regex]::Escape('只在已经确认的结构内编排')) {
    throw '图片规划缺少“不得静默改结构”的边界'
}
foreach ($dimension in @('注意力抓取', '三秒信息效率', '信任建立', '情绪与身份', '转化驱动', '平台与无障碍适配')) {
    if ($planningText -notmatch [regex]::Escape($dimension)) {
        throw "图片规划缺少用户决策维度：$dimension"
    }
}
foreach ($imageTypeGroup in @(
    '商品标准呈现类',
    '结构拆解类',
    '细节质感类',
    '功能验证类',
    '参照认知类',
    '选择适配与防错类',
    '使用教学与维护类',
    '场景呈现类',
    '创意视觉类',
    '组合、包装与到手类',
    '信任背书与来源类',
    '利益与行动类'
    '数字权益与服务交付类'
)) {
    if ($planningText -notmatch [regex]::Escape($imageTypeGroup)) {
        throw "图片规划缺少候选图型能力：$imageTypeGroup"
    }
}

$indexText = Get-Content -Raw -Encoding UTF8 (Join-Path $skillRoot 'references/image-type-index.md')
foreach ($behavior in @('商品卡确认前使用', '十三类发现入口', '数字权益与服务交付', '不是上限')) {
    if ($indexText -notmatch [regex]::Escape($behavior)) {
        throw "预构建候选图型导航缺少轻量路由规则：$behavior"
    }
}
foreach ($behavior in @(
    '能力下限，不是类型上限',
    '一个主任务和一个视觉中心',
    '多个相容手法',
    '买家问题',
    '所需证据',
    '生产方式',
    '主要风险'
)) {
    if ($planningText -notmatch [regex]::Escape($behavior)) {
        throw "候选图型库缺少开放扩展或调用规则：$behavior"
    }
}

foreach ($behavior in @('推荐图型', '买家问题', '所需证据', '生产方式', '不能制作或需要降级的原因')) {
    if ($prebuildText -notmatch [regex]::Escape($behavior)) {
        throw "预构建图片建议缺少可执行字段：$behavior"
    }
}

$categoryText = Get-Content -Raw -Encoding UTF8 (Join-Path $skillRoot 'references/category-adaptation.md')
foreach ($trait in @(
    '身份与SKU复杂度',
    '尺寸、适配与空间风险',
    '结构与功能解释难度',
    '效果与主张证据敏感度',
    '使用、安装与维护成本',
    '安全、合规与人群风险',
    '感官、审美与情绪依赖',
    '包装、交付与服务复杂度'
)) {
    if ($categoryText -notmatch [regex]::Escape($trait)) {
        throw "全行业适配缺少商品决策特征：$trait"
    }
}
foreach ($phase in @('AI预构建初筛', '商品卡确认后正式调用', '待确认假设')) {
    if ($categoryText -notmatch [regex]::Escape($phase)) {
        throw "全行业适配缺少两阶段调用规则：$phase"
    }
}
foreach ($outputObject in @('主图', 'SKU图', '海报', '详情页')) {
    if ($categoryText -notmatch [regex]::Escape($outputObject)) {
        throw "全行业适配缺少输出对象：$outputObject"
    }
}
foreach ($categoryFamily in @(
    '服饰鞋包与珠宝配饰',
    '美妆个护、食品饮料与健康相关商品',
    '数码3C、家电与智能设备',
    '家居家具、收纳与空间用品',
    '工具五金、汽配与工业品',
    '母婴、宠物与安全敏感商品',
    '户外、运动与穿戴装备',
    '礼赠、收藏与高价值商品',
    '耗材、补充装与周期购商品',
    '虚拟商品、数字内容与服务权益'
)) {
    if ($categoryText -notmatch [regex]::Escape($categoryFamily)) {
        throw "全行业适配缺少类目族：$categoryFamily"
    }
}

$templateText = Get-Content -Raw -Encoding UTF8 (Join-Path $skillRoot 'references/storyboard-template.md')
foreach ($behavior in @('参考图使用', '不输出参考图索引', '不写固定参考图编号', '本张实际向生成模型提供', '不能只留下“服从商品卡”')) {
    if ($templateText -notmatch [regex]::Escape($behavior)) {
        throw "最终分镜模板缺少动态参考图规则：$behavior"
    }
}

$renderText = Get-Content -Raw -Encoding UTF8 (Join-Path $skillRoot 'references/render-and-repair.md')
foreach ($behavior in @('等价序列化', '工具只支持一张参考图时', '其他SKU图片', '真实透明通道')) {
    if ($renderText -notmatch [regex]::Escape($behavior)) {
        throw "可选生图缺少能力适配规则：$behavior"
    }
}

$readmeText = Get-Content -Raw -Encoding UTF8 (Join-Path (Split-Path $skillRoot -Parent) 'README.md')
foreach ($tutorialHeading in @('## 第一步：图片识别', '## 第四步：生成并确认商品卡', '## 第七步：逐张分镜提示词', '## 第八步：可选生图', '## 常见问题')) {
    if ($readmeText -notmatch [regex]::Escape($tutorialHeading)) {
        throw "README 缺少使用教程章节：$tutorialHeading"
    }
}

$liveMarkdown = @($readmeText, $skillText)
$liveMarkdown += Get-ChildItem -LiteralPath (Join-Path $skillRoot 'references') -File -Filter '*.md' |
    ForEach-Object { Get-Content -Raw -Encoding UTF8 $_.FullName }
$liveText = $liveMarkdown -join "`n"
foreach ($legacy in @('91–100分', '0–90分', '高于90分', '高置信推定/示意')) {
    if ($liveText -match [regex]::Escape($legacy)) {
        throw "仍保留旧隐藏视图规则：$legacy"
    }
}
foreach ($legacyField in @('### 参考图索引', '商品身份参考图', '画面主参考图', '辅助参考图', '身份母图', '参考图职责', '身份参考图', '参考图绑定')) {
    if ($liveText -match [regex]::Escape($legacyField)) {
        throw "仍保留旧参考图输出字段：$legacyField"
    }
}

$agentText = Get-Content -Raw -Encoding UTF8 (Join-Path $skillRoot 'agents/openai.yaml')
if ($agentText -notmatch '\$ecommerce-detail-page') {
    throw 'agents/openai.yaml 的默认提示词必须显式调用 $ecommerce-detail-page'
}

$researchFiles = @(Get-ChildItem -LiteralPath (Join-Path $skillRoot 'research') -File -ErrorAction SilentlyContinue)
if ($researchFiles.Count -gt 0) {
    throw '运行技能中不应保留外部项目研究账本'
}

$python = Get-Command python -ErrorAction Stop
$fixture = Join-Path $skillRoot 'tests/fixtures/valid_storyboard.md'
& $python.Source -B -X utf8 (Join-Path $skillRoot 'scripts/validate_storyboard.py') $fixture
if ($LASTEXITCODE -ne 0) {
    throw '最终分镜夹具验证失败'
}

& $python.Source -B -X utf8 (Join-Path $skillRoot 'tests/test_validate_storyboard.py')
if ($LASTEXITCODE -ne 0) {
    throw '分镜验证器测试失败'
}

Write-Host '技能结构、中文主线和最终分镜格式验证通过。'
