from pathlib import Path

html_path = Path("static/index.html")
html = html_path.read_text(encoding="utf-8")

old_speak = """function speak(text) {
if (!ttsEnabled || !("speechSynthesis" in window)) return;
window.speechSynthesis.cancel();
const clean = text.replace(/```[\\s\\S]*?```/g, " kod blogu ").replace(/[*_`#]/g, "");
const utter = new SpeechSynthesisUtterance(clean);
utter.lang = "tr-TR";
utter.rate = 1.0;
const voices = window.speechSynthesis.getVoices();
const trVoice = voices.find(v => v.lang.startsWith("tr"));
if (trVoice) utter.voice = trVoice;
window.speechSynthesis.speak(utter);
}"""

new_speak = """function speak(text) {
if (!ttsEnabled || !("speechSynthesis" in window)) return;
window.speechSynthesis.cancel();
let clean = text;
clean = clean.replace(/```[\\s\\S]*?```/g, " kod blogu ");
clean = clean.replace(/https?:\\/\\/[^\\s]+/g, "");
clean = clean.replace(/(\\d{4})-(\\d{2})-(\\d{2})/g, (m, y, mo, d) => {
const months = ["Ocak","Subat","Mart","Nisan","Mayis","Haziran","Temmuz","Agustos","Eylul","Ekim","Kasim","Aralik"];
return parseInt(d) + " " + months[parseInt(mo)-1] + " " + y;
});
clean = clean.replace(/URL\\s*:/gi, "");
clean = clean.replace(/[*_`#>~|]/g, " ");
clean = clean.replace(/[-_\\/]/g, " ");
clean = clean.replace(/\\.{2,}/g, ".");
clean = clean.replace(/\\s{2,}/g, " ");
clean = clean.trim();
if (!clean) return;
const utter = new SpeechSynthesisUtterance(clean);
utter.lang = "tr-TR";
utter.rate = 1.05;
utter.pitch = 1.0;
const voices = window.speechSynthesis.getVoices();
const trVoice = voices.find(v => v.lang.startsWith("tr"));
if (trVoice) utter.voice = trVoice;
window.speechSynthesis.speak(utter);
}"""

if old_speak in html:
    html = html.replace(old_speak, new_speak, 1)
    html_path.write_text(html, encoding="utf-8")
    print("OK: TTS duzeltildi.")
else:
    print("HATA: Eski speak() bulunamadi")
