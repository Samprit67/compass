"""``compass`` command line.

compass quiz                      # take the questionnaire, get ranked majors
compass score answers.json        # score a saved answer file
compass major "Computer Science"   # one major's full profile
compass compare "Computer Science" "Economics"
compass serve                     # run the web dashboard
compass data info | refresh
compass version
"""

from __future__ import annotations

import functools
import json
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from compass import __version__
from compass.config import settings_from_env
from compass.data.loader import load_profiles, load_questionnaire, profiles_meta
from compass.data.schema import RIASEC, RIASEC_LETTER, Answers
from compass.errors import CompassError
from compass.model.pipeline import compare as compare_majors
from compass.model.pipeline import evaluate

app = typer.Typer(add_completion=False, help=__doc__, no_args_is_help=True)
data_app = typer.Typer(help="Inspect or rebuild the bundled data.")
app.add_typer(data_app, name="data")
console = Console()


def _friendly(fn):
    """Turn an expected CompassError into a clean message + exit code 1,
    whichever way the command was invoked."""

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except CompassError as exc:
            console.print(f"[red]error:[/] {exc}")
            raise typer.Exit(1) from exc

    return wrapper


def _riasec_bar(values: tuple[float, ...], scale: float = 7.0) -> str:
    blocks = "▁▂▃▄▅▆▇█"
    out = []
    for name, v in zip(RIASEC, values, strict=True):
        frac = max(0.0, min(1.0, v / scale))
        out.append(f"{RIASEC_LETTER[name]}{blocks[round(frac * (len(blocks) - 1))]}")
    return " ".join(out)


@app.command()
def version() -> None:
    """Print the version."""
    typer.echo(f"compass {__version__}")


@app.command()
@_friendly
def quiz(
    limit: int = typer.Option(30, help="How many of the 60 activities to ask (5 per interest at 30)."),
    top: int = typer.Option(10, help="How many majors to show."),
) -> None:
    """Take the O*NET Interest Profiler in the terminal."""
    q = load_questionnaire()
    console.print(
        Panel.fit(
            "For each activity, how much would you like doing it?\n"
            "[bold]1[/] strongly dislike   [bold]2[/] dislike   [bold]3[/] not sure   "
            "[bold]4[/] like   [bold]5[/] strongly like\n"
            "Press Enter for 'not sure'. Type [bold]x[/] to stop early.",
            title=q.title,
        )
    )
    answers: dict[str, int] = {}
    items = list(q.questions)[: max(1, limit)]
    for i, item in enumerate(items, 1):
        raw = console.input(f"[dim]{i:>2}/{len(items)}[/] {item.text}  ").strip().lower()
        if raw == "x":
            break
        if raw == "":
            answers[item.id] = 2
            continue
        if raw in {"1", "2", "3", "4", "5"}:
            answers[item.id] = int(raw) - 1
        else:
            console.print("  [yellow]not a 1-5, counting as 'not sure'[/]")
            answers[item.id] = 2

    _render_results(Answers.from_payload(answers), top)


@app.command()
@_friendly
def score(
    answers_file: Path = typer.Argument(..., help='JSON: {"answers": {"r1": 4, ...}, "dealbreakers": []}'),
    top: int = typer.Option(10),
    as_json: bool = typer.Option(False, "--json", help="Emit the full result as JSON."),
) -> None:
    """Score a saved answer file."""
    payload = json.loads(answers_file.read_text())
    answers = Answers.from_payload(payload.get("answers", {}), payload.get("dealbreakers", []))
    if as_json:
        from compass.api import present

        rec = evaluate(answers, explain_top=top)
        typer.echo(json.dumps(present.recommendation_dict(rec, top=top), indent=2))
        return
    _render_results(answers, top)


@app.command()
@_friendly
def major(name: str) -> None:
    """Show one major's interest profile and the careers it maps to."""
    m = _find_major(name)
    console.print(Panel.fit(f"[bold]{m.name}[/]  [dim]{m.category}[/]\n{m.blurb}", title=m.slug))
    console.print(f"Interest profile [{m.high_point_code}]   {_riasec_bar(m.riasec.as_tuple)}")
    console.print(f"Typical preparation: Job Zone {m.job_zone:.1f} of 5")
    if m.example_careers:
        console.print("\n[bold]Where it leads[/]")
        for c in m.example_careers:
            console.print(f"  - {c}")
    if m.top_knowledge:
        console.print("\n[bold]Knowledge it draws on[/]  " + ", ".join(m.top_knowledge))
    if m.n_occupations < 3:
        console.print(
            f"\n[yellow]Note: built from only {m.n_occupations} occupation(s); "
            "treat the profile loosely.[/]"
        )


