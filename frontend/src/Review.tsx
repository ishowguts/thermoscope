import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import {
  SOURCE_LABEL_TEXT,
  SUBTYPE_TEXT,
  confidence,
  distance,
  facilityType,
  landCoverMix,
  measurement,
  postReview,
  readApi,
  utc,
} from "./api";
import type {
  CaseSet,
  LabelSummary,
  QueueItem,
  ReviewCase,
  ReviewQueue,
} from "./api";

type Draft = {
  source_label: string;
  industrial_subtype: string;
  certainty: string;
  evidence: string;
  evidence_date: string;
  notes: string;
};

const EMPTY_DRAFT: Draft = {
  source_label: "",
  industrial_subtype: "",
  certainty: "",
  evidence: "",
  evidence_date: "",
  notes: "",
};

const SPLIT_TEXT: Record<string, string> = {
  TEST: "Test case · needs two independent reviews",
  VALIDATION: "Validation case · one review",
  TRAIN: "Training case · one review",
};

function day(value: string): string {
  return utc(value).replace(/,? \d\d:\d\d UTC$/, "");
}

function QueueRow({
  item,
  active,
  onOpen,
}: {
  item: QueueItem;
  active: boolean;
  onOpen: (id: string) => void;
}) {
  return (
    <button
      className={`observation-row ${active ? "active" : ""}`}
      aria-pressed={active}
      onClick={() => onOpen(item.case_id)}
    >
      <span className="row-top">
        <strong>{item.region_id}</strong>
        <span>
          {item.role === "ADJUDICATOR"
            ? "Adjudicate"
            : item.split.toLowerCase()}
        </span>
      </span>
      <span>{day(item.as_of)}</span>
      <span className="row-bottom">
        {item.reviews} of {item.needs} review{item.needs > 1 ? "s" : ""}{" "}
        <span>{item.case_id.slice(0, 8)}</span>
      </span>
    </button>
  );
}

