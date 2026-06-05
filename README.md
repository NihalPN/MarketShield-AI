# 🛡️ MarketShield AI: Autonomous Market Surveillance & Scam Detection Pipeline

An end-to-end data engineering, Natural Language Processing (NLP), and threat intelligence pipeline designed to mathematically detect coordinated "pump-and-dump" market manipulation schemes and automatically generate C-suite level security briefs using a local LLM.

## 📈 Project Outcomes & Business Value
This pipeline solves a critical problem in small-cap day trading and platform trust & safety: **Alert Fatigue and Manipulation Traps.**
* **Capital Preservation:** Mathematically flags artificial, bot-driven volume spikes *before* retail traders buy into a deceptive "pump" trap.
* **Zero Alert Fatigue:** Replaces thousands of raw, noisy server alerts with a single, highly accurate, LLM-translated plain-English incident report.
* **Sentiment Verification:** Cross-references hard mathematical volume anomalies with NLP sentiment analysis of live news and forum comments to confirm coordinated manipulation.
* **100% Offline & Secure Data Handling:** Utilizes local Llama-3 (via Ollama) and LangChain to process sensitive financial databases entirely on-device without leaking data to public APIs.

## 🏗️ Pipeline Architecture & Tech Stack

1. **Data Ingestion & Storage:** `SQLite3`, `SQLAlchemy`, `Faker`, `BeautifulSoup4`, `Feedparser`
2. **Statistical Anomaly Engine:** `Pandas`, `NumPy` (Rolling 96-hour Z-Score baseline)
3. **NLP Sentiment Engine:** `spaCy`, `NLTK` (Market psychology and hype tracking)
4. **Automated Visualization:** `Matplotlib`, `Seaborn`
5. **AI Orchestration:** `LangChain`, `Ollama` (Local Llama-3 8B)
6. **Infrastructure:** `Docker` containerized for cross-platform reproducibility.

## ✨ Core Pipeline Stages

* **Stage 1: The Baseline (Math Filter):** Instead of relying on static thresholds, the pipeline calculates a dynamic rolling 96-hour (4-day) mean and standard deviation. This allows the system to adapt to organic market volatility without triggering false positives.
* **Stage 2: The Trap (Anomaly Detection):** Sudden, extreme spikes in volume and social sentiment are mathematically isolated using a strict Z-score threshold (Z > 3.0). 
* **Stage 3: The Translator (AI Reporting):** A LangChain ReAct agent securely queries the relational database, extracts the exact coordinates of the threat (Ticker, Volume, Timestamp), and bypasses standard LLM safety filters to generate a clean, actionable executive brief.

## 💻 Output Example: The Executive Brief
When the pipeline detects a simulated `$FAKE` botnet attack, the LangChain agent successfully queries the SQLite database and outputs the following automated intelligence brief:

> **FINAL EXECUTIVE BRIEF:** > The ticker '$FAKE' experienced a peak volume of 2552 at exactly 14:00:00 on January 22, 2026, which appears to be an artificially inflated spike due to its unusually high magnitude compared to surrounding trading activity.

---

## ⚙️ How to Run the Pipeline (Local Setup)

The data ingestion, NLP, and anomaly detection scripts are modular. To simulate a live market environment, establish a historical baseline, inject a synthetic botnet attack, and run the mathematical filters, follow this exact execution order.

### 1. The Execution Order
Open your terminal, clone the repository, navigate to the `data_pipeline` folder, and run these scripts sequentially:

```bash
git clone [https://github.com/NihalPN/MarketShield-AI.git](https://github.com/NihalPN/MarketShield-AI.git)
cd MarketShield-AI/data_pipeline
```
# Step 1: Initialize the database schema and generate current baseline data
```bash
python synthetic_generator.py
```
# Step 2: Backfill deep historical market data to establish long-term normal trends
```bash
python backfill.py
```
# Step 3: Inject the threat (Simulates a coordinated "pump and dump" attack on the $FAKE ticker)
```bash
python hacker_backfill.py
```
# Step 4: Run the detection engine (Calculates rolling Z-scores, flags Step 3, and triggers the AI brief)
```bash
python z-score_anomly.py
```
# Step 5: (Optional) Generate the visual dashboard to view the anomaly graph
```bash
python visualizer.py
```
(Note: Advanced users can run the news_fetcher.py and sentiment_pipeline.py scripts to test the NLP feature engineering branch).

### 2. Interactive Exploration (Jupyter Notebook)
For a more hands-on, step-by-step walkthrough of the architecture, an interactive Jupyter Notebook (.ipynb) is included in this repository.

Launch the notebook to run the data generation, view the rolling Z-score math, and trigger the LangChain AI agent cell-by-cell. This is the absolute best way to deeply understand the pipeline's logic and view the Matplotlib/Seaborn visualizations inline.

### 3. Docker Deployment
This entire pipeline is containerized to ensure zero dependency conflicts. You can spin up the threat hunting environment on any machine with Docker installed:

```bash
docker build -t marketshield-pipeline:v1 .
docker run -it marketshield-pipeline:v1
```
