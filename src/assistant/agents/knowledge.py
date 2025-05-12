import os

from agno.document.reader.pdf_reader import PDFReader
from agno.knowledge.combined import CombinedKnowledgeBase
from agno.knowledge.pdf import PDFKnowledgeBase
from agno.knowledge.text import TextKnowledgeBase
from agno.vectordb.lancedb.lance_db import LanceDb

from assistant.agents.models import embedder


def get_knowledge_base(thread_id: str) -> CombinedKnowledgeBase:
    lancedb_uri = f"/opt/vector_db/{thread_id}"
    files_path = f"/opt/knowledge/{thread_id}"

    os.makedirs(lancedb_uri, exist_ok=True)
    os.makedirs(files_path, exist_ok=True)

    embeddings = embedder()

    pdf_knowledge_base = PDFKnowledgeBase(
        path=files_path,
        vector_db=LanceDb(
            table_name="documents_pdf", uri=lancedb_uri, embedder=embeddings
        ),
        reader=PDFReader(),
    )

    text_knowledge_base = TextKnowledgeBase(
        path=files_path,
        vector_db=LanceDb(
            table_name="documents_text", uri=lancedb_uri, embedder=embeddings
        ),
    )

    knowledge_base = CombinedKnowledgeBase(
        sources=[pdf_knowledge_base, text_knowledge_base],
        vector_db=LanceDb(
            table_name="documents_combined",
            uri=lancedb_uri,
            embedder=embeddings,
        ),
    )

    return knowledge_base
