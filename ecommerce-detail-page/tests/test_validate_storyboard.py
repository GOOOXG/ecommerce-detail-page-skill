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
        frame = make_frame(1, "主图-01").replace(
            "- 画布与布局：【商品居中，占画面一半，右侧保留短文案安全区】",
            "- 画布与布局：【FAST-200扫地机居中，占画面一半，右侧保留短文案安全区】",
        )
        self.assertEqual(validate_storyboard(make_storyboard([frame])), ["主图-01"])

        unsafe = make_frame(1, "主图-01").replace(
            "- 画布与布局：【商品居中，占画面一半，右侧保留短文案安全区】",
            "- 画布与布局：【FAST-200模型组织画面，商品居中，占画面一半】",
        )
        with self.assertRaises(StoryboardValidationError):
            validate_storyboard(make_storyboard([unsafe]))

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
