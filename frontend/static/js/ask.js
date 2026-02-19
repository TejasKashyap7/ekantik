async function submitQuestion() {
  const input = document.getElementById("question");
  const output = document.getElementById("output");
  const button = document.getElementById("submitBtn");

  const query = input.value.trim();
  if (!query) {
    alert("कृपया प्रश्न लिखें।");
    return;
  }

  output.innerHTML = "Ekantik Vartalap संदर्भ खोजे जा रहे हैं…";
  button.disabled = true;

  try {
    const response = await fetch(`/query?query=${encodeURIComponent(query)}`, {
      method: "POST",
      headers: { "accept": "application/json" }
    });

    if (!response.ok) {
      throw new Error("Request failed");
    }

    const text = await response.text();
    output.innerHTML = text.replace(/\\n/g, "<br>");

  } catch (err) {
    output.innerHTML =
      "उत्तर प्राप्त नहीं हो सका। कृपया स्पष्ट आध्यात्मिक प्रश्न पूछें।";
  } finally {
    button.disabled = false;
  }
}
