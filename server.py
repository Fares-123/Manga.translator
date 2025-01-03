from flask import Flask, request, jsonify, render_template
import os
import requests
from pytesseract import image_to_string, Output
from PIL import Image, ImageDraw, ImageFont
from googletrans import Translator
from github import Github

app = Flask(__name__, static_folder="static", template_folder="templates")
translator = Translator()

TEMP_FOLDER = "temp_images"
os.makedirs(TEMP_FOLDER, exist_ok=True)

# استدعاء GitHub Token من المتغير البيئي
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
if not GITHUB_TOKEN:
    raise RuntimeError("لم يتم العثور على GITHUB_TOKEN في المتغيرات البيئية.")

github = Github(GITHUB_TOKEN)
repo = github.get_repo("Fares-123/Manga.translator")  # اسم المستودع

# المسار الرئيسي يعرض الصفحة الرئيسية ويدعم GET و HEAD
@app.route("/", methods=["GET", "HEAD"])
def home():
    if request.method == "HEAD":
        return "", 200  # استجابة فارغة للطلبات من النوع HEAD
    return render_template("index.html")

# API لمعالجة الصور ورفعها
@app.route("/process_and_upload", methods=["POST"])
def process_and_upload():
    data = request.json
    chapter_link = data.get("chapterLink")
    folder_name = data.get("folderName", "Default")
    tags = data.get("tags", [])

    if not chapter_link:
        return jsonify({"error": "يجب إدخال رابط الفصل"}), 400

    try:
        response = requests.get(chapter_link)
        response.raise_for_status()  # التحقق من نجاح الطلب
        image_urls = [line.strip() for line in response.text.split("\n") if line.endswith((".jpg", ".png"))]
        folder_path = f"{folder_name}/"
        results = []

        for i, url in enumerate(image_urls):
            img_data = requests.get(url).content
            img_path = os.path.join(TEMP_FOLDER, f"{i+1:03}.jpg")
            with open(img_path, "wb") as img_file:
                img_file.write(img_data)

            img = Image.open(img_path)
            ocr_data = image_to_string(img, lang="jpn", config="--psm 6", output_type=Output.DICT)
            text_blocks = ocr_data["text"]
            block_coords = zip(ocr_data["left"], ocr_data["top"], ocr_data["width"], ocr_data["height"])

            modified_img = img.copy()
            draw = ImageDraw.Draw(modified_img)
            font = ImageFont.load_default()

            for block, coords in zip(text_blocks, block_coords):
                if block.strip():
                    translated_text = translator.translate(block, src="ja", dest="ar").text
                    x, y, w, h = coords
                    draw.rectangle((x, y, x + w, y + h), fill="white")
                    draw.text((x + 5, y + 5), translated_text, fill="black", font=font)

            modified_img_path = os.path.join(TEMP_FOLDER, f"translated_{i+1:03}.jpg")
            modified_img.save(modified_img_path)

            with open(modified_img_path, "rb") as img_file:
                repo.create_file(f"{folder_path}{os.path.basename(modified_img_path)}", 
                                 f"Upload {os.path.basename(modified_img_path)}", 
                                 img_file.read(), 
                                 branch="main")

            results.append({
                "original_image": img_path,
                "modified_image": modified_img_path,
            })

        repo.create_file(f"{folder_path}/tags.txt", "Add tags", ", ".join(tags), branch="main")
        return jsonify({"message": "تم رفع الصور المعدلة بنجاح!"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# لا داعي لتشغيل التطبيق هنا لأن Gunicorn سيشغل الخادم في بيئة الإنتاج
