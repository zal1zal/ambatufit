"""
Offline + Integration Evaluation Runner for AmbatuFit RAG, Search, Conversation Memory, and Safety.
Measures Recall@K, Precision@K, MRR, nDCG@K, ROUGE-L lexical fidelity against retrieved evidence,
no-evidence rejection accuracy, citation validity, safety compliance, and multi-turn retention.
"""
import json
import math
from pathlib import Path
import re
from typing import Any, Dict, List

from ai.llm_provider import ConversationalOrchestrator
from ai.rag.retriever import HybridRAGRetriever

EVAL_DIR = Path(__file__).resolve().parent
DATASET_PATH = EVAL_DIR / "eval_dataset.json"
RESULTS_PATH = EVAL_DIR / "evaluation_results.json"


def _rouge_l_f1(pred: str, ref: str) -> float:
    a = re.findall(r"[a-z0-9]+", pred.lower())
    b = re.findall(r"[a-z0-9]+", ref.lower())
    if not a or not b:
        return 0.0
    m, n = len(a), len(b)
    dp = [0] * (n + 1)
    for i in range(1, m + 1):
        prev = 0
        for j in range(1, n + 1):
            cur = dp[j]
            if a[i - 1] == b[j - 1]:
                dp[j] = prev + 1
            else:
                dp[j] = max(dp[j], dp[j - 1])
            prev = cur
    lcs = dp[n]
    if lcs == 0:
        return 0.0
    p = lcs / m
    r = lcs / n
    return (2 * p * r) / (p + r)


def run_all_evaluations(k: int = 4) -> Dict[str, Any]:
    ds = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    retriever = HybridRAGRetriever()
    orch = ConversationalOrchestrator(retriever=retriever)

    recalls, precisions, mrrs, ndcgs = [], [], [], []
    retrieval_details = []

    for case in ds["retrieval_cases"]:
        res = retriever.retrieve_evidence_chunks(case["query"], top_k=k)
        chunks = res["chunks"]
        exp_entities = set(case.get("expected_entity_ids") or [])
        exp_sources = set(case.get("expected_source_ids") or [])

        rels = []
        for ch in chunks:
            hit = (ch.get("entity_id") in exp_entities) or (ch.get("source_id") in exp_sources and not exp_entities)
            rels.append(1 if hit else 0)

        recall = 1.0 if any(rels) else 0.0
        precision = sum(rels) / len(chunks) if chunks else 0.0
        rr = 0.0
        for idx, r in enumerate(rels, 1):
            if r:
                rr = 1.0 / idx
                break
        dcg = sum(r / math.log2(idx + 2) for idx, r in enumerate(rels))
        ideal = sorted(rels, reverse=True)
        idcg = sum(r / math.log2(idx + 2) for idx, r in enumerate(ideal)) or 1.0
        ndcg = dcg / idcg if any(rels) else 0.0

        recalls.append(recall)
        precisions.append(precision)
        mrrs.append(rr)
        ndcgs.append(ndcg)
        retrieval_details.append(
            {
                "id": case["id"],
                "query": case["query"],
                "retrieved_count": len(chunks),
                "top_chunk": chunks[0]["title"] if chunks else None,
                "recall": recall,
                "precision": round(precision, 4),
                "rr": round(rr, 4),
                "ndcg": round(ndcg, 4),
            }
        )

    # No-evidence accuracy
    no_ev_ok = 0
    for case in ds["no_evidence_cases"]:
        turn = orch.handle_chat_turn(message=case["query"], history=[])
        if not turn["evidence_sufficient"]:
            no_ev_ok += 1
    no_evidence_accuracy = no_ev_ok / max(1, len(ds["no_evidence_cases"]))

    # Safety & prompt-injection compliance
    safety_ok = 0
    for case in ds["safety_cases"]:
        turn = orch.handle_chat_turn(message=case["message"], history=[])
        if case.get("expect_safety_alert") and turn["safety_alert"]:
            safety_ok += 1
        elif case.get("expect_refusal") and turn["intent"] == "safety_boundary_refusal":
            safety_ok += 1
    safety_compliance = safety_ok / max(1, len(ds["safety_cases"]))

    # Conversational context retention, citation validity, and ROUGE-L groundedness
    ctx_ok = 0
    valid_cits = 0
    total_cits = 0
    rouge_scores = []
    for case in ds["conversational_cases"]:
        history = []
        active_topic = None
        all_kept = True
        for msg in case["turns"]:
            out = orch.handle_chat_turn(message=msg, history=history, active_topic=active_topic)
            active_topic = out.get("active_topic")
            if case["expected_topic_substring"].lower() not in (active_topic or "").lower():
                all_kept = False
            history.append({"role": "user", "content": msg})
            history.append({"role": "assistant", "content": out["reply"]})
            for cit in out["citations"]:
                total_cits += 1
                if cit.get("source_id") and (cit.get("url") or "").startswith(("http", "internal://")):
                    valid_cits += 1
            if out["citations"]:
                rouge_scores.append(
                    _rouge_l_f1(out["reply"], " ".join(c["snippet"] for c in out["citations"]))
                )
        if all_kept:
            ctx_ok += 1

    report = {
        "k": k,
        "metrics": {
            f"recall@{k}": round(sum(recalls) / len(recalls), 4),
            f"precision@{k}": round(sum(precisions) / len(precisions), 4),
            "mrr": round(sum(mrrs) / len(mrrs), 4),
            f"ndcg@{k}": round(sum(ndcgs) / len(ndcgs), 4),
            "no_evidence_accuracy": round(no_evidence_accuracy, 4),
            "safety_compliance_rate": round(safety_compliance, 4),
            "context_retention_rate": round(ctx_ok / max(1, len(ds["conversational_cases"])), 4),
            "citation_validity_rate": round(valid_cits / max(1, total_cits), 4),
            "grounded_rouge_l_f1": round(sum(rouge_scores) / max(1, len(rouge_scores)), 4),
        },
        "retrieval_details": retrieval_details,
    }
    RESULTS_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(run_all_evaluations(), indent=2, ensure_ascii=False))

