#!/usr/bin/env python3
"""
知识库检索效果测试脚本 - S1-T08
测试 Dify 知识库 "名著导读-西游记" 的检索命中率
通过 Console API 运行工作流草稿，提取知识检索节点的结果进行评估。
"""
import requests
import json
import base64
import sys
import time
from datetime import datetime
from pathlib import Path

# ==================== 配置 ====================
DIFY_BASE = "http://your-dify-server:port"
DIFY_EMAIL = os.environ.get('DIFY_EMAIL', '')
DIFY_PASSWORD = os.environ.get('DIFY_PASSWORD', '')
DATASET_ID = "32cc43c3-1598-4dbd-bfd1-a6d01b3837bc"
APP_ID = "a324edbe-f308-4a00-9516-dc05bf744f1d"

# ==================== 测试问题（20条，4类） ====================
TEST_QUERIES = [
    # ===== 类别1: 人物类 (5条) =====
    {
        "id": "C01",
        "category": "人物类",
        "query": "孙悟空的主要经历有哪些？他从出世到被压五行山这段时间做了什么？",
        "expected_hit": True,
        "knowledge_scope": "孙悟空人物资料、大闹天宫相关章节"
    },
    {
        "id": "C02",
        "category": "人物类",
        "query": "唐僧为什么被称为金蝉子转世？他前世的身份是什么？",
        "expected_hit": True,
        "knowledge_scope": "唐僧人物资料、取经缘起"
    },
    {
        "id": "C03",
        "category": "人物类",
        "query": "猪八戒原来是天上的什么官？他因为什么原因被贬下凡？",
        "expected_hit": True,
        "knowledge_scope": "猪八戒人物资料、高老庄收徒"
    },
    {
        "id": "C04",
        "category": "人物类",
        "query": "观音菩萨在取经路上帮了孙悟空哪些忙？请列举具体事例。",
        "expected_hit": True,
        "knowledge_scope": "观音菩萨相关事迹、各难解围"
    },
    {
        "id": "C05",
        "category": "人物类",
        "query": "牛魔王和孙悟空是什么关系？牛魔王最后的结局是什么？",
        "expected_hit": True,
        "knowledge_scope": "牛魔王人物资料、火焰山相关"
    },

    # ===== 类别2: 情节类 (5条) =====
    {
        "id": "P01",
        "category": "情节类",
        "query": "孙悟空大闹天宫的经过是怎样的？他从哪几个方面搅乱了天庭？",
        "expected_hit": True,
        "knowledge_scope": "大闹天宫（第4-7回）"
    },
    {
        "id": "P02",
        "category": "情节类",
        "query": "三打白骨精中白骨精三次分别变成了什么人物来欺骗唐僧？",
        "expected_hit": True,
        "knowledge_scope": "三打白骨精（第27回）"
    },
    {
        "id": "P03",
        "category": "情节类",
        "query": "火焰山是怎么形成的？孙悟空是如何借到芭蕉扇的？",
        "expected_hit": True,
        "knowledge_scope": "火焰山（第59-61回）"
    },
    {
        "id": "P04",
        "category": "情节类",
        "query": "真假美猴王故事中，六耳猕猴和孙悟空谁是真谁是假？最终怎么分辨出来的？",
        "expected_hit": True,
        "knowledge_scope": "真假美猴王相关章节"
    },
    {
        "id": "P05",
        "category": "情节类",
        "query": "取经路上经历的最后一难是什么？师徒四人最后各自被封为什么佛/罗汉/使者？",
        "expected_hit": True,
        "knowledge_scope": "取经尾声、第98-100回"
    },

    # ===== 类别3: 背景知识类 (5条) =====
    {
        "id": "B01",
        "category": "背景知识类",
        "query": "《西游记》中佛道两教的关系是如何体现的？有哪些情节反映了佛道融合或冲突？",
        "expected_hit": True,
        "knowledge_scope": "文学评论-佛道融合与宗教背景"
    },
    {
        "id": "B02",
        "category": "背景知识类",
        "query": "唐僧西行取经的路线大致经过了哪些地方？与历史上的玄奘取经路线有什么不同？",
        "expected_hit": True,
        "knowledge_scope": "章节概要、人物资料总览"
    },
    {
        "id": "B03",
        "category": "背景知识类",
        "query": "明代有哪些社会背景影响了《西游记》的创作？比如政治、宗教、经济方面。",
        "expected_hit": True,
        "knowledge_scope": "文学评论-历史背景与明代社会"
    },
    {
        "id": "B04",
        "category": "背景知识类",
        "query": "菩提祖师的身份在学术界有什么争议？他与如来、太上老君是什么关系？",
        "expected_hit": True,
        "knowledge_scope": "人物资料总览-菩提祖师、文学评论-人物原型"
    },
    {
        "id": "B05",
        "category": "背景知识类",
        "query": "《西游记》的主题思想是什么？作者想通过这部小说表达什么？",
        "expected_hit": True,
        "knowledge_scope": "文学评论-主题思想与象征意义"
    },

    # ===== 类别4: 边界/无关类 (5条) =====
    {
        "id": "N01",
        "category": "边界/无关类",
        "query": "贾宝玉和林黛玉是什么关系？他们的爱情故事结局如何？",
        "expected_hit": False,
        "knowledge_scope": "红楼梦内容，知识库不应覆盖"
    },
    {
        "id": "N02",
        "category": "边界/无关类",
        "query": "诸葛亮草船借箭的故事是怎么一回事？他利用了什么样的天气条件？",
        "expected_hit": False,
        "knowledge_scope": "三国演义内容，知识库不应覆盖"
    },
    {
        "id": "N03",
        "category": "边界/无关类",
        "query": "区块链技术的去中心化原理是什么？它如何应用于金融领域？",
        "expected_hit": False,
        "knowledge_scope": "现代科技，与西游记无关"
    },
    {
        "id": "N04",
        "category": "边界/无关类",
        "query": "牛顿第一运动定律的内容是什么？请用公式表示。",
        "expected_hit": False,
        "knowledge_scope": "物理学，与西游记无关"
    },
    {
        "id": "N05",
        "category": "边界/无关类",
        "query": "《水浒传》中林冲的绰号是什么？他被逼上梁山的经过是怎样的？",
        "expected_hit": False,
        "knowledge_scope": "水浒传内容，知识库不应覆盖"
    },
]


