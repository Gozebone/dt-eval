"""Render a comparison run directory into report.md (pure stdlib).

Usage: python report.py <runs/<timestamp>>
"""
from __future__ import annotations

import json
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CASES_ROOT = ROOT / "cases"

# Method C's rep status is derived from its stages (protocol.md §5), and the
# rule lives in `adapters.base` so this renderer applies the same one the
# adapter applied rather than a copy that can drift. `base` is stdlib-only.
sys.path.insert(0, str(ROOT))
import adapters.base as B  # noqa: E402

HEADLINE = ["throughput_per_hour", "wip_parts", "energy_per_part_kwh"]
LABELS = {
    "throughput_per_hour": "Throughput (parts/h)",
    "wip_parts": "WIP (parts)",
    "energy_per_part_kwh": "Energy per part (kWh)",
}


def _truth(case_dir: Path) -> dict:
    # ground truth lives in cases/<case>/truth_kpis.json, not inside the run dir
    return json.loads((CASES_ROOT / case_dir.name / "truth_kpis.json")
                      .read_text(encoding="utf-8"))


def _load_results(case_dir: Path, methods):
    out = {}
    for method in methods:
        mdir = case_dir / method
        if not mdir.is_dir():
            continue
        for rep in sorted(mdir.iterdir(), key=lambda p: p.name):
            rj = rep / "result.json"
            if rj.exists():
                out.setdefault(method, []).append(
                    json.loads(rj.read_text(encoding="utf-8")))
    return out


