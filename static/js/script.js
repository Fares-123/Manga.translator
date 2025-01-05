document.getElementById("uploadForm").addEventListener("submit", async function (e) {
    e.preventDefault();  // منع إعادة تحميل الصفحة

    // جمع البيانات من الحقول
    const chapterLink = document.getElementById("chapterLink").value;
    const folderName = document.getElementById("folderName").value || "Default";
    const tags = document.getElementById("tags").value.split(",").map(tag => tag.trim());

    // منطقة عرض الرسالة أثناء المعالجة
    const responseMessage = document.getElementById("responseMessage");
    responseMessage.textContent = "جارٍ معالجة الفصل...";  // النص أثناء المعالجة
    responseMessage.style.display = "block";  // عرض الرسالة

    try {
        // إرسال البيانات إلى الخادم
        const response = await fetch("/process_and_upload", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ chapterLink, folderName, tags }),
        });

        // معالجة الرد من الخادم
        const result = await response.json();

        if (response.ok) {
            // عرض الرسالة عند النجاح
            responseMessage.textContent = result.message;
            displayResults(result.results);  // عرض النتائج في صفحة المستخدم
        } else {
            // عرض رسالة الخطأ إذا فشل الطلب
            responseMessage.textContent = `خطأ: ${result.error}`;
        }
    } catch (error) {
        // معالجة الأخطاء العامة
        responseMessage.textContent = `حدث خطأ أثناء الإرسال: ${error.message}`;
    }
});

// عرض النتائج بعد المعالجة
function displayResults(results) {
    const resultList = document.getElementById("resultList");
    resultList.innerHTML = "";  // تنظيف القائمة السابقة

    results.forEach((result, index) => {
        const listItem = document.createElement("li");
        listItem.innerHTML = `
            <p><strong>الصورة الأصلية ${index + 1}:</strong> ${result.original_image}</p>
            <p><strong>الصورة المترجمة:</strong> ${result.modified_image}</p>
        `;
        resultList.appendChild(listItem);
    });
}
