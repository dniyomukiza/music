import json
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

from glconnect.models import db
from glconnect.book_platform_models import BookProject, BookChapter, BookPlatformUser
from glconnect.book_agent import (
    fetch_book_context,
    create_developmental_editor_agent,
    create_brainstormer_agent,
    create_auto_publicist_agent,
    create_marketing_agent,
    create_media_publicist_agent,
)

book_agents_bp = Blueprint('book_agents', __name__)

def verify_book_access(book_id):
    """Ensure the user actually owns this book."""
    book = BookProject.query.get_or_404(book_id)
    profile = BookPlatformUser.query.filter_by(user_id=current_user.user_id).first()
    if not profile or book.author_id != profile.id:
        return None
    return book

@book_agents_bp.route('/<int:book_id>/critique', methods=['POST'])
@login_required
def agent_critique(book_id):
    """
    Acts as the Developmental Editor.
    Accepts the current draft text from the frontend and returns markdown critique.
    """
    book = verify_book_access(book_id)
    if not book:
        return jsonify({"error": "Unauthorized or book not found"}), 403
        
    data = request.json
    current_chapter_text = data.get('text', '')
    
    if not current_chapter_text.strip():
        return jsonify({"error": "No text provided"}), 400
        
    # 1. Fetch entire lore context natively from DB
    context = fetch_book_context(book_id)
    if "error" in context:
        return jsonify(context), 404
        
    # 2. Instantiate ADK Agent with baked-in context
    editor_agent = create_developmental_editor_agent(
        lore_context=context['lore'],
        previous_chapters=context['previous_chapters_summary']
    )
    
    # 3. Execute ADK Agent
    session_service = InMemorySessionService()
    runner = Runner(app_name="book_agents", agent=editor_agent, session_service=session_service)
    message = Content(role="user", parts=[Part(text=current_chapter_text)])
    
    import asyncio
    async def run_critique():
        session = await session_service.create_session(app_name="book_agents", user_id=str(current_user.user_id))
        final_output = ""
        async for chunk in runner.run_async(user_id=str(current_user.user_id), session_id=session.id, new_message=message):
            if hasattr(chunk, 'content') and chunk.content and hasattr(chunk.content, 'parts') and chunk.content.parts:
                if chunk.content.parts[0].text:
                    final_output += chunk.content.parts[0].text
        return final_output
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        final_output = loop.run_until_complete(run_critique())
    finally:
        loop.close()
    
    return jsonify({
        "success": True,
        "critique": final_output
    })

@book_agents_bp.route('/<int:book_id>/brainstorm', methods=['POST'])
@login_required
def agent_brainstorm(book_id):
    """
    Acts as the Ideation/Brainstormer agent.
    Accepts a prompt/roadblock and returns creative solutions based on lore.
    """
    book = verify_book_access(book_id)
    if not book:
        return jsonify({"error": "Unauthorized or book not found"}), 403
        
    data = request.json
    roadblock_prompt = data.get('prompt', '')
    
    if not roadblock_prompt.strip():
        return jsonify({"error": "No prompt provided"}), 400
        
    context = fetch_book_context(book_id)
    
    # Instantiate ADK Brainstormer
    brainstormer = create_brainstormer_agent(lore_context=context.get('lore', ''))
    
    session_service = InMemorySessionService()
    runner = Runner(app_name="book_agents", agent=brainstormer, session_service=session_service)
    message = Content(role="user", parts=[Part(text=roadblock_prompt)])
    
    import asyncio
    async def run_brainstorm():
        session = await session_service.create_session(app_name="book_agents", user_id=str(current_user.user_id))
        final_output = ""
        async for chunk in runner.run_async(user_id=str(current_user.user_id), session_id=session.id, new_message=message):
            if hasattr(chunk, 'content') and chunk.content and hasattr(chunk.content, 'parts') and chunk.content.parts:
                if chunk.content.parts[0].text:
                    final_output += chunk.content.parts[0].text
        return final_output
        
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        final_output = loop.run_until_complete(run_brainstorm())
    finally:
        loop.close()
    
    return jsonify({
        "success": True,
        "ideas": final_output
    })
    
