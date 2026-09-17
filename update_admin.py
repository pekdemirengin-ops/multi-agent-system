# -*- coding: utf-8 -*-
"""index.html'e admin paneli ekle."""
from pathlib import Path
import re

html_path = Path("static/index.html")
html = html_path.read_text(encoding="utf-8")

# Yedek al
backup = html_path.with_suffix(".html.adminbak")
backup.write_text(html, encoding="utf-8")
print(f"Yedek: {backup}")

# ============================================================
# 1) CSS EKLE (</style>'dan once)
# ============================================================
admin_css = """
/* ADMIN PANEL */
.admin-panel { flex: 1; overflow-y: auto; padding: 20px; display: none; }
.admin-panel.visible { display: block; }
.admin-panel h2 { color: #333; margin-bottom: 4px; font-size: 18px; }
.admin-panel .subtitle { color: #888; font-size: 13px; margin-bottom: 16px; }
.admin-actions { display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }
.admin-btn { padding: 8px 16px; background: #667eea; color: white; border: none;
border-radius: 8px; cursor: pointer; font-size: 13px; font-weight: 600; }
.admin-btn:hover { background: #5568d3; }
.admin-btn.danger { background: #ef4444; }
.admin-btn.danger:hover { background: #dc2626; }
.admin-btn.secondary { background: #f0f0f5; color: #555; }
.admin-btn.secondary:hover { background: #e0e0e8; }
.users-table { width: 100%; border-collapse: collapse; background: white;
border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
.users-table th { background: #f7f7fa; padding: 12px; text-align: left;
font-size: 12px; font-weight: 600; color: #555; text-transform: uppercase; }
.users-table td { padding: 12px; border-top: 1px solid #f0f0f5; font-size: 14px; color: #333; }
.users-table tr:hover { background: #fafafc; }
.role-badge { display: inline-block; padding: 3px 10px; border-radius: 12px;
font-size: 11px; font-weight: 700; }
.role-badge.admin { background: #fef3c7; color: #92400e; }
.role-badge.user { background: #e0e7ff; color: #3730a3; }
.add-user-form { background: #f7f7fa; border-radius: 12px; padding: 16px;
margin-bottom: 16px; display: none; }
.add-user-form.visible { display: block; }
.add-user-form h3 { font-size: 14px; margin-bottom: 12px; color: #333; }
.add-user-form input { width: 100%; padding: 10px 14px; border: 2px solid #e5e5ea;
border-radius: 8px; font-size: 14px; margin-bottom: 10px; outline: none; }
.add-user-form input:focus { border-color: #667eea; }
.add-user-form .form-row { display: flex; gap: 8px; }
.add-user-form .form-row button { flex: 0 0 auto; margin: 0; }
"""

# CSS ekle
html = html.replace("</style>", admin_css + "\n</style>", 1)

# ============================================================
# 2) HTML EKLE (input-area div'inin KAPANISINDAN sonra)
# ============================================================
admin_html = """
<!-- ADMIN PANEL -->
<div class="admin-panel" id="adminPanel">
  <h2>Kullanici Yonetimi</h2>
  <p class="subtitle">Kullanicilari yonetin, rol atayin, silin</p>
  <div class="admin-actions">
    <button class="admin-btn" onclick="toggleAddUserForm()">+ Yeni Kullanici</button>
    <button class="admin-btn secondary" onclick="loadUsers()">Yenile</button>
    <button class="admin-btn secondary" onclick="closeAdminPanel()">Kapat</button>
  </div>
  <div class="add-user-form" id="addUserForm">
    <h3>Yeni Kullanici Ekle</h3>
    <input type="text" id="newUsername" placeholder="Kullanici adi (min 3 karakter)">
    <input type="password" id="newPassword" placeholder="Sifre (min 6 karakter)">
    <div class="form-row">
      <button class="admin-btn" onclick="addUser()">Ekle</button>
      <button class="admin-btn secondary" onclick="toggleAddUserForm()">Iptal</button>
    </div>
  </div>
  <table class="users-table">
    <thead>
      <tr>
        <th>Kullanici</th>
        <th>Rol</th>
        <th>Olusturma</th>
        <th>Islemler</th>
      </tr>
    </thead>
    <tbody id="usersTableBody">
      <tr><td colspan="4" style="text-align:center;color:#888;">Yukleniyor...</td></tr>
    </tbody>
  </table>
</div>
"""

# chat div'inin kapanisindan SONRA, input-area'dan ONCE ekle
# input-area div'inin baslangicini bul
marker = '<div class="input-area">'
html = html.replace(marker, admin_html + "\n" + marker, 1)

# Header'a admin butonu ekle (streamingToggle'dan once)
admin_btn = '<button class="header-btn" id="adminToggle" title="Kullanici Yonetimi" style="display:none;" onclick="toggleAdminPanel()">ADMIN</button>\n'
html = html.replace('<button class="header-btn" id="streamingToggle"', admin_btn + '<button class="header-btn" id="streamingToggle"', 1)

