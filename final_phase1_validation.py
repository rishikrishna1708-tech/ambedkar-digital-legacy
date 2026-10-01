import asyncio
import hashlib
import json
import os
import sqlite3
import httpx
from backend.services.faiss_service import faiss_service

BASE_URL = "http://127.0.0.1:8000"

async def run_final_validation():
    print("==================================================")
    print("PHASE I — FINAL RUNTIME VALIDATION")
    print("AMBEDKAR DIGITAL LEGACY — AI-Powered Heritage Platform")
    print("==================================================\n")

    val_data = {}

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Start / Verify Server Running
        print("--- Item 1 & 2: Verifying Server & HTML Page Routes ---")
        health = await client.get(f"{BASE_URL}/api/health")
        assert health.status_code == 200, f"Health check failed: {health.status_code}"
        print(f"  Health Check: 200 OK | Service: {health.json()['service']} | Mode: {health.json()['data_mode']}")

        routes = ["/admin", "/archive-view", "/manuscripts", "/ask"]
        route_metrics = {}
        for r in routes:
            resp = await client.get(f"{BASE_URL}{r}")
            assert resp.status_code == 200, f"Route {r} failed with {resp.status_code}"
            route_metrics[r] = {"status": resp.status_code, "bytes": len(resp.text)}
            print(f"  Route {r}: {resp.status_code} OK ({len(resp.text)} bytes)")
        val_data["routes"] = route_metrics

        # Clean-up any previous ADL-MS-0004 records for a 100% clean test run
        clean_conn = sqlite3.connect("data/daic_archive.db")
        clean_c = clean_conn.cursor()
        clean_c.execute("DELETE FROM documents WHERE id = 'ADL-MS-0004'")
        clean_c.execute("DELETE FROM chunks WHERE document_id = 'ADL-MS-0004'")
        clean_c.execute("DELETE FROM archive_fts WHERE document_id = 'ADL-MS-0004'")
        clean_c.execute("DELETE FROM ocr_results WHERE document_id = 'ADL-MS-0004'")
        clean_c.execute("DELETE FROM audit_logs WHERE entity_id = 'ADL-MS-0004'")
        clean_conn.commit()
        clean_conn.close()

        faiss_service.metadata = [m for m in faiss_service.metadata if m.get("document_id") != "ADL-MS-0004"]
        faiss_service.save_index()

        for old_f in ["data/uploads/ADL-MS-0004.pdf", "data/uploads/ADL-MS-0004_p1.png", "data/uploads/ADL-MS-0004_p2.png"]:
            if os.path.exists(old_f):
                os.remove(old_f)

        # 3. Upload One Real Archival PDF
        print("\n--- Item 3: Uploading Real Archival PDF ---")
        pdf_filename = "adl_annihilation_of_caste_1936.pdf"
        with open(pdf_filename, "rb") as f:
            pdf_bytes = f.read()
        expected_sha256 = hashlib.sha256(pdf_bytes).hexdigest()
        expected_size = len(pdf_bytes)

        upload_payload = {
            "title": "Annihilation of Caste: With a Reply to Mahatma Gandhi (1936)",
            "author": "Dr. B. R. Ambedkar",
            "year": "1936",
            "collection": "Historical Treatises & Public Addresses",
            "doc_type": "Manuscript",
            "language": "en",
            "source_institution": "Ambedkar Memorial Archives / Jat-Pat-Todak Mandal Historical Collection",
            "description": "Historic undelivered presidential address prepared for the 1936 Annual Conference of the Jat-Pat-Todak Mandal of Lahore.",
            "keywords": "Annihilation of Caste, Liberty, Equality, Fraternity, Democracy, Associated Living",
            "provenance_type": "USER-UPLOADED DATA"
        }

        with open(pdf_filename, "rb") as f:
            files = {"file": (pdf_filename, f, "application/pdf")}
            up_res = await client.post(f"{BASE_URL}/api/admin/upload", data=upload_payload, files=files)

        assert up_res.status_code == 200, f"Upload endpoint failed: {up_res.text}"
        up_json = up_res.json()
        doc_id = up_json["document_id"]
        print(f"  Assigned Document ID: {doc_id}")
        print(f"  Recorded Filename: {up_json['original_filename']}")
        print(f"  Recorded SHA-256: {up_json['sha256_hash']}")
        print(f"  Recorded File Size: {up_json['file_size']} bytes")
        print(f"  Initial Verification Status: {up_json['verification_status']}")
        val_data["upload"] = up_json

        # 4. Verify Database Preservation & Integrity
        print("\n--- Item 4: Verifying Document Integrity in SQLite ---")
        conn = sqlite3.connect("data/daic_archive.db")
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        c.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
        doc_row = dict(c.fetchone())
        print(f"  DB Document ID: {doc_row['id']}")
        print(f"  DB Original Filename: {doc_row['original_filename']}")
        print(f"  DB File Type: {doc_row['file_type']}")
        print(f"  DB File Size: {doc_row['file_size']} bytes")
        print(f"  DB SHA-256: {doc_row['sha256_hash']}")
        print(f"  DB Upload Timestamp: {doc_row['created_at']}")
        print(f"  DB Preserved File Path: {doc_row['file_path']}")
        print(f"  Physical File Exists: {os.path.exists(doc_row['file_path'])}")

        with open(doc_row['file_path'], 'rb') as f:
            disk_sha256 = hashlib.sha256(f.read()).hexdigest()
        assert disk_sha256 == expected_sha256, "Preserved disk file hash mismatch!"
        print(f"  Disk File SHA-256 Match: True ({disk_sha256})")
        val_data["db_record"] = doc_row

        # 5. Verify Page Processing & Facsimile Generation
        print("\n--- Item 5: Verifying Page Processing & Facsimiles ---")
        page_count = doc_row["page_count"]
        print(f"  Extracted Page Count: {page_count} (Expected: 2)")
        assert page_count == 2, f"Expected 2 pages, got {page_count}"

        p1_img = f"data/uploads/{doc_id}_p1.png"
        p2_img = f"data/uploads/{doc_id}_p2.png"
        assert os.path.exists(p1_img), f"Facsimile image {p1_img} not found!"
        assert os.path.exists(p2_img), f"Facsimile image {p2_img} not found!"
        print(f"  Page 1 Facsimile: {p1_img} ({os.path.getsize(p1_img)} bytes)")
        print(f"  Page 2 Facsimile: {p2_img} ({os.path.getsize(p2_img)} bytes)")
        print(f"  Original PDF Untouched: True (SHA-256 matches exactly)")
        val_data["facsimiles"] = {
            "p1": {"path": p1_img, "bytes": os.path.getsize(p1_img)},
            "p2": {"path": p2_img, "bytes": os.path.getsize(p2_img)}
        }

        # 6. Verify OCR Records & Confidence Values
        print("\n--- Item 6: Verifying OCR Records & Non-Fabricated Confidence ---")
        c.execute("SELECT id, page, image_path, confidence, archivist_status, recognized_text FROM ocr_results WHERE document_id = ? ORDER BY page ASC", (doc_id,))
        ocr_records = [dict(r) for r in c.fetchall()]
        print(f"  OCR Records Created: {len(ocr_records)}")
        assert len(ocr_records) == 2, f"Expected 2 OCR records, got {len(ocr_records)}"

        for r in ocr_records:
            print(f"    Record {r['id']} (Page {r['page']}):")
            print(f"      Confidence: {r['confidence']} (Display: Confidence unavailable)")
            print(f"      Initial Status: {r['archivist_status']}")
            print(f"      Sample Text: {r['recognized_text'][:75]}...")
            assert r["confidence"] is None, "Confidence should be None (non-fabricated) for PyMuPDF layout extractor!"
            assert r["archivist_status"] == "pending_review", "Status must initially be pending_review!"
        val_data["ocr_records"] = ocr_records

        # 7. IMPORTANT: Verify Pre-Verification Isolation
        print("\n--- Item 7: Verifying Complete Pre-Verification Isolation ---")
        c.execute("SELECT COUNT(*) as cnt FROM chunks WHERE document_id = ?", (doc_id,))
        pre_chunks = c.fetchone()['cnt']
        c.execute("SELECT COUNT(*) as cnt FROM archive_fts WHERE document_id = ?", (doc_id,))
        pre_fts = c.fetchone()['cnt']
        pre_faiss = len([m for m in faiss_service.metadata if m.get('document_id') == doc_id])

        print(f"  Pre-Verification Chunks in SQLite: {pre_chunks} (Must be 0)")
        print(f"  Pre-Verification FTS5 Entries: {pre_fts} (Must be 0)")
        print(f"  Pre-Verification FAISS Vectors: {pre_faiss} (Must be 0)")
        assert pre_chunks == 0, "Unverified chunks exist in SQLite!"
        assert pre_fts == 0, "Unverified chunks exist in FTS5!"
        assert pre_faiss == 0, "Unverified vectors exist in FAISS!"

        # Check Evidence Gate isolation via Ask AI
        pre_ask = await client.post(f"{BASE_URL}/api/ask", json={"question": "What is Dr. Ambedkar's definition of an associated society in Annihilation of Caste?"})
        pre_sources = [s for s in pre_ask.json().get("sources", []) if s.get("document_id") == doc_id]
        print(f"  Pre-Verification Ask AI Citations for {doc_id}: {len(pre_sources)} (Must be 0)")
        assert len(pre_sources) == 0, "Evidence Gate leaked unverified document into Ask AI!"
        val_data["isolation"] = {"pre_chunks": pre_chunks, "pre_fts": pre_fts, "pre_faiss": pre_faiss, "leaked_sources": len(pre_sources)}

        # 8 & 9. Archivist Review Station (Select, Edit, Save, Verify)
        print("\n--- Item 8 & 9: Testing Archivist OCR Review & Verification ---")
        pending_res = await client.get(f"{BASE_URL}/api/admin/ocr-pending?doc_id={doc_id}")
        pending_list = pending_res.json()["records"]
        print(f"  Fetched pending records for {doc_id}: {len(pending_list)}")

        # Review Page 1
        p1 = next(r for r in pending_list if r["page"] == 1)
        rev1_payload = {
            "ocr_id": p1["id"],
            "recognized_text": p1["recognized_text"] + "\n\n[Archivist Verified: Section I text authenticated against original 1936 Lahore publication.]",
            "status": "verified",
            "notes": "Verified Section I text against first edition 1936 treatise."
        }
        rev1_res = await client.post(f"{BASE_URL}/api/admin/ocr-review", json=rev1_payload)
        assert rev1_res.status_code == 200, f"Page 1 review failed: {rev1_res.text}"
        print(f"  Page 1 Verification: Status 200, Chunks Indexed: {rev1_res.json()['chunks_indexed']}")

        # Review Page 2
        p2 = next(r for r in pending_list if r["page"] == 2)
        rev2_payload = {
            "ocr_id": p2["id"],
            "recognized_text": p2["recognized_text"] + "\n\n[Archivist Verified: Section II democratic ideal authenticated.]",
            "status": "verified",
            "notes": "Verified Section II text against first edition 1936 treatise."
        }
        rev2_res = await client.post(f"{BASE_URL}/api/admin/ocr-review", json=rev2_payload)
        assert rev2_res.status_code == 200, f"Page 2 review failed: {rev2_res.text}"
        print(f"  Page 2 Verification: Status 200, Chunks Indexed: {rev2_res.json()['chunks_indexed']}")
        val_data["review"] = {"p1_res": rev1_res.json(), "p2_res": rev2_res.json()}

        # 10. Post-Verification Storage & Indexing Verification
        print("\n--- Item 10: Verifying Post-Verification Storage & Indexing ---")
        c.execute("SELECT id, document_id, chunk_index, page, char_count, word_count, provenance_type, content FROM chunks WHERE document_id = ? ORDER BY chunk_index ASC", (doc_id,))
        post_chunks = [dict(r) for r in c.fetchall()]
        print(f"  Total Chunks Created: {len(post_chunks)}")
        assert len(post_chunks) > 0, "No chunks created after verification!"

        chunk_pages = set()
        for ch in post_chunks:
            chunk_pages.add(ch["page"])
            assert ch["document_id"] == doc_id
            print(f"    Chunk {ch['id']}: Doc: {ch['document_id']}, Page {ch['page']}, Words: {ch['word_count']}, Prov: {ch['provenance_type']}")
        assert 1 in chunk_pages and 2 in chunk_pages, "Both pages must have page-attributed chunks!"

        c.execute("SELECT COUNT(*) as cnt FROM archive_fts WHERE document_id = ?", (doc_id,))
        post_fts = c.fetchone()['cnt']
        print(f"  FTS5 Entries Indexed: {post_fts}")
        assert post_fts == len(post_chunks), "FTS5 count does not match chunk count!"

        faiss_service.load_index()
        post_faiss_vectors = [m for m in faiss_service.metadata if m.get("document_id") == doc_id]
        print(f"  FAISS Vectors Indexed: {len(post_faiss_vectors)}")
        assert len(post_faiss_vectors) == len(post_chunks), "FAISS vector count does not match chunk count!"

        # Verify vector metadata mapping
        for v in post_faiss_vectors:
            assert v["document_id"] == doc_id
            assert v["page"] in (1, 2)
            assert "chunk_id" in v
        print("  Vector Metadata Persistent Mapping: Verified (maps chunk_id, document_id, page)")

        c.execute("SELECT verification_status, ocr_status FROM documents WHERE id = ?", (doc_id,))
        updated_doc = dict(c.fetchone())
        print(f"  Updated Document Status: {updated_doc['verification_status']}")
        assert updated_doc["verification_status"] == "VERIFIED SOURCE", "Status must be promoted to VERIFIED SOURCE!"
        val_data["post_indexing"] = {
            "chunk_count": len(post_chunks),
            "fts_count": post_fts,
            "faiss_count": len(post_faiss_vectors),
            "doc_status": updated_doc["verification_status"]
        }

        # 11 & 12. Hybrid Retrieval (Exact Keyword & Semantic Query)
        print("\n--- Item 11 & 12: Testing Hybrid Retrieval & Fusion Trace ---")
        queries = [
            ("Exact Keyword", "primarily a mode of associated living, of conjoint communicated experience"),
            ("Semantic Query", "What constitutes Dr. Ambedkar's ideal society and definition of democracy?")
        ]

        ret_data_log = {}
        for q_label, q_str in queries:
            r_res = await client.post(f"{BASE_URL}/api/retrieve", json={"query": q_str, "top_k": 10})
            assert r_res.status_code == 200, f"Retrieval failed: {r_res.text}"
            r_json = r_res.json()
            stages = r_json["stages"]
            top_verified = r_json["evidence_gate"]["verified_chunks"]
            top_cand = top_verified[0] if top_verified else None

            print(f"  [{q_label}] Query: '{q_str}'")
            print(f"    Latency: {r_json['latency_ms']} ms")
            print(f"    Stages: FTS5={stages['fts_count']}, Dense={stages['dense_count']}, RRF={stages['rrf_candidates_count']}, Reranked={stages['reranked_count']}")
            print(f"    Evidence Gate Passed: {r_json['evidence_gate']['passed']} ({r_json['evidence_gate']['reason']})")
            if top_cand:
                print(f"    Top Chunk: {top_cand['chunk_id']} | Doc: {top_cand['document_id']} | Page: {top_cand['page']} | Score: {top_cand['rerank_score']}")
                print(f"    Excerpt: {top_cand['content'][:90]}...")
            
            assert r_json["evidence_gate"]["passed"] is True, "Evidence gate must pass for valid queries!"
            ret_data_log[q_label] = {
                "latency_ms": r_json["latency_ms"],
                "stages": stages,
                "gate_passed": r_json["evidence_gate"]["passed"],
                "top_chunk": top_cand["chunk_id"] if top_cand else None,
                "top_doc": top_cand["document_id"] if top_cand else None,
                "top_page": top_cand["page"] if top_cand else None,
                "score": top_cand["rerank_score"] if top_cand else None
            }
        val_data["retrieval"] = ret_data_log

        # 13. Test /api/ask Grounded Question Answering
        print("\n--- Item 13: Testing /api/ask Grounded Answering ---")
        ask_q = "How does Dr. Ambedkar define democracy and his ideal of society in Annihilation of Caste?"
        ask_res = await client.post(f"{BASE_URL}/api/ask", json={"question": ask_q, "language": "en"})
        assert ask_res.status_code == 200, f"/api/ask failed: {ask_res.text}"
        ask_json = ask_res.json()

        print(f"  Ask AI Verified: {ask_json['verified']}")
        print(f"  Grounded Answer Output:\n{ask_json['answer']}\n")
        print(f"  Sources Count: {len(ask_json.get('sources', []))}")

        matching_source = next((s for s in ask_json.get("sources", []) if s.get("document_id") == doc_id), None)
        assert matching_source is not None, f"Ask AI response did not cite uploaded document {doc_id}!"
        print(f"  Primary Citation Verified:")
        print(f"    Document ID: {matching_source['document_id']}")
        print(f"    Document Title: {matching_source['title']}")
        print(f"    Page Number: {matching_source['page']}")
        print(f"    Verification Status: {matching_source['verification_status']}")
        print(f"    Provenance: {matching_source['provenance_type']}")
        val_data["ask"] = {
            "verified": ask_json["verified"],
            "answer": ask_json["answer"],
            "cited_doc": matching_source["document_id"],
            "cited_page": matching_source["page"],
            "status": matching_source["verification_status"]
        }

        # 14. Verify Manuscript Viewer Dynamic Rendering
        print("\n--- Item 14: Verifying Manuscript Viewer Integration ---")
        man_doc_res = await client.get(f"{BASE_URL}/api/archive?type=Manuscript")
        man_docs = man_doc_res.json().get("documents", [])
        man_match = next((d for d in man_docs if d["id"] == doc_id), None)
        assert man_match is not None, f"Document {doc_id} not returned in manuscripts catalogue!"
        print(f"  Manuscript Viewer Found Ingested Document: {man_match['id']} - '{man_match['title']}'")
        print(f"  Facsimile Image Path: {p1_img} (Served at /uploads/{doc_id}_p1.png)")
        val_data["manuscript_viewer"] = {"found": True, "id": man_match["id"], "facsimile_url": f"/uploads/{doc_id}_p1.png"}

        # 15. Verify Archive Catalogue Integration
        print("\n--- Item 15: Verifying Archive Catalogue Integration ---")
        arc_search = await client.get(f"{BASE_URL}/api/archive?q=Annihilation")
        arc_results = arc_search.json().get("documents", [])
        arc_match = next((d for d in arc_results if d["id"] == doc_id), None)
        assert arc_match is not None, f"Document {doc_id} not found in Archive search for 'Annihilation'!"
        print(f"  Catalogue Search Result: ID {arc_match['id']} - '{arc_match['title']}'")
        print(f"  Provenance Badge: {arc_match['provenance_type']} | Status: {arc_match['verification_status']}")
        val_data["catalogue"] = {"found": True, "id": arc_match["id"], "provenance": arc_match["provenance_type"], "status": arc_match["verification_status"]}

        # 16. Verify Demo Data Integrity
        print("\n--- Item 16: Verifying Existing Demo Records Integrity ---")
        demo_ids = [
            "BAWS_VOL_10_LABOUR",
            "BAWS_VOL_05_PROVIDENCE",
            "CAD_VOL_07_ART17",
            "CAD_FINAL_SPEECH_1949",
            "MAHAD_SATYAGRAHA_1927"
        ]
        c.execute("SELECT id, title, provenance_type, verification_status FROM documents WHERE id IN ({})".format(','.join('?'*len(demo_ids))), demo_ids)
        demo_docs = [dict(r) for r in c.fetchall()]
        print(f"  Found {len(demo_docs)} / {len(demo_ids)} demo documents in database.")
        assert len(demo_docs) == len(demo_ids), "Some demo documents are missing!"
        for d in demo_docs:
            assert d["provenance_type"] == "DEMO DATA", f"Demo document {d['id']} provenance was altered!"
            print(f"    {d['id']}: '{d['title'][:40]}...' [{d['provenance_type']}]")

        val_data["demo_data"] = {"count": len(demo_docs), "intact": True}
        conn.close()

    print("\n==================================================")
    print("ALL 16 TEST SECTIONS COMPLETED WITH 100% PASS RATE")
    print("PHASE I STATUS: PASS")
    print("==================================================")

    with open("final_phase1_validation_metrics.json", "w") as f:
        json.dump(val_data, f, indent=2)

asyncio.run(run_final_validation())
