import json
import os
from flask import Flask, request, jsonify, redirect, url_for, render_template
import requests
from pytesseract import image_to_string, Output
from PIL import Image, ImageDraw, ImageFont
from googletrans import Translator
from github import Github

app = Flask(__name__)
translator = Translator()

# إعداد المجلد المؤقت
TEMP_FOLDER = "temp_images"
os.makedirs(TEMP_FOLDER, exist_ok=True)

# قراءة ملف config.json
def load_config():
    try:
        with open('config.json', 'r', encoding='utf-8') as config_file:
            config = json.load(config_file)
            print(f"Config loaded successfully: {config}")  # للتأكد من قراءة البيانات
        return config
    except Exception as e:
        print(f"Error reading config.json: {e}")
        return {}

# تحميل الإعدادات
config = load_config()
tags = config.get("tags", [])
folder_name = config.get("folderName", "Default")

print(f"Loaded folderName: {folder_name}, tags: {tags}")  # طباعة القيم المستخلصة من الملف

# قراءة GitHub Token من متغيرات البيئة
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise ValueError("GitHub Token is not set in environment variables")

# اسم المستودع
REPO_NAME = "Fares-123/Manga.translator"

# إعداد الاتصال بـ GitHub
try:
    github = Github(GITHUB_TOKEN)
    repo = github.get_repo(REPO_NAME)
except Exception as e:
    raise ValueError(f"Error connecting to GitHub repository: {e}")

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/process_and_upload", methods=["POST"])
def process_and_upload():
    data = request.json
    chapter_link = data.get("chapterLink")
    folder_name = data.get("folderName", folder_name)  # استخدم القيمة من config إذا لم يتم تقديمها في الطلب
    tags = data.get("tags", tags)  # استخدم القيمة من config إذا لم يتم تقديمها في الطلب

    # التحقق من صحة المدخلات
    if not chapter_link:
        return jsonify({"error": "يجب إدخال رابط الفصل"}), 400

    print(f"Processing chapter link: {chapter_link}, using folder: {folder_name}, tags: {tags}")  # طباعة المدخلات

    try:
        # تنزيل بيانات الفصل
        response = requests.get(chapter_link)
        response.raise_for_status()
        image_urls = [line.strip() for line in response.text.split("\n") if line.endswith((".jpg", ".png"))]
        folder_path = f"{folder_name}/"
        results = []

        for i, url in enumerate(image_urls):
            # تنزيل الصور الأصلية
            img_data = requests.get(url).content
            img_path = os.path.join(TEMP_FOLDER, f"{i+1:03}.jpg")
            with open(img_path, "wb") as img_file:
                img_file.write(img_data)

            # معالجة الصور
            img = Image.open(img_path)
            ocr_data = image_to_string(img, lang="jpn", config="--psm 6", output_type=Output.DICT)
            text_blocks = ocr_data["text"]
            block_coords = zip(ocr_data["left"], ocr_data["top"], ocr_data["width"], ocr_data["height"])

            modified_img = img.copy()
            draw = ImageDraw.Draw(modified_img)
            font = ImageFont.load_default()

            for block, coords in zip(text_blocks, block_coords):
                if block.strip():
                    # ترجمة النصوص
                    translated_text = translator.translate(block, src="ja", dest="ar").text
                    x, y, w, h = coords
                    draw.rectangle((x, y, x + w, y + h), fill="white")
                    draw.text((x + 5, y + 5), translated_text, fill="black", font=font)

            # حفظ الصور المعدلة
            modified_img_path = os.path.join(TEMP_FOLDER, f"translated_{i+1:03}.jpg")
            modified_img.save(modified_img_path)

            # رفع الصور إلى GitHub
            with open(modified_img_path, "rb") as img_file:
                repo.create_file(
                    f"{folder_path}{os.path.basename(modified_img_path)}",
                    f"Upload {os.path.basename(modified_img_path)}",
                    img_file.read(),
                    branch="main"
                )

            results.append({
                "original_image": img_path,
                "modified_image": modified_img_path,
            })

        # رفع ملف العلامات (Tags)
        tags_file_path = os.path.join(TEMP_FOLDER, "tags.txt")
        with open(tags_file_path, "w", encoding="utf-8") as tags_file:
            tags_file.write(", ".join(tags))

        with open(tags_file_path, "rb") as tags_file:
            repo.create_file(
                f"{folder_path}/tags.txt",
                "Add tags",
                tags_file.read(),
                branch="main"
            )

        return redirect(url_for('home'))  # التوجيه إلى الصفحة الرئيسية بعد رفع الصور والعلامات

    except Exception as e:
        print(f"Error during processing: {e}")  # طباعة الخطأ الذي حدث
        return jsonify({"error": str(e)}), 500


@app.route("/process_and_save", methods=["POST"])
def process_and_save():
    try:
        # معالجة البيانات القادمة من الطلب
        data = request.json
        if not data:
            return jsonify({"error": "بيانات الطلب غير صالحة"}), 400

        # يمكنك هنا إضافة المنطق الذي تحتاجه لمعالجة البيانات
        return jsonify({"message": "تمت معالجة البيانات وحفظها بنجاح!"}), 200

    except Exception as e:
        print(f"Error during save processing: {e}")  # طباعة الخطأ الذي حدث
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
