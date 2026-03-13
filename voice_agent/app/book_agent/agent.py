"""
ADK Agent for the book platform voice assistant.
Helps users find books, authors, prices, and investment campaigns.
"""

import os

from google.adk.agents import Agent

from app.book_tools import (
    get_author_books,
    get_book_info,
    get_campaign_info,
    get_catalog_stats,
    get_open_campaigns,
    list_authors,
    search_books,
)

agent = Agent(
    name="book_platform_agent",
    model=os.getenv(
        "VOICE_AGENT_MODEL",
        "gemini-2.5-flash-native-audio-preview-12-2025",
    ),
    tools=[
        search_books,
        get_book_info,
        list_authors,
        get_author_books,
        get_open_campaigns,
        get_campaign_info,
        get_catalog_stats,
    ],
    instruction="""You are a helpful voice assistant for a book platform. Your role is to help users:

- Find and discover books by searching titles, descriptions, genre, or language
- Get details about specific books (title, author, price, genre, description, chapters, audiobook availability)
- Browse authors and their published books
- Explore active investment campaigns where users can invest in upcoming books
- Get catalog statistics (total books, genres, languages)

When users ask about books, authors, or campaigns, use the appropriate tools to fetch accurate data from the database. Be conversational and concise in your responses. For prices, mention the currency (USD) when relevant. If a book has an audiobook, mention it. For investment campaigns, explain the funding goal, current funding, and minimum investment clearly.""",
)
