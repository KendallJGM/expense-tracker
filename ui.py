# ui.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any
from collections import defaultdict

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.rule import Rule
from rich.text import Text
from rich.align import Align
from rich.box import ROUNDED
from rich.prompt import Prompt, IntPrompt


console = Console()


def money_crc(n: int) -> str:
    return f"{n:,} CRC"


def pct(numer: int, denom: int) -> str:
    if denom <= 0:
        return "—"
    return f"{(numer / denom) * 100:.1f}%"


def ym_label(y: int, m: int) -> str:
    return f"{y:04d}-{m:02d}"


@dataclass
class CategoryStats:
    amount: int = 0


def build_summary_table(totals: Dict[str, Any]) -> Table:
    salary = totals["salary"]
    fixed = totals["expenses_fixed"]
    var = totals["expenses_var"]
    total_exp = totals["total_expenses"]
    total_inc = totals["total_income"]
    bal = totals["balance"]

    t = Table(box=ROUNDED, show_header=False, expand=True)
    t.add_column("k", style="bold")
    t.add_column("v", justify="right")

    t.add_row("Salario fijo", money_crc(salary))
    t.add_row("Ingresos extra", money_crc(totals["income_extra"]))
    t.add_row(Rule(), Rule())
    t.add_row("Gastos fijos", f"{money_crc(fixed)}   [dim]({pct(fixed, salary)} del salario)[/dim]")
    t.add_row("Gastos variables", f"{money_crc(var)}   [dim]({pct(var, salary)} del salario)[/dim]")
    t.add_row("Gasto total", f"{money_crc(total_exp)}   [dim]({pct(total_exp, salary)} del salario)[/dim]")
    t.add_row(Rule(), Rule())
    t.add_row("[bold]Total ingresos[/bold]", f"[bold]{money_crc(total_inc)}[/bold]")

    bal_style = "green" if bal >= 0 else "red"
    t.add_row("[bold]Balance[/bold]", f"[bold {bal_style}]{money_crc(bal)}[/bold {bal_style}]")
    return t


def build_category_table(totals: Dict[str, Any]) -> Table:
    salary = totals["salary"]
    fixed_rows = totals["fixed_rows"]
    tx_rows = totals["tx_rows"]

    cat = defaultdict(int)

    for r in fixed_rows:
        cat[r["category"]] += int(r["amount"])

    for r in tx_rows:
        if r["kind"] == "EXPENSE":
            cat[r["category"]] += int(r["amount"])

    total_exp = totals["total_expenses"]

    t = Table(title="Gastos por categoría", box=ROUNDED, expand=True)
    t.add_column("Categoría")
    t.add_column("Monto", justify="right")
    t.add_column("% salario", justify="right")
    t.add_column("% gasto total", justify="right")

    items = sorted(cat.items(), key=lambda x: x[1], reverse=True)
    for k, amt in items[:12]:
        t.add_row(k, money_crc(amt), pct(amt, salary), pct(amt, total_exp))

    if len(items) > 12:
        rest = sum(v for _, v in items[12:])
        t.add_row("[dim]Otros[/dim]", money_crc(rest), pct(rest, salary), pct(rest, total_exp))

    return t


def build_fixed_table(rows) -> Table:
    t = Table(title="Gastos fijos (plantilla)", box=ROUNDED, expand=True)
    t.add_column("ID", justify="right")
    t.add_column("Nombre")
    t.add_column("Monto", justify="right")
    t.add_column("Categoría")
    t.add_column("Destino")
    t.add_column("Cuenta")
    t.add_column("Frecuencia")
    t.add_column("Activo", justify="center")

    for r in rows:
        freq = "Mensual" if r["frequency"] == "MONTHLY" else f"Cada {r['every_n_months']} meses"
        t.add_row(
            str(r["id"]),
            r["name"],
            money_crc(int(r["amount"])),
            r["category"],
            r["destination"],
            r["account"],
            freq,
            "Sí" if r["active"] == 1 else "No",
        )
    return t


