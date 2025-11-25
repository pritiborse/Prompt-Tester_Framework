import os
import glob
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
import pdfplumber

class RAGSystem:
    def __init__(self, config):
        self.docs_folder = config.get("paths", "docs_folder", "docs")
        embedding_model = config.get("models", "embedding_model", "all-MiniLM-L6-v2")
        self.model = SentenceTransformer(embedding_model)

        self.chunks = []
        self.chunk_embeddings = []
        self.index = None

        self._load_docs()
        self._create_index()

    def _chunk_text(self, text: str, chunk_size=80, overlap=10):
        words = text.split()
        chunks = []
        start = 0
        while start < len(words):
            end = min(start + chunk_size, len(words))
            chunks.append(" ".join(words[start:end]))
            start += chunk_size - overlap
        return chunks

    def _load_docs(self):
        txt_files = glob.glob(os.path.join(self.docs_folder, "*.txt"))
        pdf_files = glob.glob(os.path.join(self.docs_folder, "*.pdf"))
        # Process text files
        for file in txt_files:
            with open(file, "r", encoding="utf-8") as f:
                text = f.read().strip()
                if not text:
                    continue
                paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
                for para in paragraphs:
                    self.chunks.extend(self._chunk_text(para))
        # Process PDF files
        for file in pdf_files:
            with pdfplumber.open(file) as pdf:
                text = ""
                for page in pdf.pages:
                    text += page.extract_text() or ""
                if not text:
                    continue
                paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
                for para in paragraphs:
                    self.chunks.extend(self._chunk_text(para))

    def _embed_chunk(self, chunk: str):
        return self.model.encode(chunk, convert_to_numpy=True).astype(np.float32)

    def _create_index(self):
        if not self.chunks:
            raise ValueError(f"No chunks found in {self.docs_folder}.")
        self.chunk_embeddings = [self._embed_chunk(c) for c in self.chunks]
        dim = self.chunk_embeddings[0].shape[0]
        self.index = faiss.IndexFlatL2(dim)
        self.index.add(np.array(self.chunk_embeddings))

    def retrieve(self, query: str, top_k=3):
        query_embedding = self._embed_chunk(query)
        distances, indices = self.index.search(np.array([query_embedding]), top_k)
        return [self.chunks[i] for i in indices[0]]
