import os

from agno.document.reader.pdf_reader import PDFReader
from agno.knowledge.combined import CombinedKnowledgeBase
from agno.knowledge.pdf import PDFKnowledgeBase
from agno.knowledge.text import TextKnowledgeBase
from agno.vectordb.lancedb.lance_db import LanceDb

from assistant.models import embedder


def get_knowledge_base(thread_id: str) -> CombinedKnowledgeBase:
    embeddings = embedder()
    lancedb_uri = f"/opt/vector_db/{thread_id}"
    pdfs_path = f"/opt/knowledge/{thread_id}/pdfs/"
    texts_path = f"/opt/knowledge/{thread_id}/texts/"

    if not os.path.exists(lancedb_uri):
        os.makedirs(lancedb_uri)
    if not os.path.exists(pdfs_path):
        os.makedirs(pdfs_path)
    if not os.path.exists(texts_path):
        os.makedirs(texts_path)

    pdf_knowledge_base = PDFKnowledgeBase(
        path=pdfs_path,
        vector_db=LanceDb(
            table_name="documents_pdf", uri=lancedb_uri, embedder=embeddings
        ),
        reader=PDFReader(chunk=True),
    )

    text_knowledge_base = TextKnowledgeBase(
        path=texts_path,
        vector_db=LanceDb(
            table_name="documents_text", uri=lancedb_uri, embedder=embeddings
        ),
    )

    knowledge_base = CombinedKnowledgeBase(
        sources=[pdf_knowledge_base, text_knowledge_base],
        vector_db=LanceDb(
            table_name="documents_combined", uri=lancedb_uri, embedder=embeddings
        ),
    )

    return knowledge_base
