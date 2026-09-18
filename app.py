from flask import Flask, request, render_template_string, jsonify, send_file
from google.cloud import storage, firestore
from firebase_admin import auth
import firebase_admin
from datetime import datetime, timezone
import io
import os
import uuid
import json
import mimetypes
import hashlib
import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image as PDFImage
)

app = Flask(__name__)

BUCKET_NAME = "digital-document-verification-455749068291"
ADMIN_DISPLAY_NAME = "Admin"
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

ALLOWED_EXTENSIONS = {
    ".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx"
}

FIREBASE_CONFIG = {
    "apiKey": "AIzaSyAEpaLu_-IQPN-bNNe0LSNAESzWe73NZLM",
    "authDomain": "digital-document-verification.firebaseapp.com",
    "projectId": "digital-document-verification",
    "storageBucket": "digital-document-verification.firebasestorage.app",
    "messagingSenderId": "455749068291",
    "appId": "1:455749068291:web:1903e4a720a16e13d19036",
}

if not firebase_admin._apps:
    firebase_admin.initialize_app()

storage_client = storage.Client()
db = firestore.Client()
bucket = storage_client.bucket(BUCKET_NAME)



VERIFY_HTML = """
<!DOCTYPE html>
<html>
<head>

<title>Document Verification</title>

<meta name="viewport" content="width=device-width, initial-scale=1">

<style>

body {
    margin: 0;
    font-family: Arial, sans-serif;
    background: #f4f7fb;
    color: #1f2937;
}

.header {
    background: #1769e0;
    color: white;
    padding: 28px 5%;
}

.header h1 {
    margin: 0 0 6px;
}

.header p {
    margin: 0;
    opacity: .9;
}

.container {
    width: 90%;
    max-width: 850px;
    margin: 40px auto;
}

.card {
    background: white;
    padding: 35px;
    border-radius: 16px;
    box-shadow: 0 5px 20px #00000012;
}

.badge {
    display: inline-block;
    padding: 9px 16px;
    border-radius: 30px;
    background: #dcfce7;
    color: #15803d;
    font-weight: bold;
    margin-bottom: 15px;
}

.row {
    display: grid;
    grid-template-columns: 190px 1fr;
    gap: 15px;
    padding: 14px 0;
    border-bottom: 1px solid #e5e7eb;
}

.label {
    color: #6b7280;
    font-weight: bold;
}

.verify-id,
.fingerprint {
    font-family: monospace;
}

.qr {
    text-align: center;
    margin-top: 30px;
    padding-top: 25px;
    border-top: 1px solid #e5e7eb;
}

.qr img {
    width: 220px;
    height: 220px;
}

@media(max-width: 650px) {
    .row {
        grid-template-columns: 1fr;
        gap: 5px;
    }
}

</style>

</head>

<body>

<div class="header">

    <h1>Digital Document Verification</h1>

    <p>Public verification portal</p>

</div>

<div class="container">

{% if document %}

<div class="card">

    <div class="badge">
        ✓ VERIFIED
    </div>

    <h2>Document Authenticity Confirmed</h2>

    <div class="row">
        <div class="label">Document</div>
        <div>{{ document.filename }}</div>
    </div>

    <div class="row">
        <div class="label">Verification ID</div>
        <div class="verify-id">
            {{ document.verification_id }}
        </div>
    </div>

    <div class="row">
        <div class="label">Status</div>
        <div>Verified</div>
    </div>

    <div class="row">
        <div class="label">Verified By</div>
        <div>{{ document.reviewer }}</div>
    </div>

    <div class="row">
        <div class="label">Verification Date</div>
        <div>{{ document.reviewed }}</div>
    </div>

    <div class="row">
        <div class="label">SHA-256 Fingerprint</div>
        <div class="fingerprint">
            {{ document.file_hash }}
        </div>
    </div>

    <div class="qr">

        <h3>Scan to Verify</h3>

        <img
            src="/api/qr/{{ document.verification_id }}"
            alt="Verification QR Code"
        >

        <p>
            Scan this QR code to verify this document.
        </p>

    </div>

</div>

{% else %}

<div class="card">

    <h2>Verification Not Found</h2>

    <p>
        The verification ID is invalid or the document
        has not been verified.
    </p>

</div>

{% endif %}

</div>

</body>
</html>
"""

HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Digital Document Verification</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
*{box-sizing:border-box}
body{margin:0;font-family:Arial,sans-serif;background:#f4f7fb;color:#1f2937}
.auth-loading #loginPage{visibility:hidden}
.auth-loading{overflow:hidden}
.header{background:#1769e0;color:#fff;padding:26px 5%;display:flex;justify-content:space-between;align-items:center;gap:20px}
.header h1{margin:0 0 6px;font-size:30px}
.header p{margin:0;opacity:.9}
.header-right{display:flex;align-items:center;gap:10px}
.user-email{font-size:14px;opacity:.9}
button,input,select{padding:11px 14px;border-radius:7px;font-size:15px}
button{background:#1769e0;color:#fff;border:none;cursor:pointer}
button:hover{background:#0d55bd}
.logout{background:#fff;color:#1769e0}
.logout:hover{background:#eef4ff}
.container{width:90%;max-width:1400px;margin:30px auto}
.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:18px;margin-bottom:25px}
.card,.panel{background:#fff;border-radius:12px;box-shadow:0 3px 12px #00000012}
.card{padding:22px}
.card h3{margin:0;color:#6b7280;font-size:15px}
.number{font-size:32px;font-weight:bold;margin-top:10px}
.panel{padding:25px;margin-bottom:25px}
.upload form{display:flex;gap:12px;flex-wrap:wrap;align-items:center}
input,select{border:1px solid #d1d5db}
.controls{display:flex;gap:12px;margin-bottom:18px}
.controls input{flex:1}
.table-wrapper{overflow-x:auto}
table{width:100%;border-collapse:collapse;min-width:950px}
th{background:#1769e0;color:#fff;padding:14px;text-align:left}
td{padding:14px;border-bottom:1px solid #e5e7eb;vertical-align:middle}
.filename{max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.status{display:inline-block;padding:6px 12px;border-radius:20px;font-weight:bold;font-size:13px}
.pending{background:#fff4cc;color:#d97706}.verified{background:#dcfce7;color:#15803d}.rejected{background:#fee2e2;color:#dc2626}
.action{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.reject{background:#dc2626}.reject:hover{background:#b91c1c}
.download{background:#374151}.download:hover{background:#1f2937}
.completed{color:#6b7280;font-size:14px}
.reason{margin-top:7px;color:#b91c1c;font-size:13px;white-space:normal}
.fingerprint{font-family:monospace;font-size:12px;color:#4b5563}
.empty{text-align:center;padding:30px;color:#6b7280}
.hidden{display:none!important}
.login-wrapper{min-height:100vh;display:flex;align-items:center;justify-content:center;padding:25px}
.login-card{width:100%;max-width:480px;background:#fff;padding:35px;border-radius:16px;box-shadow:0 8px 30px #00000018}
.login-card h1{margin-top:0;color:#1769e0}.login-subtitle{color:#6b7280;margin-bottom:25px}
.role-buttons{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:20px}
.role-btn{background:#eef4ff;color:#1769e0;border:1px solid #cfe0ff}.role-btn.active{background:#1769e0;color:#fff}
.login-card form{display:grid;gap:12px}.login-card input{width:100%}
.secondary-btn{background:#374151}.toggle-text{text-align:center;color:#6b7280;margin-top:18px;font-size:14px}.link{color:#1769e0;cursor:pointer;font-weight:bold}
.message{margin-top:15px;padding:12px;border-radius:8px;display:none}.error{background:#fee2e2;color:#b91c1c}
@media(max-width:800px){.cards{grid-template-columns:repeat(2,1fr)}.header{flex-direction:column;align-items:flex-start}}
@media(max-width:500px){.cards{grid-template-columns:1fr}.container{width:94%}.login-card{padding:25px}}
</style>
</head>
<body class="auth-loading">

<div id="loginPage" class="login-wrapper">
  <div class="login-card">
    <h1>Digital Document Verification</h1>
    <div class="login-subtitle">Secure document verification platform</div>

    <div class="role-buttons">
      <button id="userRoleBtn" class="role-btn active" onclick="selectRole('user')">User Login</button>
      <button id="adminRoleBtn" class="role-btn" onclick="selectRole('admin')">Admin Login</button>
    </div>

    <form id="loginForm">
      <input id="email" type="email" placeholder="Email address" required>
      <input id="password" type="password" placeholder="Password" required>
      <button type="submit">Sign In</button>
    </form>

    <div id="message" class="message"></div>

    <div id="signupToggle" class="toggle-text">
      Don't have an account?
      <span class="link" onclick="showSignup()">Create User Account</span>
    </div>

    <form id="signupForm" class="hidden">
      <input id="signupEmail" type="email" placeholder="Email address" required>
      <input id="signupPassword" type="password" placeholder="Password (6+ characters)" minlength="6" required>
      <button type="submit">Create User Account</button>
      <button type="button" class="secondary-btn" onclick="showLogin()">Back to Login</button>
    </form>
  </div>
</div>

<div id="dashboard" class="hidden">
  <div class="header">
    <div>
      <h1>Digital Document Verification System</h1>
      <p id="dashboardSubtitle"></p>
    </div>
    <div class="header-right">
      <span id="currentEmail" class="user-email"></span>
      <button id="auditButton" class="logout hidden" onclick="openAuditLog()">Audit Log</button>
      <button class="logout" onclick="logout()">Logout</button>
    </div>
  </div>

  <div class="container">
    <div id="summaryCards" class="cards hidden">
      <div class="card"><h3>Total Documents</h3><div id="totalCount" class="number">0</div></div>
      <div class="card"><h3>Pending</h3><div id="pendingCount" class="number">0</div></div>
      <div class="card"><h3>Verified</h3><div id="verifiedCount" class="number">0</div></div>
      <div class="card"><h3>Rejected</h3><div id="rejectedCount" class="number">0</div></div>
    </div>

    <div id="uploadPanel" class="panel upload">
      <h2>Upload Document</h2>
      <form id="uploadForm">
        <input id="userName" type="text" placeholder="Your name" required>
        <input id="fileInput" type="file" accept=".pdf,.jpg,.jpeg,.png,.doc,.docx" required>
        <button type="submit">Upload Document</button>
      </form>
    </div>

    <div class="panel">
      <h2 id="recordsTitle">My Documents</h2>
      <div class="controls">
        <input id="search" type="text" placeholder="Search by filename or user..." onkeyup="filterTable()">
        <select id="statusFilter" onchange="filterTable()">
          <option value="All">All Status</option>
          <option value="Pending">Pending</option>
          <option value="Verified">Verified</option>
          <option value="Rejected">Rejected</option>
        </select>
      </div>

      <div class="table-wrapper">
        <table id="documents">
          <thead>
            <tr>
              <th>File</th>
              <th>User</th>
              <th>Status</th>
              <th>Reviewer</th>
              <th>Uploaded</th>
              <th>Reviewed</th>
              <th id="fingerprintHeader" class="hidden">Fingerprint</th>
              <th id="verificationHeader" class="hidden">Verification ID</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody id="documentBody"></tbody>
        </table>
      </div>
    </div>
  </div>
</div>

<script type="module">
import { initializeApp } from "https://www.gstatic.com/firebasejs/12.9.0/firebase-app.js";
import {
  getAuth,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signOut,
  onAuthStateChanged
} from "https://www.gstatic.com/firebasejs/12.9.0/firebase-auth.js";

const firebaseConfig = {{ firebase_config | safe }};
const firebaseApp = initializeApp(firebaseConfig);
const auth = getAuth(firebaseApp);

let selectedRole = localStorage.getItem("selectedRole") || "user";
if (selectedRole !== "user" && selectedRole !== "admin") selectedRole = "user";

function updateRoleButtons() {
  document.getElementById("userRoleBtn").classList.toggle("active", selectedRole === "user");
  document.getElementById("adminRoleBtn").classList.toggle("active", selectedRole === "admin");
}

function showMessage(text) {
  const box = document.getElementById("message");
  box.textContent = text;
  box.className = "message error";
  box.style.display = "block";
}

function hideMessage() {
  const box = document.getElementById("message");
  box.textContent = "";
  box.style.display = "none";
}

function resetDashboardUI() {
  document.getElementById("uploadPanel").classList.remove("hidden");
  document.getElementById("summaryCards").classList.add("hidden");
  document.getElementById("auditButton").classList.add("hidden");
  document.getElementById("fingerprintHeader").classList.add("hidden");
  document.getElementById("verificationHeader").classList.add("hidden");
  document.getElementById("recordsTitle").textContent = "My Documents";
  document.getElementById("dashboardSubtitle").textContent = "";
  document.getElementById("documentBody").innerHTML = "";
  document.getElementById("search").value = "";
  document.getElementById("statusFilter").value = "All";
}

window.selectRole = function(role) {
  selectedRole = role;
  localStorage.setItem("selectedRole", role);
  updateRoleButtons();
  hideMessage();
};

window.showSignup = function() {
  if (selectedRole === "admin") {
    showMessage("Admin accounts are created by the system administrator.");
    return;
  }
  hideMessage();
  document.getElementById("loginForm").classList.add("hidden");
  document.getElementById("signupToggle").classList.add("hidden");
  document.getElementById("signupForm").classList.remove("hidden");
};

window.showLogin = function() {
  hideMessage();
  document.getElementById("signupForm").classList.add("hidden");
  document.getElementById("loginForm").classList.remove("hidden");
  document.getElementById("signupToggle").classList.remove("hidden");
};

document.getElementById("loginForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  hideMessage();
  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;
  try {
    await signInWithEmailAndPassword(auth, email, password);
  } catch (error) {
    showMessage(error.code || error.message);
  }
});

document.getElementById("signupForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  hideMessage();
  const email = document.getElementById("signupEmail").value.trim();
  const password = document.getElementById("signupPassword").value;
  try {
    await createUserWithEmailAndPassword(auth, email, password);
  } catch (error) {
    showMessage(error.code || error.message);
  }
});

onAuthStateChanged(auth, async (user) => {
  try {
    if (!user) {
      document.body.classList.remove("auth-loading");
      document.getElementById("loginPage").classList.remove("hidden");
      document.getElementById("dashboard").classList.add("hidden");
      resetDashboardUI();
      updateRoleButtons();
      return;
    }

    const tokenResult = await user.getIdTokenResult(true);
    const isAdmin = tokenResult.claims.admin === true;

    // When returning from /audit, the Firebase session is still active.
    // Trust the token claim rather than forcing the stale user-role state.
    if (isAdmin) {
      selectedRole = "admin";
      localStorage.setItem("selectedRole", "admin");
    } else {
      selectedRole = "user";
      localStorage.setItem("selectedRole", "user");
    }

    document.getElementById("loginPage").classList.add("hidden");
    document.getElementById("dashboard").classList.remove("hidden");
    document.getElementById("currentEmail").textContent = user.email || "";
    resetDashboardUI();

    if (isAdmin) {
      document.getElementById("dashboardSubtitle").textContent = "Administrator verification dashboard";
      document.getElementById("recordsTitle").textContent = "All Document Records";
      document.getElementById("uploadPanel").classList.add("hidden");
      document.getElementById("summaryCards").classList.remove("hidden");
      document.getElementById("auditButton").classList.remove("hidden");
      document.getElementById("fingerprintHeader").classList.remove("hidden");
      document.getElementById("verificationHeader").classList.remove("hidden");
      await loadDocuments(true);
    } else {
      document.getElementById("dashboardSubtitle").textContent = "User document submission dashboard";
      document.getElementById("recordsTitle").textContent = "My Documents";
      document.getElementById("uploadPanel").classList.remove("hidden");
      document.getElementById("summaryCards").classList.add("hidden");
      document.getElementById("auditButton").classList.add("hidden");
      await loadDocuments(false);
    }
  } catch (error) {
    await signOut(auth);
    localStorage.removeItem("selectedRole");
    document.body.classList.remove("auth-loading");
    showMessage("Authentication failed. Please try again.");
  }
});

async function apiFetch(url, options = {}) {
  const user = auth.currentUser;
  if (!user) throw new Error("You are not signed in.");
  const token = await user.getIdToken();
  options.headers = {...(options.headers || {}), Authorization: "Bearer " + token};
  return fetch(url, options);
}

async function loadDocuments(admin) {
  const endpoint = admin ? "/api/documents" : "/api/my-documents";
  const response = await apiFetch(endpoint);
  if (!response.ok) throw new Error(await response.text());
  const data = await response.json();
  renderDocuments(data.documents, admin);

  if (admin) {
    document.getElementById("totalCount").textContent = data.total;
    document.getElementById("pendingCount").textContent = data.pending;
    document.getElementById("verifiedCount").textContent = data.verified;
    document.getElementById("rejectedCount").textContent = data.rejected;
  }
}

function renderDocuments(documents, admin) {
  const body = document.getElementById("documentBody");
  body.innerHTML = "";

  if (!documents.length) {
    body.innerHTML = `<tr><td colspan="${admin ? 9 : 7}" class="empty">No documents found.</td></tr>`;
    return;
  }

  documents.forEach((doc) => {
    const row = document.createElement("tr");

    let action = "";
    if (admin && doc.status === "Pending") {
      action = `
        <div class="action">
          <button onclick="reviewDocument('${doc.id}','verify')">Verify</button>
          <button class="reject" onclick="rejectDocument('${doc.id}')">Reject</button>
        </div>`;
    } else {
      action = `
        <div class="action">
          <button class="download" onclick="viewDocument('${doc.id}')">View</button>
                ${
                    doc.status === "Verified" && doc.verification_id
                    ? `<button class="download" onclick="downloadCertificate('${doc.id}')">Certificate PDF</button>`
                    : ""
                }
          ${doc.status !== "Pending" ? '<span class="completed">Completed</span>' : ""}
        </div>`;
    }

    const reason = doc.rejectionReason
      ? `<div class="reason">Reason: ${escapeHtml(doc.rejectionReason)}</div>`
      : "";

    const fingerprint = admin
      ? `<td class="fingerprint" title="${escapeHtml(doc.file_hash || "")}">${doc.file_hash ? escapeHtml(doc.file_hash.slice(0, 16) + "...") : "-"}</td>`
      : "";

    const verification = admin
      ? `<td class="fingerprint">${escapeHtml(doc.verification_id || "-")}</td>`
      : "";

    row.innerHTML = `
      <td class="filename" title="${escapeHtml(doc.filename)}">${escapeHtml(doc.filename)}${reason}</td>
      <td>${escapeHtml(doc.user)}</td>
      <td><span class="status ${doc.status.toLowerCase()}">${escapeHtml(doc.status)}</span></td>
      <td>${escapeHtml(doc.reviewer || "-")}</td>
      <td>${escapeHtml(doc.uploaded || "-")}</td>
      <td>${escapeHtml(doc.reviewed || "-")}</td>
      ${fingerprint}
      ${verification}
      <td>${action}</td>`;

    body.appendChild(row);
  });
}

window.viewDocument = async function(docId) {
  try {
    const response = await apiFetch("/api/download/" + docId);
    if (!response.ok) throw new Error(await response.text());
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    window.open(url, "_blank");
  } catch (error) {
    alert(error.message);
  }
};

window.downloadCertificate = async function(docId) {

    try {

        const response = await apiFetch(
            "/api/certificate/" + docId
        );

        if (!response.ok) {
            throw new Error(
                await response.text()
            );
        }

        const blob = await response.blob();

        const url = URL.createObjectURL(blob);

        const link = document.createElement("a");

        link.href = url;
        link.download = "Verification_Certificate.pdf";

        document.body.appendChild(link);

        link.click();

        link.remove();

        URL.revokeObjectURL(url);

    } catch (error) {

        alert(error.message);

    }

};


window.reviewDocument = async function(docId, action) {
  try {
    const formData = new URLSearchParams();
    formData.append("action", action);
    const response = await apiFetch("/api/review/" + docId, {
      method: "POST",
      headers: {"Content-Type": "application/x-www-form-urlencoded"},
      body: formData
    });
    if (!response.ok) throw new Error(await response.text());
    await loadDocuments(true);
  } catch (error) {
    alert(error.message);
  }
};

window.rejectDocument = async function(docId) {
  const reason = prompt("Enter rejection reason:");
  if (!reason || !reason.trim()) return;

  try {
    const formData = new URLSearchParams();
    formData.append("action", "reject");
    formData.append("reason", reason.trim());
    const response = await apiFetch("/api/review/" + docId, {
      method: "POST",
      headers: {"Content-Type": "application/x-www-form-urlencoded"},
      body: formData
    });
    if (!response.ok) throw new Error(await response.text());
    await loadDocuments(true);
  } catch (error) {
    alert(error.message);
  }
};

document.getElementById("uploadForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const file = document.getElementById("fileInput").files[0];
  const name = document.getElementById("userName").value.trim();
  if (!file) {
    alert("Please select a file.");
    return;
  }

  const formData = new FormData();
  formData.append("file", file);
  formData.append("user", name);

  try {
    const response = await apiFetch("/api/upload", {method: "POST", body: formData});
    if (!response.ok) throw new Error(await response.text());
    event.target.reset();
    await loadDocuments(false);
    alert("Document uploaded successfully.");
  } catch (error) {
    alert(error.message);
  }
});

window.openAuditLog = function() {
  localStorage.setItem("selectedRole", "admin");
  window.location.href = "/audit";
};

window.logout = async function() {
  await signOut(auth);
  localStorage.removeItem("selectedRole");
  selectedRole = "user";
  updateRoleButtons();
  resetDashboardUI();
  showLogin();
};

window.filterTable = function() {
  const search = document.getElementById("search").value.toLowerCase();
  const status = document.getElementById("statusFilter").value;

  document.querySelectorAll("#documentBody tr").forEach((row) => {
    const text = row.innerText.toLowerCase();
    const rowStatus = row.cells[2] ? row.cells[2].innerText.trim() : "";
    const matchesSearch = text.includes(search);
    const matchesStatus = status === "All" || rowStatus === status;
    row.style.display = matchesSearch && matchesStatus ? "" : "none";
  });
};

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

updateRoleButtons();
</script>
</body>
</html>
"""


AUDIT_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Audit Log - Digital Document Verification</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
*{box-sizing:border-box}
body{margin:0;font-family:Arial,sans-serif;background:#f4f7fb;color:#1f2937}
.header{background:#1769e0;color:#fff;padding:26px 5%;display:flex;justify-content:space-between;align-items:center;gap:20px}
.header h1{margin:0 0 6px;font-size:30px}.header p{margin:0;opacity:.9}
.header-right{display:flex;align-items:center;gap:10px}
button,input,select{padding:11px 14px;border-radius:7px;font-size:15px}
button{border:none;background:#fff;color:#1769e0;cursor:pointer}.container{width:90%;max-width:1450px;margin:30px auto}
.panel{background:#fff;padding:25px;border-radius:12px;box-shadow:0 3px 12px #00000012}
.controls{display:flex;gap:12px;margin:20px 0}.controls input{flex:1;border:1px solid #d1d5db}.controls select{border:1px solid #d1d5db}
.table-wrapper{overflow-x:auto}table{width:100%;border-collapse:collapse;min-width:950px}th{background:#1769e0;color:#fff;padding:14px;text-align:left}
td{padding:14px;border-bottom:1px solid #e5e7eb}.filename{max-width:320px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.action-upload{color:#1769e0;font-weight:bold}.action-verified{color:#15803d;font-weight:bold}.action-rejected{color:#dc2626;font-weight:bold}.action-duplicate{color:#d97706;font-weight:bold}
.empty{text-align:center;padding:35px;color:#6b7280}
@media(max-width:700px){.header{flex-direction:column;align-items:flex-start}.controls{flex-direction:column}}
</style>
</head>
<body>
<div class="header">
  <div><h1>Audit Log</h1><p>Security and document activity history</p></div>
  <div class="header-right">
    <button onclick="goDashboard()">Dashboard</button>
    <button onclick="logout()">Logout</button>
  </div>
</div>

<div class="container">
  <div class="panel">
    <h2>Audit History</h2>
    <div class="controls">
      <input id="search" type="text" placeholder="Search document, actor or details..." onkeyup="filterLogs()">
      <select id="actionFilter" onchange="filterLogs()">
        <option value="All">All Actions</option>
        <option value="UPLOAD">Upload</option>
        <option value="VERIFIED">Verified</option>
        <option value="REJECTED">Rejected</option>
        <option value="DUPLICATE_UPLOAD_BLOCKED">Duplicate Blocked</option>
      </select>
    </div>
    <div class="table-wrapper">
      <table>
        <thead><tr><th>Timestamp</th><th>Action</th><th>Document</th><th>Actor</th><th>Details</th></tr></thead>
        <tbody id="auditBody"></tbody>
      </table>
    </div>
  </div>
</div>

<script type="module">
import { initializeApp } from "https://www.gstatic.com/firebasejs/12.9.0/firebase-app.js";
import { getAuth, onAuthStateChanged, signOut } from "https://www.gstatic.com/firebasejs/12.9.0/firebase-auth.js";

const firebaseConfig = {{ firebase_config | safe }};
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
let allLogs = [];

function escapeHtml(text){
  return String(text).replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#039;");
}

function actionClass(action){
  if(action === "UPLOAD") return "action-upload";
  if(action === "VERIFIED") return "action-verified";
  if(action === "REJECTED") return "action-rejected";
  if(action === "DUPLICATE_UPLOAD_BLOCKED") return "action-duplicate";
  return "";
}

async function loadLogs(){
  const user = auth.currentUser;
  if(!user){ window.location.href = "/"; return; }
  const token = await user.getIdToken();
  const response = await fetch("/api/audit-logs", {headers:{Authorization:"Bearer "+token}});
  if(!response.ok){ window.location.href = "/"; return; }
  const data = await response.json();
  allLogs = data.logs || [];
  renderLogs(allLogs);
}

function renderLogs(logs){
  const body = document.getElementById("auditBody");
  body.innerHTML = "";
  if(!logs.length){
    body.innerHTML = `<tr><td colspan="5" class="empty">No audit events found.</td></tr>`;
    return;
  }
  logs.forEach((log)=>{
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${escapeHtml(log.timestamp)}</td>
      <td><span class="${actionClass(log.action)}">${escapeHtml(log.action)}</span></td>
      <td class="filename" title="${escapeHtml(log.filename || "")}">${escapeHtml(log.filename || "-")}</td>
      <td>${escapeHtml(log.actor || "-")}</td>
      <td>${escapeHtml(log.details || "-")}</td>
    `;
    body.appendChild(row);
  });
}

window.filterLogs = function(){
  const search = document.getElementById("search").value.toLowerCase();
  const action = document.getElementById("actionFilter").value;
  renderLogs(allLogs.filter((log)=>{
    const text = (log.filename+" "+log.actor+" "+log.details+" "+log.action).toLowerCase();
    return text.includes(search) && (action === "All" || log.action === action);
  }));
};

window.goDashboard = function(){
  localStorage.setItem("selectedRole","admin");
  window.location.href = "/";
};

window.logout = async function(){
  await signOut(auth);
  localStorage.removeItem("selectedRole");
  window.location.href = "/";
};

onAuthStateChanged(auth, async (user)=>{
  if(!user){ window.location.href = "/"; return; }
  try{
    const tokenResult = await user.getIdTokenResult(true);
    if(tokenResult.claims.admin !== true){ window.location.href = "/"; return; }
    localStorage.setItem("selectedRole","admin");
    await loadLogs();
  }catch(error){ window.location.href = "/"; }
});
</script>
</body>
</html>
"""


def verify_token():
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    token = header.split("Bearer ", 1)[1].strip()
    if not token:
        return None
    try:
        return auth.verify_id_token(token)
    except Exception:
        return None


def is_admin(decoded_token):
    return decoded_token.get("admin", False) is True


def log_audit(action, actor, document_id="", filename="", details=""):
    db.collection("audit_logs").add({
        "action": action,
        "actor": actor,
        "document_id": document_id,
        "filename": filename,
        "details": details,
        "timestamp": datetime.now(timezone.utc),
    })


def format_timestamp(value):
    if not value:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%d %b %Y, %I:%M %p")
    return str(value)


def normalize_reviewer(value):
    if not value:
        return ""
    return ADMIN_DISPLAY_NAME if value == "admin@yourdomain.com" else value


def normalize_document(snap):
    data = snap.to_dict()
    filename = data.get("filename") or data.get("fileName") or ""
    user = data.get("user", "")
    status = data.get("status", "Pending")
    reviewer = normalize_reviewer(data.get("reviewer", ""))
    uploaded = data.get("uploaded") or data.get("uploadedAt")
    reviewed = data.get("reviewed") or data.get("reviewedAt")
    storage_path = data.get("storage_path") or data.get("storagePath") or ""
    owner_uid = data.get("owner_uid") or data.get("ownerUid") or ""
    owner_email = data.get("owner_email") or data.get("ownerEmail") or ""
    rejection_reason = data.get("rejection_reason") or data.get("rejectionReason") or ""
    content_type = data.get("content_type", "")
    file_hash = data.get("file_hash", "")
    verification_id = data.get("verification_id", "")
    if not content_type:
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    return {
        "id": snap.id,
        "filename": filename,
        "user": user,
        "status": status,
        "reviewer": reviewer,
        "uploaded": format_timestamp(uploaded),
        "reviewed": format_timestamp(reviewed),
        "storage_path": storage_path,
        "owner_uid": owner_uid,
        "owner_email": owner_email,
        "rejectionReason": rejection_reason,
        "content_type": content_type,
        "file_hash": file_hash,
        "verification_id": verification_id,
    }


def get_all_documents():
    docs = [normalize_document(snap) for snap in db.collection("documents").stream()]
    docs.sort(key=lambda x: x["uploaded"], reverse=True)
    return docs


def make_document_response(documents):
    return {
        "documents": documents,
        "total": len(documents),
        "pending": sum(d["status"] == "Pending" for d in documents),
        "verified": sum(d["status"] == "Verified" for d in documents),
        "rejected": sum(d["status"] == "Rejected" for d in documents),
    }


@app.route("/")
def home():
    return render_template_string(HTML, firebase_config=json.dumps(FIREBASE_CONFIG))


@app.route("/audit")
def audit_page():
    return render_template_string(AUDIT_HTML, firebase_config=json.dumps(FIREBASE_CONFIG))


@app.route("/api/documents")
def admin_documents():
    token = verify_token()
    if not token:
        return "Unauthorized", 401
    if not is_admin(token):
        return "Forbidden", 403
    return jsonify(make_document_response(get_all_documents()))


@app.route("/api/my-documents")
def my_documents():
    token = verify_token()
    if not token:
        return "Unauthorized", 401
    if is_admin(token):
        return "Forbidden", 403
    uid = token["uid"]
    documents = [d for d in get_all_documents() if d["owner_uid"] == uid]
    return jsonify(make_document_response(documents))


@app.route("/api/audit-logs")
def audit_logs():
    token = verify_token()
    if not token:
        return "Unauthorized", 401
    if not is_admin(token):
        return "Forbidden", 403

    raw_logs = []
    for snap in db.collection("audit_logs").stream():
        data = snap.to_dict()
        raw_logs.append({
            "id": snap.id,
            "action": data.get("action", ""),
            "actor": data.get("actor", ""),
            "document_id": data.get("document_id", ""),
            "filename": data.get("filename", ""),
            "details": data.get("details", ""),
            "timestamp": data.get("timestamp"),
        })

    raw_logs.sort(
        key=lambda x: x["timestamp"] or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )

    logs = []
    for log in raw_logs[:100]:
        logs.append({
            "id": log["id"],
            "action": log["action"],
            "actor": log["actor"],
            "document_id": log["document_id"],
            "filename": log["filename"],
            "details": log["details"],
            "timestamp": format_timestamp(log["timestamp"]),
        })
    return jsonify({"logs": logs})


@app.route("/api/upload", methods=["POST"])
def upload():
    token = verify_token()
    if not token:
        return "Unauthorized", 401
    if is_admin(token):
        return "Administrators cannot upload documents from this portal.", 403

    user = request.form.get("user", "").strip()
    file = request.files.get("file")

    if not user:
        return "Name is required.", 400
    if not file or not file.filename:
        return "No file selected.", 400

    filename = file.filename
    extension = os.path.splitext(filename)[1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        return "Unsupported file type.", 400

    file.stream.seek(0, os.SEEK_END)
    size = file.stream.tell()
    file.stream.seek(0)

    if size <= 0:
        return "Empty files are not allowed.", 400
    if size > MAX_FILE_SIZE:
        return "Maximum file size is 10 MB.", 400

    file_bytes = file.read()
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    file.stream.seek(0)

    for existing_snap in db.collection("documents").stream():
        existing_data = existing_snap.to_dict()
        if existing_data.get("file_hash") == file_hash:
            log_audit(
                "DUPLICATE_UPLOAD_BLOCKED",
                token.get("email", "User"),
                existing_snap.id,
                filename,
                "Duplicate upload blocked",
            )
            return "Duplicate document detected. This file has already been uploaded.", 409

    document_id = str(uuid.uuid4())
    safe_filename = os.path.basename(filename)
    storage_path = f"documents/{document_id}_{safe_filename}"
    content_type = (
        file.content_type
        or mimetypes.guess_type(safe_filename)[0]
        or "application/octet-stream"
    )

    blob = bucket.blob(storage_path)
    blob.upload_from_file(file, content_type=content_type)

    now = datetime.now(timezone.utc)
    db.collection("documents").document(document_id).set({
        "filename": safe_filename,
        "user": user,
        "status": "Pending",
        "reviewer": "",
        "uploaded": now,
        "reviewed": None,
        "storage_path": storage_path,
        "content_type": content_type,
        "file_hash": file_hash,
        "owner_uid": token["uid"],
        "owner_email": token.get("email", ""),
        "rejection_reason": "",
    })

    log_audit(
        "UPLOAD",
        token.get("email", "User"),
        document_id,
        safe_filename,
        "Document uploaded",
    )

    return jsonify({"message": "Document uploaded successfully."})


@app.route("/api/review/<doc_id>", methods=["POST"])
def review(doc_id):
    token = verify_token()
    if not token:
        return "Unauthorized", 401
    if not is_admin(token):
        return "Forbidden", 403

    action = request.form.get("action", "")
    reason = request.form.get("reason", "").strip()

    if action not in ("verify", "reject"):
        return "Invalid action.", 400
    if action == "reject" and not reason:
        return "Rejection reason is required.", 400

    ref = db.collection("documents").document(doc_id)
    snap = ref.get()
    if not snap.exists:
        return "Document not found.", 404

    data = snap.to_dict()
    if data.get("status") != "Pending":
        return "This document has already been reviewed.", 409

    status = "Verified" if action == "verify" else "Rejected"
    now = datetime.now(timezone.utc)

    verification_id = (
        f"DV-{now.year}-{uuid.uuid4().hex[:8].upper()}"
        if action == "verify"
        else ""
    )


    ref.update({
        "status": status,
        "reviewer": ADMIN_DISPLAY_NAME,
        "reviewed": now,
        "reviewedAt": now,
        "verification_id": verification_id,
        "rejection_reason": reason if action == "reject" else "",
    })

    log_audit(
        "VERIFIED" if action == "verify" else "REJECTED",
        ADMIN_DISPLAY_NAME,
        doc_id,
        data.get("filename", ""),
        (
            f"Document verified - {verification_id}"
            if action == "verify"
            else f"Document rejected: {reason}"
        ),
    )

    return jsonify({"message": f"Document {status.lower()}."})


@app.route("/api/download/<doc_id>")
def download_document(doc_id):
    token = verify_token()
    if not token:
        return "Unauthorized", 401

    ref = db.collection("documents").document(doc_id)
    snap = ref.get()
    if not snap.exists:
        return "Document not found.", 404

    doc = normalize_document(snap)

    if not is_admin(token) and doc["owner_uid"] != token["uid"]:
        return "Forbidden", 403

    if not doc["storage_path"]:
        return "File path not found.", 404

    blob = bucket.blob(doc["storage_path"])
    if not blob.exists():
        return "File not found in storage.", 404

    file_data = blob.download_as_bytes()
    return send_file(
        io.BytesIO(file_data),
        download_name=doc["filename"] or "document",
        mimetype=doc["content_type"],
        as_attachment=False,
    )



@app.route("/verify/<verification_id>")
def public_verify(verification_id):

    results = db.collection(
        "documents"
    ).where(
        "verification_id",
        "==",
        verification_id
    ).limit(1).stream()

    document = None

    for snap in results:

        data = snap.to_dict()

        if data.get("status") != "Verified":
            continue

        document = {
            "filename": data.get(
                "filename",
                ""
            ),
            "verification_id": data.get(
                "verification_id",
                ""
            ),
            "reviewer": normalize_reviewer(
                data.get(
                    "reviewer",
                    ""
                )
            ),
            "reviewed": format_timestamp(
                data.get("reviewed")
                or data.get("reviewedAt")
            ),
            "file_hash": data.get(
                "file_hash",
                ""
            )
        }

        break

    return render_template_string(
        VERIFY_HTML,
        document=document
    )


@app.route("/api/qr/<verification_id>")
def verification_qr(verification_id):

    results = db.collection(
        "documents"
    ).where(
        "verification_id",
        "==",
        verification_id
    ).limit(1).stream()

    found = False

    for snap in results:

        data = snap.to_dict()

        if data.get("status") == "Verified":
            found = True
            break

    if not found:
        return "Verification not found", 404

    verify_url = (
        request.url_root.rstrip("/")
        + "/verify/"
        + verification_id
    )

    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=4
    )

    qr.add_data(verify_url)
    qr.make(fit=True)

    image = qr.make_image(
        fill_color="black",
        back_color="white"
    )

    output = io.BytesIO()

    image.save(
        output,
        format="PNG"
    )

    output.seek(0)

    return send_file(
        output,
        mimetype="image/png"
    )



@app.route("/api/certificate/<doc_id>")
def download_certificate(doc_id):

    token = verify_token()

    if not token:
        return "Unauthorized", 401

    ref = db.collection(
        "documents"
    ).document(
        doc_id
    )

    snap = ref.get()

    if not snap.exists:
        return "Document not found.", 404

    doc = normalize_document(snap)

    if doc["status"] != "Verified":
        return (
            "A verification certificate is only available "
            "for verified documents.",
            400
        )

    # Only the owner or an administrator can download it.
    if not is_admin(token):

        if doc["owner_uid"] != token["uid"]:
            return "Forbidden", 403

    verification_id = doc.get(
        "verification_id",
        ""
    )

    if not verification_id:
        return (
            "Verification ID not available.",
            400
        )

    verify_url = (
        request.url_root.rstrip("/")
        + "/verify/"
        + verification_id
    )

    # Create QR image in memory.
    qr = qrcode.QRCode(
        version=1,
        box_size=8,
        border=4
    )

    qr.add_data(verify_url)
    qr.make(fit=True)

    qr_image = qr.make_image(
        fill_color="black",
        back_color="white"
    )

    qr_buffer = io.BytesIO()
    qr_image.save(
        qr_buffer,
        format="PNG"
    )
    qr_buffer.seek(0)

    # PDF in memory.
    pdf_buffer = io.BytesIO()

    document_name = (
        doc.get("filename")
        or "Verified Document"
    )

    doc_id_text = str(
        doc.get(
            "id",
            doc_id
        )
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "CertificateTitle",
        parent=styles["Title"],
        fontSize=22,
        leading=26,
        alignment=1,
        spaceAfter=8
    )

    subtitle_style = ParagraphStyle(
        "CertificateSubtitle",
        parent=styles["Normal"],
        fontSize=11,
        textColor=colors.HexColor(
            "#15803d"
        ),
        alignment=1,
        spaceAfter=20
    )

    normal_style = ParagraphStyle(
        "CertificateNormal",
        parent=styles["Normal"],
        fontSize=10,
        leading=14
    )

    small_style = ParagraphStyle(
        "CertificateSmall",
        parent=styles["Normal"],
        fontSize=8,
        leading=11
    )

    pdf = SimpleDocTemplate(
        pdf_buffer,
        pagesize=A4,
        rightMargin=45,
        leftMargin=45,
        topMargin=45,
        bottomMargin=45
    )

    story = []

    story.append(
        Paragraph(
            "DIGITAL DOCUMENT VERIFICATION",
            title_style
        )
    )

    story.append(
        Paragraph(
            "VERIFIED DOCUMENT CERTIFICATE",
            subtitle_style
        )
    )

    story.append(
        Spacer(
            1,
            10
        )
    )

    details = [
        [
            Paragraph(
                "<b>Document</b>",
                normal_style
            ),
            Paragraph(
                document_name,
                normal_style
            )
        ],
        [
            Paragraph(
                "<b>Verification ID</b>",
                normal_style
            ),
            Paragraph(
                verification_id,
                normal_style
            )
        ],
        [
            Paragraph(
                "<b>Status</b>",
                normal_style
            ),
            Paragraph(
                "VERIFIED",
                normal_style
            )
        ],
        [
            Paragraph(
                "<b>Verified By</b>",
                normal_style
            ),
            Paragraph(
                doc.get(
                    "reviewer",
                    "Admin"
                ),
                normal_style
            )
        ],
        [
            Paragraph(
                "<b>Verification Date</b>",
                normal_style
            ),
            Paragraph(
                doc.get(
                    "reviewed",
                    ""
                ),
                normal_style
            )
        ],
        [
            Paragraph(
                "<b>SHA-256 Fingerprint</b>",
                normal_style
            ),
            Paragraph(
                doc.get(
                    "file_hash",
                    ""
                ),
                small_style
            )
        ]
    ]

    table = Table(
        details,
        colWidths=[
            145,
            340
        ],
        repeatRows=0
    )

    table.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (0, -1),
                colors.HexColor(
                    "#f3f4f6"
                )
            ),
            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.HexColor(
                    "#d1d5db"
                )
            ),
            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "TOP"
            ),
            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                10
            ),
            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                10
            ),
            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                10
            ),
            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                10
            )
        ])
    )

    story.append(table)

    story.append(
        Spacer(
            1,
            25
        )
    )

    qr_buffer.seek(0)

    qr_pdf_image = PDFImage(
        qr_buffer,
        width=145,
        height=145
    )

    story.append(
        Paragraph(
            "<b>Scan to verify this document</b>",
            ParagraphStyle(
                "QRHeading",
                parent=styles["Heading2"],
                alignment=1
            )
        )
    )

    story.append(
        Spacer(
            1,
            10
        )
    )

    story.append(qr_pdf_image)

    story.append(
        Spacer(
            1,
            10
        )
    )

    story.append(
        Paragraph(
            verify_url,
            small_style
        )
    )

    story.append(
        Spacer(
            1,
            20
        )
    )

    story.append(
        Paragraph(
            "This certificate confirms that the "
            "document identified above has been verified "
            "through the Digital Document Verification System.",
            normal_style
        )
    )

    pdf.build(story)

    pdf_buffer.seek(0)

    return send_file(
        pdf_buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=(
            "Verification_Certificate_"
            + verification_id
            + ".pdf"
        )
    )


@app.route("/health")
def health():
    return "OK", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