@app.command()
@_friendly
def compare(names: list[str]) -> None:
    """Compare majors against a neutral profile (no quiz)."""
    slugs = [_find_major(n).slug for n in names]
    neutral = Answers.from_payload({})
    table = Table(title="Interest profiles")
    table.add_column("Major")
    table.add_column("Code")
    for name in RIASEC:
        table.add_column(RIASEC_LETTER[name], justify="right")
    for sm in compare_majors(neutral, slugs):
        m = sm.major
        table.add_row(m.name, m.high_point_code, *[f"{v:.1f}" for v in m.riasec.as_tuple])
    console.print(table)


@app.command()
def serve(
    host: str = typer.Option(None),
    port: int = typer.Option(None),
    open_browser: bool = typer.Option(True, "--open/--no-open"),
) -> None:
    """Run the web dashboard."""
    import uvicorn

    settings = settings_from_env()
    if host:
        settings.host = host
    if port:
        settings.port = port
    url = f"http://{settings.host}:{settings.port}"
    console.print(f"[green]Compass {__version__}[/] -> {url}")
    if open_browser:
        import contextlib
        import webbrowser

        with contextlib.suppress(Exception):
            webbrowser.open(url)
    uvicorn.run("compass.api:create_app", factory=True, host=settings.host, port=settings.port)


@data_app.command("info")
def data_info() -> None:
    """Show what the bundled data covers."""
    m = profiles_meta()
    console.print(f"O*NET version:   {m['onet_version']}")
    console.print(f"Generated:       {m['generated']}")
    console.print(f"Majors:          {m['n_majors']}")
    console.print(
        f"Questionnaire:   {load_questionnaire().title}, {len(load_questionnaire().questions)} items"
    )
    console.print("Sources:")
    for s in m["sources"]:
        console.print(f"  - {s}")


@data_app.command("refresh")
@_friendly
def data_refresh(check: bool = typer.Option(False, "--check")) -> None:
    """Rebuild major_profiles.json from the official sources (needs the 'data' extra)."""
    try:
        from compass.data.refresh import main as refresh_main
    except ImportError as exc:  # pragma: no cover
        raise CompassError("the 'data' extra is not installed: pip install -e '.[data]'") from exc
    raise typer.Exit(refresh_main(["--check"] if check else []))


def _find_major(name: str):
    profiles = load_profiles()
    key = name.strip().lower()
    for m in profiles:
        if m.slug == key or m.name.lower() == key:
            return m
    matches = [m for m in profiles if key in m.name.lower()]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise CompassError(f"no major matching {name!r}")
    raise CompassError(f"{name!r} matches several: " + ", ".join(m.name for m in matches[:6]))


def _render_results(answers: Answers, top: int) -> None:
    rec = evaluate(answers, explain_top=top)
    p = rec.profile
    console.print(
        f"\nYour profile [{p.high_point_code}]   {_riasec_bar(p.scores.as_tuple, scale=4.0)}"
        f"   [dim](answered {p.answered}/{p.total_items}, confidence: {rec.confidence})[/]"
    )
    for note in rec.notes:
        console.print(f"[yellow]  {note}[/]")

    table = Table(title="Best-fitting majors")
    table.add_column("#", justify="right")
    table.add_column("Fit", justify="right")
    table.add_column("Major")
    table.add_column("Why", overflow="fold")
    for i, sm in enumerate(rec.top(top), 1):
        why = sm.explanation.summary if sm.explanation else ""
        table.add_row(str(i), str(sm.score.score), sm.major.name, why)
    console.print(table)


def main() -> None:
    try:
        app()
    except CompassError as exc:
        console.print(f"[red]error:[/] {exc}")
        raise typer.Exit(1) from exc


if __name__ == "__main__":
    main()
