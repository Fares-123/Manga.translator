import os
import zipfile
from flask import Flask, request, jsonify, send_file, render_template
from PIL import Image
import pytesseract

# إعدادات افتراضية
config = {
    "folderName": "Default"  # اسم المجلد الافتراضي
}

app = Flask(__name__)

# الصفحة الرئيسية
@app.route("/")
def index():
    return render_template("index.html")

# معالجة الصور وتحميلها كملف ZIP
@app.route("/process_and_download", methods=["POST"])
def process_and_download():
    # تأكد من وجود ملفات في الطلب
    if "images" not in request.files:
        return jsonify({"error": "No images uploaded"}), 400

    images = request.files.getlist("images")
    output_folder = config["folderName"]

    # إنشاء المجلد إذا لم يكن موجودًا
    os.makedirs(output_folder, exist_ok=True)

    processed_images = []

    # معالجة الصور
    for image in images:
        img = Image.open(image)
        text = pytesseract.image_to_string(img, lang="eng")  # استخراج النص
        processed_image_path = os.path.join(output_folder, f"processed_{image.filename}")
        img.save(processed_image_path, "JPEG")
        processed_images.append(processed_image_path)

    # إنشاء ملف ZIP
    zip_filename = "processed_images.zip"
    with zipfile.ZipFile(zip_filename, "w") as zipf:
        for file_path in processed_images:
            zipf.write(file_path, os.path.basename(file_path))

    # حذف الملفات المؤقتة
    for file_path in processed_images:
        os.remove(file_path)

    # إرسال ملف ZIP إلى المستخدم
    return send_file(zip_filename, as_attachment=True)

# بدء التطبيق
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
