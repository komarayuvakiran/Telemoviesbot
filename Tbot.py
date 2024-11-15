import telebot
import requests
from telebot.types import Message
import json
import time
import os
import sys
from collections import defaultdict

# Replace with your tokens
TELEGRAM_BOT_TOKEN = "8025436337:AAHHZrAi6lmLZFmrhF5p9VdGs5U8gkJmCSM"
TMDB_API_KEY = "53ea700a6725bc9ce833cea89426c7c8"

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Memory to store user searches and search limits
user_memory = {}
search_limit = defaultdict(list)  # Tracks user search timestamps

WELCOME_MESSAGE = (
    "🎬 *Welcome to the HD Movies Bot! 🎥*\n\n"
    "Easily stream or download your favorite HD movies in just a few clicks!\n\n"
    "🎞 *How to Use:*\n"
    "1️⃣ Search for your movie or browse the latest uploads.\n"
    "2️⃣ Click the link to start streaming or downloading.\n"
    "3️⃣ Enjoy your movie experience hassle-free!\n\n"
    "💡 *If a server isn’t working:*\n"
    "Don't worry! Simply try another server option provided in the list.\n\n"
    "📩 Need help or have suggestions? Contact the developer: @mrottseller\n\n"
    "🌟 Enjoy seamless entertainment anytime, anywhere!"
    "🌟 To Search movies use /search example:/search iron man , /search bat man , /search venom"
    
)


@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, WELCOME_MESSAGE, parse_mode="Markdown")

@bot.message_handler(commands=['search'])
def search_movie_tv(message):
    user_id = message.chat.id

    # Enforce rate limiting
    current_time = time.time()
    search_limit[user_id] = [
        ts for ts in search_limit[user_id] if current_time - ts < 10
    ]

    if len(search_limit[user_id]) >= 8:
        bot.reply_to(
            message,
            "🚨 *Rate Limit Exceeded!*\nYou can only make 8 search requests every 10 seconds. Please wait and try again.",
            parse_mode="Markdown"
        )
        return

    # Add timestamp for current search
    search_limit[user_id].append(current_time)

    try:
        query = message.text.split(' ', 1)[1]
    except IndexError:
        bot.reply_to(
            message,
            "🚨 *Please provide a movie or TV show name.*\n"
            "Example: `/search Interstellar`",
            parse_mode="Markdown"
        )
        return

    # Perform search
    search_results = search_tmdb(query)

    if not search_results:
        bot.reply_to(
            message,
            "⚠️ *No results found. Please check your query or try a different search.*",
            parse_mode="Markdown"
        )
        return

    # Store search results in memory for the user
    user_memory[user_id] = {
        'query': query,
        'results': search_results
    }

    # Send search results with numbering
    response = "🎥 *Search Results:*\n"
    for idx, result in enumerate(search_results[:5], 1):  # Show top 5 results
        title = result.get('title') or result.get('name')
        media_type = "Movie" if result.get('title') else "TV Show"
        response += f"{idx}. *{title}* ({media_type})\n"

    response += "\n*Reply with the number to get more details.*"
    bot.reply_to(message, response, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text.isdigit())
def handle_number_response(message):
    user_id = message.chat.id

    if user_id not in user_memory or 'results' not in user_memory[user_id]:
        bot.reply_to(
            message,
            "⚠️ *Please perform a search first using the /search command.*",
            parse_mode="Markdown"
        )
        return

    # Retrieve the user's search results from memory
    search_results = user_memory[user_id]['results']
    query = user_memory[user_id]['query']
    
    # Convert message text to integer (the movie number)
    selected_number = int(message.text)

    if selected_number < 1 or selected_number > len(search_results):
        bot.reply_to(
            message,
            "🚨 *Invalid number. Please choose a number between 1 and 5.*",
            parse_mode="Markdown"
        )
        return

    # Get the selected movie or TV show's details
    selected_item = search_results[selected_number - 1]
    item_details = fetch_item_details(selected_item)

    # Send the item details to the user
    if item_details:
        image_url = f"https://image.tmdb.org/t/p/w500{selected_item.get('poster_path')}"
        if image_url:
            try:
                bot.send_photo(
                    message.chat.id,
                    image_url,
                    caption=item_details,
                    parse_mode="Markdown"
                )
            except Exception as e:
                bot.send_message(
                    message.chat.id,
                    f"⚠️ *Error sending image:* {str(e)}. Here are the details without the image.",
                    parse_mode="Markdown"
                )
                bot.send_message(message.chat.id, item_details, parse_mode="Markdown")
        else:
            bot.send_message(
                message.chat.id,
                item_details,
                parse_mode="Markdown"
            )
    else:
        bot.send_message(
            message.chat.id,
            "⚠️ *Sorry, we couldn't fetch details for this item right now.*",
            parse_mode="Markdown"
        )

@bot.message_handler(commands=['developer'])
def send_developer_info(message):
    bot.reply_to(
        message,
        "👨‍💻 *Developer Information:*\n\n"
        "This bot was developed by *Komara Yuvakiran*.\n\n"
        "For any issues or questions, you can contact me at @mrottseller.",
        parse_mode="Markdown"
    )

def search_tmdb(query):
    try:
        # Search movies and TV shows on TMDB
        movie_results = requests.get(
            f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={query}&language=en-US",
            timeout=10
        ).json()
        tv_results = requests.get(
            f"https://api.themoviedb.org/3/search/tv?api_key={TMDB_API_KEY}&query={query}&language=en-US",
            timeout=10
        ).json()

        return movie_results.get('results', []) + tv_results.get('results', [])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching TMDB results: {e}")
        return None

def fetch_item_details(item):
    try:
        item_id = item.get('id')
        media_type = 'movie' if item.get('title') else 'tv'

        # Fetch item details (movie or TV show)
        item_details = requests.get(
            f"https://api.themoviedb.org/3/{media_type}/{item_id}?api_key={TMDB_API_KEY}&language=en-US",
            timeout=10
        ).json()

        title = item_details.get('title') or item_details.get('name')
        overview = item_details.get('overview', 'No overview available.')
        genres = ", ".join([genre['name'] for genre in item_details.get('genres', [])])
        release_date = item_details.get('release_date') or item_details.get('first_air_date', 'Not Available')

        # Generate watch links
        watch_links = generate_embed_urls(item_id)

        response = f"🎬 *{title}*\n"
        response += "📖 *Overview:*\n"
        response += f"• {overview[:150]}...\n"  # Shortened overview
        response += f"• *Genres:* {genres}\n"
        response += f"• *Release Date:* {release_date}\n\n"
        response += f"🚀 *Watch Now:*\n"
        for i, url in enumerate(watch_links.values(), 1):
            response += f"🔗 *Server {i}:* [Watch Now]({url})\n"
        
        return response
    except Exception as e:
        print(f"Error fetching item details: {e}")
        return None

def generate_embed_urls(item_id):
    return {
        "tmdb": f"https://embed.su/embed/movie/{item_id}",
        "autoembed": f"https://autoembed.co/movie/tmdb/{item_id}",
        "multiembed": f"https://multiembed.mov/directstream.php?video_id={item_id}&tmdb=1",
        "vidsrc": f"https://vidsrc.xyz/embed/movie?tmdb={item_id}"
    }

# Auto-restart functionality
while True:
    try:
        bot.polling()
    except Exception as e:
        print(f"Bot stopped due to error: {e}. Restarting...")
        time.sleep(5)  # Wait 5 seconds before restarting
        os.execv(sys.executable, ['python3'] + sys.argv)  # Restart the bot
