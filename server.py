import json
import os
from flask import Flask, request, jsonify, redirect, url_for, render_template
import requests
from pytesseract import image_to_string, Output
from PIL import Image, ImageDraw, ImageFont
from googletrans import Translator
from github import Github
from bs4 import BeautifulSoup

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
folder_name = config.get("folderName", "Default")

print(f"Loaded folderName: {folder_name}")  # طباعة القيم المستخلصة من الملف

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

def download_images_from_html(chapter_link):
    """دالة لتحميل الصور من صفحة HTML."""
    try:
        response = requests.get(chapter_link)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            img_tags = soup.find_all('img')
            img_urls = [img.get('src') for img in img_tags if img.get('src')]
            image_paths = []

            for i, img_url in enumerate(img_urls):
                # التعامل مع الروابط النسبية
                if img_url.startswith('/'):
                    img_url = chapter_link + img_url
                
                img_data = requests.get(img_url).content
                img_path = os.path.join(TEMP_FOLDER, f"{i+1:03}.jpg")
                with open(img_path, 'wb') as img_file:
                    img_file.write(img_data)
                image_paths.append(img_path)
            return image_paths
        else:
            raise Exception(f"فشل تحميل الصفحة: {response.status_code}")
    except Exception as e:
        print(f"Error during image download: {e}")
        return []

@app.route("/process_and_upload", methods=["POST"])
def process_and_upload():
    data = request.json
    chapter_link = data.get("chapterLink")
    folder_name = data.get("folderName", folder_name)  # استخدم القيمة من config إذا لم يتم تقديمها في الطلب

    # التحقق من صحة المدخلات
    if not chapter_link:
        return jsonify({"error": "يجب إدخال رابط الفصل"}), 400

    print(f"Processing chapter link: {chapter_link}, using folder: {folder_name}")  # طباعة المدخلات

    try:
        # تحميل الصور من رابط HTML
        image_paths = download_images_from_html(chapter_link)
        if not image_paths:
            return jsonify({"error": "لم يتم العثور على صور في الصفحة"}), 400

        results = []
        for img_path in image_paths:
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
            modified_img_path = os.path.join(TEMP_FOLDER, f"translated_{os.path.basename(img_path)}")
            modified_img.save(modified_img_path)

            # رفع الصور إلى GitHub
            with open(modified_img_path, "rb") as img_file:
                repo.create_file(
                    f"{folder_name}/{os.path.basename(modified_img_path)}",
                    f"Upload {os.path.basename(modified_img_path)}",
                    img_file.read(),
                    branch="main"
                )

            results.append({
                "original_image": img_path,
                "modified_image": modified_img_path,
            })

        return jsonify({"message": "تمت معالجة الصور ورفعها بنجاح!"}), 200

    except Exception as e:
        print(f"Error during processing: {e}")  # طباعة الخطأ الذي حدث
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
