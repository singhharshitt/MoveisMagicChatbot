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

# Regional language mappings
REGION_MAP = {
    "punjabi": "pa",
    "south": ["te", "ta", "ml", "kn"],  # Telugu, Tamil, Malayalam, Kannada
    "tamil": "ta",
    "telugu": "te",
    "malayalam": "ml",
    "kannada": "kn",
    "bengali": "bn",
    "marathi": "mr"
}

def format_movie_list(movies):
    formatted = []
    seen_movie_ids = set()  # To track already seen movies
    
    for movie in movies:
        if movie.get("id") and movie["id"] not in seen_movie_ids:
            formatted.append({
                "title": movie.get("title", "Unknown Title"),
                "year": movie.get("release_date", "N/A")[:4] if movie.get("release_date") else "N/A",
                "rating": movie.get("vote_average", "N/A"),
                "poster": TMDB_IMAGE_BASE + movie["poster_path"] if movie.get("poster_path") else None,
                "link": f"https://www.themoviedb.org/movie/{movie.get('id')}"
            })
            seen_movie_ids.add(movie["id"])
    return formatted

def get_movies_by_rating(min_rating=7.0, genre_id=None, page=1):
    try:
        base_url = f"https://api.themoviedb.org/3/discover/movie?api_key={TMDB_API_KEY}"
        url = f"{base_url}&sort_by=vote_average.desc&vote_count.gte=100&vote_average.gte={min_rating}&page={page}"
        
        if genre_id:
            url += f"&with_genres={genre_id}"
        
        response = requests.get(url).json()
        return format_movie_list(response.get("results", []))
    except Exception as e:
        print(f"Error fetching movies by rating: {str(e)}")
        return []

def get_person_id(name, person_type):
    try:
        search_url = f"https://api.themoviedb.org/3/search/person?api_key={TMDB_API_KEY}&query={name}"
        response = requests.get(search_url).json()
        
        if response.get("results"):
            # Find the most relevant person (highest popularity)
            person = max(response["results"], key=lambda x: x.get("popularity", 0))
            return person["id"]
        return None
    except Exception as e:
        print(f"Error finding {person_type}: {str(e)}")
        return None

def get_movies_by_person(person_id, person_type, min_rating=7.0):
    try:
        url = f"https://api.themoviedb.org/3/person/{person_id}/movie_credits?api_key={TMDB_API_KEY}"
        response = requests.get(url).json()
        
        if person_type == "actor":
            movies = response.get("cast", [])
        else:  # director
            movies = response.get("crew", [])
            movies = [m for m in movies if m.get("job") == "Director"]
        
        # Filter by rating and sort
        filtered_movies = [m for m in movies if m.get("vote_average", 0) >= min_rating]
        filtered_movies.sort(key=lambda x: x.get("vote_average", 0), reverse=True)
        
        return format_movie_list(filtered_movies)[:10]
    except Exception as e:
        print(f"Error fetching movies for {person_type}: {str(e)}")
        return []

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

def get_genre_recommendations(genre_name, min_rating=7.0, count=10, page=1):
    try:
        genre_id = GENRE_MAP.get(genre_name.lower())
        if not genre_id:
            return {"text": "Genre not recognized. Try something like 'action', 'romance', or 'comedy'.", "movies": []}

        movies = get_movies_by_rating(min_rating, genre_id, page)[:count]
        if movies:
            text = f"🎥 Top Rated {genre_name.title()} Movies (Rating ≥{min_rating}):\n\n"
            text += "\n".join([f"🎬 {m['title']} ({m['year']}) ⭐ {m['rating']}" for m in movies])
            return {"text": text, "movies": movies, "has_more": len(movies) >= count}
        return {"text": f"Couldn't find high-rated movies in {genre_name} genre.", "movies": []}
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
                movies = get_movies_by_rating(7.0, genre_id)[:10]
                if movies:
                    text = "\n".join([f"🎬 {m['title']} ({m['year']}) ⭐ {m['rating']}" for m in movies])
                    return {"text": text, "movies": movies}
        return {"text": "Couldn't identify the genre or find similar movies.", "movies": []}
    except Exception as e:
        return {"text": f"Error analyzing movie genre: {str(e)}", "movies": []}

