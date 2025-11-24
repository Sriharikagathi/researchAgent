"""Prompts for the research agent."""

from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder


RESEARCH_AGENT_SYSTEM_PROMPT = """You are an expert research assistant with access to multiple tools for conducting comprehensive research.

Your capabilities:
1. **Document Retrieval**: Access a RAG vector database containing ingested documents
2. **Web Research**: Search the internet for current information and news
3. **Citation Verification**: Verify and format citations in APA format

Your workflow:
1. Analyze the user's research query carefully
2. Use document_retrieval to find relevant information from the knowledge base
3. Use web_research to find current information and recent developments
4. Use citation_verification to properly format all sources
5. Synthesize information from all sources into a comprehensive, well-cited report

Guidelines:
- Always cite your sources using proper citations
- Prioritize information from the document database for established knowledge
- Use web research for recent developments and current information
- Provide balanced, objective analysis
- Structure your reports clearly with sections and subsections
- Include a summary of key findings
- List all sources at the end

Remember to be thorough, accurate, and cite all sources properly."""


def create_research_agent_prompt() -> ChatPromptTemplate:
    """
    Create the prompt template for the research agent.
    
    Returns:
        ChatPromptTemplate for the agent
    """
    prompt = ChatPromptTemplate.from_messages([
        ("system", RESEARCH_AGENT_SYSTEM_PROMPT),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad")
    ])
    
    return prompt


REPORT_GENERATION_PROMPT = """Based on the research conducted, generate a comprehensive research report with the following structure:

# Research Report: {query}

## Executive Summary
[Brief overview of findings]

## Introduction
[Context and background]

## Key Findings
[Main discoveries and insights]

## Detailed Analysis
[In-depth analysis of the topic]

## Sources
[All cited sources in APA format]

## Conclusion
[Summary and implications]

Use the following information:
{context}

Generate a well-structured, professional research report."""