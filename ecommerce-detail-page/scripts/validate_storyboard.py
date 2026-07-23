#!/usr/bin/env python3
"""验证商品图生图分镜的公开 Markdown 格式。"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


REQUIRED_FIELDS = (
    "输出对象",
    "成图任务",
    "画布与布局",
    "参考图使用",
    "商品锁定",
    "允许变化",
    "视角与事实边界",
    "最终画面",
    "镜头与构图",
    "光影、材质与色彩",
    "生产与后期",
)
OPTIONAL_FIELDS = ("场景与人物", "最终文案")
ALLOWED_FIELDS = set(REQUIRED_FIELDS + OPTIONAL_FIELDS)
OUTPUT_ID_PREFIXES = {
    "主图": "主图",
    "SKU图": "SKU图",
    "详情页": "详情页",
    "海报": "海报",
    "白底图": "白底图",
    "透明图": "透明图",
    "无字场景图": "无字场景图",
}

HEADING_RE = re.compile(
    r"^## 第(?P<page>\d+)张（(?P<storyboard_id>[A-Za-z0-9\u4e00-\u9fff]+-\d{2,})）：(?P<title>\S.*)$",
    re.MULTILINE,
)
FIELD_RE = re.compile(r"^- ([^\n：]+)：[ \t]*(.*)$", re.MULTILINE)
QUANTITY_NOTE_RE = re.compile(
    r"^> 数量说明：(?=.*(?:\d+|[零〇一二三四五六七八九十百千万两]+)\s*张)\S.*$"
)
PROMPT_RE = re.compile(
    r"^- 🎨 图生图提示词：\s*\n```text\n(?P<text>.+?)\n```\s*$",
    re.MULTILINE | re.DOTALL,
)
NEGATIVE_RE = re.compile(
    r"^- ⚠️ 动态负面提示词：\s*\n```text\n(?P<text>.+?)\n```\s*$",
    re.MULTILINE | re.DOTALL,
)
REFERENCE_TERM = (
    r"(?:参考图(?:片)?|商品图(?:片|像)?|参考视觉|视觉资料|实拍图|"
    r"界面(?:截图|录屏|预览图)|权益(?:说明)?页(?:面)?(?:截图)?|"
    r"(?:交付|激活|预约|核销|服务)?流程(?:截图|图|页(?:面)?)?|"
    r"(?:订单|到账|交付|激活|预约|核销)?状态截图|"
    r"授权(?:页(?:面)?(?:截图)?|文件|截图)|服务场景(?:图|照片)?)"
)
REFERENCE_TERM_RE = re.compile(REFERENCE_TERM)
REFERENCE_MODIFIER = r"(?:(?:真实|原始|清晰|可访问|已授权|用户提供的|卖家|官方|同版本|同款|相关|当前|本次)\s*){0,4}"
REFERENCE_GLOBAL_ANALYSIS_RE = re.compile(
    rf"(?:(?:已|先|经过|完成)?(?:分析|读取|综合|检查|比对)[^，。；\n]{{0,20}}(?:全部|所有)(?:有效|可用)?{REFERENCE_MODIFIER}{REFERENCE_TERM}|"
    rf"(?:全部|所有)(?:有效|可用)?{REFERENCE_MODIFIER}{REFERENCE_TERM}[^，。；\n]{{0,20}}(?:已|先)?(?:分析|读取|综合|检查|比对))"
)
FIXED_REFERENCE_RE = re.compile(
    rf"{REFERENCE_TERM}\s*(?:(?:编号|序号|No\.?|#)\s*)?(?:[（(【\[]\s*)?(?:"
    r"\d+(?![\d张幅组套])|"
    r"[一二三四五六七八九十百]+(?![一二三四五六七八九十百张幅组套])|"
    r"[A-Z](?![A-Z张幅组套]))(?:\s*[）)】\]])?",
    re.IGNORECASE,
)
REFERENCE_SCOPE_PATTERNS = {
    "单张": re.compile(
        rf"(?:(?:只|仅)?(?:输入|使用|采用|提供|选用)?[^，。；\n]{{0,12}}(?:单张|一张|1张)[^，。；\n]{{0,12}}{REFERENCE_TERM}|"
        rf"{REFERENCE_TERM}[^，。；\n]{{0,12}}(?:单张|一张|1张))"
    ),
    "多张": re.compile(
        rf"(?:(?:输入|使用|采用|提供|选用)?[^，。；\n]{{0,12}}(?:多张|两张|二张|[2-9]\d*张|[二两三四五六七八九十百]+张|数张|若干张)[^，。；\n]{{0,12}}{REFERENCE_TERM}|"
        rf"{REFERENCE_TERM}[^，。；\n]{{0,12}}(?:多张|两张|二张|[2-9]\d*张|[二两三四五六七八九十百]+张|数张|若干张))"
    ),
    "全部": re.compile(rf"(?:全部|所有)(?:有效|同款|可用)?{REFERENCE_MODIFIER}{REFERENCE_TERM}"),
}
REFERENCE_PURPOSE_RE = re.compile(
    r"(?:商品身份|核心对象|商品特征|SKU|版本|几何|结构|轮廓|颜色|材质|文字|包装|配件|尺度|场景|细节|共同特征|正面|界面|权益|流程|交付|授权)"
)
REFERENCE_TARGET_FILTER_RE = re.compile(
    r"(?:(?:按|依据|围绕)[^，。；\n]{0,20}(?:目标\s*(?:SKU|版本)(?:/状态)?|各\s*(?:SKU|版本))[^，。；\n]{0,20}(?:筛选|提取|分别)|"
    r"(?:目标\s*(?:SKU|版本)(?:/状态)?|各\s*(?:SKU|版本))[^，。；\n]{0,20}(?:筛选|限定|匹配|分别提取)|"
    r"(?:只|仅)[^，。；\n]{0,12}(?:(?:目标|当前|对应)\s*(?:SKU|版本)(?:/状态)?|各\s*(?:SKU|版本))|"
    r"(?:目标|当前|对应)\s*(?:SKU|版本)(?:/状态)?[^，。；\n]{0,16}(?:有效|一致|对应)(?:参考|证据|内容|资料))"
)
REFERENCE_SKU_ISOLATION_RE = re.compile(
    r"(?:同一目标\s*(?:SKU|版本)|同一\s*(?:SKU|版本)|同\s*(?:SKU|版本)|"
    r"(?:只|仅)[^，。；\n]{0,12}(?:目标|当前|对应)\s*(?:SKU|版本)|"
    r"(?:其他|不同)\s*(?:SKU|版本)[^，。；\n]{0,30}(?:不作为生成参考输入|不传入|排除|仅用于差异|只用于差异|防串款)|"
    r"各\s*(?:SKU|版本)[^，。；\n]{0,24}(?:分别|分层|独立商品层|后期合成))"
)
REFERENCE_CONFLICT_RESOLVED_RE = re.compile(
    r"(?:(?:资料|参考(?:图|视觉)?|同款内容)[^，。；\n]{0,20}"
    r"(?:一致(?!性)|无冲突|没有冲突|无需裁决)|"
    r"(?:最终|已明确)(?:采用|保留)[^。\n]{1,60}(?:舍弃|排除|不采用)[^。\n]{1,60}|"
    r"(?:最终|已明确)(?:舍弃|排除|不采用)[^。\n]{1,60}(?:采用|保留)[^。\n]{1,60})"
)
REFERENCE_CONFLICT_UNRESOLVED_RE = re.compile(
    r"(?:(?:并非|并不|不是|没有|并未|尚未|仍未|未|无法|不能|不)(?!但|仅|只|止)"
    r"[^，。；\n]{0,12}(?:一致|无冲突|没有冲突|无需裁决)|"
    r"(?:是否|能否)[^，。；\n]{0,6}一致|"
    r"一致(?:性)?[^，。；\n]{0,10}(?:尚未|仍未|未|无法|不能|待)(?:确认|确定|证明|明确)|"
    r"(?:冲突|矛盾|不一致)[^，。；\n]{0,16}(?:尚未|仍未|未|无法|不能|待)(?:裁决|确认|解决))"
)
CHINESE_RE = re.compile(r"[\u3400-\u9fff]")
LATIN_RE = re.compile(r"[A-Za-z]")

FORBIDDEN_SECRET_RE = re.compile(
    r"(?i)(?:"
    r"sk-[A-Za-z0-9_-]{16,}|"
    r"gh[opurs]_[A-Za-z0-9]{20,}|"
    r"AKIA[0-9A-Z]{16}|"
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----|"
    r"\bBearer\s+[A-Za-z0-9._~-]{20,}|"
    r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{5,}|"
    r"\b(?:password|passwd|pwd|api[_-]?key|access[_-]?token|client[_-]?secret)"
    r"\s*[:=]\s*[\"']?[^\s\"']{8,}|"
    r"\bCookie\s*:\s*[A-Za-z0-9_.-]+=[^;\s]{8,}"
    r")"
)
FORBIDDEN_INTERNAL_RE = re.compile(
    r"(?:内部评分|候选(?:方案|比较)|角色(?:讨论|名称)|(?:循环|推演)(?:日志|记录)|"
    r"模型名|测试(?:标签|文字)|审查状态|调试字段|未采用方案|确认记录|隐藏思考链)"
)
FORBIDDEN_VIEW_ANNOTATION_RE = re.compile(
    r"(?:置信度(?:\s*\d+分?)?|高置信|推定|(?:背面|底部|内部|拆解)\s*[：:]?\s*(?:为|标注为|按|作为)?\s*示意(?:图)?)"
)
SKU_FUSION_RE = re.compile(
    r"(?i)(?:(?:融合|混合|平均|拼接|拼装)(?:多个|不同)?\s*SKU|"
    r"(?:多个|不同)\s*SKU(?:进行)?(?:融合|混合|平均|拼接|拼装)|"
    r"(?:把|将)?(?:多个|不同)\s*SKU[^，。；\n]{0,18}(?:拼成|合成|做成)(?:一款|一个)?|"
    r"(?:各|多个|不同)\s*(?:SKU|版本)[^，。；\n]{0,40}"
    r"(?:混在|融合(?:到|为|成)?|合并(?:到|为|成)?|拼成|合成(?:为|到|成)?)"
    r"[^，。；\n]{0,12}(?:同一|一个)[^，。；\n]{0,10}(?:商品层|商品身份|商品主体|主体|商品|款|版本))"
)
DIRECT_NEGATION_RE = re.compile(
    r"(?:并非|并不|不是|没有|并未|尚未|仍未|从未|未|禁止|避免|防止|杜绝|无须|无需|无法|不能|"
    r"不(?!但|仅|只|止)(?:要|得|应|可|能|允许|必|需要|再)?)"
    r"[^，。；\n但却而]{0,10}$"
)
EXPLANATORY_FUSION_PREFIX_RE = re.compile(r"(?:说明|解释|警示|展示)[^，。；\n]{0,12}$")
EXPLANATORY_FUSION_SUFFIX_RE = re.compile(r"^(?:会|将|可能)?(?:造成|导致|引发)")
CROSS_MODEL_TRANSPLANT_RE = re.compile(
    r"(?:把|将)\s*(?P<source>(?=[A-Za-z0-9_-]*\d)[A-Za-z0-9_-]{2,}|[\u4e00-\u9fff]{1,6}(?:款|版|型))\s*的?"
    r"[^，。；\n]{1,24}(?:装到|装入|移植到|拼到|接到|换到)\s*"
    r"(?P<target>(?=[A-Za-z0-9_-]*\d)[A-Za-z0-9_-]{2,}|[\u4e00-\u9fff]{1,6}(?:款|版|型))",
    re.IGNORECASE,
)
OTHER_SKU_BORROW_RE = re.compile(
    r"(?:借用|取用|采用|移用|套用)(?:其他|另一|不同)\s*SKU\s*的[^，。；\n]{1,28}"
)
UNRESOLVED_CONTEXT_RE = re.compile(
    r"(?:同上|按前文|按之前方案|(?:沿用|参考|照搬|保持)上一张|与上一张相同|"
    r"(?:按|按照|依据|参照|读取|遵循|根据)(?:已确认)?商品卡[^，。；\n]{0,16}|"
    r"与(?:已确认)?商品卡[^，。；\n]{0,12}保持一致|"
    r"(?:冲突|矛盾|不一致)?[^，。；\n]{0,8}(?:以|服从)(?:已确认)?商品卡(?:结论)?(?:为准)?)"
)
PLACEHOLDER_RE = re.compile(r"(?:TODO|TBD|待定|待补|省略号|【(?:名称|内容|填写|待补)[^】]*】|\.\.\.)", re.IGNORECASE)


class StoryboardValidationError(ValueError):
    """分镜公开格式不符合要求。"""


def _strip_brackets(value: str) -> str:
    value = value.strip()
    if value.startswith("【") and value.endswith("】"):
        return value[1:-1].strip()
    return value


def _extract_single(pattern: re.Pattern[str], block: str, label: str) -> tuple[re.Match[str], str]:
    matches = list(pattern.finditer(block))
    if len(matches) != 1:
        raise StoryboardValidationError(f"每张分镜必须且只能包含一个{label}")
    value = matches[0].group("text").strip()
    if not value:
        raise StoryboardValidationError(f"{label}不能为空")
    return matches[0], value


def _erase_spans(text: str, spans: list[tuple[int, int]]) -> str:
    characters = list(text)
    for start, end in spans:
        for index in range(start, end):
            if characters[index] not in "\r\n":
                characters[index] = " "
    return "".join(characters)


def _parse_preamble(preamble: str) -> None:
    lines = [line.strip() for line in preamble.splitlines() if line.strip()]
    if not lines:
        return
    if len(lines) != 1 or not QUANTITY_NOTE_RE.fullmatch(lines[0]):
        raise StoryboardValidationError("分镜前只允许一行“> 数量说明：……”；不得添加参考图索引或额外报告")


def _is_mainly_chinese(text: str) -> bool:
    chinese_count = len(CHINESE_RE.findall(text))
    latin_count = len(LATIN_RE.findall(text))
    return chinese_count > 0 and chinese_count * 2 >= latin_count * 3


def _generation_input_segment(text: str) -> str:
    """优先分析“本张实际输入”后的文字，避免把全局分析范围误当生成输入。"""

    markers = list(
        re.finditer(
            r"(?:本张(?:实际)?|本次生成|向(?:图像|生成)?模型|实际生成输入|生成参考输入)",
            text,
        )
    )
    return text[markers[0].start() :] if markers else text


def _reference_mode(text: str) -> str | None:
    segment = _generation_input_segment(text)
    matches = [name for name, pattern in REFERENCE_SCOPE_PATTERNS.items() if pattern.search(segment)]
    return matches[0] if len(matches) == 1 else None


def _is_locally_negated(text: str, start: int) -> bool:
    clause_start = max(text.rfind(separator, 0, start) for separator in "，。；\n") + 1
    prefix = text[clause_start:start]
    return DIRECT_NEGATION_RE.search(prefix) is not None


def _has_positive_rule(pattern: re.Pattern[str], text: str) -> bool:
    return any(not _is_locally_negated(text, match.start()) for match in pattern.finditer(text))


def _has_resolved_reference_conflict(text: str) -> bool:
    """只接受明确一致或已写明采用/舍弃结果的参考资料声明。"""

    for match in REFERENCE_CONFLICT_RESOLVED_RE.finditer(text):
        clause_start = max(text.rfind(separator, 0, match.start()) for separator in "，。；\n") + 1
        clause_ends = [text.find(separator, match.end()) for separator in "，。；\n"]
        clause_end = min((position for position in clause_ends if position >= 0), default=len(text))
        clause = text[clause_start:clause_end]
        if REFERENCE_CONFLICT_UNRESOLVED_RE.search(clause):
            continue
        if _is_locally_negated(text, match.start()):
            continue
        return True
    return False


def _contains_asserted_sku_fusion(text: str) -> bool:
    """只拦截肯定执行的跨SKU融合，允许负面提示词明确禁止它。"""

    for match in SKU_FUSION_RE.finditer(text):
        clause_start = max(text.rfind(separator, 0, match.start()) for separator in "，。；\n") + 1
        prefix = text[clause_start : match.start()]
        suffix = text[match.end() :]
        if DIRECT_NEGATION_RE.search(prefix):
            continue
        if EXPLANATORY_FUSION_PREFIX_RE.search(prefix) and EXPLANATORY_FUSION_SUFFIX_RE.search(suffix):
            continue
        return True

    for match in CROSS_MODEL_TRANSPLANT_RE.finditer(text):
        if match.group("source").casefold() == match.group("target").casefold():
            continue
        if _is_locally_negated(text, match.start()):
            continue
        return True
    for match in OTHER_SKU_BORROW_RE.finditer(text):
        if _is_locally_negated(text, match.start()):
            continue
        return True
    return False


def _frame_blocks(markdown: str) -> list[tuple[re.Match[str], str]]:
    headings = list(HEADING_RE.finditer(markdown))
    if not headings:
        raise StoryboardValidationError("没有找到“第N张（对象-编号）：标题”格式的分镜标题")
    blocks: list[tuple[re.Match[str], str]] = []
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(markdown)
        blocks.append((heading, markdown[heading.end() : end]))
    return blocks


def validate_storyboard(markdown: str, *, partial: bool = False) -> list[str]:
    """验证分镜并返回稳定分镜编号。"""

    normalized = markdown.replace("\r\n", "\n").strip()
    if normalized.startswith("````markdown\n"):
        if not normalized.endswith("\n````"):
            raise StoryboardValidationError("四反引号 markdown 外层围栏没有正确闭合")
        normalized = normalized.removeprefix("````markdown\n").removesuffix("\n````").strip()

    blocks = _frame_blocks(normalized)
    _parse_preamble(normalized[: blocks[0][0].start()])

    if FORBIDDEN_SECRET_RE.search(normalized):
        raise StoryboardValidationError("最终分镜疑似包含凭证或私钥")
    if FORBIDDEN_INTERNAL_RE.search(normalized):
        raise StoryboardValidationError("最终分镜包含内部评分、审查过程或测试信息")
    if FORBIDDEN_VIEW_ANNOTATION_RE.search(normalized):
        raise StoryboardValidationError("最终分镜不得出现置信度或视图推断性质标签")
    if UNRESOLVED_CONTEXT_RE.search(normalized):
        raise StoryboardValidationError("最终分镜不得依赖商品卡、上一张或前文等未提供上下文；请写明已裁决的具体事实")
    if _contains_asserted_sku_fusion(normalized):
        raise StoryboardValidationError("最终分镜不得融合、混合、拼装或跨型号移植SKU内容")
    if FIXED_REFERENCE_RE.search(normalized):
        raise StoryboardValidationError("最终分镜不得使用固定参考图编号；应综合说明单张、多张或全部参考图的使用方式")
    if PLACEHOLDER_RE.search(normalized):
        raise StoryboardValidationError("最终分镜包含占位符或省略内容")

    pages: list[int] = []
    storyboard_ids: list[str] = []
    for heading, block in blocks:
        page = int(heading.group("page"))
        storyboard_id = heading.group("storyboard_id")
        pages.append(page)
        if storyboard_id in storyboard_ids:
            raise StoryboardValidationError(f"稳定分镜编号重复：{storyboard_id}")
        storyboard_ids.append(storyboard_id)

        positive_match, positive = _extract_single(PROMPT_RE, block, "图生图提示词")
        negative_match, negative = _extract_single(NEGATIVE_RE, block, "动态负面提示词")
        block_without_prompts = _erase_spans(
            block,
            [(positive_match.start(), positive_match.end()), (negative_match.start(), negative_match.end())],
        )

        fields: dict[str, str] = {}
        field_spans: list[tuple[int, int]] = []
        for match in FIELD_RE.finditer(block_without_prompts):
            name = match.group(1).strip()
            if name not in ALLOWED_FIELDS:
                raise StoryboardValidationError(f"{storyboard_id}包含未知公开字段：{name}")
            if name in fields:
                raise StoryboardValidationError(f"{storyboard_id}字段重复：{name}")
            value = _strip_brackets(match.group(2))
            if not value:
                raise StoryboardValidationError(f"{storyboard_id}字段不能为空：{name}")
            fields[name] = value
            field_spans.append((match.start(), match.end()))

        residue = _erase_spans(block_without_prompts, field_spans).strip()
        if residue:
            raise StoryboardValidationError(f"{storyboard_id}包含字段之外的文字、标题或未闭合内容")

        missing = [name for name in REQUIRED_FIELDS if not fields.get(name)]
        if missing:
            raise StoryboardValidationError(f"{storyboard_id}缺少必需字段：{'、'.join(missing)}")

        output_object = fields["输出对象"]
        expected_prefix = OUTPUT_ID_PREFIXES.get(output_object)
        actual_prefix = storyboard_id.rsplit("-", 1)[0]
        if expected_prefix is None:
            raise StoryboardValidationError(f"{storyboard_id}包含不支持的输出对象：{output_object}")
        if actual_prefix != expected_prefix:
            raise StoryboardValidationError(
                f"{storyboard_id}的稳定编号与输出对象“{output_object}”不一致"
            )

        if not _is_mainly_chinese(positive) or not _is_mainly_chinese(negative):
            raise StoryboardValidationError(f"{storyboard_id}的正向与负面提示词必须以自然中文为主")
        reference_usage = fields["参考图使用"]
        field_mode = _reference_mode(reference_usage)
        prompt_mode = _reference_mode(positive)
        if (
            not REFERENCE_TERM_RE.search(reference_usage)
            or not REFERENCE_TERM_RE.search(positive)
            or field_mode is None
            or prompt_mode is None
            or not REFERENCE_PURPOSE_RE.search(reference_usage)
            or not REFERENCE_PURPOSE_RE.search(positive)
        ):
            raise StoryboardValidationError(
                f"{storyboard_id}必须在参考图使用字段和正向提示词中明确选择一张、多张或全部参考视觉作为本张生成输入，并说明提取用途"
            )
        if not _has_positive_rule(REFERENCE_GLOBAL_ANALYSIS_RE, reference_usage):
            raise StoryboardValidationError(
                f"{storyboard_id}的参考图使用字段必须说明已先分析全部有效参考视觉，再声明本张实际生成输入"
            )
        if field_mode != prompt_mode:
            raise StoryboardValidationError(
                f"{storyboard_id}的参考图使用字段与正向提示词范围不一致：{field_mode} / {prompt_mode}"
            )
        if field_mode in {"多张", "全部"}:
            for location, value in (("参考图使用字段", reference_usage), ("正向提示词", positive)):
                if not _has_positive_rule(REFERENCE_TARGET_FILTER_RE, value):
                    raise StoryboardValidationError(
                        f"{storyboard_id}的{location}使用多张或全部参考图时，必须说明按目标SKU/状态筛选或按各SKU分别提取"
                    )
                if not _has_positive_rule(REFERENCE_SKU_ISOLATION_RE, value):
                    raise StoryboardValidationError(
                        f"{storyboard_id}的{location}使用多张或全部参考图时，必须说明同一目标SKU内互补、排除其他SKU生成输入，或按各SKU分别处理"
                    )
                if not _has_resolved_reference_conflict(value):
                    raise StoryboardValidationError(
                        f"{storyboard_id}的{location}使用多张或全部参考图时，必须说明同款资料一致，或写出冲突已经采用与舍弃的具体结果"
                    )

    if len(pages) != len(set(pages)):
        raise StoryboardValidationError("页码不能重复")
    if partial:
        if pages != sorted(pages):
            raise StoryboardValidationError("局部返修页码必须递增")
    elif pages != list(range(1, len(pages) + 1)):
        raise StoryboardValidationError("完整图组页码必须从1连续递增")

    return storyboard_ids


def main() -> int:
    parser = argparse.ArgumentParser(description="验证中文商品图生图分镜格式")
    parser.add_argument("path", type=Path, help="要验证的 Markdown 文件")
    parser.add_argument("--partial", action="store_true", help="按局部返修模式保留原页码")
    args = parser.parse_args()

    try:
        markdown = args.path.read_text(encoding="utf-8")
        storyboard_ids = validate_storyboard(markdown, partial=args.partial)
    except (OSError, UnicodeError, StoryboardValidationError) as error:
        print(f"验证失败：{error}", file=sys.stderr)
        return 1

    print(f"验证通过：{len(storyboard_ids)}张分镜（{'、'.join(storyboard_ids)}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
