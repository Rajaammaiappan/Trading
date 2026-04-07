"""
Short Option Pro - Flask Web Application
Updated:
- Withdrawal / fund movement tracking with remarks
- Performance includes withdrawals summary
- Mobile + Desktop responsive view
- Checklist updated from attached HTML
"""

from flask import Flask, render_template, request, jsonify
from datetime import datetime
import sqlite3
import json
import random
import requests
import os

app = Flask(__name__)
DB_PATH = "short_option_trades.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            symbol TEXT NOT NULL,
            strategy_type TEXT NOT NULL,
            expiry_date TEXT NOT NULL,
            days_to_expiry INTEGER,
            atm REAL NOT NULL,
            lots INTEGER NOT NULL,
            lot_size INTEGER NOT NULL,
            sell_pe_strike REAL,
            sell_ce_strike REAL,
            premium_sell_pe REAL,
            premium_sell_ce REAL,
            total_credit REAL NOT NULL,
            estimated_max_profit REAL NOT NULL,
            estimated_risk_note TEXT,
            exit_pnl REAL,
            exit_date TIMESTAMP,
            notes TEXT
        );
        CREATE TABLE IF NOT EXISTS checklists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            symbol TEXT NOT NULL,
            checklist_type TEXT DEFAULT 'NIFTY',
            all_checked INTEGER NOT NULL,
            score INTEGER NOT NULL,
            checklist_json TEXT,
            notes TEXT
        );
        CREATE TABLE IF NOT EXISTS post_market_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_date TEXT NOT NULL,
            max_profit REAL,
            min_profit REAL,
            max_loss REAL,
            daily_pnl REAL,
            status TEXT,
            justification TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            amount REAL NOT NULL,
            type TEXT NOT NULL,
            remarks TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()

init_db()

_session = requests.Session()
_session.headers.update({'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json',
                          'Referer': 'https://www.nseindia.com'})
_use_simulated = False

def fetch_index(index_name):
    global _use_simulated
    if _use_simulated:
        return simulated(index_name)
    try:
        _session.get("https://www.nseindia.com", timeout=8)
        url = f"https://www.nseindia.com/api/equity-stockIndices?index={index_name}"
        r = _session.get(url, timeout=8)
        if r.status_code == 200:
            data = r.json()
            if data.get('data'):
                d = data['data'][0]
                return {'value': float(d.get('last', 0) or 0),
                        'change': float(d.get('change', 0) or 0),
                        'pct': float(d.get('pChange', 0) or 0), 'source': 'NSE Live'}
    except Exception:
        _use_simulated = True
    return simulated(index_name)

def simulated(name):
    bases = {"NIFTY%2050": (22713, 150), "NIFTY%20BANK": (52150, 300),
             "INDIA%20VIX": (14.5, 0.8), "SENSEX": (74870, 400)}
    base, rng = bases.get(name, (20000, 100))
    change = random.uniform(-rng, rng)
    return {'value': round(base + change, 2), 'change': round(change, 2),
            'pct': round((change / base) * 100, 2), 'source': 'Simulated'}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/market")
def market_data():
    return jsonify({
        "nifty": fetch_index("NIFTY%2050"),
        "banknifty": fetch_index("NIFTY%20BANK"),
        "sensex": fetch_index("SENSEX"),
        "vix": fetch_index("INDIA%20VIX"),
        "time": datetime.now().strftime("%d %b %Y %H:%M:%S")
    })

@app.route("/api/calculate", methods=["POST"])
def calculate():
    d = request.json
    atm = float(d["atm"])
    strategy = d["strategy"]
    qty = int(d["lot_size"]) * int(d["lots"])
    sell_pe = round(atm - float(d["put_dist"])) if strategy in ("SELL_PE", "SELL_BOTH") else None
    sell_ce = round(atm + float(d["call_dist"])) if strategy in ("SELL_CE", "SELL_BOTH") else None
    p_pe = float(d.get("premium_pe", 0)) if strategy in ("SELL_PE", "SELL_BOTH") else 0
    p_ce = float(d.get("premium_ce", 0)) if strategy in ("SELL_CE", "SELL_BOTH") else 0
    total_credit = (p_pe + p_ce) * qty
    notes_map = {"SELL_PE": "Downside risk if market falls sharply.",
                 "SELL_CE": "Upside risk if market rises sharply.",
                 "SELL_BOTH": "High risk on strong directional/volatile moves."}
    return jsonify({"sell_pe": sell_pe, "sell_ce": sell_ce, "qty": qty,
                    "total_credit": round(total_credit, 2), "max_profit": round(total_credit, 2),
                    "risk_note": notes_map.get(strategy, ""), "atm": atm,
                    "strategy": strategy, "lots": d["lots"], "lot_size": d["lot_size"]})

