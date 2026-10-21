import os
from copilot.evidence_retriever import retrieve
from copilot.prompts import SYSTEM

def answer(question, model="claude-sonnet-4-6"):
    ev = retrieve(question)
    if ev["intent"] == "unknown" or not ev["facts"]:
        text = ("I couldn't find matching evidence in the database for that question. Try e.g. 'Why was DOC-1 flagged?', "
                "'Which documents contradict DOC-1?', 'Show possible duplicates', or 'Which documents have low OCR confidence?'")
        return dict(answer=text, evidence=[], refs=[], grounded=True, llm=False)
    if os.getenv("ANTHROPIC_API_KEY"):
        try:
            import anthropic
            msg = anthropic.Anthropic().messages.create(model=model, max_tokens=600, system=SYSTEM, messages=[
                {"role": "user", "content": "EVIDENCE:\n" + "\n".join(f"- {f}" for f in ev["facts"][:40]) + f"\n\nQUESTION: {question}"}])
            return dict(answer=msg.content[0].text, evidence=ev["facts"], refs=ev["refs"], grounded=True, llm=True)
        except Exception:
            pass  # fall through to deterministic grounded answer
    return dict(answer="\n".join("• " + f for f in ev["facts"][:25]), evidence=ev["facts"], refs=ev["refs"], grounded=True, llm=False)
