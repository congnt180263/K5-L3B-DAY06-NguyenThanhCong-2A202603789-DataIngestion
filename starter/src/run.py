"""Day 06 pipeline orchestration."""
import csv
import json
import os
from pathlib import Path
import time
from dotenv import load_dotenv

from .chunking import by_paragraph, fixed_size
from .embeddings import DeployComEmbedder, GeminiEmbedder, LocalMiniLMEmbedder
from .evaluation import evaluate_query, summarize
from .ingestion import load_pdf
from .store import PgVectorStore


def find_file(relative_paths: list[str]) -> Path:
    """Find the first existing path from candidate relative paths."""
    for p in relative_paths:
        path = Path(p)
        if path.exists():
            return path
    raise FileNotFoundError(f"None of candidate paths exist: {relative_paths}")


def main() -> None:
    # 1. Load environment variables
    # Look for .env in starter/.env or root .env
    env_path = find_file(["starter/.env", ".env"])
    load_dotenv(dotenv_path=env_path)
    print(f"[1/6] Loaded environment from: {env_path}")

    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:55433/day6_vector_db")

    # 2. Load PDF corpus
    pdf_path = find_file(["data/A_Mathematicians_Apology.pdf", "starter/data/A_Mathematicians_Apology.pdf"])
    print(f"[2/6] Loading PDF from: {pdf_path}")
    all_pages = load_pdf(pdf_path, document_id="hardy-1940", source="data/A_Mathematicians_Apology.pdf")
    content_pages = [p for p in all_pages if p.metadata.get("is_content_page")]
    print(f"      Total physical pages: {len(all_pages)}, Valid content pages: {len(content_pages)}")
    if len(content_pages) < 30:
        raise ValueError(f"Corpus has {len(content_pages)} content pages (< 30 content pages requirement)!")

    # 3. Load benchmark questions
    benchmark_path = find_file(["benchmark/questions.json", "starter/benchmark/questions.json"])
    print(f"[3/6] Loading benchmark from: {benchmark_path}")
    with open(benchmark_path, encoding="utf-8") as f:
        questions = json.load(f)
    print(f"      Loaded {len(questions)} questions (Dev: {sum(1 for q in questions if q['split'] == 'dev')}, Test: {sum(1 for q in questions if q['split'] == 'test')})")

    # 4. Initialize Embedder and PgVectorStore
    print("[4/6] Initializing Embedder and Vector Database...")
    chosen_model = os.getenv("EMBEDDING_MODEL", "").lower()
    if "minilm" in chosen_model or chosen_model == "local":
        embedder = LocalMiniLMEmbedder()
    elif os.getenv("GEMINI_API_KEY"):
        embedder = GeminiEmbedder()
    elif os.getenv("DEPLOY_API_KEY"):
        embedder = DeployComEmbedder()
    else:
        embedder = LocalMiniLMEmbedder()
    print(f"      Embedder initialized: {embedder.model_name} (Dimensions: {embedder.dimensions})")

    store = PgVectorStore(database_url=db_url, dimensions=embedder.dimensions)
    store.create_schema()
    print("      PgVectorStore schema verified/created successfully.")

    # 5. Build and execute Strategies A, B, and C
    print("[5/6] Running 3 Ingestion and Retrieval Strategies...")

    # Output directories
    results_dir = Path("results")
    results_dir.mkdir(parents=True, exist_ok=True)
    starter_results_dir = Path("starter/results")
    starter_results_dir.mkdir(parents=True, exist_ok=True)

    artifacts_dir = Path("artifacts")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    strategies_results = {}

    # === STRATEGY A: Fixed-size (500 chars, overlap 50) ===
    print("\n--- Running Strategy A (Fixed-size: 500 chars, overlap 50) ---")
    t0 = time.time()
    chunks_a = []
    for p in content_pages:
        chunks_a.extend(fixed_size(p, size=500, overlap=50))
    ingest_prep_a = time.time() - t0

    print(f"  Generated {len(chunks_a)} chunks. Embedding chunks...")
    t_emb = time.time()
    vectors_a = embedder.embed_documents([c.text for c in chunks_a], batch_size=32)
    ingest_time_a = (time.time() - t_emb) + ingest_prep_a

    store.upsert("strategy_a", chunks_a, vectors_a)
    print(f"  Upserted {len(chunks_a)} chunks to pgvector (Total ingest time: {ingest_time_a:.2f}s).")

    print("  Retrieving and evaluating benchmark queries for Strategy A...")
    traces_a = []
    for q in questions:
        q_vec = embedder.embed_query(q["question"])
        hits = store.search("strategy_a", q_vec, top_k=3, filters=None)
        trace = evaluate_query(q, hits)
        traces_a.append(trace)

    summary_a = summarize(traces_a)
    strategies_results["strategy_a"] = {
        "name": "Strategy A (Fixed 500/50)",
        "chunk_count": len(chunks_a),
        "ingest_time": round(ingest_time_a, 2),
        "traces": traces_a,
        "summary": summary_a,
    }

    # === STRATEGY B: By Paragraph (max_size=800) ===
    print("\n--- Running Strategy B (Paragraph-based: max_size 800) ---")
    t0 = time.time()
    chunks_b = []
    for p in content_pages:
        chunks_b.extend(by_paragraph(p, max_size=800))
    ingest_prep_b = time.time() - t0

    print(f"  Generated {len(chunks_b)} chunks. Embedding chunks...")
    t_emb = time.time()
    vectors_b = embedder.embed_documents([c.text for c in chunks_b], batch_size=32)
    ingest_time_b = (time.time() - t_emb) + ingest_prep_b

    store.upsert("strategy_b", chunks_b, vectors_b)
    print(f"  Upserted {len(chunks_b)} chunks to pgvector (Total ingest time: {ingest_time_b:.2f}s).")

    print("  Retrieving and evaluating benchmark queries for Strategy B (No filter)...")
    traces_b = []
    for q in questions:
        q_vec = embedder.embed_query(q["question"])
        hits = store.search("strategy_b", q_vec, top_k=3, filters=None)
        trace = evaluate_query(q, hits)
        traces_b.append(trace)

    summary_b = summarize(traces_b)
    strategies_results["strategy_b"] = {
        "name": "Strategy B (Paragraph 800)",
        "chunk_count": len(chunks_b),
        "ingest_time": round(ingest_time_b, 2),
        "traces": traces_b,
        "summary": summary_b,
    }

    # === STRATEGY C: Paragraph + Metadata Filter ===
    print("\n--- Running Strategy C (Paragraph 800 + Metadata Filter on section) ---")
    # Reuses strategy_b chunks and vectors
    store.upsert("strategy_c", chunks_b, vectors_b)

    print("  Retrieving and evaluating benchmark queries for Strategy C (Applying section filter when present)...")
    traces_c = []
    for q in questions:
        q_vec = embedder.embed_query(q["question"])
        # Apply filter if provided in question
        filters = q.get("filter")
        hits = store.search("strategy_c", q_vec, top_k=3, filters=filters)
        trace = evaluate_query(q, hits)
        traces_c.append(trace)

    summary_c = summarize(traces_c)
    strategies_results["strategy_c"] = {
        "name": "Strategy C (Paragraph + Filter)",
        "chunk_count": len(chunks_b),
        "ingest_time": round(ingest_time_b, 2),
        "traces": traces_c,
        "summary": summary_c,
    }

    # 6. Save traces, summaries, and experiment log
    print("\n[6/6] Saving Traces and Summaries...")
    for key, data in strategies_results.items():
        out_file = results_dir / f"traces_{key}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(data["traces"], f, indent=2, ensure_ascii=False)
        # Mirror to starter/results
        with open(starter_results_dir / f"traces_{key}.json", "w", encoding="utf-8") as f:
            json.dump(data["traces"], f, indent=2, ensure_ascii=False)

    summary_file = results_dir / "benchmark_summary.json"
    clean_summary = {
        k: {
            "name": v["name"],
            "chunk_count": v["chunk_count"],
            "ingest_time": v["ingest_time"],
            "summary": v["summary"],
        }
        for k, v in strategies_results.items()
    }
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(clean_summary, f, indent=2, ensure_ascii=False)
    with open(starter_results_dir / "benchmark_summary.json", "w", encoding="utf-8") as f:
        json.dump(clean_summary, f, indent=2, ensure_ascii=False)

    # Update artifacts/experiment_log.csv
    exp_log_path = artifacts_dir / "experiment_log.csv"
    with open(exp_log_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "strategy_id",
                "strategy_name",
                "chunk_method",
                "chunk_params",
                "metadata_filter",
                "chunk_count",
                "ingest_time_sec",
                "cost_usd",
                "dev_hit1",
                "dev_hit3",
                "test_hit1",
                "test_hit3",
            ]
        )
        writer.writerow(
            [
                "Strategy A",
                "Fixed-size",
                "fixed_size",
                "size=500, overlap=50",
                "None",
                strategies_results["strategy_a"]["chunk_count"],
                strategies_results["strategy_a"]["ingest_time"],
                0.0,
                strategies_results["strategy_a"]["summary"]["dev"]["hit1_rate"],
                strategies_results["strategy_a"]["summary"]["dev"]["hit3_rate"],
                strategies_results["strategy_a"]["summary"]["test"]["hit1_rate"],
                strategies_results["strategy_a"]["summary"]["test"]["hit3_rate"],
            ]
        )
        writer.writerow(
            [
                "Strategy B",
                "Paragraph-based",
                "by_paragraph",
                "max_size=800",
                "None",
                strategies_results["strategy_b"]["chunk_count"],
                strategies_results["strategy_b"]["ingest_time"],
                0.0,
                strategies_results["strategy_b"]["summary"]["dev"]["hit1_rate"],
                strategies_results["strategy_b"]["summary"]["dev"]["hit3_rate"],
                strategies_results["strategy_b"]["summary"]["test"]["hit1_rate"],
                strategies_results["strategy_b"]["summary"]["test"]["hit3_rate"],
            ]
        )
        writer.writerow(
            [
                "Strategy C",
                "Paragraph + Filter",
                "by_paragraph",
                "max_size=800",
                "section (when present)",
                strategies_results["strategy_c"]["chunk_count"],
                strategies_results["strategy_c"]["ingest_time"],
                0.0,
                strategies_results["strategy_c"]["summary"]["dev"]["hit1_rate"],
                strategies_results["strategy_c"]["summary"]["dev"]["hit3_rate"],
                strategies_results["strategy_c"]["summary"]["test"]["hit1_rate"],
                strategies_results["strategy_c"]["summary"]["test"]["hit3_rate"],
            ]
        )

    # 7. Print Final Comparison Table
    print("\n" + "=" * 80)
    print("DAY 06 BENCHMARK EXPERIMENT RESULTS SUMMARY")
    print("=" * 80)
    print(f"{'Strategy':<25} | {'Split':<6} | {'Hit@1':<12} | {'Evidence Hit@3':<16} | {'Chunks':<8} | {'Time (s)':<8}")
    print("-" * 80)
    for k, v in strategies_results.items():
        s = v["summary"]
        print(f"{v['name']:<25} | {'dev':<6} | {s['dev']['hit1_rate'] + ' (' + str(s['dev']['hit1_pct']) + '%)':<12} | {s['dev']['hit3_rate'] + ' (' + str(s['dev']['hit3_pct']) + '%)':<16} | {v['chunk_count']:<8} | {v['ingest_time']:<8}")
        print(f"{'':<25} | {'test':<6} | {s['test']['hit1_rate'] + ' (' + str(s['test']['hit1_pct']) + '%)':<12} | {s['test']['hit3_rate'] + ' (' + str(s['test']['hit3_pct']) + '%)':<16} | {'':<8} | {'':<8}")
        print(f"{'':<25} | {'all':<6} | {s['all']['hit1_rate'] + ' (' + str(s['all']['hit1_pct']) + '%)':<12} | {s['all']['hit3_rate'] + ' (' + str(s['all']['hit3_pct']) + '%)':<16} | {'':<8} | {'':<8}")
        print("-" * 80)
    print(f"\nSaved full trace outputs to: {results_dir.resolve()}")
    print(f"Updated experiment log at: {exp_log_path.resolve()}")
    print("Pipeline execution complete!")


if __name__ == "__main__":
    main()
