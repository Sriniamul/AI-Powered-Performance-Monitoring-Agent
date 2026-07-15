def format_insights(insights: dict) -> str:
    return f"Summary: {insights.get('summary')}\nRecommendation: {insights.get('recommendation')}"
