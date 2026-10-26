const TZ = "Europe/London";

export const fmtMW = (v, digits = 0) =>
  v === null || v === undefined ? "–" : `${Number(v).toLocaleString("en-GB", { maximumFractionDigits: digits })} MW`;

export const fmtGWh = (mwh) => (mwh === null || mwh === undefined ? "–" : `${(mwh / 1000).toLocaleString("en-GB", { maximumFractionDigits: 1 })} GWh`);

export const fmtPct = (v, digits = 1) => (v === null || v === undefined ? "–" : `${Number(v).toFixed(digits)}%`);

export const fmtTime = (iso) =>
  new Intl.DateTimeFormat("en-GB", { timeZone: TZ, hour: "2-digit", minute: "2-digit" }).format(new Date(iso));

export const fmtDayLong = (isoDay) =>
  new Intl.DateTimeFormat("en-GB", { weekday: "long", day: "numeric", month: "long", timeZone: "UTC" }).format(new Date(`${isoDay}T12:00:00Z`));

export const fmtDayShort = (isoDay) =>
  new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", timeZone: "UTC" }).format(new Date(`${isoDay}T12:00:00Z`));

export const fmtStamp = (iso) =>
  new Intl.DateTimeFormat("en-GB", { timeZone: TZ, weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }).format(new Date(iso));

export const addDays = (isoDay, n) => {
  const d = new Date(`${isoDay}T12:00:00Z`);
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
};
