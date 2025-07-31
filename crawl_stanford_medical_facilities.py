import os
import sys
import json
import asyncio
import requests
import time
from typing import List, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlparse
from dotenv import load_dotenv

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
import google.generativeai as genai
from sentence_transformers import SentenceTransformer
from supabase import create_client, Client

load_dotenv()

# Initialize Gemini and Supabase clients
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-2.0-flash-exp')

# Initialize sentence transformer for embeddings
embedding_model = SentenceTransformer('all-mpnet-base-v2')

supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

@dataclass
class ProcessedChunk:
    url: str
    chunk_number: int
    title: str
    summary: str
    content: str
    metadata: Dict[str, Any]
    embedding: List[float]

def chunk_text(text: str, chunk_size: int = 5000) -> List[str]:
    """Split text into chunks, respecting code blocks and paragraphs."""
    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        # Calculate end position
        end = start + chunk_size

        # If we're at the end of the text, just take what's left
        if end >= text_length:
            chunks.append(text[start:].strip())
            break

        # Try to find a code block boundary first (```)
        chunk = text[start:end]
        code_block = chunk.rfind('```')
        if code_block != -1 and code_block > chunk_size * 0.3:
            end = start + code_block

        # If no code block, try to break at a paragraph
        elif '\n\n' in chunk:
            # Find the last paragraph break
            last_break = chunk.rfind('\n\n')
            if last_break > chunk_size * 0.3:  # Only break if we're past 30% of chunk_size
                end = start + last_break

        # If no paragraph break, try to break at a sentence
        elif '. ' in chunk:
            # Find the last sentence break
            last_period = chunk.rfind('. ')
            if last_period > chunk_size * 0.3:  # Only break if we're past 30% of chunk_size
                end = start + last_period + 1

        # Extract chunk and clean it up
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # Move start position for next chunk
        start = max(start + 1, end)

    return chunks

