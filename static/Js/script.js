document.getElementById("uploadForm").addEventListener("submit", async function (e) {
    e.preventDefault();

    const chapterLink = document.getElementById("chapterLink").value;
    const folderName = document.getElementById("folderName").value || "Default";
    const tags = document.getElementById("tags").value.split(",");

    const responseMessage = document.getElementById("responseMessage");
    responseMessage.textContent = "جارٍ معالجة الفصل...";

    try {
        const response = await fetch("/process_and_upload", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ chapterLink, folderName, tags }),
        });

        const result = await response.json();

        if (response.ok) {
            responseMessage.textContent = result.message;
        } else {
            responseMessage.textContent = `خطأ: ${result.error}`;
        }
    } catch (error) {
        responseMessage.textContent = `حدث خطأ أثناء الإرسال: ${error.message}`;
    }
});
  
