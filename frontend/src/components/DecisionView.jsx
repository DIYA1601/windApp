import React, { useMemo } from "react";
import { Area, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api.js";
import { useAsync } from "../hooks.js";
import { fmtDayLong, fmtGWh, fmtMW, fmtStamp, fmtTime } from "../format.js";
import { C } from "../theme.js";
import { Metric, Panel } from "./Panel.jsx";

function Headline({ d }) {
  const { band, summary } = d;
  const when = fmtStamp(d.cutoff_utc);
  return (
    <div className="headline">
      <h2>
        Wind on {fmtDayLong(d.delivery_day)}: {fmtGWh(summary.forecast_energy_mwh)} expected
      </h2>
      <p>
        This is the latest forecast available at the decision cut-off ({when}). Anything published after that is
        not shown, because you could not have used it.{" "}
        {band ? (
          <>
            Across {band.history_days} earlier days, in 9 of 10 half-hours the forecast was no more than{" "}
            <strong>{fmtMW(band.hi_error)}</strong> too high or <strong>{fmtMW(-band.lo_error)}</strong> too low.
            Plan your thermal purchase with that margin.
          </>
        ) : (
          <>There are not yet enough earlier days to size the error margin for this day.</>
        )}
      </p>
    </div>
  );
}

function SlotTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const s = payload[0].payload;
  return (
    <div className="tip">
      <b>{fmtTime(s.startTime)}</b>
      <div>Forecast: {fmtMW(s.forecast)}</div>
      {s.band && (
        <div>
          Likely range: {fmtMW(s.band[0])} to {fmtMW(s.band[1])}
        </div>
      )}
      <div>Actual: {fmtMW(s.actual)}</div>
      {s.horizon_h !== null && <div className="muted">Forecast age: {s.horizon_h} h before delivery</div>}
    </div>
  );
}

export default function DecisionView({ day, cutoff }) {
  const state = useAsync(() => api.decision(day, cutoff), [day, cutoff]);
  const d = state.data;

  const rows = useMemo(
    () =>
      (d?.slots ?? []).map((s) => ({
        ...s,
        t: new Date(s.startTime).getTime(),
        band: s.band_low !== null ? [s.band_low, s.band_high] : null,
      })),
    [d]
  );

  const missing = d ? d.summary.slots_total - d.summary.slots_with_forecast : 0;
  const m = d?.summary.day_metrics;

  return (
    <>
      {state.loading && <div className="status">Loading…</div>}
      {state.error && <div className="status error">{state.error.message}</div>}
      {d && (
        <>
          <Headline d={d} />
          {missing > 0 && (
            <div className="status warn">
              {missing} of {d.summary.slots_total} half-hours had no forecast published before the cut-off.
            </div>
          )}
          <Panel
            title="Forecast available at cut-off vs what happened"
            note="The teal line is what you could see when buying. The amber line is the outturn, shown afterwards so you can judge the forecast."
          >
            <div className="chart tall">
              <ResponsiveContainer>
                <ComposedChart data={rows} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
                  <CartesianGrid stroke={C.grid} vertical={false} />
                  <XAxis
                    dataKey="t"
                    type="number"
                    scale="time"
                    domain={["dataMin", "dataMax"]}
                    tickFormatter={fmtTime}
                    tick={{ fill: C.muted, fontSize: 12 }}
                    minTickGap={32}
                  />
                  <YAxis tick={{ fill: C.muted, fontSize: 12 }} width={56} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} unit=" MW" hide={false} />
                  <Tooltip content={<SlotTooltip />} />
                  <Legend verticalAlign="top" height={28} />
                  <Area dataKey="band" name="Likely range" stroke="none" fill={C.band} fillOpacity={0.16} isAnimationActive={false} />
                  <Line dataKey="forecast" name="Forecast at cut-off" stroke={C.forecast} strokeWidth={2.5} dot={false} isAnimationActive={false} />
                  <Line dataKey="actual" name="Actual" stroke={C.actual} strokeWidth={2} dot={false} isAnimationActive={false} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </Panel>

          <dl className="metrics">
            <Metric label="Forecast energy" value={fmtGWh(d.summary.forecast_energy_mwh)} hint="what you saw at cut-off" />
            <Metric label="Actual energy" value={fmtGWh(d.summary.actual_energy_mwh)} hint="outturn, known afterwards" />
            <Metric label="Mean absolute error" value={fmtMW(m?.mae_mw)} hint="this day, per half-hour" />
            <Metric label="Bias" value={fmtMW(m?.bias_mw)} hint={m?.bias_mw > 0 ? "forecast ran high" : "forecast ran low"} />
            <Metric label="Worst miss" value={fmtMW(m?.max_abs_error_mw)} hint="single half-hour" />
          </dl>
        </>
      )}
    </>
  );
}
