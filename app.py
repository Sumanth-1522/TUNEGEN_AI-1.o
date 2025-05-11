from flask import Flask, render_template_string, request, jsonify
import sqlite3
import requests
import random
import os

print("Starting TUNEGEN_AI server...")

app = Flask(__name__)

# Last.fm API credentials
LASTFM_API_KEY = "7b226907d4fbd1b9dcfe83d29de2cf63"
LASTFM_BASE_URL = "http://ws.audioscrobbler.com/2.0/"

# Simulated mood and location mappings
MOOD_TAGS = {
    "Happy": "happy",
    "Sad": "sad",
    "Calm": "chill",
    "Energetic": "energetic"
}
LOCATION_TAGS = {
    "Beach": "tropical",
    "City": "urban",
    "Forest": "acoustic",
    "Mountain": "folk"
}

# Initialize SQLite3 database
def init_db():
    print("Initializing database...")
    try:
        conn = sqlite3.connect("tunegen.db")
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            mood TEXT,
            song_title TEXT,
            artist TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            sender TEXT,
            message TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )""")
        conn.commit()
    except Exception as e:
        print(f"Database initialization error: {e}")
    finally:
        conn.close()

init_db()

# Fetch songs from Last.fm based on tag
def fetch_songs_by_tag(tag, limit=5):
    print(f"Fetching songs for tag: {tag}")
    try:
        params = {
            "method": "tag.getTopTracks",
            "tag": tag,
            "api_key": LASTFM_API_KEY,
            "format": "json",
            "limit": limit
        }
        response = requests.get(LASTFM_BASE_URL, params=params)
        data = response.json()
        if "error" in data:
            print(f"Last.fm API error: {data['message']}")
            return []
        tracks = data.get("tracks", {}).get("track", [])
        return [{"name": track["name"], "artist": track["artist"]["name"], "url": track["url"]} for track in tracks]
    except Exception as e:
        print(f"Error fetching songs: {e}")
        return []

# Simulated location recognition
def recognize_location(image_file):
    print("Simulating location recognition...")
    locations = list(LOCATION_TAGS.keys())
    return random.choice(locations)

@app.route("/")
def index():
    print("Serving index route")
    try:
        return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TUNEGEN_AI</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background: linear-gradient(135deg, #1a1a1a, #2b6cb0); min-height: 100vh; }
        .chat-container { max-height: 400px; overflow-y: auto; }
        .chat-message { max-width: 80%; padding: 10px; margin: 5px; border-radius: 10px; }
        .bot-message { background: #2b6cb0; color: white; }
        .user-message { background: #4a5568; color: white; margin-left: auto; }
    </style>
</head>
<body class="flex flex-col items-center justify-center p-4 text-gray-200">
    <h1 class="text-4xl font-bold mb-6 text-blue-300">TUNEGEN_AI</h1>
    
    <!-- Username Input -->
    <div class="mb-4 w-full max-w-md">
        <input id="username" type="text" placeholder="Enter your username" 
               class="w-full p-2 rounded bg-gray-800 text-white border border-blue-500">
        <button onclick="setUsername()" 
                class="mt-2 w-full bg-blue-600 text-white p-2 rounded hover:bg-blue-700">
            Set Username
        </button>
    </div>
    
    <!-- Mood Selection and Filters -->
    <div class="mb-4 w-full max-w-md">
        <label class="block mb-2 text-blue-200">Select Mood:</label>
        <select id="mood" class="w-full p-2 rounded bg-gray-800 text-white border border-blue-500">
            <option value="">Select Mood</option>
            {% for mood in moods %}
                <option value="{{ mood }}">{{ mood }}</option>
            {% endfor %}
        </select>
        <label class="block mt-2 mb-2 text-blue-200">Filter by Genre (optional):</label>
        <input id="genre" type="text" placeholder="e.g., pop, rock" 
               class="w-full p-2 rounded bg-gray-800 text-white border border-blue-500">
        <button onclick="getMoodSongs()" 
                class="mt-2 w-full bg-blue-600 text-white p-2 rounded hover:bg-blue-700">
            Get Mood-Based Songs
        </button>
    </div>
    
    <!-- Image Upload for Location -->
    <div class="mb-4 w-full max-w-md">
        <label class="block mb-2 text-blue-200">Upload Image for Location-Based Songs:</label>
        <input id="location-image" type="file" accept="image/*" 
               class="w-full p-2 rounded bg-gray-800 text-white border border-blue-500">
        <button onclick="getLocationSongs()" 
                class="mt-2 w-full bg-blue-600 text-white p-2 rounded hover:bg-blue-700">
            Get Location-Based Songs
        </button>
    </div>
    
    <!-- Chatbot -->
    <div class="w-full max-w-md bg-gray-900 rounded-lg shadow-lg p-4 mb-4">
        <div id="chat-container" class="chat-container mb-2 p-2 border border-blue-500 rounded">
            <div class="chat-message bot-message">Hi! I'm TUNEGEN_AI. Select a mood, upload an image, or tell me how you feel!</div>
        </div>
        <div class="flex">
            <input id="chat-input" type="text" placeholder="Type your message..." 
                   class="flex-1 p-2 rounded-l bg-gray-800 text-white border border-blue-500">
            <button onclick="sendMessage()" 
                    class="bg-blue-600 text-white p-2 rounded-r hover:bg-blue-700">
                Send
            </button>
        </div>
    </div>
    
    <!-- Song Recommendations -->
    <div id="songs" class="w-full max-w-md">
        <h2 class="text-2xl font-semibold mb-2 text-blue-200">Recommended Songs</h2>
        <ul id="song-list" class="bg-gray-900 rounded-lg shadow-lg p-4"></ul>
    </div>

    <script>
        console.log("JavaScript loaded");
        let username = "";

        function setUsername() {
            username = document.getElementById("username").value.trim();
            if (!username) {
                alert("Please enter a username");
                return;
            }
            addChatMessage("bot", `Welcome, ${username}! Let's find some songs for you.`);
        }

        function addChatMessage(sender, message) {
            const chatContainer = document.getElementById("chat-container");
            const messageDiv = document.createElement("div");
            messageDiv.className = `chat-message ${sender === "bot" ? "bot-message" : "user-message"}`;
            messageDiv.textContent = message;
            chatContainer.appendChild(messageDiv);
            chatContainer.scrollTop = chatContainer.scrollHeight;
            
            if (username) {
                fetch("/save_chat", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ username, sender, message })
                }).catch(error => console.error("Error saving chat:", error));
            }
        }

        async function getMoodSongs() {
            if (!username) {
                alert("Please set a username first");
                return;
            }
            const mood = document.getElementById("mood").value;
            const genre = document.getElementById("genre").value;
            if (!mood) {
                alert("Please select a mood");
                return;
            }
            try {
                const response = await fetch("/get_mood_songs", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ username, mood, genre })
                });
                const data = await response.json();
                displaySongs(data.songs);
                addChatMessage("bot", `Here are some ${mood} songs${genre ? ` filtered by ${genre}` : ""}!`);
            } catch (error) {
                console.error("Error fetching mood songs:", error);
            }
        }

        async function getLocationSongs() {
            if (!username) {
                alert("Please set a username first");
                return;
            }
            const imageInput = document.getElementById("location-image");
            if (!imageInput.files[0]) {
                alert("Please upload an image");
                return;
            }
            const formData = new FormData();
            formData.append("image", imageInput.files[0]);
            formData.append("username", username);
            try {
                const response = await fetch("/get_location_songs", {
                    method: "POST",
                    body: formData
                });
                const data = await response.json();
                displaySongs(data.songs);
                addChatMessage("bot", `Detected location: ${data.location}. Here are some songs for that vibe!`);
            } catch (error) {
                console.error("Error fetching location songs:", error);
            }
        }

        async function sendMessage() {
            if (!username) {
                alert("Please set a username first");
                return;
            }
            const input = document.getElementById("chat-input");
            const message = input.value.trim();
            if (!message) return;
            addChatMessage("user", message);
            input.value = "";
            
            try {
                const response = await fetch("/chat", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ username, message })
                });
                const data = await response.json();
                addChatMessage("bot", data.response);
                if (data.songs) displaySongs(data.songs);
            } catch (error) {
                console.error("Error sending chat message:", error);
            }
        }

        function displaySongs(songs) {
            const songList = document.getElementById("song-list");
            songList.innerHTML = "";
            songs.forEach(song => {
                const li = document.createElement("li");
                li.className = "mb-2";
                li.innerHTML = `<a href="${song.url}" target="_blank" class="text-blue-400 hover:underline">${song.name} by ${song.artist}</a>`;
                songList.appendChild(li);
            });
        }
    </script>
</body>
</html>
        """, moods=MOOD_TAGS.keys())
    except Exception as e:
        print(f"Error rendering index: {e}")
        return "<h1>TUNEGEN_AI Error</h1><p>Server failed to render page. Check logs.</p>", 500

