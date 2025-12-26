from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional
from src.scraper import scrape_site
from src.analyzer import analyze_content

app = FastAPI()

# --- Dátový Model (Formulár) ---
class AuditRequest(BaseModel):
    url: str
    client_name: str
    industry: str
    goals: Optional[str] = ""

# --- FRONTEND (HTML/CSS/JS) ---
# Toto je moderné UI vložené priamo do kódu pre jednoduché nasadenie
HTML_APP = """
<!DOCTYPE html>
<html lang="sk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CHOICE AI | Agency Audit</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        body { background-color: #0f172a; color: #e2e8f0; font-family: 'Inter', sans-serif; }
        .glass { background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.1); }
        .gradient-text { background: linear-gradient(45deg, #3b82f6, #8b5cf6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .loader { border-top-color: #3b82f6; -webkit-animation: spinner 1.5s linear infinite; animation: spinner 1.5s linear infinite; }
        @keyframes spinner { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body class="min-h-screen flex flex-col items-center py-10 px-4">

    <div class="text-center mb-10">
        <h1 class="text-5xl font-bold mb-2"><span class="gradient-text">CHOICE AI</span> Pilot</h1>
        <p class="text-slate-400">Agency Audit Engine v1.0</p>
    </div>

    <div class="w-full max-w-4xl grid grid-cols-1 md:grid-cols-3 gap-6">
        
        <div class="md:col-span-1 glass p-6 rounded-2xl h-fit">
            <h2 class="text-xl font-semibold mb-4 border-b border-slate-600 pb-2">Nastavenie Auditu</h2>
            <form id="auditForm" class="space-y-4">
                <div>
                    <label class="block text-sm text-slate-400 mb-1">URL Webu</label>
                    <input type="url" id="url" required placeholder="https://klient.sk" class="w-full bg-slate-800 border border-slate-600 rounded-lg p-2 focus:ring-2 focus:ring-blue-500 outline-none text-white">
                </div>
                <div>
                    <label class="block text-sm text-slate-400 mb-1">Meno Klienta</label>
                    <input type="text" id="client_name" required placeholder="Napr. Cafe Lux" class="w-full bg-slate-800 border border-slate-600 rounded-lg p-2 focus:ring-2 focus:ring-blue-500 outline-none text-white">
                </div>
                <div>
                    <label class="block text-sm text-slate-400 mb-1">Segment / Odvetvie</label>
                    <select id="industry" class="w-full bg-slate-800 border border-slate-600 rounded-lg p-2 focus:ring-2 focus:ring-blue-500 outline-none text-white">
                        <option value="E-commerce">E-commerce</option>
                        <option value="SaaS">SaaS / Software</option>
                        <option value="Služby">Lokálne Služby</option>
                        <option value="Real Estate">Reality</option>
                    </select>
                </div>
                <button type="submit" class="w-full bg-gradient-to-r from-blue-600 to-violet-600 hover:from-blue-500 hover:to-violet-500 text-white font-bold py-3 rounded-xl transition transform hover:scale-105 shadow-lg mt-4">
                    <i class="fas fa-rocket mr-2"></i> Spustiť Analýzu
                </button>
            </form>
        </div>

        <div class="md:col-span-2 glass p-6 rounded-2xl min-h-[400px] relative">
            
            <div id="loader" class="hidden absolute inset-0 flex flex-col items-center justify-center bg-slate-900/80 rounded-2xl z-10">
                <div class="loader ease-linear rounded-full border-4 border-t-4 border-gray-200 h-12 w-12 mb-4"></div>
                <p class="text-blue-400 animate-pulse">AI analyzuje štruktúru webu...</p>
                <p class="text-xs text-slate-500 mt-2">Sťahujem dáta cez Playwright</p>
            </div>

            <div id="emptyState" class="flex flex-col items-center justify-center h-full text-slate-500">
                <i class="fas fa-chart-pie text-6xl mb-4 opacity-50"></i>
                <p>Zadajte údaje vľavo a spustite audit.</p>
            </div>

            <div id="results" class="hidden space-y-6">
                <div class="flex justify-between items-start border-b border-slate-700 pb-4">
                    <div>
                        <h2 class="text-2xl font-bold text-white" id="res_title">Výsledok Analýzy</h2>
                        <a href="#" target="_blank" id="res_url" class="text-sm text-blue-400 hover:underline"></a>
                    </div>
                    <div class="text-center bg-slate-800 p-2 rounded-lg border border-slate-600">
                        <span class="block text-xs text-slate-400">CHOICE SKÓRE</span>
                        <span class="text-3xl font-bold text-green-400" id="res_score">--</span>
                    </div>
                </div>

                <div class="grid grid-cols-2 gap-4">
                    <div class="bg-slate-800/50 p-4 rounded-xl border border-slate-700">
                        <div class="text-slate-400 text-xs uppercase mb-1">UX & Dizajn</div>
                        <div class="text-xl font-semibold" id="res_ux">--</div>
                        <div class="h-1 bg-slate-700 mt-2 rounded-full"><div id="bar_ux" class="h-1 bg-blue-500 rounded-full" style="width: 0%"></div></div>
                    </div>
                    <div class="bg-slate-800/50 p-4 rounded-xl border border-slate-700">
                        <div class="text-slate-400 text-xs uppercase mb-1">SEO & Obsah</div>
                        <div class="text-xl font-semibold" id="res_seo">--</div>
                        <div class="h-1 bg-slate-700 mt-2 rounded-full"><div id="bar_seo" class="h-1 bg-purple-500 rounded-full" style="width: 0%"></div></div>
                    </div>
                </div>

                <div>
                    <h3 class="text-lg font-semibold mb-3">AI Postrehy</h3>
                    <div id="insights_list" class="space-y-3">
                        </div>
                </div>

                <div class="bg-blue-900/20 border border-blue-500/30 p-4 rounded-xl">
                    <h4 class="text-blue-400 font-bold mb-1"><i class="fas fa-lightbulb mr-2"></i>Odporúčanie</h4>
                    <p class="text-sm text-slate-300 italic" id="res_rec">--</p>
                </div>
            </div>
        </div>
    </div>

    <script>
        document.getElementById('auditForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            // UI Update
            const loader = document.getElementById('loader');
            const emptyState = document.getElementById('emptyState');
            const results = document.getElementById('results');
            
            loader.classList.remove('hidden');
            emptyState.classList.add('hidden');
            results.classList.add('hidden');

            // Data Prep
            const payload = {
                url: document.getElementById('url').value,
                client_name: document.getElementById('client_name').value,
                industry: document.getElementById('industry').value,
                goals: "General Audit"
            };

            try {
                const response = await fetch('/audit', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                if (!response.ok) throw new Error('Audit failed');

                const data = await response.json();
                renderResults(data);

            } catch (error) {
                alert("Chyba pri analýze: " + error.message);
                emptyState.classList.remove('hidden');
            } finally {
                loader.classList.add('hidden');
            }
        });

        function renderResults(data) {
            const r = document.getElementById('results');
            r.classList.remove('hidden');

            document.getElementById('res_title').innerText = data.summary.page_title || "Neznámy Titul";
            document.getElementById('res_url').innerText = document.getElementById('url').value;
            document.getElementById('res_url').href = document.getElementById('url').value;
            
            document.getElementById('res_score').innerText = data.summary.overall_score + "/100";
            
            document.getElementById('res_ux').innerText = data.summary.ux_score + "%";
            document.getElementById('bar_ux').style.width = data.summary.ux_score + "%";
            
            document.getElementById('res_seo').innerText = data.summary.seo_score + "%";
            document.getElementById('bar_seo').style.width = data.summary.seo_score + "%";

            document.getElementById('res_rec').innerText = data.recommendation;

            const list = document.getElementById('insights_list');
            list.innerHTML = '';
            
            data.insights.forEach(insight => {
                let colorClass = "border-l-4 border-blue-500 bg-slate-800";
                if(insight.type === 'warning') colorClass = "border-l-4 border-yellow-500 bg-slate-800";
                if(insight.type === 'success') colorClass = "border-l-4 border-green-500 bg-slate-800";

                list.innerHTML += `
                    <div class="${colorClass} p-3 rounded shadow-sm">
                        <div class="font-bold text-sm mb-1">${insight.title}</div>
                        <div class="text-xs text-slate-400">${insight.message}</div>
                    </div>
                `;
            });
        }
    </script>
</body>
</html>
"""

# --- ENDPOINTS ---

@app.get("/", response_class=HTMLResponse)
async def read_root():
    return HTML_APP

@app.post("/audit")
async def perform_audit(request: AuditRequest):
    # 1. Scrape
    scraped_data = await scrape_site(request.url)
    if not scraped_data:
        raise HTTPException(status_code=400, detail="Could not scrape URL")
    
    # 2. Analyze
    result = analyze_content(scraped_data, request.dict())
    return result
