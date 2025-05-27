import streamlit as st
from logic import (
    connect_spotify,
    fetch_all_spotify_data,
    deduplicate_and_weight,
    build_music_prompt,
    get_personality_traits,
    setup_conversational_chain
)
import time

PROJECT_NAME = "AI Personality Mirror"
st.set_page_config(page_title=PROJECT_NAME, layout="wide")

# --- Styling ---
st.markdown(f"""
    <style>
        body {{
            background-color: #121212;
            color: #f0f0f0;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
        }}
        .navbar {{
            background-color: #673ab7;;
            color: #f0f0f0;
            padding: 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .navbar-left {{
            font-size: 22.5px;
            font-weight: bold;
        }}
        .navbar-right {{
            list-style: none;
            padding: 0;
            margin: 0;
            display: flex;
            gap: 5px;
        }}
        .navbar-right a {{
            color: #f0f0f0;
            text-decoration: none;
            cursor: pointer;
        }}
        .navbar-right a:hover {{
            color: #bb86fc;
        }}
        .techy-text {{
            font-family: 'Courier New', monospace;
            font-size: 5em; !important
            color: #00ff99;
            text-shadow: 0 0 5px #00ff99;
            margin-bottom: 0.5em;
            text-align: center; !important
        }}
        .subtitle-text {{
            font-size: 1.1em;
            color: #90caf9;
            margin-bottom: 1.5em;
            text-align: center;
        }}
        .connect-button-container {{
            margin-top: 2em;
        }}
        .stButton>button {{
            background-color: #1DB954;
            color: black !important;
            border-radius: 15px;
            padding: 0.2em 0.9em !important;
            font size: 1px;
            font-weight: bold;
            border: none;
            transition: background-color 0.3s ease;
            
        }}
        .stButton>button:hover {{
            background-color: #7e57c2;
        }}
        hr.separator {{
            border-top: 1px solid #333;
            margin: 2em 0;
        }}
        .how-it-works-section {{
            padding: 2em;
        }}
        .how-it-works-expander .stExpander>div[data-baseweb="expandable"]>div[data-testid="stMarkdownContainer"] > p {{
            font-size: 0.9em;
            line-height: 1.6;
            color: #d0d0d0;
        }}
        .modal-container {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.5);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 1000;
        }}
        .modal-content {{
            background-color: #1e1e1e;
            padding: 2em;
            border-radius: 10px;
            color: #f0f0f0;
            position: relative;
        }}
        .modal-close-button {{
            position: absolute;
            top: 0.5em;
            right: 0.5em;
            background: none;
            border: none;
            color: #f0f0f0;
            font-size: 1.2em;
            cursor: pointer;
        }}
        .copy-url-button {{
            background-color: #5e35b1;
            color: white;
            border: none;
            padding: 0.7em 1.5em;
            border-radius: 8px;
            cursor: pointer;
            margin-top: 1em;
        }}
        .copy-url-button:hover {{
            background-color: #7e57c2;
        }}
        .url-display {{
            margin-bottom: 1em;
            word-break: break-all;
        }}
        .personality-trait-container {{
            background-color: #1e1e1e;
            padding: 1em;
            border-radius: 12px;
            margin-bottom: 0.8em;
        }}
        .trait-name {{
            color: #1DB954;
            font-weight: bold;
            margin-right: 0.5em;
        }}
        .progress-bar {{
            background-color: #333;
            border-radius: 10px;
            overflow: hidden;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 0.5em;
        }}
        .progress {{
            background-color: #bb86fc;
            height: 1em;
            border-radius: 10px;
            transition: width 0.5s ease;
        }}
        .trait-percentage {{
            color: #f0f0f0;
            font-size: 0.8em;
            min-width: 2.5em;
            text-align: right;
        }}
        .chat-container {{
            background-color: #1e1e1e;
            padding: 1.5em;
            border-radius: 12px;
            margin-top: 2em;
        }}
        .chat-title {{
            color: #bb86fc;
            margin-bottom: 1em;
            font-style: italic;
            font-size: 1.3em;
        }}
            
        div.stSpinner {{
            text-align: center;
            align-items: center;
            justify-content: center;
        }}
    </style>
""", unsafe_allow_html=True)


# --- Session State ---
if "stage" not in st.session_state:
    st.session_state.stage = "start"
if "data_loaded" not in st.session_state:
    st.session_state.data_loaded = False
if "show_traits" not in st.session_state:
    st.session_state.show_traits = False
if "chat_enabled" not in st.session_state:
    st.session_state.chat_enabled = False
