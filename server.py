from flask import Flask, request, jsonify
import os
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

# قراءة GitHub Token من متغيرات البيئة
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise ValueError("GitHub Token is not set in environment variables")

# اسم المستودع (قم بتعديل اسم المستخدم واسم المستودع)
REPO_NAME = "fares123/manga-translator"

# إعداد الاتصال بـ GitHub
try:
    github = Github(GITHUB_TOKEN)
    repo = github.get_repo(REPO_NAME)
except Exception as e:
    raise ValueError(f"Error connecting to GitHub repository: {e}")

@app.route("/process_and_upload", methods=["POST"])
def process_and_upload():
    data = request.json
    chapter_link = data.get("chapterLink")
    folder_name = data.get("folderName", "Default")
    tags = data.get("tags", [])

    # التحقق من صحة المدخلات
    if not chapter_link:
        return jsonify({"error": "يجب إدخال رابط الفصل"}), 400

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

        return jsonify({"message": "تم رفع الصور المعدلة والعلامات بنجاح!", "results": results})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
