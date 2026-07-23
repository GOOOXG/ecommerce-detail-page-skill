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
    "商品身份参考图",
    "画面主参考图",
    "商品锁定",
    "允许变化",
    "视角与事实边界",
    "最终画面",
    "镜头与构图",
    "光影、材质与色彩",
    "生产与后期",
)
OPTIONAL_FIELDS = ("辅助参考图", "场景与人物", "最终文案")
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
REFERENCE_RE = re.compile(r"^- (参考图\d+)：(.+)$", re.MULTILINE)
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
REFERENCE_TOKEN_RE = re.compile(r"参考图\d+")
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


def _parse_preamble(preamble: str) -> list[str]:
    lines = [line.strip() for line in preamble.splitlines() if line.strip()]
    if lines.count("### 参考图索引") != 1:
        raise StoryboardValidationError("必须且只能包含一个参考图索引标题")

    index_position = lines.index("### 参考图索引")
    before_index = lines[:index_position]
    if before_index and (
        len(before_index) != 1 or not QUANTITY_NOTE_RE.fullmatch(before_index[0])
    ):
        raise StoryboardValidationError("参考图索引前只允许一行“> 数量说明：……”")

    reference_lines = lines[index_position + 1 :]
    if not reference_lines:
        raise StoryboardValidationError("参考图索引不能为空")

    references: list[str] = []
    for line in reference_lines:
        match = REFERENCE_RE.fullmatch(line)
        if match is None:
            raise StoryboardValidationError("参考图索引中包含未允许的文字或标题")
        references.append(match.group(1))
    return references


def _is_mainly_chinese(text: str) -> bool:
    chinese_count = len(CHINESE_RE.findall(text))
    latin_count = len(LATIN_RE.findall(text))
    return chinese_count > 0 and chinese_count * 2 >= latin_count * 3


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
    references = _parse_preamble(normalized[: blocks[0][0].start()])
    if not references or len(references) != len(set(references)):
        raise StoryboardValidationError("参考图索引必须非空且编号不能重复")
    reference_set = set(references)

    if FORBIDDEN_SECRET_RE.search(normalized):
        raise StoryboardValidationError("最终分镜疑似包含凭证或私钥")
    if FORBIDDEN_INTERNAL_RE.search(normalized):
        raise StoryboardValidationError("最终分镜包含内部评分、审查过程或测试信息")
    if PLACEHOLDER_RE.search(normalized):
        raise StoryboardValidationError("最终分镜包含占位符或省略内容")

    pages: list[int] = []
    storyboard_ids: list[str] = []
    used_references: set[str] = set()

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

        declared_references: set[str] = set()
        for reference_field in ("商品身份参考图", "画面主参考图", "辅助参考图"):
            field_references = set(REFERENCE_TOKEN_RE.findall(fields.get(reference_field, "")))
            if reference_field != "辅助参考图" and not field_references:
                raise StoryboardValidationError(f"{storyboard_id}的{reference_field}没有真实参考图编号")
            declared_references.update(field_references)

        frame_references = set(REFERENCE_TOKEN_RE.findall(block))
        unknown_references = frame_references - reference_set
        if unknown_references:
            raise StoryboardValidationError(
                f"{storyboard_id}引用了索引中不存在的图片：{'、'.join(sorted(unknown_references))}"
            )

        undeclared_references = frame_references - declared_references
        if undeclared_references:
            raise StoryboardValidationError(
                f"{storyboard_id}使用了未说明职责的参考图：{'、'.join(sorted(undeclared_references))}"
            )

        positive_references = set(REFERENCE_TOKEN_RE.findall(positive))
        missing_prompt_references = declared_references - positive_references
        if missing_prompt_references:
            raise StoryboardValidationError(
                f"{storyboard_id}的正向提示词没有绑定已声明参考图："
                f"{'、'.join(sorted(missing_prompt_references))}"
            )
        used_references.update(declared_references)

    if len(pages) != len(set(pages)):
        raise StoryboardValidationError("页码不能重复")
    if partial:
        if pages != sorted(pages):
            raise StoryboardValidationError("局部返修页码必须递增")
    elif pages != list(range(1, len(pages) + 1)):
        raise StoryboardValidationError("完整图组页码必须从1连续递增")

    unused_references = reference_set - used_references
    if unused_references:
        raise StoryboardValidationError(
            f"参考图索引包含正文未使用的图片：{'、'.join(sorted(unused_references))}"
        )
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
