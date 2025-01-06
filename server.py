import json
import os
from flask import Flask, request, jsonify, render_template, send_file
import requests
from pytesseract import image_to_string, Output
from PIL import Image, ImageDraw, ImageFont
from googletrans import Translator
import zipfile
import io

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

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/process_and_download", methods=["POST"])
def process_and_download():
    data = request.json
    folder_name = data.get("folderName", config.get("folderName", "Default"))
    chapter_link = data.get("chapterLink")

    # التحقق من صحة المدخلات
    if not chapter_link:
        return jsonify({"error": "يجب إدخال رابط الفصل"}), 400

    print(f"Processing chapter link: {chapter_link}, using folder: {folder_name}")  # طباعة المدخلات

    try:
        # تنزيل بيانات الفصل
        response = requests.get(chapter_link)
        response.raise_for_status()
        image_urls = [line.strip() for line in response.text.split("\n") if line.endswith((".jpg", ".png"))]
        zip_buffer = io.BytesIO()  # إنشاء ملف مضغوط في الذاكرة

        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
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

                # إضافة الصورة المعدلة إلى ملف ZIP
                with open(modified_img_path, "rb") as img_file:
                    zip_file.writestr(f"translated_{i+1:03}.jpg", img_file.read())

        zip_buffer.seek(0)  # إعادة المؤشر إلى بداية الملف المضغوط
        return send_file(zip_buffer, mimetype="application/zip", as_attachment=True, download_name="translated_images.zip")

    except Exception as e:
        print(f"Error during processing: {e}")  # طباعة الخطأ الذي حدث
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
