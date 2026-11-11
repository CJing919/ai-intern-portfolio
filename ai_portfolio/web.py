"""Dependency-free local web demo for the portfolio."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .content.analytics import ContentAnalytics
from .content.pipeline import ContentWorkflow
from .environment.bid import BidAssistant
from .rag.agent import CustomerServiceAgent
from .rag.eval import evaluate


INDEX_HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI 产品 / Agent 作品集 Demo</title>
<style>
:root{--ink:#16241e;--muted:#65736c;--green:#0e5a43;--mint:#eaf4ef;--line:#d9e5df;--bg:#f7faf8;--amber:#a76512}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.65 "Microsoft YaHei","PingFang SC",system-ui,sans-serif}
header{background:linear-gradient(120deg,#0e5a43,#174d3c 55%,#203a31);color:#fff;padding:34px 28px 28px}
.wrap{max-width:1120px;margin:0 auto}header .wrap{display:flex;justify-content:space-between;gap:24px;align-items:flex-end;flex-wrap:wrap}
h1{font-size:30px;line-height:1.2;margin:0 0 8px;letter-spacing:.5px}
.sub{color:#cfe3da;max-width:760px}.badge{display:inline-block;border:1px solid #8fc3ae;color:#dff3ea;border-radius:999px;padding:2px 10px;font-size:12px;margin-bottom:10px}
main{max-width:1120px;margin:0 auto;padding:24px 18px 48px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin-top:-36px}
.kpi{background:#fff;border:1px solid var(--line);border-radius:12px;padding:14px 16px;box-shadow:0 8px 24px rgba(20,50,38,.06)}
.kpi b{display:block;font-size:24px;color:var(--green)}.kpi span{color:var(--muted);font-size:12px}
.tabs{display:flex;gap:8px;flex-wrap:wrap;margin:24px 0 14px}
.tab{border:1px solid var(--line);background:#fff;color:var(--ink);border-radius:999px;padding:8px 16px;cursor:pointer}
.tab.active{background:var(--green);color:#fff;border-color:var(--green)}
.panel{display:none;background:#fff;border:1px solid var(--line);border-radius:14px;padding:20px}
.panel.active{display:block}.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}@media(max-width:800px){.grid{grid-template-columns:1fr}}
label{display:block;font-size:12px;color:var(--muted);margin:8px 0 4px}
input,textarea,select{width:100%;border:1px solid #cbd9d2;border-radius:8px;padding:10px;font:inherit;background:#fbfdfc}
textarea{min-height:86px;resize:vertical}.row{display:flex;gap:10px;flex-wrap:wrap}.row>*{flex:1;min-width:140px}
button{margin-top:12px;background:var(--green);color:#fff;border:0;border-radius:8px;padding:10px 16px;font:inherit;cursor:pointer}
button:hover{background:#0b4a37}.answer{background:var(--mint);border-left:4px solid var(--green);border-radius:8px;padding:14px;white-space:pre-wrap;margin-top:14px;min-height:70px}
.meta{color:var(--muted);font-size:12px;margin-top:10px}.pill{display:inline-block;background:#f1f6f3;border:1px solid var(--line);border-radius:999px;padding:1px 8px;margin:2px 4px 2px 0;font-size:12px}
details{margin-top:10px;color:var(--muted)}pre{background:#0f1d18;color:#d9efe4;padding:12px;border-radius:8px;overflow:auto;font-size:12px;line-height:1.5}
.note{background:#fff8e8;border:1px solid #f0d9aa;color:#6b4b18;border-radius:8px;padding:10px 12px;font-size:12px;margin:14px 0}
h2{font-size:19px;margin:0 0 6px}h3{font-size:15px;margin:14px 0 4px}.muted{color:var(--muted)}a{color:var(--green)}
</style>
</head>
<body>
<header><div class="wrap">
<div><div class="badge">SYNTHETIC DATA · OFFLINE DEMO</div><h1>AI 产品 / Agent 作品集</h1>
<div class="sub">客服 RAG Agent、内容与数据 Workflow、环保投标助手。默认不调用外部模型，所有结果可复现；数据为合成数据。</div></div>
<div class="sub">Python 标准库 · 无 API Key · 一键运行</div>
</div></header>
<main>
<div class="kpis" id="kpis"></div>
<div class="note">这是作品集 Demo，不是真实企业系统。所有公司、价格、政策、指标均为合成数据；请勿将 Demo 结果包装为真实实习产出。</div>
<div class="tabs">
<button class="tab active" data-tab="agent">1. 客服 Agent</button>
<button class="tab" data-tab="content">2. 内容工作流</button>
<button class="tab" data-tab="analytics">3. 数据问答</button>
<button class="tab" data-tab="bid">4. 投标助手</button>
</div>

<section class="panel active" id="agent">
<h2>客服 RAG Agent</h2><div class="muted">意图识别 → 工具调用 / BM25 检索 → 引用 → 置信度与转人工。</div>
<div class="grid"><div>
<label>用户问题</label><textarea id="agent-q">租赁 2 台移动式污水处理设备 10 天，大概多少钱？</textarea>
<div class="row"><button onclick="askAgent()">运行 Agent</button><button onclick="setAgent('订单 EQ2026003 现在什么进度？')">订单查询</button><button onclick="setAgent('设备故障三天没人处理，我要投诉，转人工')">转人工</button></div>
</div><div><div class="answer" id="agent-a">等待运行…</div><details><summary>查看 tool_calls / citations</summary><pre id="agent-json"></pre></details></div></div>
</section>

<section class="panel" id="content">
<h2>内容生产 Workflow</h2><div class="muted">Brief → 标题 / 脚本 / 配图提示词 → 合规检查 → 人工审核状态。</div>
<div class="grid"><div>
<label>选题</label><input id="content-topic" value="污水设备租赁的 5 个成本坑">
<div class="row"><div><label>渠道</label><select id="content-channel"><option>公众号</option><option>小红书</option><option>视频号</option></select></div><div><label>人群</label><input id="content-audience" value="制造企业 EHS"></div></div>
<button onclick="runContent()">生成内容包</button>
</div><div><div class="answer" id="content-a">等待生成…</div><details><summary>查看完整 JSON</summary><pre id="content-json"></pre></details></div></div>
</section>

<section class="panel" id="analytics">
<h2>运营数据问答</h2><div class="muted">对 90 条合成内容数据做指标聚合与规则化问答。</div>
<div class="grid"><div>
<label>问题</label><textarea id="analytics-q">哪个渠道线索最多？</textarea>
<div class="row"><button onclick="askAnalytics()">查询</button><button onclick="setAnalytics('最近一周线索趋势怎么样？')">趋势</button><button onclick="setAnalytics('哪个选题带来的线索最多？')">选题</button></div>
</div><div><div class="answer" id="analytics-a">等待查询…</div><details><summary>查看数据</summary><pre id="analytics-json"></pre></details></div></div>
</section>

<section class="panel" id="bid">
<h2>环保投标助手</h2><div class="muted">从三份合成招标文件中检索资格、日期、评分与风险条款。</div>
<div class="grid"><div>
<label>问题</label><textarea id="bid-q">园区污水处理项目的投标截止时间和预算是什么？</textarea>
<button onclick="askBid()">检索招标文件</button>
</div><div><div class="answer" id="bid-a">等待检索…</div><details><summary>查看引用</summary><pre id="bid-json"></pre></details></div></div>
</section>
</main>
<script>
const $ = (id) => document.getElementById(id);
document.querySelectorAll('.tab').forEach(btn => btn.onclick = () => {
  document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  btn.classList.add('active'); $(btn.dataset.tab).classList.add('active');
});
function show(id, text){ $(id).textContent = text; }
function pretty(id, data){ $(id).textContent = JSON.stringify(data, null, 2); }
async function post(url, body){
  const r = await fetch(url, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
  const data = await r.json();
  if(!r.ok) throw new Error(data.error || 'request failed');
  return data;
}
function setAgent(q){ $('agent-q').value=q; askAgent(); }
async function askAgent(){
  show('agent-a','运行中…');
  try{ const d = await post('/api/agent',{question:$('agent-q').value});
    show('agent-a', d.answer + '\n\n意图: '+d.intent+' | 置信度: '+d.confidence+' | 转人工: '+d.handoff);
    pretty('agent-json', d);
  }catch(e){ show('agent-a','错误：'+e.message); }
}
async function runContent(){
  show('content-a','生成中…');
  try{ const d = await post('/api/content',{topic:$('content-topic').value,channel:$('content-channel').value,audience:$('content-audience').value});
    show('content-a', d.titles.join('\n') + '\n\n状态: '+d.status+' | 合规分: '+d.compliance.score+'/100\n\n'+d.script);
    pretty('content-json', d);
  }catch(e){ show('content-a','错误：'+e.message); }
}
function setAnalytics(q){ $('analytics-q').value=q; askAnalytics(); }
async function askAnalytics(){
  show('analytics-a','查询中…');
  try{ const d = await post('/api/analytics',{question:$('analytics-q').value});
    show('analytics-a', d.answer); pretty('analytics-json', d.data);
  }catch(e){ show('analytics-a','错误：'+e.message); }
}
async function askBid(){
  show('bid-a','检索中…');
  try{ const d = await post('/api/bid',{question:$('bid-q').value});
    show('bid-a', d.answer); pretty('bid-json', d.citations);
  }catch(e){ show('bid-a','错误：'+e.message); }
}
async function loadKpis(){
  try{ const d = await fetch('/api/metrics').then(r=>r.json());
    const items = [
      ['知识库文档', d.eval.documents, '条合成 FAQ'],
      ['Retrieval Hit@1', (d.eval.retrieval_hit_at_1*100).toFixed(1)+'%', '50 条 FAQ 评测'],
      ['工具准确率', (d.eval.tool_accuracy*100).toFixed(1)+'%', '60 条混合用例'],
      ['内容线索', d.content.leads, '90 条内容 · 30 天'],
      ['自动化机会', d.process.top_opportunities.length, 'Top 6 已排序'],
      ['招标文件', d.bid_documents, '结构化摘要'],
    ];
    $('kpis').innerHTML = items.map(x=>`<div class="kpi"><b>${x[1]}</b><span>${x[0]} · ${x[2]}</span></div>`).join('');
  }catch(e){ $('kpis').innerHTML = '<div class="kpi"><b>!</b><span>指标加载失败</span></div>'; }
}
loadKpis();
</script>
</body>
</html>
"""


