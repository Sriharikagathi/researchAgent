"""MCP (Model Context Protocol) tools for compliance and formatting."""

import re
import json
import os
from datetime import datetime
from typing import Dict, Any, List
from shared.state import SharedState, LogType
from Config.Settings import settings


class MCPComplianceTool:
    """MCP-based compliance and PII redaction tool."""
    
    # PII detection patterns
    PII_PATTERNS = {
        'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        'phone': r'\b(?:\+?1[-.]?)?\(?\d{3}\)?[-.]?\d{3}[-.]?\d{4}\b',
        'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
        'credit_card': r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
        'ip_address': r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
        'passport': r'\b[A-Z]{1,2}\d{6,9}\b',
        'driver_license': r'\b[A-Z]\d{7,8}\b'
    }
    
    @staticmethod
    def scan_and_redact(content: str, shared_state: SharedState) -> Dict[str, Any]:
        """
        Scan content for PII and redact sensitive information.
        
        Args:
            content: Content to scan
            shared_state: Shared state instance
            
        Returns:
            Dictionary with clean content and compliance report
        """
        shared_state.add_log(
            "[MCP Compliance] Starting PII scan and redaction",
            LogType.MCP
        )
        
        pii_found = []
        redacted_content = content
        redaction_count = 0
        
        for pii_type, pattern in MCPComplianceTool.PII_PATTERNS.items():
            matches = re.findall(pattern, content, re.IGNORECASE)
            
            if matches:
                unique_matches = list(set(matches))
                shared_state.add_log(
                    f"[MCP Compliance] Found {len(unique_matches)} {pii_type} instances",
                    LogType.MCP
                )
                
                for match in unique_matches:
                    pii_found.append({
                        'type': pii_type,
                        'value_hash': hash(match),  # Store hash instead of actual value
                        'redacted': True,
                        'timestamp': datetime.now().isoformat()
                    })
                
                # Redact with type-specific placeholder
                redacted_content = re.sub(
                    pattern,
                    f'[{pii_type.upper()}_REDACTED]',
                    redacted_content,
                    flags=re.IGNORECASE
                )
                redaction_count += len(unique_matches)
        
        # Generate compliance report
        compliance_report = {
            'scan_timestamp': datetime.now().isoformat(),
            'pii_count': len(pii_found),
            'redaction_count': redaction_count,
            'pii_types': list(set([p['type'] for p in pii_found])),
            'redacted': True if pii_found else False,
            'compliance_status': 'PASS',
            'details': pii_found
        }
        
        # Update shared state
        shared_state.pii_found = pii_found
        shared_state.pii_redacted_count = redaction_count
        shared_state.compliance_report = compliance_report
        
        shared_state.add_log(
            f"[MCP Compliance] Completed: {redaction_count} PII instances redacted",
            LogType.SUCCESS,
            metadata=compliance_report
        )
        
        return {
            'clean_content': redacted_content,
            'compliance_report': compliance_report
        }
    
    @staticmethod
    def validate_compliance(content: str, shared_state: SharedState) -> bool:
        """
        Validate that content is compliant (no PII).
        
        Args:
            content: Content to validate
            shared_state: Shared state instance
            
        Returns:
            True if compliant, False otherwise
        """
        shared_state.add_log(
            "[MCP Compliance] Validating content compliance",
            LogType.MCP
        )
        
        for pii_type, pattern in MCPComplianceTool.PII_PATTERNS.items():
            if re.search(pattern, content, re.IGNORECASE):
                shared_state.add_log(
                    f"[MCP Compliance] Found unredacted {pii_type}",
                    LogType.WARNING
                )
                return False
        
        shared_state.add_log(
            "[MCP Compliance] Content is compliant",
            LogType.SUCCESS
        )
        
        return True


