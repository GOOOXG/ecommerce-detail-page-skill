from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = SKILL_ROOT / "scripts" / "route_context.py"
CONFIG_PATH = SKILL_ROOT / "config" / "context-routing.json"
EXPECTED_STAGES = {
    "主体识别",
    "AI预构建",
    "编号与商品卡",
    "目标与范围",
    "结构与方向",
    "图组规划",
    "分镜编译",
    "质检交付",
    "生图返修",
}
EXPECTED_OUTPUT_FEATURES = {
    "输出_主图",
    "输出_SKU图",
    "输出_详情页",
    "输出_海报",
    "输出_白底图",
    "输出_透明图",
    "输出_无字场景图",
}
EXPECTED_IMAGE_TYPE_FEATURES = {
    "图型_商品标准呈现",
    "图型_结构拆解",
    "图型_细节质感",
    "图型_功能验证",
    "图型_参照认知",
    "图型_选择适配与防错",
    "图型_使用教学与维护",
    "图型_场景呈现",
    "图型_创意视觉",
    "图型_组合包装与到手",
    "图型_信任背书与来源",
    "图型_利益与行动",
    "图型_数字权益与服务交付",
}
EXPECTED_MARKETING_FEATURES = {
    "模型_购买路径与内容推进",
    "模型_卖点定位价值与定价",
    "模型_消费心理与选择架构",
    "模型_人群场景生命周期与关系",
    "模型_平台渠道与成交路由",
    "模型_增长经营实验与复盘",
    "模型_产品创意体验与画面转译",
    "模型_品牌行业合规与全球化",
    "模型_证据根因优先级与不确定性",
}