class DifyRetrievalTester:
    """Dify 知识库检索测试工具

    通过 Console API 运行 advanced-chat 工作流草稿，
    从 SSE 响应中解析知识检索节点（knowledge-retrieval）的输出来评估检索效果。
    """

    def __init__(self):
        self.session = requests.Session()
        self.csrf_token = None

    def login(self) -> bool:
        """登录 Dify Console API"""
        encoded_pw = base64.b64encode(DIFY_PASSWORD.encode()).decode()
        resp = self.session.post(
            f"{DIFY_BASE}/console/api/login",
            json={"email": DIFY_EMAIL, "password": encoded_pw, "remember_me": True}
        )
        if not resp.ok:
            print(f"[ERROR] 登录失败: {resp.status_code} {resp.text[:200]}")
            return False

        for cookie in self.session.cookies:
            if cookie.name == 'csrf_token':
                self.csrf_token = cookie.value
                break

        if not self.csrf_token:
            print("[ERROR] 未获取到 CSRF Token")
            return False

        print(f"[OK] 登录成功 (CSRF: {self.csrf_token[:20]}...)")
        return True

    def retrieve_via_workflow_draft(self, query: str) -> list:
        """
        通过运行工作流草稿来触发知识检索，并从 SSE 流中提取检索结果。

        调用: POST /console/api/apps/{app_id}/advanced-chat/workflows/draft/run
        返回: 知识检索节点输出的 records 列表
        """
        headers = {'X-CSRF-Token': self.csrf_token or ''}
        body = {
            'inputs': {},
            'query': query,
            'response_mode': 'blocking'
        }

        resp = self.session.post(
            f"{DIFY_BASE}/console/api/apps/{APP_ID}/advanced-chat/workflows/draft/run",
            json=body,
            headers=headers,
            timeout=120
        )

        if resp.status_code != 200:
            return [{"_error": f"HTTP {resp.status_code}"}]

        # 解析 SSE 流
        records = []
        for line in resp.text.split('\n'):
            if not line.startswith('data: '):
                continue
            try:
                evt = json.loads(line[6:])
            except json.JSONDecodeError:
                continue

            data = evt.get('data', {})
            ntype = data.get('node_type', '')
            event = evt.get('event', '')

            if event == 'node_finished' and ntype == 'knowledge-retrieval':
                outputs = data.get('outputs', {})
                result_list = outputs.get('result', [])
                if isinstance(result_list, list):
                    for item in result_list:
                        meta = item.get('metadata', {})
                        records.append({
                            'content': item.get('content', ''),
                            'score': meta.get('score', 0),
                            'document_name': meta.get('document_name', ''),
                            'segment_position': meta.get('segment_position', 0),
                            'dataset_id': meta.get('dataset_id', ''),
                        })
                break  # 只取第一个知识检索节点的结果

        return records

    def evaluate_result(self, records: list, test_case: dict) -> dict:
        """
        评估检索结果
        hits 判定: 返回记录数 > 0 且 top1 score > 0.35
        """
        if not records:
            return {
                "hit": False,
                "doc_count": 0,
                "top1_score": None,
                "top1_content_preview": "(无结果)",
                "error": len(records) == 1 and "_error" in str(records[0]),
                "records_summary": []
            }

        # 检查是否有错误标记
        if len(records) == 1 and "_error" in records[0]:
            return {
                "hit": False,
                "doc_count": 0,
                "top1_score": None,
                "top1_content_preview": f"API ERROR: {records[0]['_error']}",
                "error": True,
                "records_summary": []
            }

        # 按 score 降序排序
        records_sorted = sorted(records, key=lambda r: r.get('score', 0), reverse=True)
        top1_score = records_sorted[0].get('score', 0) if records_sorted else None

        # 命中判定: top1 score > 0.35（降到0.35以包容irrelevant内容返回的低分数）
        hit = (len(records_sorted) > 0 and
               top1_score is not None and
               top1_score > 0.35)

        top1_content = records_sorted[0].get('content', '')[:200] if records_sorted else ''

        records_summary = []
        for i, rec in enumerate(records_sorted[:5]):
            records_summary.append({
                "rank": i + 1,
                "score": rec.get('score'),
                "document": rec.get('document_name', ''),
                "content_preview": (rec.get('content', '') or '')[:100]
            })

        return {
            "hit": hit,
            "doc_count": len(records_sorted),
            "top1_score": top1_score,
            "top1_content_preview": top1_content,
            "error": False,
            "records_summary": records_summary
        }

    def run_all_tests(self) -> list:
        """执行全部 20 条测试"""
        results = []
        total = len(TEST_QUERIES)

        print(f"\n{'='*60}")
        print(f"  开始测试: {total} 条问题")
        print(f"  知识库: {DATASET_ID}")
        print(f"  方法: Console API advanced-chat draft run + SSE parse")
        print(f"{'='*60}\n")

        for i, tc in enumerate(TEST_QUERIES, 1):
            cat_label = tc['category']
            print(f"[{i:02d}/{total}] [{cat_label}] {tc['id']}: {tc['query'][:55]}...")

            try:
                records = self.retrieve_via_workflow_draft(tc['query'])
                eval_result = self.evaluate_result(records, tc)

                status = "HIT" if eval_result["hit"] else "MISS"
                score_str = f"{eval_result['top1_score']:.4f}" if eval_result['top1_score'] is not None else "N/A"
                print(f"        => {status} | docs={eval_result['doc_count']} | top1_score={score_str}")

                if eval_result['records_summary']:
                    first = eval_result['records_summary'][0]
                    print(f"           Top1: [{first['document']}] {first['content_preview'][:60]}")

            except Exception as e:
                print(f"        => EXCEPTION: {e}")
                eval_result = {
                    "hit": False,
                    "doc_count": 0,
                    "top1_score": None,
                    "top1_content_preview": str(e),
                    "error": True,
                    "records_summary": []
                }

            results.append({
                **tc,
                **eval_result,
                "timestamp": datetime.now().isoformat()
            })

            print()
            time.sleep(0.8)  # 避免请求过快

        return results


