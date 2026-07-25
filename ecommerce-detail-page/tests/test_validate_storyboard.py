#!/usr/bin/env python3
"""精简分镜验证器回归测试。"""

from __future__ import annotations

import sys
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_storyboard import StoryboardValidationError, validate_storyboard  # noqa: E402


FIXTURE = ROOT / "tests" / "fixtures" / "valid_storyboard.md"


def make_frame(
    page: int,
    storyboard_id: str,
    reference_usage: str = "已分析全部有效参考视觉；本张实际向生成模型提供全部同款参考图，按目标SKU/状态筛选共同商品特征，其他SKU不作为生成参考输入，同款资料一致，无需裁决",
    prompt_reference_usage: str | None = None,
) -> str:
    if prompt_reference_usage is None:
        if "一张" in reference_usage or "单张" in reference_usage:
            prompt_reference_usage = "只使用当前最清晰的一张参考图提取商品身份、正面几何和共同特征"
        elif "多张" in reference_usage:
            prompt_reference_usage = "本张实际向生成模型提供多张同款参考图，按目标SKU/状态筛选商品身份、几何、颜色和局部细节，确认内容属于同一目标SKU，同款资料一致，无需裁决"
        else:
            prompt_reference_usage = "本张实际向生成模型提供全部同款参考图，按目标SKU/状态筛选商品身份、正面几何和共同特征，其他SKU不作为生成参考输入，同款资料一致，无需裁决"
    return f"""## 第{page}张（{storyboard_id}）：商品识别
- 输出对象：【主图】
- 成图任务：【清楚建立商品识别】
- 画布与布局：【商品居中完整呈现，轮廓清楚，右侧保留低细节短文案安全区，关键结构避开裁切边界】
- 参考图使用：【{reference_usage}】
- 商品锁定：【保持轮廓、结构、比例、颜色与可见原文】
- 允许变化：【只改变背景、光影与留白】
- 视角与事实边界：【不补画未知背面、内部或配件】
- 最终画面：【单个商品稳定放置并成为唯一焦点】
- 镜头与构图：【平视中景，自然透视，焦点落在商品正面】
- 光影、材质与色彩：【柔和侧光，保留真实颜色、反射和接触阴影】
- 生产与后期：【模型生成背景与光影，真实商品层和文字由后期复核】
- 🎨 图生图提示词：
```text
{prompt_reference_usage}，完整保持商品轮廓、结构、比例、颜色和可见原文，只生成简洁背景、柔和侧光、真实接触阴影和右侧低细节安全区，画面只出现一个商品，不补画未知背面、内部或配件。
```
- ⚠️ 动态负面提示词：
```text
商品变形，结构增减，错误颜色，错误文字，虚构背面，虚构内部，新增配件，悬浮，接触阴影错误，多主体，乱码
```
"""


def make_storyboard(frames: list[str], quantity_note: str | None = None) -> str:
    preamble = f"{quantity_note}\n\n" if quantity_note else ""
    return f"````markdown\n{preamble}" + "\n".join(frames) + "````\n"


