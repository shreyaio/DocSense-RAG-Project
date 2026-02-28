from models.query import RetrievedContext

SYSTEM_PROMPT = """You are a document-grounded assistant.
Rules: answer only from context, cite page numbers and sections,
say 'not found in document' if absent, do not speculate."""

class PromptBuilder:
    @staticmethod
    def build_messages(question: str, contexts: list[RetrievedContext]) -> list[dict]:
        """
        Compiles the system prompt and retrieveed contexts into a format suitable for LLM APIs.
        """
        if not contexts:
            return []

        context_parts = []
        for ctx in contexts:
            source = ctx.metadata.source_file
            # Format page range nicely if it's the same page
            if len(ctx.metadata.page_range) == 2 and ctx.metadata.page_range[0] == ctx.metadata.page_range[1]:
                pages = f"{ctx.metadata.page_range[0]}"
            else:
                pages = f"{ctx.metadata.page_range[0]}-{ctx.metadata.page_range[1]}"
            
            section = ctx.metadata.section_path or "Unknown Section"
            
            header = f"[SOURCE: {source} | Page {pages} | {section}]"
            part = f"{header}\n{ctx.parent_text}"
            context_parts.append(part)

        context_str = "\n\n".join(context_parts)
        
        user_content = f"Context:\n---\n{context_str}\n---\nQuestion: {question}"
        
        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content}
        ]

    @staticmethod
    def build_summarization_prompt(context: str, mode: str) -> list[dict]:
        """
        Builds messages for summarization/key-points based on document context.
        """
        if mode == "key_points":
            system_msg = "You are a professional analyst. Extract the most important key insights from the context as a bulleted list. Do not include information not present in the context."
            user_prompt = f"Context:\n---\n{context}\n---\nProvide the key points now."
        else:
            system_msg = "You are a professional writer. Provide a concise executive-style overview of the document based ONLY on the context. Structure in 3-5 paragraphs."
            user_prompt = f"Context:\n---\n{context}\n---\nProvide the executive summary now."

        return [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_prompt}
        ]
