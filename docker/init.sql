CREATE DATABASE IF NOT EXISTS rag_flow;
USE rag_flow;

ALTER TABLE user_knowledgebase_permission 
ADD COLUMN IF NOT EXISTS nickname VARCHAR(100) NOT NULL;

ALTER TABLE user_knowledgebase_permission 
ADD COLUMN IF NOT EXISTS email VARCHAR(255) NOT NULL;