class StoryboardValidatorTests(unittest.TestCase):
    def test_runtime_guidance_uses_autonomous_layout_and_copy(self) -> None:
        repository_readme = ROOT.parent / "README.md"
        runtime_paths = [
            repository_readme,
            ROOT / "SKILL.md",
            ROOT / "config" / "context-routing.json",
            *sorted((ROOT / "references").glob("*.md")),
            FIXTURE,
        ]
        runtime_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in runtime_paths
            if path.exists()
        )
        template = (ROOT / "references" / "storyboard-template.md").read_text(
            encoding="utf-8"
        )

        self.assertNotIn("占画面" + "45" + "%", runtime_text)
        self.assertNotIn("画布" + "比例", runtime_text)
        self.assertNotIn("画布" + "尺寸", runtime_text)
        self.assertNotIn("从输入中提取" + "画布" + "比例", runtime_text)
        self.assertNotIn("商品仍是最大且最清楚", runtime_text)
        self.assertNotIn("视觉层级固定为", runtime_text)
        self.assertIn("不限制输出长宽比", runtime_text)
        self.assertIn("参考图的宽高关系不作为输出画面约束", runtime_text)
        self.assertIn("系统根据商品特征、使用场景、输出位置、信息层级和裁切风险自主决定", runtime_text)
        self.assertIn("自主决定是否使用文案", runtime_text)
        self.assertIn("`最终文案`由AI自主决定", template)
        self.assertIn("文案原文、信息层级、位置与视觉效果", template)

        template_frame = template.split("````markdown\n", 1)[1].split("\n````", 1)[0]
        fixture_text = FIXTURE.read_text(encoding="utf-8")
        readme = repository_readme.read_text(encoding="utf-8")
        readme_example = readme.split("## 最终分镜提示词示例", 1)[1].split(
            "## 返修方法", 1
        )[0]
        for public_example in (template_frame, fixture_text, readme_example):
            with self.subTest(example=public_example[:24]):
                self.assertNotRegex(
                    public_example,
                    r"(?:系统|AI)(?:根据|依据)[^，。；\n]{0,40}自主决定",
                )

        self.assertIn("普通导航型行动文案", runtime_text)
        self.assertIn("交易条件、权益、时效或稀缺性承诺", runtime_text)

    def test_fixed_canvas_specs_are_rejected_from_every_public_nonproduction_field(self) -> None:
        baseline = {
            "成图任务": "清楚建立商品识别",
            "参考图使用": (
                "已分析全部有效参考视觉；本张实际向生成模型提供全部同款参考图，"
                "按目标SKU/状态筛选共同商品特征，其他SKU不作为生成参考输入，"
                "同款资料一致，无需裁决"
            ),
            "商品锁定": "保持轮廓、结构、比例、颜色与可见原文",
            "允许变化": "只改变背景、光影与留白",
            "视角与事实边界": "不补画未知背面、内部或配件",
            "光影、材质与色彩": "柔和侧光，保留真实颜色、反射和接触阴影",
        }
        cases = {
            "成图任务": "清楚建立商品识别，成图固定为3:4",
            "参考图使用": baseline["参考图使用"] + "；当前输出固定为3:4",
            "商品锁定": "保持商品真实，当前画面固定为3:4",
            "允许变化": "背景可变化，但固定成图比例3:4",
            "视角与事实边界": "不补画未知结构，输出画幅锁定为3:4",
            "光影、材质与色彩": "柔和侧光，最终图片固定为3:4",
        }

        for field_name, value in cases.items():
            with self.subTest(field=field_name):
                frame = make_frame(1, "主图-01").replace(
                    f"- {field_name}：【{baseline[field_name]}】",
                    f"- {field_name}：【{value}】",
                )
                with self.assertRaisesRegex(
                    StoryboardValidationError,
                    field_name,
                ):
                    validate_storyboard(make_storyboard([frame]))

        optional_cases = {
            "场景与人物": "人物站在商品旁，成图固定为3:4",
            "最终文案": "查看详情；当前画面固定为3:4",
        }
        anchor = "- 光影、材质与色彩：【柔和侧光，保留真实颜色、反射和接触阴影】"
        for field_name, value in optional_cases.items():
            with self.subTest(field=field_name):
                frame = make_frame(1, "主图-01").replace(
                    anchor,
                    f"{anchor}\n- {field_name}：【{value}】",
                )
                with self.assertRaisesRegex(
                    StoryboardValidationError,
                    field_name,
                ):
                    validate_storyboard(make_storyboard([frame]))

    def test_product_facts_cannot_be_rebound_as_output_canvas_constraints(self) -> None:
        layout = "商品居中完整呈现，轮廓清楚，右侧保留低细节短文案安全区，关键结构避开裁切边界"
        rejected = (
            "产品图案宽高为5:7，画布沿用该比例",
            "包装图案尺寸为1080×1440像素，画布采用该尺寸",
            "商品本体是横版，所以成图保持同一方向",
            "商品本体规格为A4，输出采用相同规格",
            "产品图案宽高为5:7，画布并非不沿用该比例",
        )
        allowed = (
            "产品图案宽高为5:7，画布按内容自适应",
            "包装图案尺寸为1080×1440像素，画面根据任务自主组织",
            "商品本体是横版，成图方向由使用场景和信息动线决定",
            "商品本体规格为A4，输出构图按内容自适应",
            "产品图案宽高为5:7，画布不沿用该比例，按内容自适应",
            "产品图案宽高为5:7，画布采用与该比例无关的自适应布局",
            "包装图案尺寸为1080×1440像素，画布采用不同于该尺寸的布局",
        )

        for phrase in rejected:
            with self.subTest(result="reject", phrase=phrase):
                frame = make_frame(1, "主图-01").replace(layout, phrase)
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(make_storyboard([frame]))

        for phrase in allowed:
            with self.subTest(result="allow", phrase=phrase):
                frame = make_frame(1, "主图-01").replace(layout, phrase)
                self.assertEqual(
                    ["主图-01"],
                    validate_storyboard(make_storyboard([frame])),
                )

    def test_product_physical_facts_remain_allowed_in_noncomposition_fields(self) -> None:
        product_facts = (
            "零售彩盒的物理尺寸为二十六乘九乘九厘米",
            "灯板实体排列为六十四乘三十二颗发光像素",
            "商品自身长边是短边的一点六倍，此为实物轮廓事实",
        )
        baseline = "保持轮廓、结构、比例、颜色与可见原文"

        for product_fact in product_facts:
            with self.subTest(product_fact=product_fact):
                frame = make_frame(1, "主图-01").replace(
                    f"- 商品锁定：【{baseline}】",
                    f"- 商品锁定：【{product_fact}；{baseline}】",
                )
                self.assertEqual(
                    ["主图-01"],
                    validate_storyboard(make_storyboard([frame])),
                )

    def test_fixed_canvas_specs_are_rejected_from_composition_fields(self) -> None:
        cases = {
            "layout_numeric_aspect_ratio": (
                "画布与布局",
                "竖版3:4，商品居中并保留右侧留白",
            ),
            "layout_fullwidth_aspect_ratio": (
                "画布与布局",
                "竖版３：４，商品居中并保留右侧留白",
            ),
            "layout_slash_aspect_ratio": (
                "画布与布局",
                "竖版3/4，商品居中并保留右侧留白",
            ),
            "layout_chinese_aspect_ratio": (
                "画布与布局",
                "竖版三比四，商品居中并保留右侧留白",
            ),
            "layout_chinese_colon_aspect_ratio": (
                "画布与布局",
                "竖版四：五，商品居中并保留右侧留白",
            ),
            "layout_multiplication_aspect_ratio": (
                "画布与布局",
                "采用4×5画幅，商品居中并保留右侧留白",
            ),
            "layout_scalar_aspect_ratio": (
                "画布与布局",
                "成图宽高比为0.8，商品居中并保留右侧留白",
            ),
            "layout_pixel_dimensions": (
                "画布与布局",
                "输出1080×1440像素，商品居中并保留右侧留白",
            ),
            "layout_bare_separate_pixel_dimensions": (
                "画布与布局",
                "宽1080px，高1440px，商品居中并保留右侧留白",
            ),
            "layout_multiply_pixel_dimensions": (
                "画布与布局",
                "成图尺寸1080乘1440像素，商品居中并保留右侧留白",
            ),
            "layout_physical_canvas_dimensions": (
                "画布与布局",
                "画布300×400毫米，商品居中并保留右侧留白",
            ),
            "layout_screen_fit_cannot_hide_output_pixels": (
                "画布与布局",
                "成图1920×1080像素适配屏幕，商品居中并保留右侧留白",
            ),
            "layout_product_pixel_size_is_not_product_geometry": (
                "画布与布局",
                "商品宽1080px，高1440px，右侧保留短文案区",
            ),
            "final_image_subject_percentage": (
                "最终画面",
                "单个商品占画面37%，右侧保留短文案区",
            ),
            "composition_fullwidth_subject_percentage": (
                "镜头与构图",
                "平视中景，商品占画面６２％，焦点落在正面",
            ),
            "layout_half_occupancy": (
                "画布与布局",
                "商品占画面一半，右侧保留短文案区",
            ),
            "layout_chinese_percentage": (
                "画布与布局",
                "商品占画面百分之四十五，右侧保留短文案区",
            ),
            "layout_chinese_fraction": (
                "画布与布局",
                "商品占画面三分之二，右侧保留短文案区",
            ),
            "layout_chinese_tenths": (
                "画布与布局",
                "主体约占四成版面，右侧保留短文案区",
            ),
            "layout_height_percentage": (
                "画布与布局",
                "主体高度为画面高度的45%，右侧保留短文案区",
            ),
            "layout_inherits_reference_frame": (
                "画布与布局",
                "沿用参考图外框和宽高关系组织输出画面",
            ),
            "layout_follows_reference_ratio": (
                "画布与布局",
                "输出比例跟随参考图，商品居中并保留右侧留白",
            ),
            "layout_uses_reference_dimensions": (
                "画布与布局",
                "按参考图宽高关系组织成图，商品居中并保留右侧留白",
            ),
            "layout_treats_reference_as_constraint": (
                "画布与布局",
                "参考图宽高关系作为输出画面约束",
            ),
            "layout_keeps_same_reference_ratio": (
                "画布与布局",
                "成图保持与参考图相同的宽高比",
            ),
            "layout_ratio_comes_from_reference": (
                "画布与布局",
                "输出宽高比取自参考图",
            ),
            "layout_matches_reference_ratio": (
                "画布与布局",
                "匹配参考图比例生成成图",
            ),
            "layout_ratio_based_on_reference": (
                "画布与布局",
                "根据参考图比例生成成图",
            ),
            "layout_ratio_equals_reference": (
                "画布与布局",
                "成图比例和参考图一致",
            ),
            "layout_keeps_original_ratio": (
                "画布与布局",
                "成图维持原图比例",
            ),
            "layout_ratio_equals_original_ratio": (
                "画布与布局",
                "成图比例等于原图比例",
            ),
            "layout_uses_reference_visual_ratio": (
                "画布与布局",
                "按参考视觉比例生成成图",
            ),
            "layout_positive_inheritance_after_negated_inheritance": (
                "画布与布局",
                "不沿用参考图外框而根据参考图比例生成成图",
            ),
        }

        original_values = {
            "画布与布局": "商品居中完整呈现，轮廓清楚，右侧保留低细节短文案安全区，关键结构避开裁切边界",
            "最终画面": "单个商品稳定放置并成为唯一焦点",
            "镜头与构图": "平视中景，自然透视，焦点落在商品正面",
        }
        for name, (field_name, replacement) in cases.items():
            with self.subTest(name=name):
                frame = make_frame(1, "主图-01").replace(
                    original_values[field_name],
                    replacement,
                )
                with self.assertRaisesRegex(StoryboardValidationError, "固定画幅"):
                    validate_storyboard(make_storyboard([frame]))

    def test_fixed_canvas_specs_are_rejected_from_positive_prompt(self) -> None:
        replacements = {
            "aspect_ratio": "生成横版16:9画面，只生成简洁背景",
            "natural_aspect_ratio": "采用3:4比例组织留白，只生成简洁背景",
            "pixel_dimensions": "输出1080×1440像素成图，只生成简洁背景",
            "separate_pixel_dimensions": "输出宽1080像素、高1440像素，只生成简洁背景",
            "bare_separate_pixel_dimensions": "宽1080px，高1440px的输出画面，只生成简洁背景",
            "multiply_pixel_dimensions": "成图尺寸1080乘1440像素，只生成简洁背景",
            "english_by_pixel_dimensions": "输出1080 by 1440像素高清图，只生成简洁背景",
            "subject_percentage": "商品占画面45%，只生成简洁背景",
            "subject_fraction": "商品占画面2/3，只生成简洁背景",
            "reference_frame_inheritance": "沿用参考图外框和宽高关系组织输出画面，只生成简洁背景",
            "reference_same_ratio": "成图保持与参考图相同的宽高比，只生成简洁背景",
            "reference_ratio_source": "输出宽高比取自参考图，只生成简洁背景",
            "reference_ratio_match": "匹配参考图比例生成成图，只生成简洁背景",
            "reference_ratio_basis": "根据参考图比例生成成图，只生成简洁背景",
            "plain_ratio_generation": "使用3:4比例生成主图，只生成简洁背景",
            "plain_ratio_output": "按3:4出图，只生成简洁背景",
            "plain_pixel_image": "制作1080×1440像素图片，只生成简洁背景",
            "plain_pixel_export": "请按1080×1440导出，只生成简洁背景",
        }

        for name, replacement in replacements.items():
            with self.subTest(name=name):
                frame = make_frame(1, "主图-01").replace(
                    "只生成简洁背景",
                    replacement,
                )
                with self.assertRaisesRegex(StoryboardValidationError, "固定画幅"):
                    validate_storyboard(make_storyboard([frame]))

    def test_unquantified_output_frame_locks_and_output_subject_share_are_rejected(self) -> None:
        cases = {
            "task_frame_must_not_change": (
                "成图任务",
                "清楚建立商品识别",
                "画幅不得改变",
            ),
            "task_output_ratio_must_not_be_autonomous": (
                "成图任务",
                "清楚建立商品识别",
                "输出比例不得自主决定",
            ),
            "task_output_frame_cannot_be_system_selected": (
                "成图任务",
                "清楚建立商品识别",
                "输出画幅不能由系统自主决定",
            ),
            "task_output_ratio_is_user_selected": (
                "成图任务",
                "清楚建立商品识别",
                "输出比例由用户决定",
            ),
            "layout_output_frame_keeps_original": (
                "画布与布局",
                "商品居中完整呈现，轮廓清楚，右侧保留低细节短文案安全区，关键结构避开裁切边界",
                "最终画面必须保持原样",
            ),
            "layout_output_frame_keeps_unchanged": (
                "画布与布局",
                "商品居中完整呈现，轮廓清楚，右侧保留低细节短文案安全区，关键结构避开裁切边界",
                "画幅保持不变",
            ),
            "layout_subject_share_of_output_frame": (
                "画布与布局",
                "商品居中完整呈现，轮廓清楚，右侧保留低细节短文案安全区，关键结构避开裁切边界",
                "核心主体占输出画面一半",
            ),
            "layout_subject_share_with_output_frame_area": (
                "画布与布局",
                "商品居中完整呈现，轮廓清楚，右侧保留低细节短文案安全区，关键结构避开裁切边界",
                "核心主体占输出画面面积的一半",
            ),
        }

        for name, (field_name, original, replacement) in cases.items():
            with self.subTest(name=name):
                frame = make_frame(1, "主图-01").replace(
                    f"- {field_name}：【{original}】",
                    f"- {field_name}：【{replacement}】",
                )
                with self.assertRaisesRegex(StoryboardValidationError, "固定画幅"):
                    validate_storyboard(make_storyboard([frame]))

    def test_unquantified_canvas_phrase_can_remain_visible_copy(self) -> None:
        anchor = "- 光影、材质与色彩：【柔和侧光，保留真实颜色、反射和接触阴影】"
        frame = make_frame(1, "主图-01").replace(
            anchor,
            f"{anchor}\n- 最终文案：【输出比例不得自主决定】",
        )
        self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_product_fact_preservation_is_not_an_output_frame_lock(self) -> None:
        original = "商品居中完整呈现，轮廓清楚，右侧保留低细节短文案安全区，关键结构避开裁切边界"
        frame = make_frame(1, "主图-01").replace(
            original,
            "画幅不得改变商品自身比例，构图由系统根据商品特征自主决定",
        )
        self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_explicit_platform_dimensions_are_allowed_only_in_production_field(self) -> None:
        frame = make_frame(1, "主图-01").replace(
            "模型生成背景与光影，真实商品层和文字由后期复核",
            "用户已明确要求平台交付竖版3:4、1080×1440像素；模型生成背景与光影，真实商品层和文字由后期复核",
        )

        self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_natural_fixed_output_dimensions_are_rejected(self) -> None:
        layouts = (
            "成图宽高比设成0.75",
            "成图比例控制在0.8",
            "出图比例控制在0.8",
            "成图长宽比为0.8",
            "海报比例3:4，商品居中",
            "详情页比例3:4，商品居中",
            "SKU图比例1:1，商品居中",
            "整体版面比例4:5，商品居中",
            "页面长宽比3:4，商品居中",
            "导出比例3:4，商品居中",
            "最终版面比例3:4，商品居中",
            "成图采用九比十六的纵向比例",
            "成图长边1600像素、短边1200像素",
            "成图长边1440像素、短边1080像素",
            "画布宽是1080像素，高是1440像素",
            "尺寸为1080像素宽、1440像素高",
            "输出尺寸为1080像素宽、1440像素高",
            "输出分辨率为1080*1440",
            "输出尺寸设成1200像素乘1600像素",
            "导出1080像素×1440像素",
            "主图尺寸是宽1080、长1440像素",
            "画面控制为1080像素乘以1440像素",
            "最终图片宽度必须是1200像素",
            "画面尺寸固定为30厘米宽、40厘米高",
            "画布定为640像素宽、960像素长",
            "主图高是宽的1.5倍",
            "图片的比例锁死在0.8",
            "产品高度等于画布高度的0.6倍",
            "海报尺寸300×400毫米",
            "输出宽度固定为1080像素",
            "成图高度1440px",
            "画布宽1080像素",
            "导出高度为1440像素",
            "主图宽度设为1200px",
            "图片高度控制在1600像素",
            "分辨率宽1080像素",
        )
        original = "商品居中完整呈现，轮廓清楚，右侧保留低细节短文案安全区，关键结构避开裁切边界"
        for layout in layouts:
            with self.subTest(layout=layout):
                frame = make_frame(1, "主图-01").replace(original, layout)
                with self.assertRaisesRegex(StoryboardValidationError, "固定画幅"):
                    validate_storyboard(make_storyboard([frame]))

    def test_reference_frame_inheritance_synonyms_are_rejected(self) -> None:
        layouts = (
            "让成图与原图保持同样比例",
            "复刻参考图的版式比例",
            "成图比例与输入图同步",
            "照着原图来",
            "复制参考图画幅",
            "依原图比例排版",
            "成图比例由原图决定",
            "画面宽高取决于参考图",
            "参照原图确定画幅",
            "以原图为准确定画幅",
            "输出比例以参考图为准",
            "根据原图确定成图比例",
            "成图沿袭参考图外框",
            "不改变商品结构并按参考图比例生成成图",
            "不补画未知背面并沿用参考图外框",
            "不要更改商品且成图保持与参考图相同的宽高比",
            "不改变颜色并输出宽高比取自参考图",
            "不要修改结构同时根据参考图比例生成成图",
            "不复制文字以及匹配参考图比例生成成图",
            "画幅完全复刻参考图",
            "沿袭输入图的画面比例",
            "成图比例照抄原图",
            "用输入图的长宽关系为准进行构图",
            "不沿用参考图外框，但成图仍保持同样比例",
            "参考图外框不作为约束，不过最终画幅必须和它一样",
            "虽然不继承参考图版式，输出仍遵循该素材的横竖关系",
            "延续参考图的横版方向",
            "输入图横向，成图也横向",
            "参考图的比例直接套到输出上",
            "把输入图版式搬到最终成图",
            "成图照原图的画幅走",
            "主图比例随源图变化",
            "以参考图片外框为模板出图",
            "构图必须保持该素材的横竖",
            "照着输入照片的边框出图",
            "源图什么比例就生成什么比例",
            "复制输入影像的外轮廓比例",
            "不要继承输入图版式，输出只需与它同宽同高",
            "参考图比例不锁定输出；实际制作时仍照其长宽出图",
            "参考图外框不作为约束；但成图仍保持同样比例",
            "不沿用参考图外框。成图仍保持同样比例",
            "原图比例仅作参考；输出仍与它一致",
            "输入图横向。成图也横向",
            "海报比例取自参考图",
            "详情页比例沿用原图",
            "SKU图比例跟随输入图",
            "页面比例与原图一致",
            "最终版面比例来自素材图",
            "导出比例按原图确定",
            "沿用参考图尺寸",
            "参考图尺寸作为约束",
            "保持原图分辨率",
            "匹配输入图方向",
            "延续素材图横版",
            "跟随原图裁切边界",
            "按参考图边框生成",
            "照原图形状来",
        )
        original = "商品居中完整呈现，轮廓清楚，右侧保留低细节短文案安全区，关键结构避开裁切边界"
        for layout in layouts:
            with self.subTest(layout=layout):
                frame = make_frame(1, "主图-01").replace(original, layout)
                with self.assertRaisesRegex(StoryboardValidationError, "固定画幅"):
                    validate_storyboard(make_storyboard([frame]))

    def test_fixed_canvas_forms_and_relative_dimensions_are_rejected(self) -> None:
        layouts = (
            "画面固定为正方形画幅",
            "请做成横版画面",
            "按A4竖版纸张比例完成画面",
            "输出最长边固定为2048像素",
            "输出宽一千零八十像素、高一千四百四十像素",
            "高度固定为宽度的一点五倍",
            "让商品填满大约七成版面",
        )
        original = "商品居中完整呈现，轮廓清楚，右侧保留低细节短文案安全区，关键结构避开裁切边界"
        for layout in layouts:
            with self.subTest(layout=layout):
                frame = make_frame(1, "主图-01").replace(original, layout)
                with self.assertRaisesRegex(StoryboardValidationError, "固定画幅"):
                    validate_storyboard(make_storyboard([frame]))

    def test_adversarial_natural_canvas_constraints_are_rejected(self) -> None:
        layouts = (
            # 固定方向或定性外形
            "采用手机满屏竖幅组织成图",
            "输出图片只准使用竖构图",
            "成片必须是方幅，不接受横竖长图",
            "横着出图，商品居中",
            "统一按横屏规格出图",
            "保持横图，不要改成竖图",
            "需要一张横构图",
            "请给我方形版本",
            "画面必须更宽而不是更高",
            "成图做成长条形横幅",
            "一律采用竖向画面",
            "主图要横屏呈现",
            "固定成宽图，不能竖",
            "用竖构图交付",
            # 数字、范围、优先或默认比例
            "画面高为宽的四分之三",
            "宽边必须是高边的1.2倍",
            "宽度不得低于高度的1.5倍",
            "横竖比例锁死，宽比高多一半",
            "宽高关系锁为五比四",
            "不要3:4，要4:5",
            "高宽比至少4:5",
            "宽高比在0.8到1.2之间",
            "比例以9:16为优先",
            "建议4:5，AI可自行调整",
            "默认1:1，必要时由AI调整",
            # 像素、K 制式和物理输出尺寸
            "输出分辨率锁定为2K",
            "画布做成30公分宽、40公分高",
            "最终图片设成1.2K乘1.6K像素",
            "成图宽度必须达到一千二百个像素点",
            # 主体占画面比例
            "产品铺占版面一半",
            "商品面积控制为画面的百分之六十",
            "让主角占住版心的2/3",
            "主商品铺到整个画面的六成",
            "产品可见高度达到画布的0.7倍",
            "主角填满版面的60%",
            "商品视觉面积固定成0.6倍画布面积",
            "把货品压在版心五成五的区域内",
            # 继承参考图外框、方向或长短边关系
            "成片长宽关系照原素材来",
            "输出外形由样图比例决定",
            "保持原照片的画幅不变",
            "复用参考图的长短边关系",
            "不按参考图画幅生成，只把横竖比例照旧",
            "画布方向听从参考素材",
            "把源素材的长短边原样移植到成图",
            "参考图横我也横，参考图竖我也竖",
            "沿着来图的横竖方向出片",
            "输入是横图就做横图，输入是竖图就做竖图",
            "成图方向跟素材保持一模一样",
            "按底图的横纵关系交付",
            "原素材横屏，因此输出也横屏",
            "参考图为竖版，沿同一方向生成",
            # 第二轮独立压力测试补充
            "最终交一张宽幅成品图",
            "按照纵长画面制作成片",
            "画面比例建议设为0.75",
            "高边至少达到宽边的1.4倍",
            "最终图按A4尺寸制作",
            "按A4竖版纸张方向构图",
            "主体占住页面七成半",
            "留白比例固定为25%",
            "货品宽度限制在画幅宽度的3/5",
            "主物面积占据页面0.6",
            "最终外框跟样片保持一致",
            "成图沿着来稿的长短边走",
            "输出方向听原始图片安排",
        )
        original = "商品居中完整呈现，轮廓清楚，右侧保留低细节短文案安全区，关键结构避开裁切边界"
        for layout in layouts:
            with self.subTest(layout=layout):
                frame = make_frame(1, "主图-01").replace(original, layout)
                with self.assertRaisesRegex(StoryboardValidationError, "固定画幅"):
                    validate_storyboard(make_storyboard([frame]))

    def test_natural_subject_occupancy_constraints_are_rejected(self) -> None:
        layouts = (
            "主视觉面积约为0.6",
            "商品铺满画面六成",
            "留白控制在四分之一",
            "三分之二的画面交给商品",
            "画面的七成留作商品区",
            "商品视觉高度限定在画幅的0.7",
            "主体占比定为55%",
            "货品主体填充版心约百分之五十五",
            "主体占比45%，右侧留白",
            "商品占比设为45%，右侧留白",
            "产品视觉占比四成，右侧留白",
            "主物面积占比60%，右侧留白",
            "核心视觉载体占比百分之四十，右侧留白",
        )
        original = "商品居中完整呈现，轮廓清楚，右侧保留低细节短文案安全区，关键结构避开裁切边界"
        for layout in layouts:
            with self.subTest(layout=layout):
                frame = make_frame(1, "主图-01").replace(original, layout)
                with self.assertRaisesRegex(StoryboardValidationError, "固定画幅"):
                    validate_storyboard(make_storyboard([frame]))

    def test_ai_selected_orientation_is_allowed(self) -> None:
        layouts = (
            "系统根据商品结构自主采用横版构图并安排留白",
            "AI根据任务自主将画面做成竖版并安排留白",
            "系统自主选择横版画面并安排留白",
            "经系统自主判断，本张采用横版构图",
            "横版构图，系统根据任务自主决定",
            "系统根据商品结构自主确定为竖版构图",
        )
        original = "商品居中完整呈现，轮廓清楚，右侧保留低细节短文案安全区，关键结构避开裁切边界"
        for layout in layouts:
            with self.subTest(layout=layout):
                frame = make_frame(1, "主图-01").replace(original, layout)
                self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_fixed_orientation_hard_constraints_are_rejected(self) -> None:
        layouts = (
            "输出只能是方图",
            "画面必须为横版",
            "成图限定竖版",
            "图片方向固定横版",
            "要求横版构图",
            "横版是硬性要求",
            "锁定竖版构图",
            "务必使用横版",
            "画幅定为竖版",
            "保持方图输出",
        )
        original = "商品居中完整呈现，轮廓清楚，右侧保留低细节短文案安全区，关键结构避开裁切边界"
        for layout in layouts:
            with self.subTest(layout=layout):
                frame = make_frame(1, "主图-01").replace(original, layout)
                with self.assertRaisesRegex(StoryboardValidationError, "固定画幅"):
                    validate_storyboard(make_storyboard([frame]))

    def test_product_geometry_ratio_is_not_mistaken_for_canvas_ratio(self) -> None:
        frame = make_frame(1, "主图-01").replace(
            "保持轮廓、结构、比例、颜色与可见原文",
            "保持商品自身高宽比例3:1、包装尺寸300×400毫米、显示屏原生分辨率1920×1080像素、颜色与可见原文",
        ).replace(
            "完整保持商品轮廓、结构、比例、颜色和可见原文",
            "画面中完整保持商品自身高宽比例3:1、包装尺寸300×400毫米、显示屏原生分辨率1920×1080像素、颜色和可见原文",
        )

        self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_product_geometry_is_allowed_inside_composition_fields(self) -> None:
        frame = make_frame(1, "主图-01").replace(
            "商品居中完整呈现，轮廓清楚，右侧保留低细节短文案安全区，关键结构避开裁切边界",
            "依据商品自身高宽比3:1的细长结构自主安排留白与视觉动线",
        ).replace(
            "单个商品稳定放置并成为唯一焦点",
            "300×400毫米包装完整放置，商品成为唯一焦点",
        ).replace(
            "平视中景，自然透视，焦点落在商品正面",
            "平视中景对准显示屏原生分辨率1920×1080像素的真实内容",
        )

        self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_postposed_product_geometry_labels_are_allowed(self) -> None:
        cases = {
            "product_ratio_label_after_value": (
                "商品居中完整呈现，轮廓清楚，右侧保留低细节短文案安全区，关键结构避开裁切边界",
                "依据原商品3:1的高宽比自主安排留白",
            ),
            "display_resolution_label_after_value": (
                "平视中景，自然透视，焦点落在商品正面",
                "平视中景对准屏幕1920×1080原生分辨率的真实内容",
            ),
            "display_named_after_resolution": (
                "平视中景，自然透视，焦点落在商品正面",
                "平视中景对准1920×1080像素的显示屏真实内容",
            ),
            "display_separate_output_dimensions": (
                "平视中景，自然透视，焦点落在商品正面",
                "平视中景对准屏幕输出宽1920像素、高1080像素的真实内容",
            ),
        }

        for name, (original, replacement) in cases.items():
            with self.subTest(name=name):
                frame = make_frame(1, "主图-01").replace(original, replacement)
                self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_natural_product_geometry_evidence_is_allowed(self) -> None:
        layouts = (
            "根据参考图中3:1的商品高宽比自主安排构图与留白",
            "参考图显示杯身长宽约3:1，AI据此自主安排构图",
            "3:1为该商品真实高宽比，构图自主",
            "商品为3:1的细长高宽比，构图自主",
            "显示器原生分辨率3840×2160像素，构图自主",
            "参考图显示相框长宽为3:2，AI据此自主构图",
            "参考图显示折叠桌展开长宽2:1，AI根据其结构自主安排留白",
            "相框尺寸300×400毫米完整呈现，构图自主",
            "A4打印纸尺寸210×297毫米完整呈现，构图自主",
            "香水瓶本体的高宽比为1:3，画面由系统自主设计",
            "外盒规格为300×400毫米，系统自主选择画幅",
            "纸箱长宽为400×300毫米，构图自主",
            "屏显原生分辨率2560×1600像素，画幅自主决定",
            "电视屏原生比例16:9，输出画幅由系统另行决定",
            "罐体直径与高度之比1:2属于商品真实几何，构图自主",
            "包装盒长宽高为30×20×10厘米，画面自主组织",
            "产品内置屏为2.8英寸，原生分辨率320×240像素，构图自主",
            "仪表面板原生分辨率1280×480像素，系统自主构图",
            "发光二极管点阵屏原生分辨率640×320像素，画面自主",
            "参考图显示包装3:2结构，输出比例由系统决定",
            "参考图中瓶身呈三比一，系统自主定画幅",
            "商品海报本体长宽比3:4，构图自主",
            "商品是装饰画，画布本体长宽比3:4，构图自主",
            "画布包长宽比3:2，构图自主",
            "商品主图案长宽比2:1，构图自主",
            "画布本体尺寸300×400毫米，构图自主",
        )
        original = "商品居中完整呈现，轮廓清楚，右侧保留低细节短文案安全区，关键结构避开裁切边界"
        for layout in layouts:
            with self.subTest(layout=layout):
                frame = make_frame(1, "主图-01").replace(original, layout)
                self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

        frame = make_frame(1, "主图-01").replace(
            "平视中景，自然透视，焦点落在商品正面",
            "宽1920px、高1080px的显示屏展示真实内容，构图自主",
        )
        self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_non_canvas_ratios_and_product_parameters_are_allowed(self) -> None:
        layouts = (
            "采用3/4侧视角，焦点落在商品正面",
            "以3/4侧面机位展示杯身结构",
            "保留1/4英寸螺纹接口，构图自主",
            "相机传感器尺寸为1/2英寸，构图自主",
            "镜头保持1:1原生放大倍率，构图自主",
            "套装保持3:1数量关系，构图自主",
            "摄像头支持1920×1080视频，构图自主",
            "参考图显示保温杯高宽3:1，AI据此自主构图",
            "参考图显示沙发长宽2:1，AI据此自主构图",
            "显示屏宽1920px、高1080px并展示真实内容，构图自主",
            "商品采用4×5厘米包装，构图自主",
        )
        original = "商品居中完整呈现，轮廓清楚，右侧保留低细节短文案安全区，关键结构避开裁切边界"
        for layout in layouts:
            with self.subTest(layout=layout):
                frame = make_frame(1, "主图-01").replace(original, layout)
                self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_reference_product_ratios_do_not_lock_output_frame(self) -> None:
        layouts = (
            "商品真实比例等于参考图证据，AI自主构图",
            "商品高宽比取自参考图，AI自主构图",
            "杯身比例来自参考图，AI自主安排构图",
            "产品真实比例与参考图一致，AI自主构图",
            "商品外形比例沿用参考图，AI自主构图",
            "沿用参考图中的商品真实比例，AI自主构图",
        )
        original = "商品居中完整呈现，轮廓清楚，右侧保留低细节短文案安全区，关键结构避开裁切边界"
        for layout in layouts:
            with self.subTest(layout=layout):
                frame = make_frame(1, "主图-01").replace(original, layout)
                self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_product_internal_percentages_are_allowed(self) -> None:
        layouts = (
            "产品屏占比为90%，根据真实结构自主构图",
            "商品正面的屏幕覆盖机身面积90%，系统自主安排构图",
            "产品图案覆盖包装正面60%，构图自主",
            "画面展示含棉量95%的产品，系统自主构图",
            "95%含棉量的商品成为视觉焦点，构图自主",
            "画面聚焦电量为80%的设备，构图自主",
            "画面展示包装原文“浓度50%”，构图自主",
            "商品包装原文“有效成分占比20%”逐字保持，构图自主",
            "产品图案覆盖包装正面区域60%，构图自主",
            "商品屏幕占据机身正面区域90%，构图自主",
            "货品标签覆盖盒体区域30%，构图自主",
            "商品应用占存储空间50%，构图自主",
        )
        original = "商品居中完整呈现，轮廓清楚，右侧保留低细节短文案安全区，关键结构避开裁切边界"
        for layout in layouts:
            with self.subTest(layout=layout):
                frame = make_frame(1, "主图-01").replace(original, layout)
                self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_negated_fixed_specs_are_allowed(self) -> None:
        layouts = (
            "不要按16:9输出，系统自主决定画幅",
            "不要求1080×1440像素输出，尺寸交由后期适配",
            "商品不占画面45%，实际占比由系统自主确定",
            "不要锁成一比一方图，画幅由系统自主决定",
            "不把成图比例设成3:4，由系统自主决定",
            "不强制使用3:4比例，由系统自主决定",
            "无需限定1080×1440像素，交给后期适配",
            "请勿将画面做成横版，由系统自主决定",
            "切勿输出3:4画幅，由系统自主决定",
            "系统不一定采用横版，应按商品自主决定",
        )
        original = "商品居中完整呈现，轮廓清楚，右侧保留低细节短文案安全区，关键结构避开裁切边界"
        for layout in layouts:
            with self.subTest(layout=layout):
                frame = make_frame(1, "主图-01").replace(original, layout)
                self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_adversarial_negations_and_product_specs_are_allowed(self) -> None:
        layouts = (
            # 明确否定输出约束
            "成图不固定为3:4，系统自主安排构图",
            "参考图画幅为3:4但不作为输出约束",
            "商品占六成是已否决方案",
            "即便输入图为9:16，也不继承其外框",
            "画面不限定为3:4，系统自由决定",
            "不把画幅固定成1:1",
            "不要按参考图的横版外框出图",
            # 由系统比较后自主决定，不是人工锁定方向
            "对比横版与竖版后由AI选择",
            # 商品本体、包装或显示部件的真实规格
            "三比四不是输出比例，而是包装盒自身宽高比",
            "投影仪原生显示分辨率3840×2160",
            "显示模组原生像素矩阵1920×720",
            "电子墨水面板真实像素1872×1404",
            "纸张规格A4竖版，作为商品实拍",
            "竖版海报是本次拍摄的商品，不是成图规格",
            # 第二轮独立压力测试补充
            "系统比较横版和竖版后自主选择",
            "AI依据任务需要自主选择横版画面并安排留白",
            "成图不是固定4:5，系统自主安排",
            "原照片为3:4，仅描述输入载体，不约束成图",
            "商品占画面七成的方案已被取消",
        )
        original = "商品居中完整呈现，轮廓清楚，右侧保留低细节短文案安全区，关键结构避开裁切边界"
        for layout in layouts:
            with self.subTest(layout=layout):
                frame = make_frame(1, "主图-01").replace(original, layout)
                self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

        camera_fields = (
            "使用85mm镜头，f/4光圈，快门1/125秒，ISO 100，焦点落在商品正面",
            "相机焦距50mm，快门1/60秒，白平衡5600K，焦点落在商品正面",
            "灯光色温约4500K，曝光补偿+0.3EV，焦点落在商品正面",
        )
        original_camera = "平视中景，自然透视，焦点落在商品正面"
        for camera_field in camera_fields:
            with self.subTest(camera_field=camera_field):
                frame = make_frame(1, "主图-01").replace(original_camera, camera_field)
                self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_independent_black_box_canvas_constraints_are_rejected(self) -> None:
        cases = (
            # 中文自然比例、相对边长和输出规格
            ("layout", "宽和高分别按三份与四份配比"),
            ("prompt", "最终图片按三百点每英寸输出"),
            ("layout", "正文安全区域精确保留25%"),
            ("layout", "画布高边固定成短边的两倍"),
            ("layout", "横向五份、纵向四份来确定画框"),
            ("layout", "画面长宽按照七五开的比例"),
            ("prompt", "成图每条边固定十厘米"),
            ("layout", "最终画框限定为纵边是横边的四分之五"),
            ("prompt", "输出图的宽边固定为1200点"),
            ("prompt", "画面高宽固定采用每五份高配四份宽"),
            ("layout", "画布宽高固定为四份对七份"),
            ("layout", "最终图采用平方画框"),
            ("layout", "画面纵横两边按七份和十一份分配"),
            ("prompt", "成品宽边固定一千五百像素点"),
            ("layout", "成图宽边至少是高边的1.3倍"),
            # 主体、留白与安全区占比
            ("layout", "让产品的可见高度达到画布的0.7倍"),
            ("layout", "商品边界覆盖画布宽度的四分之三"),
            ("layout", "让核心产品吃掉画面一半空间"),
            ("layout", "产品在版心内占五成五"),
            ("layout", "主商品尺寸覆盖成图纵边的七成半"),
            ("layout", "商品在画心占到百分之六十五"),
            ("layout", "主产品展开宽度覆盖输出图八成"),
            ("layout", "主商品高度占据成片约百分之七十二"),
            ("layout", "主商品盖住画布约七成"),
            ("layout", "让主体宽到页面的四分之三"),
            ("layout", "留出30%的空白区域"),
            ("layout", "货品可见高度不得低于画面80%"),
            ("layout", "商品宽度不超过画布的70%"),
            # 参考来源的外框、版式、方向与尺寸继承
            ("layout", "构图外框锁定为参考视觉的边界"),
            ("layout", "锁定原图的边框形状再生成"),
            ("layout", "并非套用原图外框，只是锁定原有长宽关系"),
            ("layout", "不直接使用参考图比例，只把画布定成与参考素材等比例"),
            ("layout", "承袭样片边框形状生成"),
            ("layout", "照原始照片的横竖尺寸关系排版"),
            ("layout", "沿着样张版心比例制作"),
            ("layout", "锁死与底图一致的边界形态"),
            ("layout", "成图必须保有原素材的纵横关系"),
            ("layout", "最终画框照旧沿袭上传照片"),
            ("prompt", "参照底片原来的横纵尺度出图"),
            ("layout", "输出套用参考底稿的边框轮廓"),
            ("layout", "输入多宽多高，输出也多宽多高"),
            ("layout", "不复制参考图内容，但版式照搬"),
            ("layout", "只取商品信息，同时保留源图画幅"),
            # 否定、后期规格、输出治理与自然方向的对抗边界
            ("layout", "不需要修改商品，但成图保持与参考图同宽同高"),
            ("layout", "4:5曾被排除，但当前重新采用"),
            ("layout", "后期规格为4:5，当前构图也按它执行"),
            ("layout", "参考图只提取商品。版式仍照搬。"),
            ("layout", "照片横着排就行"),
            ("layout", "宽高差必须控制在两成内"),
            ("layout", "画布宽高比必须控制在1.2以内"),
            ("layout", "宽度必须比高度多20%"),
            ("layout", "画布真实几何比例为4:5"),
            ("layout", "成图真实比例为4:5"),
            ("layout", "输出图原生比例为4:5"),
            ("layout", "为显示器输出1920×1080成图"),
            ("layout", "输出1920×1080适配显示屏"),
        )
        original_layout = "商品居中完整呈现，轮廓清楚，右侧保留低细节短文案安全区，关键结构避开裁切边界"
        original_prompt_usage = "本张实际向生成模型提供全部同款参考图，按目标SKU/状态筛选商品身份、正面几何和共同特征，其他SKU不作为生成参考输入，同款资料一致，无需裁决"

        for field, phrase in cases:
            with self.subTest(field=field, phrase=phrase):
                frame = make_frame(1, "主图-01")
                if field == "layout":
                    frame = frame.replace(original_layout, f"{original_layout}；{phrase}")
                else:
                    frame = frame.replace(
                        original_prompt_usage,
                        f"{phrase}；{original_prompt_usage}",
                    )
                with self.assertRaisesRegex(StoryboardValidationError, "固定画幅"):
                    validate_storyboard(make_storyboard([frame]))

    def test_independent_black_box_negations_and_product_specs_are_allowed(self) -> None:
        layouts = (
            "轮胎外径与胎宽之比4:1，系统据此自主构图",
            "不让参考素材决定横竖方向，系统自主选择",
            "A4只属于后期交付规格，不约束当前构图",
            "输出不是4:5，比例由AI自由决定",
            "4:5仅是已排除的旧方案",
            "成图与参考图不需要同宽同高",
            "留白30%不是要求，实际由系统决定",
            "AI可根据首屏任务自行用横图呈现",
            "系统依据内容自动选择横构图或竖构图",
            "设备屏幕物理像素为2560×1440，输出画幅自主",
            "不照搬参考图版式，只提取商品结构",
            "后期交付规格为4:5、1080×1350像素，不约束当前构图",
            "商品包装规格4:5，输出画幅自主",
            "参考图只提取商品。版式由系统自主决定。",
            "横着还是竖着由系统选择",
            "画幅并不是非得竖着，交给系统选",
            "无需照素材的横竖走",
            "屏幕拥有3840×2160物理像素，构图自主",
            "显示器的物理像素为3840×2160，构图自主",
            "这块屏幕由2560×1440个物理像素组成，构图自主",
            "打印机原生打印分辨率300DPI，构图自主",
            "相机拍摄分辨率6000×4000像素，构图自主",
        )
        original = "商品居中完整呈现，轮廓清楚，右侧保留低细节短文案安全区，关键结构避开裁切边界"
        for layout in layouts:
            with self.subTest(layout=layout):
                frame = make_frame(1, "主图-01").replace(original, layout)
                self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_explicit_rejection_of_reference_frame_inheritance_is_allowed(self) -> None:
        allowed_layouts = (
            "参考图宽高关系不作为输出画面约束；系统依据商品结构、首屏任务和裁切风险自主决定纵向动线与安全区",
            "不根据参考图比例生成成图，系统自主决定构图与留白",
            "输出宽高比不取自参考图，系统自主决定构图与留白",
            "成图不保持与参考图相同的宽高比，系统自主决定构图与留白",
            "根据参考图中已确认的商品结构自主决定构图与留白",
            "匹配参考图中的商品颜色并自主生成构图",
            "匹配参考图构图张力但不继承外框，输出比例自主决定",
            "不要让参考图外框决定成图，比例由系统自主选择",
            "参考图显示包装3:2结构，输出比例由系统决定",
            "参考图中瓶身呈三比一，系统自主定画幅",
        )

        for layout in allowed_layouts:
            with self.subTest(layout=layout):
                frame = make_frame(1, "主图-01").replace(
                    "商品居中完整呈现，轮廓清楚，右侧保留低细节短文案安全区，关键结构避开裁切边界",
                    layout,
                )
                self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_fresh_adversarial_layout_constraints_are_rejected(self) -> None:
        """固化三路全新上下文审计发现的漏拦表达。"""

        cases = (
            # 独立画布模糊测试
            ("layout", "把画布宽度与高度固定为四分之三。"),
            ("prompt", "输出方向明确规定为纵版。"),
            ("layout", "最终画布固定横置。"),
            ("prompt", "交付文件只能是1080x1440像素。"),
            ("prompt", "交付图宽一千五百像素且高二千像素。"),
            ("prompt", "最终文件尺寸只允许720乘1280像素。"),
            ("layout", "商品必须占据画面百分之七十。"),
            ("prompt", "主体面积固定覆盖画布百分之六十五。"),
            ("layout", "杯体必须覆盖成图的三分之二。"),
            ("layout", "主商品高度锁定为画面高度的四分之三。"),
            ("prompt", "主体覆盖率不得低于百分之七十五。"),
            ("layout", "商品占比规定在百分之六十至百分之六十五。"),
            ("prompt", "核心对象必须铺满九成画面。"),
            ("layout", "杯身在画布中的面积固定为百分之五十五。"),
            ("prompt", "产品轮廓必须占整个画框约百分之七十。"),
            ("prompt", "商品横向跨度恒定占画宽的五分之四。"),
            ("layout", "主物体只能占画布一半。"),
            ("prompt", "成品中杯子必须覆盖百分之八十二的像素区域。"),
            ("prompt", "不得改变参考照片的横竖比例。"),
            # 独立语义审计
            ("layout", "并非不采用1:1的画面比例"),
            ("layout", "不是不需要1:1的输出比例"),
            ("layout", "参考图展示完整商品！画布继承其外框"),
            ("layout", "参考图展示完整商品。画幅不沿用其比例，但当前恢复采用"),
            ("layout", "参考图展示完整商品。画幅并非不按其比例生成"),
            ("layout", "参考图展示完整商品。背景使用柔和光。画幅沿用比例"),
            ("layout", "参考图展示完整商品。先清理背景。输出宽高关系照旧"),
            ("layout", "参考图展示完整商品。保留真实颜色。画框继承比例"),
            ("layout", "参考图展示完整商品。构图简洁。版式与之相同"),
            ("layout", "参考图展示完整商品。构图简洁。画布按前者比例"),
            ("layout", "本次商品图比例为1:1"),
            ("layout", "本次产品图宽高比为4:5"),
            ("layout", "本次包装展示图比例为3:4"),
            ("layout", "本次商品展示图尺寸为1200×1600像素"),
            ("layout", "设备原生分辨率1920×1080，当前输出沿用该分辨率"),
            ("layout", "设备原生分辨率1920×1080，但当前图片固定为同尺寸"),
            # 独立发布门禁
            ("layout", "最终成像比例设成1.25，右侧留白"),
            ("layout", "页面纵横比限定在0.72，主体居中"),
            ("layout", "横边需比纵边少25%"),
            ("layout", "画框宽高按2份配3份"),
            ("layout", "输出采用正方画框并居中展示商品"),
            ("layout", "最终成像固定宽屏"),
            ("layout", "画面限定为纵版"),
            ("layout", "只允许横向长图"),
            ("layout", "主图方向不可改，保持纵屏"),
            ("layout", "成片外轮廓要比高度宽"),
            ("layout", "商品主体吞掉成图面积的65%"),
            ("layout", "产品必须覆盖版面的五分之四"),
            ("layout", "核心商品高度限定为整张图纵边的70%"),
            ("layout", "安全留空区固定为22%"),
            ("layout", "文案空区必须保留三成"),
            ("layout", "主体与留白各占一半"),
            ("layout", "商品区覆盖总版面的2/3"),
            ("layout", "最终图片照搬上传素材的边长关系"),
            ("layout", "输出横纵比例与底稿同步"),
            ("layout", "参考照片的外框直接决定最终画面"),
            ("layout", "使用来图原有方向排出成片"),
            ("layout", "底稿多宽多高，成品就多宽多高"),
            ("layout", "原始影像的边界形态作为输出模板"),
            ("layout", "沿用样板的画幅制作"),
            ("layout", "复制参考视觉裁切框"),
            ("layout", "维持源照片的横纵方向"),
            ("prompt", "输出比例默认0.9"),
            # 主线程边界审计
            ("layout", "留白与主体之比4:1"),
            ("layout", "文案区与商品区之比1:2"),
            ("layout", "当前构图固定为4:5，后期A4规格不约束当前构图"),
            # 独立复测与 README 派生变形
            ("layout", "参考图展示完整商品。方向照旧"),
            ("prompt", "把原图九比十六比例带入成图。"),
            ("layout", "售卖主体在成图内所占区域不得少于七成半。"),
            ("layout", "产品可见轮廓固定覆盖版心的零点六八。"),
            ("layout", "文案留空与商品区域按一份对三份分配。"),
            ("layout", "生成结果中杯体宽度一律达到画面宽边的百分之八十五。"),
            ("layout", "来图是几比几，最终图片就照着同样关系排。"),
            ("layout", "输入素材的长短边关系直接用作本张外框。"),
            ("layout", "输入照片横则输出横，输入照片竖则输出竖。"),
        )
        original_layout = "商品居中完整呈现，轮廓清楚，右侧保留低细节短文案安全区，关键结构避开裁切边界"
        original_prompt_usage = "本张实际向生成模型提供全部同款参考图，按目标SKU/状态筛选商品身份、正面几何和共同特征，其他SKU不作为生成参考输入，同款资料一致，无需裁决"

        for field, phrase in cases:
            with self.subTest(field=field, phrase=phrase):
                frame = make_frame(1, "主图-01")
                if field == "layout":
                    frame = frame.replace(original_layout, phrase)
                else:
                    frame = frame.replace(
                        original_prompt_usage,
                        f"{phrase}；{original_prompt_usage}",
                    )
                with self.assertRaisesRegex(StoryboardValidationError, "固定画幅"):
                    validate_storyboard(make_storyboard([frame]))

    def test_fresh_adversarial_nonbinding_and_product_facts_are_allowed(self) -> None:
        """固化三路全新上下文审计发现的误杀表达。"""

        cases = (
            # 独立画布模糊测试
            ("layout", "无需沿用参考图的横版外框。"),
            ("layout", "不预设一千二百乘一千五百像素输出。"),
            ("layout", "禁止用主体占画面百分之六十五替代识别判断。"),
            ("camera", "全画幅传感器物理尺寸为三十六乘二十四毫米。"),
            ("camera", "像素位移模式采集一万二千乘八千的源文件。"),
            ("camera", "相机裁切模式记录三千八百四十乘二千五百六十像素。"),
            # 独立语义审计
            ("layout", "画面比例固定为1:1的方案已取消"),
            ("layout", "画面比例固定为1:1并非当前要求"),
            ("layout", "此前采用4:5的输出比例，现已弃用"),
            ("layout", "画面比例固定为1:1，现已取消"),
            ("layout", "原计划画面比例为1:1，但已改为自主构图"),
            ("layout", "画面比例1:1只是被否决的旧方案"),
            ("layout", "画面比例1:1仅用于说明被取消的方案"),
            ("layout", "原先固定4:5的画面比例，方案已经废弃"),
            ("layout", "原先固定4:5的画面比例，旧方案作废"),
            ("layout", "按参考图比例出图的约束已排除"),
            ("production", "生产要求竖版，不决定当前构图"),
            ("production", "后期交付规格为横版，不约束当前构图"),
            ("production", "平台交付适配为方图，不限制当前画幅"),
            ("production", "1:1用于平台交付，当前构图不受影响"),
            ("production", "1:1是交付端裁切规格，与本次构图无关"),
            ("production", "后期会裁成1:1，生成阶段不锁画幅"),
            ("production", "平台交付需要1080×1080像素，构图阶段自由"),
            ("production", "仅在导出时适配4:5，当前生成保持自适应"),
            ("layout", "参考图展示完整商品。画幅沿用其比例的方案已取消"),
            ("layout", "参考图自身比例为1:2，但输出画幅不跟随"),
            ("camera", "相机支持输出6000×4000像素"),
            ("production", "显示器交付为横版，仅用于后期且不决定当前构图"),
            ("camera", "相机支持输出6000×4000像素，但当前画面由系统自主决定"),
            # 独立发布门禁
            ("camera", "扫描仪支持600dpi，画面由系统安排"),
            ("camera", "使用1/3俯视角展示顶部结构"),
            ("camera", "采用2/3侧后方机位但不展示未知结构"),
            ("layout", "参考图显示商品是横向挂画，输出方向由AI决定"),
            ("layout", "桌面展开后长为宽的1.8倍，画面由系统自主安排"),
            ("layout", "参考照片记录的是3:2输入外框，输出不会沿用它"),
            # 独立复测与 README 派生变形
            ("prompt", "不得把四比五当作成图硬约束。"),
            ("prompt", "画布尺寸不设为九百乘一千二百像素。"),
            ("prompt", "画面方向由使用场景和信息动线共同决定。"),
            ("prompt", "不要求最终画面维持一比一，系统根据裁切风险决定空间。"),
            ("prompt", "原始素材采用方形边框，当前画面仍按信息层级自主组织。"),
            ("layout", "产品图案宽高为5:7，画布按内容自适应。"),
            ("layout", "不限定画面为正方形输出。"),
            ("layout", "五比七并不是本张成图约束，外框按信息层级另行组织。"),
            ("layout", "参考照片自身是三比二，仅用于识别杯体，输出外框重新决定。"),
        )
        original_layout = "商品居中完整呈现，轮廓清楚，右侧保留低细节短文案安全区，关键结构避开裁切边界"
        original_camera = "平视中景，自然透视，焦点落在商品正面"
        original_production = "模型生成背景与光影，真实商品层和文字由后期复核"
        original_prompt_usage = "本张实际向生成模型提供全部同款参考图，按目标SKU/状态筛选商品身份、正面几何和共同特征，其他SKU不作为生成参考输入，同款资料一致，无需裁决"
        for field, phrase in cases:
            with self.subTest(field=field, phrase=phrase):
                frame = make_frame(1, "主图-01")
                if field == "layout":
                    frame = frame.replace(original_layout, f"{original_layout}；{phrase}")
                elif field == "camera":
                    frame = frame.replace(original_camera, f"{original_camera}；{phrase}")
                elif field == "prompt":
                    frame = frame.replace(
                        original_prompt_usage,
                        f"{original_prompt_usage}；{phrase}",
                    )
                else:
                    frame = frame.replace(original_production, phrase)
                self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_valid_fixture(self) -> None:
        result = validate_storyboard(FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(result, ["主图-01"])

    def test_readme_final_storyboard_example_is_valid(self) -> None:
        readme_path = ROOT.parent / "README.md"
        if not readme_path.exists():
            self.skipTest("独立安装目录不包含仓库 README")
        readme = readme_path.read_text(encoding="utf-8")
        match = re.search(
            r"## 最终分镜提示词示例.*?(?P<storyboard>````markdown\n.*?\n````)",
            readme,
            re.DOTALL,
        )
        self.assertIsNotNone(match, "README 缺少最终分镜提示词示例")
        self.assertEqual(validate_storyboard(match.group("storyboard")), ["主图-01"])

    def test_multiple_frames_can_choose_different_reference_usage(self) -> None:
        markdown = make_storyboard(
            [
                make_frame(1, "主图-01", "已分析全部有效参考视觉；本张实际只使用当前最清晰的一张正面参考图提取商品身份与几何"),
                make_frame(
                    2,
                    "主图-02",
                    "已分析全部参考视觉；本张实际向生成模型提供多张同款参考图，按目标SKU/状态筛选结构、颜色和局部细节，确认内容属于同一目标SKU，同款资料一致，无需裁决",
                ),
            ],
        )
        self.assertEqual(validate_storyboard(markdown), ["主图-01", "主图-02"])

    def test_multi_reference_same_sku_usage_is_valid(self) -> None:
        frame = make_frame(
            1,
            "主图-01",
            "已分析全部参考视觉；本张实际向生成模型提供多张同款参考图，按目标SKU/状态筛选身份、结构和颜色，确认内容属于同一目标SKU，同款资料一致，无需裁决",
            "本张实际向生成模型提供多张同款参考图，按目标SKU/状态筛选商品身份、结构和颜色，确认内容属于同一目标SKU，同款资料一致，无需裁决",
        )
        self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_explicit_reference_conflict_adoption_and_rejection_is_valid(self) -> None:
        usage = (
            "已分析全部参考视觉；本张实际向生成模型提供多张同款参考图，按目标SKU筛选商品身份、结构和颜色，"
            "其他SKU不作为生成参考输入；同款资料存在颜色冲突，最终采用清晰正面资料中的深蓝杯身，舍弃偏色照片中的青色外观"
        )
        frame = make_frame(1, "主图-01", usage, usage)
        self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_all_reference_multi_sku_usage_is_valid(self) -> None:
        frame = make_frame(
            1,
            "主图-01",
            "已分析全部参考视觉；本张实际向生成模型提供全部可用参考图，按各SKU分别筛选身份、结构与颜色，各SKU使用独立商品层后期合成，同款资料一致，无需裁决",
            "本张实际向生成模型提供全部可用参考图，按各SKU分别筛选商品身份、结构与颜色，各SKU分别使用独立商品层后期合成，同款资料一致，无需裁决",
        )
        self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_all_reference_scope_accepts_natural_modifiers(self) -> None:
        terms = ("全部用户提供的权益页面截图", "全部真实界面截图")
        for term in terms:
            with self.subTest(term=term):
                usage = (
                    f"已分析{term}；本张实际向生成模型提供{term}，按目标版本筛选真实界面、权益和交付流程，"
                    "同一版本内互补，同款资料一致，无需裁决"
                )
                frame = make_frame(1, "主图-01", usage, usage)
                self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_multi_reference_field_requires_target_sku_filter(self) -> None:
        frame = make_frame(
            1,
            "主图-01",
            "已分析全部参考视觉；本张实际向生成模型提供全部参考图提取商品身份、结构与颜色，其他SKU不作为生成参考输入，同款资料一致，无需裁决",
            "已分析全部参考视觉；本张实际向生成模型提供全部同款参考图，按目标SKU/状态筛选商品身份、结构与颜色，其他SKU不作为生成参考输入，同款资料一致，无需裁决",
        )
        with self.assertRaises(StoryboardValidationError):
            validate_storyboard(make_storyboard([frame]))

    def test_multi_reference_prompt_requires_target_sku_filter(self) -> None:
        frame = make_frame(
            1,
            "主图-01",
            "本张实际向生成模型提供全部同款参考图，按目标SKU/状态筛选商品身份、结构与颜色，其他SKU不作为生成参考输入，同款资料一致，无需裁决",
            "本张实际向生成模型提供全部参考图提取商品身份、结构与颜色，其他SKU不作为生成参考输入，同款资料一致，无需裁决",
        )
        with self.assertRaises(StoryboardValidationError):
            validate_storyboard(make_storyboard([frame]))

    def test_multi_reference_field_requires_conflict_resolution(self) -> None:
        frame = make_frame(
            1,
            "主图-01",
            "已分析全部参考视觉；本张实际向生成模型提供全部同款参考图，按目标SKU/状态筛选商品身份、结构与颜色，其他SKU不作为生成参考输入，同款资料存在颜色冲突且尚未解决",
            "已分析全部参考视觉；本张实际向生成模型提供全部同款参考图，按目标SKU/状态筛选商品身份、结构与颜色，其他SKU不作为生成参考输入，同款资料一致，无需裁决",
        )
        with self.assertRaises(StoryboardValidationError):
            validate_storyboard(make_storyboard([frame]))

    def test_multi_reference_input_requires_a_positive_resolution(self) -> None:
        usage = (
            "已分析全部有效参考视觉；本张实际向生成模型提供多张同款参考图，"
            "按目标SKU筛选商品身份、结构与颜色，其他SKU不作为生成参考输入"
        )
        frame = make_frame(1, "主图-01", usage, usage)
        with self.assertRaises(StoryboardValidationError):
            validate_storyboard(make_storyboard([frame]))

    def test_multi_reference_prompt_requires_conflict_resolution(self) -> None:
        frame = make_frame(
            1,
            "主图-01",
            "本张实际向生成模型提供全部同款参考图，按目标SKU/状态筛选商品身份、结构与颜色，其他SKU不作为生成参考输入，同款资料一致，无需裁决",
            "本张实际向生成模型提供全部同款参考图，按目标SKU/状态筛选商品身份、结构与颜色，其他SKU不作为生成参考输入，同款资料存在颜色冲突且尚未解决",
        )
        with self.assertRaises(StoryboardValidationError):
            validate_storyboard(make_storyboard([frame]))

    def test_reference_usage_mode_must_match_prompt(self) -> None:
        frame = make_frame(
            1,
            "主图-01",
            "已分析全部有效参考视觉；本张实际只使用当前最清晰的一张正面参考图，锁定商品身份与正面几何",
            "本张实际向生成模型提供全部同款参考图，按目标SKU筛选商品身份、几何、颜色和细节，其他SKU不作为生成参考输入，同款资料一致，无需裁决",
        )
        with self.assertRaises(StoryboardValidationError):
            validate_storyboard(make_storyboard([frame]))

    def test_conflicting_later_generation_scope_is_rejected(self) -> None:
        usages = (
            "已分析全部有效参考视觉；本张实际向生成模型提供全部同款参考图，按目标SKU筛选商品身份和结构；"
            "但本张实际只使用一张参考图",
            "已分析全部有效参考视觉；本张实际向生成模型提供多张同款参考图，按目标SKU筛选商品身份和结构；"
            "但本张实际不输入任何参考图",
        )
        for usage in usages:
            with self.subTest(usage=usage):
                frame = make_frame(1, "主图-01", usage, usage)
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(make_storyboard([frame]))

    def test_reference_usage_must_describe_scope_and_purpose(self) -> None:
        frame = make_frame(1, "主图-01", "使用参考图", "使用参考图")
        with self.assertRaises(StoryboardValidationError):
            validate_storyboard(make_storyboard([frame]))

    def test_reference_field_must_state_all_visuals_were_analyzed(self) -> None:
        frame = make_frame(
            1,
            "主图-01",
            "本张实际只使用一张最清晰参考图提取商品身份和正面几何",
            "本张实际只使用一张最清晰参考图提取商品身份和正面几何",
        )
        with self.assertRaises(StoryboardValidationError):
            validate_storyboard(make_storyboard([frame]))

    def test_negated_global_analysis_claim_is_rejected_even_with_modifiers(self) -> None:
        claims = (
            "未完整分析全部有效参考视觉",
            "没有真正分析全部有效参考视觉",
            "无需分析全部有效参考视觉",
        )
        for claim in claims:
            with self.subTest(claim=claim):
                frame = make_frame(
                    1,
                    "主图-01",
                    f"{claim}；本张实际只使用一张最清晰参考图提取商品身份和正面几何",
                    f"{claim}；本张实际只使用一张最清晰参考图提取商品身份和正面几何",
                )
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(make_storyboard([frame]))

    def test_postposed_partial_analysis_claim_is_rejected(self) -> None:
        usage = (
            "已分析全部有效参考视觉，但仅看了一部分；"
            "本张实际只使用一张同款商品图，提取商品身份和正面结构"
        )
        frame = make_frame(1, "主图-01", usage, usage)
        with self.assertRaises(StoryboardValidationError):
            validate_storyboard(make_storyboard([frame]))

    def test_natural_incomplete_global_analysis_claims_are_rejected(self) -> None:
        incomplete_claims = (
            "但还有一张没看",
            "但還有部分未查看",
            "但除了最后一张以外都看过",
            "但实际漏掉了侧视图",
            "但分析完成度九成",
            "但剩余一张待查看",
            "但只是尚有遗漏",
            "但僅查看部分",
        )
        for incomplete_claim in incomplete_claims:
            with self.subTest(incomplete_claim=incomplete_claim):
                usage = (
                    f"已分析全部有效参考视觉，{incomplete_claim}；"
                    "本张实际只使用一张同款商品图，提取商品身份和正面结构"
                )
                frame = make_frame(1, "主图-01", usage, usage)
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(make_storyboard([frame]))

    def test_explicit_complete_analysis_without_omissions_is_valid(self) -> None:
        complete_claims = (
            "已分析全部有效参考视觉，没有遗漏",
            "已分析全部有效参考视觉，并避免漏掉任何参考视觉",
        )
        for complete_claim in complete_claims:
            with self.subTest(complete_claim=complete_claim):
                usage = (
                    f"{complete_claim}；"
                    "本张实际只使用一张同款商品图，提取商品身份和正面结构"
                )
                frame = make_frame(1, "主图-01", usage, usage)
                self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_resolved_reference_claim_must_not_be_negated_or_unresolved(self) -> None:
        claims = (
            "同款资料未保持一致",
            "同款资料没有保持一致",
            "同款资料尚未确认一致",
            "同款资料无法确认是否一致",
        )
        for claim in claims:
            with self.subTest(claim=claim):
                frame = make_frame(
                    1,
                    "主图-01",
                    f"已分析全部有效参考视觉；本张实际向生成模型提供全部同款参考图，按目标SKU筛选商品身份、结构和颜色，其他SKU不作为生成参考输入，{claim}",
                    f"已分析全部有效参考视觉；本张实际向生成模型提供全部同款参考图，按目标SKU筛选商品身份、结构和颜色，其他SKU不作为生成参考输入，{claim}",
                )
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(make_storyboard([frame]))

    def test_reference_material_without_a_conclusion_is_rejected(self) -> None:
        usage = (
            "已分析全部有效参考视觉；本张实际向生成模型提供多张同款商品图，"
            "综合商品身份和结构，同款资料暂不能下结论"
        )
        frame = make_frame(1, "主图-01", usage, usage)
        with self.assertRaises(StoryboardValidationError):
            validate_storyboard(make_storyboard([frame]))

    def test_natural_unresolved_reference_conclusions_are_rejected(self) -> None:
        unresolved_claims = (
            "同款资料尚无定论",
            "同款资料待客户拍板",
            "同款资料不能确认",
            "同款资料未达成共识",
            "同款资料真假难辨",
            "同款资料需后续再议",
            "同款资料仍需确认后再定",
            "同款资料需要後續再議",
            "同款资料但無法確認",
        )
        for unresolved_claim in unresolved_claims:
            with self.subTest(unresolved_claim=unresolved_claim):
                usage = (
                    "已分析全部有效参考视觉；本张实际向生成模型提供多张同款商品图，"
                    f"综合商品身份和结构，{unresolved_claim}"
                )
                frame = make_frame(1, "主图-01", usage, usage)
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(make_storyboard([frame]))

    def test_unresolved_same_variant_wording_is_rejected(self) -> None:
        unresolved_claims = (
            "尚未确认是否同款",
            "是否同款尚未确定",
            "需要后续再议",
            "不能确认",
        )
        for unresolved_claim in unresolved_claims:
            with self.subTest(unresolved_claim=unresolved_claim):
                usage = (
                    "已分析全部有效参考视觉；本张实际向生成模型提供多张同款商品图，"
                    f"综合商品身份和结构，{unresolved_claim}"
                )
                frame = make_frame(1, "主图-01", usage, usage)
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(make_storyboard([frame]))

    def test_unknown_detail_can_be_explicitly_excluded_from_multi_reference_input(self) -> None:
        usage = (
            "已分析全部有效参考视觉；本张实际向生成模型提供多张同款参考图，"
            "按目标SKU筛选商品身份和外观结构，其他SKU不作为生成参考输入，"
            "参考资料不能确认包装小字，因此本张不呈现该文字"
        )
        frame = make_frame(1, "主图-01", usage, usage)
        self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_explicit_prohibitions_are_not_mistaken_for_unresolved_status(self) -> None:
        usages = (
            "已分析全部有效参考视觉；本张实际向生成模型提供多张同款参考图，"
            "按目标SKU筛选商品身份和结构，其他SKU不作为生成参考输入，同款资料一致，无需裁决；不能补画未知背面",
            "已分析全部有效参考视觉；本张实际向生成模型提供多张同款参考图，"
            "按目标SKU筛选商品身份和结构，其他SKU不作为生成参考输入，同款资料一致，无需裁决；不能改变商品结构",
            "已分析全部有效参考视觉；本张实际向生成模型提供多张同款参考图，"
            "按目标SKU筛选商品身份和结构，其他SKU不作为生成参考输入，同款资料一致，无需裁决；不能推断隐藏结构",
            "已分析全部有效参考视觉；本张实际向生成模型提供多张同款参考图，"
            "按目标SKU筛选商品身份和结构，其他SKU不作为生成参考输入，同款资料一致，无需裁决；不能虚构未知背面",
        )
        for usage in usages:
            with self.subTest(usage=usage):
                frame = make_frame(1, "主图-01", usage, usage)
                self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_natural_prohibitions_with_model_inference_are_not_pending_status(self) -> None:
        safe_phrases = (
            "隐藏结构不能由模型推断",
            "不能作为生成参考输入",
            "不能由模型补画未知背面",
        )
        for phrase in safe_phrases:
            with self.subTest(phrase=phrase):
                usage = (
                    "已分析全部有效参考视觉；本张实际向生成模型提供多张同款参考图，"
                    "按目标SKU筛选商品身份和结构，其他SKU不作为生成参考输入，同款资料一致，无需裁决；"
                    f"{phrase}"
                )
                frame = make_frame(1, "主图-01", usage, usage)
                self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_marketing_model_and_internal_role_labels_are_rejected(self) -> None:
        labels = (
            "FABE模型",
            "AIDA阶段",
            "USP",
            "RTB证据",
            "买家红队",
            "增长循环",
            "心理模型",
        )
        base = (
            "本张实际向生成模型提供多张同款参考图，按目标SKU筛选商品身份、结构和颜色，"
            "同款资料一致，无需裁决"
        )
        for label in labels:
            with self.subTest(label=label):
                frame = make_frame(1, "主图-01", prompt_reference_usage=f"{base}；内部采用{label}")
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(make_storyboard([frame]))

    def test_marketing_term_inside_explicit_visible_original_is_allowed(self) -> None:
        base = (
            "已分析全部有效参考视觉；本张实际向生成模型提供多张同款参考图，按目标SKU筛选商品身份、结构和颜色，"
            "同款资料一致，无需裁决；逐字保留原文：“FOMO”"
        )
        frame = make_frame(1, "主图-01", reference_usage=base, prompt_reference_usage=base)
        self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_real_product_identifiers_named_like_marketing_models_are_allowed(self) -> None:
        base = (
            "已分析全部有效参考视觉；本张实际向生成模型提供一张同款参考图，按目标SKU筛选商品身份、结构和颜色，"
            "同款资料一致，无需裁决"
        )
        identity_phrases = (
            "商品锁定：AIDA品牌蓝牙耳机，型号AIDA Pro，保持可见原文",
            "商品锁定：FAST品牌扫地机，型号FAST-200，保持可见原文",
            "商品锁定：FOMO系列收纳盒，型号FOMO-1，保持可见原文",
            "商品锁定：品牌为USP，款号RTB，保持可见原文",
            "商品锁定：产品名称为AIPL旅行杯，版本FAST，保持可见原文",
            "商品锁定：COM-B品牌传感器，型号COM-B 200，保持可见原文",
            "认证：LCA，保持证据原文",
            "可见文字：Goodhart，保持证据原文",
        )
        for phrase in identity_phrases:
            with self.subTest(phrase=phrase):
                usage = f"{base}；{phrase}"
                frame = make_frame(1, "主图-01", reference_usage=usage, prompt_reference_usage=usage)
                self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_expanded_marketing_model_labels_are_rejected(self) -> None:
        labels = (
            "ELM模型",
            "4U框架",
            "CAGE模型",
            "KOC策略",
            "消费决策心理学",
            "内容循环",
            "六顶思考帽",
            "Growth Loop",
            "Hook-Proof-Close",
            "双钻",
            "Goodhart定律",
        )
        base = (
            "本张实际向生成模型提供全部同款参考图，按目标SKU筛选商品身份、结构和颜色，"
            "同款资料一致，无需裁决"
        )
        for label in labels:
            with self.subTest(label=label):
                frame = make_frame(1, "主图-01", prompt_reference_usage=f"{base}；内部采用{label}")
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(make_storyboard([frame]))

        disguised = f"{base}；商品锁定：保持商品真实，采用AIDA模型组织画面"
        frame = make_frame(1, "主图-01", reference_usage=disguised, prompt_reference_usage=disguised)
        with self.assertRaises(StoryboardValidationError):
            validate_storyboard(make_storyboard([frame]))

    def test_marketing_aliases_traditional_text_and_split_acronyms_are_rejected(self) -> None:
        labels = (
            "4A模型",
            "O5A模型",
            "福格行为模型",
            "STDC模型",
            "NSM模型",
            "5Why模型",
            "古德哈特定律",
            "OST模型",
            "Stage Gate模型",
            "營銷模型",
            "心理紅隊",
            "F.A.B.E模型",
            "F/A/B/E模型",
            "A I D A阶段",
            "增長循環",
            "框架效应",
        )
        base = (
            "本张实际向生成模型提供全部同款参考图，按目标SKU筛选商品身份、结构和颜色，"
            "同款资料一致，无需裁决"
        )
        for label in labels:
            with self.subTest(label=label):
                frame = make_frame(1, "主图-01", prompt_reference_usage=f"{base}；内部采用{label}")
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(make_storyboard([frame]))

    def test_internal_marketing_context_overrides_identity_like_suffixes(self) -> None:
        internal_phrases = (
            "内部采用AIDA品牌框架组织画面",
            "内部采用FOMO系列策略强化紧迫感",
            "内部采用FAST-200模型推演画面",
        )
        base = (
            "本张实际向生成模型提供全部同款参考图，按目标SKU筛选商品身份、结构和颜色，"
            "同款资料一致，无需裁决"
        )
        for phrase in internal_phrases:
            with self.subTest(phrase=phrase):
                frame = make_frame(1, "主图-01", prompt_reference_usage=f"{base}；{phrase}")
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(make_storyboard([frame]))

    def test_explicit_internal_model_is_rejected_after_field_punctuation(self) -> None:
        task_values = (
            "【内部采用需求张力模型组织画面】",
            "内部调用产品机会模型组织画面",
            "【设计时内部采用需求张力模型组织画面】",
            "【内部运用产品机会模型组织画面】",
            "【内部套用需求张力模型组织画面】",
            "【内部借助产品机会框架安排内容】",
            "【内部按需求张力模型分析卖点】",
            "【内部采纳购买阻力阶梯模型】",
            "【内部援引信任增益曲线模型】",
            "【幕后以需求热度分层理论】",
            "【内部参照场景触发链方法安排构图】",
            "【内部依托犹豫消解路径模型】",
            "【内部借鉴品类进入门槛矩阵】",
            "【后台采用首购阻力曲线模型】",
            "【幕后调用复购触发器模型】",
            "【内部将客群犹豫指数作为模型】",
            "【设计师内部采纳证据密度曲线模型】",
            "【幕后依据价格接受坡度框架】",
            "【制作阶段内部引用兴趣升温理论】",
            "【内部采纳购买动因叠加模型】",
            "【幕后运用信任斜坡框架】",
            "【制作阶段内部援引决策阻尼理论】",
        )
        for task_value in task_values:
            with self.subTest(task_value=task_value):
                frame = make_frame(1, "主图-01").replace(
                    "- 成图任务：【清楚建立商品识别】",
                    f"- 成图任务：{task_value}",
                )
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(make_storyboard([frame]))

    def test_internal_reasoning_record_labels_are_rejected(self) -> None:
        task_values = (
            "内部思考：先判断买家疑虑，再决定画面顺序",
            "我的推理：先判断买家疑虑，再决定画面顺序",
            "分析过程：先判断买家疑虑，再决定画面顺序",
            "后台推演：先判断买家疑虑，再决定画面顺序",
            "仅供内部：先判断买家疑虑，再决定画面顺序",
            "内部思考先判断买家疑虑，再决定画面顺序",
            "我的推理如下：先判断买家疑虑，再决定画面顺序",
            "后台分析先判断买家疑虑，再决定画面顺序",
            "仅供内部使用，先判断买家疑虑，再决定画面顺序",
            "内部判断记录",
            "供内部参考的思考",
            "决策依据记录",
            "草稿推理",
            "幕后分析笔记",
            "内部分析备忘",
            "推导笔记",
            "思路草稿",
            "取舍记录",
            "内部结论记录",
            "布局选择理由",
            "设计决策过程",
            "仅供团队查看",
            "不对外展示的分析",
            "模型思考摘要",
            "内部演算",
            "内部自检思路",
            "创作推理备忘",
        )
        for task_value in task_values:
            with self.subTest(task_value=task_value):
                frame = make_frame(1, "主图-01").replace(
                    "- 成图任务：【清楚建立商品识别】",
                    f"- 成图任务：【{task_value}】",
                )
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(make_storyboard([frame]))

    def test_long_english_product_names_are_allowed_in_identity_fields(self) -> None:
        product_names = (
            "Microsoft Surface Laptop Studio 2",
            "Apple Studio Display",
            "Samsung The Freestyle 2nd Gen",
            "Bose QuietComfort Ultra Headphones",
        )
        for product_name in product_names:
            with self.subTest(product_name=product_name):
                frame = make_frame(1, "主图-01").replace(
                    "- 商品锁定：【保持轮廓、结构、比例、颜色与可见原文】",
                    f"- 商品锁定：【商品名称：{product_name}】",
                )
                self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_real_product_name_containing_a_model_term_is_allowed(self) -> None:
        frame = make_frame(1, "主图-01").replace(
            "- 商品锁定：【保持轮廓、结构、比例、颜色与可见原文】",
            "- 商品锁定：【商品名称：波特五力模型教具，型号PF-5】",
        )
        self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_real_product_identity_contexts_are_allowed_across_storyboard_fields(self) -> None:
        identity_phrases = (
            "锁定AIDA Pro蓝牙耳机的真实轮廓",
            "目标商品为AIDA Pro蓝牙耳机",
            "保持AIDA-X1蓝牙耳机外观",
            "将AIDA Pro蓝牙耳机置于台面中央",
            "保持FACT+S设备外观",
        )
        for phrase in identity_phrases:
            with self.subTest(phrase=phrase):
                frame = make_frame(1, "主图-01")
                frame = frame.replace(
                    "- 商品锁定：【保持轮廓、结构、比例、颜色与可见原文】",
                    f"- 商品锁定：【{phrase}，保持结构、比例、颜色与可见原文】",
                )
                frame = frame.replace(
                    "- 最终画面：【单个商品稳定放置并成为唯一焦点】",
                    f"- 最终画面：【{phrase}，单个商品稳定放置并成为唯一焦点】",
                )
                frame = frame.replace(
                    "完整保持商品轮廓、结构、比例、颜色和可见原文",
                    f"{phrase}，完整保持商品轮廓、结构、比例、颜色和可见原文",
                )
                self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_real_product_action_contexts_named_like_models_are_allowed(self) -> None:
        action_phrases = (
            "画面清楚展示AIDA Pro蓝牙耳机",
            "画面清楚展示FAST-200扫地机",
            "画面清楚展示PAS传感器与线束接口",
            "启用RACE模式，仪表界面保留真实文字",
        )
        for phrase in action_phrases:
            with self.subTest(phrase=phrase):
                frame = make_frame(1, "主图-01")
                frame = frame.replace(
                    "- 最终画面：【单个商品稳定放置并成为唯一焦点】",
                    f"- 最终画面：【{phrase}，单个商品稳定放置并成为唯一焦点】",
                )
                frame = frame.replace(
                    "完整保持商品轮廓、结构、比例、颜色和可见原文",
                    f"{phrase}，完整保持商品轮廓、结构、比例、颜色和可见原文",
                )
                self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_numbered_product_identifiers_are_allowed_in_layout_context(self) -> None:
        # 型号可能出现在布局或场景描述中，不能因为与营销缩写重名就误拒；
        # 但“FAST-200模型/策略”仍属于内部方法语境，由既有规则拦截。
        safe_phrases = (
            "FAST-200扫地机居中",
            "展示FAST-200蓝牙耳机作为视觉锚点",
            "呈现FAST-200蓝牙耳机作为主体",
            "保持FAST-200蓝牙耳机作为唯一焦点",
            "让FAST-200蓝牙耳机成为视觉中心",
            "使用FAST-200蓝牙耳机进行展示",
            "FAST-200蓝牙耳机作为主体居中",
            "FAST-200蓝牙耳机作为视觉锚点居中",
            "FAST-200传感器作为唯一焦点",
            "FAST–200扫地机居中",
            "RICE50电饭煲居中",
            "AIDA2025电饭煲作为唯一焦点",
            "GROW–200电饭煲成为视觉中心",
            "采用FAST-200扫地机作为主体居中",
            "运用FAST-200扫地机作为主体居中",
            "采用AIDA Pro蓝牙耳机作为唯一焦点",
            "参考FAST-200蓝牙耳机真实外观",
            "商品型号：AIDA-2025蓝牙耳机",
        )
        for phrase in safe_phrases:
            with self.subTest(phrase=phrase):
                frame = make_frame(1, "主图-01").replace(
                    "- 画布与布局：【商品居中完整呈现，轮廓清楚，右侧保留低细节短文案安全区，关键结构避开裁切边界】",
                    f"- 画布与布局：【{phrase}，商品保持清楚识别，右侧保留短文案安全区】",
                )
                self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

        unsafe = make_frame(1, "主图-01").replace(
            "- 画布与布局：【商品居中完整呈现，轮廓清楚，右侧保留低细节短文案安全区，关键结构避开裁切边界】",
            "- 画布与布局：【FAST-200模型组织画面，商品居中并保持清楚识别】",
        )
        with self.assertRaises(StoryboardValidationError):
            validate_storyboard(make_storyboard([unsafe]))

        unsafe_phrases = (
            "依据FOMO-2025蓝牙产品组织画面",
            "依据FOMO-2025蓝牙耳机组织画面",
            "依据AIDA Pro蓝牙耳机组织画面",
            "采用RACE-2024智能设备安排内容",
            "基于FOMO Pro收纳盒作为视觉锚点",
            "基于RACE-2025传感器作为视觉锚点",
            "使用AIDA-2025蓝牙耳机构建视觉",
            "参考AIDA-2025蓝牙耳机设计画面",
            "以AIDA-2025蓝牙产品展示画面",
            "FAST-200模型扫地机作为视觉锚点居中",
            "FOMO-2025策略产品作为主体居中",
            "AIDA-2025框架耳机作为唯一焦点",
            "AIPL-2025营销产品作为主体居中",
            "GROW-2025增长设备作为视觉锚点",
            "FOMO-2025心理产品成为视觉中心",
            "FAST-200扫地机策略作为主体",
            "FAST-200扫地机模型居中",
            "AIDA Pro蓝牙耳机框架作为唯一焦点",
            "采用FOMO2025强化紧迫感",
            "商品型号：X. 基于RACE-2025传感器作为视觉锚点",
            "RICE50模型电饭煲作为主体",
            "RICE50电饭煲策略作为唯一焦点",
            "AIDA2025电饭煲组织画面居中",
            "AIDA2025组织画面产品居中",
        )
        for phrase in unsafe_phrases:
            with self.subTest(phrase=phrase):
                candidate = make_frame(1, "主图-01").replace(
                    "- 画布与布局：【商品居中完整呈现，轮廓清楚，右侧保留低细节短文案安全区，关键结构避开裁切边界】",
                    f"- 画布与布局：【{phrase}，商品居中并保持清楚识别】",
                )
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(make_storyboard([candidate]))

    def test_printing_and_product_mode_terms_named_like_models_are_allowed(self) -> None:
        domain_phrases = (
            "采用4C印刷工艺还原包装色彩",
            "后期采用4C胶印工艺并复核色彩",
            "保留ICE冷饮模式的真实界面文字",
            "显示ICE模式的可见界面文字",
        )
        for phrase in domain_phrases:
            with self.subTest(phrase=phrase):
                frame = make_frame(1, "主图-01")
                frame = frame.replace(
                    "- 商品锁定：【保持轮廓、结构、比例、颜色与可见原文】",
                    f"- 商品锁定：【{phrase}，保持轮廓、结构、比例、颜色与可见原文】",
                )
                frame = frame.replace(
                    "完整保持商品轮廓、结构、比例、颜色和可见原文",
                    f"{phrase}，完整保持商品轮廓、结构、比例、颜色和可见原文",
                )
                self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_additional_documented_model_names_are_rejected(self) -> None:
        labels = (
            "禀赋效应",
            "现状偏误",
            "心理账户",
            "叙事传输",
            "格式塔原则",
            "Persona用户画像",
            "Cohort分析",
            "选品五力",
            "货盘金字塔",
            "价格带",
            "模块化资产策略",
            "品牌原型",
            "DTC模型",
            "漏斗组织画面",
            "消费者采用路径",
            "首屏截停",
            "痛点递进",
            "竞品差异化",
            "感官转译",
            "场景穿透",
            "合规信任",
            "价值解释",
            "情绪溢价",
            "行动促进",
            "顾虑兜底",
            "首因效应",
            "近因效应",
            "序位效应",
            "冯·雷斯托夫效应",
            "互惠原则",
            "认知失调",
            "默认效应",
            "支付痛苦",
            "目标梯度",
            "心理距离",
            "解释水平",
            "信任状组合",
            "电商全链路",
            "消费仪式",
            "Campaign Brief",
            "Creative Brief",
            "Message Hierarchy",
            "Content Architecture",
            "隐喻思维",
            "互惠",
            "非目标人群",
            "不适用场景",
            "内容场",
            "关系链",
            "品牌人格",
            "支付意愿",
            "相似人群",
            "品牌资产",
            "AI代理购物",
            "Gap Selling",
            "留存阶段",
            "COM-B模型",
            "EAST框架",
            "RATER模型",
            "FMEA模型",
            "ZMOT模型",
            "PESTEL模型",
            "MoSCoW方法",
            "认知负荷理论",
            "双系统理论",
            "信息觅食",
            "信息气味",
            "信号理论",
            "服务蓝图",
            "可供性",
            "行为线索",
            "符号学",
            "视觉修辞",
            "图片任务转译框架族",
            "创意视觉技法族",
        )
        base = (
            "本张实际向生成模型提供全部同款参考图，按目标SKU筛选商品身份、结构和颜色，"
            "同款资料一致，无需裁决"
        )
        for label in labels:
            with self.subTest(label=label):
                frame = make_frame(1, "主图-01", prompt_reference_usage=f"{base}；内部采用{label}")
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(make_storyboard([frame]))

    def test_physical_funnel_product_is_not_mistaken_for_a_marketing_funnel(self) -> None:
        frame = make_frame(1, "主图-01")
        frame = frame.replace(
            "- 商品锁定：【保持轮廓、结构、比例、颜色与可见原文】",
            "- 商品锁定：【目标商品为不锈钢漏斗，保持轮廓、结构、比例、颜色与可见原文】",
        )
        frame = frame.replace(
            "完整保持商品轮廓、结构、比例、颜色和可见原文",
            "将不锈钢漏斗置于台面中央，完整保持商品轮廓、结构、比例、颜色和可见原文",
        )
        self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_explicit_internal_model_sentences_are_rejected_without_dictionary_entries(self) -> None:
        internal_sentences = (
            "内部采用波特五力模型组织画面",
            "内部采用稀缺与时效模型组织画面",
            "内部采用边际ROI模型组织画面",
            "内部采用因果推断模型组织画面",
            "内部采用价格弹性模型组织画面",
            "内部采用捆绑定价模型组织画面",
            "内部采用价值阶梯模型组织画面",
            "内部采用公域—私域—品牌域模型组织画面",
            "内部采用私域四阵地模型组织画面",
            "内部采用内容场中心场营销场模型组织画面",
            "内部采用关系链模型组织画面",
            "内部采用5W2H模型组织画面",
            "内部采用创新十类组织画面",
            "内部采用视觉独特资产组织画面",
        )
        base = (
            "本张实际向生成模型提供全部同款参考图，按目标SKU筛选商品身份、结构和颜色，"
            "同款资料一致，无需裁决"
        )
        for sentence in internal_sentences:
            with self.subTest(sentence=sentence):
                frame = make_frame(1, "主图-01", prompt_reference_usage=f"{base}；{sentence}")
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(make_storyboard([frame]))

    def test_real_product_internal_structure_language_is_allowed(self) -> None:
        product_facts = (
            "产品内部采用蜂窝支撑结构",
            "杯体内部采用漏斗形导流结构",
            "行李箱内部使用镁合金框架",
            "相机内部采用模块化框架",
            "包装内部采用矩阵式隔仓",
            "控制器内部使用环形矩阵灯板",
            "床垫内部采用弹簧矩阵",
        )
        for product_fact in product_facts:
            with self.subTest(product_fact=product_fact):
                frame = make_frame(1, "主图-01")
                frame = frame.replace(
                    "- 商品锁定：【保持轮廓、结构、比例、颜色与可见原文】",
                    f"- 商品锁定：【{product_fact}，保持轮廓、结构、比例、颜色与可见原文】",
                )
                frame = frame.replace(
                    "完整保持商品轮廓、结构、比例、颜色和可见原文",
                    f"{product_fact}，完整保持商品轮廓、结构、比例、颜色和可见原文",
                )
                self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_documented_model_names_are_rejected_without_an_internal_prefix(self) -> None:
        labels = (
            "波特五力模型",
            "稀缺与时效模型",
            "边际ROI模型",
            "因果推断模型",
            "价格弹性模型",
            "捆绑定价模型",
            "价值阶梯模型",
            "公域—私域—品牌域模型",
            "私域四阵地模型",
            "5W2H模型",
            "创新十类",
            "视觉独特资产",
        )
        base = (
            "本张实际向生成模型提供全部同款参考图，按目标SKU筛选商品身份、结构和颜色，"
            "同款资料一致，无需裁决"
        )
        for label in labels:
            with self.subTest(label=label):
                frame = make_frame(1, "主图-01", prompt_reference_usage=f"{base}；依据{label}组织画面")
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(make_storyboard([frame]))

    def test_general_unresolved_multi_reference_wording_is_rejected(self) -> None:
        unresolved_claims = (
            "资料不确定",
            "不知道是否同款",
            "同款尚不明确",
            "资料待确认",
            "需要用户判断",
            "还没有裁决",
            "暂不能得出结论",
            "暂无结论",
            "未完成核对",
            "需要后续再议",
            "不能确认",
            "资料拿不准",
            "同款关系不明",
            "尚待核实",
            "结论还没出来",
            "暂时无法判定",
            "还需进一步核对",
            "资料尚有疑问",
            "暂不确定",
            "未核对完成",
            "无法判断",
        )
        for unresolved_claim in unresolved_claims:
            with self.subTest(unresolved_claim=unresolved_claim):
                usage = (
                    "已分析全部有效参考视觉；本张实际向生成模型提供多张参考图，"
                    "按目标SKU筛选商品身份和外观结构，其他SKU不作为生成参考输入，"
                    f"{unresolved_claim}"
                )
                frame = make_frame(1, "主图-01", usage, usage)
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(make_storyboard([frame]))

    def test_uncertain_hidden_structure_can_be_explicitly_excluded(self) -> None:
        usage = (
            "已分析全部有效参考视觉；本张实际向生成模型提供多张同款商品图，"
            "综合商品身份和外观结构，同款资料一致，无需裁决；"
            "参考资料不能确认隐藏结构，因此本张不补画内部"
        )
        frame = make_frame(1, "主图-01", usage, usage)
        self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_fixed_reference_number_inside_dynamic_field_is_rejected(self) -> None:
        for index in ("1", "一", "A"):
            with self.subTest(index=index):
                frame = make_frame(
                    1,
                    "主图-01",
                    f"已分析全部参考视觉；本张只使用一张最清晰的参考图{index}锁定商品身份与正面几何",
                    f"本张只使用一张最清晰的参考图{index}提取商品身份与正面几何",
                )
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(make_storyboard([frame]))

    def test_unicode_fixed_reference_variants_are_rejected(self) -> None:
        labels = (
            "参考图\u200b1",
            "参\u200b考图1",
            "参考图Ⅰ",
        )
        for label in labels:
            with self.subTest(label=label):
                frame = make_frame(
                    1,
                    "主图-01",
                    f"已分析全部参考视觉；本张实际只使用一张最清晰的{label}锁定商品身份与正面几何",
                    f"本张只使用一张最清晰的{label}提取商品身份与正面几何",
                )
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(make_storyboard([frame]))

    def test_fixed_reference_number_synonyms_are_rejected(self) -> None:
        labels = (
            "参考图片1",
            "商品图1",
            "界面截图A",
            "激活流程截图（B）",
            "授权页面No.3",
            "授权页截图2",
        )
        for label in labels:
            with self.subTest(label=label):
                frame = make_frame(
                    1,
                    "主图-01",
                    f"已分析全部参考视觉；本张实际只使用一张最清晰的{label}提取商品身份和正面几何",
                    f"本张实际只使用一张最清晰的{label}提取商品身份和正面几何",
                )
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(make_storyboard([frame]))

    def test_fixed_reference_number_with_separators_is_rejected(self) -> None:
        labels = ("参考图：1", "参考图-1", "参考图（B）", "参考图 No.3")
        for label in labels:
            with self.subTest(label=label):
                frame = make_frame(
                    1,
                    "主图-01",
                    f"已分析全部参考视觉；本张实际只使用一张最清晰的{label}提取商品身份和正面结构",
                    f"本张实际只使用一张最清晰的{label}提取商品身份和正面结构",
                )
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(make_storyboard([frame]))

    def test_circled_fixed_reference_number_is_rejected(self) -> None:
        usage = (
            "已分析全部有效参考视觉；本张实际只使用一张最清晰的参考图①，"
            "提取商品身份和正面结构"
        )
        frame = make_frame(1, "主图-01", usage, usage)
        with self.assertRaises(StoryboardValidationError):
            validate_storyboard(make_storyboard([frame]))

    def test_unprefixed_methodology_expressions_are_rejected(self) -> None:
        """方法论不能借助“创作时/暗中/工作流里”等词绕过公开交付边界。"""
        expressions = (
            "依据需求张力模型组织画面",
            "采用购买阻力框架安排内容",
            "按照信任增益效应推演卖点",
            "基于产品机会模型分析画面",
            "暗中套用场景代入套路排布画面",
            "制作端依照信任升温范式编排卖点",
            "在脑内按复购触发机制安排画面",
            "将复购触发模型作为构图骨架",
            "设计环节运用品牌人格体系规划内容",
            "工作流里借助选择架构组织构图",
            "创作时采用价格接受曲线推演卖点",
        )
        base = (
            "本张实际向生成模型提供全部同款参考图，按目标SKU筛选商品身份、结构和颜色，"
            "同款资料一致，无需裁决"
        )
        for expression in expressions:
            with self.subTest(expression=expression):
                frame = make_frame(1, "主图-01", prompt_reference_usage=f"{base}；{expression}")
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(make_storyboard([frame]))

    def test_reasoning_record_labels_are_rejected_without_internal_prefix(self) -> None:
        labels = (
            "判断草案",
            "方案取舍表",
            "分析手记",
            "选择依据",
            "创作复盘",
            "审稿备注",
            "决策轨迹",
            "草案比较",
            "供审核的思路",
            "候选排序记录",
            "设计者备注",
            "过程说明",
            "利弊权衡",
            "团队讨论摘要",
            "为什么选这版：采用左侧布局",
        )
        for label in labels:
            with self.subTest(label=label):
                frame = make_frame(1, "主图-01").replace(
                    "- 成图任务：【清楚建立商品识别】",
                    f"- 成图任务：【{label}】",
                )
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(make_storyboard([frame]))

    def test_explicit_negative_internal_rules_are_allowed(self) -> None:
        negatives = (
            "不生成虚假稀缺与时效标签",
            "禁止输出内部判断记录",
            "不要出现模型思考摘要",
            "不得写出后台采用方法论的过程",
            "禁止添加幕后分析笔记",
        )
        for negative in negatives:
            with self.subTest(negative=negative):
                frame = make_frame(1, "主图-01").replace(
                    "商品变形，结构增减，错误颜色，错误文字，虚构背面，虚构内部，新增配件，悬浮，接触阴影错误，多主体，乱码",
                    f"商品变形，{negative}，结构增减，错误颜色，错误文字，虚构背面，虚构内部，新增配件，悬浮，接触阴影错误，多主体，乱码",
                )
                self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_product_internal_mechanisms_and_structures_are_allowed(self) -> None:
        product_facts = (
            "产品内部采用防漏机制",
            "设备内部采用散热机制",
            "相机内部采用自动对焦机制",
            "内部采用磁吸机制",
            "内部采用防水机制",
            "内部采用滤芯更换机制",
            "内部采用安全锁定机制",
            "内部采用四点支撑机制",
            "内部采用环形框架",
            "手机内部使用NPU推理模型",
            "产品内部依据已提供剖面图还原齿轮",
            "展示产品内部框架",
        )
        for product_fact in product_facts:
            with self.subTest(product_fact=product_fact):
                frame = make_frame(1, "主图-01")
                frame = frame.replace(
                    "- 商品锁定：【保持轮廓、结构、比例、颜色与可见原文】",
                    f"- 商品锁定：【{product_fact}，保持轮廓、结构、比例、颜色与可见原文】",
                )
                frame = frame.replace(
                    "完整保持商品轮廓、结构、比例、颜色和可见原文",
                    f"{product_fact}，完整保持商品轮廓、结构、比例、颜色和可见原文",
                )
                self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_long_english_product_identity_with_qualifier_is_allowed(self) -> None:
        frame = make_frame(1, "主图-01").replace(
            "- 商品锁定：【保持轮廓、结构、比例、颜色与可见原文】",
            "- 商品锁定：【商品名称：Blackmagic Pocket Cinema Camera 6K，保持可见原文】",
        )
        self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_natural_fixed_reference_labels_are_rejected(self) -> None:
        labels = (
            "参考图一号",
            "一号参考图",
            "编号一的参考图",
            "编号为1的参考图",
            "标记为A的商品图",
            "参考图壹号",
            "参考图甲号",
            "参考图❶",
            "参考图➊",
            "参考图㈠",
            "参考图㊀",
        )
        for label in labels:
            with self.subTest(label=label):
                usage = (
                    f"已分析全部有效参考视觉；本张实际只使用一张最清晰的{label}，"
                    "提取商品身份和正面结构"
                )
                frame = make_frame(1, "主图-01", usage, usage)
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(make_storyboard([frame]))

    def test_prefixed_and_compound_reference_ids_are_rejected(self) -> None:
        labels = ("第1张参考图", "一张参考图A1", "一张参考图No.A1")
        for label in labels:
            with self.subTest(label=label):
                usage = (
                    f"已分析全部有效参考视觉；本张实际只使用{label}，"
                    "提取商品身份和正面结构"
                )
                frame = make_frame(1, "主图-01", usage, usage)
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(make_storyboard([frame]))

    def test_reference_metadata_is_not_mistaken_for_a_fixed_index(self) -> None:
        labels = ("商品图4K原图", "商品图1080px原图", "商品图2026年拍摄版本", "商品图V2版本")
        for label in labels:
            with self.subTest(label=label):
                usage = (
                    f"已分析全部有效参考视觉；本张实际只使用一张最清晰的{label}，"
                    "提取商品身份和正面结构"
                )
                frame = make_frame(1, "主图-01", usage, usage)
                self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_reference_image_count_is_not_mistaken_for_an_index(self) -> None:
        counts = ("参考图12张", "参考图十二张")
        for count in counts:
            with self.subTest(count=count):
                usage = (
                    f"已分析全部参考视觉；本张实际向生成模型提供{count}同款资料，按目标SKU筛选商品身份和结构，"
                    "其他SKU不作为生成参考输入，同款资料一致，无需裁决"
                )
                frame = make_frame(1, "主图-01", usage, usage)
                self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_cross_sku_fusion_is_rejected(self) -> None:
        markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
            "完整保持商品轮廓", "融合多个SKU后保持商品轮廓", 1
        )
        with self.assertRaises(StoryboardValidationError):
            validate_storyboard(markdown)

    def test_multi_sku_separate_filter_cannot_hide_later_identity_fusion(self) -> None:
        unsafe_usages = (
            "已分析全部参考视觉；本张实际向生成模型提供全部参考图，按各SKU分别筛选商品身份，各SKU混在同一商品层生成，同款资料一致，无需裁决",
            "已分析全部参考视觉；本张实际向生成模型提供全部参考图，按各SKU分别筛选后合成为同一商品身份，同款资料一致，无需裁决",
        )
        for usage in unsafe_usages:
            with self.subTest(usage=usage):
                frame = make_frame(1, "SKU图-01", usage, usage).replace(
                    "- 输出对象：【主图】", "- 输出对象：【SKU图】", 1
                )
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(make_storyboard([frame]))

    def test_negative_prompt_can_explicitly_forbid_sku_fusion(self) -> None:
        rules = (
            "不要融合不同SKU",
            "不得将多个SKU进行融合",
            "避免把不同SKU混合",
            "并非融合不同SKU",
            "没有融合不同SKU",
            "不是融合不同SKU",
            "不要把各SKU混在同一商品层生成",
        )
        for rule in rules:
            with self.subTest(rule=rule):
                markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
                    "商品变形，结构增减，错误颜色",
                    f"{rule}，商品变形，结构增减，错误颜色",
                    1,
                )
                self.assertEqual(validate_storyboard(markdown), ["主图-01"])

    def test_negative_prompt_can_forbid_named_variant_component_pairing(self) -> None:
        markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
            "商品变形，结构增减，错误颜色",
            "不要A款瓶身配B款瓶盖，商品变形，结构增减，错误颜色",
            1,
        )
        self.assertEqual(validate_storyboard(markdown), ["主图-01"])

    def test_unrelated_negation_does_not_hide_sku_fusion(self) -> None:
        markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
            "完整保持商品轮廓", "不要改背景但要融合不同SKU，完整保持商品轮廓", 1
        )
        with self.assertRaises(StoryboardValidationError):
            validate_storyboard(markdown)

    def test_sku_spacing_does_not_bypass_fusion_check(self) -> None:
        markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
            "完整保持商品轮廓", "将不同 SKU 融合成一款并保持商品轮廓", 1
        )
        with self.assertRaises(StoryboardValidationError):
            validate_storyboard(markdown)

    def test_unicode_sku_variants_cannot_bypass_fusion_check(self) -> None:
        phrases = (
            "融合不同ＳＫＵ为一个商品并保持商品轮廓",
            "融合不同S\u200bKU为一个商品并保持商品轮廓",
            "融合不同S\u0332KU为一个商品并保持商品轮廓",
            "融合不同Ｓ\u200bＫＵ为一个商品并保持商品轮廓",
            "融合不同ЅKU为一个商品并保持商品轮廓",
            "融合不同ЅКU为一个商品并保持商品轮廓",
        )
        for phrase in phrases:
            with self.subTest(phrase=phrase):
                markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
                    "完整保持商品轮廓", phrase, 1
                )
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(markdown)

    def test_explicitly_nonmatching_reference_material_is_rejected(self) -> None:
        usage = (
            "已分析全部有效参考视觉；本张实际向生成模型提供多张并非同款参考图，"
            "综合商品身份和结构，同款资料一致，无需裁决"
        )
        frame = make_frame(1, "主图-01", usage, usage)
        with self.assertRaises(StoryboardValidationError):
            validate_storyboard(make_storyboard([frame]))

    def test_cross_model_component_transplant_is_rejected(self) -> None:
        transplant_phrases = (
            "将PX65的三接口模块装到PX45机身",
            "将PX65三接口模块移植到PX45机身",
            "将65X三接口模块换到45X机身",
            "将旗舰款接口模块移植到基础款机身",
            "把SKU-A的盖子装到SKU-B",
            "将A版的手柄换到B版",
            "将A款的杯盖装到B款",
            "把A款的部件用于B款",
            "将A版部件配给B版",
            "把其他版本的外壳装配到当前商品",
            "把A型号的接口给B型号使用",
        )
        for phrase in transplant_phrases:
            with self.subTest(phrase=phrase):
                markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
                    "完整保持商品轮廓", f"{phrase}并保持商品轮廓", 1
                )
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(markdown)

    def test_borrowing_other_sku_parts_is_rejected(self) -> None:
        phrases = (
            "借用其他SKU的杯盖",
            "把另一个SKU的配件借用给当前商品",
        )
        for phrase in phrases:
            with self.subTest(phrase=phrase):
                markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
                    "完整保持商品轮廓", f"{phrase}并保持商品轮廓", 1
                )
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(markdown)

    def test_natural_cross_sku_fusion_phrases_are_rejected(self) -> None:
        phrases = (
            "合并不同SKU为一个商品",
            "多个SKU混成一个商品",
            "两个SKU合并成一款",
            "A款和B款合成为一个商品",
            "红色与蓝色SKU组合成同一商品",
            "红色杯盖装到蓝色SKU机身",
            "取红色款的瓶身搭配蓝色款的瓶盖生成一款新品",
            "混合不同款式为一个主体",
            "将多个版本合成一个商品",
            "A款和B款混搭",
            "不同型号拼搭成一个主体",
            "在一个主体中使用A款和B款零件",
            "合用A版和B版的结构",
        )
        for phrase in phrases:
            with self.subTest(phrase=phrase):
                markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
                    "完整保持商品轮廓", f"{phrase}并保持商品轮廓", 1
                )
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(markdown)

    def test_cross_sku_shorthand_component_pairing_is_rejected(self) -> None:
        markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
            "完整保持商品轮廓", "A款瓶身配B款瓶盖并保持商品轮廓", 1
        )
        with self.assertRaises(StoryboardValidationError):
            validate_storyboard(markdown)

    def test_natural_cross_variant_component_installation_is_rejected(self) -> None:
        prompt_phrases = (
            "A款瓶身加装B款瓶盖",
            "A款瓶身搭上B款瓶盖",
            "A款瓶身采用B款瓶盖",
            "A款瓶身换上B款瓶盖",
            "A款瓶身配以B款瓶盖",
            "A款瓶身加B款瓶盖",
        )
        for phrase in prompt_phrases:
            with self.subTest(location="prompt", phrase=phrase):
                markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
                    "完整保持商品轮廓", f"{phrase}并保持商品轮廓", 1
                )
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(markdown)

        field_phrases = (
            "在A款瓶身上安装B款瓶盖",
            "在A款瓶身上装上B款瓶盖",
        )
        for phrase in field_phrases:
            with self.subTest(location="field", phrase=phrase):
                markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
                    "保持轮廓、结构、比例、颜色与可见原文",
                    f"{phrase}，保持其余结构、比例、颜色与可见原文",
                    1,
                )
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(markdown)

    def test_additional_cross_variant_component_reuse_is_rejected(self) -> None:
        phrases = (
            "A款杯身沿用B款杯盖",
            "A款杯身安到B款杯盖",
            "A款杯身叠上B款杯盖",
            "拆下A款杯盖给另一款使用",
            "借B款上盖",
            "套B款外壳",
            "取长补短做新品",
            "承接B款上盖",
            "吸收B款接口",
        )
        for phrase in phrases:
            with self.subTest(phrase=phrase):
                markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
                    "完整保持商品轮廓", f"{phrase}并保持商品轮廓", 1
                )
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(markdown)

    def test_asserted_fact_boundary_reversals_are_rejected(self) -> None:
        reversals = (
            "允许虚构并补画未知背面、内部和配件",
            "改变商品结构、颜色和品牌文字",
            "重画轮廓并增减结构",
            "改变背景颜色并改变商品结构",
        )
        for reversal in reversals:
            with self.subTest(reversal=reversal):
                markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
                    "不补画未知背面、内部或配件", reversal, 1
                )
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(markdown)

    def test_expanded_product_mutation_verbs_are_rejected(self) -> None:
        reversals = (
            "改造商品结构",
            "调整产品轮廓",
            "变更主体颜色",
            "替换机身配件",
            "重构商品接口",
            "移除商品配件",
            "增加商品部件",
            "添加SKU颜色",
            "删去商品结构",
            "重新设计产品外形",
            "重做商品包装",
        )
        for reversal in reversals:
            with self.subTest(reversal=reversal):
                markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
                    "不补画未知背面、内部或配件", reversal, 1
                )
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(markdown)

    def test_negated_expanded_product_mutation_is_allowed(self) -> None:
        markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
            "不补画未知背面、内部或配件",
            "不得改造、调整或替换商品结构与配件",
            1,
        )
        self.assertEqual(validate_storyboard(markdown), ["主图-01"])

    def test_unicode_variants_cannot_bypass_product_mutation_check(self) -> None:
        reversals = (
            "改\u200b造商品结构",
            "改造\u200b商\u200b品\u200b结构",
            "改造商品結構",
            "改造商品结\u0301构",
        )
        for reversal in reversals:
            with self.subTest(reversal=reversal):
                markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
                    "不补画未知背面、内部或配件", reversal, 1
                )
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(markdown)

    def test_visible_original_text_does_not_count_as_product_mutation(self) -> None:
        markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
            "完整保持商品轮廓、结构、比例、颜色和可见原文",
            "完整保持商品轮廓、结构、比例、颜色，并逐字保留包装原文「改造商品结构」",
            1,
        )
        self.assertEqual(validate_storyboard(markdown), ["主图-01"])

    def test_evidence_bounded_section_view_wording_is_allowed(self) -> None:
        instructions = (
            "改变视角为剖面示意，结构仅呈现参考图已证实部分",
            "依据工程图制作商品内部结构剖面示意图，不新增未知部件",
            "按资料中已证实的部件关系制作结构拆解示意图",
            "按已确认资料制作结构拆解示意图，部件保持原位关系",
        )
        for instruction in instructions:
            with self.subTest(instruction=instruction):
                markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
                    "完整保持商品轮廓", instruction, 1
                )
                self.assertEqual(validate_storyboard(markdown), ["主图-01"])

    def test_unconfirmed_internal_structure_can_be_excluded_naturally(self) -> None:
        markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
            "不补画未知背面、内部或配件",
            "无法确认内部结构，剖面图不补画未知部件",
            1,
        )
        self.assertEqual(validate_storyboard(markdown), ["主图-01"])

    def test_creative_environment_changes_are_allowed(self) -> None:
        changes = (
            "改变场景结构并保持商品事实",
            "改变背景结构并保持商品事实",
            "改变构图轮廓并保持商品事实",
            "改变背景颜色并保持商品事实",
            "改变光影颜色并保持商品事实",
            "修改道具轮廓并保持商品事实",
            "重画场景结构并保持商品事实",
            "新增场景配件并保持商品事实",
            "删除背景部件并保持商品事实",
            "改变人物衣服颜色并保持商品事实",
        )
        for change in changes:
            with self.subTest(change=change):
                markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
                    "只生成简洁背景", change, 1
                )
                self.assertEqual(validate_storyboard(markdown), ["主图-01"])

    def test_explicit_product_fact_mutations_are_rejected(self) -> None:
        mutations = (
            "改变商品比例",
            "修改商品材质",
            "改变商品表面",
            "调整商品尺寸",
            "改变商品数量",
            "改变商品容量",
            "重新设计商品参数",
            "改造商品功能",
            "重构商品材质",
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
                    "完整保持商品轮廓", f"{mutation}并保持商品轮廓", 1
                )
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(markdown)

    def test_explicit_non_realistic_concept_variation_is_valid(self) -> None:
        markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
            "不补画未知背面、内部或配件",
            "用户已确认这是非实物还原的概念稿，允许创意改变商品结构",
            1,
        )
        self.assertEqual(validate_storyboard(markdown), ["主图-01"])

    def test_unrelated_plain_negation_does_not_hide_sku_fusion(self) -> None:
        markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
            "完整保持商品轮廓", "不改变背景并融合不同SKU，完整保持商品轮廓", 1
        )
        with self.assertRaises(StoryboardValidationError):
            validate_storyboard(markdown)

    def test_traditional_sku_fusion_wording_is_rejected(self) -> None:
        instructions = (
            "不同型號拼搭成一個主體",
            "多個SKU融合成一個主體",
        )
        for instruction in instructions:
            with self.subTest(instruction=instruction):
                markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
                    "完整保持商品轮廓", instruction, 1
                )
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(markdown)

    def test_cross_sku_transfer_prohibitions_are_allowed(self) -> None:
        prohibitions = (
            "请勿将A款的部件装到B款",
            "不应将A款的部件装到B款",
            "切勿将A款的部件装到B款",
        )
        for prohibition in prohibitions:
            with self.subTest(prohibition=prohibition):
                markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
                    "完整保持商品轮廓", f"{prohibition}，完整保持商品轮廓", 1
                )
                self.assertEqual(validate_storyboard(markdown), ["主图-01"])

    def test_explanatory_sku_fusion_warning_is_allowed(self) -> None:
        markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
            "右侧保留短文案安全区", "右侧说明融合不同SKU会造成误购", 1
        )
        self.assertEqual(validate_storyboard(markdown), ["主图-01"])

    def test_separate_sku_layers_can_be_composited_into_an_overview(self) -> None:
        usage = (
            "已分析全部参考视觉；本张实际向生成模型提供全部可用参考图，按各SKU分别筛选商品身份，"
            "A款和B款分别生成独立商品层后合成一个总览画面，参考资料无冲突"
        )
        frame = make_frame(1, "主图-01", usage, usage)
        self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_independent_skus_can_form_a_comparison_image(self) -> None:
        usage = (
            "已分析全部参考视觉；本张实际向生成模型提供全部可用参考图，按各SKU分别筛选商品身份，"
            "将两个SKU组合为左右对比图，各SKU保持独立商品层，参考资料无冲突"
        )
        frame = make_frame(1, "主图-01", usage, usage).replace(
            "画面只出现一个商品", "画面出现两个彼此独立的商品主体", 1
        )
        self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_component_color_comparison_across_independent_skus_is_valid(self) -> None:
        usage = (
            "已分析全部参考视觉；本张实际向生成模型提供全部可用参考图，按各SKU分别筛选商品身份，"
            "对比A款瓶身配色与B款瓶盖配色，各SKU分别生成独立商品层，参考资料无冲突"
        )
        frame = make_frame(1, "主图-01", usage, usage).replace(
            "画面只出现一个商品", "画面出现两个彼此独立的商品主体", 1
        )
        self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_compact_target_sku_reference_wording_is_valid(self) -> None:
        frame = make_frame(
            1,
            "主图-01",
            "已分析全部有效参考视觉；本张实际向生成模型提供多张同款参考图，只综合目标SKU的商品身份、结构与颜色，同款资料一致，无需裁决",
            "本张实际向生成模型提供多张同款参考图，仅采用目标SKU的商品身份、结构与颜色，同款资料一致，无需裁决",
        )
        self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_two_reference_images_is_valid_natural_wording(self) -> None:
        frame = make_frame(
            1,
            "主图-01",
            "已分析全部参考视觉；本张实际向生成模型提供两张同款参考图，按目标SKU筛选商品身份、结构和颜色，同一SKU内互补，同款资料一致，无需裁决",
            "本张实际向生成模型提供两张同款参考图，只采用目标SKU的商品身份、结构和颜色，同一SKU内互补，同款资料一致，无需裁决",
        )
        self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_digital_service_reference_visual_is_valid(self) -> None:
        frame = make_frame(
            1,
            "主图-01",
            "已分析全部有效参考视觉；本张实际向生成模型提供两张同版本界面截图，按目标版本筛选真实界面、权益和流程，同一版本内互补，同款资料一致，无需裁决",
            "本张实际向生成模型提供两张同版本界面截图，按目标版本筛选真实界面、权益和交付流程，同一版本内互补，同款资料一致，无需裁决",
        )
        frame = frame.replace(
            "保持轮廓、结构、比例、颜色与可见原文",
            "保持真实界面层级、权益版本、交付状态与品牌原文",
        ).replace(
            "单个商品稳定放置并成为唯一焦点",
            "真实权益界面作为唯一核心视觉载体",
        )
        self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_digital_reference_visual_natural_terms_are_valid(self) -> None:
        cases = (
            ("权益页截图", "权益版本和可见原文"),
            ("激活流程截图", "激活流程和交付状态"),
            ("真实卖家授权页面", "授权范围和品牌原文"),
            ("到账状态截图", "交付状态和权益版本"),
            ("已授权服务场景", "服务触点和真实场景"),
        )
        for reference_term, purpose in cases:
            with self.subTest(reference_term=reference_term):
                usage = (
                    f"已分析全部有效{reference_term}；本张实际向生成模型提供两张同版本{reference_term}，"
                    f"按目标版本筛选{purpose}，同一版本内互补，同款资料一致，无需裁决"
                )
                frame = make_frame(1, "主图-01", usage, usage)
                self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_natural_reference_media_and_units_are_valid(self) -> None:
        cases = (
            ("一张同款商品实拍", "商品身份和正面结构"),
            ("一幅同款实物照片", "商品身份和表面细节"),
            ("一张同款包装照片", "包装版本和可见原文"),
            ("一份同款结构图", "商品结构和部件关系"),
            ("一段同版本界面录屏", "真实界面和流程状态"),
            ("一帧同版本界面录屏", "真实界面和流程状态"),
            ("一屏同版本界面截图", "真实界面和流程状态"),
            ("一份同版本授权文件", "授权范围和品牌原文"),
            ("两页同版本权益页面", "权益版本和可见原文"),
            ("两份同款资料", "商品身份、结构和细节"),
            ("两份同版本资料", "权益版本、界面和流程"),
        )
        for actual_input, purpose in cases:
            with self.subTest(actual_input=actual_input):
                usage = (
                    "已分析全部有效参考视觉；"
                    f"本张实际向生成模型提供{actual_input}，综合{purpose}"
                )
                frame = make_frame(1, "主图-01", usage, usage)
                self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_natural_paired_reference_scopes_are_valid(self) -> None:
        scopes = (
            "一对同款参考图",
            "成对同款参考图",
            "双份同款参考图",
            "双张同款参考图",
            "两帧界面录屏",
            "两屏界面截图",
            "正反两面商品图",
            "若干幅实拍图",
        )
        for scope in scopes:
            with self.subTest(scope=scope):
                usage = (
                    f"已分析全部有效参考视觉；本张实际向生成模型提供{scope}，"
                    "只综合目标SKU的商品身份、结构和颜色，同款资料一致，无需裁决"
                )
                frame = make_frame(1, "主图-01", usage, usage)
                self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_natural_global_analysis_synonyms_are_valid(self) -> None:
        verbs = ("逐一查看", "审阅", "核对", "核验")
        for verb in verbs:
            with self.subTest(verb=verb):
                usage = (
                    f"已{verb}全部有效参考图；本张实际只使用一张同款商品图，"
                    "提取商品身份和正面结构"
                )
                frame = make_frame(1, "主图-01", usage, usage)
                self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_multi_digit_and_chinese_reference_counts_are_multi_reference(self) -> None:
        counts = ("10张", "11张", "21张", "101张", "十一张", "二十一张", "一百零一张")
        for count in counts:
            with self.subTest(count=count):
                field_usage = (
                    f"已分析全部有效参考视觉；本张实际向生成模型提供{count}同款商品图，"
                    "综合互补商品身份、结构和细节"
                )
                prompt_usage = (
                    "本张实际向生成模型提供多张同款商品图，综合互补商品身份、结构和细节"
                )
                frame = make_frame(1, "主图-01", field_usage, prompt_usage)
                self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_single_reference_counts_with_natural_units_are_valid(self) -> None:
        counts = ("1张", "一张", "1幅", "一幅", "1份", "一份", "1页", "一页", "1段", "一段")
        for count in counts:
            with self.subTest(count=count):
                usage = (
                    f"已分析全部有效参考视觉；本张实际向生成模型提供{count}同款商品实拍，"
                    "提取商品身份和正面结构"
                )
                frame = make_frame(1, "主图-01", usage, usage)
                self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_collection_units_and_multiple_single_mentions_trigger_multi_reference_safety(self) -> None:
        unsafe_usages = (
            "已分析全部有效参考视觉；本张实际向生成模型提供一套参考图，综合红色款商品身份与蓝色款结构",
            "已分析全部有效参考视觉；本张实际向生成模型提供参考视觉：正面1张、侧面1张，提取商品身份和结构",
        )
        for usage in unsafe_usages:
            with self.subTest(usage=usage):
                frame = make_frame(1, "主图-01", usage, usage)
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(make_storyboard([frame]))

    def test_natural_batch_reference_scope_is_valid(self) -> None:
        usage = (
            "已分析全部有效参考视觉；本张实际向生成模型提供一批同款参考图，"
            "只综合目标SKU的商品身份、结构与颜色，同款资料一致，无需裁决"
        )
        frame = make_frame(1, "主图-01", usage, usage)
        self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_natural_batch_quantities_are_valid_multi_reference_scopes(self) -> None:
        for quantity in ("2批", "两批", "多批"):
            with self.subTest(quantity=quantity):
                usage = (
                    f"已分析全部有效参考视觉；本张实际向生成模型提供{quantity}同款参考图，"
                    "只综合目标SKU的商品身份、结构与颜色，同款资料一致，无需裁决"
                )
                frame = make_frame(1, "主图-01", usage, usage)
                self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_invalid_reference_counts_are_rejected(self) -> None:
        counts = ("-1张", "0张")
        for count in counts:
            with self.subTest(count=count):
                usage = (
                    f"已分析全部有效参考视觉；本张实际向生成模型提供{count}同款参考图，"
                    "提取商品身份和正面结构"
                )
                frame = make_frame(1, "主图-01", usage, usage)
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(make_storyboard([frame]))

    def test_global_analysis_and_single_generation_input_can_coexist(self) -> None:
        frame = make_frame(
            1,
            "主图-01",
            "已分析全部有效参考视觉；本张实际向生成模型只提供一张最清晰参考图，提取商品身份和正面几何",
            "已分析全部参考视觉后，本张实际向生成模型只提供一张最清晰参考图，提取商品身份和正面几何",
        )
        self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_global_analysis_can_use_partial_same_sku_generation_subset(self) -> None:
        usage = (
            "已分析全部有效参考视觉，但本张实际只使用其中一部分同款参考图，"
            "只综合目标SKU的商品身份和结构，同款资料一致，无需裁决"
        )
        frame = make_frame(1, "主图-01", usage, usage)
        self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_specific_generation_input_marker_takes_priority(self) -> None:
        usage = (
            "本张已分析全部有效参考视觉后，实际向生成模型提供一张最清晰商品图，"
            "提取商品身份和正面结构"
        )
        frame = make_frame(1, "主图-01", usage, usage)
        self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_single_sku_multi_reference_wording_does_not_require_formulaic_sku_text(self) -> None:
        usages = (
            "已分析全部有效参考视觉；本张实际向生成模型提供两张同款商品图综合互补，提取商品身份、结构和细节",
            "已分析全部有效参考视觉；本张实际向生成模型提供全部同款商品图，综合商品身份、结构和细节",
            "已分析全部有效参考视觉；本张实际向生成模型提供多张商品图，只综合红色500ml款的商品身份、结构和细节",
        )
        for usage in usages:
            with self.subTest(usage=usage):
                frame = make_frame(1, "主图-01", usage, usage)
                self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_negated_target_sku_filter_is_rejected(self) -> None:
        for negation in ("不按", "并非按", "没有按"):
            with self.subTest(negation=negation):
                usage = (
                    f"已分析全部参考视觉；本张实际向生成模型提供多张参考图，{negation}目标SKU筛选商品身份，"
                    "同一SKU内互补，同款资料一致，无需裁决"
                )
                frame = make_frame(1, "主图-01", usage, usage)
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(make_storyboard([frame]))

    def test_postposed_negation_cannot_claim_analysis_or_sku_safety(self) -> None:
        unsafe_usages = (
            "已分析的并非全部有效参考视觉；本张实际向生成模型提供多张参考图，按目标SKU筛选商品身份，同一SKU内互补，同款资料一致",
            "已分析全部有效参考视觉；本张实际向生成模型提供多张参考图，按目标SKU并未筛选商品身份，同一SKU内互补，同款资料一致",
            "已分析全部有效参考视觉；本张实际向生成模型提供多张参考图，按目标SKU筛选商品身份，同一SKU并未互补，同款资料一致",
            "已分析全部有效参考视觉；本张实际向生成模型提供多张参考图，按目标SKU筛选商品身份，其他SKU没有排除，同款资料一致",
            "已分析全部有效参考视觉尚未完成；本张实际只使用一张参考图提取商品身份和正面结构",
            "已分析全部有效参考视觉；本张实际向生成模型提供多张参考图，不只综合红色款的商品身份，也综合蓝色款的结构，同款资料一致",
            "已分析全部有效参考视觉；本张实际向生成模型提供多张同款参考图，综合商品身份和结构，同款资料是否相同尚不确定",
        )
        for usage in unsafe_usages:
            with self.subTest(usage=usage):
                frame = make_frame(1, "主图-01", usage, usage)
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(make_storyboard([frame]))

    def test_other_sku_later_generation_input_is_rejected(self) -> None:
        unsafe_usages = (
            "已分析全部有效参考视觉；本张实际向生成模型提供多张同款参考图，按目标SKU筛选商品身份和结构，"
            "其他SKU不作为生成参考输入；但其他SKU也传入生成模型，同款资料一致，无需裁决",
            "已分析全部有效参考视觉；本张实际向生成模型提供多张同款参考图，按目标SKU筛选商品身份和结构，"
            "其他SKU不作为生成参考输入；但其他SKU也傳入生成模型，同款资料一致，无需裁决",
            "已分析全部有效参考视觉；本张实际向生成模型提供多张同款参考图，按目标SKU筛选商品身份和结构，"
            "向生成模型提供其他SKU的参考图，同款资料一致，无需裁决",
        )
        for usage in unsafe_usages:
            with self.subTest(usage=usage):
                frame = make_frame(1, "主图-01", usage, usage)
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(make_storyboard([frame]))

    def test_explicit_other_sku_exclusion_is_valid(self) -> None:
        usages = (
            "已分析全部有效参考视觉；本张实际向生成模型提供多张同款参考图，按目标SKU筛选商品身份和结构，"
            "其他SKU不传入生成模型，同款资料一致，无需裁决",
            "已分析全部有效参考视觉；本张实际向生成模型提供多张同款参考图，按目标SKU筛选商品身份和结构，"
            "不同SKU仅用于差异比对，不作为生成参考输入，同款资料一致，无需裁决",
        )
        for usage in usages:
            with self.subTest(usage=usage):
                frame = make_frame(1, "主图-01", usage, usage)
                self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

    def test_later_unresolved_statement_overrides_earlier_positive_claim(self) -> None:
        unsafe_usages = (
            "已分析全部有效参考视觉；本张实际向生成模型提供多张同款商品图，综合商品身份和结构，同款资料一致；冲突尚未解决",
            "已分析全部有效参考视觉；实际未完整分析全部有效参考视觉；本张实际向生成模型提供一张同款商品图，提取商品身份和结构",
        )
        for usage in unsafe_usages:
            with self.subTest(usage=usage):
                frame = make_frame(1, "主图-01", usage, usage)
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(make_storyboard([frame]))

    def test_negated_sku_isolation_is_rejected(self) -> None:
        for negation in ("不只用", "并非只用", "没有只用"):
            with self.subTest(negation=negation):
                usage = (
                    f"已分析全部参考视觉；本张实际向生成模型提供多张参考图，按目标SKU筛选商品身份，{negation}目标SKU，"
                    "其他SKU作为主身份来源，同款资料一致，无需裁决"
                )
                frame = make_frame(1, "主图-01", usage, usage)
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(make_storyboard([frame]))

    def test_unresolved_product_card_pointer_is_rejected(self) -> None:
        markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
            "同款资料一致，无需裁决", "冲突以已确认商品卡为准", 1
        )
        with self.assertRaises(StoryboardValidationError):
            validate_storyboard(markdown)

    def test_reading_product_card_inside_final_prompt_is_rejected(self) -> None:
        pointers = (
            "按照已确认商品卡中的结论保持商品轮廓",
            "遵循已确认商品卡保持商品轮廓",
            "根据已确认商品卡保持商品轮廓",
            "与已确认商品卡保持一致并保持商品轮廓",
        )
        for pointer in pointers:
            with self.subTest(pointer=pointer):
                markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
                    "完整保持商品轮廓", pointer, 1
                )
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(markdown)

    def test_common_hidden_context_pointers_are_rejected(self) -> None:
        pointers = (
            "按上述商品信息保持商品轮廓",
            "依照前述方案保持商品轮廓",
            "保持与前一张一致",
            "沿用前图中的商品",
            "按已确认信息保持商品轮廓",
            "依据上面的商品资料保持商品轮廓",
            "沿用上图的商品轮廓与颜色",
            "照上文执行商品锁定",
            "与前图一致并保持商品轮廓",
            "承接前一页的商品表现",
        )
        for pointer in pointers:
            with self.subTest(pointer=pointer):
                markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
                    "完整保持商品轮廓", pointer, 1
                )
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(markdown)

    def test_natural_hidden_context_pointers_are_rejected(self) -> None:
        pointers = (
            "继续使用刚才那个商品",
            "参照先前页面",
            "延续前面商品",
            "按先前定稿",
            "承接刚才画面",
            "商品设定同前",
            "复用之前设定",
        )
        for pointer in pointers:
            with self.subTest(pointer=pointer):
                markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
                    "完整保持商品轮廓", pointer, 1
                )
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(markdown)

    def test_natural_continuation_context_pointers_are_rejected(self) -> None:
        pointers = (
            "延续前页的浅灰背景",
            "与前一页保持一致",
            "接续上一模块的主光",
            "沿用前页背景",
            "承接前模块",
            "与上一模块相同",
            "依据上一张的设定",
            "跟前图无缝衔接",
            "上一屏保持同样色调",
        )
        for pointer in pointers:
            with self.subTest(pointer=pointer):
                markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
                    "完整保持商品轮廓", pointer, 1
                )
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(markdown)

    def test_explicit_shared_visual_anchor_does_not_require_previous_context(self) -> None:
        explicit_anchors = (
            "采用已写明的浅灰背景、左侧主光和统一色调",
            "本张明确使用浅灰背景与同样色温的主光",
        )
        for anchor in explicit_anchors:
            with self.subTest(anchor=anchor):
                markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
                    "完整保持商品轮廓", anchor, 1
                )
                self.assertEqual(validate_storyboard(markdown), ["主图-01"])

    def test_unmarked_non_chinese_scripts_are_rejected(self) -> None:
        instructions = (
            "保持商品轮廓、结构和颜色、商品は高品質で描画",
            "保持商品轮廓、结构和颜色、Создать реалистичный товар",
        )
        for instruction in instructions:
            with self.subTest(instruction=instruction):
                markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
                    "完整保持商品轮廓", instruction, 1
                )
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(markdown)

    def test_non_chinese_scripts_in_preserved_ui_original_are_allowed(self) -> None:
        for original in ("商品名 カメラ", "Товар PRO"):
            with self.subTest(original=original):
                markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
                    "完整保持商品轮廓、结构、比例、颜色和可见原文",
                    f"完整保持商品轮廓、结构、比例、颜色，并逐字保留界面原文「{original}」",
                    1,
                )
                self.assertEqual(validate_storyboard(markdown), ["主图-01"])

    def test_previous_frame_pointer_is_rejected(self) -> None:
        markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
            "完整保持商品轮廓", "参照上一帧保持商品轮廓", 1
        )
        with self.assertRaises(StoryboardValidationError):
            validate_storyboard(markdown)

    def test_storyboard_without_reference_index_is_valid(self) -> None:
        markdown = make_storyboard([make_frame(1, "主图-01")])
        self.assertEqual(validate_storyboard(markdown), ["主图-01"])

    def test_legacy_reference_index_is_rejected(self) -> None:
        markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
            "````markdown\n",
            "````markdown\n### 参考图索引\n- 参考图1：【旧格式】\n\n",
            1,
        )
        with self.assertRaises(StoryboardValidationError):
            validate_storyboard(markdown)

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
            "本张实际向生成模型提供全部同款参考图，按目标SKU/状态筛选商品身份、正面几何和共同特征，其他SKU不作为生成参考输入，同款资料一致，无需裁决，完整保持商品轮廓、结构、比例、颜色和可见原文，只生成简洁背景、柔和侧光、真实接触阴影和右侧低细节安全区，画面只出现一个商品，不补画未知背面、内部或配件。",
            "Keep the product unchanged on a clean studio background.",
        )
        with self.assertRaises(StoryboardValidationError):
            validate_storyboard(markdown)

    def test_almost_entirely_english_prompt_is_rejected(self) -> None:
        markdown = make_storyboard([make_frame(1, "主图-01")])
        markdown = markdown.replace(
            "本张实际向生成模型提供全部同款参考图，按目标SKU/状态筛选商品身份、正面几何和共同特征，其他SKU不作为生成参考输入，同款资料一致，无需裁决，完整保持商品轮廓、结构、比例、颜色和可见原文，只生成简洁背景、柔和侧光、真实接触阴影和右侧低细节安全区，画面只出现一个商品，不补画未知背面、内部或配件。",
            "Keep all reference images unchanged and render a clean premium studio product photo with realistic lighting, shadows, composition, materials and typography. 中文",
        )
        with self.assertRaises(StoryboardValidationError):
            validate_storyboard(markdown)

    def test_fullwidth_english_prompt_is_rejected(self) -> None:
        markdown = make_storyboard([make_frame(1, "主图-01")])
        fullwidth = "Ｇｅｎｅｒａｔｅ　ａ　ｐｒｅｍｉｕｍ　ｐｒｏｄｕｃｔ　ｓｃｅｎｅ"
        markdown = markdown.replace(
            "本张实际向生成模型提供全部同款参考图，按目标SKU/状态筛选商品身份、正面几何和共同特征，其他SKU不作为生成参考输入，同款资料一致，无需裁决，完整保持商品轮廓、结构、比例、颜色和可见原文，只生成简洁背景、柔和侧光、真实接触阴影和右侧低细节安全区，画面只出现一个商品，不补画未知背面、内部或配件。",
            fullwidth,
        )
        with self.assertRaises(StoryboardValidationError):
            validate_storyboard(markdown)

    def test_fullwidth_english_padding_cannot_hide_instruction_language(self) -> None:
        fullwidth = "　".join("ＲｅｎｄｅｒＰｒｅｍｉｕｍＳｃｅｎｅ" for _ in range(180))
        prompt = (
            "本张实际向生成模型提供全部同款参考图，按目标SKU筛选商品身份和结构，"
            "其他SKU不作为生成参考输入，同款资料一致，无需裁决，"
            f"{fullwidth}"
        )
        frame = make_frame(1, "主图-01", prompt_reference_usage=prompt)
        with self.assertRaises(StoryboardValidationError):
            validate_storyboard(make_storyboard([frame]))

    def test_repeated_chinese_padding_cannot_hide_english_instructions(self) -> None:
        english_instruction = " ".join(
            f"RenderPremiumProductScene{index}" for index in range(250)
        )
        paddings = ("中文" * 300, "商品" * 300, "请生成" * 200, "保持真实" * 200)
        for padding in paddings:
            with self.subTest(padding=padding[:8]):
                prompt = (
                    "本张实际向生成模型提供全部同款参考图，按目标SKU筛选商品身份和结构，"
                    "其他SKU不作为生成参考输入，同款资料一致，无需裁决，"
                    f"{english_instruction}，{padding}"
                )
                frame = make_frame(1, "主图-01", prompt_reference_usage=prompt)
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(make_storyboard([frame]))

    def test_unknown_public_field_is_rejected(self) -> None:
        markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
            "- 成图任务：", "- 内部评分：95\n- 成图任务：", 1
        )
        with self.assertRaises(StoryboardValidationError):
            validate_storyboard(markdown)

    def test_extra_report_outside_frames_is_rejected(self) -> None:
        markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
            "````markdown\n", "````markdown\n内部评分与审查报告：95分\n\n", 1
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

    def test_natural_internal_review_terms_are_rejected(self) -> None:
        internal_terms = (
            "内部打分95分",
            "审核结论：通过",
            "评审意见：采用当前稿",
            "候选稿A优于B",
            "思维链如下",
            "推理过程如下",
            "内部质检合格",
        )
        for internal_term in internal_terms:
            with self.subTest(internal_term=internal_term):
                markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
                    "真实商品层和文字由后期复核", internal_term, 1
                )
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(markdown)

    def test_unicode_internal_review_terms_are_rejected(self) -> None:
        internal_terms = (
            "内\u200b部评分合格",
            "写实视\u200b图确认",
            "背\u200b面\u200b置信度92分",
            "內部審核通過",
        )
        for internal_term in internal_terms:
            with self.subTest(internal_term=internal_term):
                markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
                    "真实商品层和文字由后期复核", internal_term, 1
                )
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(markdown)

    def test_visible_ui_original_can_contain_internal_sounding_words(self) -> None:
        for ui_original in (
            "候选方案A",
            "调试字段：enabled",
            "评审意见：已确认",
            "置信度95%",
            "推定为蓝色",
            "背面：示意图",
            "写实视图确认",
            "待范围判断",
        ):
            with self.subTest(ui_original=ui_original):
                markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
                    "完整保持商品轮廓、结构、比例、颜色和可见原文",
                    f"完整保持商品轮廓、结构、比例和颜色，并逐字保留界面原文「{ui_original}」",
                    1,
                )
                self.assertEqual(validate_storyboard(markdown), ["主图-01"])

    def test_hidden_view_inference_annotations_are_rejected(self) -> None:
        annotations = (
            "高置信推定",
            "背面：示意",
            "置信度92分",
            "推测背面为平面结构",
            "看起来背面有第二个接口",
            "大概率存在隐藏配件",
            "写实视图确认",
            "待范围判断",
            "81–100分",
            "已确认写实视图",
            "独立还原置信度",
            "识别置信度",
            "分数：92",
            "评分92分",
            "得分92分",
            "还原得分92",
            "独立置信度满分",
            "评分结果",
            "待审核",
            "写实确认已通过",
            "还原可信度92%",
            "视图审核通过",
            "待进一步审核",
            "置信水平92%",
            "还原把握度高",
            "背面确认状态：通过",
        )
        for annotation in annotations:
            with self.subTest(annotation=annotation):
                markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
                    "不补画未知背面", f"背面标注为{annotation}", 1
                )
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(markdown)

    def test_traditional_hidden_view_annotations_are_rejected(self) -> None:
        annotations = (
            "寫實視圖確認",
            "背面確認狀態：通過",
            "背面置信度92分",
        )
        for annotation in annotations:
            with self.subTest(annotation=annotation):
                markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
                    "不补画未知背面", f"背面标注为{annotation}", 1
                )
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(markdown)

    def test_non_hidden_visual_phrases_are_not_mistaken_for_view_inference(self) -> None:
        phrases = (
            "商品看起来真实可信",
            "高光很可能形成自然层次",
            "大概率提升首屏识别效率",
        )
        for phrase in phrases:
            with self.subTest(phrase=phrase):
                markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
                    "完整保持商品轮廓", f"{phrase}，完整保持商品轮廓", 1
                )
                self.assertEqual(validate_storyboard(markdown), ["主图-01"])

    def test_product_measurements_with_fen_unit_prefix_are_allowed(self) -> None:
        product_facts = (
            "右侧显示已确认的续航92分钟与降噪92分贝参数",
            "右侧显示已确认的100分区Mini LED背光参数",
            "右侧显示已确认的主钻81分规格",
            "右侧显示已确认的客户评分结果",
        )
        for product_fact in product_facts:
            with self.subTest(product_fact=product_fact):
                markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
                    "右侧低细节安全区", product_fact, 1
                )
                self.assertEqual(validate_storyboard(markdown), ["主图-01"])

    def test_negated_view_inference_wording_is_allowed(self) -> None:
        markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
            "不补画未知背面",
            "不得推定参考视觉未展示的内部接口，不补画未知背面",
            1,
        )
        self.assertEqual(validate_storyboard(markdown), ["主图-01"])

    def test_traditional_hidden_context_and_fixed_reference_markers_are_rejected(self) -> None:
        cases = (
            ("完整保持商品轮廓", "沿用上一張保持商品轮廓"),
            ("商品锁定：", "商品身份参考圖編號：壹\n- 商品锁定："),
            ("商品锁定：", "商品身份第壹張參考圖\n- 商品锁定："),
        )
        for original, replacement in cases:
            with self.subTest(replacement=replacement):
                markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
                    original, replacement, 1
                )
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(markdown)

    def test_non_view_diagram_word_is_allowed(self) -> None:
        markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
            "右侧低细节安全区", "右侧低细节尺寸关系示意区", 1
        )
        self.assertEqual(validate_storyboard(markdown), ["主图-01"])

    def test_quantity_note_is_the_only_allowed_preamble_line(self) -> None:
        markdown = make_storyboard(
            [make_frame(1, "主图-01")],
            "> 数量说明：用户要求2张，现有素材只能真实制作1张。",
        )
        self.assertEqual(validate_storyboard(markdown), ["主图-01"])

    def test_quantity_note_accepts_natural_chinese_counts(self) -> None:
        notes = (
            "> 数量说明：用户要求三张，现有素材只能真实制作两张。",
            "> 数量说明：用户要求3 张，现有素材只能真实制作 2 张。",
            "> 数量说明：用户要求5个详情页模块，现有证据只能支持4个模块。",
            "> 数量说明：用户要求六条分镜，去重后交付四条分镜。",
        )
        for note in notes:
            with self.subTest(note=note):
                markdown = make_storyboard([make_frame(1, "主图-01")], note)
                self.assertEqual(validate_storyboard(markdown), ["主图-01"])

    def test_quantity_note_without_an_image_count_is_rejected(self) -> None:
        markdown = make_storyboard(
            [make_frame(1, "主图-01")],
            "> 数量说明：内部评分与审查报告95分。",
        )
        with self.assertRaises(StoryboardValidationError):
            validate_storyboard(markdown)

    def test_english_product_name_is_allowed_inside_chinese_prompts(self) -> None:
        markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
            "商品身份、正面几何", "iPhone 16 Pro Max MagSafe USB-C商品身份、正面几何", 1
        )
        self.assertEqual(validate_storyboard(markdown), ["主图-01"])

    def test_compact_brand_and_model_fields_are_allowed(self) -> None:
        for model in ("Canon EOSR5", "iPhone 16 Pro Max", "Apple AirPods Pro"):
            with self.subTest(model=model):
                markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
                    "保持轮廓、结构、比例、颜色与可见原文", model, 1
                )
                self.assertEqual(validate_storyboard(markdown), ["主图-01"])

    def test_english_description_field_is_rejected(self) -> None:
        descriptions = (
            "Render 3 premium product images",
            "Cinematic 3D Hyperrealistic Packshot",
            "Ultra HD Cinematic Studio Photography",
        )
        for description in descriptions:
            with self.subTest(description=description):
                markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
                    "保持轮廓、结构、比例、颜色与可见原文",
                    description,
                    1,
                )
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(markdown)

    def test_chinese_instructions_can_preserve_long_brand_model_and_ui_text(self) -> None:
        preserved_original = (
            "Microsoft Surface Laptop Studio 2 Windows Hello Copilot Microsoft 365 "
            "Adobe Creative Cloud Sign in Continue Account Settings Privacy Security "
            "Subscription Benefits Order History Device Management Terms and Conditions"
        )
        markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
            "完整保持商品轮廓、结构、比例、颜色和可见原文",
            f"完整保持商品轮廓、结构、比例、颜色，并逐字保留界面中的原文“{preserved_original}”",
            1,
        )
        self.assertEqual(validate_storyboard(markdown), ["主图-01"])

    def test_short_chinese_negative_prompt_is_allowed(self) -> None:
        markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
            "商品变形，结构增减，错误颜色，错误文字，虚构背面，虚构内部，新增配件，悬浮，接触阴影错误，多主体，乱码",
            "商品变形、错色、乱码",
            1,
        )
        self.assertEqual(validate_storyboard(markdown), ["主图-01"])

    def test_three_character_chinese_negative_prompt_is_allowed(self) -> None:
        markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
            "商品变形，结构增减，错误颜色，错误文字，虚构背面，虚构内部，新增配件，悬浮，接触阴影错误，多主体，乱码",
            "勿变形",
            1,
        )
        self.assertEqual(validate_storyboard(markdown), ["主图-01"])

    def test_quoted_long_ui_original_does_not_change_instruction_language(self) -> None:
        ui_original = " ".join(f"Button{index}" for index in range(300))
        markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
            "完整保持商品轮廓、结构、比例、颜色和可见原文",
            f"完整保持商品轮廓、结构、比例和颜色，并逐字保留界面原文“{ui_original}”",
            1,
        )
        self.assertEqual(validate_storyboard(markdown), ["主图-01"])

    def test_corner_quoted_long_ui_original_does_not_change_instruction_language(self) -> None:
        ui_original = " ".join(f"Button{index}" for index in range(300))
        markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
            "完整保持商品轮廓、结构、比例、颜色和可见原文",
            f"完整保持商品轮廓、结构、比例和颜色，并逐字保留界面原文「{ui_original}」",
            1,
        )
        self.assertEqual(validate_storyboard(markdown), ["主图-01"])

    def test_long_ui_original_in_full_width_brackets_does_not_change_instruction_language(self) -> None:
        ui_original = " ".join(f"Button{index}" for index in range(300))
        for opening, closing in (("（", "）"), ("〈", "〉"), ("〖", "〗"), ("〔", "〕")):
            with self.subTest(brackets=opening + closing):
                markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
                    "完整保持商品轮廓、结构、比例、颜色和可见原文",
                    f"完整保持商品轮廓、结构、比例和颜色，并逐字保留界面原文{opening}{ui_original}{closing}",
                    1,
                )
                self.assertEqual(validate_storyboard(markdown), ["主图-01"])

    def test_non_original_english_in_preserved_brackets_is_rejected(self) -> None:
        ui_original = " ".join(f"Button{index}" for index in range(100))
        english_instruction = " ".join(
            f"RenderPremiumProductScene{index}" for index in range(300)
        )
        markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
            "完整保持商品轮廓、结构、比例、颜色和可见原文",
            (
                "完整保持商品轮廓、结构、比例和颜色，并逐字保留界面原文"
                f"（{ui_original}；以下内容不是原文而是生成指令：{english_instruction}）"
            ),
            1,
        )
        with self.assertRaises(StoryboardValidationError):
            validate_storyboard(markdown)

    def test_template_placeholder_is_rejected(self) -> None:
        markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
            "【清楚建立商品识别】", "【填写：本张唯一需要解决的问题】", 1
        )
        with self.assertRaises(StoryboardValidationError):
            validate_storyboard(markdown)

    def test_common_template_placeholder_syntaxes_are_rejected(self) -> None:
        placeholders = (
            "{{商品名称}}",
            "${PRODUCT_NAME}",
            "<填写核心卖点>",
            "<PRODUCT_NAME>",
            "商品名称：待填写",
            "⟦商品名称⟧",
            "〈PRODUCT_NAME〉",
            "《商品名称》",
            "「填写名称」",
            "[INSERT PRODUCT]",
            "[[商品名称]]",
            "【稍后补充卖点】",
            "XXX商品名称",
            "佔位符",
            "省略號",
            "名稱：待填寫",
            "待更新",
            "后续补充",
            "待完善",
            "…",
        )
        for placeholder in placeholders:
            with self.subTest(placeholder=placeholder):
                markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
                    "清楚建立商品识别", placeholder, 1
                )
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(markdown)

    def test_common_secret_formats_are_rejected(self) -> None:
        secrets = (
            "Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.signature",
            "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.signature",
            "password=SuperSecret12345",
            "Cookie: sessionid=abcdef1234567890",
            "AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "api key=ExampleSecretValue12345",
            "Authorization: Basic dGVzdDpFeGFtcGxlU2VjcmV0MTIzNDU=",
            "session_token=ExampleSessionToken12345",
            "refresh_token=ExampleRefreshToken12345",
            "client secret=ExampleClientSecret12345",
            "密码：abcdefgh",
            "密碼：abcdefgh",
            "API密钥：abcdefgh",
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

    def test_transparent_background_alias_is_supported(self) -> None:
        for output_object, storyboard_id in (
            ("透明背景图", "透明图-01"),
            ("透明图", "透明背景图-01"),
        ):
            with self.subTest(output_object=output_object, storyboard_id=storyboard_id):
                frame = make_frame(1, storyboard_id).replace(
                    "- 输出对象：【主图】", f"- 输出对象：【{output_object}】", 1
                )
                self.assertEqual(validate_storyboard(make_storyboard([frame])), [storyboard_id])

    def test_legacy_fixed_reference_field_is_rejected(self) -> None:
        frame = make_frame(1, "主图-01").replace(
            "- 商品锁定：", "- 商品身份参考图：【参考图1｜旧格式固定绑定】\n- 商品锁定：", 1
        )
        with self.assertRaises(StoryboardValidationError):
            validate_storyboard(make_storyboard([frame]))

    def test_outer_markdown_fence_is_optional(self) -> None:
        markdown = make_storyboard([make_frame(1, "主图-01")])
        markdown = markdown.removeprefix("````markdown\n").removesuffix("````\n")
        self.assertEqual(validate_storyboard(markdown), ["主图-01"])

    def test_reference_usage_field_is_required(self) -> None:
        markdown = make_storyboard([make_frame(1, "主图-01").replace("- 参考图使用：", "- 已删除字段：", 1)])
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
