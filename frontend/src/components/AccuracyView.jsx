import React, { useMemo } from "react";
import { Bar, BarChart, CartesianGrid, ComposedChart, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api.js";
import { useAsync } from "../hooks.js";
import { fmtDayShort, fmtMW, fmtPct, fmtTime } from "../format.js";
import { C } from "../theme.js";
import { Metric, Panel } from "./Panel.jsx";

const axis = { tick: { fill: C.muted, fontSize: 12 }, stroke: C.grid };
const mwTick = (v) => `${Math.round(v).toLocaleString("en-GB")}`;

const horizonLabel = (r) => (r.horizon_to_h > 1000 ? `${r.horizon_from_h}h+` : `${r.horizon_from_h}–${r.horizon_to_h}h`);

export default function AccuracyView({ cutoff }) {
  const overall = useAsync(() => api.metrics(cutoff), [cutoff]);
  const daily = useAsync(() => api.daily(cutoff), [cutoff]);
  const hourly = useAsync(() => api.byHour(cutoff), [cutoff]);
  const horizon = useAsync(() => api.byHorizon(), []);
  const errors = useAsync(() => api.errors(cutoff), [cutoff]);

  const s = overall.data?.summary;

  const hist = useMemo(() => {
    const h = overall.data?.histogram;
    if (!h?.counts?.length) return [];
    return h.counts.map((count, i) => ({ mid: Math.round((h.edges[i] + h.edges[i + 1]) / 2), count }));
  }, [overall.data]);

  const errSeries = useMemo(() => (errors.data ?? []).map((e) => ({ t: new Date(e.startTime).getTime(), error: e.error })), [errors.data]);

  return (
    <>
      <div className="headline">
        <h2>How wrong is the forecast at decision time?</h2>
        {s?.n ? (
          <p>
            Using the forecast available at {cutoff} on the previous day, the average miss is{" "}
            <strong>{fmtMW(s.mae_mw)}</strong> per half-hour ({fmtPct(s.nmae_pct, 0)} of average output). In 9 of 10
            half-hours the miss is under <strong>{fmtMW(s.p90_abs_error_mw)}</strong>. The forecast runs{" "}
            {s.bias_mw > 0 ? "high" : "low"} by {fmtMW(Math.abs(s.bias_mw))} on average, so{" "}
            {s.bias_mw > 0 ? "relying on it alone tends to leave you short of power" : "relying on it alone tends to leave you over-bought"}.
          </p>
        ) : (
          <p>Loading metrics…</p>
        )}
      </div>

      {s?.n > 0 && (
        <dl className="metrics">
          <Metric label="Mean absolute error" value={fmtMW(s.mae_mw)} hint="MAE" />
          <Metric label="Root mean square error" value={fmtMW(s.rmse_mw)} hint="penalises big misses" />
          <Metric label="Bias" value={fmtMW(s.bias_mw)} hint="forecast − actual" />
          <Metric label="90th percentile miss" value={fmtMW(s.p90_abs_error_mw)} hint="size of a bad half-hour" />
          <Metric label="Error vs output" value={fmtPct(s.nmae_pct)} hint="MAE ÷ mean actual" />
          <Metric label="Percentage error" value={fmtPct(s.mape_pct)} hint={`slots ≥ ${s.mape_min_actual_mw} MW only`} />
          <Metric label="Coverage" value={fmtPct(s.coverage * 100, 0)} hint={`${s.n.toLocaleString("en-GB")} of ${s.n_slots_total.toLocaleString("en-GB")} half-hours`} />
        </dl>
      )}

      <div className="grid2">
        <Panel title="Error through the month" note="Above zero the forecast was too high; below zero too low." state={errors}>
          <div className="chart">
            <ResponsiveContainer>
              <LineChart data={errSeries} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
                <CartesianGrid stroke={C.grid} vertical={false} />
                <XAxis dataKey="t" type="number" scale="time" domain={["dataMin", "dataMax"]} tickFormatter={(t) => fmtDayShort(new Date(t).toISOString().slice(0, 10))} {...axis} minTickGap={40} />
                <YAxis {...axis} tickFormatter={mwTick} width={56} />
                <ReferenceLine y={0} stroke={C.ink} />
                <Tooltip labelFormatter={(t) => `${fmtDayShort(new Date(t).toISOString().slice(0, 10))} ${fmtTime(new Date(t).toISOString())}`} formatter={(v) => [fmtMW(v), "Error"]} />
                <Line dataKey="error" stroke={C.over} strokeWidth={1} dot={false} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Panel>

        <Panel title="How big are the misses?" note="Count of half-hours by error size (MW). A narrow hump near zero is good." state={overall}>
          <div className="chart">
            <ResponsiveContainer>
              <BarChart data={hist} margin={{ top: 8, right: 12, bottom: 0, left: 0 }} barCategoryGap={1}>
                <CartesianGrid stroke={C.grid} vertical={false} />
                <XAxis dataKey="mid" {...axis} tickFormatter={mwTick} minTickGap={24} />
                <YAxis {...axis} width={40} />
                <Tooltip formatter={(v) => [v, "Half-hours"]} labelFormatter={(m) => `Around ${fmtMW(m)}`} />
                <ReferenceLine x={0} stroke={C.ink} />
                <Bar dataKey="count" fill={C.forecast} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>

        <Panel title="Day by day" note="Average miss for each delivery day. Spikes are the days to be cautious about." state={daily}>
          <div className="chart">
            <ResponsiveContainer>
              <BarChart data={daily.data ?? []} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
                <CartesianGrid stroke={C.grid} vertical={false} />
                <XAxis dataKey="delivery_day" {...axis} tickFormatter={fmtDayShort} minTickGap={16} />
                <YAxis {...axis} tickFormatter={mwTick} width={56} />
                <Tooltip formatter={(v) => [fmtMW(v), "MAE"]} labelFormatter={fmtDayShort} />
                <Bar dataKey="mae_mw" fill={C.actual} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>

        <Panel title="Time of day" note="Bars are the average miss, the line is bias. Shows when the forecast is least reliable." state={hourly}>
          <div className="chart">
            <ResponsiveContainer>
              <ComposedChart data={hourly.data ?? []} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
                <CartesianGrid stroke={C.grid} vertical={false} />
                <XAxis dataKey="hour" {...axis} tickFormatter={(h) => `${String(h).padStart(2, "0")}:00`} minTickGap={16} />
                <YAxis {...axis} tickFormatter={mwTick} width={56} />
                <ReferenceLine y={0} stroke={C.ink} />
                <Tooltip formatter={(v, n) => [fmtMW(v), n]} labelFormatter={(h) => `${String(h).padStart(2, "0")}:00 UK`} />
                <Bar dataKey="mae_mw" name="MAE" fill={C.forecast} isAnimationActive={false} />
                <Line dataKey="bias_mw" name="Bias" stroke={C.over} strokeWidth={2} dot={false} isAnimationActive={false} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </Panel>
      </div>

      <Panel
        title="Does waiting for a newer forecast help?"
        note="Average miss by how many hours before delivery the forecast was published. Uses every forecast, not just the one at cut-off."
        state={horizon}
      >
        <div className="chart">
          <ResponsiveContainer>
            <BarChart data={(horizon.data ?? []).map((r) => ({ ...r, label: horizonLabel(r) }))} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
              <CartesianGrid stroke={C.grid} vertical={false} />
              <XAxis dataKey="label" {...axis} />
              <YAxis {...axis} tickFormatter={mwTick} width={56} />
              <Tooltip formatter={(v) => [fmtMW(v), "MAE"]} />
              <Bar dataKey="mae_mw" fill={C.under} isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Panel>
    </>
  );
}
