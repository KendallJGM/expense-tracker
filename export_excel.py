# export_excel.py
from __future__ import annotations

from typing import List, Tuple, Dict, Any, Optional
from collections import defaultdict

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.formatting.rule import CellIsRule
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.chart.label import DataLabelList


CRC_FMT = '#,##0 "CRC"'
PCT_FMT = "0.0%"


# ----------------- Estilos base -----------------

def _thin_border(color: str = "E5E7EB") -> Border:
    thin = Side(style="thin", color=color)
    return Border(left=thin, right=thin, top=thin, bottom=thin)


def _apply_border(ws, cell_range: str, color: str = "E5E7EB") -> None:
    b = _thin_border(color)
    for row in ws[cell_range]:
        for cell in row:
            cell.border = b


def _set_col_widths(ws, widths: List[int]) -> None:
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w


def _header_row(ws, row: int, max_col: int, fill_hex: str = "111827") -> None:
    fill = PatternFill("solid", fgColor=fill_hex)
    font = Font(color="FFFFFF", bold=True)
    align = Alignment(horizontal="center", vertical="center")
    border = _thin_border("374151")

    ws.row_dimensions[row].height = 20
    for c in range(1, max_col + 1):
        cell = ws.cell(row=row, column=c)
        cell.fill = fill
        cell.font = font
        cell.alignment = align
        cell.border = border


def _zebra_table(ws, start_row: int, end_row: int, start_col: int, end_col: int) -> None:
    fill = PatternFill("solid", fgColor="F9FAFB")  # gris muy suave
    for r in range(start_row, end_row + 1):
        if (r - start_row) % 2 == 1:
            for c in range(start_col, end_col + 1):
                ws.cell(row=r, column=c).fill = fill


def _fmt_range(ws, row_from: int, row_to: int, col_from: int, col_to: int, number_format: str) -> None:
    for r in range(row_from, row_to + 1):
        for c in range(col_from, col_to + 1):
            ws.cell(row=r, column=c).number_format = number_format


def _kpi_card(ws, top_row: int, left_col: int, title: str, value: str, accent: str) -> None:
    """
    Dibuja una "card" de 2 filas x 4 columnas aproximadamente.
    """
    # Card area: left_col..left_col+3
    r1, r2 = top_row, top_row + 2
    c1, c2 = left_col, left_col + 3

    ws.merge_cells(start_row=r1, start_column=c1, end_row=r1, end_column=c2)
    ws.merge_cells(start_row=r1 + 1, start_column=c1, end_row=r2, end_column=c2)

    title_cell = ws.cell(row=r1, column=c1)
    value_cell = ws.cell(row=r1 + 1, column=c1)

    title_cell.value = title
    title_cell.font = Font(bold=True, color="FFFFFF")
    title_cell.alignment = Alignment(horizontal="left", vertical="center")
    title_cell.fill = PatternFill("solid", fgColor=accent)

    value_cell.value = value
    value_cell.font = Font(bold=True, size=18, color="111827")
    value_cell.alignment = Alignment(horizontal="left", vertical="center")
    value_cell.fill = PatternFill("solid", fgColor="FFFFFF")

    _apply_border(ws, f"{get_column_letter(c1)}{r1}:{get_column_letter(c2)}{r2}", color="D1D5DB")

    ws.row_dimensions[r1].height = 18
    ws.row_dimensions[r1 + 1].height = 26
    ws.row_dimensions[r2].height = 4  # pequeño espacio visual


def _title_block(ws, title: str, subtitle: str) -> None:
    ws.merge_cells("A1:L1")
    ws.merge_cells("A2:L2")
    ws["A1"].value = title
    ws["A2"].value = subtitle
    ws["A1"].font = Font(bold=True, size=20, color="111827")
    ws["A2"].font = Font(size=11, color="6B7280")
    ws["A1"].alignment = Alignment(horizontal="left", vertical="center")
    ws["A2"].alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[1].height = 28
    ws.row_dimensions[2].height = 16


# ----------------- Utilidades de data -----------------

def _pct(numer: int, denom: int) -> Optional[float]:
    if denom <= 0:
        return None
    return numer / denom


