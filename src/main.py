from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional
import pandas as pd
import io
import json
import asyncio
from vertexai.generative_models import GenerativeModel
from src.scraper import scrape_site
from src.analyzer import analyze_universal

app = FastAPI()

# --- Data Models ---
class AuditRequest(BaseModel):
    url: str
    client_name: str
    industry: str
    goals: str

class GeneratorRequest(BaseModel):
    prompt: str

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
            <p class="text-slate-400 text-sm">Unified Audit & Choice Analysis Engine</p>
        </div>
        <div class="flex space-x-4">
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

    <script>
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
            
            try {
                const res = await fetch('/generate-leads', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ prompt })
                });
                const data = await res.json();
                loadTable(data);
            } catch(e) { alert(e); }
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
            document.getElementById('btnStart').disabled = true;

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
            document.getElementById('btnStart').disabled = false;
        }

        function viewResult(idx) {
            const data = leads[idx].result;
            if(!data) return;

            const card = document.getElementById('resultCard');
            card.classList.remove('hidden');

            document.getElementById('resName').innerText = data.metadata.client;
            document.getElementById('resLink').href = data.metadata.url;

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
        model = GenerativeModel("gemini-2.5-pro")
        prompt = f"""
        Generate a JSON list of 5 real institutions/companies based on this request: "{req.prompt}".
        For each, provide:
        - client_name (string)
        - url (string, start with https://)
        - industry (string)
        - goals (string, inferred goals based on their nature)

        Output strictly JSON array. No markdown.
        """
        response = await model.generate_content_async(prompt)
        text = response.text.strip()
        # Clean potential markdown
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text)
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
