from langchain_community.document_loaders import UnstructuredFileLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.chat_models import ChatOpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langgraph.graph import StateGraph
from typing import Dict, TypedDict
import asyncio

def process_document(file_path: str) -> str:
    """Process the uploaded document and extract its content."""
    loader = UnstructuredFileLoader(file_path)
    documents = loader.load()
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    
    splits = text_splitter.split_documents(documents)
    return "\n".join([doc.page_content for doc in splits])

class AgentState(TypedDict):
    content: str
    thread_parts: list
    complete: bool

def create_thread(content: str) -> Dict:
    """Create a thread from the document content using LangChain and LangGraph."""
    
    # Initialize LLM
    llm = ChatOpenAI(temperature=0.7)
    
    # Create prompts for different agents
    summarizer_prompt = PromptTemplate(
        template="Summarize the following content into a thread title: {content}",
        input_variables=["content"]
    )
    
    thread_creator_prompt = PromptTemplate(
        template="Create an engaging thread post from this content. Make it conversational and informative: {content}",
        input_variables=["content"]
    )
    
    # Create chains
    title_chain = LLMChain(llm=llm, prompt=summarizer_prompt)
    post_chain = LLMChain(llm=llm, prompt=thread_creator_prompt)
    
    # Define agent functions
    def generate_title(state: AgentState) -> AgentState:
        title = title_chain.run(content=state['content'])
        state['thread_parts'].append({"type": "title", "content": title})
        return state
    
    def generate_posts(state: AgentState) -> AgentState:
        chunks = state['content'].split('\n\n')
        for chunk in chunks[:5]:  # Limit to 5 posts
            post = post_chain.run(content=chunk)
            state['thread_parts'].append({"type": "post", "content": post})
        state['complete'] = True
        return state
    
    # Create workflow graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("title_generator", generate_title)
    workflow.add_node("post_generator", generate_posts)
    
    # Add edges
    workflow.add_edge("title_generator", "post_generator")
    
    # Set entry and exit points
    workflow.set_entry_point("title_generator")
    workflow.set_finish_point("post_generator")
    
    # Execute workflow
    initial_state = {"content": content, "thread_parts": [], "complete": False}
    final_state = workflow.run(initial_state)
    
    # Process results
    thread_data = {
        "title": "",
        "posts": []
    }
    
    for part in final_state['thread_parts']:
        if part['type'] == 'title':
            thread_data['title'] = part['content']
        else:
            thread_data['posts'].append({"content": part['content']})
    
    return thread_data
