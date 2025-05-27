# logic.py

import os
import pandas as pd
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from langchain_core.messages import SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

# ✅ Load credentials from .env file
load_dotenv()

SPOTIPY_CLIENT_ID = os.environ.get("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = os.environ.get("SPOTIPY_CLIENT_SECRET")
SPOTIPY_REDIRECT_URI = os.environ.get("SPOTIPY_REDIRECT_URI")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

scope = "user-top-read user-library-read user-read-recently-played"

def connect_spotify():
    return spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=SPOTIPY_CLIENT_ID,
        client_secret=SPOTIPY_CLIENT_SECRET,
        redirect_uri=SPOTIPY_REDIRECT_URI,
        scope=scope
    ))

def extract_track_info(tracks, source, weight, wrap_in_track_key=False):
    return [
        {
            "track_id": item["track"]["id"] if wrap_in_track_key else item["id"],
            "track_name": item["track"]["name"] if wrap_in_track_key else item["name"],
            "artists": ", ".join(artist["name"] for artist in (item["track"]["artists"] if wrap_in_track_key else item["artists"])),
            "weight": weight,
            "source": source
        } for item in tracks
    ]


def fetch_all_spotify_data(sp):
    all_data = []
    all_data += extract_track_info(sp.current_user_top_tracks(limit=50)["items"], "top", 1.0, wrap_in_track_key=False)
    all_data += extract_track_info(sp.current_user_saved_tracks(limit=50)["items"], "liked", 0.8, wrap_in_track_key=True)
    all_data += extract_track_info(sp.current_user_recently_played(limit=50)["items"], "recent", 0.7, wrap_in_track_key=True)
    return pd.DataFrame(all_data)

def deduplicate_and_weight(df):
    df = df.groupby(['track_id', 'track_name', 'artists']).agg({
        'weight': 'sum',
        'source': lambda x: ', '.join(sorted(set(x)))
    }).reset_index()
    return df

def build_music_prompt(df):
    df = df.sort_values("weight", ascending=False)
    song_entries = [
        f'"{row.track_name}" by {row.artists} [Weight: {row.weight:.2f}, Source: {row.source}]'
        for _, row in df.iterrows()
    ]
    song_list = "\n".join(f"- {entry}" for entry in song_entries)

    personality_traits = """
Analyze the user's personality based on the following list of songs.

Each song entry includes:
- **Track Name** and **Artist Name** → Infer emotional tone, genre, mood, lyrical themes, and musical style from these — as understood from your general knowledge of music and pop culture.
- **Weight** → Representing how strongly the user identifies with it or how frequently it is played
- **Source** → Indicates where the song came from in the app (e.g., "Liked", "Recent", or "Top Tracks").

📌 Prioritize traits based on listening weight.
🎧 Interpret songs with awareness of artist style and emotional/genre cues.
📈 Use source context to understand depth of user connection (e.g., “Liked” is stronger than “Recently Played”).

Return only a **percentage breakdown** of the user’s most dominant personality traits (summing to 100%). Focus on **accuracy over coverage** (max 6 traits). Do not include extra text or analysis.

🎭 EMOTIONAL CORE
🌞 Happy-go-vibey, 💔 Old-School Romantic, 🫥 Melancholic Thinker, 🔥 Passion Pusher

🚀 AMBITION & ENERGY
💪 Motivated Maverick, 🎯 Determined Hustler, 🧘 Zen Seeker, 🎨 ArtSoul Explorer

🧑‍🤝‍🧑 SOCIAL STYLE
🕺 Party Starter, 🚗 Roadtrip Junkie, 🐺 Lone Wolf, 💃 Drama Enthusiast

🌍 WORLDVIEW & LIFESTYLE
✈️ Wanderlust Dreamer, 🧠 Deep Diver, 🏞️ Nature Chiller, 🎮 Digital Escapist

Optional (only if clearly supported by music):
🐉 Fantasy Head, 🪩 Retro Rider, 🧃 Chillwave Surfer
"""

    # Final full prompt
    prompt = f"""
The user listens to the following songs:

{song_list}

{personality_traits}

🎯 Return output ONLY in this strict format (nothing else):
🎧 Trait Name: XX%
🎧 Trait Name: XX%
🎧 Trait Name: XX%
🎧 Trait Name: XX%
🎧 Trait Name: XX%
🎧 Trait Name: XX%

❌ Do NOT include any explanations, analysis, lists, bullet points, or extra text — only the percentage breakdown in the exact above structure.
"""
    return prompt.strip(), song_list

def get_personality_traits(prompt):
    model = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=GEMINI_API_KEY, temperature=0.6)
    return model.invoke(prompt)

def setup_conversational_chain(trait_summary, song_list):
    system_prompt = f"""
You are a funny, personality-aware assistant who understands users through their music taste.

🎯 User's Musical Context:
- 🧠 Personality Profile: {trait_summary}
- 🎷 Top Songs & Artists: {song_list}

Each song entry includes:
- **Track Name** and **Artist Name** → Infer emotional tone, genre, mood, lyrical themes, and musical style from these.
- **Weight** → Represents how strongly the user identifies with it.
- **Source** → Indicates app context (e.g., "Liked", "Top", etc.).

🛠️ Your Job:
1. **Analyze the user's personality** based on their music taste, creating a mental profile.
2. **Answer funny and creative questions** about their personality based *solely* on this inferred profile. The answers should be creative and **must not directly mention specific songs, artists, or musical data** provided.
3. Help with dating prompts based on their vibe.
4. Be funny, smart, insightful, and refer to the *inferred personality* to curate answers.

⚠️ Important Instructions:
1. Questions can be about any topic. Use the inferred personality profile to answer without referring back to the music data.
2. Keep answers strictly one-liners.
3. Do not provide explanations, bullet points, tables, comments, or justifications.
4. Only answer when the user asks a question. Do not respond to this initial prompt.
5. Ensure the answer aligns with the user's inferred personality.
6. Be multi-faceted and insightful. Avoid any song references in your responses.
"""

    memory = ConversationBufferMemory()
    memory.chat_memory.add_message(SystemMessage(content=system_prompt))

    chain = ConversationChain(
        llm=ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=GEMINI_API_KEY, temperature=0.6),
        memory=memory,
        verbose=True
    )
    return chain