def _category_totals_for_month(t: Dict[str, Any]) -> Dict[str, int]:
    cat = defaultdict(int)
    for rfx in t["fixed_rows"]:
        cat[rfx["category"]] += int(rfx["amount"])
    for rtx in t["tx_rows"]:
        if rtx["kind"] == "EXPENSE":
            cat[rtx["category"]] += int(rtx["amount"])
    return dict(cat)


# ----------------- Export premium -----------------

def export_excel_premium(
    out_path: str,
    months: List[Tuple[int, int, Dict[str, Any]]],  # (year, month, totals)
    fixed_expenses_rows=None,  # opcional: rows de db.list_fixed_expenses
) -> None:
    """
    months: lista cronológica (recomendado). Si no, igual funciona.
    fixed_expenses_rows: para llenar hoja Plantilla_Gastos_Fijos (opcional).
    """
    if not months:
        raise ValueError("months vacío")

    # asegurar orden cronológico
    months = sorted(months, key=lambda x: (x[0], x[1]))

    wb = Workbook()

    # ----------------- Dashboard -----------------
    ws = wb.active
    ws.title = "Dashboard"
    ws.sheet_view.showGridLines = False

    last_y, last_m, last_t = months[-1]
    first_y, first_m, _ = months[0]

    _set_col_widths(ws, [16, 16, 16, 16, 3, 18, 18, 18, 18, 3, 20, 20])
    _title_block(
        ws,
        title="Reporte de Finanzas (CRC)",
        subtitle=f"Período: {first_y:04d}-{first_m:02d}  →  {last_y:04d}-{last_m:02d}    |    Mes destacado: {last_y:04d}-{last_m:02d}",
    )

    # KPI cards (fila 4)
    sal = last_t["salary"]
    total_inc = last_t["total_income"]
    total_exp = last_t["total_expenses"]
    bal = last_t["balance"]
    pct_spend = _pct(total_exp, sal)

    _kpi_card(ws, 4, 1, "TOTAL INGRESOS", f"{total_inc:,} CRC", "2563EB")
    _kpi_card(ws, 4, 6, "TOTAL GASTOS", f"{total_exp:,} CRC", "DC2626")
    _kpi_card(ws, 4, 11, "BALANCE", f"{bal:,} CRC", "16A34A" if bal >= 0 else "DC2626")
    _kpi_card(ws, 8, 1, "% GASTO / SALARIO", "—" if pct_spend is None else f"{pct_spend*100:.1f}%", "7C3AED")
    _kpi_card(ws, 8, 6, "GASTOS FIJOS", f"{last_t['expenses_fixed']:,} CRC", "0F766E")
    _kpi_card(ws, 8, 11, "GASTOS VARIABLES", f"{last_t['expenses_var']:,} CRC", "B45309")

    # Sección: Top categorías (último mes)
    ws["A12"].value = "Top categorías del mes (por gasto total)"
    ws["A12"].font = Font(bold=True, size=12, color="111827")
    ws["A12"].alignment = Alignment(horizontal="left")
    ws.merge_cells("A12:D12")

    ws["A13"].value = "Categoría"
    ws["B13"].value = "Monto (CRC)"
    ws["C13"].value = "% gasto"
    ws["D13"].value = "% salario"
    _header_row(ws, 13, 4, fill_hex="111827")

    cat = _category_totals_for_month(last_t)
    items = sorted(cat.items(), key=lambda kv: kv[1], reverse=True)
    items = items[:10]  # top 10

    start_row = 14
    for i, (k, amt) in enumerate(items, start=0):
        r = start_row + i
        ws.cell(r, 1).value = k
        ws.cell(r, 2).value = amt
        ws.cell(r, 3).value = (amt / last_t["total_expenses"]) if last_t["total_expenses"] > 0 else None
        ws.cell(r, 4).value = (amt / sal) if sal > 0 else None
        ws.cell(r, 2).number_format = CRC_FMT
        ws.cell(r, 3).number_format = PCT_FMT
        ws.cell(r, 4).number_format = PCT_FMT

    end_row = start_row + len(items) - 1 if items else start_row
    _zebra_table(ws, start_row, end_row, 1, 4)
    _apply_border(ws, f"A13:D{end_row}", color="E5E7EB")

    # Chart: top categorías
    if items:
        bar = BarChart()
        bar.title = "Gasto por categoría (Top 10)"
        bar.y_axis.title = "CRC"
        bar.x_axis.title = "Categoría"
        bar.dataLabels = DataLabelList()
        bar.dataLabels.showVal = False

        cats_ref = Reference(ws, min_col=1, min_row=start_row, max_row=end_row)
        data_ref = Reference(ws, min_col=2, min_row=13, max_row=end_row)  # incluye header
        bar.add_data(data_ref, titles_from_data=True)
        bar.set_categories(cats_ref)
        bar.height = 10
        bar.width = 22
        ws.add_chart(bar, "F13")

    # Chart: ingresos vs gastos por mes + balance línea
    ws["F12"].value = "Tendencia por mes"
    ws["F12"].font = Font(bold=True, size=12, color="111827")
    ws["F12"].alignment = Alignment(horizontal="left")
    ws.merge_cells("F12:L12")

    # Mini tabla de serie (oculta visualmente, pero útil para charts)
    base_r = 26
    ws.cell(base_r, 6).value = "Mes"
    ws.cell(base_r, 7).value = "Ingresos"
    ws.cell(base_r, 8).value = "Gastos"
    ws.cell(base_r, 9).value = "Balance"
    _header_row(ws, base_r, 9, fill_hex="111827")

    for i, (y, m, t) in enumerate(months, start=1):
        r = base_r + i
        ws.cell(r, 6).value = f"{y:04d}-{m:02d}"
        ws.cell(r, 7).value = t["total_income"]
        ws.cell(r, 8).value = t["total_expenses"]
        ws.cell(r, 9).value = t["balance"]
        ws.cell(r, 7).number_format = CRC_FMT
        ws.cell(r, 8).number_format = CRC_FMT
        ws.cell(r, 9).number_format = CRC_FMT

    end_series = base_r + len(months)

    bar2 = BarChart()
    bar2.title = "Ingresos vs Gastos (CRC)"
    bar2.y_axis.title = "CRC"
    bar2.x_axis.title = "Mes"
    cats2 = Reference(ws, min_col=6, min_row=base_r + 1, max_row=end_series)
    data2 = Reference(ws, min_col=7, min_row=base_r, max_col=8, max_row=end_series)
    bar2.add_data(data2, titles_from_data=True)
    bar2.set_categories(cats2)
    bar2.height = 10
    bar2.width = 26
    ws.add_chart(bar2, "F13")

    line = LineChart()
    line.title = "Balance (CRC)"
    line.y_axis.title = "CRC"
    line.x_axis.title = "Mes"
    data3 = Reference(ws, min_col=9, min_row=base_r, max_row=end_series)
    line.add_data(data3, titles_from_data=True)
    line.set_categories(cats2)
    line.height = 10
    line.width = 26
    ws.add_chart(line, "F24")

    # Ocultar la mini tabla de series (opcional) -> la dejamos visible pero abajo.
    _zebra_table(ws, base_r + 1, end_series, 6, 9)
    _apply_border(ws, f"F{base_r}:I{end_series}", color="E5E7EB")

    # ----------------- Resumen_Meses -----------------
    ws_r = wb.create_sheet("Resumen_Meses")
    ws_r.sheet_view.showGridLines = False
    ws_r.freeze_panes = "A2"

    headers = [
        "Mes",
        "Salario fijo",
        "Ingresos extra",
        "Gastos fijos",
        "Gastos variables",
        "Total ingresos",
        "Total gastos",
        "Balance",
        "% gasto/salario",
    ]
    ws_r.append(headers)
    _header_row(ws_r, 1, len(headers), fill_hex="111827")

    for y, m, t in months:
        salary = t["salary"]
        ws_r.append([
            f"{y:04d}-{m:02d}",
            t["salary"],
            t["income_extra"],
            t["expenses_fixed"],
            t["expenses_var"],
            t["total_income"],
            t["total_expenses"],
            t["balance"],
            _pct(t["total_expenses"], salary),
        ])

    last_row = 1 + len(months)
    _fmt_range(ws_r, 2, last_row, 2, 8, CRC_FMT)
    _fmt_range(ws_r, 2, last_row, 9, 9, PCT_FMT)
    ws_r.auto_filter.ref = f"A1:I{last_row}"
    ws_r.row_dimensions[1].height = 20
    _set_col_widths(ws_r, [12, 16, 16, 16, 18, 16, 16, 16, 16])
    _zebra_table(ws_r, 2, last_row, 1, 9)
    _apply_border(ws_r, f"A1:I{last_row}", color="E5E7EB")

    # Condicional balance
    red_fill = PatternFill("solid", fgColor="FEE2E2")
    green_fill = PatternFill("solid", fgColor="DCFCE7")
    ws_r.conditional_formatting.add(f"H2:H{last_row}", CellIsRule(operator="lessThan", formula=["0"], fill=red_fill))
    ws_r.conditional_formatting.add(f"H2:H{last_row}", CellIsRule(operator="greaterThanOrEqual", formula=["0"], fill=green_fill))

    # ----------------- Detalle_Ultimo_Mes -----------------
    ws_d = wb.create_sheet("Detalle_Ultimo_Mes")
    ws_d.sheet_view.showGridLines = False
    ws_d.freeze_panes = "A2"

    ws_d.append([f"Detalle del mes: {last_y:04d}-{last_m:02d} (CRC)"])
    ws_d.merge_cells("A1:H1")
    ws_d["A1"].font = Font(bold=True, size=16, color="111827")
    ws_d["A1"].alignment = Alignment(horizontal="left")

    ws_d.append(["Fecha", "Tipo", "Monto", "Categoría", "Destino", "Cuenta", "Nota", "Origen"])
    _header_row(ws_d, 2, 8, fill_hex="111827")

    r = 3
    # Gastos fijos aplicados
    for fx in last_t["fixed_rows"]:
        ws_d.append([
            f"{last_y:04d}-{last_m:02d}-01",
            "Gasto",
            int(fx["amount"]),
            fx["category"],
            fx["destination"],
            fx["account"],
            fx["name"],
            "Fijo",
        ])
        r += 1

    # Movimientos variables
    for tx in last_t["tx_rows"]:
        typ = "Ingreso" if tx["kind"] == "INCOME" else "Gasto"
        ws_d.append([
            tx["tx_date"],
            typ,
            int(tx["amount"]),
            tx["category"],
            tx["destination"],
            tx["account"],
            tx["note"] or "",
            "Variable",
        ])
        r += 1

    end_d = r - 1
    _fmt_range(ws_d, 3, end_d, 3, 3, CRC_FMT)
    ws_d.auto_filter.ref = f"A2:H{end_d}"
    _set_col_widths(ws_d, [12, 12, 16, 18, 14, 10, 36, 12])
    _zebra_table(ws_d, 3, end_d, 1, 8)
    _apply_border(ws_d, f"A2:H{end_d}", color="E5E7EB")

    # ----------------- Plantilla_Gastos_Fijos (opcional) -----------------
    ws_f = wb.create_sheet("Plantilla_Gastos_Fijos")
    ws_f.sheet_view.showGridLines = False
    ws_f.freeze_panes = "A2"

    ws_f.append(["ID", "Nombre", "Monto", "Categoría", "Destino", "Cuenta", "Frecuencia", "Activo"])
    _header_row(ws_f, 1, 8, fill_hex="111827")

    if fixed_expenses_rows:
        rr = 2
        for fx in fixed_expenses_rows:
            freq = "Mensual" if fx["frequency"] == "MONTHLY" else f"Cada {fx['every_n_months']} meses"
            ws_f.append([
                int(fx["id"]),
                fx["name"],
                int(fx["amount"]),
                fx["category"],
                fx["destination"],
                fx["account"],
                freq,
                "Sí" if fx["active"] == 1 else "No",
            ])
            ws_f.cell(rr, 3).number_format = CRC_FMT
            rr += 1

        end_fx = rr - 1
        ws_f.auto_filter.ref = f"A1:H{end_fx}"
        _set_col_widths(ws_f, [8, 28, 16, 18, 14, 10, 18, 10])
        _zebra_table(ws_f, 2, end_fx, 1, 8)
        _apply_border(ws_f, f"A1:H{end_fx}", color="E5E7EB")
    else:
        _set_col_widths(ws_f, [8, 28, 16, 18, 14, 10, 18, 10])
        ws_f["A3"].value = "No se incluyeron filas de gastos fijos (pasa fixed_expenses_rows al export)."
        ws_f["A3"].font = Font(color="6B7280")
        ws_f.merge_cells("A3:H3")

    wb.save(out_path)
