"""
Standalone script to build FAISS indices from local agriculture PDFs per state.

This script is NOT part of the FastAPI app. It will:
- Scan `agri_knowledge_base/` for state subfolders (e.g., `karnataka`, `maharashtra`)
- For each state folder:
  - Read all PDFs under that folder
  - Extract and chunk the text
  - Generate embeddings with Google Generative AI
  - Create a FAISS vector store for that state
  - Save it to `<state>_faiss_index/` (e.g., `karnataka_faiss_index/`)
"""

from __future__ import annotations
import time
import os
import sys
import shutil
from pathlib import Path
from typing import List, Tuple, Dict

from dotenv import load_dotenv
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings


def ensure_api_key() -> str:
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("ERROR: GOOGLE_API_KEY not found. Set it in a .env file or environment.")
        sys.exit(1)
    return api_key


def find_pdf_files(root_dir: Path) -> List[Path]:
    if not root_dir.exists():
        root_dir.mkdir(parents=True, exist_ok=True)
        print(f"Created knowledge directory at {root_dir}. Add state folders with PDFs and rerun.")
        sys.exit(0)
    return sorted(root_dir.glob("**/*.pdf"))


def find_state_dirs(base_dir: Path) -> List[Path]:
    if not base_dir.exists():
        base_dir.mkdir(parents=True, exist_ok=True)
        print(f"Created knowledge directory at {base_dir}. Add state folders and rerun.")
        sys.exit(0)
    return sorted([p for p in base_dir.iterdir() if p.is_dir()])


def extract_text_from_pdf(pdf_path: Path) -> List[Tuple[int, str]]:
    page_texts: List[Tuple[int, str]] = []
    try:
        reader = PdfReader(str(pdf_path))
        for page_index, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""
            if text.strip():
                page_texts.append((page_index, text))
    except Exception as exc:
        print(f"WARN: Failed to parse PDF: {pdf_path.name} ({exc})")
    return page_texts


def chunk_texts(page_texts: List[Tuple[int, str]], file_name: str) -> Tuple[List[str], List[Dict[str, str]]]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)
    chunks: List[str] = []
    metadatas: List[Dict[str, str]] = []

    for page_number, page_text in page_texts:
        page_chunks = splitter.split_text(page_text)
        chunks.extend(page_chunks)
        metadatas.extend(
            {
                "source": file_name,
                "page": str(page_number),
            }
            for _ in page_chunks
        )
    return chunks, metadatas


import time

def build_faiss_index(texts: List[str], metadatas: List[Dict[str, str]], output_dir: Path) -> None:
    # Remove old index folder to avoid stale files
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001",
        task_type="retrieval_document"
    )

    # Process in batches to avoid 429 ResourceExhausted errors
    batch_size = 10  # Adjust this (e.g., 50 or 20) if you still get errors
    vector_store = None

    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i : i + batch_size]
        batch_metadatas = metadatas[i : i + batch_size]
        
        print(f"    - Processing batch {i//batch_size + 1} (chunks {i} to {min(i + batch_size, len(texts))})...")
        
        if vector_store is None:
            vector_store = FAISS.from_texts(
                texts=batch_texts, 
                embedding=embeddings, 
                metadatas=batch_metadatas
            )
        else:
            vector_store.add_texts(texts=batch_texts, metadatas=batch_metadatas)
        
        # Give the API a break (10 seconds) between batches
        time.sleep(15)

    if vector_store:
        vector_store.save_local(str(output_dir))


def main() -> None:
    base_dir = Path(__file__).parent / "agri_knowledge_base"

    ensure_api_key()

    state_dirs = find_state_dirs(base_dir)
    if not state_dirs:
        print(f"No state folders found in {base_dir}. Add folders like 'karnataka', 'maharashtra' with PDFs and rerun.")
        sys.exit(0)

    print(f"Found {len(state_dirs)} state folder(s). Processing...")

    processed_states = 0
    for state_dir in state_dirs:
        state_name = state_dir.name.strip().lower().replace(" ", "_")
        pdf_paths = find_pdf_files(state_dir)
        if not pdf_paths:
            print(f"- Skipping '{state_name}': no PDFs found.")
            continue

        print(f"- {state_name}: {len(pdf_paths)} PDF(s). Extracting and chunking...")
        state_chunks: List[str] = []
        state_metadatas: List[Dict[str, str]] = []

        for pdf_path in pdf_paths:
            page_texts = extract_text_from_pdf(pdf_path)
            if not page_texts:
                print(f"  · WARN: No extractable text in {pdf_path.name}.")
                continue
            chunks, metadatas = chunk_texts(page_texts, file_name=pdf_path.name)
            state_chunks.extend(chunks)
            state_metadatas.extend(metadatas)
            print(f"  · {pdf_path.name}: {len(chunks)} chunk(s)")

        if not state_chunks:
            print(f"  · No text chunks generated for '{state_name}'. Skipping index build.")
            continue

        output_dir = Path(__file__).parent / "backend" / "faiss_indexes" / f"{state_name}_faiss_index"
        print(f"  · Building FAISS index with {len(state_chunks)} chunk(s) → {output_dir}")
        build_faiss_index(state_chunks, state_metadatas, output_dir)
        print(f"  · Saved state FAISS index to {output_dir}")
        processed_states += 1

    if processed_states == 0:
        print("No state indices were built.")
    else:
        print(f"Done. Built {processed_states} state index/indices.")


if __name__ == "__main__":
    main()


