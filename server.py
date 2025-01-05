from flask import Flask, request, jsonify
import os
import requests
from pytesseract import image_to_string, Output
from PIL import Image, ImageDraw, ImageFont
from googletrans import Translator
from github import Github

# تهيئة التطبيق
app = Flask(__name__)

# إعداد مترجم Google
translator = Translator()

# إعداد مجلد مؤقت للصور
TEMP_FOLDER = "temp_images"
os.makedirs(TEMP_FOLDER, exist_ok=True)

# إعداد GitHub
GITHUB_TOKEN = "your_github_token"  # ضع GitHub Token هنا
REPO_NAME = "username/translated-chapters"  # اسم المستودع في GitHub
github = Github(GITHUB_TOKEN)
repo = github.get_repo(REPO_NAME)

@app.route("/process_and_upload", methods=["POST"])
def process_and_upload():
    try:
        # الحصول على البيانات من الطلب
        data = request.json
        chapter_link = data.get("chapterLink")
        folder_name = data.get("folderName", "Default")
        tags = data.get("tags", [])

        # التحقق من المدخلات
        if not chapter_link:
            return jsonify({"error": "يجب إدخال رابط الفصل"}), 400

        # إنشاء مسار المجلد في GitHub
        folder_path = f"{folder_name}/"

        # تحميل الصور من رابط الفصل
        response = requests.get(chapter_link)
        response.raise_for_status()
        image_urls = [line.strip() for line in response.text.split("\n") if line.endswith((".jpg", ".png"))]

        results = []

        for i, url in enumerate(image_urls):
            # تحميل الصور الأصلية
            img_data = requests.get(url).content
            img_path = os.path.join(TEMP_FOLDER, f"{i+1:03}.jpg")
            with open(img_path, "wb") as img_file:
                img_file.write(img_data)

            # معالجة الصور باستخدام OCR
            img = Image.open(img_path)
            ocr_data = image_to_string(img, lang="jpn", config="--psm 6", output_type=Output.DICT)
            text_blocks = ocr_data["text"]
            block_coords = zip(ocr_data["left"], ocr_data["top"], ocr_data["width"], ocr_data["height"])

            # تعديل الصور
            modified_img = img.copy()
            draw = ImageDraw.Draw(modified_img)
            font = ImageFont.load_default()

            for block, coords in zip(text_blocks, block_coords):
                if block.strip():
                    try:
                        translated_text = translator.translate(block, src="ja", dest="ar").text
                    except Exception:
                        translated_text = "ترجمة غير متوفرة"
                    x, y, w, h = coords
                    draw.rectangle((x, y, x + w, y + h), fill="white")
                    draw.text((x + 5, y + 5), translated_text, fill="black", font=font)

            # حفظ الصورة المعدلة محليًا
            modified_img_path = os.path.join(TEMP_FOLDER, f"translated_{i+1:03}.jpg")
            modified_img.save(modified_img_path)

            # رفع الصورة المعدلة إلى GitHub
            with open(modified_img_path, "rb") as img_file:
                repo.create_file(f"{folder_path}{os.path.basename(modified_img_path)}", 
                                 f"Upload {os.path.basename(modified_img_path)}", 
                                 img_file.read(), 
                                 branch="main")

            # حفظ النتائج
            results.append({
                "original_image": img_path,
                "modified_image": modified_img_path,
            })

        # رفع ملف العلامات (Tags) إلى GitHub
        repo.create_file(f"{folder_path}/tags.txt", "Add tags", ", ".join(tags), branch="main")

        return jsonify({"message": "تم رفع الصور المعدلة والعلامات بنجاح!", "results": results})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
