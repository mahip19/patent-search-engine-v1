import time

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from patent_index import PatentSearchEngine

DATA_DIR = "data/patent_data_small"

app = Flask(__name__, static_folder="static")
CORS(app)

print("Building search index (one-time)...")
engine = PatentSearchEngine(DATA_DIR)


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/search", methods=["GET", "POST"])
def api_search():
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
    else:
        data = request.args

    query = data.get("query", "").strip()
    if not query:
        return jsonify({"results": [], "count": 0, "time_ms": 0})

    classification = data.get("classification", "").strip() or None
    title_contains = data.get("title_contains", "").strip() or None
    top_k = int(data.get("top_k", 10))

    t0 = time.time()
    results, surviving, total = engine.search(
        query,
        top_k=top_k,
        classification_prefix=classification,
        title_contains=title_contains,
    )
    elapsed_ms = round((time.time() - t0) * 1000, 1)

    return jsonify({
        "results": results,
        "count": len(results),
        "surviving_chunks": surviving,
        "total_chunks": total,
        "time_ms": elapsed_ms,
    })


if __name__ == "__main__":
    print("\n  → http://localhost:5001\n")
    app.run(host="0.0.0.0", port=5001, debug=False)
