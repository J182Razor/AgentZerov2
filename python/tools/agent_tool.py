"""
Agent-as-Tool Pattern for Agent Zero
Allows wrapping any agent as a callable tool.
"""

import asyncio
from typing import Optional, Any
from agent import Agent, AgentContext, AgentContextType, UserMessage
from python.helpers.tool import Tool, Response
from python.helpers.subagents import load_agent_data
from initialize import initialize_agent
from python.helpers.print_style import PrintStyle


class AgentTool(Tool):
    """
    Use another agent as a tool. The agent becomes a callable
    capability that can be invoked within workflows.
    """
    
    async def execute(
        self,
        agent_name: str,
        task: str,
        timeout: int = 300,
        profile: str = "",
        system_prompt: str = "",
        **kwargs
    ) -> Response:
        """
        Execute an agent as a tool.
        
        Args:
            agent_name: Name of the agent to invoke (from subagents)
            task: The task to send to the agent
            timeout: Maximum execution time in seconds
            profile: Optional profile override
            system_prompt: Optional system prompt override
            **kwargs: Additional parameters
        
        Returns:
            Response with the agent's output
        """
        try:
            # Load agent configuration
            try:
                agent_data = load_agent_data(agent_name)
                PrintStyle(font_color="cyan").print(
                    f"AgentTool: Loaded agent '{agent_name}' with title '{agent_data.title}'"
                )
            except FileNotFoundError:
                return Response(
                    message=f"Error: Agent '{agent_name}' not found. Available agents can be listed via subagents.",
                    break_loop=False
                )
            
            # Initialize config
            config = initialize_agent()
            
            # Override profile if specified
            if profile:
                config.profile = profile
            
            # Create isolated context for tool agent
            tool_context = AgentContext(
                config=config,
                name=f"tool_{agent_name}",
                type=AgentContextType.BACKGROUND,
                set_current=False
            )
            
            # Create agent instance
            tool_agent = Agent(
                number=self.agent.number + 1,
                config=config,
                context=tool_context
            )
            
            # Set superior relationship
            tool_agent.set_data(Agent.DATA_NAME_SUPERIOR, self.agent)
            
            # Add user message to the tool agent
            tool_agent.hist_add_user_message(
                UserMessage(message=task, attachments=[])
            )
            
            PrintStyle(font_color="cyan").print(
                f"AgentTool: Executing agent '{agent_name}' with timeout {timeout}s"
            )
            
            # Execute with timeout
            try:
                result = await asyncio.wait_for(
                    tool_agent.monologue(),
                    timeout=timeout
                )
                
                # Seal the history
                tool_agent.history.new_topic()
                
                PrintStyle(font_color="green").print(
                    f"AgentTool: Agent '{agent_name}' completed successfully"
                )
                
                return Response(
                    message=result,
                    break_loop=False,
                    additional={
                        "agent": agent_name,
                        "task": task,
                        "timeout": timeout,
                        "success": True
                    }
                )
                
            except asyncio.TimeoutError:
                PrintStyle(font_color="yellow").print(
                    f"AgentTool: Agent '{agent_name}' timed out after {timeout}s"
                )
                return Response(
                    message=f"Agent '{agent_name}' timed out after {timeout} seconds. Consider increasing timeout or simplifying the task.",
                    break_loop=False,
                    additional={
                        "agent": agent_name,
                        "task": task,
                        "timeout": timeout,
                        "success": False,
                        "error": "timeout"
                    }
                )
                
        except Exception as e:
            PrintStyle(font_color="red").print(
                f"AgentTool: Error executing agent '{agent_name}': {str(e)}"
            )
            return Response(
                message=f"Error executing agent '{agent_name}': {str(e)}",
                break_loop=False,
                additional={
                    "agent": agent_name,
                    "success": False,
                    "error": str(e)
                }
            )


class swarm_agent(Tool):
    """
    Spawn a specialized agent to handle a specific task.
    This is an alias for the agent_tool with a swarm-friendly name.
    """
    
    async def execute(
        self,
        agent: str,
        task: str,
        timeout: str = "300",
        **kwargs
    ) -> Response:
        """
        Execute a specialized agent.
        
        Args:
            agent: Name of the agent profile to use (developer, researcher, hacker, etc.)
            task: The task for the agent to complete
            timeout: Maximum execution time in seconds (as string)
        """
        timeout_int = int(timeout) if timeout.isdigit() else 300
        
        tool = AgentTool(
            agent=self.agent,
            args={"agent_name": agent, "task": task, "timeout": timeout_int},
            message="",
            loop_count=0
        )
        return await tool.execute(
            agent_name=agent,
            task=task,
            timeout=timeout_int,
            **kwargs
        )
