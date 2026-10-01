import time
import logging
from typing import Dict, Any, List
from backend.services.fts_service import fts_service
from backend.services.faiss_service import faiss_service
from backend.services.rrf import rrf_service
from backend.services.reranker import reranker_service
from backend.services.evidence_gate import evidence_gate
from backend.services.gemini_service import gemini_service
from backend.config import DATA_MODE

logger = logging.getLogger("daic.retrieval")

class ArchivalRetrievalPipeline:
    @classmethod
    async def execute_retrieval(cls, question: str, top_k: int = 15) -> Dict[str, Any]:
        """
        Runs the full hybrid retrieval, fusion, reranking, and evidence gate pipeline.
        Returns all intermediate debug statistics for the Explainability / Judge view.
        """
        start_time = time.time()
        clean_q = question.strip()

        # Step 1 & 2: Parallel Lexical + Dense Retrieval
        fts_candidates = fts_service.search(clean_q, top_k=top_k)
        dense_candidates = faiss_service.search(clean_q, top_k=top_k)

        # Step 3: Reciprocal Rank Fusion (RRF)
        rrf_candidates = rrf_service.fuse(
            lexical_results=fts_candidates,
            dense_results=dense_candidates,
            top_n=15
        )

        # Step 4: Re-ranking
        reranked_chunks = reranker_service.rerank(
            query=clean_q,
            candidates=rrf_candidates,
            top_k=5
        )

        # Step 5: Evidence Gate Validation
        is_verified, reason, verified_evidence = evidence_gate.validate_retrieved_evidence(
            query=clean_q,
            reranked_chunks=reranked_chunks
        )

        elapsed_ms = round((time.time() - start_time) * 1000, 2)

        return {
            "query": clean_q,
            "latency_ms": elapsed_ms,
            "data_mode": DATA_MODE,
            "stages": {
                "fts_count": len(fts_candidates),
                "dense_count": len(dense_candidates),
                "rrf_candidates_count": len(rrf_candidates),
                "reranked_count": len(reranked_chunks),
                "verified_evidence_count": len(verified_evidence)
            },
            "fts_results": fts_candidates[:5],
            "dense_results": dense_candidates[:5],
            "rrf_results": rrf_candidates[:5],
            "reranked_results": reranked_chunks,
            "evidence_gate": {
                "passed": is_verified,
                "reason": reason,
                "verified_chunks": verified_evidence
            }
        }

    @classmethod
    async def ask(cls, question: str, language: str = "en") -> Dict[str, Any]:
        """
        Full end-to-end question answering pipeline:
        Retrieval -> RRF -> Rerank -> Evidence Gate -> Gemini Grounding -> Citation Validation
        """
        retrieval_meta = await cls.execute_retrieval(question)
        gate_info = retrieval_meta["evidence_gate"]

        # If Evidence Gate rejects:
        if not gate_info["passed"]:
            return {
                "answer": "The archive does not contain enough verified evidence to answer this question confidently. Insufficient archival evidence was found to provide a verified answer.",
                "verified": False,
                "reason": gate_info["reason"],
                "sources": [],
                "evidence": [],
                "data_mode": DATA_MODE,
                "retrieval": {
                    "query": question,
                    "latency_ms": retrieval_meta["latency_ms"],
                    "fts_results": retrieval_meta["stages"]["fts_count"],
                    "dense_results": retrieval_meta["stages"]["dense_count"],
                    "rrf_candidates": retrieval_meta["stages"]["rrf_candidates_count"],
                    "reranked": retrieval_meta["stages"]["reranked_count"],
                    "evidence_gate_passed": False
                },
                "explainability": retrieval_meta
            }

        verified_evidence = gate_info["verified_chunks"]

        # Gemini Grounded Generation
        synth_result = await gemini_service.generate_grounded_answer(
            question=question,
            verified_evidence=verified_evidence,
            language=language
        )

        # Citation & Provenance Validation
        citation_info = evidence_gate.validate_citations(
            answer_text=synth_result["answer"],
            verified_chunks=verified_evidence
        )

        return {
            "answer": synth_result["answer"],
            "verified": True,
            "is_demo": synth_result.get("is_demo", True),
            "data_mode": DATA_MODE,
            "sources": citation_info["sources"],
            "evidence": [
                {
                    "chunk_id": c["chunk_id"],
                    "document_id": c["document_id"],
                    "title": c.get("title"),
                    "page": c.get("page"),
                    "section": c.get("section_title"),
                    "excerpt": c.get("content"),
                    "relevance": c.get("rerank_score", 0.9),
                    "relevance_label": c.get("relevance_label", "Highly relevant"),
                    "provenance_type": c.get("provenance_type", "DEMO DATA")
                }
                for c in verified_evidence
            ],
            "retrieval": {
                "query": question,
                "latency_ms": retrieval_meta["latency_ms"],
                "fts_results": retrieval_meta["stages"]["fts_count"],
                "dense_results": retrieval_meta["stages"]["dense_count"],
                "rrf_candidates": retrieval_meta["stages"]["rrf_candidates_count"],
                "reranked": retrieval_meta["stages"]["reranked_count"],
                "evidence_gate_passed": True
            },
            "explainability": retrieval_meta
        }

retrieval_pipeline = ArchivalRetrievalPipeline()
