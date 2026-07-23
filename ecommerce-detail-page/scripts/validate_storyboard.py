#!/usr/bin/env python3
"""验证商品图生图分镜的公开 Markdown 格式。"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path


SECURITY_CONFUSABLES = str.maketrans(
    {
        # 常见西里尔/希腊同形字，防止“SKU”等安全边界词被异体字拆穿。
        "А": "A", "В": "B", "С": "C", "Е": "E", "Н": "H", "К": "K",
        "М": "M", "О": "O", "Р": "P", "Т": "T", "Х": "X", "І": "I",
        "Ј": "J", "Ѕ": "S", "У": "Y",
        "а": "a", "в": "b", "с": "c", "е": "e", "н": "h", "к": "k",
        "м": "m", "о": "o", "р": "p", "т": "t", "х": "x", "і": "i",
        "ј": "j", "ѕ": "s", "у": "y",
        "Α": "A", "Β": "B", "Ε": "E", "Ζ": "Z", "Η": "H", "Ι": "I",
        "Κ": "K", "Μ": "M", "Ν": "N", "Ο": "O", "Ρ": "P", "Τ": "T",
        "Χ": "X", "Υ": "Y", "Ϲ": "C", "Ϻ": "M",
        "α": "a", "β": "b", "ε": "e", "ζ": "z", "η": "h", "ι": "i",
        "κ": "k", "μ": "m", "ν": "n", "ο": "o", "ρ": "p", "τ": "t",
        "χ": "x", "υ": "y", "ϲ": "c",
    }
)
# 只用于规则扫描的少量繁体字归一化。正式提示词仍保留用户要求的原文，
# 但不能让繁体/简体切换成为事实边界的绕过方式。
SECURITY_TRADITIONAL = str.maketrans(
    {
        "結": "结", "構": "构", "輪": "轮", "顏": "颜", "變": "变", "換": "换",
        "刪": "删", "畫": "画", "內": "内", "補": "补", "虛": "虚", "許": "许",
        "編": "编", "製": "制", "調": "调", "設": "设", "計": "计", "裝": "装",
        "產": "产", "標": "标", "誌": "志", "連": "连",
        "開": "开", "並": "并", "與": "与", "給": "给", "從": "从", "為": "为",
        "實": "实", "體": "体", "確": "确", "認": "认", "獨": "独", "立": "立",
        "參": "参", "考": "考", "圖": "图", "視": "视", "覺": "觉", "資": "资",
        "料": "料", "選": "选", "擇": "择", "採": "采", "納": "纳", "審": "审",
        "評": "评", "狀": "状", "態": "态", "籤": "签", "論": "论", "過": "过",
        "範": "范", "圍": "围", "後": "后", "續": "续", "議": "议", "無": "无",
        "達": "达", "識": "识", "偽": "伪", "難": "难", "戶": "户", "驗": "验",
        "決": "决", "關": "关", "係": "系", "還": "还", "暫": "暂", "沒": "没",
        "衝": "冲", "捨": "舍", "棄": "弃", "證": "证", "僅": "仅",
        "傳": "传", "輸": "输", "將": "将", "號": "号", "張": "张",
        "個": "个", "寫": "写", "佔": "占", "稱": "称", "碼": "码",
        "鑰": "钥", "訪": "访", "組": "组", "質": "质", "單": "单",
        "層": "层", "總": "总", "覽": "览", "對": "对", "顯": "显",
        "數": "数", "頁": "页", "幀": "帧", "執": "执", "陳": "陈",
        "請": "请", "說": "说", "會": "会", "誤": "误", "購": "购",
    }
)
SECURITY_PUNCTUATION = str.maketrans({",": "，", ";": "；"})


REQUIRED_FIELDS = (
    "输出对象",
    "成图任务",
    "画布与布局",
    "参考图使用",
    "商品锁定",
    "允许变化",
    "视角与事实边界",
    "最终画面",
    "镜头与构图",
    "光影、材质与色彩",
    "生产与后期",
)
OPTIONAL_FIELDS = ("场景与人物", "最终文案")
ALLOWED_FIELDS = set(REQUIRED_FIELDS + OPTIONAL_FIELDS)
DESCRIPTIVE_PUBLIC_FIELDS = {
    "成图任务",
    "画布与布局",
    "参考图使用",
    "商品锁定",
    "允许变化",
    "视角与事实边界",
    "最终画面",
    "镜头与构图",
    "光影、材质与色彩",
    "生产与后期",
    "场景与人物",
}
OUTPUT_ID_PREFIXES = {
    "主图": "主图",
    "SKU图": "SKU图",
    "详情页": "详情页",
    "海报": "海报",
    "白底图": "白底图",
    "透明图": "透明图",
    "透明背景图": "透明图",
    "无字场景图": "无字场景图",
}
OUTPUT_PREFIX_ALIASES = {"透明背景图": "透明图"}

HEADING_RE = re.compile(
    r"^## 第(?P<page>\d+)张（(?P<storyboard_id>[A-Za-z0-9\u4e00-\u9fff]+-\d{2,})）：(?P<title>\S.*)$",
    re.MULTILINE,
)
FIELD_RE = re.compile(r"^- ([^\n：]+)：[ \t]*(.*)$", re.MULTILINE)
QUANTITY_NOTE_RE = re.compile(
    r"^> 数量说明：(?=.*(?:\d+|[零〇一二三四五六七八九十百千万两]+)\s*"
    r"(?:张|幅|个(?:详情页)?模块|(?:个|条)分镜|个候选(?:图)?|张候选(?:图)?))\S.*$"
)
PROMPT_RE = re.compile(
    r"^- 🎨 图生图提示词：\s*\n```text\n(?P<text>.+?)\n```\s*$",
    re.MULTILINE | re.DOTALL,
)
NEGATIVE_RE = re.compile(
    r"^- ⚠️ 动态负面提示词：\s*\n```text\n(?P<text>.+?)\n```\s*$",
    re.MULTILINE | re.DOTALL,
)
REFERENCE_TERM = (
    r"(?:参考图(?:片)?|商品(?:实拍|图(?:片|像)?)|实拍图|实物照片|包装照片|结构图|"
    r"参考视觉|视觉资料|界面(?:截图|录屏|预览图)|权益(?:说明)?页(?:面)?(?:截图)?|"
    r"(?:交付|激活|预约|核销|服务)?流程(?:截图|图|页(?:面)?)?|"
    r"(?:订单|到账|交付|激活|预约|核销)?状态截图|"
    r"授权(?:页(?:面)?(?:截图)?|文件|截图)|服务场景(?:图|照片)?|"
    r"(?:同款|同版本|商品|包装|结构|界面|权益|流程|授权|服务场景)资料)"
)
REFERENCE_TERM_RE = re.compile(REFERENCE_TERM)
REFERENCE_MODIFIER = r"(?:(?:真实|原始|清晰|可访问|已授权|用户提供的|卖家|官方|同版本|同款|相关|当前|本次)\s*){0,4}"
REFERENCE_ANALYSIS_VERB = r"(?:逐一查看|分析|读取|综合|检查|比对|查看|审阅|核对|核验)"
REFERENCE_GLOBAL_ANALYSIS_RE = re.compile(
    rf"(?:(?:已|先|经过|完成)?{REFERENCE_ANALYSIS_VERB}[^，。；\n]{{0,20}}(?:全部|所有)(?:有效|可用)?{REFERENCE_MODIFIER}{REFERENCE_TERM}|"
    rf"(?:全部|所有)(?:有效|可用)?{REFERENCE_MODIFIER}{REFERENCE_TERM}[^，。；\n]{{0,20}}(?:已|先)?{REFERENCE_ANALYSIS_VERB})"
)
NEGATED_GLOBAL_ANALYSIS_RE = re.compile(
    rf"(?:(?:未|没有|并未|尚未|仍未|无需|无须|不必)[^，。；\n]{{0,8}}(?:真正|完整)?{REFERENCE_ANALYSIS_VERB}"
    rf"[^，。；\n]{{0,20}}(?:全部|所有)(?:有效|可用)?{REFERENCE_MODIFIER}{REFERENCE_TERM}|"
    rf"{REFERENCE_ANALYSIS_VERB}[^，。；\n]{{0,10}}(?:的)?(?:并非|并不|不是|未覆盖|没有覆盖|不含)"
    rf"[^，。；\n]{{0,8}}(?:全部|所有)(?:有效|可用)?{REFERENCE_MODIFIER}{REFERENCE_TERM})"
)
POSTPOSED_GLOBAL_ANALYSIS_UNRESOLVED_RE = re.compile(
    r"(?:(?:尚未|仍未|并未|未)(?:完成|结束|覆盖完整|核验完成|确认完成)|"
    r"(?:但|不过|然而)?(?:仅|只)(?:实际)?(?:看|查看|分析|读取|审阅|检查|核对|核验)"
    r"(?:了)?(?:其中)?(?:一部分|部分|少量))"
)
GLOBAL_ANALYSIS_INCOMPLETE_RE = re.compile(
    r"(?:(?:还有|尚有|剩余|余下)[^，。；\n]{0,12}"
    r"(?:(?:没|未)(?:看|查看|分析|读取|审阅|检查|核对|核验)|"
    r"待(?:看|查看|分析|读取|审阅|检查|核对|核验))|"
    r"(?:实际|仍|又|另外)?(?:(?:漏掉|漏看|漏读)(?:了)?|遗漏了)[^，。；\n]{0,12}|"
    r"(?:分析|查看|读取|审阅|检查|核对|核验)?完成度\s*"
    r"(?:[一二三四五六七八九]成|[1-9]\d?%)|"
    r"(?:除了|除)[^，。；\n]{0,4}(?:最后|其中|某|第?\s*(?:\d+|[零〇一二三四五六七八九十百千万两]+))"
    r"\s*(?:张|幅|份|页|个)[^，。；\n]{0,8}(?:以外|之外)|"
    r"(?:(?:只是|仍然?|尚|依然|确实|实际)[^，。；\n]{0,3}(?:有|存在)(?:所)?遗漏|"
    r"存在(?:一处|部分|若干)?遗漏))"
)
REFERENCE_UNITS = "张幅份页段组套批帧屏面"
CHINESE_NUMBER = r"[零〇一二三四五六七八九十百千万两]+"
CIRCLED_NUMBER = (
    r"[\u2460-\u2487\u2776-\u277f\u278a-\u2793\u3220-\u3229"
    r"\u3251-\u325f\u3280-\u3289\u32b1-\u32bf]"
)
COUNTED_REFERENCE_BEFORE_RE = re.compile(
    rf"(?P<count>-?\d+|{CHINESE_NUMBER})\s*(?P<unit>[{REFERENCE_UNITS}])[^，。；\n]{{0,14}}{REFERENCE_TERM}"
)
COUNTED_REFERENCE_AFTER_RE = re.compile(
    rf"{REFERENCE_TERM}[^，。；\n]{{0,16}}(?P<count>-?\d+|{CHINESE_NUMBER})\s*(?P<unit>[{REFERENCE_UNITS}])"
)
CONTINUED_COUNTED_REFERENCE_RE = re.compile(
    rf"(?:正面|侧面|背面|底部|顶部|局部|包装|结构|界面|权益|流程|授权|场景|实拍)"
    rf"[^，。；\n]{{0,4}}(?P<count>-?\d+|{CHINESE_NUMBER})\s*(?P<unit>[{REFERENCE_UNITS}])"
)
NATURAL_MULTI_REFERENCE_SCOPE = (
    r"(?:多张|数张|若干张|好几张|若干幅|多幅|数幅|一对|成对|"
    r"双份|双张|双幅|双帧|双屏|一批|多批|数批|若干批|整批|好几批|十余批|"
    r"一整组|整组|一整套|整套|一系列|十余张|数十张|几十张)"
)
NAMED_REFERENCE_SCOPE_RE = re.compile(
    rf"(?P<scope>单张|一部分|部分|{NATURAL_MULTI_REFERENCE_SCOPE})[^，。；\n]{{0,14}}{REFERENCE_TERM}|"
    rf"{REFERENCE_TERM}[^，。；\n]{{0,10}}(?P<scope_after>单张|{NATURAL_MULTI_REFERENCE_SCOPE})"
)
ALL_REFERENCE_SCOPE_RE = re.compile(
    rf"(?:全部|所有)(?:有效|可用)?{REFERENCE_MODIFIER}{REFERENCE_TERM}"
)
CONJOINED_REFERENCE_SCOPE_RE = re.compile(
    rf"(?:正面|侧面|背面|底部|顶部|局部|包装|结构|界面|权益|流程|授权|场景|实拍)"
    rf"[^，。；\n]{{0,8}}(?:与|和|、)[^，。；\n]{{0,12}}(?:{REFERENCE_TERM}|资料)"
)
FIXED_REFERENCE_ID = (
    rf"(?:\d+(?![\d{REFERENCE_UNITS}A-Za-z年月日版像素])|"
    rf"{CHINESE_NUMBER}(?![{REFERENCE_UNITS}零〇一二三四五六七八九十百千万两])|"
    r"[壹贰叁肆伍陆柒捌玖拾佰仟]+|[甲乙丙丁戊己庚辛壬癸]|"
    rf"{CIRCLED_NUMBER}|"
    r"[A-Z](?![A-Z0-9]))"
)
FIXED_REFERENCE_RE = re.compile(
    rf"(?:第\s*(?:\d+|{CHINESE_NUMBER}|{CIRCLED_NUMBER}|[A-Z]\d*)\s*(?:[{REFERENCE_UNITS}])?\s*{REFERENCE_TERM}|"
    rf"{REFERENCE_TERM}\s*(?:"
    rf"(?:编号|序号|No\.?|#|[:：-])\s*(?:[（(【\[]\s*)?{FIXED_REFERENCE_ID}(?:\s*[）)】\]])?|"
    rf"[（(【\[]\s*{FIXED_REFERENCE_ID}\s*[）)】\]]|"
    rf"(?:No\.?\s*)?[A-Z]\d+(?![A-Za-z0-9]|版本|型号|像素|年|月|日)|"
    rf"{FIXED_REFERENCE_ID}(?=$|[\s，。；、,:：;]|用于|用来|提取|锁定|作为|保持|显示|确认|中)))",
    re.IGNORECASE,
)
NATURAL_FIXED_REFERENCE_RE = re.compile(
    rf"(?:{REFERENCE_TERM})\s*{FIXED_REFERENCE_ID}\s*号|"
    rf"{FIXED_REFERENCE_ID}\s*号\s*(?:的)?\s*(?:{REFERENCE_TERM})|"
    rf"(?:编号|序号|标记|标注)\s*(?:为|是|[:：-])?\s*{FIXED_REFERENCE_ID}"
    rf"\s*(?:号)?\s*(?:的)?\s*(?:{REFERENCE_TERM})",
    re.IGNORECASE,
)
REFERENCE_PURPOSE_RE = re.compile(
    r"(?:商品身份|核心对象|商品特征|SKU|版本|几何|结构|轮廓|颜色|材质|文字|包装|配件|尺度|场景|细节|共同特征|正面|界面|权益|流程|交付|授权)"
)
REFERENCE_TARGET_FILTER_RE = re.compile(
    r"(?:(?:按|依据|围绕)[^，。；\n]{0,20}(?:目标\s*(?:SKU|版本)(?:/状态)?|各\s*(?:SKU|版本))[^，。；\n]{0,20}(?:筛选|提取|分别)|"
    r"(?:目标\s*(?:SKU|版本)(?:/状态)?|各\s*(?:SKU|版本))[^，。；\n]{0,20}(?:筛选|限定|匹配|分别提取)|"
    r"(?:只|仅)[^，。；\n]{0,12}(?:(?:目标|当前|对应)\s*(?:SKU|版本)(?:/状态)?|各\s*(?:SKU|版本))|"
    r"(?:目标|当前|对应)\s*(?:SKU|版本)(?:/状态)?[^，。；\n]{0,16}(?:有效|一致|对应)(?:参考|证据|内容|资料))"
)
REFERENCE_SKU_ISOLATION_RE = re.compile(
    r"(?:同一目标\s*(?:SKU|版本)|同一\s*(?:SKU|版本)|同\s*(?:SKU|版本)|"
    r"(?:只|仅)[^，。；\n]{0,12}(?:目标|当前|对应)\s*(?:SKU|版本)|"
    r"(?:其他|不同)\s*(?:SKU|版本)[^，。；\n]{0,30}(?:不作为生成参考输入|不传入|排除|仅用于差异|只用于差异|防串款)|"
    r"各\s*(?:SKU|版本)[^，。；\n]{0,24}(?:分别|分层|独立商品层|后期合成))"
)
SAME_TARGET_REFERENCE_RE = re.compile(
    rf"(?:(?:同款|同版本)[^，。；\n]{{0,12}}(?:{REFERENCE_TERM}|资料)|"
    rf"(?:{REFERENCE_TERM}|资料)[^，。；\n]{{0,10}}(?:均为|都是|属于)(?:同款|同版本))"
)
NAMED_TARGET_SELECTION_RE = re.compile(
    r"(?<!不)(?:只|仅)(?:综合|采用|提取|使用)[^，。；\n]{1,32}(?:款|版本|型号)(?:的)?"
)
NEGATED_TARGET_FILTER_RE = re.compile(
    r"(?:(?:不按|并非按|没有按|未按)[^，。；\n]{0,12}(?:目标\s*(?:SKU|版本)|各\s*(?:SKU|版本))|"
    r"(?:目标\s*(?:SKU|版本)(?:/状态)?|各\s*(?:SKU|版本))[^，。；\n]{0,10}"
    r"(?:并未|没有|尚未|仍未|未|不曾|并非)[^，。；\n]{0,6}(?:筛选|限定|匹配|提取|分别))"
)
NEGATED_SKU_ISOLATION_RE = re.compile(
    r"(?:(?:同一目标\s*(?:SKU|版本)|同一\s*(?:SKU|版本)|同\s*(?:SKU|版本))[^，。；\n]{0,10}"
    r"(?:并未|没有|尚未|仍未|未|不能)[^，。；\n]{0,6}(?:互补|隔离|分开|分别)|"
    r"(?:其他|不同)\s*(?:SKU|版本)[^，。；\n]{0,10}(?:并未|没有|尚未|仍未|未|不能)"
    r"[^，。；\n]{0,6}(?:排除|隔离|分开|剔除)|"
    r"(?:不只用|并非只用|没有只用|不只采用|并非仅采用)[^，。；\n]{0,12}(?:目标|当前|对应)\s*(?:SKU|版本))"
)
OTHER_SKU_GENERATION_INPUT_RE = re.compile(
    r"(?:"
    r"(?:其他|不同|另一|另一个)\s*(?:SKU|版本|型号|款式)(?:图片|参考图|资料)?"
    r"[^，。；\n]{0,24}(?:传入|输入|送入|提供给|作为|用作)"
    r"[^，。；\n]{0,12}(?:生成模型|图像模型|模型|生成参考输入|参考输入|身份输入)|"
    r"(?:向|给)?(?:图像|生成)?模型(?:提供|输入|传入|送入|接收)"
    r"[^，。；\n]{0,20}(?:其他|不同|另一|另一个)\s*(?:SKU|版本|型号|款式)"
    r"(?:图片|参考图|资料)?|"
    r"(?:其他|不同|另一|另一个)\s*(?:SKU|版本|型号|款式)(?:图片|参考图|资料)?"
    r"[^，。；\n]{0,20}(?:也|一并|同时)?(?:传入|输入|送入)"
    r"[^，。；\n]{0,12}(?:生成模型|图像模型|模型|生成参考输入|参考输入|身份输入)"
    r")"
)
NEGATED_OTHER_SKU_INPUT_RE = re.compile(
    r"(?:不|未|没有|并未|禁止|避免|排除|拒绝)[^，。；\n]{0,10}"
    r"(?:传入|输入|送入|提供给|作为|用作)"
)
REFERENCE_CONFLICT_RESOLVED_RE = re.compile(
    r"(?:(?:资料|参考(?:图|视觉)?|同款内容)[^，。；\n]{0,20}"
    r"(?:一致(?!性)|无冲突|没有冲突|无需裁决)|"
    r"(?:最终|已明确)(?:采用|保留)[^。\n]{1,60}(?:舍弃|排除|不采用)[^。\n]{1,60}|"
    r"(?:最终|已明确)(?:舍弃|排除|不采用)[^。\n]{1,60}(?:采用|保留)[^。\n]{1,60})"
)
REFERENCE_CONFLICT_UNRESOLVED_RE = re.compile(
    r"(?:(?:并非|并不|不是|没有|并未|尚未|仍未|未|无法|不能|不)(?!但|仅|只|止)"
    r"[^，。；\n]{0,12}(?:一致|无冲突|没有冲突|无需裁决)|"
    r"(?:尚未|仍未|未能|无法|不能)\s*(?:确认|确定|判断|证明)?\s*是否\s*(?:为|属于)?\s*(?:同款|同版本)|"
    r"(?:是否\s*(?:为|属于)?\s*(?:同款|同版本))\s*(?:尚未|仍未|未能|无法|不能)\s*(?:确认|确定|判断|证明)?|"
    r"(?:是否|能否)[^，。；\n]{0,8}(?:一致|相同)[^，。；\n]{0,8}(?:尚不确定|不确定|尚未确定|仍未确定|无法确定|不能确定)?|"
    r"(?:一致|相同)(?:性)?[^，。；\n]{0,10}(?:尚未|仍未|未|无法|不能|待|尚不)(?:确认|确定|证明|明确)?|"
    r"(?:冲突|矛盾|不一致)[^，。；\n]{0,16}(?:尚未|仍未|未|无法|不能|待)(?:裁决|确认|解决)|"
    r"(?:资料|参考(?:图|视觉)?|同款内容)[^，。；\n]{0,12}"
    r"(?:暂时|暂|目前|现阶段)?(?:尚|仍)?(?:不能|无法|未能)"
    r"(?:下|得出|形成|作出|做出)?(?:结论|判断))"
)
REFERENCE_PENDING_CONCLUSION_RE = re.compile(
    r"(?:资料|参考(?:图|视觉)?|同款内容)[^，。；\n]{0,16}"
    r"(?:尚无定论|待(?:用户|客户)?拍板|不能确认|未达成共识|真假难辨|"
    r"需(?:要)?后续再议|仍需确认后再定)\s*(?=$|[。；\n])"
)
REFERENCE_SAME_VARIANT_PENDING_RE = re.compile(
    r"(?:同款|同版本)[^。；\n]{0,80}"
    r"(?:需要后续再议|不能确认(?![^，。；\n]{0,12}(?:隐藏结构|背面|内部|配件)))"
)
GENERAL_REFERENCE_PENDING_RE = re.compile(
    r"(?:资料(?:仍|尚)?(?:不确定|拿不准|尚有疑问)|"
    r"不知道是否(?:同款|同版本|一致|相同)|"
    r"(?:同款|同版本)(?:关系)?(?:仍|尚)?(?:不明确|不明|不清楚)|"
    r"(?:资料|参考(?:图|视觉|资料)?)(?:仍|尚)?待(?:用户|客户)?确认|"
    r"(?:尚待|待)(?:用户|客户)?(?:核实|核验|确认|判断|裁决)|"
    r"需要(?:用户|客户)(?:判断|确认|拍板)|"
    r"(?:还|尚|仍)?没有裁决|"
    r"结论(?:还|尚|仍)?(?:没(?:有)?出来|未出)|"
    r"(?:暂|尚|仍|目前)?不能(?:得出|形成|作出|做出)?(?:结论|判断)?|"
    r"(?:暂时|暂|目前|尚|仍)?无法(?:判定|判断|确认|核实|得出(?:结论)?)|"
    r"还需(?:进一步)?(?:核对|核验|确认|判断|裁决)|"
    r"(?:暂|尚|仍|目前)?无(?:明确)?结论|"
    r"暂不确定|(?:尚|仍|还)?未(?:完成)?核对(?:完成)?|"
    r"(?:尚|仍|还)?未完成(?:核验|确认|裁决)|"
    r"需要后续再议|不能确认|待确认)"
)
EXPLICIT_PROHIBITION_RE = re.compile(
    r"(?:不得|不能|不可|不要|禁止|避免|防止|杜绝|切勿|请勿|不应|勿|切莫)"
    r"(?:补画|生成|还原|呈现|写入|采用|使用|改变|修改|重画|重塑|增加|添加|删除|新增|"
    r"推断|推测|虚构|编造|猜测|补充|"
    r"融合|混合|拼装|拼搭|传入|输入|把|将)"
)
SAFE_PENDING_EXCLUSION_RE = re.compile(
    r"(?:(?:不能确认|无法确认|不确定|待确认|待判断|拿不准|尚有疑问)"
    r"[^，。；\n]{0,10}(?:隐藏结构|未知(?:背面|底部|内部|配件|拆解|接口)|"
    r"背面|底部|内部|配件|拆解|接口|包装(?:小字|文字|内容|细节|结构)?|"
    r"文字|文案|参数|卖点|认证|颜色|材质|尺寸|容量|功能|权益(?:内容|细节)?|流程(?:内容|细节)?)"
    r"[^。；\n]{0,32}(?:不补画|不生成|不呈现|不写入|不采用|不使用|排除|舍弃)|"
    r"(?:不能确认|无法确认|不确定|待确认|待判断|拿不准|尚有疑问)[^。；\n]{0,20}资料"
    r"[^。；\n]{0,20}(?:不作为生成参考输入|不输入|不采用|不使用|排除|舍弃))"
)
REFERENCE_CONFLICT_SIGNAL_RE = re.compile(r"(?:冲突|矛盾|不一致)")
REFERENCE_POSITIVE_RESOLUTION_RE = re.compile(
    r"(?:(?:参考(?:图|视觉|资料)?|资料|同款(?:资料)?|同版本(?:资料)?|"
    r"同一(?:目标)?(?:SKU|版本))[^。；\n]{0,40}"
    r"(?:一致|无冲突|没有冲突|无需裁决|互补|相互印证|彼此印证|可兼容)|"
    r"(?:参考图|商品图|资料|界面截图|权益页面|结构图)[^。；\n]{0,28}"
    r"(?:综合|整合|互补)[^。；\n]{0,28}"
    r"(?:商品身份|核心对象|结构|几何|颜色|材质|细节|文字|权益|流程|内容)|"
    r"(?:互补|相互印证|彼此印证|已核对|已核验|已比对|已确认)[^。；\n]{0,24}"
    r"(?:商品身份|核心对象|结构|几何|颜色|材质|细节|文字|资料|内容)|"
    r"(?:最终|已明确)(?:采用|保留)[^。；\n]{1,60}(?:舍弃|排除|不采用)[^。；\n]{1,60}|"
    r"(?:最终|已明确)(?:舍弃|排除|不采用)[^。；\n]{1,60}(?:采用|保留)[^。；\n]{1,60})"
)
NEGATED_SAME_TARGET_REFERENCE_RE = re.compile(
    r"(?:提供|输入|使用|采用|选用)[^，。；\n]{0,16}"
    r"(?:并非|并不|不是|非|不同于)\s*(?:同款|同版本)"
    r"(?:参考图(?:片)?|资料|内容)?|"
    r"(?:并非|并不|不是|非|不同于)\s*(?:同款|同版本)"
    r"(?:参考图(?:片)?|资料|内容)"
    r"|(?:同款|同版本)(?:参考图(?:片)?|资料|内容)"
    r"[^，。；\n]{0,12}(?:并非|并不|不是|非|不同于)"
)
CHINESE_RE = re.compile(r"[\u3400-\u9fff]")
LATIN_CHARACTER_RE = re.compile(r"[A-Za-z]")
NON_CHINESE_SCRIPT_RE = re.compile(r"[\u3040-\u30ff\u31f0-\u31ff\u0400-\u052f]")
PRESERVED_ORIGINAL_RE = re.compile(
    r"(?:逐字|原样|完整)?(?:保留|还原|呈现)(?:界面|页面|包装|屏幕|可见)?(?:中|内|中的|内的)?"
    r"(?:原文|文字|文案|品牌|型号)?\s*[：:]?\s*[“\"‘'「『《【（(〈〖〔]"
    r"(?P<original>.*?)[”\"’'」』》】）)〉〗〕]",
    re.DOTALL,
)
NON_ORIGINAL_INSTRUCTION_RE = re.compile(
    r"(?:以下|下列|后续|后面|其后)?(?:内容)?\s*(?:并非|不是|不属于|非)\s*"
    r"(?:界面|页面|包装|商品)?原文[^：:；;\n]{0,16}(?:而是|是)?\s*(?:生成)?(?:指令|提示词)"
)

FORBIDDEN_SECRET_RE = re.compile(
    r"(?i)(?:"
    r"sk-[A-Za-z0-9_-]{16,}|"
    r"gh[opurs]_[A-Za-z0-9]{20,}|"
    r"AKIA[0-9A-Z]{16}|"
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----|"
    r"\bBearer\s+[A-Za-z0-9._~-]{20,}|"
    r"\bAuthorization\s*:\s*Basic\s+[A-Za-z0-9+/]{12,}={0,2}|"
    r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{5,}|"
    r"(?<![A-Za-z0-9])(?:password|passwd|pwd|api[\s_-]?key|"
    r"aws[\s_-]?secret[\s_-]?access[\s_-]?key|access[\s_-]?token|"
    r"session[\s_-]?token|refresh[\s_-]?token|client[\s_-]?secret)"
    r"\s*[:=]\s*[\"']?[^\s\"']{8,}|"
    r"(?:\bAPI\s*密钥|(?<![\u3400-\u9fffA-Za-z0-9])(?:密码|密钥|访问令牌|令牌))"
    r"\s*[:=：]\s*[\"']?[^\s\"']{8,}|"
    r"\bCookie\s*:\s*[A-Za-z0-9_.-]+=[^;\s]{8,}"
    r")"
)
FORBIDDEN_INTERNAL_RE = re.compile(
    r"(?:内部(?:评分|打分|质检(?:结论)?|审核)|审核结论\s*[：:]|评审意见\s*[：:]|"
    r"候选(?:方案|比较|稿[^，。；\n]{0,16}优于)|角色(?:讨论|名称)|"
    r"(?:循环|推演)(?:日志|记录)|思维链(?:如下)?|推理过程(?:如下)?|"
    r"模型名|测试(?:标签|文字)|审查状态|调试字段|未采用方案|确认记录|隐藏思考链|"
    r"写实视图确认|待范围判断|(?:已确认|未确认|待确认|候选)写实视图|"
    r"置信水平|还原把握度|待审核)"
)
FORBIDDEN_VIEW_METADATA_RE = re.compile(
    r"(?:(?:背面|底部|内部|拆解|隐藏(?:结构|配件|视图)|写实视图)"
    r"[^，。；\n]{0,32}(?:确认(?:状态)?|审核(?:状态)?|状态|可信度|置信(?:度|水平)?|"
    r"把握度|评分(?:结果)?|得分|分数|分值|通过|待[^。；\n]{0,6}审核|"
    r"(?:8[1-9]|9\d|100)(?:\s*[–—-]\s*100)?\s*分)|"
    r"(?:确认(?:状态)?|审核(?:状态)?|状态|可信度|置信(?:度|水平)?|把握度|"
    r"评分(?:结果)?|得分|分数|分值|通过|待[^。；\n]{0,6}审核|"
    r"(?:8[1-9]|9\d|100)(?:\s*[–—-]\s*100)?\s*分)"
    r"[^，。；\n]{0,32}(?:背面|底部|内部|拆解|隐藏(?:结构|配件|视图)|写实视图))"
)
ASSERTED_FACT_MUTATION_RE = re.compile(
    r"(?:(?:允许|可以|可|直接)?(?:虚构|编造)[^，。；\n]{0,24}(?:背面|底部|内部|配件|拆解)|"
    r"(?:允许|可以|可|直接)?(?:补画|生成|还原)[^，。；\n]{0,16}"
    r"(?:未知|未确认|无证据)[^，。；\n]{0,12}(?:背面|底部|内部|配件|拆解)|"
    r"(?:允许|可以|可|直接|创意)?(?:改变|修改|重画|重塑)[^，。；\n]{0,12}"
    r"(?:商品)?(?:结构|轮廓|比例|颜色|材质|表面|尺寸|大小|数量|容量|重量|参数|规格|功能|成分|功效|适配|品牌文字)|"
    r"(?:允许|可以|可|直接)?(?:增减|新增|删除)[^，。；\n]{0,10}"
    r"(?:商品)?(?:结构|部件|配件))"
)
EXPLICIT_PRODUCT_MUTATION_RE = re.compile(
    r"(?:改变|修改|重画|重塑|改造|调整|变更|替换|重构|移除|增加|添加|删去|"
    r"增减|新增|删除|重新设计|重做)"
    r"[^，。；\n]{0,8}(?:商品|产品|主体|机身|本体|品牌(?:文字)?|SKU|版本)"
    r"[^，。；\n]{0,8}(?:结构|轮廓|比例|外形|颜色|材质|表面|尺寸|大小|数量|容量|重量|参数|规格|功能|成分|功效|适配|部件|配件|接口|开孔|连接件|包装|文字|标志)"
)
CREATIVE_ENVIRONMENT_MUTATION_RE = re.compile(
    r"(?:背景|场景|构图|道具|布景|光影|人物|衣服|服装|环境|桌面|地面|墙面|"
    r"视角|镜头|画面|呈现|表现|图示|剖面|示意|线稿)"
    r"[^，。；\n]{0,10}(?:结构|轮廓|颜色|部件|配件)"
 )
CONFIRMED_CONCEPT_VARIATION_RE = re.compile(
    r"(?:用户|客户|需求方)已(?:明确)?确认[^。；\n]{0,40}"
    r"(?:非实物还原|概念稿|概念设计|创意改款|虚构创作)"
)
FACT_MUTATION_PROHIBITION_RE = re.compile(
    r"(?:不|不得|不可|禁止|避免|防止|杜绝|切勿|严禁)"
    r"[^，。；\n但却而]{0,64}$"
)
FORBIDDEN_VIEW_ANNOTATION_RE = re.compile(
    r"(?:置信度(?:\s*\d+分?)?|高置信|推定|推测|"
    r"(?:看起来|大概率|很可能|可能|疑似|估计)[^，。；\n]{0,20}"
    r"(?:背面|底部|内部|拆解|隐藏(?:结构|配件|视图)|平面结构)|"
    r"(?:背面|底部|内部|拆解|隐藏(?:结构|配件|视图)|平面结构)"
    r"[^，。；\n]{0,20}(?:看起来|大概率|很可能|可能|疑似|估计|示意(?:图)?))"
)
EVIDENCE_BOUNDED_DIAGRAM_RE = re.compile(
    r"(?=.*(?:剖面|结构拆解|爆炸分解|线稿|结构示意|装配演示|分层堆叠|局部开窗))"
    r"(?=.*(?:参考图|工程图|结构图|拆解实拍|资料(?:中|内)?|用户确认|"
    r"已证实|可见|仅呈现|只呈现|不新增|不补画|非写实|概念稿))"
)
UNSAFE_DIAGRAM_INFERENCE_RE = re.compile(
    r"(?:置信度|高置信|推定|推测|大概率|很可能|可能|疑似|估计|待确认|待审核|"
    r"审核状态|评分|得分|分数|分值)"
)
SKU_FUSION_RE = re.compile(
    r"(?i)(?:(?:融合|混合|平均|拼接|拼装|合并|组合|合成|混成)(?:多个|不同|两个|两种)?\s*SKU|"
    r"(?:多个|不同|两个|两种)\s*SKU(?:进行)?(?:融合|混合|平均|拼接|拼装|合并|组合|合成|混成)|"
    r"(?:把|将)?(?:多个|不同|两个|两种)\s*SKU[^，。；\n]{0,18}(?:拼成|合成|做成|合并成|组合成)(?:一款|一个)?|"
    r"(?:各|多个|不同|两个|两种)\s*(?:SKU|版本)[^，。；\n]{0,40}"
    r"(?:混在|融合(?:到|为|成)?|合并(?:到|为|成)?|组合(?:到|为|成)?|拼成|合成(?:为|到|成)?)"
    r"[^，。；\n]{0,12}(?:同一|一个)[^，。；\n]{0,10}(?:商品层|商品身份|商品主体|主体|商品|款|版本))"
)
NAMED_VARIANT_FUSION_RE = re.compile(
    r"(?i)(?:[A-Za-z0-9\u4e00-\u9fff]{1,12}款\s*(?:和|与|、)\s*"
    r"[A-Za-z0-9\u4e00-\u9fff]{1,12}款[^，。；\n]{0,12}(?:融合|混合|拼接|拼装|合并|组合|合成)"
    r"[^，。；\n]{0,12}(?:(?:同一|一个)[^，。；\n]{0,6}(?:商品身份|商品主体|商品|款|版本)|一款)|"
    r"[A-Za-z0-9\u4e00-\u9fff]{1,12}\s*(?:和|与|、)\s*"
    r"[A-Za-z0-9\u4e00-\u9fff]{1,12}\s*SKU[^，。；\n]{0,12}"
    r"(?:融合|混合|拼接|拼装|合并|组合|合成)[^，。；\n]{0,12}"
    r"(?:(?:同一|一个)[^，。；\n]{0,6}(?:商品身份|商品主体|商品|款|版本)|一款))"
)
DIRECT_NEGATION_RE = re.compile(
    r"(?:并非|并不|不是|没有|并未|尚未|仍未|从未|未|禁止|避免|防止|杜绝|无须|无需|无法|不能|"
    r"不(?!但|仅|只|止)(?:要|得|应|可|能|允许|必|需要|再)?)"
    r"[^，。；\n但却而]{0,10}$"
)
EXPLANATORY_FUSION_PREFIX_RE = re.compile(r"(?:说明|解释|警示|展示)[^，。；\n]{0,12}$")
EXPLANATORY_FUSION_SUFFIX_RE = re.compile(r"^(?:会|将|可能)?(?:造成|导致|引发)")
FUSION_PROHIBITION_RE = re.compile(
    r"(?:(?:不要|不得|禁止|避免|防止|杜绝|不能|不可|不应|切勿|切莫|严禁|请勿|勿|并非|没有|不是|不允许)"
    r"[^，。；\n但却而并]{0,24}|不(?:再)?(?:把|将)?)$"
)
CROSS_MODEL_TRANSPLANT_RE = re.compile(
    r"(?:把|将)\s*(?P<source>(?:SKU[-_ ]?[A-Za-z0-9_-]{1,12}|(?=[A-Za-z0-9_-]*\d)[A-Za-z0-9_-]{2,}|[A-Za-z0-9_-]{1,12}(?:款|版|型)|[\u4e00-\u9fff]{1,6}(?:款|版|型)))\s*的?"
    r"[^，。；\n]{1,24}(?:装到|装入|移植到|拼到|接到|换到)\s*"
    r"(?P<target>(?:SKU[-_ ]?[A-Za-z0-9_-]{1,12}|(?=[A-Za-z0-9_-]*\d)[A-Za-z0-9_-]{2,}|[A-Za-z0-9_-]{1,12}(?:款|版|型)|[\u4e00-\u9fff]{1,6}(?:款|版|型)))",
    re.IGNORECASE,
)
TRANSFER_VARIANT_LABEL = (
    r"(?:SKU[-_ ]?[A-Za-z0-9_-]{1,12}|[A-Za-z0-9_-]{1,12}(?:款|版|型号|版本)|"
    r"[\u4e00-\u9fff]{1,8}(?:款|版|型号|版本))"
)
CROSS_VARIANT_TRANSFER_RE = re.compile(
    rf"(?:把|将)\s*(?P<source>{TRANSFER_VARIANT_LABEL})\s*(?:的)?"
    r"(?P<part>[^，。；\n]{1,20}?)\s*"
    r"(?:用于|配给|给|交给|提供给|转给|共用|合用|装配到|装配给|安装到|安装给|接到|换到)\s*"
    rf"(?P<target>{TRANSFER_VARIANT_LABEL})(?:\s*使用)?",
    re.IGNORECASE,
)
OTHER_VERSION_TRANSFER_RE = re.compile(
    r"(?:把|将)(?:其他|另一|不同)(?:SKU|版本|型号|款式)的[^，。；\n]{1,24}"
    r"(?:用于|配给|给|交给|提供给|转给|装配到|装配给|安装到|安装给|接到|换到)\s*"
    r"(?:当前|目标|本次)(?:商品|SKU|版本|型号)",
    re.IGNORECASE,
)
OTHER_SKU_BORROW_RE = re.compile(
    r"(?:(?:借用|取用|采用|移用|套用)(?:其他|另一|另一个|不同)\s*SKU\s*的[^，。；\n]{1,28}|"
    r"(?:把|将)\s*(?:其他|另一|另一个|不同)\s*SKU\s*的[^，。；\n]{1,28}(?:借用|取用|采用|移用|套用))"
)
COLOR_COMPONENT_TRANSPLANT_RE = re.compile(
    r"(?P<source>红色|蓝色|黑色|白色|灰色|绿色|黄色|紫色|粉色|金色|银色)"
    r"[^，。；\n]{0,12}(?:装到|装入|移植到|拼到|接到|换到)"
    r"(?P<target>红色|蓝色|黑色|白色|灰色|绿色|黄色|紫色|粉色|金色|银色)"
    r"\s*(?:SKU|款|版|型号)",
    re.IGNORECASE,
)
COLOR_COMPONENT_MIX_RE = re.compile(
    r"(?P<source>红色|蓝色|黑色|白色|灰色|绿色|黄色|紫色|粉色|金色|银色)(?:款)?的?"
    r"[^，。；\n]{1,16}(?:搭配|配上|组合|结合)"
    r"(?P<target>红色|蓝色|黑色|白色|灰色|绿色|黄色|紫色|粉色|金色|银色)(?:款)?的?"
    r"[^，。；\n]{1,16}(?:生成|形成|做成|组成|成为|打造)[^，。；\n]{0,6}(?:一款|一个|新品|商品)",
    re.IGNORECASE,
)
STYLE_FUSION_RE = re.compile(
    r"(?i)(?:"
    r"(?:融合|混合|平均|拼接|拼装|合并|组合|合成|混成)"
    r"(?:多个|不同|两个|两种)?\s*(?:款式|版本)"
    r"[^，。；\n]{0,18}(?:为|成|做成|拼成|合成|合并成|组合成)"
    r"(?:一个|一款)?(?:主体|商品|产品|款|版本)|"
    r"(?:把|将)(?:多个|不同|两个|两种)\s*(?:款式|版本)"
    r"[^，。；\n]{0,18}(?:拼成|合成|做成|合并成|组合成)"
    r"(?:一个|一款)?(?:主体|商品|产品|款|版本)"
    r")"
)
VARIANT_COMBINATION_RE = re.compile(
    rf"(?:(?P<source>{TRANSFER_VARIANT_LABEL})\s*(?:和|与|、)\s*"
    rf"(?P<target>{TRANSFER_VARIANT_LABEL})\s*(?:混搭|混合|拼搭|合用|共用|混装|拼装)"
    r"(?:成|为)?(?:一个|一款)?(?:主体|商品|产品)?|"
    r"(?:混搭|混合|拼搭|合用|共用|混装|拼装)\s*"
    rf"{TRANSFER_VARIANT_LABEL}\s*(?:和|与|、)\s*{TRANSFER_VARIANT_LABEL}"
    r"[^，。；\n]{0,12}(?:主体|商品|产品|结构|零件|部件)|"
    r"(?:不同|多个|两个|两种)\s*(?:型号|版本|款式)\s*"
    r"(?:混搭|混合|拼搭|合用|共用|混装|拼装)"
    r"(?:成|为)?(?:一个|一款)?(?:主体|商品|产品)?|"
    r"(?:在|于)(?:同一|一个)主体[^，。；\n]{0,12}(?:使用|采用|共用|合用)"
    rf"[^，。；\n]{{0,20}}{TRANSFER_VARIANT_LABEL}\s*(?:和|与|、)\s*"
    rf"{TRANSFER_VARIANT_LABEL}[^，。；\n]{{0,8}}(?:零件|部件|结构))"
)
VARIANT_LABEL = r"(?:[A-Za-z0-9_-]{1,12}款|[\u4e00-\u9fff]{1,8}款)"
CROSS_VARIANT_COMPONENT_PAIR_RE = re.compile(
    rf"(?:在\s*)?(?P<source>{VARIANT_LABEL})\s*的?"
    r"(?P<source_part>[A-Za-z0-9\u4e00-\u9fff_-]{1,12}?)\s*"
    r"(?:上\s*)?(?:搭配|配上|配合|配以|加装|安装|装上|搭上|换上|沿用|安到|叠上|采用|使用|"
    r"加(?!强|工|入|速|热|载|密|大|宽|长|厚)|配(?!色|置|方|件|套|额|乐|对|比))\s*"
    rf"(?P<target>{VARIANT_LABEL})\s*的?"
    r"(?P<target_part>[A-Za-z0-9\u4e00-\u9fff_-]{1,12})",
    re.IGNORECASE,
)
VARIANT_COMPONENT_REUSE_RE = re.compile(
    rf"(?:借用?|套用?|承接|吸收)\s*(?P<source>{VARIANT_LABEL})\s*的?\s*"
    r"(?P<source_part>[A-Za-z0-9\u4e00-\u9fff_-]{1,12})",
    re.IGNORECASE,
)
DETACHED_COMPONENT_REUSE_RE = re.compile(
    rf"(?:拆下|取下|卸下)\s*(?P<source>{VARIANT_LABEL})\s*的?\s*"
    r"(?P<source_part>[A-Za-z0-9\u4e00-\u9fff_-]{1,12}?)\s*"
    r"(?:给|供|用于)\s*(?:另一|其他|不同)(?:款|SKU)[^，。；\n]{0,8}(?:使用|采用|安装|装配)",
    re.IGNORECASE,
)
HYBRID_NEW_PRODUCT_RE = re.compile(
    r"取长补短[^，。；\n]{0,12}(?:做|制成|生成|打造|形成)(?:一款|一个)?(?:新品|新款|商品)"
)
SAFE_MULTI_SKU_COMPOSITION_RE = re.compile(
    r"(?:左右|并列|同屏|多款)?(?:对比图|对照图|总览(?:图|画面)?|组合陈列|同屏展示)"
)
INDEPENDENT_SKU_LAYER_RE = re.compile(
    r"(?:各|每个|每一)\s*SKU[^。；\n]{0,28}(?:独立商品层|分别生成|分层生成|保持独立|互不融合|互不混合)"
)
UNSAFE_SINGLE_PRODUCT_RE = re.compile(
    r"(?:同一|一个)[^，。；\n]{0,8}(?:商品层|商品身份|商品主体|主体|商品|款|版本)|"
    r"(?:生成|形成|做成|组成|成为|打造)[^，。；\n]{0,6}(?:一款|一个|新品|商品)"
)
UNRESOLVED_CONTEXT_RE = re.compile(
    r"(?:(?:延续|沿用|接续|承接)(?:前|上一)(?:页|模块|屏|张|帧|图)[^，。；\n]{0,24}|"
    r"(?:与|跟)(?:前一|前|上一)(?:页|模块|屏|张|帧|图)[^，。；\n]{0,24}(?:保持(?:一致|相同)|无缝衔接|一致|相同)|"
    r"(?:前|上一)(?:页|模块|屏|张|帧|图)[^，。；\n]{0,24}(?:保持(?:一致|相同|同样)|无缝衔接|一致|相同)|"
    r"(?:依据|根据|按照|参照)(?:前|上一)(?:页|模块|屏|张|帧|图)[^，。；\n]{0,24}(?:设定|背景|色调|主光|光线|画面|表现)?|"
    r"同上|按前文|按之前方案|(?:依照|按照|根据)前述方案|"
    r"(?:沿用|参考|参照|照搬|保持)(?:上一张|上一帧|上一镜|上图)|"
    r"(?:沿用|参考|参照|照搬)(?:前图|前一帧|前一镜)|"
    r"与(?:上一张|上一帧|上一镜)相同|保持与(?:前一张|前一帧|前一镜)一致|"
    r"照上文执行|与(?:前图|前一帧|前一镜)一致|承接(?:前一页|上一帧|上一镜)|"
    r"(?:按|按照|依据|依照|根据)(?:上述|上面的)(?:商品信息|商品资料|资料|信息|方案)|"
    r"(?:按|按照|依据|依照|根据)已确认信息|"
    r"(?:继续使用|延续|复用|承接|参照|按照|按)(?:刚才|先前|之前|前面)"
    r"[^，。；\n]{0,12}(?:商品|页面|画面|定稿|设定|方案)?|"
    r"商品设定同前|"
    r"(?:按|按照|依据|参照|读取|遵循|根据)(?:已确认)?商品卡[^，。；\n]{0,16}|"
    r"与(?:已确认)?商品卡[^，。；\n]{0,12}保持一致|"
    r"(?:冲突|矛盾|不一致)?[^，。；\n]{0,8}(?:以|服从)(?:已确认)?商品卡(?:结论)?(?:为准)?)"
)
PLACEHOLDER_RE = re.compile(
    r"(?:TODO|TBD|待定|待补|待更新|待完善|后续(?:补充|填写|确定|完善)|"
    r"稍后(?:补充|填写|确定|完善)|占位(?:符|内容)?|省略号|…|"
    r"\{\{[^{}\n]{1,80}\}\}|\$\{[^{}\n]{1,80}\}|"
    r"<\s*(?:填写|待补|插入|替换|输入|占位|TODO|TBD|"
    r"[A-Z][A-Z0-9_ -]{2,}|[\u3400-\u9fff]{2,}(?:名称|产品|商品|卖点|内容|文案))[^>\n]*>|"
    r"\[\s*(?:INSERT|PLACEHOLDER|TODO|TBD|填写|待补|插入|替换)[^\]\n]*\]|"
    r"\[\[[^\]\n]{1,80}\]\]|"
    r"【(?:名称|内容|填写|待补|稍后|补充|确定)[^】]*】|"
    r"[⟦〈《「『]\s*(?:填写|待填|待补|插入|替换|输入|TODO|TBD|"
    r"(?:商品|产品)?名称|[A-Z][A-Z0-9_ -]{2,})[^⟧〉》」』]{0,60}[⟧〉》」』]|"
    r"(?:商品|产品)?名称\s*[：:]\s*(?:待填写|填写|待补|待更新|待完善|TODO|TBD)|"
    r"(?<![A-Za-z0-9_])X{3,}\s*(?:商品|产品|名称|卖点|文案)?"
    r"|\.\.\.)",
    re.IGNORECASE,
)


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


def _normalize_security_text(text: str) -> str:
    """统一兼容字符并移除零宽/组合附加符号，仅用于安全规则扫描。"""

    normalized = (
        unicodedata.normalize("NFKD", text)
        .translate(SECURITY_CONFUSABLES)
        .translate(SECURITY_TRADITIONAL)
        .translate(SECURITY_PUNCTUATION)
    )
    return "".join(
        character
        for character in normalized
        if unicodedata.category(character) not in {"Cf", "Mn", "Mc", "Me"}
    )


def _erase_preserved_originals(text: str) -> str:
    """从内部流程扫描中移除明确标注为可见原文的内容。

    可见界面/包装原文可能合法包含“候选方案”“调试字段”等词，不能因此
    被当成模型的内部审查记录；若引号内明确声明后文是生成指令，则保留
    该声明及其后内容继续检查，避免借原文引号隐藏真正的指令。
    """

    spans: list[tuple[int, int]] = []
    for match in PRESERVED_ORIGINAL_RE.finditer(text):
        original_start, original_end = match.span("original")
        instruction_marker = NON_ORIGINAL_INSTRUCTION_RE.search(match.group("original"))
        if instruction_marker is None:
            spans.append((original_start, original_end))
        else:
            marker_start = original_start + instruction_marker.start()
            if marker_start > original_start:
                spans.append((original_start, marker_start))
    return _erase_spans(text, spans)


def _parse_preamble(preamble: str) -> None:
    lines = [line.strip() for line in preamble.splitlines() if line.strip()]
    if not lines:
        return
    if len(lines) != 1 or not QUANTITY_NOTE_RE.fullmatch(lines[0]):
        raise StoryboardValidationError("分镜前只允许一行“> 数量说明：……”；不得添加参考图索引或额外报告")


def _instruction_language_text(text: str) -> str:
    """移除明确要求逐字保留的可见原文，只判断生成指令本身的语言。"""

    spans: list[tuple[int, int]] = []
    for match in PRESERVED_ORIGINAL_RE.finditer(text):
        original_start, original_end = match.span("original")
        instruction_marker = NON_ORIGINAL_INSTRUCTION_RE.search(match.group("original"))
        if instruction_marker is None:
            spans.append((original_start, original_end))
            continue
        preserved_end = original_start + instruction_marker.start()
        if preserved_end > original_start:
            spans.append((original_start, preserved_end))
    return _erase_spans(text, spans)


def _is_mainly_chinese(text: str, *, minimum_chinese: int = 4) -> bool:
    instruction_text = _normalize_security_text(_instruction_language_text(text))
    if NON_CHINESE_SCRIPT_RE.search(instruction_text):
        return False
    chinese_count = len(CHINESE_RE.findall(instruction_text))
    latin_character_count = len(LATIN_CHARACTER_RE.findall(instruction_text))
    return chinese_count >= minimum_chinese and chinese_count >= latin_character_count


FIELD_ENGLISH_STOPWORDS = {
    "a", "an", "and", "background", "camera", "create", "for", "generate",
    "cinematic", "commercial", "hd", "hyperrealistic", "image", "keep", "layout",
    "lighting", "luxury", "maintain", "of", "on", "packshot", "photo",
    "photography", "premium", "product", "professional", "realistic", "render",
    "scene", "studio", "the", "to", "uhd", "ultra", "use", "visual", "with",
}
GENERIC_VISUAL_MODEL_TOKENS = {"3d", "4k", "8k", "ai", "cmyk", "hd", "hdr", "rgb", "uhd"}


def _is_descriptive_field_language_valid(text: str) -> bool:
    """公开描述字段以中文为主；仅放行紧凑品牌/型号标识与逐字原文。"""

    instruction_text = _normalize_security_text(_instruction_language_text(text))
    if NON_CHINESE_SCRIPT_RE.search(instruction_text):
        return False
    chinese_count = len(CHINESE_RE.findall(instruction_text))
    latin_tokens = re.findall(r"[A-Za-z][A-Za-z0-9._/-]*", instruction_text)
    latin_count = len(LATIN_CHARACTER_RE.findall(instruction_text))
    if chinese_count and chinese_count >= latin_count:
        return True
    if chinese_count:
        return not any(token.casefold() in FIELD_ENGLISH_STOPWORDS for token in latin_tokens)
    if not latin_tokens:
        return True
    # A standalone compact identifier such as SKU-A or iPhone16 is not an
    # instruction and may be used as a product/model label.
    compact = instruction_text.strip()
    if re.fullmatch(r"SKU[-_ ]?[A-Za-z0-9._-]+", compact, re.IGNORECASE):
        return True
    compact_tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9._/+()-]*", compact)
    specific_alphanumeric = any(
        re.search(r"[A-Za-z]", token)
        and re.search(r"\d", token)
        and token.casefold() not in GENERIC_VISUAL_MODEL_TOKENS
        for token in compact_tokens
    )
    mixed_case_brand = any(
        any(character.islower() for character in token)
        and any(character.isupper() for character in token[1:])
        for token in compact_tokens
    )
    specific_acronym = any(
        token.isupper()
        and 2 <= len(token) <= 10
        and token.casefold() not in GENERIC_VISUAL_MODEL_TOKENS
        for token in compact_tokens
    )
    numeric_with_name = any(token.isdigit() for token in compact_tokens) and any(
        token[:1].isupper() and any(character.islower() for character in token)
        for token in compact_tokens
    )
    has_model_signal = specific_alphanumeric or mixed_case_brand or specific_acronym or numeric_with_name
    has_english_instruction_token = any(
        token.casefold() in FIELD_ENGLISH_STOPWORDS
        or any(token.casefold().startswith(word) for word in ("cinematic", "hyperrealistic", "packshot", "render"))
        for token in compact_tokens
    )
    if (
        1 <= len(compact_tokens) <= 6
        and len(compact) <= 48
        and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/+() -]*", compact)
        and has_model_signal
        and not has_english_instruction_token
    ):
        return True
    return False


def _chinese_number_to_int(value: str) -> int:
    digits = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
              "六": 6, "七": 7, "八": 8, "九": 9}
    units = {"十": 10, "百": 100, "千": 1000, "万": 10000}
    total = 0
    section = 0
    number = 0
    for character in value:
        if character in digits:
            number = digits[character]
            continue
        unit = units[character]
        if unit == 10000:
            section += number
            total += (section or 1) * unit
            section = 0
        else:
            section += (number or 1) * unit
        number = 0
    return total + section + number


def _reference_count(value: str) -> int:
    count = int(value) if re.fullmatch(r"-?\d+", value) else _chinese_number_to_int(value)
    if count <= 0:
        raise StoryboardValidationError("参考视觉数量必须大于零")
    return count


def _reference_count_mode(counts: list[tuple[str, str]]) -> str:
    total = 0
    for value, unit in counts:
        count = _reference_count(value)
        if unit in {"组", "套", "批"}:
            return "多张"
        total += count
    return "单张" if total == 1 else "多张"


def _generation_input_segment(text: str) -> str:
    """优先分析“本张实际输入”后的文字，避免把全局分析范围误当生成输入。"""

    for pattern in GENERATION_INPUT_MARKER_PATTERNS:
        marker = re.search(pattern, text)
        if marker:
            return text[marker.start() :]
    fallback = re.search(r"本张", text)
    return text[fallback.start() :] if fallback else text


GENERATION_INPUT_MARKER_PATTERNS = (
        r"本张实际(?:向(?:图像|生成)?模型)?(?:只|仅)?(?:提供|输入|使用|采用|选用)",
        r"实际向(?:图像|生成)?模型(?:只|仅)?(?:提供|输入|使用|采用|选用)",
        r"向(?:图像|生成)?模型(?:只|仅)?(?:提供|输入|使用|采用|选用)",
        r"(?:本次|本张)(?:实际)?生成(?:输入|参考输入)",
        r"实际生成输入|生成参考输入",
)
GENERATION_INPUT_MARKER_RE = re.compile(
    "(?:" + "|".join(GENERATION_INPUT_MARKER_PATTERNS) + ")"
)
NO_REFERENCE_INPUT_RE = re.compile(
    r"(?:不|未|没有|并未|尚未|仍未|无需|无须)(?:向(?:图像|生成)?模型)?"
    r"(?:提供|输入|使用|采用|选用)(?:任何|任何一张|任何参考)?(?:参考图|参考视觉|商品图|资料)"
)


def _scope_mode_from_clause(scope_clause: str) -> str | None:
    """只解析一个实际生成输入范围短句，不把后续说明混入范围。"""

    modes: set[str] = set()
    if ALL_REFERENCE_SCOPE_RE.search(scope_clause):
        modes.add("全部")
    for match in NAMED_REFERENCE_SCOPE_RE.finditer(scope_clause):
        scope = match.group("scope") or match.group("scope_after")
        modes.add("单张" if scope == "单张" else "多张")
    counted_references: dict[tuple[int, int], tuple[str, str]] = {}
    for pattern in (
        COUNTED_REFERENCE_BEFORE_RE,
        COUNTED_REFERENCE_AFTER_RE,
        CONTINUED_COUNTED_REFERENCE_RE,
    ):
        for match in pattern.finditer(scope_clause):
            counted_references[match.span("count")] = (match.group("count"), match.group("unit"))
    if counted_references:
        modes.add(_reference_count_mode(list(counted_references.values())))
    if CONJOINED_REFERENCE_SCOPE_RE.search(scope_clause) and not counted_references:
        modes.add("多张")
    if "全部" in modes and modes <= {"全部", "多张"}:
        return "全部"
    return next(iter(modes)) if len(modes) == 1 else None


def _reference_mode(text: str) -> str | None:
    segment = _generation_input_segment(text)
    scope_clause = re.split(r"[。；\n]", segment, maxsplit=1)[0]
    mode = _scope_mode_from_clause(scope_clause)
    if mode is None:
        return None

    # 只允许一个明确的实际输入结论。全量与多张可以互相补充，单张与
    # 多张/全量冲突；后置“实际不输入任何参考图”同样使范围失效。
    markers = list(GENERATION_INPUT_MARKER_RE.finditer(text))
    first_marker = markers[0] if markers else None
    if first_marker is not None:
        for marker in markers[1:]:
            clause_end_positions = [text.find(separator, marker.end()) for separator in "。；\n"]
            clause_end = min((position for position in clause_end_positions if position >= 0), default=len(text))
            later_clause = text[marker.start() : clause_end]
            if NO_REFERENCE_INPUT_RE.search(later_clause):
                return None
            later_mode = _scope_mode_from_clause(later_clause)
            if later_mode is None:
                continue
            if {mode, later_mode} <= {"全部", "多张"}:
                continue
            if later_mode != mode:
                return None
    # 处理未带“模型”字样的后置否定，例如“但本张实际不输入任何参考图”。
    first_start = first_marker.start() if first_marker is not None else 0
    if NO_REFERENCE_INPUT_RE.search(text[first_start:]):
        return None
    return mode


def _is_locally_negated(text: str, start: int) -> bool:
    clause_start = max(text.rfind(separator, 0, start) for separator in "，。；\n") + 1
    prefix = text[clause_start:start]
    return DIRECT_NEGATION_RE.search(prefix) is not None


def _has_positive_rule(pattern: re.Pattern[str], text: str) -> bool:
    return any(not _is_locally_negated(text, match.start()) for match in pattern.finditer(text))


def _is_evidence_bounded_diagram_clause(text: str, start: int, end: int) -> bool:
    """区分有证据约束的结构图型与把未知视图标成“示意”的推断标签。"""

    sentence_start = max(text.rfind(separator, 0, start) for separator in "。；\n") + 1
    sentence_ends = [text.find(separator, end) for separator in "。；\n"]
    sentence_end = min((position for position in sentence_ends if position >= 0), default=len(text))
    sentence = text[sentence_start:sentence_end]
    return bool(
        EVIDENCE_BOUNDED_DIAGRAM_RE.search(sentence)
        and not UNSAFE_DIAGRAM_INFERENCE_RE.search(sentence)
    )


def _contains_asserted_view_annotation(text: str) -> bool:
    """只拦截把推断/置信度写成画面事实的表述，允许明确的禁令。"""

    for match in FORBIDDEN_VIEW_ANNOTATION_RE.finditer(text):
        if _is_locally_negated(text, match.start()):
            continue
        if _is_evidence_bounded_diagram_clause(text, match.start(), match.end()):
            continue
        clause_start = max(text.rfind(separator, 0, match.start()) for separator in "，。；\n") + 1
        prefix = text[clause_start : match.start()]
        if re.search(
            r"(?:不得|不可|禁止|避免|防止|杜绝|切勿|严禁|不能|不要|不应|不把|不将)"
            r"[^，。；\n]{0,24}$",
            prefix,
        ):
            continue
        return True
    return False


SAFE_VIEW_METADATA_EXCLUSION_RE = re.compile(
    r"(?:(?:不能确认|无法确认|不确定|未知|未确认)[^，。；\n]{0,24}"
    r"(?:隐藏(?:结构|配件|视图)|背面|底部|内部|拆解|接口)"
    r"[^。；\n]{0,24}(?:不补画|不生成|不呈现|不写入|不采用|不使用|排除|舍弃)|"
    r"(?:不补画|不生成|不呈现|不写入|不采用|不使用|排除|舍弃)"
    r"[^。；\n]{0,24}(?:隐藏(?:结构|配件|视图)|背面|底部|内部|拆解|接口))"
)


def _contains_forbidden_view_metadata(text: str) -> bool:
    """拦截隐藏视图附近的流程/评分标签，保留明确排除或禁止表达。"""

    for match in FORBIDDEN_VIEW_METADATA_RE.finditer(text):
        if _is_locally_negated(text, match.start()):
            continue
        clause_start = max(text.rfind(separator, 0, match.start()) for separator in "，。；\n") + 1
        clause_ends = [text.find(separator, match.end()) for separator in "，。；\n"]
        clause_end = min((position for position in clause_ends if position >= 0), default=len(text))
        clause = text[clause_start:clause_end]
        if SAFE_VIEW_METADATA_EXCLUSION_RE.search(clause):
            continue
        if _is_evidence_bounded_diagram_clause(text, match.start(), match.end()):
            continue
        return True
    return False


def _has_global_reference_analysis(text: str) -> bool:
    if NEGATED_GLOBAL_ANALYSIS_RE.search(text) or _has_positive_rule(
        GLOBAL_ANALYSIS_INCOMPLETE_RE, text
    ):
        return False
    for match in REFERENCE_GLOBAL_ANALYSIS_RE.finditer(text):
        if _is_locally_negated(text, match.start()):
            continue
        clause_end_positions = [text.find(separator, match.end()) for separator in "。；\n"]
        clause_end = min((position for position in clause_end_positions if position >= 0), default=len(text))
        if POSTPOSED_GLOBAL_ANALYSIS_UNRESOLVED_RE.search(text[match.end() : clause_end]):
            continue
        return True
    return False


def _has_safe_reference_partition(text: str) -> bool:
    if NEGATED_TARGET_FILTER_RE.search(text) or NEGATED_SKU_ISOLATION_RE.search(text):
        return False
    generation_input = _generation_input_segment(text)
    input_clause = re.split(r"[，。；\n]", generation_input, maxsplit=1)[0]
    # “实际提供多张并非同款参考图”不能被后面的“同款资料一致”覆盖。
    # 只在本张实际生成输入的首个范围短句中检查，避免把明确排除的其他
    # SKU 说明误判成输入污染。
    if NEGATED_SAME_TARGET_REFERENCE_RE.search(input_clause):
        return False
    # “其他 SKU 不作为生成参考输入”是合法的隔离声明；同一生成输入范围
    # 后面若又明确写成“其他 SKU 传入/输入生成模型”，则以后置肯定为准并拒绝。
    for match in OTHER_SKU_GENERATION_INPUT_RE.finditer(generation_input):
        if NEGATED_OTHER_SKU_INPUT_RE.search(match.group()):
            continue
        return False
    if SAME_TARGET_REFERENCE_RE.search(input_clause) or _has_positive_rule(NAMED_TARGET_SELECTION_RE, text):
        return True
    return _has_positive_rule(REFERENCE_TARGET_FILTER_RE, text) and _has_positive_rule(
        REFERENCE_SKU_ISOLATION_RE, text
    )


def _has_resolved_reference_conflict(text: str) -> bool:
    """只接受明确一致或已写明采用/舍弃结果的参考资料声明。"""

    if REFERENCE_CONFLICT_UNRESOLVED_RE.search(text) or REFERENCE_PENDING_CONCLUSION_RE.search(text):
        return False
    for match in REFERENCE_CONFLICT_RESOLVED_RE.finditer(text):
        clause_start = max(text.rfind(separator, 0, match.start()) for separator in "，。；\n") + 1
        clause_ends = [text.find(separator, match.end()) for separator in "，。；\n"]
        clause_end = min((position for position in clause_ends if position >= 0), default=len(text))
        clause = text[clause_start:clause_end]
        if REFERENCE_CONFLICT_UNRESOLVED_RE.search(clause):
            continue
        if _is_locally_negated(text, match.start()):
            continue
        return True
    return False


def _has_general_pending_reference_status(text: str) -> bool:
    """识别多参考资料中的未决状态；明确舍弃未知事实时允许继续。"""

    for match in GENERAL_REFERENCE_PENDING_RE.finditer(text):
        if EXPLICIT_PROHIBITION_RE.match(text, match.start()):
            continue
        clause_start = max(text.rfind(separator, 0, match.start()) for separator in "。；\n") + 1
        clause_ends = [text.find(separator, match.end()) for separator in "。；\n"]
        clause_end = min((position for position in clause_ends if position >= 0), default=len(text))
        clause = text[clause_start:clause_end]
        if SAFE_PENDING_EXCLUSION_RE.search(clause):
            continue
        return True
    return False


def _has_unresolved_reference_marker(text: str) -> bool:
    patterns = (
        REFERENCE_CONFLICT_UNRESOLVED_RE,
        REFERENCE_PENDING_CONCLUSION_RE,
        REFERENCE_SAME_VARIANT_PENDING_RE,
    )
    for pattern in patterns:
        for match in pattern.finditer(text):
            if _is_locally_negated(text, match.start()):
                continue
            clause_start = max(text.rfind(separator, 0, match.start()) for separator in "。；\n") + 1
            clause_ends = [text.find(separator, match.end()) for separator in "。；\n"]
            clause_end = min((position for position in clause_ends if position >= 0), default=len(text))
            clause = text[clause_start:clause_end]
            if SAFE_PENDING_EXCLUSION_RE.search(clause):
                continue
            return True
    return False


def _reference_conflicts_are_resolved(text: str) -> bool:
    text = _erase_preserved_originals(text)
    if _has_unresolved_reference_marker(text) or _has_general_pending_reference_status(text):
        return False
    if not REFERENCE_CONFLICT_SIGNAL_RE.search(text):
        return bool(
            REFERENCE_POSITIVE_RESOLUTION_RE.search(text)
            or SAFE_PENDING_EXCLUSION_RE.search(text)
        )
    return _has_resolved_reference_conflict(text)


def _is_fusion_prohibited(text: str, start: int) -> bool:
    clause_start = max(text.rfind(separator, 0, start) for separator in "，。；\n") + 1
    return FUSION_PROHIBITION_RE.search(text[clause_start:start]) is not None


def _is_safe_multi_sku_composition(text: str, start: int, end: int) -> bool:
    """允许各SKU保持独立商品层的对比、总览或并列陈列。"""

    sentence_start = max(text.rfind(separator, 0, start) for separator in "。；\n") + 1
    sentence_ends = [text.find(separator, end) for separator in "。；\n"]
    sentence_end = min((position for position in sentence_ends if position >= 0), default=len(text))
    sentence = text[sentence_start:sentence_end]
    return (
        SAFE_MULTI_SKU_COMPOSITION_RE.search(sentence) is not None
        and INDEPENDENT_SKU_LAYER_RE.search(sentence) is not None
        and UNSAFE_SINGLE_PRODUCT_RE.search(sentence) is None
    )


def _normalized_variant_label(value: str) -> str:
    """比较款式标签时忽略大小写与空白，不改变公开提示词文本。"""

    return re.sub(r"\s+", "", value).casefold()


def _is_explanatory_fusion_clause(text: str, start: int, end: int) -> bool:
    """允许把跨款融合作为风险说明，而不是把它作为生成动作。"""

    clause_start = max(text.rfind(separator, 0, start) for separator in "，。；\n") + 1
    prefix = text[clause_start:start]
    suffix = text[end:]
    return bool(
        EXPLANATORY_FUSION_PREFIX_RE.search(prefix)
        and EXPLANATORY_FUSION_SUFFIX_RE.search(suffix)
    )


def _contains_asserted_sku_fusion(text: str) -> bool:
    """只拦截肯定执行的跨SKU融合，允许负面提示词明确禁止它。"""

    for pattern in (SKU_FUSION_RE, NAMED_VARIANT_FUSION_RE, STYLE_FUSION_RE):
        for match in pattern.finditer(text):
            if _is_fusion_prohibited(text, match.start()):
                continue
            if _is_safe_multi_sku_composition(text, match.start(), match.end()):
                continue
            if _is_explanatory_fusion_clause(text, match.start(), match.end()):
                continue
            return True

    for pattern in (CROSS_VARIANT_TRANSFER_RE, OTHER_VERSION_TRANSFER_RE, VARIANT_COMBINATION_RE):
        for match in pattern.finditer(text):
            if _is_fusion_prohibited(text, match.start()):
                continue
            if _is_explanatory_fusion_clause(text, match.start(), match.end()):
                continue
            if pattern is VARIANT_COMBINATION_RE:
                source = match.groupdict().get("source")
                target = match.groupdict().get("target")
                if source and target and _normalized_variant_label(source) == _normalized_variant_label(target):
                    continue
                if _is_safe_multi_sku_composition(text, match.start(), match.end()):
                    continue
            else:
                source = match.groupdict().get("source")
                target = match.groupdict().get("target")
                if source and target and _normalized_variant_label(source) == _normalized_variant_label(target):
                    continue
            return True

    for match in CROSS_MODEL_TRANSPLANT_RE.finditer(text):
        if _normalized_variant_label(match.group("source")) == _normalized_variant_label(match.group("target")):
            continue
        if _is_fusion_prohibited(text, match.start()):
            continue
        return True
    for match in COLOR_COMPONENT_TRANSPLANT_RE.finditer(text):
        if match.group("source") == match.group("target"):
            continue
        if _is_fusion_prohibited(text, match.start()):
            continue
        return True
    for match in COLOR_COMPONENT_MIX_RE.finditer(text):
        if match.group("source") == match.group("target"):
            continue
        if _is_fusion_prohibited(text, match.start()):
            continue
        return True
    for match in CROSS_VARIANT_COMPONENT_PAIR_RE.finditer(text):
        if match.group("source").casefold() == match.group("target").casefold():
            continue
        if _is_fusion_prohibited(text, match.start()):
            continue
        if _is_safe_multi_sku_composition(text, match.start(), match.end()):
            continue
        return True
    for match in OTHER_SKU_BORROW_RE.finditer(text):
        if _is_fusion_prohibited(text, match.start()):
            continue
        return True
    for pattern in (
        VARIANT_COMPONENT_REUSE_RE,
        DETACHED_COMPONENT_REUSE_RE,
        HYBRID_NEW_PRODUCT_RE,
    ):
        for match in pattern.finditer(text):
            if _is_fusion_prohibited(text, match.start()):
                continue
            return True
    return False


def _contains_asserted_fact_mutation(text: str) -> bool:
    """拦截写实任务中肯定执行的事实篡改，保留用户确认的概念创作。"""

    for pattern in (ASSERTED_FACT_MUTATION_RE, EXPLICIT_PRODUCT_MUTATION_RE):
        for match in pattern.finditer(text):
            if _is_locally_negated(text, match.start()):
                continue
            if (
                CREATIVE_ENVIRONMENT_MUTATION_RE.search(match.group())
                and not EXPLICIT_PRODUCT_MUTATION_RE.search(match.group())
            ):
                continue
            clause_start = max(text.rfind(separator, 0, match.start()) for separator in "，。；\n") + 1
            if FACT_MUTATION_PROHIBITION_RE.search(text[clause_start:match.start()]):
                continue
            sentence_start = max(text.rfind(separator, 0, match.start()) for separator in "。；\n") + 1
            sentence_ends = [text.find(separator, match.end()) for separator in "。；\n"]
            sentence_end = min((position for position in sentence_ends if position >= 0), default=len(text))
            if CONFIRMED_CONCEPT_VARIATION_RE.search(text[sentence_start:sentence_end]):
                continue
            return True
    return False


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
    _parse_preamble(normalized[: blocks[0][0].start()])

    public_scan_text = _erase_preserved_originals(normalized)
    security_scan_text = _normalize_security_text(normalized)
    public_security_scan_text = _normalize_security_text(public_scan_text)
    if FORBIDDEN_SECRET_RE.search(security_scan_text):
        raise StoryboardValidationError("最终分镜疑似包含凭证或私钥")
    if (
        FORBIDDEN_INTERNAL_RE.search(public_security_scan_text)
        or _contains_forbidden_view_metadata(public_security_scan_text)
    ):
        raise StoryboardValidationError("最终分镜包含内部评分、审查过程或测试信息")
    if _contains_asserted_view_annotation(public_security_scan_text):
        raise StoryboardValidationError("最终分镜不得出现置信度或视图推断性质标签")
    if UNRESOLVED_CONTEXT_RE.search(public_security_scan_text):
        raise StoryboardValidationError("最终分镜不得依赖商品卡、上一张或前文等未提供上下文；请写明已裁决的具体事实")
    negative_prompt_spans = [match.span() for match in NEGATIVE_RE.finditer(normalized)]
    fusion_check_text = _erase_spans(normalized, negative_prompt_spans)
    instruction_check_text = _normalize_security_text(_erase_preserved_originals(fusion_check_text))
    if _contains_asserted_sku_fusion(instruction_check_text):
        raise StoryboardValidationError("最终分镜不得融合、混合、拼装或跨型号移植SKU内容")
    if _contains_asserted_fact_mutation(instruction_check_text):
        raise StoryboardValidationError("写实分镜不得虚构未知视图或改写商品结构、轮廓、颜色和品牌事实")
    if FIXED_REFERENCE_RE.search(public_security_scan_text) or NATURAL_FIXED_REFERENCE_RE.search(public_security_scan_text):
        raise StoryboardValidationError("最终分镜不得使用固定参考图编号；应综合说明单张、多张或全部参考图的使用方式")
    if PLACEHOLDER_RE.search(public_security_scan_text):
        raise StoryboardValidationError("最终分镜包含占位符或省略内容")

    pages: list[int] = []
    storyboard_ids: list[str] = []
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
        for field_name in DESCRIPTIVE_PUBLIC_FIELDS:
            field_value = fields.get(field_name)
            if field_value and not _is_descriptive_field_language_valid(field_value):
                raise StoryboardValidationError(f"{storyboard_id}的{field_name}必须以中文描述为主")

        output_object = fields["输出对象"]
        expected_prefix = OUTPUT_ID_PREFIXES.get(output_object)
        raw_prefix = storyboard_id.rsplit("-", 1)[0]
        actual_prefix = OUTPUT_PREFIX_ALIASES.get(raw_prefix, raw_prefix)
        if expected_prefix is None:
            raise StoryboardValidationError(f"{storyboard_id}包含不支持的输出对象：{output_object}")
        if actual_prefix != expected_prefix:
            raise StoryboardValidationError(
                f"{storyboard_id}的稳定编号与输出对象“{output_object}”不一致"
            )

        if not _is_mainly_chinese(positive) or not _is_mainly_chinese(negative, minimum_chinese=3):
            raise StoryboardValidationError(f"{storyboard_id}的正向与负面提示词必须以自然中文为主")
        reference_usage = fields["参考图使用"]
        reference_usage_scan = _normalize_security_text(_erase_preserved_originals(reference_usage))
        positive_scan = _normalize_security_text(_erase_preserved_originals(positive))
        field_mode = _reference_mode(reference_usage_scan)
        prompt_mode = _reference_mode(positive_scan)
        if (
            not REFERENCE_TERM_RE.search(reference_usage_scan)
            or not REFERENCE_TERM_RE.search(positive_scan)
            or field_mode is None
            or prompt_mode is None
            or not REFERENCE_PURPOSE_RE.search(reference_usage_scan)
            or not REFERENCE_PURPOSE_RE.search(positive_scan)
        ):
            raise StoryboardValidationError(
                f"{storyboard_id}必须在参考图使用字段和正向提示词中明确选择一张、多张或全部参考视觉作为本张生成输入，并说明提取用途"
            )
        if not _has_global_reference_analysis(reference_usage_scan):
            raise StoryboardValidationError(
                f"{storyboard_id}的参考图使用字段必须说明已先分析全部有效参考视觉，再声明本张实际生成输入"
            )
        if field_mode != prompt_mode:
            raise StoryboardValidationError(
                f"{storyboard_id}的参考图使用字段与正向提示词范围不一致：{field_mode} / {prompt_mode}"
            )
        if field_mode in {"多张", "全部"}:
            for location, value in (("参考图使用字段", reference_usage_scan), ("正向提示词", positive_scan)):
                if not _has_safe_reference_partition(value):
                    raise StoryboardValidationError(
                        f"{storyboard_id}的{location}使用多份参考视觉时，必须自然说明它们属于同一目标、只提取明确目标款，或按各SKU分别处理"
                    )
                if not _reference_conflicts_are_resolved(value):
                    raise StoryboardValidationError(
                        f"{storyboard_id}的{location}包含尚未解决的参考资料冲突；请写明最终采用与舍弃的具体结果"
                    )

    if len(pages) != len(set(pages)):
        raise StoryboardValidationError("页码不能重复")
    if partial:
        if pages != sorted(pages):
            raise StoryboardValidationError("局部返修页码必须递增")
    elif pages != list(range(1, len(pages) + 1)):
        raise StoryboardValidationError("完整图组页码必须从1连续递增")

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
