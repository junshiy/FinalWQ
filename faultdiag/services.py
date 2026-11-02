"""诊断引擎：把一段报错文本匹配到知识库规则并给出可执行修复建议。

设计要点（对应任务一「机制说明」与「风险兜底」）：
1. 纯规则 + 正则匹配，离线可运行，无外部 API 依赖，响应稳定在毫秒级；
2. 置信度 = 命中模式数加权 + 关键词加权，低于阈值转人工，避免「一本正经胡说」；
3. 每条结论必须携带 source（引用溯源）与 verify（验证命令），不给出无法验证的答案。
"""
import re
import time
from typing import Dict, List, Optional

from .knowledge import RULES

# 置信度阈值：低于该值不直接给结论，转人工复核
MIN_CONFIDENCE = 55

# 单条规则的置信度上限，留出「不确定」空间
MAX_CONFIDENCE = 96


def _score(rule: Dict, text: str) -> Optional[Dict]:
    """计算单条规则的置信度。未命中任何模式返回 None。"""
    hits: List[str] = []
    for pattern in rule["patterns"]:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            hits.append(match.group(0).strip())
    if not hits:
        return None

    # 基础分：命中 1 个模式 68 分，之后每多命中一个 +12
    score = 68 + 12 * (len(hits) - 1)

    # 关键词加权：标签出现在原文里，说明上下文更贴合
    lowered = text.lower()
    for tag in rule.get("tags", []):
        if tag.lower() in lowered:
            score += 8

    # 命中模式占该规则全部模式的比例，作为覆盖度修正
    coverage = len(hits) / len(rule["patterns"])
    score += int(coverage * 10)

    return {
        "rule_id": rule["id"],
        "title": rule["title"],
        "confidence": min(score, MAX_CONFIDENCE),
        "cause": rule["cause"],
        "steps": rule["steps"],
        "verify": rule["verify"],
        "source": rule["source"],
        "matched": hits[:5],
    }


def diagnose(text: str, top_k: int = 3) -> Dict:
    """对报错文本做诊断，返回排序后的候选结论。

    Returns:
        {
            "query": 原文,
            "matches": [ {rule_id, title, confidence, cause, steps, verify, source, matched} ],
            "need_human": bool,
            "message": 提示语,
            "elapsed_ms": 耗时,
            "library_size": 知识库规则数,
        }
    """
    started = time.perf_counter()
    text = (text or "").strip()

    if not text:
        return {
            "query": "",
            "matches": [],
            "need_human": True,
            "message": "请粘贴报错信息后再提交。",
            "elapsed_ms": 0.0,
            "library_size": len(RULES),
        }

    matches = [result for rule in RULES if (result := _score(rule, text))]
    matches.sort(key=lambda item: item["confidence"], reverse=True)
    matches = matches[:top_k]

    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    top = matches[0]["confidence"] if matches else 0
    need_human = top < MIN_CONFIDENCE

    if not matches:
        message = "知识库未覆盖该报错，建议先执行 dmesg -T | tail -50 与 journalctl -xe 收集上下文，再提交给教师复核。"
    elif need_human:
        message = "匹配置信度低于阈值（55），结论仅供参考，请转人工复核后再执行高危命令。"
    else:
        message = "已按置信度排序给出候选根因，请先执行「验证」命令确认后再动手修改。"

    return {
        "query": text,
        "matches": matches,
        "need_human": need_human,
        "message": message,
        "elapsed_ms": elapsed_ms,
        "library_size": len(RULES),
    }
