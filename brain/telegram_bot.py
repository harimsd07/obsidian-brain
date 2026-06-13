"""
Telegram bot integration for Obsidian Brain.
Allows querying your vault via Telegram with source citations.
"""

import logging
from typing import Optional
from telegram import Update, Chat
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ContextTypes,
    filters, ConversationHandler, CallbackQueryHandler
)
from telegram.constants import ParseMode, ChatAction

from brain import db
from brain.config import VAULT_PATH, HYBRID_SEARCH
from brain.exceptions import VaultNotIndexed
from brain.retriever import retrieve, build_context
from brain.llm import generate

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# State constants
# ──────────────────────────────────────────────────────────────────────────────

WAITING_FOR_QUERY = 1


# ──────────────────────────────────────────────────────────────────────────────
# Command handlers
# ──────────────────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start command - show help"""
    user = update.effective_user
    help_text = """🧠 *Obsidian Brain Bot*

I can search and answer questions about your Obsidian vault.

*Commands:*
/help — show this message
/ask — ask a question about your notes
/search — search for notes
/stats — view vault statistics
/cancel — stop current operation

Just type your question after /ask or /search!"""
    
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Help command"""
    help_text = """🧠 *Obsidian Brain Bot*

*How to use:*

1. `/ask` — I'll answer questions using your notes
   Example: `/ask What is RAG?`

2. `/search` — Find relevant notes
   Example: `/search machine learning`

3. `/stats` — See vault statistics

*Features:*
• Semantic search across all your notes
• LLM-generated answers with reasoning
• Source citations for transparency
• Hybrid search (semantic + keyword)

