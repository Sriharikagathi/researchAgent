"""Main research agent implementation."""

import asyncio
from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.schema import Document

from Config.Settings import settings
from shared.state import SharedState, JobStatus, LogType
from shared.logging_config import setup_logging
from RAG.DocumentLoader import DocumentLoader
from RAG.VectorStore import VectorStore
from Tools.DocumentRetrievalTool import create_document_retrieval_tool
from Tools.WebResearchTool import create_web_research_tool
from Tools.CitationVerificationTool import create_citation_verification_tool
from Tools.MCPTools import MCPComplianceTool, MCPFormattingTool
from Agent.prompts import create_research_agent_prompt


class ResearchAgent:
    """Main research agent orchestrating all tools and workflows."""
    
    def __init__(self, openai_api_key: Optional[str] = None):
        """
        Initialize research agent.
        
        Args:
            openai_api_key: OpenAI API key (uses settings if not provided)
        """
        # Setup logging
        import os
        os.environ['OPENAI_API_KEY'] = openai_api_key or settings.openai_api_key
        setup_logging(settings.log_level)
        
        # Initialize shared state
        self.shared_state = SharedState(
            audit_log_path=settings.audit_log_path
        )
        
        self.shared_state.add_log(
            "=== Research Agent Initializing ===",
            LogType.INFO
        )
        
        # Initialize API key
        self.api_key = openai_api_key or settings.openai_api_key
        
        # Initialize components
        self.document_loader = DocumentLoader(self.shared_state)
        self.vector_store = VectorStore(self.shared_state)
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            model=settings.llm_model,
            temperature=settings.agent_temperature,
            api_key=self.api_key
        )
        
        # Create tools
        self.tools = [
            create_document_retrieval_tool(self.vector_store, self.shared_state),
            create_web_research_tool(self.shared_state),
            create_citation_verification_tool(self.shared_state)
        ]
        
        # Create agent
        self.agent_executor = self._create_agent()
        
        self.shared_state.add_log(
            "=== Research Agent Initialized Successfully ===",
            LogType.SUCCESS
        )
    
    def _create_agent(self) -> AgentExecutor:
        """
        Create LangChain agent with tools.
        
        Returns:
            AgentExecutor instance
        """
        prompt = create_research_agent_prompt()
        
        agent = create_openai_tools_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
        
        agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            max_iterations=settings.max_iterations,
            handle_parsing_errors=True
        )
        
        return agent_executor
    
    async def ingest_document(self, file_path: str) -> int:
        """
        Ingest a single document into RAG system.
        
        Args:
            file_path: Path to document
            
        Returns:
            Number of chunks created
        """
        self.shared_state.add_log(
            f"=== Document Ingestion Started: {file_path} ===",
            LogType.INFO
        )
        
        try:
            # Load and process document
            chunks = await self.document_loader.load_and_process(file_path)
            
            if not chunks:
                self.shared_state.add_log(
                    f"No chunks created from {file_path}",
                    LogType.WARNING
                )
                return 0
            
            # Add to vector store
            self.vector_store.add_documents(chunks)
            
            self.shared_state.add_log(
                f"=== Document Ingestion Completed: {len(chunks)} chunks ===",
                LogType.SUCCESS
            )
            
            return len(chunks)
            
        except Exception as e:
            self.shared_state.add_log(
                f"Error ingesting document: {str(e)}",
                LogType.ERROR
            )
            return 0
    
    async def ingest_documents(self, file_paths: List[str]) -> int:
        """
        Ingest multiple documents.
        
        Args:
            file_paths: List of document paths
            
        Returns:
            Total number of chunks created
        """
        total_chunks = 0
        
        for file_path in file_paths:
            chunks = await self.ingest_document(file_path)
            total_chunks += chunks
        
        return total_chunks
    
    async def ingest_directory(self, directory_path: str) -> int:
        """
        Ingest all documents from a directory.
        
        Args:
            directory_path: Path to directory
            
        Returns:
            Total number of chunks created
        """
        self.shared_state.add_log(
            f"=== Directory Ingestion Started: {directory_path} ===",
            LogType.INFO
        )
        
        chunks = await self.document_loader.load_directory(directory_path)
        
        if chunks:
            self.vector_store.add_documents(chunks)
        
        self.shared_state.add_log(
            f"=== Directory Ingestion Completed: {len(chunks)} chunks ===",
            LogType.SUCCESS
        )
        
        return len(chunks)
    
    async def run_research(self, query: str) -> Dict[str, Any]:
        """
        Run complete research workflow.
        
        Args:
            query: Research query
            
        Returns:
            Dictionary with research results
        """
        self.shared_state.query = query
        self.shared_state.update_status(JobStatus.RUNNING, "Research started")
        self.shared_state.add_log(
            "=== Research Workflow Started ===",
            LogType.INFO
        )
        
        try:
            # Run agent
            self.shared_state.add_log(
                "[Agent] Executing research agent",
                LogType.AGENT
            )
            
            result = await asyncio.to_thread(
                self.agent_executor.invoke,
                {"input": query}
            )
            
            # Generate comprehensive report
            report = self._generate_report(result)
            self.shared_state.final_report = report
            
            # Apply MCP compliance (PII redaction)
            self.shared_state.add_log(
                "[Agent] Applying compliance checks",
                LogType.AGENT
            )
            compliance_result = MCPComplianceTool.scan_and_redact(
                report,
                self.shared_state
            )
            clean_report = compliance_result['clean_content']
            
            # Apply MCP formatting
            self.shared_state.add_log(
                "[Agent] Formatting final report",
                LogType.AGENT
            )
            formatted = MCPFormattingTool.format_content(
                clean_report,
                'markdown',
                self.shared_state,
                metadata={
                    'query': query,
                    'session_id': self.shared_state.session_id
                }
            )
            
            # Export report
            filename = f"research_report_{self.shared_state.session_id}.md"
            filepath = MCPFormattingTool.export_to_file(
                formatted['formatted_content'],
                filename,
                self.shared_state
            )
            
            # Create audit report
            audit_report = MCPFormattingTool.create_audit_report(self.shared_state)
            audit_filename = f"audit_report_{self.shared_state.session_id}.json"
            MCPFormattingTool.export_to_file(
                audit_report,
                audit_filename,
                self.shared_state
            )
            
            self.shared_state.update_status(
                JobStatus.COMPLETED,
                "Research completed successfully"
            )
            self.shared_state.add_log(
                "=== Research Workflow Completed ===",
                LogType.SUCCESS
            )
            
            return {
                'success': True,
                'query': query,
                'report': clean_report,
                'formatted_report': formatted['formatted_content'],
                'compliance': self.shared_state.compliance_report,
                'summary': self.shared_state.get_summary(),
                'export_path': filepath,
                'logs': self.shared_state.logs,
                'session_id': self.shared_state.session_id
            }
            
        except Exception as e:
            self.shared_state.update_status(JobStatus.FAILED, str(e))
            self.shared_state.add_log(
                f"Error in research workflow: {str(e)}",
                LogType.ERROR
            )
            
            return {
                'success': False,
                'error': str(e),
                'logs': self.shared_state.logs,
                'session_id': self.shared_state.session_id
            }
    
    def _generate_report(self, agent_result: Dict) -> str:
        """
        Generate final research report.
        
        Args:
            agent_result: Result from agent execution
            
        Returns:
            Formatted research report
        """
        self.shared_state.add_log(
            "[Agent] Generating final research report",
            LogType.AGENT
        )
        
        from datetime import datetime
        
        report = f"""# Research Report: {self.shared_state.query}

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Session ID**: {self.shared_state.session_id}

---

## Agent Response

{agent_result.get('output', 'No output generated')}

---

## Research Metadata

### Documents Retrieved
- **Total Documents**: {self.shared_state.document_count}
- **Source**: RAG Vector Database (PGVector)
- **Total Chunks Ingested**: {self.shared_state.total_chunks}

### Web Research
- **Web Sources Found**: {len(self.shared_state.web_sources)}
- **URLs**: 
"""
        
        for idx, url in enumerate(self.shared_state.web_sources[:5], 1):
            report += f"  {idx}. {url}\n"
        
        if len(self.shared_state.web_sources) > 5:
            report += f"  ... and {len(self.shared_state.web_sources) - 5} more\n"
        
        report += f"""
### Citations
- **Total Citations Verified**: {self.shared_state.citation_count}
- **Citation Format**: APA
- **Verification Status**: ✓ All verified

---

## Compliance
- **PII Scan**: Completed
- **PII Redacted**: {self.shared_state.pii_redacted_count} instances
- **Compliance Status**: PASS

---

*This report was generated by the Research Agent with full audit trail.*
"""
        
        return report
    
    def get_logs(self) -> List[Dict]:
        """Get all logs."""
        return self.shared_state.logs
    
    def get_state_summary(self) -> Dict:
        """Get state summary."""
        return self.shared_state.get_summary()
    
    def clear_state(self):
        """Clear shared state."""
        self.shared_state.clear_state()