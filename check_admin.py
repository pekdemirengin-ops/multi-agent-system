from pathlib import Path
html = Path("static/index.html").read_text(encoding="utf-8")
checks = {
    "adminPanel div": 'id="adminPanel"' in html,
    "adminToggle btn": 'id="adminToggle"' in html,
    "loadUsers func": "async function loadUsers()" in html,
    "loadCurrentUserInfo": "loadCurrentUserInfo" in html,
    "admin CSS": ".admin-panel" in html,
    "usersTable": 'id="usersTableBody"' in html,
}
for k, v in checks.items():
    print(("OK   " if v else "HATA ") + k)

# Ekstra: encoding, toplam boyut
print()
print("Toplam boyut:", len(html), "karakter")
print("Admin JS var mi:", "loadCurrentUserInfo" in html)
