# Contributing to Job Hunt Helper

## Development Workflow
1. **Branching**: Always create a feature branch before making changes.
2. **Testing**: Run tests (`pytest`) and ensure all unit/integration tests pass before submitting a PR.
3. **Linting & Types**: Keep code clean, adhere to PEP 8, and use type annotations for all new Python functions.
4. **Vector Store & Embeddings**: When modifying `VectorStore`, `EmbeddingService`, or `RAGEngine`:
   - Never commit runtime vector databases in `data/chroma_db/` (it is git-ignored).
   - Ensure unit tests mock external Gemini embedding and LLM calls so tests remain fast, offline, and deterministic.
   - Maintain the bundled ATS best-practice seed in `data/ats_knowledge.json`.

## Project Structure
- Code belongs in `app/`:
  - API routers in `app/routers/`
  - Business logic, embeddings, and RAG services in `app/services/`
  - SQLAlchemy models in `app/models/`
- Templates belong in `app/templates/`.
- All CSS/JS assets belong in `app/static/`.
- Knowledge bases and reference data belong in `data/`.
- Automated test suites belong in `tests/`.

## Running Tests
Run the test suite using pytest:
```bash
python -m pytest tests/ -v
```
To run specific RAG or vector store test modules:
```bash
python -m pytest tests/test_rag_engine.py tests/test_vector_store.py tests/test_embedding_service.py tests/test_recommendations.py -v
```

