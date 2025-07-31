# Stanford Medical Facilities: Documentation Crawler and RAG Agent

An intelligent documentation crawler and RAG (Retrieval-Augmented Generation) agent built using Pydantic AI and Supabase. The agent can crawl Stanford Medical Facilities documentation websites, store content in a vector database, and provide intelligent answers to user questions by retrieving and analyzing relevant documentation chunks.

## Features

- Medical facilities documentation website crawling and chunking
- Vector database storage with Supabase
- Semantic search using all-mpnet-base-v2 embeddings
- RAG-based question answering using Gemini 2.0
- Support for code block preservation
- Streamlit UI for interactive querying
- Available as both API endpoint and web interface

## Prerequisites

- Python 3.11+
- Supabase account and database
- Google Gemini API key
- Streamlit (for web interface)

## Installation

1. Clone the repository and navigate to the stanford-medical-facilities-agent directory:
```bash
cd stanford-medical-facilities-agent
```

2. Install dependencies (recommended to use a Python virtual environment):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Set up environment variables:
   - Create a `.env` file in the project directory
   - Edit `.env` with your API keys and preferences:
   ```env
   GEMINI_API_KEY=your_gemini_api_key
   SUPABASE_URL=your_supabase_url
   SUPABASE_SERVICE_KEY=your_supabase_service_key
   ```

## Database Setup

Execute the SQL commands in `site_pages.sql` to:
1. Create the necessary tables
2. Enable vector similarity search
3. Set up Row Level Security policies

In Supabase, do this by going to the "SQL Editor" tab and pasting in the SQL into the editor there. Then click "Run".

**Important**: Make sure your Supabase database has the `pgvector` extension enabled for vector similarity search.

## Usage

### Crawl Documentation

To crawl and store documentation in the vector database:

```bash
python crawl_stanford_medical_facilities.py
```

This will:
1. Fetch URLs from the Stanford Medical Facilities website
2. Crawl each page and split into chunks
3. Generate embeddings using all-mpnet-base-v2 and store in Supabase

### Streamlit Web Interface

For an interactive web interface to query the documentation:

```bash
streamlit run streamlit_ui.py
```

The interface will be available at `http://localhost:8501`

## Configuration

### Database Schema

The Supabase database uses the following schema:
```sql
CREATE TABLE site_pages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    url TEXT,
    chunk_number INTEGER,
    title TEXT,
    summary TEXT,
    content TEXT,
    metadata JSONB,
    embedding VECTOR(768)  -- Note: all-mpnet-base-v2 uses 768 dimensions
);
```

### Chunking Configuration

You can configure chunking parameters in `crawl_stanford_medical_facilities.py`:
```python
chunk_size = 5000  # Characters per chunk
```

The chunker intelligently preserves:
- Code blocks
- Paragraph boundaries
- Sentence boundaries

## Project Structure

- `crawl_stanford_medical_facilities.py`: Documentation crawler and processor
- `stanford_medical_facilities_expert.py`: RAG agent implementation
- `streamlit_ui.py`: Web interface
- `requirements.txt`: Project dependencies

## Key Differences from Original

1. **LLM Model**: Uses Google Gemini 2.0 instead of OpenAI GPT models
2. **Embedding Model**: Uses all-mpnet-base-v2 instead of OpenAI embeddings
3. **Vector Dimensions**: 768 dimensions instead of 1536 (matching mpnet-base-v2)
4. **Target Website**: Stanford Medical Facilities instead of Pydantic AI docs
5. **Source Metadata**: Uses 'stanford_medical_facilities' as source identifier

## Error Handling

The system includes robust error handling for:
- Network failures during crawling
- API rate limits
- Database connection issues
- Embedding generation errors
- Invalid URLs or content

## Troubleshooting

1. **Gemini API Issues**: Make sure your Gemini API key is valid and has sufficient quota
2. **Embedding Model Download**: The first run will download the all-mpnet-base-v2 model (~1GB)
3. **Supabase Vector Extension**: Ensure pgvector extension is enabled in your Supabase database
4. **Memory Issues**: The sentence-transformers model requires significant RAM, consider using a machine with at least 4GB RAM 