if "messages" not in st.session_state:
    st.session_state.messages = []
if "show_share_modal" not in st.session_state:
    st.session_state.show_share_modal = False


# --- Navigation Bar ---
st.markdown("""
    <div class='navbar'>
        <div class='navbar-left'>🎧 AI Personality Mirror</div>
        <ul class='navbar-right'>
            <li><a onclick='Streamlit.setSessionState({"stage": "start"})'>Home</a></li>
            <li><a onclick='document.getElementById("how-it-works")?.scrollIntoView({ behavior: "smooth" });'>How it Works</a></li>
            <li><a href="#" onclick="document.dispatchEvent(new CustomEvent('open-share'));">Share</a></li>
            <li><a>Feedback</a></li>
        </ul>
    </div>
""", unsafe_allow_html=True)

# Listen to JS event and set session state
st.markdown("""
<script>
document.addEventListener("open-share", function() {
    window.parent.postMessage({type: "open_share_modal"}, "*");
});
</script>
""", unsafe_allow_html=True)

st.markdown("""
<script>
window.addEventListener("message", (event) => {
    if (event.data.type === "open_share_modal") {
        Streamlit.setComponentValue({ show_share_modal: true });
    }
});
</script>
""", unsafe_allow_html=True)


#Modal Block
if st.session_state.show_share_modal:
    st.markdown("""
        <div class="modal-container">
            <div class="modal-content">
                <button class="modal-close-button" onclick="document.dispatchEvent(new CustomEvent('close-share'));">×</button>
                <div class="url-display">
                    🔗 <span id="copy-target">https://your-website-link.com</span>
                    <span style="cursor:pointer; margin-left:10px;" onclick="copyToClipboard()">📋</span>
                </div>
            </div>
            <script>
                function copyToClipboard() {
                    const text = document.getElementById("copy-target").innerText;
                    navigator.clipboard.writeText(text).then(function() {
                        alert("Link copied to clipboard!");
                    }, function(err) {
                        alert("Failed to copy: " + err);
                    });
                }
            </script>
        </div>
    """, unsafe_allow_html=True)







# --- Page 1: The Cool Techy Entrance ---
if st.session_state.stage == "start":
    st.markdown("<p class='techy-text'></p>", unsafe_allow_html=True)
    st.markdown("<p class='techy-text'></p>", unsafe_allow_html=True)
    st.markdown("<h0 style='text-align: center; margin-bottom: 1.5em' class='techy-text'>Decoding Your Sonic Identity</h0>", unsafe_allow_html=True)
    
    st.markdown("<h5 style = 'color: #90caf9;' class='subtitle-text'>Unlock the secrets in your playlists. Connect your Spotify and decode what your music taste says about your personality</h5>", unsafe_allow_html=True)
    st.markdown("<p class='techy-text'></p>", unsafe_allow_html=True)
    st.markdown("<p class='techy-text'></p>", unsafe_allow_html=True)
    cols = st.columns([2, 1, 2])
    with cols[1]:
        connect_button = st.button("🔗 Connect to Spotify", key="connect_button", use_container_width=True)
    if connect_button:
        try:
            with st.spinner("Tuning into your musical universe..."):
                sp = connect_spotify()
                df = fetch_all_spotify_data(sp)
                df = deduplicate_and_weight(df)
                prompt, song_list = build_music_prompt(df)
                trait_summary = get_personality_traits(prompt)

                st.session_state.song_list = song_list
                st.session_state.trait_summary = trait_summary.content
                st.session_state.chat_chain = setup_conversational_chain(trait_summary.content, song_list)

                st.session_state.data_loaded = True
                st.session_state.stage = "show_button"
                st.rerun()
        except Exception as e:
            st.error(f"Failed to connect the audio stream: {e}")


    st.markdown("<hr class='separator'>", unsafe_allow_html=True)

    st.markdown("<div class='how-it-works-section' id='how-it-works'>", unsafe_allow_html=True)
    with st.expander("💡 How it Works", expanded=False):
        st.markdown("""
            We analyze your Spotify activity – recent plays, top tracks, and liked songs – to identify patterns.
            Our intelligent AI then deciphers these sonic footprints to reveal your unique personality.
            Think of it as a musical Rorschach test, with an AI twist!
        """,)
    st.markdown("</div>", unsafe_allow_html=True)