def load_router():
    spec = importlib.util.spec_from_file_location("route_context", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载上下文路由脚本")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ContextRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.router = load_router()
        cls.policy = cls.router.load_policy(CONFIG_PATH)

    def section_keys(self, result):
        return {
            (item["文件"], item["章节"])
            for item in result["读取章节"]
        }

    def test_simple_recognition_does_not_load_heavy_libraries(self):
        result = self.router.resolve_context("主体识别", [], self.policy)
        files = {item["文件"] for item in result["读取章节"]}

        self.assertIn("references/product-and-reference.md", files)
        self.assertNotIn("references/marketing-reasoning.md", files)
        self.assertNotIn("references/image-set-planning.md", files)

    def test_image_planning_only_loads_selected_output_and_image_type(self):
        result = self.router.resolve_context(
            "图组规划",
            ["输出_主图", "图型_场景呈现"],
            self.policy,
        )
        sections = self.section_keys(result)

        self.assertIn(("references/output-objects.md", "## 主图"), sections)
        self.assertNotIn(("references/output-objects.md", "## SKU图"), sections)
        self.assertIn(
            ("references/image-set-planning.md", "### 八、场景呈现类"),
            sections,
        )
        self.assertNotIn(
            ("references/image-set-planning.md", "### 九、创意视觉类"),
            sections,
        )

    def test_marketing_route_loads_shared_rules_and_only_one_category(self):
        result = self.router.resolve_context(
            "目标与范围",
            ["模型_消费心理与选择架构"],
            self.policy,
        )
        sections = self.section_keys(result)

        self.assertIn(
            ("references/marketing-reasoning.md", "## 统一调用卡与编译出口"),
            sections,
        )
        self.assertIn(
            ("references/marketing-reasoning.md", "### 3. 消费心理与选择架构"),
            sections,
        )
        self.assertNotIn(
            ("references/marketing-reasoning.md", "### 2. 卖点、定位、价值与定价"),
            sections,
        )

    def test_storyboard_compilation_loads_smart_copy_compiler(self):
        result = self.router.resolve_context("分镜编译", [], self.policy)
        sections = self.section_keys(result)

        self.assertIn(
            ("references/prompt-writing.md", "## 智能卖点文案编译"),
            sections,
        )

    def test_unknown_feature_never_falls_back_to_full_files(self):
        with self.assertRaises(self.router.RoutingError):
            self.router.resolve_context("图组规划", ["图型_不存在"], self.policy)

    def test_known_and_unknown_features_fail_as_one_request(self):
        with self.assertRaises(self.router.RoutingError):
            self.router.resolve_context(
                "图组规划",
                ["输出_主图", "图型_不存在"],
                self.policy,
            )

    def test_stage_and_feature_keys_require_exact_match(self):
        with self.assertRaises(self.router.RoutingError):
            self.router.resolve_context(" 主体识别", [], self.policy)
        with self.assertRaises(self.router.RoutingError):
            self.router.resolve_context("图组规划", [" 输出_主图"], self.policy)

    def test_repeated_features_and_sections_are_stably_deduplicated(self):
        first = self.router.resolve_context(
            "图组规划",
            ["输出_主图", "输出_主图", "图型_场景呈现"],
            self.policy,
        )
        second = self.router.resolve_context(
            "图组规划",
            ["输出_主图", "输出_主图", "图型_场景呈现"],
            self.policy,
        )

        self.assertEqual(first, second)
        self.assertEqual(
            len(first["读取章节"]),
            len(self.section_keys(first)),
        )
        self.assertEqual(
            ["输出_主图", "图型_场景呈现"],
            first["命中特征"],
        )

    def test_policy_contains_routes_not_model_definitions(self):
        raw = CONFIG_PATH.read_text(encoding="utf-8")
        policy = json.loads(raw)
        marketing = (SKILL_ROOT / "references" / "marketing-reasoning.md").read_text(
            encoding="utf-8"
        )
        model_labels = re.findall(r"^\| \*\*(.+?)\*\* \|", marketing, re.MULTILINE)

        self.assertEqual(1, policy["配置版本"])
        self.assertNotIn("| **", raw)
        self.assertGreaterEqual(len(model_labels), 148)
        for label in model_labels:
            with self.subTest(label=label):
                self.assertNotIn(label, raw)
        self.assertFalse(policy["读取策略"]["允许整文件回退"])
        self.assertFalse(policy["读取策略"]["允许整库回退"])

    def test_policy_covers_all_runtime_stages_and_feature_families(self):
        self.assertEqual(EXPECTED_STAGES, set(self.policy["阶段路由"]))
        regular = set(self.policy["特征路由"])
        marketing = set(self.policy["营销类别路由"]["类别"])

        self.assertTrue(EXPECTED_OUTPUT_FEATURES <= regular)
        self.assertTrue(EXPECTED_IMAGE_TYPE_FEATURES <= regular)
        self.assertEqual(EXPECTED_MARKETING_FEATURES, marketing)

    def test_policy_routes_every_reference_file_without_whole_file_entries(self):
        configured = set()
        groups = list(self.policy["阶段路由"].values())
        groups.extend(self.policy["特征路由"].values())
        groups.extend(self.policy["营销类别路由"]["类别"].values())
        groups.append(self.policy["营销类别路由"]["共用前置"])
        groups.append(self.policy["营销类别路由"]["共用收尾"])
        for entries in groups:
            for entry in entries:
                configured.add(entry["文件"])
                self.assertTrue(entry["章节"])
                self.assertTrue(all(heading.startswith("#") for heading in entry["章节"]))

        actual = {
            path.relative_to(SKILL_ROOT).as_posix()
            for path in (SKILL_ROOT / "references").glob("*.md")
        }
        self.assertEqual(actual, configured)

    def test_policy_validation_reads_each_reference_only_once(self):
        reads = []
        original_read = self.router._read_utf8

        def tracked_read(path):
            reads.append(Path(path).resolve())
            return original_read(path)

        with patch.object(self.router, "_read_utf8", side_effect=tracked_read):
            self.router.validate_policy(deepcopy(self.policy))

        markdown_reads = [path for path in reads if path.suffix.lower() == ".md"]
        self.assertEqual(len(set(markdown_reads)), len(markdown_reads))

    def test_every_stage_includes_non_skippable_first_checks(self):
        for stage in EXPECTED_STAGES:
            with self.subTest(stage=stage):
                result = self.router.resolve_context(stage, [], self.policy)
                ids = {item["编号"] for item in result["强制检查"]}
                self.assertTrue({"P01", "P02", "P03", "P04"} <= ids)

        delivery = self.router.resolve_context("质检交付", [], self.policy)
        self.assertTrue(
            {"P01", "P02", "P03", "P04", "P12"}
            <= {item["编号"] for item in delivery["强制检查"]}
        )

    def test_policy_cannot_disable_mandatory_stage_checks(self):
        broken = deepcopy(self.policy)
        broken["阶段检查"] = {
            stage: ["生图"]
            for stage in broken["阶段检查"]
        }

        with self.assertRaisesRegex(self.router.RoutingError, "不可关闭"):
            self.router.validate_policy(broken)

    def test_prebuild_requires_conflict_convergence_but_not_product_card_confirmation(self):
        prebuild = self.router.resolve_context("AI预构建", [], self.policy)
        ids = {item["编号"] for item in prebuild["强制检查"]}

        self.assertIn("P05", ids)
        self.assertNotIn("P06", ids)

    def test_checks_are_attached_to_the_stage_that_can_complete_them(self):
        target = {
            item["编号"]
            for item in self.router.resolve_context("目标与范围", [], self.policy)[
                "强制检查"
            ]
        }
        direction = {
            item["编号"]
            for item in self.router.resolve_context("结构与方向", [], self.policy)[
                "强制检查"
            ]
        }
        planning = {
            item["编号"]
            for item in self.router.resolve_context("图组规划", [], self.policy)[
                "强制检查"
            ]
        }

        self.assertIn("P10", target)
        self.assertNotIn("P11", target)
        self.assertIn("P10", direction)
        self.assertNotIn("P11", direction)
        self.assertTrue({"P10", "P11"} <= planning)

    def test_extract_context_returns_selected_sections_without_adjacent_leakage(self):
        result = self.router.resolve_context("图组规划", ["输出_主图"], self.policy)
        extracted = self.router.extract_context(result)

        self.assertIn("## 主图", extracted)
        self.assertNotIn("## SKU图", extracted)
        self.assertNotIn("### 九、创意视觉类", extracted)

    def test_extracted_context_does_not_repeat_nested_sections(self):
        planning = self.router.extract_context(
            self.router.resolve_context("图组规划", [], self.policy)
        )
        enhanced = self.router.extract_context(
            self.router.resolve_context(
                "图组规划",
                ["复杂任务或子智能体"],
                self.policy,
            )
        )

        self.assertEqual(1, planning.count("### 当前图的 0–9 操作"))
        self.assertEqual(1, enhanced.count("### 按问题增配的专业角色"))

    def test_storyboard_compilation_includes_the_executable_single_image_template(self):
        extracted = self.router.extract_context(
            self.router.resolve_context("分镜编译", [], self.policy)
        )

        self.assertIn("## 第1张（主图-01）：【填写：成图名称】", extracted)
        self.assertIn("**图片任务**", extracted)
        self.assertIn("🎨 图生图提示词", extracted)
        self.assertIn("⚠️ 动态负面提示词", extracted)

    def test_markdown_extractor_ignores_fenced_code_headings(self):
        markdown = """# 根\n\n## 目标\n保留\n\n```md\n## 伪标题\n```\n\n## 下一节\n不保留\n"""

        section = self.router.extract_markdown_section(markdown, "## 目标")
        self.assertIn("## 伪标题", section)
        self.assertNotIn("## 下一节", section)
        with self.assertRaises(self.router.RoutingError):
            self.router.extract_markdown_section(markdown, "## 伪标题")

    def test_fence_like_code_content_does_not_close_the_fenced_block(self):
        markdown = """## 目标\n```md\n```不是结束围栏\n## 围栏内标题\n```\n\n## 下一节\n不保留\n"""

        section = self.router.extract_markdown_section(markdown, "## 目标")
        self.assertIn("## 围栏内标题", section)
        self.assertNotIn("## 下一节", section)
        with self.assertRaises(self.router.RoutingError):
            self.router.extract_markdown_section(markdown, "## 围栏内标题")

    def test_duplicate_real_headings_are_rejected(self):
        markdown = "## 重复\n第一段\n\n## 重复\n第二段\n"
        with self.assertRaises(self.router.RoutingError):
            self.router.extract_markdown_section(markdown, "## 重复")

    def test_invalid_target_path_or_heading_is_rejected_when_loading_policy(self):
        for mutation in ("path", "heading"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temp_dir:
                broken = deepcopy(self.policy)
                target = broken["阶段路由"]["主体识别"][0]
                if mutation == "path":
                    target["文件"] = "../README.md"
                else:
                    target["章节"][0] = "## 不存在的章节"
                path = Path(temp_dir) / "broken.json"
                path.write_text(json.dumps(broken, ensure_ascii=False), encoding="utf-8")

                with self.assertRaises(self.router.RoutingError):
                    self.router.load_policy(path)

    def test_cli_lists_routes_and_returns_json_plan(self):
        listed = subprocess.run(
            ["python", "-B", "-X", "utf8", str(SCRIPT_PATH), "--列出"],
            cwd=SKILL_ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        planned = subprocess.run(
            [
                "python",
                "-B",
                "-X",
                "utf8",
                str(SCRIPT_PATH),
                "--阶段",
                "图组规划",
                "--特征",
                "输出_主图",
                "--格式",
                "json",
            ],
            cwd=SKILL_ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        self.assertEqual(0, listed.returncode, listed.stderr)
        self.assertIn("主体识别", listed.stdout)
        self.assertIn("输出_主图", listed.stdout)
        self.assertEqual(0, planned.returncode, planned.stderr)
        self.assertEqual("图组规划", json.loads(planned.stdout)["阶段"])

    def test_cli_unknown_key_fails_without_partial_route_output(self):
        completed = subprocess.run(
            [
                "python",
                "-B",
                "-X",
                "utf8",
                str(SCRIPT_PATH),
                "--阶段",
                "图组规划",
                "--特征",
                "输出_主图",
                "图型_不存在",
            ],
            cwd=SKILL_ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        self.assertEqual(2, completed.returncode)
        self.assertIn("未知特征", completed.stderr)
        self.assertNotIn("references/output-objects.md", completed.stdout)


if __name__ == "__main__":
    unittest.main()