@app.route("/get_mood_songs", methods=["POST"])
def get_mood_songs():
    print("Processing get_mood_songs request")
    try:
        data = request.json
        username = data.get("username")
        mood = data.get("mood")
        genre = data.get("genre", "")
        
        conn = sqlite3.connect("tunegen.db")
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (username) VALUES (?)", (username,))
        c.execute("SELECT id FROM users WHERE username = ?", (username,))
        user_id = c.fetchone()[0]
        
        tag = MOOD_TAGS.get(mood, "pop")
        if genre:
            tag = f"{tag}+{genre.replace(' ', '+')}"
        songs = fetch_songs_by_tag(tag)
        
        for song in songs:
            c.execute("INSERT INTO preferences (user_id, mood, song_title, artist) VALUES (?, ?, ?, ?)",
                      (user_id, mood, song["name"], song["artist"]))
        
        conn.commit()
        conn.close()
        return jsonify({"songs": songs})
    except Exception as e:
        print(f"Error in get_mood_songs: {e}")
        return jsonify({"error": "Failed to fetch songs"}), 500

@app.route("/get_location_songs", methods=["POST"])
def get_location_songs():
    print("Processing get_location_songs request")
    try:
        username = request.form.get("username")
        image = request.files.get("image")
        
        conn = sqlite3.connect("tunegen.db")
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (username) VALUES (?)", (username,))
        c.execute("SELECT id FROM users WHERE username = ?", (username,))
        user_id = c.fetchone()[0]
        
        location = recognize_location(image)
        tag = LOCATION_TAGS.get(location, "pop")
        songs = fetch_songs_by_tag(tag)
        
        for song in songs:
            c.execute("INSERT INTO preferences (user_id, mood, song_title, artist) VALUES (?, ?, ?, ?)",
                      (user_id, location, song["name"], song["artist"]))
        
        conn.commit()
        conn.close()
        return jsonify({"songs": songs, "location": location})
    except Exception as e:
        print(f"Error in get_location_songs: {e}")
        return jsonify({"error": "Failed to fetch location songs"}), 500

