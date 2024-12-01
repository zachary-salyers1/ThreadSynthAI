from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from typing import Dict, TypedDict, Annotated
import os
import mimetypes
from config import get_config

def process_document(file_path: str) -> str:
    """Process the uploaded document and extract its content."""
    # Get current configuration
    config = get_config()
    
    # Detect file type using mimetypes
    file_type, _ = mimetypes.guess_type(file_path)
    
    if file_type == 'text/plain':
        loader = TextLoader(file_path)
    elif file_type == 'application/pdf':
        loader = PyPDFLoader(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")
        
    documents = loader.load()
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap
    )
    
    splits = text_splitter.split_documents(documents)
    return "\n".join([doc.page_content for doc in splits[:config.max_chunks]])

class ThreadState(TypedDict):
    content: str
    thread_parts: list
    complete: bool

def create_thread(content: str) -> Dict:
    """Create a thread from the document content using LangChain."""
    # Get current configuration
    config = get_config()
    
    # Split content into smaller chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.chunk_size * 2,  # Larger chunks for thread creation
        chunk_overlap=config.chunk_overlap
    )
    chunks = text_splitter.split_text(content)
    
    # Initialize LLM with configuration
    llm = ChatOpenAI(
        model_name=config.model_name,
        temperature=config.temperature,
        max_tokens=config.max_tokens
    )
    output_parser = StrOutputParser()
    
    # Create title from first chunk using configured prompt
    title_prompt = PromptTemplate.from_template(config.prompts["title"])
    title_chain = title_prompt | llm | output_parser
    title = title_chain.invoke({"content": chunks[0]})
    
    # Combine chunks into one content piece (limited to preserve context)
    combined_content = " ".join(chunks[:3])
    
    # Generate thread post using configured prompt
    post_prompt = PromptTemplate.from_template(config.prompts["thread"])
    post_chain = post_prompt | llm | output_parser
    post = post_chain.invoke({"content": combined_content})
    posts = [{"content": post}]
    
    return {
        "title": title,
        "posts": posts
    }
