import os
import json
import asyncio
from typing import List, Dict, Any
from dotenv import load_dotenv
import google.generativeai as genai
from sentence_transformers import SentenceTransformer
from supabase import Client

load_dotenv()

# Initialize Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-2.0-flash')

# Initialize sentence transformer for embeddings
embedding_model = SentenceTransformer('all-mpnet-base-v2')

# Initialize Supabase
supabase: Client = Client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

def get_embedding(text: str) -> List[float]:
    """Get embedding vector using all-mpnet-base-v2."""
    try:
        embedding = embedding_model.encode(text)
        return embedding.tolist()
    except Exception as e:
        print(f"Error getting embedding: {e}")
        return [0] * 768

async def retrieve_relevant_documentation(user_query: str) -> tuple[str, List[Dict]]:
    """Retrieve relevant documentation chunks based on the query with RAG."""
    try:
        # Get the embedding for the query
        query_embedding = get_embedding(user_query)
        
        # Query Supabase for relevant documents
        result = supabase.rpc(
            'match_site_pages',
            {
                'query_embedding': query_embedding,
                'match_count': 8,  # Increased to get more context
                'filter': {'source': 'stanford_medical_facilities'}
            }
        ).execute()
        
        if not result.data:
            return "No relevant documentation found.", []
            
        # Format the results and collect URLs
        formatted_chunks = []
        urls = []
        for doc in result.data:
            chunk_text = f"""
# {doc['title']}

{doc['content']}
"""
            formatted_chunks.append(chunk_text)
            if doc['url'] not in urls:
                urls.append(doc['url'])
            
        # Join all chunks with a separator
        return "\n\n---\n\n".join(formatted_chunks), urls
        
    except Exception as e:
        print(f"Error retrieving documentation: {e}")
        return f"Error retrieving documentation: {str(e)}", []

async def list_documentation_pages() -> List[str]:
    """Retrieve a list of all available Stanford Medical Facilities documentation pages."""
    try:
        # Query Supabase for unique URLs where source is stanford_medical_facilities
        result = supabase.from_('site_pages') \
            .select('url') \
            .eq('metadata->>source', 'stanford_medical_facilities') \
            .execute()
        
        if not result.data:
            return []
            
        # Extract unique URLs
        urls = sorted(set(doc['url'] for doc in result.data))
        return urls
        
    except Exception as e:
        print(f"Error retrieving documentation pages: {e}")
        return []

async def get_page_content(url: str) -> str:
    """Retrieve the full content of a specific documentation page by combining all its chunks."""
    try:
        # Query Supabase for all chunks of this URL, ordered by chunk_number
        result = supabase.from_('site_pages') \
            .select('title, content, chunk_number') \
            .eq('url', url) \
            .eq('metadata->>source', 'stanford_medical_facilities') \
            .order('chunk_number') \
            .execute()
        
        if not result.data:
            return f"No content found for URL: {url}"
            
        # Format the page with its title and all chunks
        page_title = result.data[0]['title'].split(' - ')[0]  # Get the main title
        formatted_content = [f"# {page_title}\n"]
        
        # Add each chunk's content
        for chunk in result.data:
            formatted_content.append(chunk['content'])
            
        # Join everything together
        return "\n\n".join(formatted_content)
        
    except Exception as e:
        print(f"Error retrieving page content: {e}")
        return f"Error retrieving page content: {str(e)}"

async def generate_response(user_query: str) -> str:
    """Generate a response using Gemini with RAG."""
    try:
        # First, retrieve relevant documentation
        relevant_docs, source_urls = await retrieve_relevant_documentation(user_query)
        
        # Get list of available pages
        available_pages = await list_documentation_pages()
        
        # Create the prompt for Gemini
        system_prompt = """You are a helpful and knowledgeable assistant for Stanford Medical Facilities. You have access to comprehensive documentation about Stanford's medical facilities, including emergency management, safety guidelines, facility information, projects, space planning, and locations.

Your role is to:
1. Provide helpful, conversational responses based on the available documentation
2. Be specific and detailed when possible
3. If you find relevant information, mention the source URLs
4. If you don't have enough information, suggest where users can find more details
5. Always be friendly and professional
6. Format your response properly

Available documentation pages: {available_pages}

Relevant documentation chunks:
{relevant_docs}

Source URLs: {source_urls}

User question: {user_query}

Please provide a helpful, conversational response. If you reference information from the documentation, mention the relevant URLs. If you don't have complete information, suggest checking the specific pages for more details."""
        
        # Generate response using Gemini
        response = model.generate_content(system_prompt.format(
            available_pages=available_pages,
            relevant_docs=relevant_docs,
            source_urls=source_urls,
            user_query=user_query
        ))
        
        return response.text
        
    except Exception as e:
        print(f"Error generating response: {e}")
        return f"I apologize, but I encountered an error: {str(e)}"

# For compatibility with the existing Streamlit UI
class StanfordMedicalFacilitiesDeps:
    def __init__(self):
        self.supabase = supabase
        self.embedding_model = embedding_model

class StreamResult:
    """Result class that provides streaming functionality."""
    
    def __init__(self, response_text: str):
        self.response_text = response_text
    
    async def stream_text(self, delta=True):
        """Stream the response text character by character."""
        for char in self.response_text:
            yield char
            await asyncio.sleep(0.01)  # Small delay for streaming effect
    
    def new_messages(self):
        return []

class StanfordMedicalFacilitiesExpert:
    """Simple expert class that mimics the pydantic-ai Agent interface."""
    
    def __init__(self):
        self.deps = StanfordMedicalFacilitiesDeps()
    
    async def run_stream(self, user_input: str, deps=None, message_history=None):
        """Run the expert with streaming response."""
        # Generate response
        response_text = await generate_response(user_input)
        
        return StreamResult(response_text)

# Create the expert instance
stanford_medical_facilities_expert = StanfordMedicalFacilitiesExpert() 