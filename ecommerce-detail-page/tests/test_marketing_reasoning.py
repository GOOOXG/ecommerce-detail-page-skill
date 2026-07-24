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

    def test_requested_models_have_actionable_call_cards(self) -> None:
        start = self.text.index("## 模型调用卡：从触发到分镜")
        end = self.text.index("## 模型选择规则", start)
        call_cards = self.text[start:end]
        for phrase in (
            "触发问题",
            "所需输入",
            "阶段动作",
            "对象/图型",
            "可用证据",
            "不可推导",
            "降级路径",
            "停止条件",
        ):
            with self.subTest(field=phrase):
                self.assertIn(phrase, call_cards)
        rows = {}
        for line in call_cards.splitlines():
            if not line.startswith("| **") or line.count("|") < 4:
                continue
            label = line.split("|", 2)[1].strip().strip("*")
            rows[label] = line

        # 每个指定模型都必须在自己的表格行内同时留下专属阶段、图片动作、
        # 输入/证据边界和停止或降级语义，不能靠其他行的词汇让测试通过。
        expectations = {
            "AIPL": ("认知", "兴趣", "购买", "忠诚", "主图", "证据", "停止"),
            "FAST": ("人群总量", "转化", "高价值", "活跃", "入口", "数据", "停止"),
            "GROW": ("渗透力", "复购力", "价格力", "延展力", "品类教育", "资料", "停止"),
            "人货场": ("动作", "尺度", "道具", "商品事实", "刻板印象", "停止"),
            "AARRR": ("获客", "激活", "留存", "收入", "推荐", "证据", "停止"),
            "FOMO/错失恐惧": ("截止时间", "库存", "预约窗口", "真实时点", "资料", "删除"),
            "锚定效应": ("尺寸", "容量", "套装", "使用寿命", "原价", "证据", "停止"),
            "消费决策心理学（综合链）": ("注意", "理解", "信任", "选择", "行动", "证据", "停止"),
        }
        self.assertEqual(set(rows), set(expectations))
        for model, required_terms in expectations.items():
            row = rows[model]
            with self.subTest(model=model):
                for term in required_terms:
                    self.assertIn(term, row)

    def test_fast_and_grow_definition_priority_is_explicit(self) -> None:
        self.assertIn("FAST 与 GROW 在不同平台可能有不同释义", self.text)
        self.assertIn("用户/平台资料优先", self.text)
        self.assertIn("本文件固定采用“渗透力—复购力—价格力—延展力”", self.text)

    def test_psychology_chain_is_mapped_without_manipulation(self) -> None:
        for phrase in (
            "注意 → 理解 → 信任 → 选择 → 行动 → 复购/推荐",
            "不制造虚假稀缺",
            "不虚构原价",
            "不把心理推断当作用户事实",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.text)

    def test_skill_routes_marketing_layer_without_replacing_main_flow(self) -> None:
        expected_flow = (
            "识别商品主体 → AI预构建 → 编号建议/手动纠正 → 商品卡（待确认） → "
            "用户确认或明确直出授权 → 已确认商品卡 → 首要目标/风险/工具能力画像 → "
            "设计需求预判与输出范围 → 自适应多图结构与综合方向 → 图组编排 → "
            "逐图确认/内部自动复核 → 最终分镜 → 可选生图与结果反馈"
        )
        self.assertIn(expected_flow, self.skill_text)
        light_call = self.skill_text.index("可轻量读取 [marketing-reasoning.md]")
        formal_call = self.skill_text.index("在商品卡确认且首要目标已明确后")
        output_scope = self.skill_text.index("### 6. 需求预判与输出范围")
        self.assertLess(light_call, formal_call)
        self.assertLess(formal_call, output_scope)
        self.assertIn("不改变主流程", self.skill_text[formal_call:output_scope])

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

    def test_readme_contains_model_call_card_tutorial(self) -> None:
        self.assertIn("### 模型调用卡：让模型真正参与构图", self.readme_text)
        for phrase in ("FAST", "GROW", "AARRR", "FOMO", "锚定效应", "停止条件"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.readme_text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