@app.route("/chat", methods=["POST"])
def chat():
    print("Processing chat request")
    try:
        data = request.json
        username = data.get("username")
        message = data.get("message").lower()
        
        conn = sqlite3.connect("tunegen.db")
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (username) VALUES (?)", (username,))
        c.execute("SELECT id FROM users WHERE username = ?", (username,))
        user_id = c.fetchone()[0]
        c.execute("INSERT INTO chat_history (user_id, sender, message) VALUES (?, ?, ?)",
                  (user_id, "user", message))
        
        response = "Got it! Want me to find songs for that?"
        songs = []
        for mood, tag in MOOD_TAGS.items():
            if mood.lower() in message:
                songs = fetch_songs_by_tag(tag)
                response = f"Here are some {mood} songs!"
                if songs:
                    c.execute("INSERT INTO preferences (user_id, mood, song_title, artist) VALUES (?, ?, ?, ?)",
                              (user_id, mood, songs[0]["name"], songs[0]["artist"]))
                break
        for location, tag in LOCATION_TAGS.items():
            if location.lower() in message:
                songs = fetch_songs_by_tag(tag)
                response = f"Here are some songs for a {location} vibe!"
                if songs:
                    c.execute("INSERT INTO preferences (user_id, mood, song_title, artist) VALUES (?, ?, ?, ?)",
                              (user_id, location, songs[0]["name"], songs[0]["artist"]))
                break
        
        c.execute("INSERT INTO chat_history (user_id, sender, message) VALUES (?, ?, ?)",
                  (user_id, "bot", response))
        conn.commit()
        conn.close()
        return jsonify({"response": response, "songs": songs})
    except Exception as e:
        print(f"Error in chat: {e}")
        return jsonify({"error": "Failed to process chat"}), 500

@app.route("/save_chat", methods=["POST"])
def save_chat():
    print("Processing save_chat request")
    try:
        data = request.json
        username = data.get("username")
        sender = data.get("sender")
        message = data.get("message")
        
        conn = sqlite3.connect("tunegen.db")
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (username) VALUES (?)", (username,))
        c.execute("SELECT id FROM users WHERE username = ?", (username,))
        user_id = c.fetchone()[0]
        c.execute("INSERT INTO chat_history (user_id, sender, message) VALUES (?, ?, ?)",
                  (user_id, sender, message))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e:
        print(f"Error in save_chat: {e}")
        return jsonify({"error": "Failed to save chat"}), 500

if __name__ == "__main__":
    print("Running Flask server on http://localhost:5000")
    app.run(debug=True, port=5000)