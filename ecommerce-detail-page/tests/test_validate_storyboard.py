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
- 画布与布局：【商品居中，占画面一半，右侧保留短文案安全区】
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
    def test_valid_fixture(self) -> None:
        result = validate_storyboard(FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(result, ["主图-01"])

    def test_readme_final_storyboard_example_is_valid(self) -> None:
        readme = (ROOT.parent / "README.md").read_text(encoding="utf-8")
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
            "已分析全部参考视觉；本张实际向生成模型提供全部同款参考图提取商品身份、结构与颜色，其他SKU不作为生成参考输入，同款资料一致，无需裁决",
            "已分析全部参考视觉；本张实际向生成模型提供全部同款参考图，按目标SKU/状态筛选商品身份、结构与颜色，其他SKU不作为生成参考输入，同款资料一致，无需裁决",
        )
        with self.assertRaises(StoryboardValidationError):
            validate_storyboard(make_storyboard([frame]))

    def test_multi_reference_prompt_requires_target_sku_filter(self) -> None:
        frame = make_frame(
            1,
            "主图-01",
            "本张实际向生成模型提供全部同款参考图，按目标SKU/状态筛选商品身份、结构与颜色，其他SKU不作为生成参考输入，同款资料一致，无需裁决",
            "本张实际向生成模型提供全部同款参考图提取商品身份、结构与颜色，其他SKU不作为生成参考输入，同款资料一致，无需裁决",
        )
        with self.assertRaises(StoryboardValidationError):
            validate_storyboard(make_storyboard([frame]))

    def test_multi_reference_field_requires_conflict_resolution(self) -> None:
        frame = make_frame(
            1,
            "主图-01",
            "已分析全部参考视觉；本张实际向生成模型提供全部同款参考图，按目标SKU/状态筛选商品身份、结构与颜色，其他SKU不作为生成参考输入",
            "已分析全部参考视觉；本张实际向生成模型提供全部同款参考图，按目标SKU/状态筛选商品身份、结构与颜色，其他SKU不作为生成参考输入，同款资料一致，无需裁决",
        )
        with self.assertRaises(StoryboardValidationError):
            validate_storyboard(make_storyboard([frame]))

    def test_multi_reference_prompt_requires_conflict_resolution(self) -> None:
        frame = make_frame(
            1,
            "主图-01",
            "本张实际向生成模型提供全部同款参考图，按目标SKU/状态筛选商品身份、结构与颜色，其他SKU不作为生成参考输入，同款资料一致，无需裁决",
            "本张实际向生成模型提供全部同款参考图，按目标SKU/状态筛选商品身份、结构与颜色，其他SKU不作为生成参考输入",
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

    def test_cross_model_component_transplant_is_rejected(self) -> None:
        transplant_phrases = (
            "将PX65的三接口模块装到PX45机身",
            "将PX65三接口模块移植到PX45机身",
            "将65X三接口模块换到45X机身",
            "将旗舰款接口模块移植到基础款机身",
        )
        for phrase in transplant_phrases:
            with self.subTest(phrase=phrase):
                markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
                    "完整保持商品轮廓", f"{phrase}并保持商品轮廓", 1
                )
                with self.assertRaises(StoryboardValidationError):
                    validate_storyboard(markdown)

    def test_borrowing_other_sku_parts_is_rejected(self) -> None:
        markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
            "完整保持商品轮廓", "借用其他SKU的杯盖并保持商品轮廓", 1
        )
        with self.assertRaises(StoryboardValidationError):
            validate_storyboard(markdown)

    def test_explanatory_sku_fusion_warning_is_allowed(self) -> None:
        markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
            "右侧保留短文案安全区", "右侧说明融合不同SKU会造成误购", 1
        )
        self.assertEqual(validate_storyboard(markdown), ["主图-01"])

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

    def test_global_analysis_and_single_generation_input_can_coexist(self) -> None:
        frame = make_frame(
            1,
            "主图-01",
            "已分析全部有效参考视觉；本张实际向生成模型只提供一张最清晰参考图，提取商品身份和正面几何",
            "已分析全部参考视觉后，本张实际向生成模型只提供一张最清晰参考图，提取商品身份和正面几何",
        )
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

    def test_hidden_view_inference_annotations_are_rejected(self) -> None:
        annotations = ("高置信推定", "背面：示意", "置信度92分")
        for annotation in annotations:
            with self.subTest(annotation=annotation):
                markdown = make_storyboard([make_frame(1, "主图-01")]).replace(
                    "不补画未知背面", f"背面标注为{annotation}", 1
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
