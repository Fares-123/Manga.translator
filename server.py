from flask import Flask, render_template, request, jsonify
import requests
from io import BytesIO
from PIL import Image
import pytesseract

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/process_and_download', methods=['POST'])
def process_and_download():
    # الحصول على روابط الصور من الطلب
    image_urls = request.json.get("image_urls", [])
    
    if not image_urls:
        return jsonify({"error": "No image URLs provided"}), 400

    processed_images = []

    for url in image_urls:
        try:
            # جلب الصورة من الرابط
            response = requests.get(url, stream=True)
            response.raise_for_status()
            image = Image.open(BytesIO(response.content))
            
            # تشغيل OCR لاستخراج النصوص من الصورة
            extracted_text = pytesseract.image_to_string(image, lang="eng")
            
            # إضافة النتائج إلى القائمة
            processed_images.append({"url": url, "extracted_text": extracted_text})

        except requests.exceptions.RequestException as e:
            processed_images.append({"url": url, "error": f"Failed to fetch image: {str(e)}"})
        except Exception as e:
            processed_images.append({"url": url, "error": f"Processing error: {str(e)}"})

    return jsonify({"processed_images": processed_images}), 200

if __name__ == '__main__':
    app.run(debug=True)