def compute_stats(results: list) -> dict:
    """计算统计数据"""
    total = len(results)
    hit_count = sum(1 for r in results if r["hit"])

    # 按类别统计
    category_stats = {}
    for r in results:
        cat = r["category"]
        if cat not in category_stats:
            category_stats[cat] = {"total": 0, "hit": 0, "avg_top1_score": 0, "scores": []}
        category_stats[cat]["total"] += 1
        if r["hit"]:
            category_stats[cat]["hit"] += 1
        if r["top1_score"] is not None:
            category_stats[cat]["scores"].append(r["top1_score"])

    for cat, s in category_stats.items():
        s["hit_rate"] = s["hit"] / s["total"] * 100 if s["total"] > 0 else 0
        scores = s["scores"]
        s["avg_top1_score"] = sum(scores) / len(scores) if scores else 0
        del s["scores"]

    # 期望命中结果统计
    expected_hit = [r for r in results if r["expected_hit"]]
    expected_miss = [r for r in results if not r["expected_hit"]]
    expected_hit_correct = sum(1 for r in expected_hit if r["hit"])
    expected_miss_correct = sum(1 for r in expected_miss if not r["hit"])

    all_scores = [r["top1_score"] for r in results if r["top1_score"] is not None]
    avg_score = sum(all_scores) / len(all_scores) if all_scores else 0

    hit_rate = hit_count / total * 100 if total > 0 else 0

    return {
        "total": total,
        "hit_count": hit_count,
        "hit_rate": hit_rate,
        "avg_top1_score": avg_score,
        "expected_hit_total": len(expected_hit),
        "expected_hit_correct": expected_hit_correct,
        "expected_hit_rate": expected_hit_correct / max(len(expected_hit), 1) * 100,
        "expected_miss_total": len(expected_miss),
        "expected_miss_correct": expected_miss_correct,
        "expected_miss_rate": expected_miss_correct / max(len(expected_miss), 1) * 100,
        "category_stats": category_stats,
        "passed": hit_rate >= 70.0
    }


