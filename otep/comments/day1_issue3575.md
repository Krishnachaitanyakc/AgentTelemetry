The N+1 span type problem is real — I've been thinking about this exact tension while
working on agent instrumentation.

One case where I think grouping and dedicated operations solve different problems:

An agent planning phase. The agent calls an LLM to decompose a task, then executes each
step. You could tag those spans with `gen_ai.group.type = "plan"`, but you'd lose the
duration of the planning phase itself — how long did the agent spend deciding *what* to do
vs. actually doing it? The `chat` call that generates the plan is causally a *child* of
the planning decision, not a sibling that happens to share a group tag.

`execute_tool` exists as its own operation for the same reason — it could be a grouped
`chat` span, but tool-specific attributes and the timing of the tool phase justify a
dedicated operation.

So maybe: grouping for loose structural relationships (correlating spans in a ReAct round
or conversation turn), and dedicated operations where the phase has its own meaningful
duration and hierarchy. They'd work together rather than replace each other.

Where do you see the line between "this is just a grouping concern" and "this needs its
own operation"?
