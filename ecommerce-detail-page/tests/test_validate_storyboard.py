#!/usr/bin/env python3
"""精简分镜验证器回归测试。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_storyboard import StoryboardValidationError, validate_storyboard  # noqa: E402


FIXTURE = ROOT / "tests" / "fixtures" / "valid_storyboard.md"


def make_frame(page: int, storyboard_id: str, reference: str = "参考图1") -> str:
    return f"""## 第{page}张（{storyboard_id}）：商品识别
- 输出对象：【主图】
- 成图任务：【清楚建立商品识别】
- 画布与布局：【商品居中，占画面一半，右侧保留短文案安全区】
- 商品身份参考图：【{reference}｜锁定目标商品】
- 画面主参考图：【{reference}｜定义正面视角与可见几何】
- 商品锁定：【保持轮廓、结构、比例、颜色与可见原文】
- 允许变化：【只改变背景、光影与留白】
- 视角与事实边界：【不补画未知背面、内部或配件】
- 最终画面：【单个商品稳定放置并成为唯一焦点】
- 镜头与构图：【平视中景，自然透视，焦点落在商品正面】
- 光影、材质与色彩：【柔和侧光，保留真实颜色、反射和接触阴影】
- 生产与后期：【模型生成背景与光影，真实商品层和文字由后期复核】
- 🎨 图生图提示词：
```text
以{reference}锁定目标商品身份和正面几何，完整保持商品轮廓、结构、比例、颜色和可见原文，只生成简洁背景、柔和侧光、真实接触阴影和右侧低细节安全区，画面只出现一个商品，不补画未知背面、内部或配件。
```
- ⚠️ 动态负面提示词：
```text
商品变形，结构增减，错误颜色，错误文字，虚构背面，虚构内部，新增配件，悬浮，接触阴影错误，多主体，乱码
```
"""


def make_storyboard(frames: list[str], references: list[str] | None = None) -> str:
    references = references or ["参考图1"]
    index = "\n".join(f"- {reference}：【真实商品｜本张身份与视角依据】" for reference in references)
    return f"````markdown\n### 参考图索引\n{index}\n\n" + "\n".join(frames) + "````\n"


class StoryboardValidatorTests(unittest.TestCase):
    def test_valid_fixture(self) -> None:
        result = validate_storyboard(FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(result, ["主图-01"])

    def test_multiple_frames_can_use_different_reference_subsets(self) -> None:
        markdown = make_storyboard(
            [make_frame(1, "主图-01", "参考图1"), make_frame(2, "主图-02", "参考图2")],
            ["参考图1", "参考图2"],
        )
        self.assertEqual(validate_storyboard(markdown), ["主图-01", "主图-02"])

    def test_missing_required_field_is_rejected(self) -> None:
        markdown = make_storyboard([make_frame(1, "主图-01").replace("- 商品锁定：", "- 已删除字段：", 1)])
        with self.assertRaises(StoryboardValidationError):
            validate_storyboard(markdown)

    def test_empty_optional_field_is_rejected(self) -> None:
        frame = make_frame(1, "主图-01").replace("- 商品锁定：", "- 最终文案：\n- 商品锁定：", 1)
        with self.assertRaises(StoryboardValidationError):
            validate_storyboard(make_storyboard([frame]))

    def test_english_prompts_are_rejected(self) -> None:
        markdown = make_storyboard([make_frame(1, "主图-01")])
        markdown = markdown.replace(
            "以参考图1锁定目标商品身份和正面几何，完整保持商品轮廓、结构、比例、颜色和可见原文，只生成简洁背景、柔和侧光、真实接触阴影和右侧低细节安全区，画面只出现一个商品，不补画未知背面、内部或配件。",
            "Keep the product unchanged on a clean studio background.",
        )
        with self.assertRaises(StoryboardValidationError):
            validate_storyboard(markdown)

    def test_almost_entirely_english_prompt_is_rejected(self) -> None:
        markdown = make_storyboard([make_frame(1, "主图-01")])
        markdown = markdown.replace(
            "以参考图1锁定目标商品身份和正面几何，完整保持商品轮廓、结构、比例、颜色和可见原文，只生成简洁背景、柔和侧光、真实接触阴影和右侧低细节安全区，画面只出现一个商品，不补画未知背面、内部或配件。",
            "Keep 参考图1 unchanged and render a clean premium studio product photo with realistic lighting, shadows, composition, materials and typography. 中文",
        )
        with self.assertRaises(StoryboardValidationError):
            validate_storyboard(markdown)

    def test_unknown_public_field_is_rejected(self) -> None:
        markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
            "- 成图任务：", "- 内部评分：95\n- 成图任务：", 1
        )
        with self.assertRaises(StoryboardValidationError):
            validate_storyboard(markdown)

    def test_extra_report_outside_frames_is_rejected(self) -> None:
        markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
            "### 参考图索引", "内部评分与审查报告：95分\n\n### 参考图索引", 1
        )
        with self.assertRaises(StoryboardValidationError):
            validate_storyboard(markdown)

    def test_extra_heading_inside_frame_is_rejected(self) -> None:
        markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
            "- 输出对象：", "### 内部审查报告\n结论：通过\n\n- 输出对象：", 1
        )
        with self.assertRaises(StoryboardValidationError):
            validate_storyboard(markdown)

    def test_internal_process_terms_inside_prompt_are_rejected(self) -> None:
        markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
            "完整保持商品轮廓", "内部评分95分，完整保持商品轮廓", 1
        )
        with self.assertRaises(StoryboardValidationError):
            validate_storyboard(markdown)

    def test_quantity_note_is_the_only_allowed_preamble_line(self) -> None:
        markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
            "### 参考图索引",
            "> 数量说明：用户要求2张，现有素材只能真实制作1张。\n\n### 参考图索引",
            1,
        )
        self.assertEqual(validate_storyboard(markdown), ["主图-01"])

    def test_quantity_note_accepts_natural_chinese_counts(self) -> None:
        notes = (
            "> 数量说明：用户要求三张，现有素材只能真实制作两张。",
            "> 数量说明：用户要求3 张，现有素材只能真实制作 2 张。",
        )
        for note in notes:
            with self.subTest(note=note):
                markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
                    "### 参考图索引", f"{note}\n\n### 参考图索引", 1
                )
                self.assertEqual(validate_storyboard(markdown), ["主图-01"])

    def test_quantity_note_without_an_image_count_is_rejected(self) -> None:
        markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
            "### 参考图索引",
            "> 数量说明：内部评分与审查报告95分。\n\n### 参考图索引",
            1,
        )
        with self.assertRaises(StoryboardValidationError):
            validate_storyboard(markdown)

    def test_english_product_name_is_allowed_inside_chinese_prompts(self) -> None:
        markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
            "目标商品身份和正面几何", "iPhone 16 Pro Max MagSafe USB-C商品身份和正面几何", 1
        )
        self.assertEqual(validate_storyboard(markdown), ["主图-01"])

    def test_short_chinese_negative_prompt_is_allowed(self) -> None:
        markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
            "商品变形，结构增减，错误颜色，错误文字，虚构背面，虚构内部，新增配件，悬浮，接触阴影错误，多主体，乱码",
            "商品变形、错色、乱码",
            1,
        )
        self.assertEqual(validate_storyboard(markdown), ["主图-01"])

    def test_template_placeholder_is_rejected(self) -> None:
        markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
            "【清楚建立商品识别】", "【填写：本张唯一需要解决的问题】", 1
        )
        with self.assertRaises(StoryboardValidationError):
            validate_storyboard(markdown)

    def test_common_secret_formats_are_rejected(self) -> None:
        secrets = (
            "Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.signature",
            "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.signature",
            "password=SuperSecret12345",
            "Cookie: sessionid=abcdef1234567890",
        )
        for secret in secrets:
            with self.subTest(secret=secret.split("=", 1)[0]):
                markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
                    "真实商品层和文字由后期复核", secret, 1
                )
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(markdown)

    def test_output_object_must_match_storyboard_id(self) -> None:
        markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
            "- 输出对象：【主图】", "- 输出对象：【详情页】", 1
        )
        with self.assertRaises(StoryboardValidationError):
            validate_storyboard(markdown)

    def test_supported_output_objects_use_matching_ids(self) -> None:
        output_objects = ("主图", "SKU图", "详情页", "海报", "白底图", "透明图", "无字场景图")
        for output_object in output_objects:
            with self.subTest(output_object=output_object):
                frame = make_frame(1, f"{output_object}-01").replace(
                    "- 输出对象：【主图】", f"- 输出对象：【{output_object}】", 1
                )
                self.assertEqual(validate_storyboard(make_storyboard([frame])), [f"{output_object}-01"])

    def test_auxiliary_reference_must_be_bound_in_prompt(self) -> None:
        frame = make_frame(1, "主图-01").replace(
            "- 商品锁定：", "- 辅助参考图：【参考图2｜补充局部细节】\n- 商品锁定：", 1
        )
        markdown = make_storyboard([frame], ["参考图1", "参考图2"])
        with self.assertRaises(StoryboardValidationError):
            validate_storyboard(markdown)

    def test_outer_markdown_fence_is_optional(self) -> None:
        markdown = make_storyboard([make_frame(1, "主图-01")])
        markdown = markdown.removeprefix("````markdown\n").removesuffix("````\n")
        self.assertEqual(validate_storyboard(markdown), ["主图-01"])

    def test_unknown_reference_is_rejected(self) -> None:
        markdown = make_storyboard([make_frame(1, "主图-01", "参考图2")], ["参考图1"])
        with self.assertRaises(StoryboardValidationError):
            validate_storyboard(markdown)

    def test_malformed_prompt_fence_is_rejected(self) -> None:
        markdown = make_storyboard([make_frame(1, "主图-01")]).replace("```text", "```", 1)
        with self.assertRaises(StoryboardValidationError):
            validate_storyboard(markdown)

    def test_partial_mode_preserves_original_pages(self) -> None:
        markdown = make_storyboard([make_frame(2, "主图-02")])
        with self.assertRaises(StoryboardValidationError):
            validate_storyboard(markdown)
        self.assertEqual(validate_storyboard(markdown, partial=True), ["主图-02"])

    def test_duplicate_storyboard_id_is_rejected(self) -> None:
        markdown = make_storyboard([make_frame(1, "主图-01"), make_frame(2, "主图-01")])
        with self.assertRaises(StoryboardValidationError):
            validate_storyboard(markdown)


if __name__ == "__main__":
    unittest.main(verbosity=2)