# --- Page 2: The Personality Revelation Hub ---
elif st.session_state.stage == "show_button":
    st.title(f"🎧 {PROJECT_NAME}")
    #st.markdown("<div class='stSuccess'>Connection successful! Ready to see what your music reveals?</div>", unsafe_allow_html=True)
    st.markdown("<h4 style='color: #d0d0d0; text-align: center; margin-bottom: 2em;'>Your musical data has been processed. Ready to see what your music reveals?</h4>", unsafe_allow_html=True)
    cols = st.columns([2, 1, 2])
    with cols[1]:  
        Reveal_button = st.button("✨ Reveal My Musical Personality", key="reveal_button", use_container_width=False)
    
    if Reveal_button:
        st.session_state.show_traits = True
        st.session_state.chat_enabled = True
        st.session_state.stage = "results"
        st.rerun()
    st.markdown("""
    <style>
        @keyframes fadeInOut {
            0% { opacity: 0.7; }
            50% { opacity: 1; }
            100% { opacity: 0.7; }
        }
        .pulse-text {
            animation: fadeInOut 2s infinite;
        }
    </style>
    <div class='pulse-text' style='text-align: center; font-size: 0.9em; color: #888; margin-top: 1em;'>
        This is where the magic happens...
    </div>
    """, unsafe_allow_html=True)

# --- Page 3: The Unveiling and Chat ---
elif st.session_state.stage == "results":
    #st.title(f"🔮 {PROJECT_NAME}")
    st.subheader("Your Musical Signature:")

    if st.session_state.show_traits:
        traits = st.session_state.trait_summary.strip().split('\n')
        cols = st.columns(3)
        for i, trait_line in enumerate(traits):
            if ": " in trait_line:
                name, percentage_str = trait_line.split(": ")
                col_index = i % 3
                with cols[col_index]:
                    st.markdown(f"""
                        <div class='personality-trait-container'>
                            <span class='trait-name'>{name.strip()}</span>
                            <div class='progress-bar'>
                                <div class='progress' style='width: {percentage_str.strip()};'></div>
                                <span class='trait-percentage'>{percentage_str.strip()}</span>
                            </div>
                        </div>
                        <style>
                            .progress-bar {{
                                background-color: #333;
                                border-radius: 10px;
                                overflow: hidden;
                                display: flex;
                                align-items: center;
                                justify-content: space-between;
                                padding: 0 0.5em;
                            }}
                            .progress {{
                                background-color: #3CB371;
                                height: 1em;
                                border-radius: 10px;
                                transition: width 0.5s ease;
                            }}
                            .trait-percentage {{
                                color: #f0f0f0;
                                font-size: 0.8em;
                                min-width: 2.5em;
                                text-align: right;
                            }}
                        </style>
                    """, unsafe_allow_html=True)
        

    if st.session_state.chat_enabled:
        st.markdown("<hr class='separator'>", unsafe_allow_html=True)
        #st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
        st.markdown("<h2 class='chat-title'>🗣️ Chat with Your Sonic Reflection</h2>", unsafe_allow_html=True)
        st.markdown("<p style='font-size: 0.9em; color: #d0d0d0;'>Ask questions about your personality analysis, dating app prompts, funny fictional questions and more.</p>", unsafe_allow_html=True)
        st.markdown("<p style='font-size: 0.9em; color: #d0d0d0;'>Sample Questions:</p>", unsafe_allow_html=True)
        st.markdown("<p style='font-size: 0.9em; color: #d0d0d0;'>🧙🏼‍♂️ What Harry Potter house would I be in?</p>", unsafe_allow_html=True)
        st.markdown("<p style='font-size: 0.9em; color: #d0d0d0;'>🚗 What car model would I be?</p>", unsafe_allow_html=True)
        st.markdown("<p style='font-size: 0.9em; color: #d0d0d0;'>Dating Promt: A life goal of mine...</p>", unsafe_allow_html=True)
        if "messages" in st.session_state:
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

        if prompt := st.chat_input("Type your question here..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.spinner("Consulting the musical spirits..."):
                ai_response = st.session_state.chat_chain.predict(input=prompt)
                st.session_state.messages.append({"role": "assistant", "content": ai_response})
                with st.chat_message("assistant"):
                    st.markdown(ai_response)
        st.markdown("</div>", unsafe_allow_html=True)

        # Share Modal Logic
if st.session_state.get("show_share_modal", False):
    st.markdown("""
        <div class="modal-container">
            <div class="modal-content">
                <button class="modal-close-button" onclick="document.dispatchEvent(new CustomEvent('close-share-modal'));">×</button>
                <div class="url-display">🔗 https://your-website-link.com</div>
                <button class="copy-url-button" onclick="navigator.clipboard.writeText('https://your-website-link.com')">📋 Copy</button>
            </div>
        </div>
    """, unsafe_allow_html=True)