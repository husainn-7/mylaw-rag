FROM python:3.12-slim

RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH" \
    HF_HOME="/home/user/.cache/huggingface" \
    PYTHONUNBUFFERED=1

RUN mkdir -p /home/user/app/data/processed /home/user/app/index
WORKDIR /home/user/app

# CPU-only torch keeps the image small
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=user src ./src
COPY --chown=user app ./app
COPY --chown=user .streamlit ./.streamlit
COPY --chown=user data/processed/chunks.jsonl ./data/processed/chunks.jsonl

# build the search index and cache the reranker at build time so the app starts fast
RUN python src/index.py && python -c "from sentence_transformers import CrossEncoder; CrossEncoder('cross-encoder/ms-marco-MiniLM-L-12-v2')"

EXPOSE 7860
CMD ["streamlit", "run", "app/ui.py", "--server.port=7860", "--server.address=0.0.0.0", "--server.headless=true"]
