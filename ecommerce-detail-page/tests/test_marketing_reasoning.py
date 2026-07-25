#!/usr/bin/env python3
"""分类模型调用卡总库的内容、唯一来源与流程路由回归测试。"""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MARKETING = ROOT / "references" / "marketing-reasoning.md"
SKILL = ROOT / "SKILL.md"
README = ROOT.parent / "README.md"

EXPECTED_LABELS_BY_CATEGORY: dict[str, tuple[str, ...]] = {
    "### 1. 购买路径与内容推进": (
        "AIDA、AIDMA",
        "AISAS",
        "ACCA、DAGMAR",
        "PAS、PASTOR",
        "BAB",
        "QUEST",
        "CDJ",
        "AIPL",
        "5A、4A、O-5A（按任务口径解释）",
        "RACE、See-Think-Do-Care",
        "消费者采用路径、关键时刻 ZMOT/FMOT/SMOT",
    ),
    "### 2. 卖点、定位、价值与定价": (
        "FAB、FABE",
        "USP、RTB",
        "EPP、ESP、RSP",
        "4U、4C文案",
        "3C定位",
        "价值主张画布、JTBD",
        "Kano",
        "MECE、金字塔原则",
        "4P、4C营销、7P",
        "WTP/支付意愿、价格弹性",
        "捆绑定价、价格带、价值阶梯",
        "蓝海战略画布",
        "RATER服务质量、服务蓝图",
    ),
    "### 3. 消费心理与选择架构": (
        "消费决策心理学综合链",
        "FOMO/错失恐惧、稀缺与时效",
        "锚定效应",
        "框架效应、前景理论、损失厌恶",
        "认知流畅、认知负荷理论、双系统理论",
        "精细加工可能性模型",
        "峰终定律",
        "蔡格尼克效应、信息觅食/信息气味",
        "首因、近因、序位效应",
        "冯·雷斯托夫效应、格式塔原则",
        "社会证明、权威原则、信号理论",
        "互惠、承诺一致",
        "禀赋效应、具身认知",
        "风险逆转",
        "Fogg行为模型、COM-B、EAST",
        "认知失调、现状偏误、默认效应",
        "心理账户、支付痛苦",
        "折中效应、诱饵效应、选择悖论、选择架构",
        "目标梯度、心理距离/解释水平",
    ),
    "### 4. 人群、场景、生命周期与关系": (
        "人货场",
        "STP",
        "人口、地理、心理、行为、场景、价值、圈层细分",
        "Persona、用户故事、同理心地图",
        "场景立方体",
        "非目标人群/不适用场景/排除人群",
        "RFM、RFMTC",
        "CLV/LTV、NPS",
        "用户生命周期五阶段",
        "首单到二单、补货周期、订阅续订、流失原因树、服务补救",
        "相似人群 Lookalike、人群迁移",
        "KOC/UGC、DTC社区飞轮、品牌社区与会员关系",
    ),
    "### 5. 平台、渠道与成交路由": (
        "货架销售、搜索词包",
        "履约与服务链、以旧换新",
        "内容销售、直播销售、社交销售",
        "MEDDIC、SPIN、Gap Selling、LAER",
        "GPM、FACT/FACT+S",
        "KFS、笔记漏斗、搜索词与内容词包",
        "STEPS、关系链、私域四阵地",
        "DEEPLINK、ONE-ID、公域—私域—品牌域",
        "Amazon Listing SEO、FBA、PPC、A+、Review、订阅购",
        "独立站/DTC漏斗、Email/SMS生命周期、Affiliate、订阅",
        "地理便利、小时达、门店/即时零售路由",
        "AI代理购物、结构化商品信息、内容智能、个性化引擎、预测性营销、AI归因",
    ),
    "### 6. 增长、经营、实验与复盘": (
        "AARRR、RARRA",
        "FAST",
        "GROW",
        "增长循环 Growth Loop、内容循环 Content Loop、付费循环 Paid Loop、病毒循环、K因子",
        "北极星指标、输入指标、护栏指标",
        "漏斗、路径、留存、指标树",
        "CRO",
        "A/B/n、多臂老虎机、Lift Test、因果推断",
        "OODA、PDCA",
        "Goodhart定律",
        "Cohort、归因",
        "VOC文本分析",
        "PMF、CMF、IMF",
        "选品五力、单位经济",
        "货盘金字塔、SKU精简/长尾平衡",
        "单品—爆品—品类—品牌成长",
        "电商全链路",
        "详情页转化信息序",
        "主图CTR与三秒信息效率",
        "计划—单元—创意、素材工厂",
        "边际ROI",
    ),
    "### 7. 产品、创意、体验与画面转译": (
        "双钻、设计思维",
        "Opportunity Solution Tree",
        "Story Mapping、旅程地图",
        "Acceptance Criteria",
        "TRIZ、创新十类",
        "Stage-Gate",
        "情感化设计三层",
        "内容4E",
        "叙事传输、消费仪式",
        "Campaign Brief、Creative Brief",
        "Message Hierarchy、Hook-Proof-Close",
        "Content Architecture、模块化资产策略",
        "隐喻思维、符号学、视觉修辞",
        "可供性、行为线索",
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
        "创意视觉：截停与相关性",
        "创意视觉：感官体验",
        "创意视觉：场景延展",
        "创意视觉：差异比较",
        "创意视觉：信任与价值",
        "创意视觉：行动与兜底",
    ),
    "### 8. 品牌、行业、合规与全球化": (
        "定位理论、品类心智阶梯、How Brands Grow",
        "品牌资产、CBBE",
        "品牌棱镜",
        "独特性资产、视觉独特资产、品牌符号",
        "品牌原型、品牌人格、奢侈品梦想方程",
        "PEST/PESTEL",
        "波特五力",
        "SWOT",
        "BCG、Ansoff",
        "CAGE",
        "EPRG",
        "国潮/文化符号与内容本地化",
        "ESG、LCA、绿色供应链",
        "知识产权矩阵",
        "广告法宣传合规、平台责任",
        "产品合规认证路径",
        "危机沟通3T",
    ),
    "### 9. 证据、根因、优先级与不确定性": (
        "5Why、逻辑树",
        "5W2H",
        "鱼骨图",
        "决策矩阵、MoSCoW",
        "ICE、RICE、PIE",
        "事前验尸 Pre-Mortem、FMEA",
        "二阶思维",
        "奥卡姆剃刀",
        "Cynefin",
        "情景规划",
        "六顶思考帽",
        "贝叶斯更新",
        "证据链、信任状组合",
    ),
}


class MarketingReasoningContentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = MARKETING.read_text(encoding="utf-8")
        cls.skill_text = SKILL.read_text(encoding="utf-8")
        cls.readme_text = README.read_text(encoding="utf-8")
        start = cls.text.index("## 分类模型调用卡总库")
        end = cls.text.index("## 调用组合与停止", start)
        cls.library = cls.text[start:end]

    def test_reference_is_chinese_first_and_has_one_library(self) -> None:
        self.assertTrue(MARKETING.is_file())
        self.assertIn("# 营销、心理与经营推演加速层", self.text)
        self.assertEqual(self.text.count("## 分类模型调用卡总库"), 1)
        self.assertIn("## 统一调用卡与编译出口", self.text)
        self.assertIn("## 调用组合与停止", self.text)

    def test_all_model_types_are_grouped_in_nine_categories(self) -> None:
        categories = tuple(EXPECTED_LABELS_BY_CATEGORY)
        headings = [
            line for line in self.library.splitlines() if line.startswith("### ")
        ]
        self.assertEqual(headings, list(categories))

        lines = self.library.splitlines()
        for position, category in enumerate(categories):
            start = lines.index(category)
            end = (
                lines.index(categories[position + 1])
                if position + 1 < len(categories)
                else len(lines)
            )
            labels = tuple(
                line.split("**", 2)[1]
                for line in lines[start + 1 : end]
                if line.startswith("| **")
            )
            with self.subTest(category=category):
                self.assertEqual(labels, EXPECTED_LABELS_BY_CATEGORY[category])

    @staticmethod
    def required_model_markers() -> tuple[str, ...]:
        return (
            "FAB",
            "FABE",
            "AIDA",
            "AIDMA",
            "AISAS",
            "ACCA",
            "DAGMAR",
            "PAS",
            "PASTOR",
            "BAB",
            "QUEST",
            "CDJ",
            "AIPL",
            "5A",
            "RACE",
            "消费者采用路径",
            "USP",
            "RTB",
            "EPP",
            "ESP",
            "RSP",
            "4U",
            "JTBD",
            "Kano",
            "MECE",
            "WTP",
            "服务蓝图",
            "FOMO",
            "锚定效应",
            "消费决策心理学",
            "损失厌恶",
            "社会证明",
            "选择架构",
            "Fogg行为模型",
            "COM-B",
            "精细加工可能性模型",
            "前景理论",
            "认知流畅",
            "认知负荷理论",
            "禀赋效应",
            "现状偏误",
            "心理账户",
            "格式塔原则",
            "人货场",
            "STP",
            "用户故事",
            "场景立方体",
            "非目标人群/不适用场景/排除人群",
            "RFM",
            "CLV",
            "NPS",
            "用户生命周期五阶段",
            "首单到二单",
            "订阅续订",
            "Lookalike",
            "KOC/UGC",
            "FAST",
            "GROW",
            "MEDDIC",
            "SPIN",
            "GPM",
            "FACT/FACT+S",
            "KFS",
            "STEPS",
            "DEEPLINK",
            "ONE-ID",
            "AI代理购物",
            "AARRR",
            "Growth Loop",
            "A/B/n",
            "OODA",
            "Goodhart",
            "Cohort",
            "VOC",
            "PMF",
            "选品五力",
            "货盘金字塔",
            "捆绑定价",
            "价值阶梯",
            "详情页转化信息序",
            "主图CTR",
            "双钻",
            "Opportunity Solution Tree",
            "Story Mapping",
            "Acceptance Criteria",
            "TRIZ",
            "Stage-Gate",
            "内容4E",
            "叙事传输",
            "Hook-Proof-Close",
            "Content Architecture",
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
            "创意视觉：截停与相关性",
            "创意视觉：感官体验",
            "创意视觉：场景延展",
            "创意视觉：差异比较",
            "创意视觉：信任与价值",
            "创意视觉：行动与兜底",
            "履约与服务链",
            "以旧换新",
            "笔记漏斗",
            "内容词包",
            "私域四阵地",
            "DTC漏斗",
            "地理便利",
            "小时达",
            "人群迁移",
            "DTC社区飞轮",
            "国潮/文化符号",
            "How Brands Grow",
            "CBBE",
            "品牌棱镜",
            "PESTEL",
            "波特五力",
            "SWOT",
            "BCG",
            "Ansoff",
            "CAGE",
            "EPRG",
            "ESG",
            "LCA",
            "知识产权矩阵",
            "广告法宣传合规",
            "产品合规认证路径",
            "危机沟通3T",
            "5Why",
            "5W2H",
            "鱼骨图",
            "决策矩阵",
            "ICE",
            "RICE",
            "PIE",
            "Pre-Mortem",
            "FMEA",
            "Cynefin",
            "六顶思考帽",
            "贝叶斯更新",
        )

    def test_historical_requested_and_extended_models_are_inside_library(self) -> None:
        card_text = "\n".join(
            line for line in self.library.splitlines() if line.startswith("| **")
        )
        for model in self.required_model_markers():
            with self.subTest(model=model):
                self.assertIn(model, card_text)

    def test_every_model_family_uses_the_same_call_card_shape(self) -> None:
        lines = self.library.splitlines()
        category_indexes = [
            index for index, line in enumerate(lines) if line.startswith("### ")
        ]
        rows: list[str] = []
        expected_header = (
            "| 模型/模型簇与口径 | 触发问题与所需输入 | 阶段动作与图片落点 | "
            "可用证据与不可推导 | 降级路径与停止条件 |"
        )
        expected_separator = "|---|---|---|---|---|"
        for position, start in enumerate(category_indexes):
            end = (
                category_indexes[position + 1]
                if position + 1 < len(category_indexes)
                else len(lines)
            )
            category = lines[start]
            table_lines = [line for line in lines[start + 1 : end] if line.startswith("|")]
            with self.subTest(category=category):
                self.assertGreaterEqual(len(table_lines), 3, "每个类别至少包含一张调用卡")
                self.assertEqual(table_lines[0], expected_header)
                self.assertEqual(table_lines[1], expected_separator)
                self.assertEqual(table_lines.count(expected_header), 1)
                self.assertEqual(table_lines.count(expected_separator), 1)
                self.assertTrue(
                    all(line.startswith("| **") for line in table_lines[2:]),
                    "类别中的每个模型定义都必须使用统一调用卡行",
                )
            rows.extend(table_lines[2:])
        self.assertGreaterEqual(len(rows), 80)
        labels: list[str] = []
        for row in rows:
            with self.subTest(row=row[:80]):
                self.assertEqual(row.count("|"), 6)
                cells = [cell.strip() for cell in row.strip("|").split("|")]
                self.assertEqual(len(cells), 5)
                self.assertTrue(all(cells))
                self.assertTrue(
                    any(
                        term in cells[-1]
                        for term in (
                            "停止",
                            "不加载",
                            "删除",
                            "不分层",
                            "止于",
                            "退回",
                            "合并",
                        )
                    ),
                    "最后一栏必须同时给出降级或停止语义",
                )
            labels.append(row.split("|", 2)[1].strip())
        self.assertEqual(len(labels), len(set(labels)))

    def test_call_card_fields_compile_only_to_existing_storyboard_work(self) -> None:
        for phrase in (
            "模型/模型簇与口径",
            "触发问题与所需输入",
            "阶段动作与图片落点",
            "可用证据与不可推导",
            "降级路径与停止条件",
            "商品事实 → 买家任务 → 主要阻力/动机",
            "图片任务 → 文案命题 → 生产边界 → 成功标准",
            "不得泄露内部方法论名称、类别名、调用卡、内部评分或推演过程",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.text)

    def test_old_scattered_model_sections_are_removed(self) -> None:
        old_headings = (
            "## 模型调用卡：从触发到分镜",
            "## 模型选择规则",
            "## 购买路径与内容推进模型",
            "## 图片转化框架",
            "## 卖点、定位与价值表达模型",
            "## 消费者心理与选择架构",
            "## 人群、平台与人货场模型",
            "## 增长、经营与复盘模型",
            "## 补充模型：仅在能改变图片任务时启用",
            "## 产品、创意与体验模型",
            "## 品牌、行业与长期价值模型",
            "## FABE完整编译示例",
        )
        for heading in old_headings:
            with self.subTest(heading=heading):
                self.assertNotIn(heading, self.text)

    def test_model_definitions_cannot_escape_the_single_library(self) -> None:
        start = self.text.index("## 分类模型调用卡总库")
        end = self.text.index("## 调用组合与停止", start)
        outside = self.text[:start] + self.text[end:]

        self.assertNotIn(
            "| 模型/模型簇与口径 | 触发问题与所需输入 | 阶段动作与图片落点 | "
            "可用证据与不可推导 | 降级路径与停止条件 |",
            outside,
        )
        self.assertFalse(
            any(line.startswith("| **") for line in outside.splitlines()),
            "规范调用卡不得出现在唯一总库区段之外",
        )
        for category, labels in EXPECTED_LABELS_BY_CATEGORY.items():
            for label in labels:
                with self.subTest(category=category, label=label):
                    self.assertNotIn(label, outside)
        for name in self.required_model_markers():
            with self.subTest(name=name):
                self.assertNotIn(name, outside)

    def test_fast_and_grow_have_one_explicit_ecommerce_definition(self) -> None:
        self.assertEqual(self.library.count("**FAST**"), 1)
        self.assertEqual(self.library.count("**GROW**"), 1)
        self.assertIn("人群总量、转化、高价值、活跃", self.library)
        self.assertIn("渗透力、复购力、价格力、延展力", self.library)
        self.assertIn("用户或平台明确定义优先", self.library)
        self.assertIn("不与教练式同名框架混用", self.library)

    def test_ambiguous_and_cross_market_models_keep_distinct_meanings(self) -> None:
        self.assertIn("5A、4A、O-5A（按任务口径解释）", self.library)
        self.assertIn("可接受、可负担、可获得、可知晓", self.library)
        self.assertIn("同名4A不能混用", self.library)
        self.assertIn("容易、吸引、社会与适时", self.library)
        self.assertEqual(self.library.count("| **CAGE** |"), 1)
        self.assertEqual(self.library.count("| **EPRG** |"), 1)
        self.assertEqual(
            self.library.count("| **国潮/文化符号与内容本地化** |"),
            1,
        )
        self.assertNotIn("**CAGE、EPRG、", self.library)
        self.assertIn("真实商品名称、型号、认证和可见原文仍按商品证据保留", self.text)

    def test_platform_and_growth_cards_have_clear_ownership(self) -> None:
        platform_start = self.library.index("### 5. 平台、渠道与成交路由")
        growth_start = self.library.index("### 6. 增长、经营、实验与复盘")
        product_start = self.library.index("### 7. 产品、创意、体验与画面转译")
        platform = self.library[platform_start:growth_start]
        growth = self.library[growth_start:product_start]

        self.assertNotIn("**FAST**", platform)
        self.assertNotIn("**GROW**", platform)
        self.assertIn("**FAST**", growth)
        self.assertIn("**GROW**", growth)
        self.assertIn("**KFS、笔记漏斗、搜索词与内容词包**", platform)
        self.assertIn("**STEPS、关系链、私域四阵地**", platform)
        self.assertNotIn("**KFS、STEPS**", self.library)
        self.assertEqual(
            self.library.count("**捆绑定价、价格带、价值阶梯**"),
            1,
        )
        self.assertNotIn("价格带卡位", self.library)

    def test_historical_visual_and_channel_capabilities_are_preserved(self) -> None:
        visual_capabilities = (
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
            "认知反差",
            "强对比",
            "隐性问题可视化",
            "圈层语境",
            "悬念线索",
            "情绪共鸣",
            "剖面透视",
            "流体/阻尼定格",
            "解压瞬间",
            "五感联想",
            "微观放大",
            "悬浮展示",
            "全天候/全空间",
            "第一视角",
            "特殊使用情境",
            "独处/办公/户外",
            "生态搭配",
            "结构并列",
            "匿名方案对比",
            "信息清单",
            "盲测/雷达式数据",
            "缺口图鉴",
            "证据链",
            "研发/工艺过程",
            "真实用户体验",
            "第三方测试",
            "比例参照",
            "生命周期解释",
            "真实限时",
            "阶梯权益",
            "默认推荐",
            "轻量行动阶梯",
            "顾虑分层",
            "期望值管理",
            "开箱/交付",
        )
        channel_capabilities = (
            "履约与服务链",
            "以旧换新",
            "笔记漏斗",
            "搜索词与内容词包",
            "私域四阵地",
            "DTC漏斗",
            "地理便利",
            "小时达",
            "人群迁移",
            "DTC社区飞轮",
            "国潮/文化符号",
        )
        for capability in visual_capabilities + channel_capabilities:
            with self.subTest(capability=capability):
                self.assertIn(capability, self.library)

    def test_combination_is_open_but_stops_without_image_value(self) -> None:
        for phrase in (
            "分类是检索路由，不是能力上限",
            "最小非重复组合",
            "不设固定模型数量",
            "新调用没有新增买家问题、证据、选择帮助、场景理解、生产可行性或风险降低",
            "不另建营销评分表",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.text)
        for obsolete_limit in (
            "最多两个辅助检查",
            "同一阶段通常不超过3个模型",
            "1个主模型",
        ):
            self.assertNotIn(obsolete_limit, self.text)

    def test_skill_routes_library_without_replacing_main_flow(self) -> None:
        expected_flow = (
            "识别商品主体 → AI预构建 → 编号建议/手动纠正 → 商品卡（待确认） → "
            "用户确认或明确直出授权 → 已确认商品卡 → 首要目标/风险/工具能力画像 → "
            "设计需求预判与输出范围 → 自适应多图结构与综合方向 → 图组编排 → "
            "逐图确认/内部自动复核 → 最终分镜 → 可选生图与结果反馈"
        )
        self.assertIn(expected_flow, self.skill_text)
        light_call = self.skill_text.index("执行`AI预构建`阶段路由")
        formal_call = self.skill_text.index("在商品卡确认且首要目标已明确后")
        output_scope = self.skill_text.index("### 6. 需求预判与输出范围")
        self.assertLess(light_call, formal_call)
        self.assertLess(formal_call, output_scope)
        routed = self.skill_text[formal_call:output_scope]
        self.assertIn("`模型_…`类别特征", routed)
        self.assertIn("不改变主流程", routed)
        self.assertIn("不设固定模型数量", routed)
        self.assertNotIn("最多两个辅助检查", routed)
        self.assertIn("config/context-routing.json", self.skill_text)
        self.assertIn("scripts/route_context.py", self.skill_text)

    def test_readme_is_a_tutorial_not_a_second_model_catalog(self) -> None:
        self.assertIn("## 分类模型调用卡总库：使用教程", self.readme_text)
        self.assertIn(
            "ecommerce-detail-page/references/marketing-reasoning.md",
            self.readme_text,
        )
        self.assertIn("不要求用户选择模型", self.readme_text)
        self.assertIn("不增加主流程步骤", self.readme_text)
        self.assertNotIn("### FABE：", self.readme_text)
        self.assertNotIn("### 不同模型怎样转成图片任务", self.readme_text)
        self.assertNotIn("### 模型调用卡：让模型真正参与构图", self.readme_text)

    def test_named_model_knowledge_is_not_redefined_in_other_markdown(self) -> None:
        markdown_files = [README, SKILL]
        markdown_files.extend(
            path
            for path in (ROOT / "references").glob("*.md")
            if path != MARKETING
        )
        for path in markdown_files:
            content = path.read_text(encoding="utf-8")
            for name in self.required_model_markers():
                with self.subTest(path=path.name, name=name):
                    self.assertNotIn(name, content)


if __name__ == "__main__":
    unittest.main(verbosity=2)
