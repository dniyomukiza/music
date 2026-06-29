import os
import json
from dotenv import load_dotenv
from google.adk.agents import Agent

load_dotenv()

# Configure Google AI SDK
google_api_key = os.getenv("GOOGLE_API_KEY")
if google_api_key:
    os.environ['GOOGLE_API_KEY'] = google_api_key

def fetch_book_context(book_id: int) -> dict:
    """
    Fetches the entire context of a book (lore, previous chapters) directly from the database.
    This runs inside the Flask app context before the ADK agent is executed.
    """
    from glconnect.book_platform_models import BookProject, BookChapter
    
    book = BookProject.query.get(book_id)
    if not book:
        return {"error": "Book not found"}
        
    chapters = BookChapter.query.filter_by(book_project_id=book_id).order_by(BookChapter.chapter_number).all()
    
    chapter_summaries = []
    for chap in chapters:
        chapter_summaries.append(f"Chapter {chap.chapter_number} ({chap.title}): {chap.content[:500]}...")
        
    lore = f"""
    Title: {book.title}
    Genre: {book.genre}
    Audience: {book.target_audience}
    Description/Logline: {book.description}
    """
    
    return {
        "lore": lore.strip(),
        "previous_chapters_summary": "\n".join(chapter_summaries)
    }

def create_developmental_editor_agent(lore_context: str, previous_chapters: str) -> Agent:
    """
    Creates the ADK Agent that acts as a Developmental Editor for Ink Studio.
    The book's context is injected directly into the instruction to avoid DB context issues.
    """
    return Agent(
        model="gemini-2.0-flash",
        name="developmental_editor",
        description="A professional developmental editor that critiques chapter pacing, character arcs, and consistency.",
        instruction=f"""
        You are a New York Times bestselling developmental editor.
        Your job is to read the CURRENT DRAFT of a chapter provided by the author and provide professional critique.
        
        BOOK LORE:
        {lore_context}
        
        PREVIOUS CHAPTERS:
        {previous_chapters}
        
        YOUR TASK:
        - Do NOT rewrite the text for the author.
        - Critique pacing. Is the chapter moving too fast or too slow?
        - Highlight 'show don't tell' violations.
        - Analyze character consistency based on the lore and previous chapters.
        - Provide extreme encouragement while being structurally strict.
        
        Format your response directly in markdown. DO NOT output JSON. Output your critique clearly with headers.
        """
    )

def create_brainstormer_agent(lore_context: str) -> Agent:
    """
    Creates an ADK Agent to brainstorm plot twists or solve writer's block instantly.
    """
    return Agent(
        model="gemini-2.0-flash",
        name="creative_brainstormer",
        description="A hyper-creative brainstorming engine to resolve narrative dead-ends.",
        instruction=f"""
        You are an elite creative brainstorming engine.
        
        BOOK LORE:
        {lore_context}
        
        YOUR TASK:
        - Read the narrative roadblock the author provides.
        - Suggest 3 scientifically/logically accurate plot twists or resolutions based on the established lore.
        - Be highly creative but keep the tone matching the Genre.
        
        Format your response in markdown. Use bullet points for the 3 distinct ideas.
        """
    )

def create_auto_publicist_agent(book_text_compiled: str, genre: str) -> Agent:
    """
    Creates the Agent responsible for writing the Investment Campaign pitch.
    Instead of google search (to keep it fast for now), we use pure Gemini reasoning.
    """
    return Agent(
        model="gemini-2.0-flash",  # Upgrade to gemini-1.5-pro for huge books in production
        name="auto_publicist",
        description="An elite publicist that writes viral investment campaign pitches for debut authors.",
        instruction=f"""
        You are an elite publishing publicist whose job is to raise investment capital for debut authors.
        
        You are about to read the compiled draft of an unfinished book.
        
        YOUR TASK:
        - Write the marketing copy for their Investment Campaign Page.
        - Section 1: "The Hook" (1 sentence logline that is guaranteed to sell)
        - Section 2: "The Synopsis" (2 paragraphs max)
        - Section 3: "Why Investors Should Fund This" (Highlight the genre {genre} and explain why this manuscript has massive market potential).
        
        Keep it highly persuasive and professional. Format in markdown.
        """
    )

def create_marketing_agent(book_text_compiled: str, genre: str) -> Agent:
    """
    Agent responsible for generating the final sales metadata (Synopsis, Tagline, Tags) for the marketplace.
    """
    return Agent(
        model="gemini-2.0-flash",
        name="marketing_manager",
        description="A Chief Marketing Officer that generates explosive metadata for book launches.",
        instruction=f"""
        You are the Chief Marketing Officer at a top-tier book publishing company.
        You have been handed the finalized manuscript of a new {genre} book.
        Your job is to read the compiled text (or summaries) and return a dynamic markdown payload containing:
        1. "TAGLINE": A short, punchy tagline (1 sentence).
        2. "SYNOPSIS": A compelling synopsis for the back cover or marketplace page (2 paragraphs).
        3. "TAGS": A Comma separated list of 5 SEO-optimized tags.

        Here is the manuscript context:
        {book_text_compiled}
        """
    )


def create_media_publicist_agent(
    book_title: str,
    book_text_compiled: str,
    genre: str,
    author_name: str = "the author",
) -> Agent:
    """
    Generates launch publicity materials: press release, interview prep, feature pitches.
    """
    return Agent(
        model="gemini-2.0-flash",
        name="media_publicist",
        description="Publicity specialist for press releases, interviews, and book reviews outreach.",
        instruction=f"""
        You are a senior publicity director at a major publisher launching "{book_title}" ({genre}) by {author_name}.

        Use this manuscript context:
        {book_text_compiled}

        Return professional markdown with these exact section headers:

        ## Press release
        (400–600 words, ready for media distribution: dateline, headline, lead, quotes placeholder for author, boilerplate about Ndotonic/Ink Studio imprint)

        ## Media pitch email
        (Short email to journalists/bloggers pitching coverage)

        ## Author interview guide
        (10 talking points + 5 suggested Q&A pairs for TV, radio, or podcast interviews)

        ## Feature article angles
        (3 distinct angles freelancers or bloggers could write, with suggested headlines)

        ## Book review outreach
        (2-paragraph note to reviewers/critics explaining why the book merits attention)

        Be factual to the manuscript; do not invent plot spoilers beyond the context provided.
        """
    )
