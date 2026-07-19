"""
Agentic RAG implementation using LangGraph
Implements multi-step reasoning with self-reflection
"""
from typing import TypedDict, List, Annotated
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from loguru import logger
import operator
import os

# Load settings so we can default to configured OpenAI model/key
try:
    from config import settings as _settings
except Exception:
    _settings = None


class ComplianceState(TypedDict):
    """State for the compliance agent"""
    messages: Annotated[List, operator.add]
    query: str
    retrieved_docs: List[dict]
    answer: str
    reflection: str
    iterations: int
    max_iterations: int
    needs_reflection: bool


class ComplianceAgent:
    """
    Agentic compliance auditor with reasoning and self-reflection
    """

    def __init__(
        self,
        retriever,
        tools,
        model_name: str = "gpt-4o-mini",
        max_iterations: int = 5,
        enable_reflection: bool = True,
        api_key: str = None,
        base_url: str = None,
        temperature: float = 0.1,
    ):
        """
        Initialize compliance agent

        Args:
            retriever: Document retriever
            tools: List of LangChain tools
            model_name: OpenAI model name (e.g. gpt-4o-mini)
            max_iterations: Maximum reasoning iterations
            enable_reflection: Enable self-reflection
            api_key: OpenAI API key (falls back to settings / OPENAI_API_KEY env var)
            base_url: OpenAI-compatible base URL (optional)
            temperature: Sampling temperature
        """
        self.retriever = retriever
        self.tools = tools
        self.max_iterations = max_iterations
        self.enable_reflection = enable_reflection

        # Resolve API key / base URL from args -> settings -> env
        api_key = api_key or (getattr(_settings, "OPENAI_API_KEY", None) if _settings else None) \
                  or os.getenv("OPENAI_API_KEY")
        base_url = base_url or (getattr(_settings, "OPENAI_BASE_URL", None) if _settings else None) \
                   or os.getenv("OPENAI_BASE_URL")

        if not api_key:
            raise ValueError(
                "OpenAI API key not set. Put OPENAI_API_KEY in .env or pass api_key=..."
            )

        # Initialize LLM
        logger.info(f"Initializing OpenAI LLM: {model_name}")
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=temperature,
            api_key=api_key,
            base_url=base_url,
        )

        # Bind tools to LLM
        self.llm_with_tools = self.llm.bind_tools(tools)

        # Build agent graph
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(ComplianceState)

        # Add nodes
        workflow.add_node("retrieve", self.retrieve_node)
        workflow.add_node("generate", self.generate_node)
        workflow.add_node("reflect", self.reflect_node)
        workflow.add_node("tools", ToolNode(self.tools))

        # Set entry point
        workflow.set_entry_point("retrieve")

        # Add edges
        workflow.add_edge("retrieve", "generate")
        workflow.add_conditional_edges(
            "generate",
            self.should_use_tools,
            {
                "tools": "tools",
                "reflect": "reflect",
                "end": END
            }
        )
        workflow.add_edge("tools", "generate")
        workflow.add_conditional_edges(
            "reflect",
            self.should_continue,
            {
                "retrieve": "retrieve",
                "end": END
            }
        )

        return workflow.compile()

    def retrieve_node(self, state: ComplianceState) -> ComplianceState:
        """Retrieve relevant documents"""
        logger.info("Node: retrieve")

        query = state['query']

        # Use retriever to get relevant documents
        results = self.retriever.retrieve(query, top_k=5, strategy="hybrid")

        state['retrieved_docs'] = results

        logger.info(f"Retrieved {len(results)} documents")

        return state

    def generate_node(self, state: ComplianceState) -> ComplianceState:
        """Generate answer using LLM"""
        logger.info("Node: generate")

        # Build context from retrieved documents
        context = self._format_context(state['retrieved_docs'])

        # System prompt
        system_prompt = """You are a compliance auditor AI assistant specializing in regulatory compliance.

Your task is to:
1. Answer compliance questions accurately using ONLY information from the provided regulatory documents
2. Cite specific articles, sections, or regulations when making claims
3. Use available tools when you need more information
4. Be precise and avoid speculation
5. If information is not in the documents, say so clearly

When answering:
- Always cite the source (Article/Section number and regulation name)
- Be specific about requirements and obligations
- Identify any gaps or contradictions
- Use tools if you need to search for specific information"""

        # Build messages
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Question: {state['query']}\n\nContext:\n{context}")
        ]

        # Add any previous messages (for tool calls)
        if 'messages' in state and state['messages']:
            messages.extend(state['messages'])

        # Generate response
        response = self.llm_with_tools.invoke(messages)

        # Update state
        if not state.get('messages'):
            state['messages'] = []

        state['messages'].append(response)

        # Extract answer if present
        if hasattr(response, 'content') and response.content:
            state['answer'] = response.content

        return state

    def reflect_node(self, state: ComplianceState) -> ComplianceState:
        """Self-reflection on the answer"""
        logger.info("Node: reflect")

        if not self.enable_reflection:
            return state

        answer = state.get('answer', '')

        # Reflection prompt
        reflection_prompt = f"""Review this compliance answer for accuracy and completeness:

Answer: {answer}

Check for:
1. Are all claims properly cited with article/section numbers?
2. Is there any speculation or unsupported information?
3. Are there contradictions in the answer?
4. Is anything missing that should be addressed?
5. Is the answer directly answering the question?

Provide a brief reflection (2-3 sentences) on whether the answer needs improvement."""

        reflection_response = self.llm.invoke([
            SystemMessage(content="You are a compliance expert reviewing answers for accuracy."),
            HumanMessage(content=reflection_prompt)
        ])

        state['reflection'] = reflection_response.content

        # Determine if we need to iterate
        needs_improvement = any(keyword in reflection_response.content.lower() for keyword in [
            'missing', 'incomplete', 'need', 'should', 'incorrect', 'unsupported'
        ])

        state['needs_reflection'] = needs_improvement
        state['iterations'] = state.get('iterations', 0) + 1

        logger.info(f"Reflection: {reflection_response.content[:100]}...")

        return state

    def should_use_tools(self, state: ComplianceState) -> str:
        """Decide if tools should be used"""
        last_message = state['messages'][-1]

        # Check if LLM wants to use tools
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            logger.info("Decision: Using tools")
            return "tools"

        # Check if we should reflect
        if self.enable_reflection:
            logger.info("Decision: Reflecting")
            return "reflect"

        logger.info("Decision: End")
        return "end"

    def should_continue(self, state: ComplianceState) -> str:
        """Decide if we should continue iterating"""
        iterations = state.get('iterations', 0)

        # Check max iterations
        if iterations >= self.max_iterations:
            logger.info(f"Max iterations ({self.max_iterations}) reached")
            return "end"

        # Check if reflection suggests improvement needed
        if state.get('needs_reflection', False):
            logger.info("Reflection suggests improvement needed, continuing")
            return "retrieve"

        logger.info("Answer is satisfactory")
        return "end"

    def _format_context(self, documents: List[dict]) -> str:
        """Format retrieved documents as context"""
        if not documents:
            return "No relevant documents found."

        context_parts = []

        for i, doc in enumerate(documents, 1):
            citation = doc.get('citation', f"[{i}]")
            content = doc['content']
            score = doc.get('similarity_score', 0)

            context_parts.append(
                f"{citation} (Relevance: {score:.2%})\n{content}"
            )

        return "\n\n---\n\n".join(context_parts)

    def run(self, query: str) -> dict:
        """
        Run the agent on a query

        Args:
            query: Compliance question

        Returns:
            Dictionary with answer and metadata
        """
        logger.info(f"Running agent for query: {query}")

        # Initial state
        initial_state = ComplianceState(
            messages=[],
            query=query,
            retrieved_docs=[],
            answer="",
            reflection="",
            iterations=0,
            max_iterations=self.max_iterations,
            needs_reflection=False
        )

        # Run the graph
        final_state = self.graph.invoke(initial_state)

        # Extract result
        result = {
            'query': query,
            'answer': final_state.get('answer', 'No answer generated'),
            'sources': final_state.get('retrieved_docs', []),
            'reflection': final_state.get('reflection', ''),
            'iterations': final_state.get('iterations', 0),
            'messages': final_state.get('messages', [])
        }

        logger.info(f"Agent completed in {result['iterations']} iterations")

        return result

    def stream(self, query: str):
        """
        Stream the agent execution (for real-time updates)

        Args:
            query: Compliance question

        Yields:
            State updates as they occur
        """
        initial_state = ComplianceState(
            messages=[],
            query=query,
            retrieved_docs=[],
            answer="",
            reflection="",
            iterations=0,
            max_iterations=self.max_iterations,
            needs_reflection=False
        )

        for state in self.graph.stream(initial_state):
            yield state


if __name__ == "__main__":
    # Test the agent
    from pathlib import Path
    import sys

    sys.path.append(str(Path(__file__).parent.parent))

    from retrieval import VectorStore, CitationRetriever
    from agents.tools import create_langchain_tools

    # Initialize components
    vector_store = VectorStore(
        persist_directory="./data/chroma_db",
        collection_name="test_compliance"
    )
    retriever = CitationRetriever(vector_store)
    tools = create_langchain_tools(retriever)

    # Create agent
    agent = ComplianceAgent(
        retriever=retriever,
        tools=tools,
        model_name="gpt-4o-mini",
        max_iterations=3
    )

    # Test query
    test_query = "What are the requirements for data retention under GDPR Article 17?"

    print(f"Query: {test_query}\n")

    result = agent.run(test_query)

    print(f"Answer:\n{result['answer']}\n")
    print(f"Iterations: {result['iterations']}")
    print(f"Reflection: {result['reflection']}")
