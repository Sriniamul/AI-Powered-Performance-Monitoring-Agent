def summarize_gc_text(text: str) -> str:
    if not text:
        return "No GC text available."
    full_gc_count = text.lower().count("full")
    return f"GC text available. Approximate occurrences of 'full': {full_gc_count}."