def _json_bytes(data: Any) -> bytes:
    return json.dumps(data, ensure_ascii=False).encode("utf-8")


def create_handler(agent: CustomerServiceAgent, analytics: ContentAnalytics, bid: BidAssistant, metrics: dict) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "AIPortfolio/1.0"

        def _send(self, status: int, body: bytes, content_type: str = "application/json; charset=utf-8") -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, data: Any, status: int = 200) -> None:
            self._send(status, _json_bytes(data))

        def do_OPTIONS(self) -> None:  # noqa: N802
            self._send(204, b"")

        def do_GET(self) -> None:  # noqa: N802
            if self.path in ("/", "/index.html"):
                self._send(200, INDEX_HTML.encode("utf-8"), "text/html; charset=utf-8")
            elif self.path == "/api/health":
                self._json({"status": "ok", "documents": len(agent.kb), "synthetic": True})
            elif self.path == "/api/metrics":
                self._json(metrics)
            else:
                self._json({"error": "not found"}, 404)

        def do_POST(self) -> None:  # noqa: N802
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            except (ValueError, json.JSONDecodeError):
                self._json({"error": "invalid JSON body"}, 400)
                return

            try:
                if self.path == "/api/agent":
                    self._json(agent.answer(str(payload.get("question", ""))).as_dict())
                elif self.path == "/api/content":
                    brief = ContentWorkflow().generate(
                        str(payload.get("topic", "环保设备租赁如何选型")),
                        str(payload.get("channel", "公众号")),
                        str(payload.get("audience", "环保工程公司")),
                    )
                    self._json(brief.as_dict())
                elif self.path == "/api/analytics":
                    self._json(analytics.answer_question(str(payload.get("question", ""))))
                elif self.path == "/api/bid":
                    self._json(bid.answer(str(payload.get("question", ""))))
                else:
                    self._json({"error": "not found"}, 404)
            except Exception as exc:  # keep the demo process alive
                self._json({"error": str(exc)}, 500)

        def log_message(self, fmt: str, *args: Any) -> None:
            print(f"[web] {self.address_string()} - {fmt % args}")

    return Handler


def build_metrics() -> dict:
    eval_report = evaluate()
    analytics = ContentAnalytics()
    from .environment.process import analyze_process

    process = analyze_process()
    return {
        "eval": eval_report["metrics"],
        "content": {
            "posts": analytics.summary()["posts"],
            "views": analytics.summary()["views"],
            "leads": analytics.summary()["leads"],
            "cpl": analytics.summary()["cpl"],
        },
        "process": {
            "flows": len(process["flows"]),
            "steps": process["steps"],
            "top_opportunities": process["top_opportunities"],
        },
        "bid_documents": len(list((Path(__file__).parent.parent / "data" / "environment" / "bid_docs").glob("*.md"))),
        "synthetic": True,
    }


def make_server(host: str = "127.0.0.1", port: int = 8000) -> ThreadingHTTPServer:
    handler = create_handler(
        agent=CustomerServiceAgent(),
        analytics=ContentAnalytics(),
        bid=BidAssistant(),
        metrics=build_metrics(),
    )
    return ThreadingHTTPServer((host, port), handler)


def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    server = make_server(host, port)
    url = f"http://{host}:{server.server_address[1]}"
    print(f"AI portfolio demo: {url}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        server.server_close()


if __name__ == "__main__":
    serve()