def build_tx_table(rows) -> Table:
    t = Table(title="Movimientos (variables)", box=ROUNDED, expand=True)
    t.add_column("Fecha")
    t.add_column("Tipo")
    t.add_column("Monto", justify="right")
    t.add_column("Categoría")
    t.add_column("Destino")
    t.add_column("Cuenta")
    t.add_column("Nota")

    for r in rows:
        kind = "Ingreso" if r["kind"] == "INCOME" else "Gasto"
        amt = int(r["amount"])
        style = "green" if r["kind"] == "INCOME" else "red"
        t.add_row(
            r["tx_date"],
            kind,
            f"[{style}]{money_crc(amt)}[/{style}]",
            r["category"],
            r["destination"],
            r["account"],
            r["note"] or "",
        )
    return t


def _actions_grid(hint: str) -> Panel:
    """
    Footer: acciones en 2 columnas (pares de 2 en 2).
    """
    actions = [
        ("1", "Salario", "Configurar salario fijo"),
        ("2", "Gastos", "Agregar gasto (fijo o variable)"),
        ("3", "Editar gasto fijo", "Modificar un gasto fijo existente"),
        ("4", "Editar movimiento", "Modificar un movimiento del mes"),
        ("5", "Plantilla", "Ver/activar/desactivar fijos"),
        ("6", "Cuentas", "Agregar/eliminar cuentas de banco"),
        ("7", "Detalle", "Ver movimientos del mes"),
        ("8", "Excel", "Exportar reporte"),
        ("9", "Mes", "Cambiar mes"),
        ("0", "Salir", "Cerrar aplicación"),
    ]

    grid = Table(box=None, show_header=False, pad_edge=False, expand=True)
    grid.add_column("Col1", ratio=1)
    grid.add_column("Col2", ratio=1)

    def cell(a) -> Text:
        key, title, desc = a
        return Text.assemble(
            ("[", "dim"), (key, "bold cyan"), ("] ", "dim"),
            (title, "bold"),
            ("\n", ""),
            (desc, "dim"),
        )

    # 2 por fila
    for i in range(0, len(actions), 2):
        left = cell(actions[i])
        right = cell(actions[i + 1]) if i + 1 < len(actions) else Text("")
        grid.add_row(left, right)

    footer = Table(box=None, show_header=False, expand=True, pad_edge=False)
    footer.add_column("A", ratio=1)
    footer.add_row(grid)
    footer.add_row(Text(hint, style="dim"))

    return Panel(footer, title="Acciones", box=ROUNDED)


def dashboard(
    *,
    app_title: str,
    now: datetime,
    selected_year: int,
    selected_month: int,
    totals: Dict[str, Any],
    hint: str,
) -> None:
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=5),
        Layout(name="body", ratio=1),
        Layout(name="footer", size=9),  # más alto para la grilla
    )

    h = Text.assemble(
        (f"{app_title}  ", "bold"),
        (f"Fecha PC: {now.strftime('%Y-%m-%d %H:%M:%S')}", "dim"),
        ("\n", ""),
        (f"Mes seleccionado: {ym_label(selected_year, selected_month)}", "bold"),
    )
    layout["header"].update(Panel(Align.left(h), box=ROUNDED))

    left = Layout(name="left", ratio=1)
    right = Layout(name="right", ratio=1)
    layout["body"].split_row(left, right)

    left.update(Panel(build_summary_table(totals), title="Resumen", box=ROUNDED))
    right.update(Panel(build_category_table(totals), title="Análisis", box=ROUNDED))

    layout["footer"].update(_actions_grid(hint))

    console.clear()
    console.print(layout)


def prompt_action() -> int:
    """
    Acción validada: 0..7
    """
    while True:
        v = IntPrompt.ask("Opción", default=5)
        if v in (0, 1, 2, 3, 4, 5, 6, 7):
            return v
        console.print("[red]Opción inválida. Use 0..7[/red]")


def pick_from_list(title: str, labels: List[str], default_index: int = 1) -> int:
    console.print()
    console.print(Panel(Text(title, style="bold"), box=ROUNDED))
    for i, lab in enumerate(labels, start=1):
        console.print(f"  {i}) {lab}")
    while True:
        raw = Prompt.ask(f"Seleccione [1-{len(labels)}] ({default_index})", default=str(default_index)).strip()
        if raw.isdigit():
            v = int(raw)
            if 1 <= v <= len(labels):
                return v
        console.print("[red]Opción inválida.[/red]")