@app.route("/api/trade", methods=["POST"])
def save_trade():
    d = request.json
    conn = get_db()
    try:
        expiry = d.get("expiry_date", "")
        try:
            dte = max(0, (datetime.strptime(expiry, "%Y-%m-%d").date() - datetime.now().date()).days)
        except Exception:
            dte = 0
        cur = conn.execute("""
            INSERT INTO trades (symbol, strategy_type, expiry_date, days_to_expiry, atm, lots, lot_size,
                sell_pe_strike, sell_ce_strike, premium_sell_pe, premium_sell_ce,
                total_credit, estimated_max_profit, estimated_risk_note, notes)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (d["symbol"], d["strategy"], expiry, dte, d["atm"], d["lots"], d["lot_size"],
              d.get("sell_pe"), d.get("sell_ce"), d.get("premium_pe", 0), d.get("premium_ce", 0),
              d["total_credit"], d["max_profit"], d.get("risk_note", ""), d.get("notes", "")))
        conn.commit()
        return jsonify({"success": True, "id": cur.lastrowid})
    finally:
        conn.close()

@app.route("/api/trades")
def get_trades():
    conn = get_db()
    rows = conn.execute("SELECT * FROM trades ORDER BY date DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/trade/<int:tid>/exit", methods=["POST"])
def update_exit(tid):
    d = request.json
    conn = get_db()
    conn.execute("UPDATE trades SET exit_pnl=?, exit_date=CURRENT_TIMESTAMP WHERE id=?",
                 (d["exit_pnl"], tid))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route("/api/checklist", methods=["POST"])
def save_checklist():
    d = request.json
    conn = get_db()
    conn.execute("INSERT INTO checklists (symbol, checklist_type, all_checked, score, checklist_json, notes) VALUES (?,?,?,?,?,?)",
                 (d["symbol"], d["type"], d["all_ok"], d["score"], json.dumps(d["states"]), d.get("notes", "")))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route("/api/checklists")
def get_checklists():
    conn = get_db()
    rows = conn.execute("SELECT * FROM checklists ORDER BY date DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/postmarket", methods=["POST"])
def save_postmarket():
    d = request.json
    pnl = float(d.get("daily_pnl", 0))
    mp, mnp, ml = float(d.get("max_profit", 0)), float(d.get("min_profit", 0)), float(d.get("max_loss", 0))
    if pnl <= -abs(ml): status = "LOSS HIT"
    elif pnl < 0: status = "SMALL LOSS"
    elif pnl < mnp: status = "SMALL PROFIT"
    elif pnl <= mp: status = "TARGET HIT"
    else: status = "SUPER PROFIT"
    conn = get_db()
    conn.execute("INSERT INTO post_market_analysis (trade_date, max_profit, min_profit, max_loss, daily_pnl, status, justification) VALUES (?,?,?,?,?,?,?)",
                 (d["trade_date"], mp, mnp, ml, pnl, status, d.get("justification", "")))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "status": status})

@app.route("/api/postmarket/all")
def get_postmarket():
    conn = get_db()
    rows = conn.execute("SELECT * FROM post_market_analysis ORDER BY trade_date DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/withdrawal", methods=["POST"])
def save_withdrawal():
    d = request.json
    conn = get_db()
    conn.execute("INSERT INTO withdrawals (date, amount, type, remarks) VALUES (?,?,?,?)",
                 (d["date"], float(d["amount"]), d["type"], d.get("remarks", "")))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route("/api/withdrawals")
def get_withdrawals():
    conn = get_db()
    rows = conn.execute("SELECT * FROM withdrawals ORDER BY date DESC, id DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/withdrawal/<int:wid>", methods=["DELETE"])
def delete_withdrawal(wid):
    conn = get_db()
    conn.execute("DELETE FROM withdrawals WHERE id=?", (wid,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route("/api/performance")
def performance():
    conn = get_db()
    rows = conn.execute("SELECT * FROM trades WHERE exit_pnl IS NOT NULL").fetchall()
    trades = [dict(r) for r in rows]
    wrows = conn.execute("SELECT * FROM withdrawals ORDER BY date DESC").fetchall()
    withdrawals = [dict(r) for r in wrows]
    conn.close()

    total_withdrawn = sum(w["amount"] for w in withdrawals if w["type"] == "withdrawal")
    total_deposited = sum(w["amount"] for w in withdrawals if w["type"] == "deposit")

    if not trades:
        return jsonify({"total": 0, "wins": 0, "losses": 0, "win_rate": 0,
                        "total_pnl": 0, "avg": 0, "monthly": [],
                        "total_withdrawn": round(total_withdrawn, 2),
                        "total_deposited": round(total_deposited, 2),
                        "net_withdrawn": round(total_withdrawn - total_deposited, 2),
                        "withdrawals": withdrawals})

    wins = [t for t in trades if t["exit_pnl"] > 0]
    total_pnl = sum(t["exit_pnl"] for t in trades)
    monthly = {}
    for t in trades:
        # Use exit_date if available, fall back to trade date
        raw = t.get("exit_date") or t.get("date") or ""
        m = raw[:7] if raw else "unknown"
        if m not in monthly:
            monthly[m] = {"month": m, "pnl": 0, "count": 0}
        monthly[m]["pnl"] += t["exit_pnl"]
        monthly[m]["count"] += 1

    return jsonify({
        "total": len(trades), "wins": len(wins), "losses": len(trades) - len(wins),
        "win_rate": round(len(wins) / len(trades) * 100, 1),
        "total_pnl": round(total_pnl, 2), "avg": round(total_pnl / len(trades), 2),
        "monthly": sorted(monthly.values(), key=lambda x: x["month"], reverse=True),
        "total_withdrawn": round(total_withdrawn, 2),
        "total_deposited": round(total_deposited, 2),
        "net_withdrawn": round(total_withdrawn - total_deposited, 2),
        "withdrawals": withdrawals
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
