# Inter-Rater Reliability Coding Sheet
## AgentTelemetry Span Kind Classification

### Instructions for Coder

You are helping validate a taxonomy of 9 "span kinds" for observing AI agent execution. Each span kind represents a distinct phase of agent behavior.

**Your task:** For each of the 25 API entry points listed below, assign the ONE most appropriate span kind from the list of 9 kinds.

### The 9 Span Kinds (with definitions)

| # | Span Kind | Definition |
|---|-----------|------------|
| 1 | AGENT | Wraps the entire lifecycle of an autonomous agent instance |
| 2 | LLM_CALL | A single invocation of a language model (chat completion, text generation) |
| 3 | TOOL_CALL | Execution of an external tool or function by the agent |
| 4 | PLANNING | Task decomposition or action plan generation by the agent |
| 5 | REASONING | Chain-of-thought or intermediate reasoning steps within an action |
| 6 | RETRIEVAL | Fetching documents or data from external sources (RAG, search, embeddings) |
| 7 | GUARD_RAIL | Safety check, content filter, or policy enforcement |
| 8 | DELEGATION | Handoff of a task from one agent to another agent |
| 9 | MEMORY | Reading from or writing to the agent's persistent memory/state |

### API Entry Points to Classify

For each entry, write the span kind number (1-9) in the "Your Classification" column.

| # | Framework | API Method | Description | Your Classification |
|---|-----------|------------|-------------|-------------------|
| 1 | LangChain | `on_llm_start(serialized, prompts)` | Called when an LLM begins generating a response | |
| 2 | LangChain | `on_chat_model_start(serialized, messages)` | Called when a chat model begins processing messages | |
| 3 | LangChain | `on_tool_start(serialized, input_str)` | Called when a tool begins execution | |
| 4 | LangChain | `on_retriever_start(serialized, query)` | Called when a document retriever begins searching | |
| 5 | LangChain | `on_agent_action(action)` | Called when an agent decides on its next action (tool + input) | |
| 6 | LangChain | `on_chain_start(serialized, inputs)` [AgentExecutor] | Called when an agent executor chain begins | |
| 7 | LangChain | `on_chain_start(serialized, inputs)` [other chains] | Called when a non-agent chain (e.g., summarization) begins | |
| 8 | CrewAI | `before_kickoff(inputs)` | Called before a crew of agents starts executing | |
| 9 | CrewAI | `task_started(task)` | Called when a specific task is assigned to an agent | |
| 10 | CrewAI | `before_tool_call_hook(agent, tool, input)` | Called before an agent invokes a tool | |
| 11 | CrewAI | `after_tool_call_hook(agent, tool, output)` | Called after a tool returns its result | |
| 12 | AutoGen | `initiate_chat(message)` | Called when one agent starts a conversation with another | |
| 13 | AutoGen | `generate_reply(messages, sender)` | Called when an agent generates an LLM-based reply | |
| 14 | AutoGen | `execute_function(func_call)` | Called when an agent executes a function/tool | |
| 15 | AutoGen | `register_nested_chats(chat_queue)` | Called when an agent delegates a sub-conversation to other agents | |
| 16 | LlamaIndex | `query(query_str)` | Called when a query engine processes a user question | |
| 17 | LlamaIndex | `retrieve(query_str)` | Called when a retriever fetches relevant documents | |
| 18 | LlamaIndex | `synthesize(query, nodes)` | Called when a response synthesizer generates an answer from retrieved docs | |
| 19 | LlamaIndex | `sub_question_query(sub_questions)` | Called when a query is decomposed into sub-questions | |
| 20 | OpenAI SDK | `chat.completions.create(model, messages)` | Makes an API call to generate a chat completion | |
| 21 | OpenAI SDK | `Handoff(target_agent)` [Agents SDK] | Transfers control from one agent to another | |
| 22 | Anthropic SDK | `messages.create(model, messages)` | Makes an API call to generate a message response | |
| 23 | Anthropic SDK | `tool_use` (response block) | Agent decides to invoke a tool based on LLM output | |
| 24 | Custom | `start_planning_span(strategy)` | Developer explicitly marks the beginning of a planning phase | |
| 25 | Custom | `start_guardrail_span(check_name)` | Developer explicitly marks a safety/policy check | |

### Expected Answers (DO NOT show to coder — for analysis only)

| # | Author's Classification | Span Kind |
|---|------------------------|-----------|
| 1 | 2 | LLM_CALL |
| 2 | 2 | LLM_CALL |
| 3 | 3 | TOOL_CALL |
| 4 | 6 | RETRIEVAL |
| 5 | 4 | PLANNING |
| 6 | 1 | AGENT |
| 7 | 5 | REASONING |
| 8 | 1 | AGENT |
| 9 | 8 | DELEGATION |
| 10 | 3 | TOOL_CALL |
| 11 | 3 | TOOL_CALL |
| 12 | 8 | DELEGATION |
| 13 | 2 | LLM_CALL |
| 14 | 3 | TOOL_CALL |
| 15 | 8 | DELEGATION |
| 16 | 5 | REASONING |
| 17 | 6 | RETRIEVAL |
| 18 | 2 | LLM_CALL |
| 19 | 4 | PLANNING |
| 20 | 2 | LLM_CALL |
| 21 | 8 | DELEGATION |
| 22 | 2 | LLM_CALL |
| 23 | 3 | TOOL_CALL |
| 24 | 4 | PLANNING |
| 25 | 7 | GUARD_RAIL |

### Computing Agreement

After the coder completes classification:

1. **Raw agreement** = (number matching) / 25
2. **Cohen's kappa**: Use Python:
```python
from sklearn.metrics import cohen_kappa_score
author = [2,2,3,6,4,1,5,1,8,3,3,8,2,3,8,5,6,2,4,2,8,2,3,4,7]
coder = [...]  # fill in coder's answers
kappa = cohen_kappa_score(author, coder)
print(f"Cohen's kappa: {kappa:.3f}")
# Interpretation: <0.20 slight, 0.21-0.40 fair, 0.41-0.60 moderate,
#                  0.61-0.80 substantial, 0.81-1.00 almost perfect
```

### Notes for Paper

Add to Section 3.1 (Taxonomy Derivation):
"To assess inter-rater reliability, a second coder with [X years] of agent development experience independently classified all 25 API entry points into the 9 span kinds. Agreement was [raw]% (Cohen's κ = [X.XX], [interpretation]). Disagreements occurred primarily at the [X]/[Y] boundary, consistent with [explanation]."
