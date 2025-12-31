from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional
import pandas as pd
import io
import json
import asyncio
from vertexai.generative_models import GenerativeModel, Tool, grounding
# google.cloud.aiplatform_v1beta1 imports removed as they are no longer used in generate_leads
# from google.cloud.aiplatform_v1beta1 import types as gapic_types
from src.scraper import scrape_site
from src.analyzer import analyze_universal

# New imports for direct REST API call
import google.auth
from google.auth.transport.requests import Request as GoogleAuthRequest
import requests
import os

app = FastAPI()

# --- Data Models ---
class AuditRequest(BaseModel):
    url: str
    client_name: str
    industry: str
    goals: str

class GeneratorRequest(BaseModel):
    prompt: str

class ChatRequest(BaseModel):
    message: str

# --- FRONTEND (Unified Hub) ---
HTML_APP = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Veritic Unified Hub</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    colors: {
                        slate: { 850: '#1e293b' }
                    }
                }
            }
        }
    </script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        body { background-color: #0f172a; color: #e2e8f0; font-family: 'Inter', sans-serif; }
        .glass { background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.1); }
        .gradient-text { background: linear-gradient(45deg, #10b981, #8b5cf6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .veritic-border { border-left: 4px solid #10b981; }
        .choice-border { border-left: 4px solid #8b5cf6; }
        .loader { border-top-color: #10b981; animation: spinner 1.5s linear infinite; }
        @keyframes spinner { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body class="min-h-screen p-6">

    <!-- Header -->
    <header class="flex justify-between items-center mb-10">
        <div>
            <h1 class="text-3xl font-bold gradient-text">Veritic Intelligence Hub</h1>
            <p class="text-slate-400 text-sm mb-2">Unified Audit & Choice Analysis Engine</p>
            <div class="flex space-x-3 text-xs font-bold">
                 <span class="text-slate-500">Powered by modules:</span>
                 <span class="text-red-400">🔴 RimLab (Research)</span>
                 <span class="text-slate-600">|</span>
                 <span class="text-green-400">🟢 Veritic (Audit)</span>
                 <span class="text-slate-600">|</span>
                 <span class="text-purple-400">🟣 Choice (Brand)</span>
            </div>
        </div>
        <div class="flex items-center space-x-4">
            <button onclick="toggleManual()" class="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg font-bold border border-slate-500 transition">📘 Nápověda</button>
            <span class="px-3 py-1 bg-green-900/30 text-green-400 rounded-full text-xs font-bold border border-green-500/20">VERITIC ACTIVE</span>
            <span class="px-3 py-1 bg-purple-900/30 text-purple-400 rounded-full text-xs font-bold border border-purple-500/20">CHOICE ACTIVE</span>
        </div>
    </header>

    <!-- Main Grid -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        <!-- Left Panel: Campaign Manager -->
        <div class="lg:col-span-4 space-y-6">

            <!-- Tabs -->
            <div class="glass p-1 rounded-xl flex space-x-1">
                <button onclick="switchTab('ai')" id="tab-ai" class="flex-1 py-2 rounded-lg text-sm font-bold bg-slate-700 text-white transition">AI Generator</button>
                <button onclick="switchTab('csv')" id="tab-csv" class="flex-1 py-2 rounded-lg text-sm font-bold text-slate-400 hover:text-white transition">CSV Upload</button>
            </div>

            <!-- Tab Content: AI -->
            <div id="content-ai" class="glass p-6 rounded-2xl">
                <label class="block text-xs text-slate-400 uppercase font-bold mb-2">Prompt for Leads</label>
                <textarea id="aiPrompt" rows="3" class="w-full bg-slate-900 border border-slate-700 rounded-lg p-3 text-sm text-white focus:ring-2 focus:ring-green-500 outline-none" placeholder="Find 5 high schools in Prague..."></textarea>
                <button onclick="generateLeads()" class="w-full mt-4 bg-green-600 hover:bg-green-500 text-white font-bold py-2 rounded-lg transition">
                    <i class="fas fa-magic mr-2"></i> Generate Leads
                </button>
            </div>

            <!-- Tab Content: CSV -->
            <div id="content-csv" class="glass p-6 rounded-2xl hidden">
                <label class="block text-xs text-slate-400 uppercase font-bold mb-2">Upload File (CSV/XLSX)</label>
                <input type="file" id="csvInput" class="w-full text-sm text-slate-400 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-slate-700 file:text-white hover:file:bg-slate-600"/>
                <button onclick="uploadLeads()" class="w-full mt-4 bg-blue-600 hover:bg-blue-500 text-white font-bold py-2 rounded-lg transition">
                    <i class="fas fa-upload mr-2"></i> Upload & Parse
                </button>
            </div>

            <!-- Campaign Controls -->
            <div class="glass p-6 rounded-2xl">
                 <div class="flex justify-between items-center mb-4">
                    <h3 class="font-bold text-white">Campaign Queue</h3>
                    <span id="queueCount" class="text-xs bg-slate-700 px-2 py-1 rounded text-white">0</span>
                 </div>
                 <button onclick="startCampaign()" id="btnStart" class="w-full bg-gradient-to-r from-green-600 to-purple-600 text-white font-bold py-3 rounded-xl shadow-lg transform active:scale-95 transition disabled:opacity-50 disabled:cursor-not-allowed" disabled>
                    START CAMPAIGN
                 </button>
            </div>

        </div>

        <!-- Right Panel: Data & Results -->
        <div class="lg:col-span-8 space-y-6">

            <!-- Table -->
            <div class="glass rounded-2xl overflow-hidden min-h-[300px]">
                <table class="w-full text-left border-collapse">
                    <thead class="bg-slate-800 text-xs uppercase text-slate-400">
                        <tr>
                            <th class="p-4">Name</th>
                            <th class="p-4">URL</th>
                            <th class="p-4">Status</th>
                            <th class="p-4 text-right">Action</th>
                        </tr>
                    </thead>
                    <tbody id="campaignTable" class="text-sm divide-y divide-slate-700">
                        <!-- Rows injected here -->
                        <tr class="text-slate-500 text-center"><td colspan="4" class="p-8">No leads loaded. Generate or Upload to start.</td></tr>
                    </tbody>
                </table>
            </div>

            <!-- Results View -->
            <div id="resultCard" class="glass p-6 rounded-2xl hidden animate-fade-in">
                <div class="flex justify-between items-center mb-6">
                    <h2 id="resName" class="text-2xl font-bold text-white">Result Name</h2>
                    <a id="resLink" href="#" target="_blank" class="text-blue-400 text-sm hover:underline"><i class="fas fa-external-link-alt"></i> Open Web</a>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                    
                    <!-- RimLab Column (The Trap) -->
                    <div class="bg-slate-900/50 p-5 rounded-xl border border-red-500/30 relative overflow-hidden">
                        <div class="absolute top-0 left-0 w-1 h-full bg-red-500"></div>
                        <h3 class="text-red-400 font-bold uppercase text-xs mb-4 flex items-center"><i class="fas fa-exclamation-triangle mr-2"></i> AI Memory Risk</h3>

                        <div class="flex justify-between items-center mb-4">
                            <span class="text-slate-400 text-sm">Hallucination Risk</span>
                            <span id="rimlabConf" class="text-2xl font-bold text-white">--</span>
                        </div>

                        <div class="mb-4">
                            <p class="text-xs text-slate-500 uppercase">AI Thinks CEO Is:</p>
                            <p id="rimlabDirector" class="text-lg font-bold text-white">--</p>
                        </div>

                        <div>
                            <p class="text-xs text-slate-500 uppercase mb-2">AI Thinks Email Is:</p>
                            <p id="rimlabEmail" class="text-sm text-red-300 break-all">--</p>
                        </div>
                    </div>

                    <!-- Veritic Column (Web Reality) -->
                    <div class="bg-slate-900/50 p-5 rounded-xl border border-green-500/30 relative overflow-hidden">
                        <div class="absolute top-0 left-0 w-1 h-full bg-green-500"></div>
                        <h3 class="text-green-400 font-bold uppercase text-xs mb-4 flex items-center"><i class="fas fa-shield-alt mr-2"></i> Web Reality</h3>

                        <div class="flex justify-between items-center mb-4">
                            <span class="text-slate-400 text-sm">Integrity Score</span>
                            <span id="veriticScore" class="text-2xl font-bold text-white">--</span>
                        </div>

                        <div class="space-y-2">
                            <p class="text-xs text-slate-500 uppercase">Missing Data</p>
                            <div id="veriticMissing" class="flex flex-wrap gap-2"></div>
                        </div>

                        <div class="mt-4 pt-4 border-t border-slate-700">
                            <p class="text-xs text-slate-500 uppercase mb-2">Extracted</p>
                            <ul id="veriticExtracted" class="text-sm space-y-1 text-slate-300"></ul>
                        </div>
                    </div>

                    <!-- Choice Column (Brand Perception) -->
                    <div class="bg-slate-900/50 p-5 rounded-xl border border-purple-500/30 relative overflow-hidden">
                        <div class="absolute top-0 left-0 w-1 h-full bg-purple-500"></div>
                        <h3 class="text-purple-400 font-bold uppercase text-xs mb-4 flex items-center"><i class="fas fa-heart mr-2"></i> Brand Perception</h3>

                        <div class="flex justify-between items-center mb-4">
                            <span class="text-slate-400 text-sm">Brand Score</span>
                            <span id="choiceScore" class="text-2xl font-bold text-white">--</span>
                        </div>

                        <div class="mb-4">
                            <p class="text-xs text-slate-500 uppercase">Archetype</p>
                            <p id="choiceArchetype" class="text-lg font-bold text-white">--</p>
                        </div>

                        <div>
                            <p class="text-xs text-slate-500 uppercase mb-2">Emotional Vibe</p>
                            <div id="choiceVibe" class="flex flex-wrap gap-2"></div>
                        </div>

                        <div class="mt-4 pt-4 border-t border-slate-700">
                             <p class="text-xs text-slate-500 uppercase mb-1">Alignment</p>
                             <p id="choiceAlignment" class="text-xs italic text-slate-400">--</p>
                        </div>
                    </div>

                </div>
            </div>

        </div>
    </div>

    <!-- Manual Modal -->
    <div id="manualModal" class="fixed inset-0 bg-black/80 hidden z-50 flex items-center justify-center backdrop-blur-sm">
        <div class="glass p-8 rounded-2xl max-w-2xl w-full relative">
            <button onclick="toggleManual()" class="absolute top-4 right-4 text-slate-400 hover:text-white"><i class="fas fa-times text-xl"></i></button>
            <h2 class="text-2xl font-bold text-white mb-6">📚 Manuál Veritic Hub</h2>

            <div class="space-y-6">
                <div class="p-4 rounded-xl border border-red-500/30 bg-red-900/10">
                    <h3 class="text-red-400 font-bold mb-2">🔴 RimLab (Research)</h3>
                    <p class="text-slate-300 text-sm">Simuluje "paměť AI". Ukazuje, co si modely myslí, že vědí (riziko halucinace).</p>
                </div>
                <div class="p-4 rounded-xl border border-green-500/30 bg-green-900/10">
                    <h3 class="text-green-400 font-bold mb-2">🟢 Veritic (Audit)</h3>
                    <p class="text-slate-300 text-sm">Realita webu. Robot, který v reálném čase ověřuje fakta na stránce.</p>
                </div>
                <div class="p-4 rounded-xl border border-purple-500/30 bg-purple-900/10">
                    <h3 class="text-purple-400 font-bold mb-2">🟣 Choice (Brand)</h3>
                    <p class="text-slate-300 text-sm">Emoční analýza. Jak značka působí na zákazníka (archetypy, nálada).</p>
                </div>

                <div class="mt-4 pt-4 border-t border-slate-700">
                    <p class="text-xs text-slate-500 uppercase font-bold mb-2">💡 Tip pro Prompty</p>
                    <p class="text-sm text-slate-400">Buďte specifičtí. Místo "školy" napište "Soukromá gymnázia v Brně".</p>
                </div>
            </div>
        </div>
    </div>

    <!-- Chat Widget -->
    <div class="fixed bottom-6 right-6 z-40 flex flex-col items-end">

        <!-- Chat Window -->
        <div id="chatWindow" class="glass w-80 h-96 rounded-2xl mb-4 hidden flex flex-col overflow-hidden shadow-2xl border-slate-600">
            <div class="bg-slate-800 p-4 border-b border-slate-700 flex justify-between items-center">
                <h3 class="font-bold text-white"><i class="fas fa-robot mr-2"></i>Veritic Support</h3>
                <button onclick="toggleChat()" class="text-slate-400 hover:text-white"><i class="fas fa-times"></i></button>
            </div>
            <div id="chatMessages" class="flex-1 p-4 overflow-y-auto space-y-3 text-sm">
                <div class="bg-slate-700 text-slate-200 p-3 rounded-lg rounded-tl-none self-start max-w-[85%]">
                    Ahoj! Jsem tu, abych ti pomohl pochopit RimLab, Veritic a Choice. Na co se chceš zeptat?
                </div>
            </div>
            <div class="p-3 bg-slate-800 border-t border-slate-700 flex">
                <input id="chatInput" type="text" class="flex-1 bg-slate-900 border border-slate-600 rounded-l-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500" placeholder="Zeptej se..." onkeypress="if(event.key === 'Enter') sendChat()">
                <button onclick="sendChat()" class="bg-blue-600 hover:bg-blue-500 text-white px-4 rounded-r-lg"><i class="fas fa-paper-plane"></i></button>
            </div>
        </div>

        <!-- Toggle Button -->
        <button onclick="toggleChat()" class="bg-blue-600 hover:bg-blue-500 text-white w-14 h-14 rounded-full shadow-lg flex items-center justify-center transition transform hover:scale-110">
            <i class="fas fa-comment-dots text-2xl"></i>
        </button>
    </div>

    <script>
        function toggleManual() {
            const el = document.getElementById('manualModal');
            el.classList.toggle('hidden');
        }

        function toggleChat() {
            const el = document.getElementById('chatWindow');
            el.classList.toggle('hidden');
        }

        async function sendChat() {
            const input = document.getElementById('chatInput');
            const msg = input.value.trim();
            if(!msg) return;

            const chatDiv = document.getElementById('chatMessages');

            // User Msg
            chatDiv.innerHTML += `<div class="bg-blue-600 text-white p-3 rounded-lg rounded-tr-none self-end max-w-[85%] ml-auto">${msg}</div>`;
            input.value = '';
            chatDiv.scrollTop = chatDiv.scrollHeight;

            // Loading
            const loadingId = 'loading-' + Date.now();
            chatDiv.innerHTML += `<div id="${loadingId}" class="bg-slate-700 text-slate-200 p-3 rounded-lg rounded-tl-none self-start max-w-[85%]"><i class="fas fa-spinner fa-spin"></i></div>`;
            chatDiv.scrollTop = chatDiv.scrollHeight;

            try {
                const res = await fetch('/support-chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ message: msg })
                });
                const data = await res.json();

                document.getElementById(loadingId).remove();
                chatDiv.innerHTML += `<div class="bg-slate-700 text-slate-200 p-3 rounded-lg rounded-tl-none self-start max-w-[85%]">${data.reply}</div>`;

            } catch(e) {
                document.getElementById(loadingId).remove();
                chatDiv.innerHTML += `<div class="text-red-400 text-xs p-2">Error connecting to support.</div>`;
            }
            chatDiv.scrollTop = chatDiv.scrollHeight;
        }

        let leads = [];

        function switchTab(tab) {
            document.querySelectorAll('[id^="content-"]').forEach(el => el.classList.add('hidden'));
            document.getElementById('content-' + tab).classList.remove('hidden');
            
            document.getElementById('tab-ai').className = tab === 'ai' ? 'flex-1 py-2 rounded-lg text-sm font-bold bg-slate-700 text-white transition' : 'flex-1 py-2 rounded-lg text-sm font-bold text-slate-400 hover:text-white transition';
            document.getElementById('tab-csv').className = tab === 'csv' ? 'flex-1 py-2 rounded-lg text-sm font-bold bg-slate-700 text-white transition' : 'flex-1 py-2 rounded-lg text-sm font-bold text-slate-400 hover:text-white transition';
        }

        async function generateLeads() {
            const prompt = document.getElementById('aiPrompt').value;
            if(!prompt) return alert("Enter a prompt");

            const btn = document.querySelector('button[onclick="generateLeads()"]');
            const originalText = btn.innerHTML;
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Working...';
            
            try {
                const res = await fetch('/generate-leads', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ prompt })
                });
                const data = await res.json();
                loadTable(data);
            } catch(e) { alert(e); }
            finally {
                btn.disabled = false;
                btn.innerHTML = originalText;
            }
        }

        async function uploadLeads() {
            const fileInput = document.getElementById('csvInput');
            if(fileInput.files.length === 0) return alert("Select a file");

            const formData = new FormData();
            formData.append('file', fileInput.files[0]);

            try {
                const res = await fetch('/upload-leads', {
                    method: 'POST',
                    body: formData
                });
                const data = await res.json();
                loadTable(data);
            } catch(e) { alert(e); }
        }

        function loadTable(data) {
            leads = data.map(d => ({...d, status: 'Ready', result: null}));
            renderTable();
            document.getElementById('btnStart').disabled = false;
            document.getElementById('queueCount').innerText = leads.length;
        }

        function renderTable() {
            const tbody = document.getElementById('campaignTable');
            tbody.innerHTML = '';
            leads.forEach((lead, idx) => {
                let statusColor = 'text-slate-400';
                if(lead.status === 'Processing') statusColor = 'text-blue-400 animate-pulse';
                if(lead.status === 'Done') statusColor = 'text-green-400';
                if(lead.status === 'Error') statusColor = 'text-red-400';

                const tr = document.createElement('tr');
                tr.className = 'hover:bg-slate-800/50 transition';
                tr.innerHTML = `
                    <td class="p-4 font-medium text-white">${lead.client_name}</td>
                    <td class="p-4 text-blue-400 truncate max-w-[150px]"><a href="${lead.url}" target="_blank">${lead.url}</a></td>
                    <td class="p-4 ${statusColor} font-bold text-xs uppercase">${lead.status}</td>
                    <td class="p-4 text-right">
                        ${lead.result ? `<button onclick="viewResult(${idx})" class="bg-slate-700 hover:bg-slate-600 text-white text-xs px-2 py-1 rounded">View</button>` : ''}
                    </td>
                `;
                tbody.appendChild(tr);
            });
        }

        async function startCampaign() {
            const btn = document.getElementById('btnStart');
            btn.disabled = true;
            const originalText = btn.innerHTML;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Working...';

            for (let i = 0; i < leads.length; i++) {
                if(leads[i].status === 'Done') continue;

                leads[i].status = 'Processing';
                renderTable();

                try {
                    const res = await fetch('/audit', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            url: leads[i].url,
                            client_name: leads[i].client_name,
                            industry: leads[i].industry || 'General',
                            goals: leads[i].goals || 'Analyze reputation'
                        })
                    });

                    if(!res.ok) throw new Error("Failed");

                    const result = await res.json();
                    leads[i].status = 'Done';
                    leads[i].result = result;
                    renderTable();
                    viewResult(i); // Auto-show latest

                } catch (e) {
                    leads[i].status = 'Error';
                    renderTable();
                }
            }
            btn.disabled = false;
            btn.innerHTML = originalText;
        }

        function viewResult(idx) {
            const data = leads[idx].result;
            if(!data) return;

            const card = document.getElementById('resultCard');
            card.classList.remove('hidden');

            document.getElementById('resName').innerText = data.metadata.client;
            document.getElementById('resLink').href = data.metadata.url;

            // Layman Verdict Banner
            const banner = document.getElementById('laymanBanner');
            if (banner) banner.remove(); // Clear previous

            if (data.layman_verdict) {
                const newBanner = document.createElement('div');
                newBanner.id = 'laymanBanner';

                // Color logic based on Veritic Score
                const score = data.veritic_result.integrity_score || 0;
                let bgClass = 'bg-slate-700';
                if(score < 50) bgClass = 'bg-red-600';
                if(score > 80) bgClass = 'bg-green-600';

                newBanner.className = `p-4 rounded-xl mb-6 font-bold text-white shadow-lg ${bgClass}`;
                newBanner.innerText = data.layman_verdict;

                // Insert after header (resName/resLink container is first child)
                card.children[0].after(newBanner);
            }

            // RimLab
            const r = data.rimlab_result;
            document.getElementById('rimlabConf').innerText = r.confidence;
            document.getElementById('rimlabDirector').innerText = r.ai_director;
            document.getElementById('rimlabEmail').innerText = r.ai_email;

            // Veritic
            const v = data.veritic_result;
            document.getElementById('veriticScore').innerText = v.integrity_score + "/100";
            
            const vMissing = document.getElementById('veriticMissing');
            vMissing.innerHTML = '';
            v.missing_data.forEach(m => {
                vMissing.innerHTML += `<span class="px-2 py-1 bg-red-900/30 text-red-400 rounded text-[10px] font-bold border border-red-500/20">${m}</span>`;
            });
            if(v.missing_data.length === 0) vMissing.innerHTML = '<span class="text-green-500 text-xs">All Clear</span>';

            const vExt = document.getElementById('veriticExtracted');
            vExt.innerHTML = '';
            for (const [key, val] of Object.entries(v.extracted_data)) {
                vExt.innerHTML += `<li><strong class="capitalize text-slate-400">${key}:</strong> ${val}</li>`;
            }

            // Choice
            const c = data.choice_result;
            document.getElementById('choiceScore').innerText = c.brand_score + "/100";
            document.getElementById('choiceArchetype').innerText = c.archetype;
            document.getElementById('choiceAlignment').innerText = '"' + c.alignment_analysis + '"';

            const cVibe = document.getElementById('choiceVibe');
            cVibe.innerHTML = '';
            c.vibe.forEach(adj => {
                 cVibe.innerHTML += `<span class="px-2 py-1 bg-purple-900/30 text-purple-300 rounded text-[10px] font-bold border border-purple-500/20">${adj}</span>`;
            });
        }

    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def read_root():
    return HTML_APP

