$ErrorActionPreference = 'Stop'

$skillRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

$requiredFiles = @(
    'SKILL.md'
    'agents/openai.yaml'
    'references/product-and-reference.md'
    'references/prebuild-and-product-card.md'
    'references/confirmation-workflow.md'
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
    'output-objects.md'
    'preference-learning.md'
    'product-and-reference.md'
    'prebuild-and-product-card.md'
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
    '待确认卡阶段不再提供裸数字确认菜单',
    '可选生图',
    '91–100分'
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
    '正式分镜只写“高置信推定/示意”或“已证实视图”',
    '确认商品卡',
    '待确认卡阶段不再提供裸数字确认菜单'
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

$readmeText = Get-Content -Raw -Encoding UTF8 (Join-Path (Split-Path $skillRoot -Parent) 'README.md')
foreach ($tutorialHeading in @('## 第一步：图片识别', '## 第四步：生成并确认商品卡', '## 第七步：逐张分镜提示词', '## 第八步：可选生图', '## 常见问题')) {
    if ($readmeText -notmatch [regex]::Escape($tutorialHeading)) {
        throw "README 缺少使用教程章节：$tutorialHeading"
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