@book_agents_bp.route('/<int:book_id>/pitch', methods=['POST'])
@login_required
def agent_pitch(book_id):
    """
    Acts as the Auto-Publicist.
    Reads the entire book and generates a viral pitch for the Investment Campaign block.
    """
    book = verify_book_access(book_id)
    if not book:
        return jsonify({"error": "Unauthorized or book not found"}), 403
        
    # Grab context (simulating reading the full book via summaries for now to save tokens natively)
    context = fetch_book_context(book_id)
    compiled_text = context.get('previous_chapters_summary', '')
    
    if not compiled_text:
        return jsonify({"error": "Not enough chapters written to generate a pitch"}), 400
        
    publicist = create_auto_publicist_agent(
        book_text_compiled=compiled_text,
        genre=book.genre or "Fiction"
    )
    
    session_service = InMemorySessionService()
    runner = Runner(app_name="book_agents", agent=publicist, session_service=session_service)
    
    prompt_text = "Please write the investment campaign pitch based on the manuscript context you have. Include a Hook, Synopsis, and Why Investors Should Fund This."
    message = Content(role="user", parts=[Part(text=prompt_text)])
    
    import asyncio
    async def run_pitch():
        session = await session_service.create_session(app_name="book_agents", user_id=str(current_user.user_id))
        final_output = ""
        async for chunk in runner.run_async(user_id=str(current_user.user_id), session_id=session.id, new_message=message):
            if hasattr(chunk, 'content') and chunk.content and hasattr(chunk.content, 'parts') and chunk.content.parts:
                if chunk.content.parts[0].text:
                    final_output += chunk.content.parts[0].text
        return final_output
        
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        final_output = loop.run_until_complete(run_pitch())
    finally:
        loop.close()
    
    return jsonify({
        "success": True,
        "pitch": final_output
    })

@book_agents_bp.route('/<int:book_id>/marketing', methods=['POST'])
@login_required
def agent_marketing(book_id):
    """
    Called by AI Publishing House to generate final metadata (Synopsis, Tagline, Tags).
    """
    book = verify_book_access(book_id)
    if not book:
        return jsonify({"error": "Unauthorized"}), 403
        
    context = fetch_book_context(book_id)
    compiled_text = context.get('previous_chapters_summary', '')
    
    marketing_agent = create_marketing_agent(
        book_text_compiled=compiled_text,
        genre=book.genre or "Fiction"
    )
    
    session_service = InMemorySessionService()
    runner = Runner(app_name="book_agents", agent=marketing_agent, session_service=session_service)
    message = Content(role="user", parts=[Part(text="Generate the final marketing metadata including Synopsis, Tagline, and comma-separated Tags.")])
    
    import asyncio
    async def run_marketing():
        session = await session_service.create_session(app_name="book_agents", user_id=str(current_user.user_id))
        final_output = ""
        async for chunk in runner.run_async(user_id=str(current_user.user_id), session_id=session.id, new_message=message):
            if hasattr(chunk, 'content') and chunk.content and hasattr(chunk.content, 'parts') and chunk.content.parts:
                if chunk.content.parts[0].text:
                    final_output += chunk.content.parts[0].text
        return final_output
        
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        final_output = loop.run_until_complete(run_marketing())
    finally:
        loop.close()
        
    return jsonify({
        "success": True,
        "marketing_copy": final_output
    })


@book_agents_bp.route('/<int:book_id>/publicity', methods=['POST'])
@login_required
def agent_publicity(book_id):
    """Press kit: press release, interview guide, feature angles, review outreach."""
    book = verify_book_access(book_id)
    if not book:
        return jsonify({"error": "Unauthorized or book not found"}), 403

    context = fetch_book_context(book_id)
    compiled_text = context.get('previous_chapters_summary', '') or context.get('lore', '')
    if not compiled_text.strip():
        return jsonify({"error": "Not enough manuscript content to generate publicity materials"}), 400

    author_name = "the author"
    if book.author:
        if getattr(book.author, 'pen_name', None):
            author_name = book.author.pen_name
        elif getattr(book.author, 'username', None):
            author_name = book.author.username

    publicist = create_media_publicist_agent(
        book_title=book.title or "Untitled",
        book_text_compiled=compiled_text,
        genre=book.genre or "Fiction",
        author_name=author_name,
    )

    session_service = InMemorySessionService()
    runner = Runner(app_name="book_agents", agent=publicist, session_service=session_service)
    message = Content(
        role="user",
        parts=[Part(text="Generate the full publicity press kit with all sections.")],
    )

    import asyncio

    async def run_publicity():
        session = await session_service.create_session(
            app_name="book_agents", user_id=str(current_user.user_id)
        )
        final_output = ""
        async for chunk in runner.run_async(
            user_id=str(current_user.user_id),
            session_id=session.id,
            new_message=message,
        ):
            if (
                hasattr(chunk, 'content')
                and chunk.content
                and hasattr(chunk.content, 'parts')
                and chunk.content.parts
                and chunk.content.parts[0].text
            ):
                final_output += chunk.content.parts[0].text
        return final_output

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        final_output = loop.run_until_complete(run_publicity())
    finally:
        loop.close()

    return jsonify({"success": True, "publicity_kit": final_output})
