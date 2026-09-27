import { useState } from "react";
import { measurement, utc } from "./api";
import type { Timeline as TimelineData, TimelinePass } from "./api";

const W = 720;
const H = 190;
const M = { left: 46, right: 14, top: 14, bottom: 28 };
const TICKS = [0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000];
const DAY_MS = 86_400_000;

function logScale(min: number, max: number) {
  const lo = Math.log10(min);
  const hi = Math.log10(max);
  const top = M.top;
  const bottom = H - M.bottom;
  return (value: number) =>
    bottom - ((Math.log10(value) - lo) / (hi - lo || 1)) * (bottom - top);
}

function runs(days: TimelineData["days"]) {
  const gaps: { start: string; end: string }[] = [];
  for (const day of days) {
    if (day.retrieved) continue;
    const last = gaps[gaps.length - 1];
    const previous = last
      ? new Date(Date.parse(last.end) + DAY_MS).toISOString().slice(0, 10)
      : null;
    if (last && previous === day.date) last.end = day.date;
    else gaps.push({ start: day.date, end: day.date });
  }
  return gaps;
}

export function Timeline({ data }: { data: TimelineData }) {
  const [active, setActive] = useState<TimelinePass | null>(null);
  const start = Date.parse(data.days[0].date + "T00:00:00Z");
  const end = Date.parse(data.as_of);
  const x = (time: number) =>
    M.left + ((time - start) / (end - start || 1)) * (W - M.left - M.right);
  const plotted = data.overpasses.filter((p) => p.max_frp_mw != null);
  const values = plotted.map((p) => p.max_frp_mw as number);
  const lowest = TICKS.filter(
    (t) => t <= Math.max(0.1, Math.min(...values, 1)),
  );
  const highest = TICKS.filter((t) => t >= Math.max(...values, 2) * 1.25);
  const min = lowest[lowest.length - 1] ?? 0.1;
  const max = highest[0] ?? 1000;
  const y = logScale(min, max);
  const ticks = TICKS.filter((t) => t >= min && t <= max);
  const months: number[] = [];
  const cursor = new Date(start);
  cursor.setUTCDate(1);
  cursor.setUTCMonth(cursor.getUTCMonth() + 1);
  while (cursor.getTime() <= end) {
    months.push(cursor.getTime());
    cursor.setUTCMonth(cursor.getUTCMonth() + 1);
  }
  const unknownDays = data.days.filter((d) => !d.retrieved).length;
  const episode = Date.parse(data.episode_start);

  return (
    <figure className="timeline">
      <div className="timeline-legend" aria-hidden="true">
        <span>
          <i className="dot night" /> Night overpass
        </span>
        <span>
          <i className="dot day" /> Day overpass
        </span>
        <span>
          <i className="hatch" /> Not retrieved (unknown, not zero)
        </span>
        <span>
          <i className="asof" /> Assessed time
        </span>
      </div>
      <div className="timeline-plot">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          role="img"
          aria-label={`Maximum FRP per satellite overpass within ${data.radius_m} metres over ${data.days.length - 1} days`}
        >
          <defs>
            <pattern
              id="not-retrieved"
              width="6"
              height="6"
              patternUnits="userSpaceOnUse"
              patternTransform="rotate(45)"
            >
              <rect width="6" height="6" fill="#f3f4f1" />
              <line
                x1="0"
                y1="0"
                x2="0"
                y2="6"
                stroke="#cfd4cc"
                strokeWidth="2"
              />
            </pattern>
          </defs>
          {runs(data.days).map((gap) => (
            <rect
              key={gap.start}
              x={x(Date.parse(gap.start + "T00:00:00Z"))}
              y={M.top}
              width={Math.max(
                1,
                x(Date.parse(gap.end + "T00:00:00Z") + DAY_MS) -
                  x(Date.parse(gap.start + "T00:00:00Z")),
              )}
              height={H - M.top - M.bottom}
              fill="url(#not-retrieved)"
            />
          ))}
          <rect
            x={x(episode)}
            y={M.top}
            width={Math.max(2, x(end) - x(episode))}
            height={H - M.top - M.bottom}
            className="episode-band"
          />
          {ticks.map((tick) => (
            <g key={tick}>
              <line
                x1={M.left}
                x2={W - M.right}
                y1={y(tick)}
                y2={y(tick)}
                className="grid"
              />
              <text
                x={M.left - 6}
                y={y(tick) + 3}
                className="axis"
                textAnchor="end"
              >
                {tick}
              </text>
            </g>
          ))}
          {months.map((month) => (
            <text
              key={month}
              x={x(month)}
              y={H - 8}
              className="axis"
              textAnchor="middle"
            >
              {new Date(month).toLocaleString("en-GB", {
                month: "short",
                timeZone: "UTC",
              })}
            </text>
          ))}
          <line
            x1={x(end)}
            x2={x(end)}
            y1={M.top - 4}
            y2={H - M.bottom}
            className="asof-line"
          />
          {plotted.map((pass) => {
            const cx = x(Date.parse(pass.acquired_at));
            const cy = y(Math.max(min, pass.max_frp_mw as number));
            const label = `${utc(pass.acquired_at)}, ${pass.group}: ${measurement(pass.max_frp_mw, "MW")} maximum from ${pass.detections} detection(s)`;
            return (
              <g
                key={pass.acquired_at + pass.group}
                tabIndex={0}
                role="button"
                aria-label={label}
                onPointerEnter={() => setActive(pass)}
                onPointerLeave={() => setActive(null)}
                onFocus={() => setActive(pass)}
                onBlur={() => setActive(null)}
                className="pass"
              >
                <circle cx={cx} cy={cy} r={12} fill="transparent" />
                <circle
                  cx={cx}
                  cy={cy}
                  r={4.5}
                  className={pass.daynight === "N" ? "mark night" : "mark day"}
                />
              </g>
            );
          })}
          <text x={4} y={M.top + 2} className="axis" textAnchor="start">
            MW
          </text>
        </svg>
        {active && active.max_frp_mw != null && (
          <div
            className="timeline-tip"
            role="status"
            style={{
              left: `${(x(Date.parse(active.acquired_at)) / W) * 100}%`,
              top: `${(y(Math.max(min, active.max_frp_mw)) / H) * 100}%`,
              // Keep the tooltip inside the chart near either edge.
              transform: `translate(${
                x(Date.parse(active.acquired_at)) > W * 0.7
                  ? "calc(-100% + 10px)"
                  : x(Date.parse(active.acquired_at)) < W * 0.3
                    ? "-10px"
                    : "-50%"
              }, calc(-100% - 12px))`,
            }}
          >
            <strong>{measurement(active.max_frp_mw, "MW")}</strong>
            <span>
              {utc(active.acquired_at)} · {active.group} · {active.detections}{" "}
              detection(s)
            </span>
          </div>
        )}
      </div>
      <figcaption className="help">
        Maximum fire radiative power per overpass within{" "}
        {data.radius_m.toLocaleString("en-GB")} m of this pixel, log scale.{" "}
        {unknownDays} of {data.days.length} days were not retrieved. {data.note}
      </figcaption>
      <details className="timeline-table">
        <summary>Show as table ({data.overpasses.length} overpasses)</summary>
        <table>
          <thead>
            <tr>
              <th>Acquired (UTC)</th>
              <th>Group</th>
              <th>Detections</th>
              <th>Max FRP</th>
            </tr>
          </thead>
          <tbody>
            {[...data.overpasses].reverse().map((pass) => (
              <tr key={pass.acquired_at + pass.group}>
                <td>{utc(pass.acquired_at)}</td>
                <td>{pass.group}</td>
                <td>{pass.detections}</td>
                <td>{measurement(pass.max_frp_mw, "MW")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </figure>
  );
}