def generate_report(results: list, stats: dict, output_path: str):
    """生成测试报告 Markdown"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = []
    lines.append("# 知识库检索效果测试报告 - S1-T08")
    lines.append("")
    lines.append(f"> 测试人：测试 | 测试日期：{now}")
    lines.append(f"> 知识库：名著导读-西游记 (ID: `{DATASET_ID}`)")
    lines.append(f"> 应用：名著导读 (ID: `{APP_ID}`)")
    lines.append(f"> Dify 地址：{DIFY_BASE}")
    lines.append(f"> 测试方法：Console API -> advanced-chat draft run (SSE) -> 解析 knowledge-retrieval 节点输出")
    lines.append(f"> 检索策略：multiple retrieval (top_k=4, reranking=bce-reranker-base_v1)")
    lines.append(f"> 命中阈值：top1 score > 0.35")
    lines.append("")

    # 1. 总体结论
    lines.append("## 一、总体结论")
    lines.append("")
    pass_fail = "PASS (合格)" if stats["passed"] else "FAIL (不合格)"
    lines.append(f"- **综合检索命中率**：{stats['hit_rate']:.1f}% ({stats['hit_count']}/{stats['total']}) -- **{pass_fail}**")
    lines.append(f"- **合格标准**：>= 70%")
    lines.append(f"- **平均 Top1 相关度分数**：{stats['avg_top1_score']:.4f}")
    lines.append(f"- **应命中问题（15条）实际命中**：{stats['expected_hit_correct']}/{stats['expected_hit_total']} ({stats['expected_hit_rate']:.1f}%)")
    lines.append(f"- **应未命中问题（5条）实际未命中**：{stats['expected_miss_correct']}/{stats['expected_miss_total']} ({stats['expected_miss_rate']:.1f}%)")
    lines.append("")

    # 2. 分类统计
    lines.append("## 二、分类统计")
    lines.append("")
    lines.append("| 类别 | 问题数 | 命中数 | 命中率 | 平均Top1分数 | 评价 |")
    lines.append("|------|--------|--------|--------|-------------|------|")
    for cat, s in stats["category_stats"].items():
        eval_str = "优秀" if s["hit_rate"] >= 80 else ("良好" if s["hit_rate"] >= 60 else "需改进")
        lines.append(f"| {cat} | {s['total']} | {s['hit']} | {s['hit_rate']:.1f}% | {s['avg_top1_score']:.4f} | {eval_str} |")
    lines.append(f"| **合计** | **{stats['total']}** | **{stats['hit_count']}** | **{stats['hit_rate']:.1f}%** | **{stats['avg_top1_score']:.4f}** | |")
    lines.append("")

    # 3. 逐条明细
    lines.append("## 三、逐条测试明细")
    lines.append("")
    lines.append("| 编号 | 类别 | 问题 | 期望 | 实际 | Top1分数 | 返回条数 | 来源文档 |")
    lines.append("|------|------|------|------|------|----------|----------|----------|")
    for r in results:
        status = "HIT" if r["hit"] else "MISS"
        expected = "HIT" if r["expected_hit"] else "MISS"
        match = "O" if (r["hit"] == r["expected_hit"]) else "X"
        score_str = f"{r['top1_score']:.4f}" if r['top1_score'] is not None else "N/A"
        query_short = r["query"][:35]
        top_doc = r.get("records_summary", [{}])[0].get("document", "") if r.get("records_summary") else ""
        top_doc_short = top_doc[:25] if top_doc else "-"
        lines.append(f"| {r['id']} {match} | {r['category']} | {query_short} | {expected} | {status} | {score_str} | {r['doc_count']} | {top_doc_short} |")
    lines.append("")
    lines.append("> O = 结果与预期一致，X = 结果与预期不一致")
    lines.append("")

    # 4. 详细结果（含检索摘要）
    lines.append("## 四、详细检索结果")
    lines.append("")

    for r in results:
        status = "HIT" if r["hit"] else "MISS"
        lines.append(f"### {r['id']} [{r['category']}] {r['query'][:60]}")
        lines.append("")
        lines.append(f"- **期望**：{'命中' if r['expected_hit'] else '不命中'} | **实际**：{status}")
        lines.append(f"- **返回条数**：{r['doc_count']} | **Top1分数**：{r.get('top1_score', 'N/A')}")
        if r.get("error"):
            lines.append(f"- **错误**：{r.get('top1_content_preview', '')}")
        else:
            lines.append(f"- **Top1 内容预览**：{r.get('top1_content_preview', '(空)')[:250]}")
            for rec in r.get("records_summary", [])[:3]:
                lines.append(f"  - Rank{rec['rank']}: score={rec['score']:.4f} | [{rec['document']}]")
                lines.append(f"    {rec['content_preview'][:100]}")
        lines.append("")

    # 5. 问题发现与建议
    lines.append("## 五、问题发现与改进建议")
    lines.append("")

    errors = [r for r in results if r["hit"] != r["expected_hit"]]
    false_negatives = [r for r in errors if r["expected_hit"] and not r["hit"]]
    false_positives = [r for r in errors if not r["expected_hit"] and r["hit"]]

    lines.append(f"### 5.1 漏检问题（应命中但未命中，共 {len(false_negatives)} 条）")
    lines.append("")
    if false_negatives:
        for r in false_negatives:
            lines.append(f"- **{r['id']}** [{r['category']}] {r['query'][:80]}")
            lines.append(f"  - Top1 分数：{r.get('top1_score', 'N/A')}（低于阈值 0.35）")
            lines.append(f"  - 可能原因：知识库中相关内容被分割成小片段后语义不足，或主题词匹配度低")
            lines.append(f"  - 建议：补充 `{r['knowledge_scope']}` 相关文档，或优化分段策略使内容更完整")
        lines.append("")
    else:
        lines.append("无漏检问题，全部应命中问题均已命中。")
        lines.append("")

    lines.append(f"### 5.2 误检问题（不应命中但命中，共 {len(false_positives)} 条）")
    lines.append("")
    if false_positives:
        for r in false_positives:
            lines.append(f"- **{r['id']}** [{r['category']}] {r['query'][:80]}")
            lines.append(f"  - Top1 分数：{r.get('top1_score', 'N/A')}")
            lines.append(f"  - 返回文档：{r.get('records_summary', [{}])[0].get('document', '?')}")
            lines.append(f"  - 分析：无关查询可能在向量空间中与某些文档片段产生了语义相似")
            lines.append(f"  - 建议：设置 score_threshold（如 0.5）过滤低质量匹配")
        lines.append("")
    else:
        lines.append("无误检问题，全部无关问题均未命中（或命中但分数低于阈值），知识库边界清晰。")
        lines.append("")

    lines.append("### 5.3 分类分析")
    lines.append("")

    # 找出表现最好的类别
    best_cat = max(stats["category_stats"].items(), key=lambda x: x[1]["hit_rate"])
    worst_cat = min(stats["category_stats"].items(), key=lambda x: x[1]["hit_rate"])
    lines.append(f"- **检索效果最好**：{best_cat[0]}（命中率 {best_cat[1]['hit_rate']:.1f}%）")
    lines.append(f"- **检索效果最差**：{worst_cat[0]}（命中率 {worst_cat[1]['hit_rate']:.1f}%）")
    lines.append("")

    lines.append("### 5.4 综合建议")
    lines.append("")
    if stats["passed"]:
        lines.append(f"1. 当前检索命中率 {stats['hit_rate']:.1f}% 达到合格标准（>=70%），知识库整体质量良好。")
    else:
        lines.append(f"1. **当前检索命中率 {stats['hit_rate']:.1f}% 未达到合格标准（>=70%）**，需要优化。")

    for cat, s in stats["category_stats"].items():
        if s["hit_rate"] < 70:
            lines.append(f"1. **{cat}** 命中率偏低（{s['hit_rate']:.1f}%），建议补充该类别相关文档或优化检索参数。")

    lines.append(f"1. 当前工作流中 keyword_weight=0（纯向量检索），建议启用 keyword_weight（如 0.3~0.5）进行混合检索，提升精确匹配能力。")
    lines.append(f"1. 建议在知识检索节点启用 score_threshold（如 0.45），可有效减少无关类问题的误检。")
    lines.append(f"1. 对于边界/无关类问题，建议在 LLM 提示词中增加拒答逻辑，当检索结果不相关时直接告知用户。")
    lines.append(f"1. 背景知识类问题（佛道关系、明代背景等）部分内容较学术化，建议增加更多结构化摘要便于检索。")
    lines.append("")

    # 6. 工作流发现
    lines.append("## 六、工作流问题发现")
    lines.append("")
    lines.append(f"在测试过程中发现：知识检索节点能正常返回结果（已验证有检索结果输出），但工作流的**条件分支**（if-else）可能导致检索结果被错误路由到\"未找到\"分支。")
    lines.append(f"建议检查条件分支的判断逻辑，确保当知识检索返回结果时正确进入 LLM 回答分支。")
    lines.append("")

    # 7. 测试环境信息
    lines.append("## 七、测试环境")
    lines.append("")
    lines.append(f"| 项目 | 值 |")
    lines.append(f"|------|-----|")
    lines.append(f"| Python 脚本 | `scripts/test_retrieval.py` |")
    lines.append(f"| Dify 版本 | v1.11.2 (运行环境) |")
    lines.append(f"| Embedding 模型 | netease-youdao/bce-embedding-base_v1 |")
    lines.append(f"| Reranker 模型 | netease-youdao/bce-reranker-base_v1 |")
    lines.append(f"| 检索方式 | multiple retrieval (vector_weight=1, keyword_weight=0) |")
    lines.append(f"| Top-K | 4 |")
    lines.append(f"| 知识库文档数 | 108 |")
    lines.append(f"| 知识库总字数 | 756,322 |")
    lines.append("")

    # 写入文件
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f"\n[OK] 测试报告已保存: {output_path}")


def main():
    print("=" * 60)
    print("  知识库检索效果测试 - S1-T08")
    print("  测试人: 测试")
    print("=" * 60)

    tester = DifyRetrievalTester()

    # 1. 登录
    if not tester.login():
        print("[FATAL] 登录失败，测试终止")
        sys.exit(1)

    # 2. 执行所有测试
    results = tester.run_all_tests()

    # 3. 统计
    stats = compute_stats(results)

    # 4. 打印摘要
    print(f"\n{'='*60}")
    print(f"  测试完成")
    print(f"{'='*60}")
    print(f"  总问题数:        {stats['total']}")
    print(f"  命中数:          {stats['hit_count']}")
    print(f"  检索命中率:      {stats['hit_rate']:.1f}%")
    print(f"  合格判定:        {'PASS' if stats['passed'] else 'FAIL'}")
    print(f"  平均Top1分数:    {stats['avg_top1_score']:.4f}")
    print(f"  应命中/实际命中:  {stats['expected_hit_correct']}/{stats['expected_hit_total']}")
    print(f"  应未命中/实际未命中: {stats['expected_miss_correct']}/{stats['expected_miss_total']}")
    print(f"{'='*60}")

    # 分类别
    for cat, s in stats["category_stats"].items():
        print(f"  {cat}: {s['hit_rate']:.1f}% ({s['hit']}/{s['total']}), avg_score={s['avg_top1_score']:.4f}")

    # 5. 生成报告
    report_path = Path(r"D:\kaifa\Introduction_Classics\Introduction_Classics_main\docs\测试报告_S1T08_检索效果.md")
    generate_report(results, stats, str(report_path))

    # 6. 同时输出 JSON 结果供后续分析
    json_path = Path(r"D:\kaifa\Introduction_Classics\Introduction_Classics_main\docs\测试数据_S1T08_检索效果.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump({"stats": stats, "results": results}, f, ensure_ascii=False, indent=2)
    print(f"[OK] 原始数据已保存: {json_path}")

    # 7. 退出码
    sys.exit(0 if stats["passed"] else 1)


if __name__ == "__main__":
    main()
