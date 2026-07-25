from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable


SKILL_ROOT = Path(__file__).resolve().parents[1]
REFERENCES_ROOT = (SKILL_ROOT / "references").resolve()
DEFAULT_POLICY = SKILL_ROOT / "config" / "context-routing.json"
REQUIRED_TOP_LEVEL_KEYS = {
    "配置版本",
    "用途",
    "读取策略",
    "检查名称",
    "检查组",
    "阶段检查",
    "阶段路由",
    "特征路由",
    "营销类别路由",
}
REQUIRED_READ_POLICY_KEYS = {
    "允许整文件回退",
    "允许整库回退",
    "重复章节",
    "未知键",
}
MANDATORY_STAGE_CHECKS = {
    "主体识别": frozenset({"P01", "P02", "P03", "P04"}),
    "AI预构建": frozenset({"P01", "P02", "P03", "P04", "P05"}),
    "编号与商品卡": frozenset({"P01", "P02", "P03", "P04", "P05", "P06"}),
    "目标与范围": frozenset(f"P{index:02d}" for index in range(1, 11)),
    "结构与方向": frozenset(f"P{index:02d}" for index in range(1, 11)),
    "图组规划": frozenset(f"P{index:02d}" for index in range(1, 12)),
    "分镜编译": frozenset(f"P{index:02d}" for index in range(1, 12)),
    "质检交付": frozenset(f"P{index:02d}" for index in range(1, 13)),
    "生图返修": frozenset(f"P{index:02d}" for index in range(1, 14)),
}
HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*$")
FENCE_OPEN_RE = re.compile(r"^[ \t]*(`{3,}|~{3,}).*$")
FENCE_CLOSE_RE = re.compile(r"^[ \t]*(`{3,}|~{3,})[ \t]*$")


class RoutingError(ValueError):
    """路由配置、路由键或 Markdown 章节不安全时抛出。"""


def _read_utf8(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="strict")
    except (OSError, UnicodeError) as exc:
        raise RoutingError(f"无法按 UTF-8 读取文件：{path}") from exc


def _cached_read(path: Path, cache: dict[Path, str]) -> str:
    if path not in cache:
        cache[path] = _read_utf8(path)
    return cache[path]


def _normalize_heading(hashes: str, title: str) -> str:
    title = re.sub(r"[ \t]+#+[ \t]*$", "", title).rstrip()
    return f"{hashes} {title}"


def _heading_locations(markdown: str) -> list[dict[str, int | str]]:
    lines = markdown.splitlines(keepends=True)
    locations: list[dict[str, int | str]] = []
    open_fence: tuple[str, int] | None = None

    for index, line in enumerate(lines):
        plain = line.rstrip("\r\n")
        if open_fence is None:
            fence = FENCE_OPEN_RE.match(plain)
            if fence:
                marker = fence.group(1)
                open_fence = (marker[0], len(marker))
                continue
        else:
            fence = FENCE_CLOSE_RE.match(plain)
            if fence:
                marker = fence.group(1)
                if marker[0] == open_fence[0] and len(marker) >= open_fence[1]:
                    open_fence = None
            if open_fence is not None:
                continue
            if fence:
                continue

        match = HEADING_RE.match(plain)
        if match:
            hashes, title = match.groups()
            locations.append(
                {
                    "line": index,
                    "level": len(hashes),
                    "heading": _normalize_heading(hashes, title),
                }
            )
    return locations


def extract_markdown_section(markdown: str, heading: str) -> str:
    """精确提取一个 ATX 标题及其内容，不把代码围栏内标题当作结构。"""
    locations = _heading_locations(markdown)
    matches = [item for item in locations if item["heading"] == heading]
    if len(matches) != 1:
        reason = "不存在" if not matches else "重复"
        raise RoutingError(f"Markdown 章节{reason}：{heading}")

    current = matches[0]
    start_line = int(current["line"])
    level = int(current["level"])
    end_line = len(markdown.splitlines(keepends=True))
    for item in locations:
        if int(item["line"]) > start_line and int(item["level"]) <= level:
            end_line = int(item["line"])
            break

    lines = markdown.splitlines(keepends=True)
    return "".join(lines[start_line:end_line]).rstrip() + "\n"


def _resolve_reference(relative_path: str) -> Path:
    if not isinstance(relative_path, str) or not relative_path:
        raise RoutingError("路由文件必须是非空字符串")
    candidate = (SKILL_ROOT / relative_path).resolve()
    try:
        candidate.relative_to(REFERENCES_ROOT)
    except ValueError as exc:
        raise RoutingError(f"路由文件越出 references 目录：{relative_path}") from exc
    if candidate.suffix.lower() != ".md" or not candidate.is_file():
        raise RoutingError(f"路由文件不存在或不是 Markdown：{relative_path}")
    return candidate