async def get_title_and_summary_with_retry(chunk: str, url: str, max_retries: int = 3) -> Dict[str, str]:
    """Extract title and summary using Gemini 2.0 with rate limiting and retry logic."""
    system_prompt = """You are an AI that extracts titles and summaries from medical facilities documentation chunks.
    Return a JSON object with 'title' and 'summary' keys.
    For the title: If this seems like the start of a document, extract its title. If it's a middle chunk, derive a descriptive title.
    For the summary: Create a concise summary of the main points in this chunk.
    Keep both title and summary concise but informative."""
    
    for attempt in range(max_retries):
        try:
            prompt = f"{system_prompt}\n\nURL: {url}\n\nContent:\n{chunk[:1000]}..."
            
            # Add delay between requests to avoid rate limiting
            if attempt > 0:
                delay = min(2 ** attempt, 30)  # Exponential backoff, max 30 seconds
                print(f"Rate limited, waiting {delay} seconds before retry {attempt + 1}/{max_retries}")
                await asyncio.sleep(delay)
            
            response = model.generate_content(prompt)
            
            # Try to parse JSON from response
            try:
                return json.loads(response.text)
            except json.JSONDecodeError:
                # If JSON parsing fails, create a simple title and summary
                return {
                    "title": f"Stanford Medical Facilities - {urlparse(url).path.split('/')[-1]}",
                    "summary": f"Content from {url} - {len(chunk)} characters"
                }
                
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "quota" in error_msg.lower():
                if attempt < max_retries - 1:
                    print(f"Rate limited (attempt {attempt + 1}/{max_retries}): {error_msg}")
                    continue
                else:
                    print(f"Rate limit exceeded after {max_retries} attempts, using fallback")
                    return {
                        "title": f"Stanford Medical Facilities - {urlparse(url).path.split('/')[-1]}",
                        "summary": f"Content from {url} - {len(chunk)} characters"
                    }
            else:
                print(f"Error getting title and summary (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    return {"title": "Error processing title", "summary": "Error processing summary"}
    
    return {"title": "Error processing title", "summary": "Error processing summary"}

def get_embedding(text: str) -> List[float]:
    """Get embedding vector using all-mpnet-base-v2."""
    try:
        embedding = embedding_model.encode(text)
        return embedding.tolist()
    except Exception as e:
        print(f"Error getting embedding: {e}")
        return [0] * 768  # Return zero vector on error (mpnet-base-v2 has 768 dimensions)

async def process_chunk(chunk: str, chunk_number: int, url: str) -> ProcessedChunk:
    """Process a single chunk of text."""
    # Get title and summary with retry logic
    extracted = await get_title_and_summary_with_retry(chunk, url)
    
    # Get embedding
    embedding = get_embedding(chunk)
    
    # Create metadata
    metadata = {
        "source": "stanford_medical_facilities",
        "chunk_size": len(chunk),
        "crawled_at": datetime.now(timezone.utc).isoformat(),
        "url_path": urlparse(url).path
    }
    
    return ProcessedChunk(
        url=url,
        chunk_number=chunk_number,
        title=extracted['title'],
        summary=extracted['summary'],
        content=chunk,  # Store the original chunk content
        metadata=metadata,
        embedding=embedding
    )

async def insert_chunk(chunk: ProcessedChunk):
    """Insert a processed chunk into Supabase."""
    try:
        data = {
            "url": chunk.url,
            "chunk_number": chunk.chunk_number,
            "title": chunk.title,
            "summary": chunk.summary,
            "content": chunk.content,
            "metadata": chunk.metadata,
            "embedding": chunk.embedding
        }
        
        result = supabase.table("site_pages").insert(data).execute()
        print(f"Inserted chunk {chunk.chunk_number} for {chunk.url}")
        return result
    except Exception as e:
        print(f"Error inserting chunk: {e}")
        return None

async def process_and_store_document(url: str, markdown: str):
    """Process a document and store its chunks with rate limiting."""
    # Split into chunks
    chunks = chunk_text(markdown)
    
    print(f"Processing {len(chunks)} chunks for {url}")
    
    # Process chunks with rate limiting
    for i, chunk in enumerate(chunks):
        try:
            # Process chunk
            processed_chunk = await process_chunk(chunk, i, url)
            
            # Insert chunk
            await insert_chunk(processed_chunk)
            
            # Add delay between chunks to avoid overwhelming the API
            if i < len(chunks) - 1:  # Don't delay after the last chunk
                await asyncio.sleep(1)  # 1 second delay between chunks
                
        except Exception as e:
            print(f"Error processing chunk {i} for {url}: {e}")
            continue

async def crawl_parallel(urls: List[str], max_concurrent: int = 2):
    """Crawl multiple URLs in parallel with a concurrency limit and rate limiting."""
    browser_config = BrowserConfig(
        headless=True,
        verbose=False,
        extra_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"],
    )
    crawl_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)

    # Create the crawler instance
    crawler = AsyncWebCrawler(config=browser_config)
    await crawler.start()

    try:
        # Create a semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_url(url: str):
            async with semaphore:
                try:
                    result = await crawler.arun(
                        url=url,
                        config=crawl_config,
                        session_id="session1"
                    )
                    if result.success:
                        print(f"Successfully crawled: {url}")
                        await process_and_store_document(url, result.markdown_v2.raw_markdown)
                    else:
                        print(f"Failed: {url} - Error: {result.error_message}")
                except Exception as e:
                    print(f"Error crawling {url}: {e}")
                
                # Add delay between URLs to avoid overwhelming the system
                await asyncio.sleep(2)
        
        # Process URLs sequentially to avoid overwhelming APIs
        for url in urls:
            await process_url(url)
            
    finally:
        await crawler.close()

def get_stanford_medical_facilities_urls() -> List[str]:
    """Get URLs for Stanford Medical Facilities."""
    urls = [
        "https://med.stanford.edu/medfacilities/emergency-management.html",
        "https://med.stanford.edu/medfacilities/safety-guidelines-resources.html", 
        "https://med.stanford.edu/medfacilities/about-us.html",
        "https://med.stanford.edu/medfacilities/projects.html",
        "https://med.stanford.edu/medfacilities/space-planning-assets.html",
        "https://med.stanford.edu/medfacilities/locations.html"
    ]
    return urls

async def main():
    # Get URLs for Stanford Medical Facilities
    urls = get_stanford_medical_facilities_urls()
    if not urls:
        print("No URLs found to crawl")
        return
    
    print(f"Found {len(urls)} URLs to crawl")
    print("Starting crawl with rate limiting and retry logic...")
    await crawl_parallel(urls)
    print("Crawl completed!")

if __name__ == "__main__":
    asyncio.run(main()) 