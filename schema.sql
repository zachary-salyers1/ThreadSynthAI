-- Create a table for threads
CREATE TABLE threads (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) NOT NULL,
    title TEXT NOT NULL,
    content JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Create an index on user_id for faster queries
CREATE INDEX idx_threads_user_id ON threads(user_id);

-- Create a table for user configurations
CREATE TABLE user_configs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) NOT NULL UNIQUE,
    model_name TEXT NOT NULL DEFAULT 'gpt-3.5-turbo',
    temperature FLOAT NOT NULL DEFAULT 0.7,
    max_tokens INTEGER NOT NULL DEFAULT 1000,
    chunk_size INTEGER NOT NULL DEFAULT 2000,
    chunk_overlap INTEGER NOT NULL DEFAULT 100,
    max_chunks INTEGER NOT NULL DEFAULT 10,
    prompts JSONB NOT NULL DEFAULT '{"title": "Summarize the following content into a thread title that would grab attention on X (formerly Twitter): {content}", "thread": "Create a single engaging thread post from this content. Format it as a thread with line breaks between key points, use emojis where appropriate, and make it conversational: {content}"}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Create an index on user_id for faster queries
CREATE INDEX idx_user_configs_user_id ON user_configs(user_id);

-- Enable Row Level Security (RLS)
ALTER TABLE threads ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_configs ENABLE ROW LEVEL SECURITY;

-- Create policies for thread access
-- Allow users to view only their own threads
CREATE POLICY "Users can view their own threads"
    ON threads FOR SELECT
    USING (auth.uid() = user_id);

-- Allow users to insert their own threads
CREATE POLICY "Users can create threads"
    ON threads FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Allow users to update their own threads
CREATE POLICY "Users can update their own threads"
    ON threads FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Allow users to delete their own threads
CREATE POLICY "Users can delete their own threads"
    ON threads FOR DELETE
    USING (auth.uid() = user_id);

-- Create policies for user configurations
-- Allow users to view only their own config
CREATE POLICY "Users can view their own config"
    ON user_configs FOR SELECT
    USING (auth.uid() = user_id);

-- Allow users to insert their own config
CREATE POLICY "Users can create their own config"
    ON user_configs FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Allow users to update their own config
CREATE POLICY "Users can update their own config"
    ON user_configs FOR UPDATE
    USING (auth.uid() = user_id);

-- Create a function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = timezone('utc'::text, now());
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers to automatically update updated_at timestamp
CREATE TRIGGER update_threads_updated_at
    BEFORE UPDATE ON threads
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_configs_updated_at
    BEFORE UPDATE ON user_configs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column(); 