*Pro tip:* Type `/ask Your question here` in a single message for fastest response."""
    
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)


async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ask command - ask a question"""
    # Get the question from the message
    text = update.message.text
    
    # Extract question (everything after /ask)
    if text.startswith("/ask "):
        question = text[5:].strip()
        if question:
            # Directly answer the question
            await _answer_question(update, context, question)
            return ConversationHandler.END
    
    # If no question provided, ask for one
    await update.message.reply_text(
        "❓ What would you like to know about your notes?",
        parse_mode=ParseMode.MARKDOWN
    )
    return WAITING_FOR_QUERY


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Search command - search for notes"""
    text = update.message.text
    
    # Extract query (everything after /search)
    if text.startswith("/search "):
        query = text[8:].strip()
        if query:
            # Directly search
            await _search_notes(update, context, query)
            return ConversationHandler.END
    
    # If no query provided, ask for one
    await update.message.reply_text(
        "🔍 What would you like to search for?",
        parse_mode=ParseMode.MARKDOWN
    )
    return WAITING_FOR_QUERY


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Stats command - show vault statistics"""
    try:
        stats = db.collection_stats()
        
        stats_text = f"""📊 *Vault Statistics*

• *Location:* `{VAULT_PATH}`
• *Indexed Chunks:* {stats['total_chunks']}
• *Hybrid Search:* {'✓ Enabled' if HYBRID_SEARCH else '✗ Disabled'}

Use /ask or /search to query your vault!"""
        
        await update.message.reply_text(stats_text, parse_mode=ParseMode.MARKDOWN)
    except VaultNotIndexed:
        await update.message.reply_text(
            "❌ Vault not indexed. Run `brain ingest` first.",
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        await update.message.reply_text(
            f"❌ Error: {str(e)}",
            parse_mode=ParseMode.MARKDOWN
        )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel conversation"""
    await update.message.reply_text(
        "❌ Cancelled.",
        parse_mode=ParseMode.MARKDOWN
    )
    return ConversationHandler.END


# ──────────────────────────────────────────────────────────────────────────────
# Helper functions
# ──────────────────────────────────────────────────────────────────────────────

async def _answer_question(
    update: Update, 
    context: ContextTypes.DEFAULT_TYPE, 
    question: str
) -> None:
    """Answer a question using vault notes"""
    try:
        # Show "typing" indicator
        await update.message.chat.send_action(ChatAction.TYPING)
        
        stats = db.collection_stats()
        if stats["total_chunks"] == 0:
            raise VaultNotIndexed()
        
        # Retrieve relevant chunks
        chunks = retrieve(question, n=5, hybrid=HYBRID_SEARCH)
        
        if not chunks:
            await update.message.reply_text(
                "❌ No relevant notes found for your question.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Build context and get answer
        context_text = build_context(chunks)
        sources = list(dict.fromkeys(
            f"{c.note_title}" for c in chunks
        ))
        
        system_prompt = """You are a helpful assistant with access to the user's Obsidian notes.
Answer using ONLY the provided notes. Be concise (under 500 words).
If notes don't contain enough information, say so.
Format your answer clearly with bullet points where appropriate."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"Notes:\n\n{context_text}\n\nQuestion: {question}"
            }
        ]
        
        # Show "typing" while generating
        await update.message.chat.send_action(ChatAction.TYPING)
        
        # Collect LLM response
        answer = ""
        for delta in generate(messages, stream=True):
            answer += delta
        
        # Format answer with sources
        source_text = "\n".join(f"• {s}" for s in sources)
        
        final_answer = f"""📚 *Answer*

{answer.strip()}

*Sources:*
{source_text}"""
        
        # Split long messages (Telegram limit: 4096 chars)
        if len(final_answer) > 4000:
            # Send answer first
            await update.message.reply_text(
                answer.strip(),
                parse_mode=ParseMode.MARKDOWN
            )
            # Then send sources
            await update.message.reply_text(
                f"*Sources:*\n{source_text}",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(
                final_answer,
                parse_mode=ParseMode.MARKDOWN
            )
    
    except VaultNotIndexed:
        await update.message.reply_text(
            "❌ Vault not indexed. Run `brain ingest` first.",
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        logger.error(f"Error answering question: {e}")
        await update.message.reply_text(
            f"❌ Error: {str(e)}",
            parse_mode=ParseMode.MARKDOWN
        )


async def _search_notes(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    query: str
) -> None:
    """Search for notes in the vault"""
    try:
        # Show "typing" indicator
        await update.message.chat.send_action(ChatAction.TYPING)
        
        stats = db.collection_stats()
        if stats["total_chunks"] == 0:
            raise VaultNotIndexed()
        
        # Perform search
        chunks = retrieve(query, n=5, hybrid=HYBRID_SEARCH)
        
        if not chunks:
            await update.message.reply_text(
                "❌ No notes found matching your search.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Build search results
        results = []
        for i, chunk in enumerate(chunks, 1):
            snippet = chunk.text[:150] + "..." if len(chunk.text) > 150 else chunk.text
            result = f"{i}. *{chunk.note_title}*"
            if chunk.heading and chunk.heading != "":
                result += f" › {chunk.heading}"
            result += f"\n__{snippet}__\n"
            results.append(result)
        
        search_results = "🔍 *Search Results*\n\n" + "".join(results)
        
        # Split if too long
        if len(search_results) > 4000:
            chunks_to_send = []
            current = "🔍 *Search Results*\n\n"
            for result in results:
                if len(current) + len(result) > 4000:
                    chunks_to_send.append(current)
                    current = result
                else:
                    current += result
            if current:
                chunks_to_send.append(current)
            
            for chunk in chunks_to_send:
                await update.message.reply_text(
                    chunk,
                    parse_mode=ParseMode.MARKDOWN
                )
        else:
            await update.message.reply_text(
                search_results,
                parse_mode=ParseMode.MARKDOWN
            )
    
    except VaultNotIndexed:
        await update.message.reply_text(
            "❌ Vault not indexed. Run `brain ingest` first.",
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        logger.error(f"Error searching notes: {e}")
        await update.message.reply_text(
            f"❌ Error: {str(e)}",
            parse_mode=ParseMode.MARKDOWN
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle text messages in conversation"""
    text = update.message.text
    
    # Check which conversation state we're in
    if "ask" in context.user_data.get("mode", ""):
        await _answer_question(update, context, text)
    elif "search" in context.user_data.get("mode", ""):
        await _search_notes(update, context, text)
    else:
        # Default: treat as question
        await _answer_question(update, context, text)
    
    return ConversationHandler.END


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors caused by updates"""
    logger.error(f"Update {update} caused error {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ An error occurred. Please try again.",
            parse_mode=ParseMode.MARKDOWN
        )


# ──────────────────────────────────────────────────────────────────────────────
# Bot startup
# ──────────────────────────────────────────────────────────────────────────────

async def run_bot(token: str) -> None:
    """Run the Telegram bot"""
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN not set. Get one from @BotFather on Telegram.")
    
    # Create the Application
    application = Application.builder().token(token).build()
    
    # Add conversation handler
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("ask", ask_command),
            CommandHandler("search", search_command),
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message),
        ],
        states={
            WAITING_FOR_QUERY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(conv_handler)
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Start the bot
    print("🤖 Obsidian Brain Telegram bot running...")
    print("   Send /help to see available commands")
    await application.run_polling(allowed_updates=Update.ALL_TYPES)


def run(token: Optional[str] = None) -> None:
    """Run the Telegram bot (blocking)"""
    import asyncio
    from brain.config import TELEGRAM_BOT_TOKEN
    
    bot_token = token or TELEGRAM_BOT_TOKEN
    if not bot_token:
        raise ValueError(
            "Telegram bot token not found.\n"
            "Set TELEGRAM_BOT_TOKEN in .env or pass --token flag."
        )
    
    # Configure logging
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    
    asyncio.run(run_bot(bot_token))


if __name__ == "__main__":
    run()
