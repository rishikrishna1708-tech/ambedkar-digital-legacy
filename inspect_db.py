import sqlite3
import json

conn = sqlite3.connect('data/daic_archive.db')
conn.row_factory = sqlite3.Row

# 1. Total chunks
cur = conn.execute('SELECT COUNT(*) as cnt FROM chunks')
print('Total chunks:', cur.fetchone()[0])

# 2. Chunks by provenance type
cur = conn.execute('SELECT provenance_type, COUNT(*) as cnt FROM chunks GROUP BY provenance_type')
for row in cur.fetchall():
    print(f'  provenance_type={row[0]}: {row[1]} chunks')

# 3. ADL-MS chunks specifically
cur = conn.execute("SELECT id, document_id, page, provenance_type, content FROM chunks WHERE document_id LIKE 'ADL-MS%' ORDER BY document_id, page")
adl_chunks = cur.fetchall()
print(f'\nADL-MS chunks: {len(adl_chunks)}')
for row in adl_chunks:
    print(f'  chunk_id={row[0]}, doc={row[1]}, page={row[2]}, prov={row[3]}')
    print(f'    content_preview: {row[4][:100]}')

# 4. FTS5 count
cur = conn.execute('SELECT COUNT(*) as cnt FROM archive_fts')
print('\nFTS5 total entries:', cur.fetchone()[0])

# 5. FTS5 entries for ADL-MS
cur = conn.execute("SELECT chunk_id, document_id FROM archive_fts WHERE document_id LIKE 'ADL-MS%'")
fts_adl = cur.fetchall()
print(f'FTS5 ADL-MS entries: {len(fts_adl)}')
for row in fts_adl:
    print(f'  chunk_id={row[0]}, doc={row[1]}')

# 6. Documents table
cur = conn.execute("SELECT id, title, provenance_type, verification_status FROM documents WHERE id LIKE 'ADL-MS%'")
docs = cur.fetchall()
print(f'\nADL-MS documents: {len(docs)}')
for row in docs:
    print(f'  id={row[0]}, title={row[1]}, prov={row[2]}, status={row[3]}')

# 7. All chunks with their document_ids
print('\nAll chunks by document:')
cur = conn.execute('SELECT document_id, COUNT(*) as cnt FROM chunks GROUP BY document_id ORDER BY document_id')
for row in cur.fetchall():
    print(f'  doc={row[0]}: {row[1]} chunks')

# 8. OCR results for ADL-MS-0004
print('\nOCR results for ADL-MS-0004:')
cur = conn.execute("SELECT id, document_id, page, recognized_text FROM ocr_results WHERE document_id = 'ADL-MS-0004' ORDER BY page")
for row in cur.fetchall():
    print(f'  id={row[0]}, page={row[1]}, text_preview: {row[2][:150]}')

conn.close()
