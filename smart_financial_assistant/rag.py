"""RAG service backed by Qdrant for local financial knowledge retrieval."""

from __future__ import annotations

from threading import Lock
from typing import ClassVar

from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from .config import Settings


class RAGService:
    """Manage embedding, indexing, retrieval, and lifecycle for RAG documents."""

    _init_lock: ClassVar[Lock] = Lock()
    _client_cache: ClassVar[dict[str, QdrantClient]] = {}
    _store_cache: ClassVar[dict[str, QdrantVectorStore]] = {}

    def __init__(self, settings: Settings) -> None:
        """Initialize cached Qdrant client/store and ensure collection availability."""
        self._settings = settings
        self._embeddings = HuggingFaceEmbeddings(model_name=settings.embedding_model)
        cache_key = str(settings.qdrant_path.resolve())

        with self._init_lock:
            self._client = self._client_cache.get(cache_key) or QdrantClient(path=str(settings.qdrant_path))
            self._client_cache[cache_key] = self._client

            if not self._client.collection_exists(settings.qdrant_collection):
                vector_size = len(self._embeddings.embed_query("init"))
                self._client.create_collection(
                    collection_name=settings.qdrant_collection,
                    vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
                )

            store_key = f"{cache_key}:{settings.qdrant_collection}"
            self._store = self._store_cache.get(store_key) or QdrantVectorStore(
                client=self._client,
                collection_name=settings.qdrant_collection,
                embedding=self._embeddings,
            )
            self._store_cache[store_key] = self._store

    def _load_documents(self) -> list[Document]:
        """Load markdown and text files from the knowledge base directory."""
        docs: list[Document] = []
        base = self._settings.knowledge_base_path
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".md", ".txt"}:
                continue
            text = path.read_text(encoding="utf-8")
            if text.strip():
                docs.append(Document(page_content=text, metadata={"source": str(path)}))
        return docs

    def ingest(self, force: bool = False) -> int:
        """Split and index knowledge documents, optionally recreating the collection."""
        if (
            not force
            and self._client.collection_exists(self._settings.qdrant_collection)
            and self._client.count(self._settings.qdrant_collection).count > 0
        ):
            return 0

        docs = self._load_documents()
        if not docs:
            return 0

        splitter = RecursiveCharacterTextSplitter(chunk_size=900, chunk_overlap=120)
        chunks = splitter.split_documents(docs)

        if force:
            self._client.delete_collection(self._settings.qdrant_collection)
            vector_size = len(self._embeddings.embed_query("init"))
            self._client.create_collection(
                collection_name=self._settings.qdrant_collection,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )

            self._store = QdrantVectorStore(
                client=self._client,
                collection_name=self._settings.qdrant_collection,
                embedding=self._embeddings,
            )
            self._store.add_documents(chunks)

            cache_key = str(self._settings.qdrant_path.resolve())
            store_key = f"{cache_key}:{self._settings.qdrant_collection}"
            self._store_cache[store_key] = self._store
            return len(chunks)

        self._store.add_documents(chunks)
        return len(chunks)

    def as_retriever(self, k: int = 4):
        """Expose the vector store as a retriever configured with top-k search."""
        return self._store.as_retriever(search_kwargs={"k": k})

    def count_indexed_fragments(self) -> int:
        """Return the number of vectors currently stored in the collection."""
        if not self._client.collection_exists(self._settings.qdrant_collection):
            return 0
        return int(self._client.count(self._settings.qdrant_collection).count)

    def close(self) -> None:
        """Close the Qdrant client safely during normal shutdown."""
        try:
            self._client.close()
        except ImportError:
            # Guard against interpreter-shutdown import errors from qdrant local client.
            pass