def _native_index(run_dir: Path) -> dict:
    """`(case, method, rep) -> native block`, read from each rep's `result.json`.

    `summary.json` carries only the status, so a rep whose status is to be
    re-derived has to be read from the run's own artefact.
    """
    idx = {}
    for rj in run_dir.glob("*/[ABC]/rep*/result.json"):
        try:
            r = json.loads(rj.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        nat = (r.get("kpis") or {}).get("native")
        idx[(r.get("case"), r.get("method"), r.get("rep"))] = nat or {}
    return idx


def _display_status(recorded, nat):
    """`(displayed, note)`: C's status re-derived from its stored stage evidence.

    C's status is a *derivation* from its stages (protocol.md §5, decided
    2026-09-20), so a rep recorded before that decision as `ok` while its DES
    model crashed is displayed as `simulation_error` — otherwise the validity
    table counts a method failure as a success. A/B rows and C rows whose stage
    evidence cannot settle the verdict are shown as recorded, with a note.
    """
    if not isinstance(nat, dict) or "machines_truth" not in nat:
        return recorded, None
    if recorded != "ok" or nat.get("des_stage") == "not_attempted":
        # not `ok`, or a mock run, where no stage ran and there is no verdict
        # to derive — nothing to say
        return recorded, None
    status, basis = B.status_from_native(nat)
    if status == "unknown":
        return recorded, f"recorded as `{recorded}`; {basis}"
    return status, None


def _median(vals):
    vals = [v for v in vals if v is not None]
    return statistics.median(vals) if vals else None


def _mape(pred, truth):
    if pred is None or truth in (None, 0):
        return None
    return abs(pred - truth) / abs(truth)


def _util_ape(kpis, truth_util):
    u = kpis.get("utilization")
    if not u or not truth_util:
        return None, None
    errs = []
    matched = []
    for mid, t in truth_util.items():
        if isinstance(t, dict):          # truth_kpis.json stores {mean, std}
            t = t.get("mean")
        if mid in u and u[mid] is not None and t not in (None, 0):
            errs.append(abs(u[mid] - t) / abs(t))
            matched.append(mid)
    if not errs:
        return None, len(truth_util)
    return statistics.mean(errs), len(matched)


# ---- per-rep structural cells (method C) --------------------------------- #
# C's stage outcomes are per-rep facts: one rep's DB agent answers while
# another's times out, so every cell below is read from a single rep's own
# native block and never summarised across reps.
def _timeout(note: str, key: str | None = None) -> str | None:
    m = re.search((rf"{key}: poll timeout after ([\d.]+)s" if key
                   else r"poll timeout after ([\d.]+)s"), note or "")
    if not m:
        return None
    return f"timeout {m.group(1).rstrip('0').rstrip('.')}s"


def _status_cell(status, nat: dict) -> str:
    if status != "ok":
        return str(status)
    sub, ans = nat.get("agent_tasks_attempted"), nat.get("agent_tasks")
    if sub and ans is not None and sub != ans:
        return f"ok ({sub} sub / {ans} ans)"
    return "ok"


def _db_facts(nat: dict) -> list:
    """The facts a run of this version records about agent 1's reply.

    Empty for a run stored before 2026-09-21: it carries neither the schema's own
    counts nor the reply/repair counts, and must keep rendering as it always did.
    """
    facts = []
    summ = nat.get("db_sql_summary") or {}
    if summ.get("tables"):
        facts.append(f"{summ['tables']} table{'' if summ['tables'] == 1 else 's'}")
        if summ.get("views"):
            facts.append(f"{summ['views']} view{'' if summ['views'] == 1 else 's'}")
    programs, repairs = nat.get("db_programs"), nat.get("db_repairs_used")
    if isinstance(programs, int) and programs > 1:
        n = repairs if isinstance(repairs, int) else programs - 1
        facts.append(f"{programs} replies, {n} repair{'' if n == 1 else 's'}")
    return facts


def _db_cell(nat: dict) -> str:
    """What agent 1 actually returned, and since 2026-09-21 whether it is a
    schema — `db_stage` now carries that verdict instead of only answer receipt.

    A reply that arrived but does not read as SQL renders as `answered Nc` with
    the rule it broke, which is what the cell could not say before: `db_stage`
    read `ok` for any reply at all, and the only evidence here was a
    DDL-phrase test. The reply and repair counts are shown for the same reason
    as the DES cell's program counts — they say whether the loop stopped on a
    reply that reads as SQL or ran out of attempts. A run stored before this
    change carries none of those keys and renders exactly as it always did,
    including the `(recorded Nc, no DDL)` marker for a reply whose recorded
    artefact was `_get_json`'s fragment rather than the reply itself.
    """
    if not nat:
        return "—"
    shp = nat.get("stage_shapes") or {}
    ans, rec = shp.get("db_answer") or {}, shp.get("db_recorded") or {}
    stage, note = nat.get("db_stage"), nat.get("db_note") or ""
    if stage == "not_attempted":
        return "not attempted"
    if ans.get("chars"):
        parts = [f"answered {ans['chars']}c"]
        if ans.get("looks_like_ddl"):
            parts.append("DDL")
        elif stage == "invalid_sql":
            parts.append("not a schema")
        cell = " / ".join(parts)
        facts = _db_facts(nat)
        if facts:
            cell += f" ({', '.join(facts)})"
        if ans.get("looks_like_ddl") and rec.get("chars") and not rec.get("looks_like_ddl"):
            # `_get_json` brace-scanned the reply and recorded a fragment of it
            # as the schema artefact; the agent's own answer is upstream.
            cell += f" (recorded {rec['chars']}c, no DDL)"
        if stage == "unavailable":
            # the reply was not JSON, so `db_stage` is `unavailable` even though
            # the agent did answer: the status tracks parseability, not receipt
            cell += " (not JSON → stage unavailable)"
        if stage == "invalid_sql" and nat.get("db_gave_up_reason"):
            cell += f"; rejected: {_rejection_marker(nat['db_gave_up_reason'])}"
        return cell
    if (t := _timeout(note)):
        return t
    # Runs recorded before stage_shapes existed carry no answer size; say so
    # rather than render them as an empty answer.
    if stage == "unavailable":
        return "answered, not JSON" if "not JSON" in note else "no answer"
    return "answered (chars unrecorded)"


def _dt_cell(nat: dict, key: str) -> str:
    if not nat:
        return "—"
    if nat.get("dt_stage") == "not_attempted":
        return "not attempted"
    s = (nat.get("stage_shapes") or {}).get(f"dt_{key}") or {}
    if s.get("chars"):
        cell = f"{s['chars']}c / {s.get('ids_present')} ids"
        if s.get("looks_like_json") is False:
            cell += " / not JSON"
        return cell
    if (t := _timeout(nat.get("dt_note") or "", key)):
        return t
    # legacy native blocks (pre-stage_shapes) record the slot size but not the
    # case ids found in it
    if (legacy := (nat.get("artifact_chars") or {}).get(key)):
        return f"{legacy}c (ids unrecorded)"
    return "no output"


# Every reason the gate returns opens with this clause, because it is written
# for the *model* as a repair message. A report cell wants the rule that was
# violated, so the shared preamble is dropped before the clause is shown.
_GATE_PREAMBLE = "the program ran and printed the three contract lines, but "


# Wider than the other cells' prose because it is a quotation from C's own gate
# rather than a summary of it: shortening it further would mean paraphrasing the
# rule here, which is the drift this renderer deliberately avoids everywhere else.
_REJECTION_CHARS = 140


def _rejection_marker(reason) -> str:
    """The violated rule alone, bounded to fit a table cell."""
    text = str(reason).split("\n", 1)[0].strip()
    if text.startswith(_GATE_PREAMBLE):
        text = text[len(_GATE_PREAMBLE):]
    text = text.split(". ", 1)[0].rstrip(".")
    if len(text) <= _REJECTION_CHARS:
        return text
    # cut on a word boundary so the quoted clause stays readable
    return text[:_REJECTION_CHARS].rsplit(" ", 1)[0] + "…"


def _des_cell(nat: dict) -> str:
    """What *executing* the DES slot did, which the text cell cannot show.

    `_dt_cell(nat, "des")` says whether code arrived; this says whether C can be
    measured — the distinction the DES stage exists to make. Kept per rep for the
    same reason as every other cell here: one rep's model runs and another fails
    to import, and those two must not be averaged into "the DES works".

    A program the semantic gate rejects still exits 0 on a run that printed the
    contract, so it lands on `des_stage: ok` and the rep's status stays `ok`
    (protocol.md §5 — status semantics do not change mid-study). Its KPIs are
    then a printed number, not an accepted measurement, and
    `native.des_gave_up_reason` is the only field that says so; without it here
    the report would render that rep exactly like a clean one. The program and
    repair counts are shown for the same reason the protocol names them: they
    say whether the loop stopped on an accepted program or ran out of attempts.
    """
    if not nat:
        return "—"
    stage = nat.get("des_stage")
    if stage is None:
        return "—"
    if stage == "not_attempted":
        return "not attempted"
    if stage == "unavailable":
        return "no model"
    if stage == "ran_no_contract":
        return "ran, no contract"
    if stage in ("timeout", "simulation_error", "error"):
        return stage
    k = nat.get("des_kpis") or {}
    got = sum(1 for v in (k.get("throughput_per_hour"), k.get("wip_parts"),
                          k.get("energy_per_part_kwh")) if v is not None)
    cell = f"ok, {got}/3 KPIs" if got else "ok, no KPIs"
    programs, repairs = nat.get("des_programs"), nat.get("des_repairs_used")
    if isinstance(programs, int) and programs > 1:
        n_repairs = repairs if isinstance(repairs, int) else programs - 1
        cell += f" ({programs} programs, {n_repairs} repair{'' if n_repairs == 1 else 's'})"
    reason = nat.get("des_gave_up_reason")
    if reason:
        cell += f"; gate rejected: {_rejection_marker(reason)}"
    return cell


def _values_cell(nat: dict) -> str:
    if not nat or ("machine_stats" not in nat and not nat.get("buffers")):
        return "—"
    ms = nat.get("machine_stats") or {}
    n = nat.get("machines_truth") or len(ms)
    t = sum(1 for v in ms.values() if v.get("process_time_found"))
    a = sum(1 for v in ms.values() if v.get("availability_found"))
    bufs = nat.get("buffers") or {}
    parts = [f"time {t}/{n}", f"avail {a}/{n}"]
    if bufs:
        parts.append(f"bufs {sum(1 for v in bufs.values() if v)}/{len(bufs)}")
    parts.append(f"arrival {'found' if nat.get('arrival_found') else 'missing'}")
    # What C stated where it did not recover the truth. Without this the counts
    # above cannot be told apart from an invented number, which is how a whole
    # run of fabricated parameters read as full recovery.
    bad = [f"{mid} t={v['process_time_claimed']:g}" for mid, v in sorted(ms.items())
           if v.get("process_time_claimed") is not None and not v.get("process_time_found")]
    bad += [f"{mid} a={v['availability_claimed']:g}" for mid, v in sorted(ms.items())
            if v.get("availability_claimed") is not None and not v.get("availability_found")]
    if nat.get("arrival_claimed") is not None and not nat.get("arrival_found"):
        bad.append(f"arrival={nat['arrival_claimed']:g}")
    if bad:
        parts.append("claimed: " + ", ".join(bad))
    if "arrival_claimed" not in nat:
        # A native block written before the recovery check was corrected: its
        # process-time/availability counts came from searching the artefact for
        # the bare digit, which credits C for numbers it invented, so they are
        # not comparable with a current rep's. Say so rather than print them
        # as if they were.
        parts.append("(pre-2026-09-20 recovery metric — counts not comparable)")
    return ", ".join(parts)


def render(run_dir: Path) -> str:
    summary_path = run_dir / "summary.json"
    summary = (json.loads(summary_path.read_text(encoding="utf-8"))
               if summary_path.exists() else [])
    methods = sorted({r.get("method") for r in summary} - {None})
    if not methods:
        methods = ["A", "B", "C"]
    case_dirs = sorted(p for p in run_dir.iterdir()
                       if p.is_dir() and (CASES_ROOT / p.name / "truth_kpis.json").exists())
    lines = []
    lines.append(f"# Comparison report — `{run_dir.name}`")
    meta_p = run_dir / "environment.json"
    if meta_p.exists():
        meta = json.loads(meta_p.read_text(encoding="utf-8"))
        lines.append(f"- mode: {meta.get('mode')} | methods: {meta.get('methods')} "
                     f"| repetitions: {meta.get('repetitions')}")
    lines.append("")

    # ---- validity table ------------------------------------------------ #
    lines.append("## Validity")
    lines.append("")
    # Columns are derived from the statuses actually present, in this canonical
    # order. A fixed column list would silently hide any status it does not
    # name, and the statuses it would hide are precisely the ones that are not
    # the method's fault: `service_unavailable` (the remote host never answered)
    # and the orchestrator's `adapter_timeout`/`adapter_error`.
    status_order = ["ok", "service_unavailable", "generation_error",
                    "simulation_error", "timeout", "parse_error"]
    nat_idx = _native_index(run_dir)
    shown, notes = {}, []
    for r in summary:
        key = (r.get("case"), r.get("method"), r.get("rep"))
        disp, note = _display_status(r.get("status", "?"), nat_idx.get(key))
        shown[id(r)] = disp
        if note:
            notes.append(f"{r.get('case')}/{r.get('method')}/rep{r.get('rep')}: {note}")
    present = {r.get("status", "?") for r in summary}
    present |= set(shown.values())
    cols = ([s for s in status_order if s in present]
            + sorted(present - set(status_order)))
    lines.append("| Method | " + " | ".join(cols) + " | total |")
    lines.append("|---|" + "---|" * len(cols) + "---|")
    for m in methods:
        rows = [r for r in summary if r.get("method") == m]
        if not rows:
            continue
        counts = {}
        for r in rows:
            s = shown[id(r)]
            counts[s] = counts.get(s, 0) + 1
        cells = " | ".join(str(counts.get(c, 0)) for c in cols)
        lines.append(f"| {m} | {cells} | {len(rows)} |")
    if any(shown[id(r)] != r.get("status", "?") for r in summary):
        lines.append("")
        lines.append("_C's status is derived from its stages (protocol.md §5); "
                     "reps whose recorded `ok` predates that derivation are "
                     "counted under the stage outcome. The per-rep tables below "
                     "give the stage each verdict came from._")
    for n in notes:
        lines.append(f"- {n}")
    lines.append("")

    # ---- per-case tables ---------------------------------------------- #
    case_summaries = []
    for case_dir in case_dirs:
        truth = _truth(case_dir)
        results = _load_results(case_dir, methods)
        lines.append(f"## Case {case_dir.name}")
        lines.append("")
        t = truth.get("throughput_per_hour", {}).get("mean")
        w = truth.get("wip_parts", {}).get("mean")
        e = truth.get("energy_per_part_kwh", {}).get("mean")
        lines.append(
            f"Truth: throughput={t} parts/h, WIP={w} parts, "
            f"energy={e} kWh/part "
            f"(std: {truth.get('throughput_per_hour', {}).get('std')}/"
            f"{truth.get('wip_parts', {}).get('std')}/"
            f"{truth.get('energy_per_part_kwh', {}).get('std')})")
        lines.append("")
        if not any(results.values()):
            lines.append("_no results_")
            lines.append("")
            continue
        # headline indicators
        lines.append("### Headline indicators vs truth")
        lines.append("")
        lines.append("| Method | rep | status | " + " | ".join(LABELS[k]
                     for k in HEADLINE) + " |")
        lines.append("|---|--|--|" + "---|" * len(HEADLINE))
        row = {}
        for m in methods:
            for r in results.get(m, []):
                k = r.get("kpis", {})
                cells = []
                for h in HEADLINE:
                    v = k.get(h)
                    tv = {"throughput_per_hour": t, "wip_parts": w,
                          "energy_per_part_kwh": e}[h]
                    if v is None:
                        cells.append("—")
                    elif tv is not None:
                        mape = _mape(v, tv)
                        cells.append(f"{v:.4g} ({mape * 100:.1f}% err)"
                                     if mape is not None else f"{v:.4g}")
                    else:
                        cells.append(f"{v:.4g}")
                disp, _ = _display_status(
                    r.get("status"), (r.get("kpis") or {}).get("native"))
                lines.append(f"| {m} | {r.get('rep')} | {disp} "
                             f"| {' | '.join(cells)} |")
                errs = []
                for h in HEADLINE:
                    v = k.get(h)
                    tv = {"throughput_per_hour": t, "wip_parts": w,
                          "energy_per_part_kwh": e}[h]
                    mape = _mape(v, tv)
                    if mape is not None:
                        errs.append(mape)
                if errs:
                    row.setdefault(m, []).append(statistics.mean(errs))
        lines.append("")
        # utilization (method A native) + structural
        for m in methods:
            reps = results.get(m, [])
            aps = []
            recovered_n = None
            struct_reps = []
            for r in reps:
                k = r.get("kpis", {})
                nat = k.get("native") or {}
                # Structural-recovery stats are method C's: they carry
                # "machines_truth"/"buffers" and describe what C's stages said,
                # not what a simulation ran. Runtime stats (method A) do not.
                # Detect C by its own keys, never by machine_stats being
                # non-empty: an empty machine_stats is precisely the run whose
                # stage evidence most needs rendering.
                if "machines_truth" in nat and "buffers" in nat:
                    struct_reps.append((r, nat))
                    continue
                if r.get("status") != "ok":
                    continue
                ape, matched = _util_ape(k, truth.get("utilization"))
                if ape is not None:
                    aps.append((ape, matched))
                ms = nat.get("machine_stats")
                if isinstance(ms, dict) and recovered_n is None:
                    recovered_n = len(ms)
            if aps:
                mean_ape = statistics.mean(a for a, _ in aps)
                matched = max(x for _, x in aps)
                lines.append(f"- **{m}** utilisation APE "
                             f"(mean over ok reps, {matched}/{len(truth.get('utilization', {}))}"
                             f" machines matched): `{mean_ape * 100:.1f}%`")
            if recovered_n is not None:
                truth_n = len(truth.get("utilization", {}))
                lines.append(f"- **{m}** recovered machine count: "
                             f"{recovered_n}/{truth_n}")
            if struct_reps:
                # One row per rep, never a line aggregated across reps: C's
                # stages are stochastic, so a rep where every stage answered and
                # a rep where two timed out must stay distinguishable. A rep that
                # never reached the stages (generation_error) still gets a row.
                lines.append(f"### {m} structure per rep")
                lines.append("")
                lines.append("| rep | status | turns | DB (agent 1) | DT config "
                             "| DT script | DES run | ids named | values recovered |")
                lines.append("|---|---|---|---|---|---|---|---|---|")
                for r in reps:
                    nat = r.get("kpis", {}).get("native") or {}
                    rec = r.get("status")
                    disp, _ = _display_status(rec, nat)
                    # keep the recorded status visible when the derivation
                    # supersedes it: the table should not silently disagree with
                    # the run's own result.json
                    st_cell = (f"{_status_cell(disp, nat)} (recorded `{rec}`)"
                               if disp != rec else _status_cell(disp, nat))
                    lines.append(
                        f"| {r.get('rep')} | {st_cell} "
                        f"| {nat.get('interview_turns', '—')} | {_db_cell(nat)} "
                        f"| {_dt_cell(nat, 'config')} | {_dt_cell(nat, 'sim')} "
                        f"| {_des_cell(nat)} "
                        f"| {nat.get('machines_mentioned', '—')}/"
                        f"{nat.get('machines_truth', '—')} | {_values_cell(nat)} |")
                lines.append("")
                for r in reps:
                    if r.get("status") != "ok":
                        lines.append(f"- **{m}** rep{r.get('rep')}: "
                                     f"{str(r.get('error') or '')[:300]}")
                lines.append("")
            for r in reps:
                ns = r.get("notes") or []
                if ns:
                    lines.append(f"- **{m}** rep{r.get('rep')} notes: "
                                 + " | ".join(ns))
        lines.append("")
        # mean headline error per method for the aggregation across cases
        cs = {}
        for m, errs in row.items():
            cs[m] = statistics.median(errs)
        case_summaries.append((case_dir.name, cs))
        if not row:
            lines.append("_no comparable KPIs_")
            lines.append("")

    # ---- aggregation across cases ------------------------------------- #
    if len(case_summaries) > 1:
        lines.append("## Aggregated headline error (median MAPE over cases)")
        lines.append("")
        lines.append("| Method | median MAPE (throughput/WIP/energy) |")
        lines.append("|---|---|")
        for m in methods:
            per = []
            for _, cs in case_summaries:
                if m in cs:
                    per.append(cs[m])
            if per:
                lines.append(f"| {m} | {statistics.median(per) * 100:.1f}% "
                             f"(n={len(per)} cases) |")
        lines.append("")
        lines.append("_Paired non-parametric tests (Friedman/Wilcoxon) apply "
                     "once >=5 cases exist; skipped here._")
    return "\n".join(lines)


def main(argv) -> int:
    if len(argv) < 1:
        print("usage: python report.py <runs/<timestamp>>")
        return 2
    run_dir = Path(argv[0])
    md = render(run_dir)
    out = run_dir / "report.md"
    out.write_text(md, encoding="utf-8")
    print(md)
    print(f"\n[report] written to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
