from models.query import RetrievedContext

SYSTEM_PROMPT = """
You are a strict document-grounded assistant.

You MUST follow these rules:

1. Only use the provided Context to answer.
2. Do NOT use prior knowledge.
3. Do NOT infer beyond what is explicitly stated.
4. If the answer is not explicitly present in the Context, reply exactly:
   "not found in document"
5. Every factual statement must include a citation in this format:
   (Source: <file name>, Page: <page number>, Section: <section name>)
6. Do NOT fabricate citations.
7. Do NOT combine unrelated sections unless explicitly connected in the Context.

Your goal is precise, verifiable answers grounded only in the document.
"""


class PromptBuilder:

    @staticmethod
    def build_messages(
        question: str,
        contexts: list[RetrievedContext]
    ) -> list[dict]:
        """
        Builds chat messages for document-grounded QA.
        Strictly enforces context-only answering with citations.
        """

        # 🔒 Safe fallback if retrieval failed
        if not contexts:
            return [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "No relevant context was retrieved.\n\n"
                        "Reply exactly: not found in document"
                    )
                }
            ]

        context_parts = []

        for ctx in contexts:
            source = ctx.metadata.source_file

            # Format page range nicely
            if (
                ctx.metadata.page_range
                and len(ctx.metadata.page_range) == 2
                and ctx.metadata.page_range[0] == ctx.metadata.page_range[1]
            ):
                pages = f"{ctx.metadata.page_range[0]}"
            elif ctx.metadata.page_range and len(ctx.metadata.page_range) == 2:
                pages = f"{ctx.metadata.page_range[0]}-{ctx.metadata.page_range[1]}"
            else:
                pages = "Unknown"

            section = ctx.metadata.section_path or "Unknown Section"

            header = (
                f"[SOURCE: {source} | Page {pages} | {section}]"
            )

            part = f"{header}\n{ctx.parent_text.strip()}"
            context_parts.append(part)

        context_str = "\n\n".join(context_parts)

        user_content = f"""
You are given extracted document context below.
Only use this context to answer the question.

<BEGIN_CONTEXT>
{context_str}
<END_CONTEXT>

Question:
{question}

Remember:
- Cite every factual statement.
- Use the required citation format.
- If not explicitly stated, reply: not found in document

Answer:
"""

        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content.strip()}
        ]

    @staticmethod
    def build_summarization_prompt(
        context: str,
        mode: str
    ) -> list[dict]:
        """
        Builds messages for summarization or key-points extraction.
        Ensures strict context grounding.
        """

        if not context:
            return [
                {
                    "role": "system",
                    "content": "You are a document assistant."
                },
                {
                    "role": "user",
                    "content": "No context available. Reply exactly: not found in document"
                }
            ]

        if mode == "key_points":
            system_msg = """
You are a professional analyst.

Extract the most important key insights from the provided context.
Only use information present in the context.
Do NOT introduce external knowledge.
Return a concise bulleted list.
"""
            user_prompt = f"""
<BEGIN_CONTEXT>
{context.strip()}
<END_CONTEXT>

Provide the key points now.
"""
        else:
            system_msg = """
You are a professional executive writer.

Provide a concise executive-style overview of the document.
Use ONLY the provided context.
Do NOT introduce external knowledge.
Structure the response in 3-5 clear paragraphs.
"""
            user_prompt = f"""
<BEGIN_CONTEXT>
{context.strip()}
<END_CONTEXT>

Provide the executive summary now.
"""

        return [
            {"role": "system", "content": system_msg.strip()},
            {"role": "user", "content": user_prompt.strip()}
        ]