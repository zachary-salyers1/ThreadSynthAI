from supabase import create_client
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_ANON_KEY")
)

async def sign_up(email: str, password: str):
    """Register a new user with email and password."""
    try:
        response = supabase.auth.sign_up({
            "email": email,
            "password": password
        })
        if response.user:
            return response.user, None
        return None, "Registration failed"
    except Exception as e:
        return None, str(e)

async def sign_in(email: str, password: str):
    """Sign in an existing user with email and password."""
    try:
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        # Check if we have both user and session
        if response.user and response.session:
            return {
                'user': response.user,
                'session': response.session
            }, None
        return None, "Login failed: Invalid credentials"
    except Exception as e:
        print(f"Login error: {str(e)}")  # Debug logging
        return None, str(e)

async def sign_out(session):
    """Sign out the current user."""
    try:
        supabase.auth.sign_out()
        return True, None
    except Exception as e:
        return False, str(e)

async def get_user(access_token: str):
    """Get user details from access token."""
    try:
        response = supabase.auth.get_user(access_token)
        if response.user:
            return response.user, None
        return None, "User not found"
    except Exception as e:
        return None, str(e)

async def save_thread(user_id: str, title: str, content: list):
    """Save a thread to Supabase database."""
    try:
        response = supabase.table('threads').insert({
            'user_id': user_id,
            'title': title,
            'content': content,
        }).execute()
        return response.data[0] if response.data else None, None
    except Exception as e:
        return None, str(e)

async def get_user_threads(user_id: str):
    """Get all threads for a user."""
    try:
        response = supabase.table('threads').select('*').eq('user_id', user_id).execute()
        return response.data, None
    except Exception as e:
        return None, str(e)

async def get_thread(thread_id: str):
    """Get a specific thread by ID."""
    try:
        response = supabase.table('threads').select('*').eq('id', thread_id).single().execute()
        return response.data, None
    except Exception as e:
        return None, str(e)

async def delete_thread(thread_id: str, user_id: str):
    """Delete a thread."""
    try:
        response = supabase.table('threads').delete().eq('id', thread_id).eq('user_id', user_id).execute()
        return True, None
    except Exception as e:
        return False, str(e)

async def get_user_config(user_id: str):
    """Get user configuration."""
    try:
        print(f"Fetching config for user {user_id}")  # Debug log
        
        # First try to get existing config
        try:
            response = supabase.table('user_configs').select('*').eq('user_id', user_id).execute()
            if response and response.data and len(response.data) > 0:
                return response.data[0], None
        except Exception as e:
            print(f"Error fetching config: {str(e)}")  # Debug log
        
        print("No existing config found, creating default")  # Debug log
        # If no config exists, create default config
        default_config = {
            'user_id': user_id,
            'model_name': 'gpt-3.5-turbo',
            'temperature': 0.7,
            'max_tokens': 1000,
            'chunk_size': 2000,
            'chunk_overlap': 100,
            'max_chunks': 10,
            'prompts': {
                'title': 'Summarize the following content into a thread title that would grab attention on X (formerly Twitter): {content}',
                'thread': 'Create a single engaging thread post from this content. Format it as a thread with line breaks between key points, use emojis where appropriate, and make it conversational: {content}'
            }
        }
        
        insert_response = supabase.table('user_configs').insert(default_config).execute()
        print(f"Insert response: {insert_response}")  # Debug log
        
        if insert_response and insert_response.data and len(insert_response.data) > 0:
            return insert_response.data[0], None
        return None, "Failed to create default configuration"
    except Exception as e:
        print(f"Error in get_user_config: {str(e)}")  # Debug log
        return None, str(e)

async def update_user_config(user_id: str, config_data: dict):
    """Update user configuration."""
    try:
        print(f"Updating config for user {user_id}")  # Debug log
        print(f"Config data: {config_data}")  # Debug log
        
        # Ensure user_id is included in the update
        config_data['user_id'] = user_id
        
        # First try to get existing config
        try:
            existing_response = supabase.table('user_configs').select('*').eq('user_id', user_id).execute()
            if existing_response and existing_response.data and len(existing_response.data) > 0:
                # Update existing config
                response = supabase.table('user_configs').update(config_data).eq('user_id', user_id).execute()
            else:
                # Insert new config
                response = supabase.table('user_configs').insert(config_data).execute()
            
            print(f"Update/Insert response: {response}")  # Debug log
            
            if response and response.data and len(response.data) > 0:
                return response.data[0], None
            return None, "Failed to update configuration"
        except Exception as e:
            print(f"Database operation failed: {str(e)}")  # Debug log
            return None, str(e)
    except Exception as e:
        print(f"Error in update_user_config: {str(e)}")  # Debug log
        return None, str(e) 