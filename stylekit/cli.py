"""stylekit CLI."""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Windows 中文系统默认 GBK 编不了 emoji/特殊字符，强制 UTF-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

import httpx
import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn, TimeElapsedColumn
from rich.prompt import Confirm, Prompt
from rich.table import Table

from . import __version__
from .analyzer import FaceAnalyzer
from .config import config_path, get_api_key, get_setting, load_config, save_config
from .grid import build_grid
from .presets import find_preset, list_categories, load_presets
from .providers import (
    DEFAULT_OPENROUTER_MODEL,
    DEFAULT_POLLINATIONS_MODEL,
    build_provider,
)

app = typer.Typer(
    help="🎨 stylekit — AI 试发型 / 试发色 / 试穿搭。先看效果，再去理发店。",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()


def _need_key() -> str:
    key = get_api_key()
    if not key:
        console.print(Panel.fit(
            "[red]找不到 OpenRouter API key[/red]\n\n"
            "  解决：[bold cyan]stylekit setup[/bold cyan]  (交互式配置)\n"
            "  或者：在当前目录建 [cyan].env[/cyan] 写入 OPENROUTER_API_KEY=...\n"
            "  注册：https://openrouter.ai/",
            border_style="red", title="未配置"))
        raise typer.Exit(1)
    return key


def _resolve_provider(provider_flag: str | None, model_flag: str | None):
    """根据 --provider / --model / 当前配置选 provider。

    优先级：
      1. --provider 显式指定
      2. config 里 default_provider
      3. 有 OpenRouter key → openrouter
      4. 否则 → pollinations（免费 fallback）
    """
    name = provider_flag or get_setting("default_provider")
    if not name:
        name = "openrouter" if get_api_key() else "pollinations"

    if name == "openrouter":
        key = _need_key()
        model = model_flag or get_setting("default_model", DEFAULT_OPENROUTER_MODEL)
        return build_provider("openrouter", api_key=key, model=model), name, model
    elif name == "pollinations":
        model = model_flag or get_setting("pollinations_model", DEFAULT_POLLINATIONS_MODEL)
        return build_provider("pollinations", model=model), name, model
    else:
        console.print(f"[red]未知 provider: {name}[/red]")
        raise typer.Exit(1)


# ─────────────────────────────────────────── 配置 ───────────────────────────────────────────

@app.command()
def setup():
    """🔧 交互式首次配置（选 provider、配 API key）。"""
    console.print(Panel.fit(
        "[bold]欢迎使用 stylekit[/bold]\n\n"
        "可选两种生图后端：\n\n"
        "  [bold cyan]openrouter[/bold cyan]   付费、质量最好（GPT-Image-2 / Nano Banana Pro）\n"
        "             单张约 ¥0.4-1.8，需要 OpenRouter 账号+充值\n\n"
        "  [bold green]pollinations[/bold green] [bold]✨ 免费、无需 key[/bold]、零门槛\n"
        "             质量较弱（主要是文生图，面部保留有限）\n"
        "             适合先试一试、看大概效果",
        border_style="cyan", title="setup"))

    provider = Prompt.ask(
        "\n选哪个 provider",
        choices=["openrouter", "pollinations"],
        default="pollinations",
    )

    cfg = load_config()
    cfg["default_provider"] = provider

    if provider == "pollinations":
        model = Prompt.ask("Pollinations 模型", default=DEFAULT_POLLINATIONS_MODEL,
                           choices=["flux", "turbo", "kontext"], show_choices=False)
        cfg["pollinations_model"] = model
        save_config(cfg)
        console.print(f"\n[green]✓[/green] 已选 [bold]免费 Pollinations[/bold] 模式，可直接开始用")
        console.print(f"[dim]配置: {config_path()}[/dim]\n")
        console.print("[bold]试试：[/bold]")
        console.print("  [cyan]stylekit recommend -p me.jpg[/cyan]")
        console.print("\n[dim]之后想升级到付费高质量？再跑一次 [cyan]stylekit setup[/cyan][/dim]")
        return

    # OpenRouter 路径
    console.print(Panel.fit(
        "现在配置 OpenRouter：\n"
        "  1. 访问 [cyan]https://openrouter.ai/[/cyan] 注册（Google/GitHub 一键登录）\n"
        "  2. 进入 [cyan]Keys[/cyan] 页面创建一个 key（格式 sk-or-v1-...）\n"
        "  3. 充值最少 $5（约 ¥36，每张图约 ¥0.4-1.8）",
        border_style="cyan"))
    existing = cfg.get("api_key")
    if existing:
        console.print(f"[dim]当前 key: {existing[:14]}...{existing[-6:]}[/dim]")
        if not Confirm.ask("替换现有 key？", default=False):
            save_config(cfg)
            console.print("[green]✓[/green] 保留现有 key + 切换到 openrouter 模式")
            return

    key = Prompt.ask("粘贴 OpenRouter API key", password=False).strip()
    if not key.startswith("sk-or-"):
        console.print("[yellow]⚠ key 通常以 sk-or- 开头，请确认[/yellow]")
        if not Confirm.ask("继续保存？", default=False):
            raise typer.Exit(1)

    model = Prompt.ask(
        "默认 OpenRouter 图像模型",
        default=DEFAULT_OPENROUTER_MODEL,
        choices=[
            "openai/gpt-5.4-image-2",
            "openai/gpt-5-image",
            "openai/gpt-5-image-mini",
            "google/gemini-3-pro-image-preview",
            "google/gemini-3.1-flash-image-preview",
            "google/gemini-2.5-flash-image",
        ],
        show_choices=False,
    )
    cfg.update({"api_key": key, "default_model": model})
    path = save_config(cfg)
    console.print(f"\n[green]✓[/green] 已保存到 [cyan]{path}[/cyan]")
    console.print("\n[bold]接下来：[/bold]")
    console.print("  [cyan]stylekit doctor[/cyan]                     检查环境")
    console.print("  [cyan]stylekit recommend -p me.jpg[/cyan]        AI 推荐 + 自动生图")


@app.command()
def doctor():
    """🩺 诊断当前环境，看 stylekit 能不能正常用。"""
    rows: list[tuple[str, str, str]] = []

    rows.append(("Python", f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                 "✓" if sys.version_info >= (3, 10) else "✗ 需要 3.10+"))
    rows.append(("stylekit", __version__, "✓"))

    # Config file
    cfg_p = config_path()
    rows.append(("Config 文件", str(cfg_p),
                 "✓ 已存在" if cfg_p.exists() else "✗ 缺失（运行 stylekit setup）"))

    # API key
    key = get_api_key()
    if key:
        masked = f"{key[:14]}...{key[-6:]}"
        rows.append(("API key", masked, "✓ 已配置"))
    else:
        rows.append(("API key", "—", "✗ 未配置（运行 stylekit setup）"))

    # Presets
    presets = load_presets()
    rows.append(("内置预设数", str(len(presets)), "✓"))

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("项")
    table.add_column("值", overflow="fold")
    table.add_column("状态")
    for r in rows:
        table.add_row(*r)
    console.print(table)

    if not key:
        console.print("\n[red]✗ 未通过：API key 没配置。运行 [bold]stylekit setup[/bold][/red]")
        raise typer.Exit(1)

    # 实际打 OpenRouter /models 验证 key
    console.print("\n[dim]验证 API key 是否能连上 OpenRouter...[/dim]")
    try:
        r = httpx.get("https://openrouter.ai/api/v1/models",
                      headers={"Authorization": f"Bearer {key}"}, timeout=15)
        if r.status_code == 200:
            console.print("[green]✓[/green] API key 可用")
        else:
            console.print(f"[red]✗[/red] API 返回 {r.status_code}：可能 key 错了或额度用完")
            raise typer.Exit(1)
    except httpx.RequestError as e:
        console.print(f"[red]✗[/red] 网络问题：{e}")
        raise typer.Exit(1)


@app.command()
def version():
    """📦 显示版本号。"""
    console.print(f"stylekit [bold]{__version__}[/bold]")


# ─────────────────────────────────────────── 预设浏览 ───────────────────────────────────────────

@app.command(name="list")
def list_cmd(
    category: str | None = typer.Option(None, "--category", "-c", help="hairstyle | haircolor | outfit"),
    gender: str | None = typer.Option(None, "--gender", help="male | female"),
):
    """📋 列出可用预设。"""
    presets = load_presets(category)
    if gender:
        presets = [p for p in presets if p.fits(gender=gender)]

    title = f"stylekit 预设 {f'({category})' if category else ''}"
    table = Table(title=title, show_header=True, header_style="bold cyan")
    table.add_column("Slug", style="cyan", no_wrap=True)
    table.add_column("中文名")
    table.add_column("类别")
    table.add_column("说明", style="dim", overflow="fold")
    for p in presets:
        table.add_row(p.slug, p.name_zh, f"{p.category}/{p.subcategory}", p.description_zh[:50])
    console.print(table)
    console.print(f"\n共 [bold]{len(presets)}[/bold] 个预设。用 [cyan]stylekit transform --preset <slug>[/cyan] 试一个。")


# ─────────────────────────────────────────── 核心操作 ───────────────────────────────────────────

@app.command()
def analyze(
    photo: Path = typer.Option(..., "--photo", "-p", exists=True, help="正面照路径"),
):
    """🔍 AI 分析照片：脸型、肤色、年龄估计、气质、改造建议。"""
    api_key = _need_key()
    analyzer = FaceAnalyzer(api_key)
    with console.status("[cyan]分析中...[/cyan]"):
        result = analyzer.analyze(photo)
    console.print_json(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


@app.command()
def transform(
    photo: Path = typer.Option(..., "--photo", "-p", exists=True, help="源照片"),
    preset: str = typer.Option(..., "--preset", "-s", help="例如 hairstyle:side_part"),
    output: Path = typer.Option(Path("out.png"), "--output", "-o", help="输出路径"),
    provider: str = typer.Option(None, "--provider", help="openrouter | pollinations"),
    model: str = typer.Option(None, "--model", "-m", help="覆盖默认图像模型"),
):
    """✨ 应用一个预设。"""
    style = find_preset(preset)
    gen, prov_name, prov_model = _resolve_provider(provider, model)
    console.print(f"[dim]provider={prov_name} model={prov_model}[/dim]")
    with console.status(f"[yellow]生成中: {preset}...[/yellow]"):
        result = gen.transform(photo, style, output)
    cost_str = f"${result.cost_usd:.4f}" if result.cost_usd > 0 else "免费"
    console.print(f"[green]✓[/green] {result.output_path}  "
                  f"[dim]({result.output_path.stat().st_size//1024} KB · "
                  f"{result.elapsed_s}s · {cost_str})[/dim]")


@app.command()
def batch(
    photo: Path = typer.Option(..., "--photo", "-p", exists=True),
    presets: str = typer.Option(..., "--presets", help="逗号分隔: hairstyle:a,hairstyle:b"),
    output_dir: Path = typer.Option(Path("./stylekit-out"), "--output-dir", "-o"),
    provider: str = typer.Option(None, "--provider", help="openrouter | pollinations"),
    model: str = typer.Option(None, "--model", "-m"),
    grid: bool = typer.Option(True, "--grid/--no-grid", help="生成对比图集"),
):
    """🎁 批量生成多个预设。"""
    slugs = [s.strip() for s in presets.split(",") if s.strip()]
    styles = [find_preset(s) for s in slugs]
    gen, prov_name, prov_model = _resolve_provider(provider, model)
    output_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"provider: [cyan]{prov_name}[/cyan]  model: [cyan]{prov_model}[/cyan]  "
                  f"输出: [cyan]{output_dir}[/cyan]  共 {len(styles)} 个变体\n")

    results = []
    total_cost = 0.0
    with Progress(SpinnerColumn(), TextColumn("[bold]{task.description}"),
                  BarColumn(), TaskProgressColumn(), TimeElapsedColumn(),
                  console=console) as progress:
        task = progress.add_task(f"生成 {len(styles)} 个变体", total=len(styles))
        for style in styles:
            out = output_dir / f"{style.category}_{style.id}.png"
            progress.update(task, description=f"{style.slug} ({style.name_zh})")
            try:
                r = gen.transform(photo, style, out)
                results.append((style, r))
                total_cost += r.cost_usd
                console.print(f"  [green]✓[/green] {style.slug:<35} {r.elapsed_s}s  ${r.cost_usd:.4f}")
            except Exception as e:
                console.print(f"  [red]✗[/red] {style.slug}: {e}")
            progress.advance(task)

    cost_str = f"${total_cost:.4f}" if total_cost > 0 else "免费"
    console.print(f"\n[bold]{len(results)}/{len(styles)}[/bold] 张完成  "
                  f"总耗时 {sum(r.elapsed_s for _, r in results):.0f}s  "
                  f"总花费 [bold]{cost_str}[/bold]")

    if grid and results:
        grid_path = output_dir / "_grid.jpg"
        build_grid(
            [r.output_path for _, r in results],
            labels=[s.name_zh for s, _ in results],
            output=grid_path, source=photo,
        )
        console.print(f"[green]✓[/green] 对比图集: [cyan]{grid_path}[/cyan]")


@app.command()
def recommend(
    photo: Path = typer.Option(..., "--photo", "-p", exists=True),
    category: str = typer.Option("hairstyle", "--category", "-c", help="hairstyle | haircolor | outfit"),
    top: int = typer.Option(6, "--top", "-n", help="生成多少个变体"),
    output_dir: Path = typer.Option(Path("./stylekit-out"), "--output-dir", "-o"),
    dry_run: bool = typer.Option(False, "--dry-run", help="只推荐不生图"),
    provider: str = typer.Option(None, "--provider", help="openrouter | pollinations"),
    model: str = typer.Option(None, "--model", "-m"),
    gender: str = typer.Option(None, "--gender", help="无 key 时手动指定 male/female"),
):
    """🪄 一站式：AI 分析照片 → 推荐合适预设 → 批量生图 → 对比图集。

    用 pollinations 时跳过 AI 分析（只能用 --gender 手动筛选）。
    """
    api_key = get_api_key()
    picks: list
    if api_key:
        analyzer = FaceAnalyzer(api_key)
        with console.status("[cyan]分析人像 (Claude vision)...[/cyan]"):
            face = analyzer.analyze(photo)
        console.print(Panel.fit(
            f"[bold]脸型[/bold] {face.face_shape}    "
            f"[bold]肤色[/bold] {face.skin_tone}/{face.skin_tone_depth}    "
            f"[bold]性别[/bold] {face.gender}    "
            f"[bold]年龄[/bold] ~{face.age_estimate}\n"
            f"[bold]气质[/bold] {face.vibe}\n\n"
            + "\n".join(f"  · {s}" for s in face.suggested_directions),
            border_style="cyan", title="人像分析"))
        candidates = [
            p for p in load_presets(category)
            if p.fits(face_shape=face.face_shape, skin_tone=face.skin_tone, gender=face.gender)
        ]
    else:
        console.print(Panel.fit(
            "[yellow]没有 OpenRouter key，跳过 AI 人像分析[/yellow]\n"
            f"按 --gender [bold]{gender or '不限'}[/bold] 推荐（想精准请 [cyan]stylekit setup[/cyan] 配 key）",
            border_style="yellow"))
        candidates = [p for p in load_presets(category) if not gender or p.fits(gender=gender)]

    picks = candidates[:top]
    console.print(f"\n推荐 [bold]{len(picks)}[/bold] 个 [cyan]{category}[/cyan] 预设：")
    for p in picks:
        console.print(f"  · [cyan]{p.slug:<35}[/cyan] {p.name_zh}  [dim]— {p.description_zh[:40]}[/dim]")

    if dry_run or not picks:
        return

    if not Confirm.ask(f"\n开始批量生成 {len(picks)} 张？", default=True):
        return

    gen, prov_name, prov_model = _resolve_provider(provider, model)
    console.print(f"[dim]provider={prov_name} model={prov_model}[/dim]")
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    total_cost = 0.0
    with Progress(SpinnerColumn(), TextColumn("[bold]{task.description}"),
                  BarColumn(), TaskProgressColumn(), TimeElapsedColumn(),
                  console=console) as progress:
        task = progress.add_task("生成中", total=len(picks))
        for style in picks:
            out = output_dir / f"{style.category}_{style.id}.png"
            progress.update(task, description=f"{style.slug}")
            try:
                r = gen.transform(photo, style, out)
                results.append((style, r))
                total_cost += r.cost_usd
                console.print(f"  [green]✓[/green] {style.slug:<35} {r.elapsed_s}s  ${r.cost_usd:.4f}")
            except Exception as e:
                console.print(f"  [red]✗[/red] {style.slug}: {e}")
            progress.advance(task)

    grid_path = output_dir / "_grid.jpg"
    build_grid(
        [r.output_path for _, r in results],
        labels=[s.name_zh for s, _ in results],
        output=grid_path, source=photo,
    )
    cost_str = f"${total_cost:.4f}" if total_cost > 0 else "免费"
    console.print(f"\n[green]✓[/green] {len(results)} 张完成  花费 [bold]{cost_str}[/bold]")
    console.print(f"[green]✓[/green] 对比图: [cyan]{grid_path}[/cyan]")


if __name__ == "__main__":
    app()
