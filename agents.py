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
        chunk_size=1000,
        chunk_overlap=200
    )
    
    splits = text_splitter.split_documents(documents)
    return "\n".join([doc.page_content for doc in splits])

class ThreadState(TypedDict):
    content: str
    thread_parts: list
    complete: bool

def create_thread(content: str) -> Dict:
    """Create a thread from the document content using LangChain."""
    
    # Initialize LLM
    llm = ChatOpenAI(temperature=0.7)
    output_parser = StrOutputParser()
    
    # Create prompts for different parts
    title_prompt = PromptTemplate.from_template(
        "Summarize the following content into a thread title that would grab attention on social media: {content}"
    )
    
    post_prompt = PromptTemplate.from_template(
        "Create an engaging thread post from this content. Make it conversational and informative, "
        "using a style similar to popular social media threads: {content}"
    )
    
    # Create chains
    title_chain = title_prompt | llm | output_parser
    post_chain = post_prompt | llm | output_parser
    
    # Generate title
    title = title_chain.invoke({"content": content[:1000]})  # Use first 1000 chars for title
    
    # Generate posts
    posts = []
    chunks = content.split('\n\n')
    for chunk in chunks[:5]:  # Limit to 5 posts
        if chunk.strip():
            post = post_chain.invoke({"content": chunk})
            posts.append({"content": post})
    
    return {
        "title": title,
        "posts": posts
    }
