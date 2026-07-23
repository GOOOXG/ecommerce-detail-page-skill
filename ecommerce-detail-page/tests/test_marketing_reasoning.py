#!/usr/bin/env python3
"""营销模型加速层的内容与路由回归测试。"""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MARKETING = ROOT / "references" / "marketing-reasoning.md"
SKILL = ROOT / "SKILL.md"
README = ROOT.parent / "README.md"


class MarketingReasoningContentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = MARKETING.read_text(encoding="utf-8")
        cls.skill_text = SKILL.read_text(encoding="utf-8")
        cls.readme_text = README.read_text(encoding="utf-8")

    def test_reference_exists_and_is_chinese_first(self) -> None:
        self.assertTrue(MARKETING.is_file())
        self.assertIn("# 营销、心理与经营推演加速层", self.text)
        self.assertIn("## 统一编译出口", self.text)
        self.assertIn("## 停止条件", self.text)

    def test_historical_and_requested_models_are_present(self) -> None:
        required_models = (
            "FABE",
            "FAB",
            "AIDA",
            "AIDMA",
            "AISAS",
            "ACCA",
            "DAGMAR",
            "PAS",
            "PASTOR",
            "BAB",
            "USP",
            "RTB",
            "EPP",
            "4U",
            "JTBD",
            "Kano",
            "MECE",
            "AIPL",
            "FAST",
            "GROW",
            "AARRR",
            "RACE",
            "人货场",
            "FOMO",
            "锚定效应",
            "消费决策心理学",
            "损失厌恶",
            "社会证明",
            "选择架构",
            "Fogg行为模型",
            "精细加工可能性模型",
            "前景理论",
            "认知流畅",
            "禀赋效应",
            "现状偏误",
            "心理账户",
            "叙事传输",
            "格式塔原则",
            "RFM",
            "CLV",
            "OODA",
            "Goodhart",
            "Cohort",
            "选品五力",
            "货盘金字塔",
            "品牌原型",
            "DTC",
            "非目标人群/不适用场景",
            "首屏截停",
            "Hook-Proof-Close",
            "Lookalike",
            "Growth Loop",
            "A/B/n",
            "WTP",
            "CAGE",
            "5W2H",
            "知识产权矩阵",
            "用户故事",
            "场景立方体",
            "人口、地理、心理、行为、场景、价值、圈层细分",
            "主图CTR",
            "详情页转化信息序",
            "价格带卡位",
            "GPM",
            "FACT/FACT+S",
            "KFS",
            "STEPS",
            "AI代理购物",
            "用户生命周期五阶段",
            "首单到二单",
            "订阅续订",
            "转化视觉技法库",
            "广告法宣传合规",
            "产品合规认证路径",
        )
        for model in required_models:
            with self.subTest(model=model):
                self.assertIn(model, self.text)

    def test_every_model_must_compile_to_image_work(self) -> None:
        for phrase in (
            "买家问题",
            "卖点/利益",
            "证据需求",
            "图片任务",
            "文案命题",
            "生产边界",
            "一个主模型",
            "最多两个辅助检查",
            "不把模型名称写入最终分镜",
            "不另建评分表",
            "不建立新的合同式接口、营销锁或独立状态机",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.text)

    def test_skill_routes_marketing_layer_without_replacing_main_flow(self) -> None:
        self.assertIn("references/marketing-reasoning.md", self.skill_text)
        self.assertIn("营销模型加速层", self.skill_text)
        self.assertIn("不改变主流程", self.skill_text)

    def test_grow_uses_one_ecommerce_growth_definition(self) -> None:
        definition = "GROW | 渗透力、复购力、价格力、延展力"
        self.assertIn(definition, self.text)
        self.assertIn("GROW（渗透力、复购力、价格力、延展力）", self.readme_text)
        self.assertNotIn("GROW | 目标—现状—选项—行动", self.text)
        self.assertEqual(self.text.count("| GROW |"), 1)

    def test_readme_contains_a_fabe_tutorial(self) -> None:
        self.assertIn("## 营销模型如何帮助 AI 更快构建分镜", self.readme_text)
        self.assertIn("FABE", self.readme_text)
        self.assertIn("AIPL", self.readme_text)
        self.assertIn("人货场", self.readme_text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
