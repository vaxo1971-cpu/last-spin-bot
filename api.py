from flask import Flask, request, jsonify

app = Flask(__name__)

valid_codes = set()

@app.route("/add", methods=["POST"])
def add_code():
    data = request.json
    code = data.get("code")
    if code:
        valid_codes.add(code)
        return jsonify({"status": "added"})
    return jsonify({"error": "no code"}), 400

@app.route("/check", methods=["POST"])
def check_code():
    data = request.json
    code = data.get("code")

    if code in valid_codes:
        valid_codes.remove(code)
        return jsonify({"valid": True})

    return jsonify({"valid": False})

@app.route("/")
def home():
    return "API working"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
