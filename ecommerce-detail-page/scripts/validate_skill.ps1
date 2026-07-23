$ErrorActionPreference = 'Stop'

$skillRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

$requiredFiles = @(
    'SKILL.md'
    'agents/openai.yaml'
    'references/product-and-reference.md'
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
