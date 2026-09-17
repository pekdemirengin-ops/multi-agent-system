from pathlib import Path

html_path = Path("static/index.html")
html = html_path.read_text(encoding="utf-8")

# Eski: isAdmin ise sil butonu yok
old_block = """${isAdmin ? '<span style="color:#888;font-size:12px;">-</span>' : `
<button class="admin-btn secondary" onclick="changeRole('${escapeHtml(u.username)}', '${isAdmin ? "user" : "admin"}')">
${isAdmin ? "User Yap" : "Admin Yap"}
</button>
<button class="admin-btn danger" onclick="deleteUser('${escapeHtml(u.username)}')">Sil</button>
`}"""

# Yeni: sadece "admin" kullanicisi korunuyor
new_block = """${u.username === "admin" ? '<span style="color:#888;font-size:12px;">-</span>' : `
<button class="admin-btn secondary" onclick="changeRole('${escapeHtml(u.username)}', '${isAdmin ? "user" : "admin"}')">
${isAdmin ? "User Yap" : "Admin Yap"}
</button>
<button class="admin-btn danger" onclick="deleteUser('${escapeHtml(u.username)}')">Sil</button>
`}"""

if old_block in html:
    html = html.replace(old_block, new_block, 1)
    html_path.write_text(html, encoding="utf-8")
    print("OK: UI duzeltildi")
else:
    print("HATA: Eski blok bulunamadi!")
    print("changeRole etrafinda ne var:")
    idx = html.find("changeRole(")
    if idx > 0:
        print(repr(html[idx-200:idx+400]))