def _validate_entries(entries: Any, cache: dict[Path, str]) -> None:
    if not isinstance(entries, list):
        raise RoutingError("路由项集合必须是数组")
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"文件", "章节"}:
            raise RoutingError("每个路由项只能包含“文件”和“章节”")
        path = _resolve_reference(entry["文件"])
        headings = entry["章节"]
        if not isinstance(headings, list) or not headings:
            raise RoutingError(f"路由章节不能为空：{entry['文件']}")
        text = _cached_read(path, cache)
        for heading in headings:
            if not isinstance(heading, str) or not heading.startswith("#"):
                raise RoutingError(f"非法 Markdown 标题：{heading!r}")
            extract_markdown_section(text, heading)


def _all_route_lists(policy: dict[str, Any]) -> Iterable[list[dict[str, Any]]]:
    yield from policy["阶段路由"].values()
    yield from policy["特征路由"].values()
    marketing = policy["营销类别路由"]
    yield marketing["共用前置"]
    yield from marketing["类别"].values()
    yield marketing["共用收尾"]


def _validate_checks(policy: dict[str, Any]) -> None:
    names = policy["检查名称"]
    groups = policy["检查组"]
    stage_checks = policy["阶段检查"]
    stages = policy["阶段路由"]
    if not all(isinstance(value, str) and value for value in names.values()):
        raise RoutingError("检查名称必须是非空中文说明")
    if set(stage_checks) != set(stages):
        raise RoutingError("阶段检查必须与阶段路由一一对应")
    if set(stages) != set(MANDATORY_STAGE_CHECKS):
        raise RoutingError("主流程阶段不可通过配置增删或替换")
    used_checks: set[str] = set()
    for group_name, check_ids in groups.items():
        if not isinstance(check_ids, list) or not check_ids:
            raise RoutingError(f"检查组为空：{group_name}")
        unknown = set(check_ids) - set(names)
        if unknown:
            raise RoutingError("检查组引用未知检查：" + "、".join(sorted(unknown)))
        used_checks.update(check_ids)
    if used_checks != set(names):
        raise RoutingError("存在未进入任何检查组的检查项")
    for stage, group_names in stage_checks.items():
        if not isinstance(group_names, list) or not group_names:
            raise RoutingError(f"阶段缺少检查组：{stage}")
        unknown = set(group_names) - set(groups)
        if unknown:
            raise RoutingError("阶段引用未知检查组：" + "、".join(sorted(unknown)))
        actual_checks = {
            check_id
            for group_name in group_names
            for check_id in groups[group_name]
        }
        missing = MANDATORY_STAGE_CHECKS[stage] - actual_checks
        if missing:
            raise RoutingError(
                f"阶段强制检查不可关闭：{stage}缺少"
                + "、".join(sorted(missing))
            )


def _validate_marketing_boundaries(policy: dict[str, Any], cache: dict[Path, str]) -> None:
    marketing = policy["营销类别路由"]
    if set(marketing) != {"共用前置", "类别", "共用收尾"}:
        raise RoutingError("营销类别路由结构不完整")
    source = _resolve_reference("references/marketing-reasoning.md")
    text = _cached_read(source, cache)
    locations = _heading_locations(text)
    root_matches = [
        item for item in locations if item["heading"] == "## 分类模型调用卡总库"
    ]
    if len(root_matches) != 1:
        raise RoutingError("无法定位唯一分类模型调用卡总库")
    root_line = int(root_matches[0]["line"])
    root_end = min(
        (
            int(item["line"])
            for item in locations
            if int(item["line"]) > root_line and int(item["level"]) <= 2
        ),
        default=sys.maxsize,
    )
    for key, entries in marketing["类别"].items():
        if not isinstance(key, str) or not key.startswith("模型_"):
            raise RoutingError(f"营销类别键格式错误：{key}")
        for entry in entries:
            if entry["文件"] != "references/marketing-reasoning.md":
                raise RoutingError("营销类别只能路由到唯一模型总库")
            for heading in entry["章节"]:
                matches = [item for item in locations if item["heading"] == heading]
                if (
                    len(matches) != 1
                    or int(matches[0]["level"]) != 3
                    or not root_line < int(matches[0]["line"]) < root_end
                ):
                    raise RoutingError(f"营销类别不在总库直属分类中：{heading}")


def validate_policy(policy: dict[str, Any]) -> None:
    if not isinstance(policy, dict) or set(policy) != REQUIRED_TOP_LEVEL_KEYS:
        raise RoutingError("路由配置顶层字段不符合固定结构")
    if policy["配置版本"] != 1:
        raise RoutingError("不支持的路由配置版本")
    if not isinstance(policy["用途"], str) or not policy["用途"]:
        raise RoutingError("路由配置必须说明只读用途")
    read_policy = policy["读取策略"]
    if not isinstance(read_policy, dict) or set(read_policy) != REQUIRED_READ_POLICY_KEYS:
        raise RoutingError("读取策略字段不符合固定结构")
    if read_policy["允许整文件回退"] is not False:
        raise RoutingError("不得开启整文件回退")
    if read_policy["允许整库回退"] is not False:
        raise RoutingError("不得开启整库回退")
    for mapping_name in ("检查名称", "检查组", "阶段检查", "阶段路由", "特征路由"):
        if not isinstance(policy[mapping_name], dict) or not policy[mapping_name]:
            raise RoutingError(f"配置字段必须是非空对象：{mapping_name}")

    cache: dict[Path, str] = {}
    for entries in _all_route_lists(policy):
        _validate_entries(entries, cache)
    _validate_checks(policy)
    _validate_marketing_boundaries(policy, cache)


