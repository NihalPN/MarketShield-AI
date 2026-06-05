import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "database", "techpulse.db"))
output_image = os.path.abspath(os.path.join(os.path.dirname(__file__), "anomaly_report.png"))

def generate_executive_dashboard():
    print("--- Stage 8: Executive Visualization Engine ---")
    print("[*] Querying database for the Jan 20-24 anomaly window...")
    
    con = sqlite3.connect(db_path)
    
    # Fetch data specifically around the time of our attack to frame the visual
    query = """
        SELECT ticker, metric_hour, rolling_24h_volume, rolling_24h_sentiment
        FROM hourly_ticker_metrics
        WHERE metric_hour BETWEEN '2026-01-19 00:00:00' AND '2026-01-25 00:00:00'
        AND ticker IN ('$FAKE', '$AAPL', '$MSFT')
    """
    df = pd.read_sql_query(query, con)
    con.close()
    
    df['metric_hour'] = pd.to_datetime(df['metric_hour'])
    
    print("[*] Rendering high-fidelity Matplotlib/Seaborn graphics...")
    
    # Set up the visual style
    sns.set_theme(style="darkgrid")
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)
    fig.suptitle('TechPulse Threat Intelligence: Coordinated Bot Attack Detected', fontsize=18, fontweight='bold')
    
    # --- TOP PLOT: Rolling Volume ---
    sns.lineplot(data=df, x='metric_hour', y='rolling_24h_volume', hue='ticker', 
                 palette={'$FAKE': '#ff2a2a', '$AAPL': '#4a90e2', '$MSFT': '#50e3c2'}, 
                 linewidth=2.5, ax=ax1)
    ax1.set_title('24-Hour Rolling Conversation Volume', fontsize=14)
    ax1.set_ylabel('Total Comments (24h Window)')
    ax1.axvspan(pd.to_datetime('2026-01-21 14:00:00'), pd.to_datetime('2026-01-23 14:00:00'), 
                color='red', alpha=0.1, label='Detected Attack Window')
    ax1.legend(loc='upper left')
    
    # --- BOTTOM PLOT: Sentiment Trajectory ---
    sns.lineplot(data=df, x='metric_hour', y='rolling_24h_sentiment', hue='ticker', 
                 palette={'$FAKE': '#ff2a2a', '$AAPL': '#4a90e2', '$MSFT': '#50e3c2'}, 
                 linewidth=2.0, ax=ax2, legend=False)
    ax2.set_title('24-Hour Rolling Sentiment Trajectory', fontsize=14)
    ax2.set_ylabel('Sentiment (-1.0 to 1.0)')
    ax2.set_xlabel('Timeline (Hourly)')
    ax2.set_ylim(-0.5, 1.0)
    
    # Save the output
    plt.tight_layout()
    plt.savefig(output_image, dpi=300, bbox_inches='tight')
    
    print(f"[✔] Dashboard rendered successfully!")
    print(f"[✔] Saved high-resolution artifact to: {output_image}")

if __name__ == "__main__":
    generate_executive_dashboard()