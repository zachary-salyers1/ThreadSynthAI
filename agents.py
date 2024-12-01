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
    
    # Combine chunks into one content piece (limited to preserve context)
    combined_content = " ".join(chunks[:3])  # Limit to first 3 chunks to stay within token limits
    
    # Generate single thread post
    post_prompt = PromptTemplate.from_template(
        "Create a single engaging thread post from this content. Format it as a thread with line breaks between key points, use emojis where appropriate, and make it conversational: {content}"
    )
    post_chain = post_prompt | llm | output_parser
    post = post_chain.invoke({"content": combined_content})
    posts = [{"content": post}]
    
    return {
        "title": title,
        "posts": posts
    }
