document.getElementById("processForm").addEventListener("submit", async (e) => {
    e.preventDefault();

    const chapterLink = document.getElementById("chapterLink").value;
    const folderName = document.getElementById("folderName").value;

    if (!chapterLink || !folderName) {
        alert("يرجى إدخال جميع الحقول المطلوبة.");
        return;
    }

    const requestData = {
        chapterLink: chapterLink,
        folderName: folderName,
    };

    try {
        const response = await fetch("/process_and_download", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(requestData),
        });

        if (response.ok) {
            const blob = await response.blob();
            const downloadLink = document.createElement("a");
            downloadLink.href = URL.createObjectURL(blob);
            downloadLink.download = "translated_images.zip";
            downloadLink.click();
            document.getElementById("responseMessage").textContent = "تم معالجة الصور بنجاح!";
        } else {
            const errorData = await response.json();
            document.getElementById("responseMessage").textContent = `خطأ: ${errorData.error}`;
        }
    } catch (error) {
        console.error("Error:", error);
        document.getElementById("responseMessage").textContent = "حدث خطأ أثناء المعالجة.";
    }
});
