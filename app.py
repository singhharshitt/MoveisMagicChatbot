from flask import Flask, request, render_template, jsonify
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"

# TMDB Genre List
GENRE_MAP = {
    "action": 28, "adventure": 12, "animation": 16, "comedy": 35,
    "crime": 80, "documentary": 99, "drama": 18, "family": 10751,
    "fantasy": 14, "history": 36, "horror": 27, "music": 10402,
    "mystery": 9648, "romance": 10749, "sci-fi": 878,
    "thriller": 53, "war": 10752, "western": 37
}

def format_movie_list(movies):
    formatted = []
    for movie in movies[:10]:
        formatted.append({
            "title": movie.get("title", "Unknown Title"),
            "year": movie.get("release_date", "N/A")[:4],
            "rating": movie.get("vote_average", "N/A"),
            "poster": TMDB_IMAGE_BASE + movie["poster_path"] if movie.get("poster_path") else None,
            "link": f"https://www.themoviedb.org/movie/{movie.get('id')}"
        })
    return formatted

def get_recommendations(movie_name):
    try:
        search_url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={movie_name}"
        search_response = requests.get(search_url).json()

        if search_response.get("results"):
            movie_id = search_response["results"][0]["id"]
            rec_url = f"https://api.themoviedb.org/3/movie/{movie_id}/recommendations?api_key={TMDB_API_KEY}"
            rec_response = requests.get(rec_url).json()

            movies = format_movie_list(rec_response.get("results", []))
            if movies:
                text = "\n".join([f"🎬 {m['title']} ({m['year']}) ⭐ {m['rating']}" for m in movies])
                return {"text": text, "movies": movies}
            else:
                return {"text": "No similar movies found.", "movies": []}
        return {"text": "Movie not found. Try another title!", "movies": []}
    except Exception as e:
        return {"text": f"Error fetching recommendations: {str(e)}", "movies": []}

def get_genre_recommendations(genre_name):
    try:
        genre_id = GENRE_MAP.get(genre_name.lower())
        if not genre_id:
            return {"text": "Genre not recognized. Try something like 'action', 'romance', or 'comedy'.", "movies": []}

        discover_url = (
            f"https://api.themoviedb.org/3/discover/movie?api_key={TMDB_API_KEY}"
            f"&with_genres={genre_id}&sort_by=popularity.desc"
        )
        response = requests.get(discover_url).json()

        movies = format_movie_list(response.get("results", []))
        if movies:
            text = "\n".join([f"🎬 {m['title']} ({m['year']}) ⭐ {m['rating']}" for m in movies])
            return {"text": text, "movies": movies}
        return {"text": "Couldn't find any movies in this genre.", "movies": []}
    except Exception as e:
        return {"text": f"Error fetching genre movies: {str(e)}", "movies": []}

def get_top_movies():
    try:
        url = f"https://api.themoviedb.org/3/movie/top_rated?api_key={TMDB_API_KEY}&language=en-US&page=1"
        response = requests.get(url).json()

        movies = format_movie_list(response.get("results", []))
        if movies:
            text = "\n".join([f"🏆 {m['title']} ({m['year']}) ⭐ {m['rating']}" for m in movies])
            return {"text": text, "movies": movies}
        return {"text": "Couldn't fetch top-rated movies.", "movies": []}
    except Exception as e:
        return {"text": f"Error fetching top-rated movies: {str(e)}", "movies": []}

def get_movies_by_movie_genre(movie_name):
    try:
        search_url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={movie_name}"
        search_response = requests.get(search_url).json()

        if search_response.get("results"):
            genre_ids = search_response["results"][0].get("genre_ids", [])
            if genre_ids:
                genre_id = genre_ids[0]
                discover_url = f"https://api.themoviedb.org/3/discover/movie?api_key={TMDB_API_KEY}&with_genres={genre_id}&sort_by=popularity.desc"
                response = requests.get(discover_url).json()
                movies = format_movie_list(response.get("results", []))
                if movies:
                    text = "\n".join([f"🎬 {m['title']} ({m['year']}) ⭐ {m['rating']}" for m in movies])
                    return {"text": text, "movies": movies}
        return {"text": "Couldn't identify the genre or find similar movies.", "movies": []}
    except Exception as e:
        return {"text": f"Error analyzing movie genre: {str(e)}", "movies": []}

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data.get("message", "").strip().lower()

    if not user_message:
        return jsonify({"response": "Please enter a movie name or genre!"})

    if user_message in ["hi", "hello", "hey"]:
        return jsonify({"response": "Hi there! 👋 Which movie recommendation are you looking for?"})

    if "genre" in user_message or "genera" in user_message:
        buttons_html = "<strong>🎬 Tap a genre to explore:</strong><br><br>"
        for genre in GENRE_MAP:
            buttons_html += (
                f'<button onclick="selectGenre(\'{genre}\')" '
                f'style="margin:5px; padding:10px 15px; border-radius:8px; '
                f'border:1px solid #aaa; background:#E9ECEF; cursor:pointer;">{genre.title()}</button>'
            )
        return jsonify({"response": buttons_html})

    if user_message in GENRE_MAP:
        result = get_genre_recommendations(user_message)
        return jsonify({"response": result["text"], "movies": result["movies"]})

    if any(keyword in user_message for keyword in ["bollywood", "hindi movies", "top bollywood", "top hindi"]):
        try:
            bollywood_url = f"https://api.themoviedb.org/3/discover/movie?api_key={TMDB_API_KEY}&with_original_language=hi&sort_by=popularity.desc"
            response = requests.get(bollywood_url).json()
            movies = format_movie_list(response.get("results", []))
            if movies:
                text = "🎥 Here are some popular Bollywood movies:\n\n"
                text += "\n".join([f"{m['title']} ({m['year']}) ⭐ {m['rating']}" for m in movies])
                return jsonify({"response": text, "movies": movies})
            else:
                return jsonify({"response": "Couldn't find popular Bollywood movies.", "movies": []})
        except Exception as e:
            return jsonify({"response": f"Error fetching Bollywood movies: {str(e)}", "movies": []})

    if any(keyword in user_message for keyword in ["top 10 movies", "best top movies", "highest ranking movies"]):
        result = get_top_movies()
        return jsonify({"response": result["text"], "movies": result["movies"]})

    result = get_movies_by_movie_genre(user_message)
    if result["movies"]:
        return jsonify({"response": result["text"], "movies": result["movies"]})
    else:
        result = get_recommendations(user_message)
        return jsonify({"response": result["text"], "movies": result["movies"]})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
