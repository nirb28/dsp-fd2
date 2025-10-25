"""
LangGraph Workflow Module
Implements multi-step AI workflows with prompt chaining using LangGraph
"""

import json
import logging
import httpx
from typing import Dict, Any, Optional, List, Annotated
from datetime import datetime
import asyncio
from functools import reduce
from operator import add

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from src.core.module_interface import (
    BaseModule,
    ModuleConfig,
    ModuleRequest,
    ModuleResponse,
    ModuleStatus
)


logger = logging.getLogger(__name__)


class WorkflowState(TypedDict):
    """Base state for LangGraph workflows"""
    messages: Annotated[List[Dict[str, Any]], add_messages]
    document: str
    chunks: List[str]
    summaries: List[str]
    final_summary: str
    error: Optional[str]
    metadata: Dict[str, Any]


class LangGraphWorkflowModule(BaseModule):
    """
    Module for executing LangGraph-based AI workflows with prompt chaining.
    Supports sequential, parallel, and conditional workflows.
    """

    def __init__(self):
        super().__init__()
        self.workflow_graph = None
        self.workflow_config = None
        self.jwt_token = None
        self.inference_endpoint = None

    async def initialize(self, config: ModuleConfig) -> None:
        """Initialize the LangGraph workflow module"""
        await super().initialize(config)

        # Extract workflow configuration from runtime references
        self.workflow_config = config.runtime_references.get("workflow_config", {})
        
        # Get JWT token for authenticated requests
        jwt_module = self.workflow_config.get("jwt_module")
        if jwt_module:
            self.jwt_token = config.runtime_references.get("jwt_token")
        
        # Get inference endpoint URL
        inference_modules = self.workflow_config.get("inference_modules", [])
        if inference_modules:
            # Use the first inference module
            self.inference_endpoint = config.runtime_references.get(
                f"inference_endpoint_{inference_modules[0]}"
            )
        
        # Build the workflow graph
        self.workflow_graph = await self._build_workflow_graph()
        
        self.status = ModuleStatus.READY
        logger.info(f"LangGraph workflow module initialized: {self.workflow_config.get('workflow_name')}")

    async def _build_workflow_graph(self) -> StateGraph:
        """Build the LangGraph workflow from configuration"""
        # Create the state graph
        graph = StateGraph(WorkflowState)
        
        # Get nodes and edges from config
        nodes_config = self.workflow_config.get("nodes", [])
        edges_config = self.workflow_config.get("edges", [])
        
        # Add nodes to graph
        for node_config in nodes_config:
            node_id = node_config["id"]
            node_type = node_config["type"]
            
            if node_type == "function":
                # Add function node
                func_name = node_config["function"]
                node_func = self._get_node_function(func_name, node_config)
                graph.add_node(node_id, node_func)
                
            elif node_type == "llm":
                # Add LLM node
                node_func = self._create_llm_node(node_config)
                graph.add_node(node_id, node_func)
        
        # Add edges
        for edge_config in edges_config:
            from_node = edge_config["from"]
            to_node = edge_config["to"]
            
            # Handle special START node
            if from_node == "START":
                graph.add_edge(START, to_node)
            elif to_node == "END":
                graph.add_edge(from_node, END)
            else:
                graph.add_edge(from_node, to_node)
        
        # Set entry point if no START edge
        if nodes_config and not any(e.get("from") == "START" for e in edges_config):
            graph.set_entry_point(nodes_config[0]["id"])
        
        # Set finish point if no END edge
        if nodes_config and not any(e.get("to") == "END" for e in edges_config):
            graph.set_finish_point(nodes_config[-1]["id"])
        
        return graph.compile()

    def _get_node_function(self, func_name: str, config: Dict[str, Any]):
        """Get the appropriate function for a node"""
        functions = {
            "split_into_chunks": self._split_into_chunks,
            "combine_results": self._combine_results,
        }
        
        func = functions.get(func_name)
        if not func:
            raise ValueError(f"Unknown function: {func_name}")
        
        # Return a wrapper that includes config
        async def wrapper(state: WorkflowState) -> WorkflowState:
            return await func(state, config.get("config", {}))
        
        return wrapper

    async def _split_into_chunks(
        self, 
        state: WorkflowState, 
        config: Dict[str, Any]
    ) -> WorkflowState:
        """Split document into chunks"""
        document = state.get("document", "")
        chunk_size = config.get("chunk_size", 2000)
        chunk_overlap = config.get("chunk_overlap", 200)
        
        chunks = []
        start = 0
        
        while start < len(document):
            end = start + chunk_size
            chunk = document[start:end]
            chunks.append(chunk)
            start = end - chunk_overlap
        
        state["chunks"] = chunks
        state["metadata"]["num_chunks"] = len(chunks)
        
        logger.info(f"Split document into {len(chunks)} chunks")
        return state

    async def _combine_results(
        self,
        state: WorkflowState,
        config: Dict[str, Any]
    ) -> WorkflowState:
        """Combine results from previous steps"""
        summaries = state.get("summaries", [])
        combined = "\n\n".join(summaries)
        state["final_summary"] = combined
        return state

    def _create_llm_node(self, node_config: Dict[str, Any]):
        """Create an LLM node function"""
        prompt_template = node_config.get("prompt_template", "{input}")
        node_id = node_config["id"]
        llm_config = node_config.get("config", {})
        
        async def llm_node(state: WorkflowState) -> WorkflowState:
            """Execute LLM call"""
            try:
                # Handle parallel processing of chunks
                if llm_config.get("parallel") and "chunks" in state:
                    summaries = []
                    chunks = state["chunks"]
                    
                    # Process chunks in parallel batches
                    batch_size = 5
                    for i in range(0, len(chunks), batch_size):
                        batch = chunks[i:i + batch_size]
                        tasks = [
                            self._call_llm(prompt_template.format(chunk=chunk), llm_config)
                            for chunk in batch
                        ]
                        batch_results = await asyncio.gather(*tasks)
                        summaries.extend(batch_results)
                    
                    state["summaries"] = summaries
                    logger.info(f"Processed {len(summaries)} chunks in parallel")
                
                # Handle combining summaries
                elif "summaries" in state and node_id == "combine_summaries":
                    summaries_text = "\n\n".join(state["summaries"])
                    prompt = prompt_template.format(summaries=summaries_text)
                    final_summary = await self._call_llm(prompt, llm_config)
                    state["final_summary"] = final_summary
                    logger.info("Combined summaries into final summary")
                
                # Handle single LLM call
                else:
                    input_text = state.get("document", "")
                    prompt = prompt_template.format(input=input_text)
                    result = await self._call_llm(prompt, llm_config)
                    state["final_summary"] = result
                
                return state
                
            except Exception as e:
                logger.error(f"LLM node error: {str(e)}")
                state["error"] = str(e)
                return state
        
        return llm_node

    async def _call_llm(
        self,
        prompt: str,
        config: Dict[str, Any]
    ) -> str:
        """Make LLM API call through APISIX gateway"""
        if not self.inference_endpoint:
            raise ValueError("No inference endpoint configured")
        
        # Prepare request body
        body = {
            "model": config.get("model", "llama-3.1-70b-versatile"),
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful AI assistant."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": config.get("max_tokens", 500),
            "temperature": config.get("temperature", 0.3)
        }
        
        # Add JWT token if available
        headers = {"Content-Type": "application/json"}
        if self.jwt_token:
            headers["Authorization"] = f"Bearer {self.jwt_token}"
        
        # Make API call
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.inference_endpoint,
                    json=body,
                    headers=headers
                )
                response.raise_for_status()
                
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                return content
                
        except Exception as e:
            logger.error(f"LLM API call failed: {str(e)}")
            raise

    async def handle_request(self, request: ModuleRequest) -> ModuleResponse:
        """
        Handle workflow execution requests
        
        Expected request body:
        {
            "document": "text to process",
            "workflow_params": {}
        }
        """
        try:
            body = request.body or {}
            document = body.get("document", "")
            
            if not document:
                return ModuleResponse(
                    status_code=400,
                    body={"error": "No document provided"}
                )
            
            # Initialize workflow state
            initial_state: WorkflowState = {
                "messages": [],
                "document": document,
                "chunks": [],
                "summaries": [],
                "final_summary": "",
                "error": None,
                "metadata": {
                    "started_at": datetime.utcnow().isoformat(),
                    "workflow_name": self.workflow_config.get("workflow_name")
                }
            }
            
            # Execute workflow
            logger.info(f"Starting workflow: {self.workflow_config.get('workflow_name')}")
            final_state = await self.workflow_graph.ainvoke(initial_state)
            
            # Check for errors
            if final_state.get("error"):
                return ModuleResponse(
                    status_code=500,
                    body={
                        "error": final_state["error"],
                        "metadata": final_state.get("metadata", {})
                    }
                )
            
            # Return results
            return ModuleResponse(
                status_code=200,
                body={
                    "final_summary": final_state.get("final_summary", ""),
                    "metadata": {
                        **final_state.get("metadata", {}),
                        "num_chunks": len(final_state.get("chunks", [])),
                        "completed_at": datetime.utcnow().isoformat()
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {str(e)}", exc_info=True)
            return ModuleResponse(
                status_code=500,
                body={"error": f"Workflow execution failed: {str(e)}"}
            )

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        health = await super().health_check()
        health.update({
            "workflow_name": self.workflow_config.get("workflow_name") if self.workflow_config else None,
            "has_graph": self.workflow_graph is not None,
            "has_jwt": self.jwt_token is not None,
            "has_endpoint": self.inference_endpoint is not None
        })
        return health

    async def shutdown(self) -> None:
        """Shutdown the module"""
        logger.info("Shutting down LangGraph workflow module")
        await super().shutdown()
