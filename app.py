from flask import Flask, render_template, request, abort, jsonify
from utils.utils import  youtube_info_batch, update_video_ids, youtube_info_batch_with_links
import json
from werkzeug.utils import secure_filename
import os
from dotenv import load_dotenv


app = Flask(__name__)

with open('config.json') as f:
    config = json.load(f)

@app.route("/")
def home():
    cards = config.get('cards', []) 
    return render_template("index.html", cards=cards)

@app.route("/<page>")
def show_page(page):
    cards = config.get('cards', [])
    video_ids = config.get("video_ids", {}).get(page, [])

    try:
        video_details = youtube_info_batch(video_ids)
    except RuntimeError as e:
        return str(e), 503
    
    card = next((card for card in cards if card['link'] == page), None)
    title = card['title'] if card else page.capitalize()

    if card:
        return render_template(
            "page.html",
            video_details=video_details,
            title = title,
            page=page
        )
    else:
        return "Page not found", 404


@app.route('/<page>/<video_id>')
def video(page, video_id):
    video_ids = config.get("video_ids", {}).get(page, [])

    try:
        video_details = youtube_info_batch_with_links(video_ids)
    except RuntimeError as e:
        return str(e), 503

    index = next((i for i, v in enumerate(video_details) if v['video_id'] == video_id), None)
    if index is None:
        abort(404)
    video = video_details[index]
    prev_video = video_details[index - 1] if index > 0 else None
    next_video = video_details[index + 1] if index < len(video_details) - 1 else None
    return render_template(
        'video.html',
        video=video,
        index=index,
        prev_video=prev_video,
        next_video=next_video,
        page=page
    )


@app.route("/update")
def update():
    try:
        return update_video_ids()
    except RuntimeError as e:
        return str(e), 503
    

def save_config(new_config):
    with open('config.json', 'w') as f:
        json.dump(new_config, f, indent=4)


PASSWORD = os.environ.get("PASSWORD")
@app.route("/edit_config", methods=["GET","POST"])
def edit_config():
    if request.method == "POST":
        try:
            data = request.get_json()
            password = data.get("password")
            new_config = data.get("config")
            if password != PASSWORD:
                return jsonify({"status": "error", "message": "Incorrect password"}), 403
            if not isinstance(new_config, dict):
                return "Invalid config format", 400
            save_config(new_config)
            global config
            config = new_config  # Update in-memory config
            return jsonify({"status": "success"})
        except Exception as e:
            return str(e), 500
    return render_template("edit_config.html", config=json.dumps(config, indent=4))


UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static','assets', 'img')
ALLOWED_EXTENSIONS = {'png', 'jpg'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/upload_image", methods=["GET", "POST"])
def upload_image():
    if request.method == "POST":
        password = request.form.get("password")

        if password != PASSWORD:
            return render_template(
                "upload_image.html",
                message="Incorrect password.",
                status="error"
            )
        if 'image' not in request.files:
            return render_template("upload_image.html", message="No file part", status="error")
        file = request.files['image']
        if file.filename == '':
            return render_template("upload_image.html", message="No selected file", status="error")
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Ensure upload folder exists
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return render_template("upload_image.html", message="Image uploaded successfully!", status="success", filename=filename)
        else:
            return render_template("upload_image.html", message="Invalid file type", status="error")
    return render_template("upload_image.html")


if __name__ == "__main__":
    app.run(debug=True)