@app.post("/audit")
async def perform_audit(request: AuditRequest):
    scraped_data = await scrape_site(request.url)
    if not scraped_data:
         # Fallback if scraping fails, analysis might still want to run on empty data or handle it
         scraped_data = {"content_preview": "", "title": "Scraping Failed", "url": request.url}
    
    result = await analyze_universal(scraped_data, request.dict())
    return result

@app.post("/generate-leads")
async def generate_leads(req: GeneratorRequest):
    try:
        # Get credentials
        credentials, project_id = google.auth.default()
        auth_req = GoogleAuthRequest()
        credentials.refresh(auth_req)

        # Fallback for project_id if not detected automatically
        if not project_id:
             project_id = os.environ.get("GCP_PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT")

        if not project_id:
            raise Exception("Could not determine Google Cloud Project ID")

        # Hardcode region as requested
        location = "us-central1"

        # Construct URL
        url = f"https://us-central1-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{location}/publishers/google/models/gemini-2.5-pro:generateContent"

        headers = {
            "Authorization": f"Bearer {credentials.token}",
            "Content-Type": "application/json; charset=utf-8"
        }

        prompt_text = f"""
QUERY: {req.prompt}
TASK: Search Google for the OFFICIAL websites.
CONSTRAINT: Do NOT guess. If unsure, skip.
OUTPUT FORMAT: You MUST return a strict JSON array of objects with exactly these keys: "client_name" and "url".
EXAMPLE: [{{"client_name": "Gymnazium Jana Keplera", "url": "https://gjk.cz"}}]
"""

        # Construct raw JSON payload
        payload = {
            "contents": [{ "role": "user", "parts": [{ "text": prompt_text }] }],
            "tools": [{ "googleSearch": {} }],
            "generationConfig": { "temperature": 0.1 }
        }

        # Make the request
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()

        # 1. Parse the Vertex AI JSON structure
        response_json = response.json()
        try:
            # Extract the text content
            raw_text = response_json['candidates'][0]['content']['parts'][0]['text']
        except (KeyError, IndexError):
            print(f"Vertex Error: {response.text}")
            raise HTTPException(status_code=500, detail="Invalid response structure from Vertex AI")

        # 2. Clean Markdown (removes ```json ... ```)
        cleaned_text = raw_text.strip()
        if cleaned_text.startswith("```json"):
            cleaned_text = cleaned_text[7:]
        elif cleaned_text.startswith("```"):
            cleaned_text = cleaned_text[3:]
        if cleaned_text.endswith("```"):
            cleaned_text = cleaned_text[:-3]

        # 3. Parse string to List
        try:
            data = json.loads(cleaned_text)
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail=f"AI returned invalid JSON: {cleaned_text}")

        # 4. CRITICAL: Normalize Keys for Frontend
        normalized_data = []
        for item in data:
            # Map AI keys to Frontend keys
            client_name = item.get('client_name') or item.get('name') or item.get('school') or item.get('title') or item.get('institution') or item.get('entity') or "Unknown"
            url = item.get('url') or item.get('website') or item.get('link') or item.get('web') or "#"

            normalized_data.append({
                "client_name": client_name,
                "url": url,
                "industry": "Education", # Defaulting for context
                "goals": "General Audit"
            })

        return normalized_data

    except Exception as e:
        # Ensure we log the error for debugging
        print(f"Error in generate_leads: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/support-chat")
