"""数据模型。

诊断规则以代码形式维护（faultdiag/knowledge.py），便于版本管理；
这里保留一张诊断记录表，用于统计「答案采纳率」「高频报错 TopN」等运营指标。
"""
from django.db import models


class DiagnosisRecord(models.Model):
    """一次诊断请求的留痕，用于可量化收益统计。"""

    raw_text = models.TextField("报错原文")
    top_rule = models.CharField("命中规则", max_length=64, blank=True)
    confidence = models.PositiveSmallIntegerField("置信度", default=0)
    elapsed_ms = models.FloatField("耗时(ms)", default=0)
    need_human = models.BooleanField("是否转人工", default=False)
    adopted = models.BooleanField("学生是否采纳", default=False)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        verbose_name = "诊断记录"
        verbose_name_plural = "诊断记录"
        ordering = ["-created_at"]

    def __str__(self):
        """后台列表展示。"""
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.top_rule} ({self.confidence})"