def load_policy(path: Path = DEFAULT_POLICY) -> dict[str, Any]:
    try:
        policy = json.loads(_read_utf8(Path(path)))
    except json.JSONDecodeError as exc:
        raise RoutingError(f"路由配置不是合法 JSON：{exc}") from exc
    validate_policy(policy)
    return policy


def _expand_entries(entries: list[dict[str, Any]]) -> list[dict[str, str]]:
    expanded: list[dict[str, str]] = []
    for entry in entries:
        for heading in entry["章节"]:
            expanded.append({"文件": entry["文件"], "章节": heading})
    return expanded


def _required_checks(stage: str, policy: dict[str, Any]) -> list[dict[str, str]]:
    checks: list[dict[str, str]] = []
    seen: set[str] = set()
    for group_name in policy["阶段检查"][stage]:
        for check_id in policy["检查组"][group_name]:
            if check_id not in seen:
                seen.add(check_id)
                checks.append({"编号": check_id, "名称": policy["检查名称"][check_id]})
    return checks


def resolve_context(
    stage: str,
    features: list[str],
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """把规范化阶段与特征键解析为确定性的检查和 Markdown 章节。"""
    policy = policy or load_policy()
    if stage not in policy["阶段路由"]:
        raise RoutingError(f"未知阶段：{stage}")
    if not isinstance(features, list) or not all(isinstance(key, str) for key in features):
        raise RoutingError("特征必须是字符串数组")

    regular_features = policy["特征路由"]
    marketing = policy["营销类别路由"]
    marketing_features = marketing["类别"]
    unknown = [key for key in features if key not in regular_features and key not in marketing_features]
    if unknown:
        raise RoutingError("未知特征：" + "、".join(dict.fromkeys(unknown)))

    unique_features = list(dict.fromkeys(features))
    entries = list(policy["阶段路由"][stage])
    marketing_added = False
    for feature in unique_features:
        if feature in regular_features:
            entries.extend(regular_features[feature])
        else:
            if not marketing_added:
                entries.extend(marketing["共用前置"])
                marketing_added = True
            entries.extend(marketing_features[feature])
    if marketing_added:
        entries.extend(marketing["共用收尾"])

    sections: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for item in _expand_entries(entries):
        key = (item["文件"], item["章节"])
        if key not in seen:
            seen.add(key)
            sections.append(item)

    return {
        "阶段": stage,
        "命中特征": unique_features,
        "强制检查": _required_checks(stage, policy),
        "读取章节": sections,
    }


def extract_context(result: dict[str, Any]) -> str:
    """根据已解析结果只输出命中章节，供模型作为本阶段上下文读取。"""
    blocks: list[str] = []
    cache: dict[Path, str] = {}
    for item in result["读取章节"]:
        path = _resolve_reference(item["文件"])
        text = _cached_read(path, cache)
        section = extract_markdown_section(text, item["章节"])
        blocks.append(f"<!-- 来源：{item['文件']} -->\n{section.rstrip()}")
    return "\n\n".join(blocks) + "\n"


def _format_plan(result: dict[str, Any]) -> str:
    lines = [f"阶段：{result['阶段']}"]
    features = "、".join(result["命中特征"]) if result["命中特征"] else "无"
    lines.append(f"命中特征：{features}")
    lines.append("强制检查：")
    lines.extend(f"- {item['编号']} {item['名称']}" for item in result["强制检查"])
    lines.append("读取章节：")
    lines.extend(f"- {item['文件']} :: {item['章节']}" for item in result["读取章节"])
    return "\n".join(lines)


def _list_routes(policy: dict[str, Any]) -> str:
    regular = list(policy["特征路由"])
    marketing = list(policy["营销类别路由"]["类别"])
    return "\n".join(
        [
            "可用阶段：",
            *(f"- {item}" for item in policy["阶段路由"]),
            "可用特征：",
            *(f"- {item}" for item in regular),
            "可用模型类别：",
            *(f"- {item}" for item in marketing),
        ]
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="按现有技能阶段提取最小必要上下文")
    parser.add_argument("--列出", action="store_true", help="列出可用阶段与特征键")
    parser.add_argument("--阶段", help="现有主流程中的阶段键")
    parser.add_argument("--特征", nargs="*", default=[], help="零个或多个规范化特征键")
    parser.add_argument(
        "--格式",
        choices=("text", "json", "markdown"),
        default="text",
        help="输出路由计划、JSON 或命中章节正文",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        policy = load_policy()
        if args.列出:
            print(_list_routes(policy))
            return 0
        if not args.阶段:
            raise RoutingError("必须提供 --阶段，或使用 --列出")
        result = resolve_context(args.阶段, args.特征, policy)
        if args.格式 == "json":
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif args.格式 == "markdown":
            print(extract_context(result), end="")
        else:
            print(_format_plan(result))
        return 0
    except RoutingError as exc:
        print(f"路由失败：{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
