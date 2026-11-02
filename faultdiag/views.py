"""视图：诊断首页（含表单提交）与 JSON API。"""
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from .knowledge import RULES
from .services import MIN_CONFIDENCE, diagnose

SAMPLE_LOG = """$ systemctl start nginx
Job for nginx.service failed because the control process exited with error code.
See "systemctl status nginx.service" and "journalctl -xe" for details.
$ nginx -t
nginx: [emerg] bind() to 0.0.0.0:80 failed (98: Address already in use)"""


@require_http_methods(["GET", "POST"])
def index(request):
    """诊断页面。POST 时执行诊断并回填结果。"""
    context = {
        "sample_log": SAMPLE_LOG,
        "query": "",
        "result": None,
        "library_size": len(RULES),
        "min_confidence": MIN_CONFIDENCE,
    }
    if request.method == "POST":
        text = (request.POST.get("log") or "").strip()
        context["query"] = text
        if text:
            context["result"] = diagnose(text, top_k=3)
    return render(request, "index.html", context)


@require_http_methods(["GET"])
def api_diagnose(request):
    """GET /api/diagnose?q=<报错文本> 返回 JSON，便于脚本或前端异步调用。"""
    text = request.GET.get("q", "")
    return JsonResponse(diagnose(text), json_dumps_params={"ensure_ascii": False})