class MCPFormattingTool:
    """MCP-based formatting and export tool."""
    
    SUPPORTED_FORMATS = ['markdown', 'html', 'json', 'text', 'pdf']
    
    @staticmethod
    def format_content(
        content: str,
        format_type: str,
        shared_state: SharedState,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Format content in specified format.
        
        Args:
            content: Content to format
            format_type: Desired format (markdown, html, json, text)
            shared_state: Shared state instance
            metadata: Optional metadata to include
            
        Returns:
            Dictionary with formatted content
        """
        shared_state.add_log(
            f"[MCP Formatting] Formatting content as {format_type}",
            LogType.MCP
        )
        
        if format_type not in MCPFormattingTool.SUPPORTED_FORMATS:
            shared_state.add_log(
                f"[MCP Formatting] Unsupported format: {format_type}, defaulting to markdown",
                LogType.WARNING
            )
            format_type = 'markdown'
        
        formatted = content
        
        if format_type == 'html':
            formatted = MCPFormattingTool._format_as_html(content, metadata)
        elif format_type == 'json':
            formatted = MCPFormattingTool._format_as_json(content, metadata)
        elif format_type == 'text':
            formatted = MCPFormattingTool._format_as_text(content)
        # markdown is default, no transformation needed
        
        result = {
            'formatted_content': formatted,
            'format': format_type,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        
        shared_state.formatted_output = formatted
        
        shared_state.add_log(
            f"[MCP Formatting] Successfully formatted as {format_type}",
            LogType.SUCCESS
        )
        
        return result
    
    @staticmethod
    def _format_as_html(content: str, metadata: Dict = None) -> str:
        """Format content as HTML."""
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Research Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
        h1 {{ color: #333; }}
        .metadata {{ background: #f4f4f4; padding: 10px; margin-bottom: 20px; }}
        .content {{ white-space: pre-wrap; }}
    </style>
</head>
<body>
    <h1>Research Report</h1>
"""
        
        if metadata:
            html += "    <div class='metadata'>\n"
            for key, value in metadata.items():
                html += f"        <p><strong>{key}:</strong> {value}</p>\n"
            html += "    </div>\n"
        
        html += f"""    <div class='content'>
{content}
    </div>
</body>
</html>"""
        
        return html
    
    @staticmethod
    def _format_as_json(content: str, metadata: Dict = None) -> str:
        """Format content as JSON."""
        data = {
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    @staticmethod
    def _format_as_text(content: str) -> str:
        """Format content as plain text (strip markdown)."""
        # Remove markdown formatting
        text = re.sub(r'#+ ', '', content)  # Headers
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)  # Bold
        text = re.sub(r'\*(.+?)\*', r'\1', text)  # Italic
        text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)  # Links
        return text
    
    @staticmethod
    def export_to_file(
        content: str,
        filename: str,
        shared_state: SharedState,
        export_path: str = None
    ) -> str:
        """
        Export content to file.
        
        Args:
            content: Content to export
            filename: Output filename
            shared_state: Shared state instance
            export_path: Optional custom export path
            
        Returns:
            Full path to exported file
        """
        shared_state.add_log(
            f"[MCP Export] Exporting to {filename}",
            LogType.MCP
        )
        
        if export_path is None:
            export_path = settings.export_path
        
        os.makedirs(export_path, exist_ok=True)
        filepath = os.path.join(export_path, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            shared_state.export_path = filepath
            
            shared_state.add_log(
                f"[MCP Export] Successfully exported to {filepath}",
                LogType.SUCCESS
            )
            
            return filepath
            
        except Exception as e:
            shared_state.add_log(
                f"[MCP Export] Error exporting file: {str(e)}",
                LogType.ERROR
            )
            raise
    
    @staticmethod
    def create_audit_report(shared_state: SharedState) -> str:
        """
        Create comprehensive audit report.
        
        Args:
            shared_state: Shared state instance
            
        Returns:
            Audit report as JSON string
        """
        audit_report = {
            'session_id': shared_state.session_id,
            'timestamp': datetime.now().isoformat(),
            'query': shared_state.query,
            'status': shared_state.status.value,
            'summary': shared_state.get_summary(),
            'compliance': shared_state.compliance_report,
            'logs': shared_state.logs,
            'ingested_documents': shared_state.ingested_documents,
            'retrieved_documents_count': shared_state.document_count,
            'web_sources_count': len(shared_state.web_sources),
            'citations_verified': shared_state.citation_count
        }
        
        return json.dumps(audit_report, indent=2, ensure_ascii=False)