function CaseEvidence({ data }: { data: ReviewCase }) {
  const land = data.land_cover;
  const frp = data.observations
    .map((o) => o.frp_mw)
    .filter((v): v is number => v != null);
  return (
    <div className="review-evidence">
      <div className="panel-heading">
        <h2>
          {data.region_id} · {day(data.started_at)}
          {day(data.started_at) !== day(data.as_of)
            ? ` – ${day(data.as_of)}`
            : ""}
        </h2>
        <span className="tag">{SPLIT_TEXT[data.split] ?? data.split}</span>
      </div>
      <div className="review-grid">
        <section>
          <h3>Where and when</h3>
          <dl>
            <dt>Location</dt>
            <dd>
              {data.location.latitude.toFixed(5)},{" "}
              {data.location.longitude.toFixed(5)}
            </dd>
            <dt>Approximate pixel radius</dt>
            <dd>{distance(data.location.support_radius_m)}</dd>
            <dt>Detections</dt>
            <dd>
              {data.observations.length} over{" "}
              {new Set(data.observations.map((o) => o.acquired_at)).size}{" "}
              overpass(es)
            </dd>
            <dt>Strongest FRP</dt>
            <dd>{measurement(frp.length ? Math.max(...frp) : null, "MW")}</dd>
          </dl>
          <h3>Look at the place yourself</h3>
          <ul className="link-list">
            {data.links.map((link) => (
              <li key={link.url}>
                <a href={link.url} target="_blank" rel="noreferrer">
                  {link.label} ↗
                </a>
              </li>
            ))}
          </ul>
          <p className="help">
            Copy the link you relied on into the evidence box. Imagery on the
            event date is the strongest evidence; a map label alone is weak.
          </p>
        </section>
        <section>
          <h3>Mapped features (OpenStreetMap)</h3>
          {data.osm_snapshot ? (
            data.mapped_features.length ? (
              <ul className="candidates">
                {data.mapped_features.slice(0, 8).map((c) => (
                  <li key={`${c.osm_type}/${c.osm_id}`}>
                    <span>
                      <strong>{facilityType(c.facility_type)}</strong>
                      {c.name ? ` · ${c.name}` : ""}
                    </span>
                    <span className="where">
                      {c.contains_pixel_centre
                        ? "Pixel centre inside"
                        : distance(c.distance_m)}
                    </span>
                    <small>
                      OSM {c.primary_tag} ·{" "}
                      <a href={c.osm_url} target="_blank" rel="noreferrer">
                        {c.osm_type}/{c.osm_id}
                      </a>
                    </small>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="help">No mapped industrial feature within 2 km.</p>
            )
          ) : (
            <p className="help">No OSM snapshot covers this place.</p>
          )}
          <h3>Registry records within 5 km</h3>
          {data.registry_records_within_5km.length ? (
            <ul className="candidates">
              {data.registry_records_within_5km.map((r) => (
                <li key={`${r.source}/${r.record_id}`}>
                  <span>
                    <strong>{r.name ?? r.record_id}</strong>
                    {r.fuel ? ` · ${r.fuel}` : ""}
                    {r.capacity_mw ? ` · ${Math.round(r.capacity_mw)} MW` : ""}
                  </span>
                  <span className="where">{distance(r.distance_m)}</span>
                  <small>{r.attribution}</small>
                </li>
              ))}
            </ul>
          ) : (
            <p className="help">
              None in the power-plant registry (WRI GPPD v1.3.0).
            </p>
          )}
          <h3>Land cover (ESA WorldCover 2021)</h3>
          <p className="land-mix">
            {land
              ? `Pixel area: ${landCoverMix(land.support)} · 1 km: ${landCoverMix(land.context)}`
              : "Not extracted for this detection."}
          </p>
        </section>
      </div>
      <details>
        <summary>All {data.observations.length} detections (UTC)</summary>
        <table className="detections">
          <thead>
            <tr>
              <th>Acquired</th>
              <th>FRP</th>
              <th>Day/night</th>
              <th>Confidence</th>
              <th>Lat, lon</th>
            </tr>
          </thead>
          <tbody>
            {data.observations.map((o) => (
              <tr key={o.id}>
                <td>{utc(o.acquired_at)}</td>
                <td>{measurement(o.frp_mw, "MW")}</td>
                <td>{o.daynight === "D" ? "Day" : "Night"}</td>
                <td>{confidence(o.confidence)}</td>
                <td>
                  {o.lat.toFixed(4)}, {o.lon.toFixed(4)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
      {data.adjudication && (
        <div className="notice" role="status">
          <strong>Two reviewers disagreed.</strong> As adjudicator, weigh their
          evidence and your own, then decide.
          <ul>
            {data.adjudication.earlier_reviews.map((r, i) => (
              <li key={i}>
                {SOURCE_LABEL_TEXT[r.source_label] ?? r.source_label} (
                {r.certainty.toLowerCase()} certainty)
                {r.evidence.map((url) => (
                  <span key={url}>
                    {" "}
                    ·{" "}
                    <a href={url} target="_blank" rel="noreferrer">
                      evidence ↗
                    </a>
                  </span>
                ))}
                {r.notes ? ` · “${r.notes}”` : ""}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function ReviewForm({
  data,
  reviewer,
  token,
  onToken,
  onSaved,
}: {
  data: ReviewCase;
  reviewer: string;
  token: string;
  onToken: (value: string) => void;
  onSaved: (message: string) => void;
}) {
  const [draft, setDraft] = useState<Draft>(EMPTY_DRAFT);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const set = (patch: Partial<Draft>) => setDraft({ ...draft, ...patch });
  const links = draft.evidence
    .split(/\s+/)
    .map((v) => v.trim())
    .filter(Boolean);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    if (!draft.source_label || !draft.certainty) {
      setError("Choose a source and a certainty.");
      return;
    }
    if (draft.source_label !== "UNRESOLVED" && links.length === 0) {
      setError("Add at least one evidence link, or choose “Cannot decide”.");
      return;
    }
    if (links.length > 5 || links.some((l) => !/^https?:\/\//.test(l))) {
      setError("Use up to five links starting with http:// or https://.");
      return;
    }
    setSaving(true);
    try {
      const saved = await postReview(data.case_set_id, token, {
        case_id: data.case_id,
        reviewer,
        source_label: draft.source_label,
        industrial_subtype:
          draft.source_label === "INDUSTRIAL" && draft.industrial_subtype
            ? draft.industrial_subtype
            : null,
        certainty: draft.certainty,
        evidence: links,
        evidence_date: draft.evidence_date || null,
        notes: draft.notes.trim() || null,
      });
      setDraft(EMPTY_DRAFT);
      onSaved(
        saved.role === "ADJUDICATOR"
          ? "Adjudication saved."
          : "Review saved. The next case is open.",
      );
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="review-form" onSubmit={submit}>
      <h3>Your decision</h3>
      <fieldset>
        <legend>Most likely heat source</legend>
        {data.labels.map((label) => (
          <label key={label} className="choice">
            <input
              type="radio"
              name="source"
              value={label}
              checked={draft.source_label === label}
              onChange={() => set({ source_label: label })}
            />
            {SOURCE_LABEL_TEXT[label] ?? label}
          </label>
        ))}
      </fieldset>
      {draft.source_label === "INDUSTRIAL" && (
        <label>
          Industrial type (optional)
          <select
            value={draft.industrial_subtype}
            onChange={(e) => set({ industrial_subtype: e.target.value })}
          >
            <option value="">Not specified</option>
            {data.subtypes.map((s) => (
              <option key={s} value={s}>
                {SUBTYPE_TEXT[s] ?? s}
              </option>
            ))}
          </select>
        </label>
      )}
      <fieldset>
        <legend>Certainty</legend>
        {["HIGH", "MEDIUM", "LOW"].map((level) => (
          <label key={level} className="choice inline">
            <input
              type="radio"
              name="certainty"
              value={level}
              checked={draft.certainty === level}
              onChange={() => set({ certainty: level })}
            />
            {level.charAt(0) + level.slice(1).toLowerCase()}
          </label>
        ))}
      </fieldset>
      <label>
        Evidence links (one per line, up to five)
        <textarea
          rows={3}
          value={draft.evidence}
          onChange={(e) => set({ evidence: e.target.value })}
          placeholder="https://worldview.earthdata.nasa.gov/…"
        />
      </label>
      <label>
        Date of the imagery or source you used (optional)
        <input
          type="date"
          value={draft.evidence_date}
          onChange={(e) => set({ evidence_date: e.target.value })}
        />
      </label>
      <label>
        Notes (optional)
        <textarea
          rows={2}
          maxLength={2000}
          value={draft.notes}
          onChange={(e) => set({ notes: e.target.value })}
        />
      </label>
      <label>
        Review token
        <input
          type="password"
          autoComplete="off"
          value={token}
          onChange={(e) => onToken(e.target.value)}
          placeholder="Ask the team lead"
        />
      </label>
      {error && (
        <div className="notice error" role="alert">
          {error}
        </div>
      )}
      <button className="primary" disabled={saving || !token}>
        {saving ? "Saving…" : "Save review"}
      </button>
      <p className="help">
        Reviews are append-only. Save only what the evidence supports.
      </p>
    </form>
  );
}

export function ReviewPage() {
  const [sets, setSets] = useState<CaseSet[] | null>(null);
  const [enabled, setEnabled] = useState(false);
  const [setName, setSetName] = useState("");
  const [nameInput, setNameInput] = useState("");
  const [reviewer, setReviewer] = useState("");
  const [token, setToken] = useState("");
  const [queue, setQueue] = useState<ReviewQueue | null>(null);
  const [summary, setSummary] = useState<LabelSummary | null>(null);
  const [caseId, setCaseId] = useState<string | null>(null);
  const [data, setData] = useState<ReviewCase | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    readApi<{ case_sets: CaseSet[]; review_enabled: boolean }>(
      "/api/v1/annotation/case-sets",
      controller.signal,
    )
      .then((result) => {
        setSets(result.case_sets);
        setEnabled(result.review_enabled);
        if (result.case_sets.length) setSetName(result.case_sets[0].name);
      })
      .catch(() => {
        if (!controller.signal.aborted)
          setError("Case sets could not be loaded.");
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!setName || !reviewer) return;
    const controller = new AbortController();
    const base = `/api/v1/annotation/${encodeURIComponent(setName)}`;
    Promise.all([
      readApi<ReviewQueue>(
        `${base}/queue?reviewer=${encodeURIComponent(reviewer)}&limit=30`,
        controller.signal,
      ),
      readApi<LabelSummary>(`${base}/summary`, controller.signal),
    ])
      .then(([q, s]) => {
        setQueue(q);
        setSummary(s);
        const first = q.adjudication[0] ?? q.review[0];
        setCaseId(first ? first.case_id : null);
      })
      .catch(() => {
        if (!controller.signal.aborted)
          setError("The review queue could not be loaded.");
      });
    return () => controller.abort();
  }, [setName, reviewer, tick]);

  useEffect(() => {
    setData(null);
    if (!caseId || !setName) return;
    const controller = new AbortController();
    readApi<ReviewCase>(
      `/api/v1/annotation/${encodeURIComponent(setName)}/cases/${caseId}`,
      controller.signal,
    )
      .then(setData)
      .catch(() => {
        if (!controller.signal.aborted)
          setError("This case could not be loaded.");
      });
    return () => controller.abort();
  }, [caseId, setName]);

  const saved = useCallback((text: string) => {
    setMessage(text);
    setTick((v) => v + 1);
  }, []);

  const gold = summary?.gold_test_labels ?? {};
  const industrial = gold.INDUSTRIAL ?? 0;
  const other =
    (gold.VEGETATION_FIRE ?? 0) +
    (gold.AGRICULTURAL_BURN ?? 0) +
    (gold.OTHER ?? 0);

  return (
    <>
      <header>
        <span>BLIND LABEL REVIEW</span>
        <span className="tag">Human evidence only</span>
      </header>
      <section className="intro">
        <div>
          <div className="eyebrow">P05 · Reviewed labels</div>
          <h1>What caused this heat?</h1>
          <p>
            Decide from imagery and records. Rules and model scores stay hidden
            so they cannot sway you.
          </p>
        </div>
      </section>
      {error && (
        <div className="notice error" role="alert">
          {error}
        </div>
      )}
      {sets && !enabled && (
        <div className="notice" role="status">
          Saving reviews is switched off on this server. Set ANNOTATION_TOKEN in
          the server’s .env to enable it. You can still browse cases.
        </div>
      )}
      {!reviewer ? (
        <form
          className="filters"
          onSubmit={(e) => {
            e.preventDefault();
            const name = nameInput.trim();
            if (/^[\w .'-]{2,60}$/.test(name)) setReviewer(name);
            else setError("Use 2–60 letters, digits, spaces, . ' or -.");
          }}
        >
          <label>
            Case set
            <select
              value={setName}
              onChange={(e) => setSetName(e.target.value)}
              disabled={!sets?.length}
            >
              {sets?.map((s) => (
                <option key={s.id} value={s.name}>
                  {s.name} · {s.case_count.toLocaleString("en-GB")} cases
                </option>
              )) ?? <option>Loading…</option>}
            </select>
          </label>
          <label>
            Your name
            <input
              value={nameInput}
              onChange={(e) => setNameInput(e.target.value)}
              placeholder="e.g. Priya S"
              maxLength={60}
            />
          </label>
          <button className="primary" disabled={!setName}>
            Start reviewing
          </button>
          <span className="filter-hint">
            Your name is stored with each review
          </span>
        </form>
      ) : (
        <>
          <section className="metrics" aria-label="Label progress">
            <div>
              <span>Reviewed test labels (industrial / not)</span>
              <strong>
                {industrial} / {other}
              </strong>
              <small>10 of each to report results, 30 to promote a model</small>
            </div>
            <div>
              <span>Reviews saved · awaiting adjudication</span>
              <strong>
                {summary?.reviews_total ?? "—"} ·{" "}
                {summary?.pending_adjudication ?? "—"}
              </strong>
              <small>Across all reviewers</small>
            </div>
            <div>
              <span>Reviewer agreement (industrial vs not)</span>
              <strong>
                {summary?.binary_agreement_kappa == null
                  ? "—"
                  : summary.binary_agreement_kappa.toFixed(2)}
              </strong>
              <small>
                Cohen’s kappa over {summary?.double_reviewed_cases ?? 0}{" "}
                double-reviewed case(s)
              </small>
            </div>
          </section>
          {message && (
            <div className="notice" role="status">
              {message}
            </div>
          )}
          <section className="review-workspace" aria-label="Review workbench">
            <div className="list-panel">
              <div className="panel-heading">
                <h2>Queue for {reviewer}</h2>
                <button className="quiet" onClick={() => setReviewer("")}>
                  Switch
                </button>
              </div>
              <div className="observations">
                {queue?.adjudication.map((item) => (
                  <QueueRow
                    key={item.case_id}
                    item={item}
                    active={item.case_id === caseId}
                    onOpen={setCaseId}
                  />
                ))}
                {queue?.review.map((item) => (
                  <QueueRow
                    key={item.case_id}
                    item={item}
                    active={item.case_id === caseId}
                    onOpen={setCaseId}
                  />
                ))}
                {queue &&
                  !queue.review.length &&
                  !queue.adjudication.length && (
                    <p className="empty-list">Nothing left for you here.</p>
                  )}
              </div>
              <p className="help queue-note">
                {queue
                  ? `${queue.remaining_reviews.toLocaleString("en-GB")} cases open for review · ${queue.remaining_adjudications} awaiting adjudication. Test cases need two people.`
                  : "Loading queue…"}
              </p>
            </div>
            <div className="map-panel">
              {data ? (
                <CaseEvidence data={data} />
              ) : (
                <div className="map-placeholder">
                  {caseId ? "Loading case…" : "Choose a case from the queue."}
                </div>
              )}
            </div>
            {data && (
              <div className="list-panel form-panel">
                <ReviewForm
                  key={data.case_id}
                  data={data}
                  reviewer={reviewer}
                  token={token}
                  onToken={setToken}
                  onSaved={saved}
                />
              </div>
            )}
          </section>
          <footer>
            <p>{data?.guidance}</p>
            <span>ThermoScope · Git_Push_Pray</span>
          </footer>
        </>
      )}
    </>
  );
}