async def support_chat(req: ChatRequest):
    try:
        model = GenerativeModel("gemini-2.5-pro")
        system_prompt = """Jsi technická podpora pro aplikaci Veritic Intelligence Hub.
        Tvým úkolem je vysvětlovat uživatelům, jak systém funguje.

        ZNALOSTNÍ BÁZE:
        1. Modul RimLab (Červená): Ukazuje 'AI Memory Risk' - tedy to, co si ChatGPT pamatuje z tréninkových dat (často staré omyly).
        2. Modul Veritic (Zelená): Ukazuje 'Web Reality' - fakta, která jsme právě našli na webu klienta.
        3. Modul Choice (Fialová): Ukazuje 'Brand Perception' - marketingový dojem a archetyp.
        4. Jak zadat prompt: Doporučuj specifické dotazy, např. 'Najdi 5 gymnázií v Praze', ne jen 'školy'.
        5. Interpretace: Pokud Veritic (Zelená) nenajde data, AI (Červená) bude halucinovat. To je špatně.

        Odpovídej stručně, nápomocně a pouze v Češtině."""

        full_prompt = f"{system_prompt}\n\nDOTAZ UŽIVATELE: {req.message}"
        response = await model.generate_content_async(full_prompt)
        return {"reply": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload-leads")
async def upload_leads(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(contents))
        elif file.filename.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(io.BytesIO(contents))
        else:
            raise HTTPException(status_code=400, detail="Invalid file type")

        # Normalize columns
        df.columns = [c.lower() for c in df.columns]
        # Rename common variations
        rename_map = {
            'name': 'client_name', 'company': 'client_name', 'institution': 'client_name',
            'web': 'url', 'website': 'url', 'link': 'url'
        }
        df.rename(columns=rename_map, inplace=True)

        # Fill missing
        if 'goals' not in df.columns:
            df['goals'] = "General Audit"
        if 'industry' not in df.columns:
            df['industry'] = "Unknown"

        return df[['client_name', 'url', 'industry', 'goals']].to_dict(orient='records')

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