# ============================================================
# 3) JS EKLE (INIT bolumunden once)
# ============================================================
admin_js = """
// ============================================================
// ADMIN PANEL
// ============================================================
let currentUserRole = "user";

async function loadCurrentUserInfo() {
try {
const res = await fetch(`${API_BASE}/api/auth/me`, { headers: authHeaders() });
if (!res.ok) return;
const user = await res.json();
currentUserRole = user.role || "user";
if (currentUserRole === "admin") {
const adminBtn = document.getElementById("adminToggle");
if (adminBtn) adminBtn.style.display = "block";
}
} catch (e) { console.error("loadCurrentUserInfo:", e); }
}

function toggleAdminPanel() {
const panel = document.getElementById("adminPanel");
const chat = document.getElementById("chat");
const inputArea = document.querySelector(".input-area");
const agentsBar = document.getElementById("agentsBar");
const isVisible = panel.classList.contains("visible");
if (isVisible) {
closeAdminPanel();
} else {
panel.classList.add("visible");
chat.style.display = "none";
inputArea.style.display = "none";
agentsBar.style.display = "none";
loadUsers();
}
}

function closeAdminPanel() {
document.getElementById("adminPanel").classList.remove("visible");
document.getElementById("chat").style.display = "flex";
document.querySelector(".input-area").style.display = "flex";
document.getElementById("agentsBar").style.display = "flex";
}

function toggleAddUserForm() {
document.getElementById("addUserForm").classList.toggle("visible");
}

async function loadUsers() {
const tbody = document.getElementById("usersTableBody");
tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:#888;">Yukleniyor...</td></tr>';
try {
const res = await fetch(`${API_BASE}/api/auth/users`, { headers: authHeaders() });
if (!res.ok) {
const err = await res.json();
tbody.innerHTML = `<tr><td colspan="4" style="text-align:center;color:#ef4444;">${err.detail || "Hata"}</td></tr>`;
return;
}
const data = await res.json();
if (!data.users || data.users.length === 0) {
tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:#888;">Kullanici yok</td></tr>';
return;
}
tbody.innerHTML = "";
data.users.forEach(u => {
const tr = document.createElement("tr");
const roleClass = u.role === "admin" ? "admin" : "user";
const created = (u.created_at || "").slice(0, 10);
const isAdmin = u.role === "admin";
tr.innerHTML = `
<td><strong>${escapeHtml(u.username)}</strong></td>
<td><span class="role-badge ${roleClass}">${u.role}</span></td>
<td>${created || "-"}</td>
<td>
${isAdmin ? '<span style="color:#888;font-size:12px;">-</span>' : `
<button class="admin-btn secondary" onclick="changeRole('${escapeHtml(u.username)}', '${isAdmin ? "user" : "admin"}')">
${isAdmin ? "User Yap" : "Admin Yap"}
</button>
<button class="admin-btn danger" onclick="deleteUser('${escapeHtml(u.username)}')">Sil</button>
`}
</td>
`;
tbody.appendChild(tr);
});
} catch (e) {
tbody.innerHTML = `<tr><td colspan="4" style="text-align:center;color:#ef4444;">Baglanti hatasi: ${e.message}</td></tr>`;
}
}

async function addUser() {
const username = document.getElementById("newUsername").value.trim();
const password = document.getElementById("newPassword").value;
if (!username || username.length < 3) { alert("Kullanici adi min 3 karakter"); return; }
if (!password || password.length < 6) { alert("Sifre min 6 karakter"); return; }
try {
const res = await fetch(`${API_BASE}/api/auth/register`, {
method: "POST",
headers: { "Content-Type": "application/json" },
body: JSON.stringify({ username, password })
});
if (!res.ok) {
const err = await res.json();
alert("Hata: " + (err.detail || "Bilinmeyen"));
return;
}
document.getElementById("newUsername").value = "";
document.getElementById("newPassword").value = "";
toggleAddUserForm();
loadUsers();
} catch (e) { alert("Baglanti hatasi: " + e.message); }
}

async function changeRole(username, newRole) {
if (!confirm(`${username} -> ${newRole}?`)) return;
try {
const res = await fetch(`${API_BASE}/api/auth/users/${encodeURIComponent(username)}/role`, {
method: "PATCH",
headers: authHeaders(),
body: JSON.stringify({ role: newRole })
});
if (!res.ok) {
const err = await res.json();
alert("Hata: " + (err.detail || "Bilinmeyen"));
return;
}
loadUsers();
} catch (e) { alert("Baglanti hatasi: " + e.message); }
}

async function deleteUser(username) {
if (!confirm(`${username} silinsin mi?`)) return;
try {
const res = await fetch(`${API_BASE}/api/auth/users/${encodeURIComponent(username)}`, {
method: "DELETE",
headers: authHeaders()
});
if (!res.ok) {
const err = await res.json();
alert("Hata: " + (err.detail || "Bilinmeyen"));
return;
}
loadUsers();
} catch (e) { alert("Baglanti hatasi: " + e.message); }
}

// ============================================================
// INIT
// ============================================================
"""

# INIT yorumundan once ekle (son INIT'i bul)
init_marker = "// ============================================================\n// INIT\n// ============================================================"
if init_marker in html:
    html = html.replace(init_marker, admin_js + init_marker, 1)
    print("Admin JS eklendi (INIT'ten once)")
else:
    print("UYARI: INIT marker bulunamadi!")

# ============================================================
# 4) showMainApp'e rol yukleme ekle
# ============================================================
old_show = '''function showMainApp() {
loginScreen.style.display = "none";
mainApp.classList.add("visible");
userInfo.textContent = currentUser;
loadAgents();
loadHistory();
messageInput.focus();
}'''

new_show = '''function showMainApp() {
loginScreen.style.display = "none";
mainApp.classList.add("visible");
userInfo.textContent = currentUser;
loadAgents();
loadCurrentUserInfo();
messageInput.focus();
}'''

if old_show in html:
    html = html.replace(old_show, new_show, 1)
    print("showMainApp guncellendi (loadCurrentUserInfo eklendi)")
else:
    print("UYARI: showMainApp bulunamadi!")

# Dosyayi kaydet
html_path.write_text(html, encoding="utf-8")
print(f"OK: {html_path} guncellendi")
print(f"Yeni boyut: {len(html)} karakter")
