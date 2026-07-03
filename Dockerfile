FROM python:3.11-slim

WORKDIR /app

# System dependencies (Tesseract for OCR)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir streamlit requests python-dotenv pydantic \
    sentence-transformers scikit-learn chromadb pandas plotly \
    Pillow pytesseract pytest pytest-cov psutil

# App source
COPY . .

# Create vector store directory
RUN mkdir -p vector_store/chroma_db

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false"]
