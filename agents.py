from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from typing import Dict, TypedDict, Annotated
import os
import mimetypes

def process_document(file_path: str) -> str:
    """Process the uploaded document and extract its content."""
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
        chunk_size=2000,  # Smaller chunks for initial processing
        chunk_overlap=100
    )
    
    splits = text_splitter.split_documents(documents)
    # Take only first N chunks to avoid overwhelming the model
    max_chunks = 10
    return "\n".join([doc.page_content for doc in splits[:max_chunks]])

class ThreadState(TypedDict):
    content: str
    thread_parts: list
    complete: bool

def create_thread(content: str) -> Dict:
    """Create a thread from the document content using LangChain."""
    # Split content into smaller chunks (max ~4000 tokens each)
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=4000,
        chunk_overlap=200
    )
    chunks = text_splitter.split_text(content)
    
    # Initialize LLM
    llm = ChatOpenAI(temperature=0.7)
    output_parser = StrOutputParser()
    
    # Create title from first chunk only
    title_prompt = PromptTemplate.from_template(
        "Summarize the following content into a thread title that would grab attention on social media: {content}"
    )
    title_chain = title_prompt | llm | output_parser
    title = title_chain.invoke({"content": chunks[0]})
    
    # Process each chunk into 1-2 posts
    posts = []
    post_prompt = PromptTemplate.from_template(
        "Create 1-2 engaging thread posts from this content. Make them conversational and informative: {content}"
    )
    post_chain = post_prompt | llm | output_parser
    
    for chunk in chunks[:5]:  # Limit to 5 chunks to keep thread reasonable
        if chunk.strip():
            post = post_chain.invoke({"content": chunk})
            posts.append({"content": post})
    
    return {
        "title": title,
        "posts": posts
    }
