import React, { useState } from "react";
import { api } from "./api.js";
import { useAsync } from "./hooks.js";
import { addDays, fmtDayLong } from "./format.js";
import DecisionView from "./components/DecisionView.jsx";
import AccuracyView from "./components/AccuracyView.jsx";

export default function App() {
  const cfg = useAsync(() => api.config(), []);
  const [tab, setTab] = useState("decision");
  const [day, setDay] = useState("2026-01-15");
  const [cutoff, setCutoff] = useState(null);

  const c = cfg.data;
  const activeCutoff = cutoff ?? c?.default_cutoff ?? "09:00";
  const first = c?.first_delivery_day ?? "2026-01-02";
  const last = c?.last_delivery_day ?? "2026-02-01";
  const clamp = (d) => (d < first ? first : d > last ? last : d);
  const validCutoff = /^\d{2}:\d{2}$/.test(activeCutoff);

  return (
    <div className="shell">
      <aside className="rail">
        <h1>Wind forecast desk</h1>
        <p className="sub">UK day-ahead purchasing, January 2026</p>

        <label htmlFor="day">Delivery day</label>
        <div className="stepper">
          <button type="button" aria-label="Previous day" onClick={() => setDay(clamp(addDays(day, -1)))} disabled={day <= first}>
            ‹
          </button>
          <input id="day" type="date" value={day} min={first} max={last} onChange={(e) => e.target.value && setDay(clamp(e.target.value))} />
          <button type="button" aria-label="Next day" onClick={() => setDay(clamp(addDays(day, 1)))} disabled={day >= last}>
            ›
          </button>
        </div>
        <p className="hint">{fmtDayLong(day)}</p>

        <label htmlFor="cutoff">Decision cut-off on the day before (UK time)</label>
        <input id="cutoff" type="time" value={activeCutoff} onChange={(e) => e.target.value && setCutoff(e.target.value)} />
        <p className="hint">
          Only forecasts published up to this time are used. Try an earlier or later time to see what you gain or lose by waiting.
        </p>

        <nav aria-label="Views">
          <button type="button" className={tab === "decision" ? "on" : ""} aria-pressed={tab === "decision"} onClick={() => setTab("decision")}>
            Decision day
          </button>
          <button type="button" className={tab === "accuracy" ? "on" : ""} aria-pressed={tab === "accuracy"} onClick={() => setTab("accuracy")}>
            Forecast accuracy
          </button>
        </nav>

        <footer>
          Source: Elexon BMRS, national wind (FUELHH actuals, WINDFOR forecasts). Error = forecast − actual.
        </footer>
      </aside>

      <main>
        {cfg.error && (
          <div className="status error">
            Could not reach the data service: {cfg.error.message}. Start the backend or check the deployment.
          </div>
        )}
        {c?.data?.source === "synthetic" && (
          <div className="status warn">Demo data: these figures are synthetic and are not real Elexon values.</div>
        )}
        {c?.data?.source === "missing" && (
          <div className="status error">No data loaded. Run the ingest script (see README) and restart.</div>
        )}
        {!validCutoff && <div className="status warn">Enter the cut-off as HH:MM.</div>}
        {c && validCutoff && (tab === "decision" ? <DecisionView day={day} cutoff={activeCutoff} /> : <AccuracyView cutoff={activeCutoff} />)}
      </main>
    </div>
  );
}
