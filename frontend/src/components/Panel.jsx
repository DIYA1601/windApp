import React from "react";

// A titled block with a one-line plain-English explanation of what it shows.
export function Panel({ title, note, children, state }) {
  return (
    <section className="panel">
      <header>
        <h3>{title}</h3>
        {note && <p>{note}</p>}
      </header>
      {state?.loading && <div className="status">Loading…</div>}
      {state?.error && <div className="status error">{state.error.message}</div>}
      {!state?.loading && !state?.error && children}
    </section>
  );
}

export function Metric({ label, value, hint }) {
  return (
    <div className="metric">
      <dt>{label}</dt>
      <dd>{value}</dd>
      {hint && <small>{hint}</small>}
    </div>
  );
}