def get_best_from_each_genre(max_movies=20):
    try:
        all_movies = []
        for genre_name, genre_id in GENRE_MAP.items():
            discover_url = f"https://api.themoviedb.org/3/discover/movie?api_key={TMDB_API_KEY}&with_genres={genre_id}&sort_by=vote_average.desc&vote_count.gte=500&page=1"
            response = requests.get(discover_url).json()
            
            # Get top 1-2 movies per genre
            top_movies = response.get("results", [])[:2]
            all_movies.extend(top_movies)
        
        # Format and remove duplicates
        movies = format_movie_list(all_movies)[:max_movies]
        
        if movies:
            text = "🎥 Top Rated Movies Across Genres:\n\n"
            text += "\n".join([f"🎬 {m['title']} ({m['year']}) ⭐ {m['rating']}" for m in movies])
            return {"text": text, "movies": movies}
        return {"text": "Couldn't fetch top movies across genres.", "movies": []}
    except Exception as e:
        return {"text": f"Error fetching top movies across genres: {str(e)}", "movies": []}

def get_regional_movies(region_name):
    try:
        region_code = REGION_MAP.get(region_name.lower())
        if not region_code:
            return {"text": f"Sorry, I don't have data for {region_name} movies.", "movies": []}
        
        if isinstance(region_code, list):
            # Handle cases where multiple languages are mapped (like "south")
            all_movies = []
            for code in region_code:
                url = f"https://api.themoviedb.org/3/discover/movie?api_key={TMDB_API_KEY}&with_original_language={code}&sort_by=popularity.desc"
                response = requests.get(url).json()
                all_movies.extend(response.get("results", []))
        else:
            url = f"https://api.themoviedb.org/3/discover/movie?api_key={TMDB_API_KEY}&with_original_language={region_code}&sort_by=popularity.desc"
            response = requests.get(url).json()
            all_movies = response.get("results", [])
        
        movies = format_movie_list(all_movies)[:10]
        if movies:
            text = f"🎥 Popular {region_name.title()} Movies:\n\n"
            text += "\n".join([f"🎬 {m['title']} ({m['year']}) ⭐ {m['rating']}" for m in movies])
            return {"text": text, "movies": movies}
        return {"text": f"Couldn't find popular {region_name} movies.", "movies": []}
    except Exception as e:
        return {"text": f"Error fetching {region_name} movies: {str(e)}", "movies": []}

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data.get("message", "").strip().lower()
    is_more_request = data.get("is_more", False)
    current_page = data.get("page", 1)

    if not user_message:
        return jsonify({"response": "Please enter a movie name or genre!"})

    if user_message in ["hi", "hello", "hey"]:
        return jsonify({"response": "Hi there! 👋 Which movie recommendation are you looking for?"})

    # Handle "more" requests
    if is_more_request:
        current_page += 1
        # Check if previous response had a genre context
        context = data.get("context", {})
        if context.get("type") == "rating":
            min_rating = float(context.get("min_rating", 7.0))
            genre = context.get("genre")
            movies = get_movies_by_rating(min_rating, GENRE_MAP.get(genre) if genre else None, current_page)
            if movies:
                text = "\n".join([f"🎬 {m['title']} ({m['year']}) ⭐ {m['rating']}" for m in movies])
                return jsonify({
                    "response": text,
                    "movies": movies,
                    "page": current_page,
                    "context": context
                })
            return jsonify({"response": "No more movies found.", "movies": []})
        
        # Handle more requests for other contexts if needed
        return jsonify({"response": "Can't load more for this request type.", "movies": []})

    # Genre selection buttons
    if "genre" in user_message or "genera" in user_message:
        buttons_html = "<strong>🎬 Tap a genre to explore:</strong><br><br>"
        for genre in GENRE_MAP:
            buttons_html += (
                f'<button onclick="selectGenre(\'{genre}\')" '
                f'style="margin:5px; padding:10px 15px; border-radius:8px; '
                f'border:1px solid #aaa; background:#E9ECEF; cursor:pointer;">{genre.title()}</button>'
            )
        return jsonify({"response": buttons_html})

    # Check for rating requests (e.g., "movies above 7 rating" or "action movies above 8")
    rating_keywords = ["above", "rating", "rated", "at least"]
    if any(kw in user_message for kw in rating_keywords):
        try:
            # Extract rating number from message
            words = user_message.split()
            rating_index = next((i for i, word in enumerate(words) 
                               if word.isdigit() or (word.replace('.', '').isdigit() and '.' in word)), None)
            
            if rating_index is not None:
                min_rating = float(words[rating_index])
                # Check if there's also a genre mentioned
                genre = next((g for g in GENRE_MAP if g in user_message), None)
                
                if genre:
                    result = get_genre_recommendations(genre, min_rating, page=current_page)
                    result["context"] = {"type": "rating", "min_rating": min_rating, "genre": genre}
                    return jsonify(result)
                else:
                    movies = get_movies_by_rating(min_rating, page=current_page)[:10]
                    if movies:
                        text = f"🎥 Movies with Rating ≥{min_rating}:\n\n"
                        text += "\n".join([f"🎬 {m['title']} ({m['year']}) ⭐ {m['rating']}" for m in movies])
                        return jsonify({
                            "response": text,
                            "movies": movies,
                            "context": {"type": "rating", "min_rating": min_rating}
                        })
                    else:
                        return jsonify({"response": f"No movies found with rating ≥{min_rating}.", "movies": []})
        except Exception as e:
            print(f"Error processing rating request: {str(e)}")

    # Check for actor/actress/director requests
    person_keywords = ["actor", "actress", "director", "starring", "by"]
    if any(kw in user_message for kw in person_keywords):
        try:
            # Extract person name (simple approach - take words after keyword)
            parts = user_message.split()
            keyword_index = next((i for i, word in enumerate(parts) if word in person_keywords), None)
            
            if keyword_index is not None and keyword_index + 1 < len(parts):
                person_name = " ".join(parts[keyword_index+1:])
                person_type = "actor" if "actor" in user_message or "actress" in user_message or "starring" in user_message else "director"
                
                person_id = get_person_id(person_name, person_type)
                if person_id:
                    movies = get_movies_by_person(person_id, person_type)
                    if movies:
                        text = f"🎥 Top Rated Movies by {person_name.title()} ({person_type}):\n\n"
                        text += "\n".join([f"🎬 {m['title']} ({m['year']}) ⭐ {m['rating']}" for m in movies])
                        return jsonify({"response": text, "movies": movies})
                    else:
                        return jsonify({"response": f"No high-rated movies found for {person_name}.", "movies": []})
                else:
                    return jsonify({"response": f"Couldn't find {person_type} named {person_name}.", "movies": []})
        except Exception as e:
            print(f"Error processing person request: {str(e)}")

    # Check for genre requests
    for genre in GENRE_MAP:
        if genre in user_message:
            result = get_genre_recommendations(genre)
            return jsonify({"response": result["text"], "movies": result["movies"]})

    # Check for "best movies" or "good movies" requests
    if any(keyword in user_message for keyword in ["best movies", "good movies", "suggest me some good movies"]):
        result = get_best_from_each_genre()
        return jsonify({"response": result["text"], "movies": result["movies"]})

    # Check for regional movies
    for region in REGION_MAP:
        if region in user_message:
            result = get_regional_movies(region)
            return jsonify({"response": result["text"], "movies": result["movies"]})

    # Bollywood movies
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

    # Top 10 movies
    if any(keyword in user_message for keyword in ["top 10 movies", "best top movies", "highest ranking movies"]):
        result = get_top_movies()
        return jsonify({"response": result["text"], "movies": result["movies"]})

    # Try movie genre-based recommendations first
    result = get_movies_by_movie_genre(user_message)
    if result["movies"]:
        return jsonify({"response": result["text"], "movies": result["movies"]})
    else:
        # Fall back to general recommendations
        result = get_recommendations(user_message)
        return jsonify({"response": result["text"], "movies": result["movies"]})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)