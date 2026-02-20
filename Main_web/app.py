# app.py
from __future__ import annotations

from datetime import datetime, date
import getpass

import db
from ui import (
    console,
    dashboard,
    pick_from_list,
    ym_label,
)
from constants import CATEGORIES, DESTINATIONS, ACCOUNTS
from rich.prompt import Prompt, IntPrompt
from rich.table import Table

from export_excel import export_excel_premium


def _index_in_list(items: list, value: str) -> int:
    """Retorna el índice (1‑based) de value en items, o 1 si no lo encuentra."""
    try:
        return items.index(value) + 1
    except ValueError:
        return 1


def login_screen(con) -> db.User:
    """Pantalla de login y autenticación"""
    while True:
        console.print("\n[bold cyan]=== SISTEMA DE FINANZAS PERSONALES ===[/bold cyan]")
        console.print("Usuario: [bold green]admin[/bold green] | Contraseña: [bold green]admin123[/bold green] (primer login)")
        console.print()
        
        username = Prompt.ask("Usuario").strip()
        if not username:
            continue
            
        password = getpass.getpass("Contraseña: ").strip()
        if not password:
            continue
        
        user = db.authenticate_user(con, username, password)
        if user:
            console.print(f"[green]✓ Bienvenido, {user.username}![/green]")
            
            # Forzar cambio de contraseña si es necesario
            if user.must_change_password:
                console.print("\n[yellow]⚠ Debes cambiar tu contraseña antes de continuar.[/yellow]")
                change_password_screen(con, user)
                
            return user
        else:
            console.print("[red]✗ Usuario o contraseña incorrectos.[/red]")


def change_password_screen(con, user: db.User) -> None:
    """Pantalla para cambiar contraseña"""
    while True:
        console.print("\n[bold]Cambiar Contraseña[/bold]")
        current = getpass.getpass("Contraseña actual: ").strip()
        if not db.verify_password(current, user.password_hash):
            console.print("[red]Contraseña actual incorrecta.[/red]")
            continue
            
        new_pass = getpass.getpass("Nueva contraseña: ").strip()
        if len(new_pass) < 4:
            console.print("[red]La contraseña debe tener al menos 4 caracteres.[/red]")
            continue
            
        confirm = getpass.getpass("Confirmar nueva contraseña: ").strip()
        if new_pass != confirm:
            console.print("[red]Las contraseñas no coinciden.[/red]")
            continue
            
        db.change_password(con, user.id, new_pass)
        console.print("[green]✓ Contraseña cambiada exitosamente.[/green]")
        break


def manage_users_screen(con, current_user: db.User) -> None:
    """Pantalla de gestión de usuarios (solo admin)"""
    while True:
        users = db.list_users(con)
        
        console.print("\n[bold]Gestión de Usuarios[/bold]")
        table = Table(title="Usuarios Registrados")
        table.add_column("ID", style="cyan")
        table.add_column("Usuario", style="magenta")
        table.add_column("Rol", style="green")
        table.add_column("Cambiar Contraseña", style="yellow")
        table.add_column("Creado", style="blue")
        
        for user in users:
            table.add_row(
                str(user.id),
                user.username,
                user.role,
                "Sí" if user.must_change_password else "No",
                user.created_at[:10]
            )
        
        console.print(table)
        
        options = ["Crear usuario", "Eliminar usuario", "Volver"]
        action = pick_from_list("Acción", options, default_index=3)
        
        if action == 3:
            return
        elif action == 1:
            create_user_screen(con)
        elif action == 2:
            delete_user_screen(con, users)


def create_user_screen(con) -> None:
    """Crear nuevo usuario"""
    console.print("\n[bold]Crear Nuevo Usuario[/bold]")
    username = Prompt.ask("Nombre de usuario").strip()
    if not username:
        console.print("[yellow]Nombre de usuario inválido.[/yellow]")
        return
        
    password = getpass.getpass("Contraseña: ").strip()
    if len(password) < 4:
        console.print("[red]La contraseña debe tener al menos 4 caracteres.[/red]")
        return
        
    role = pick_from_list("Rol", ["usuario", "administrador"], default_index=1)
    role_str = "user" if role == 1 else "admin"
    
    if db.create_user(con, username, password, role_str):
        console.print(f"[green]✓ Usuario '{username}' creado exitosamente.[/green]")
    else:
        console.print(f"[red]✗ El usuario '{username}' ya existe.[/red]")


def delete_user_screen(con, users: list) -> None:
    """Eliminar usuario"""
    if len(users) <= 1:
        console.print("[yellow]No se pueden eliminar usuarios (debe quedar al menos uno).[/yellow]")
        return
        
    console.print("\n[bold]Eliminar Usuario[/bold]")
    for i, user in enumerate(users, start=1):
        console.print(f"  {i}) {user.username} ({user.role})")
        
    try:
        idx = IntPrompt.ask("Número de usuario a eliminar (0 para cancelar)", default=0)
        if idx == 0:
            return
        if 1 <= idx <= len(users):
            user = users[idx - 1]
            confirm = Prompt.ask(f"¿Eliminar '{user.username}'? (s/N)", default="N").strip().lower()
            if confirm == "s":
                if db.delete_user(con, user.id):
                    console.print(f"[green]✓ Usuario '{user.username}' eliminado.[/green]")
                else:
                    console.print("[red]✗ No se pudo eliminar el usuario.[/red]")
            else:
                console.print("[yellow]Cancelado.[/yellow]")
        else:
            console.print("[red]Número inválido.[/red]")
    except (ValueError, IndexError):
        console.print("[red]Entrada inválida.[/red]")


def ensure_current_month(con, user_id: int) -> tuple[int, int]:
    """
    Usa FECHA REAL de la PC (local) y crea automáticamente el mes si no existe.
    """
    today = date.today()
    db.ensure_month_for_today(con, today, user_id)
    return today.year, today.month


def pick_month(con, user_id: int, default_y: int, default_m: int) -> tuple[int, int]:
    months = db.list_months(con, user_id, limit=48)
    labels = [ym_label(r.year, r.month) for r in months]

    default_label = ym_label(default_y, default_m)
    default_index = 1
    for i, lab in enumerate(labels, start=1):
        if lab == default_label:
            default_index = i
            break

    idx = pick_from_list("Cambiar mes", labels, default_index=default_index)
    r = months[idx - 1]
    db.ensure_month(con, r.year, r.month, user_id)
    return r.year, r.month


def config_salary(con, user_id: int) -> None:
    salary = db.get_salary(con, user_id)
    console.print(f"\nSalario actual: [bold]{salary:,} CRC[/bold]")
    v = IntPrompt.ask("Nuevo salario (CRC)", default=salary)
    if v < 0:
        v = 0
    db.set_salary(con, v, user_id)
    console.print("[green]Salario actualizado.[/green]")


def manage_accounts(con, user_id: int) -> None:
    while True:
        accounts = db.list_accounts(con, user_id)
        console.print("\n[bold]Cuentas de banco[/bold]")
        for i, acc in enumerate(accounts, start=1):
            console.print(f"  {i}) {acc}")

        action = pick_from_list("Acción", ["Agregar cuenta", "Eliminar cuenta", "Volver"], default_index=3)
        if action == 3:
            return
        if action == 1:
            name = Prompt.ask("Nombre de la nueva cuenta").strip()
            if not name:
                console.print("[yellow]Nombre inválido.[/yellow]")
                continue
            if name in accounts:
                console.print("[yellow]Ya existe una cuenta con ese nombre.[/yellow]")
                continue
            db.add_account(con, name, user_id)
            console.print(f"[green]Cuenta '{name}' agregada.[/green]")
        else:  # Eliminar
            if not accounts:
                console.print("[yellow]No hay cuentas para eliminar.[/yellow]")
                continue
            console.print()
            for i, acc in enumerate(accounts, start=1):
                console.print(f"  {i}) {acc}")
            idx = IntPrompt.ask("Número de cuenta a eliminar (0 para cancelar)", default=0)
            if idx == 0:
                continue
            if 1 <= idx <= len(accounts):
                name = accounts[idx - 1]
                # Preguntar confirmación
                confirm = Prompt.ask(f"¿Eliminar la cuenta '{name}'? (s/N)", default="N").strip().lower()
                if confirm == "s":
                    db.delete_account(con, name, user_id)
                    console.print(f"[green]Cuenta '{name}' eliminada.[/green]")
                else:
                    console.print("[yellow]Cancelado.[/yellow]")
            else:
                console.print("[red]Número inválido.[/red]")


def add_expense(con, user_id: int, y: int, m: int) -> None:
    kind = pick_from_list("Tipo de gasto", ["Fijo (plantilla)", "Variable (mes actual)"], default_index=2)
    if kind == 1:
        add_fixed(con, user_id, y, m)
    else:
        add_movement(con, user_id, y, m)


def add_fixed(con, user_id: int, y: int, m: int) -> None:
    console.print("\n[bold]Agregar gasto fijo (plantilla)[/bold]")
    amount = IntPrompt.ask("Monto (CRC)", default=0)
    if amount <= 0:
        console.print("[yellow]Monto inválido.[/yellow]")
        return

    name = Prompt.ask("Nombre").strip()
    if not name:
        console.print("[yellow]Nombre inválido.[/yellow]")
        return

    c = pick_from_list("Categoría", CATEGORIES, default_index=len(CATEGORIES))
    d = pick_from_list("Destino del gasto", DESTINATIONS, default_index=1)
    accounts = db.list_accounts(con, user_id)
    a = pick_from_list("Cuenta", accounts, default_index=1)
    f = pick_from_list("Frecuencia", ["Mensual", "Cada N meses"], default_index=1)

    if f == 1:
        freq = "MONTHLY"
        every_n = None
    else:
        freq = "EVERY_N_MONTHS"
        every_n = IntPrompt.ask("Cada cuántos meses (N)", default=2)
        if every_n < 2:
            every_n = 2

    db.add_fixed_expense(
        con,
        name=name,
        amount=amount,
        category=CATEGORIES[c - 1],
        destination=DESTINATIONS[d - 1],
        account=accounts[a - 1],
        frequency=freq,
        every_n_months=every_n,
        start_year=y,
        start_month=m,
        user_id=user_id,
    )
    console.print("[green]Gasto fijo agregado.[/green]")


def edit_fixed_expense(con, user_id: int) -> None:
    rows = db.list_fixed_expenses(con, user_id, active_only=False)
    if not rows:
        console.print("[yellow]No hay gastos fijos para editar.[/yellow]")
        return

    from ui import build_fixed_table
    console.print()
    console.print(build_fixed_table(rows))

    fx_id = IntPrompt.ask("ID del gasto fijo a editar (0 para salir)", default=0)
    if fx_id == 0:
        return

    target = next((r for r in rows if r["id"] == fx_id), None)
    if not target:
        console.print("[red]ID no encontrado.[/red]")
        return

    console.print("\n[bold]Editar gasto fijo[/bold]")
    name = Prompt.ask("Nombre", default=target["name"]).strip()
    if not name:
        console.print("[yellow]Nombre inválido.[/yellow]")
        return

    amount = IntPrompt.ask("Monto (CRC)", default=int(target["amount"]))
    if amount <= 0:
        console.print("[yellow]Monto inválido.[/yellow]")
        return

    c = pick_from_list("Categoría", CATEGORIES, default_index=_index_in_list(CATEGORIES, target["category"]))
    d = pick_from_list("Destino", DESTINATIONS, default_index=_index_in_list(DESTINATIONS, target["destination"]))
    accounts = db.list_accounts(con, user_id)
    a = pick_from_list("Cuenta", accounts, default_index=_index_in_list(accounts, target["account"]))
    f = pick_from_list("Frecuencia", ["Mensual", "Cada N meses"], default_index=1 if target["frequency"] == "MONTHLY" else 2)

    if f == 1:
        freq = "MONTHLY"
        every_n = None
    else:
        freq = "EVERY_N_MONTHS"
        every_n = IntPrompt.ask("Cada cuántos meses (N)", default=target["every_n_months"] or 2)
        if every_n < 2:
            every_n = 2

    db.update_fixed_expense(
        con,
        fx_id,
        name=name,
        amount=amount,
        category=CATEGORIES[c - 1],
        destination=DESTINATIONS[d - 1],
        account=accounts[a - 1],
        frequency=freq,
        every_n_months=every_n,
        user_id=user_id,
    )
    console.print("[green]Gasto fijo actualizado.[/green]")


def manage_fixed(con, user_id: int) -> None:
    rows = db.list_fixed_expenses(con, user_id, active_only=False)
    if not rows:
        console.print("[yellow]No hay gastos fijos.[/yellow]")
        return

    from ui import build_fixed_table
    console.print()
    console.print(build_fixed_table(rows))

    fx_id = IntPrompt.ask("ID para editar/activar/desactivar (0 para salir)", default=0)
    if fx_id == 0:
        return

    # Buscar el registro
    target = next((r for r in rows if r["id"] == fx_id), None)
    if not target:
        console.print("[red]ID no encontrado.[/red]")
        return

    action = pick_from_list("Acción", ["Editar", "Activar", "Desactivar"], default_index=1)
    if action == 2 or action == 3:
        db.toggle_fixed_expense(con, fx_id, active=(action == 2), user_id=user_id)
        console.print("[green]Actualizado.[/green]")
        return

    # Editar
    console.print("\n[bold]Editar gasto fijo[/bold]")
    name = Prompt.ask("Nombre", default=target["name"]).strip()
    if not name:
        console.print("[yellow]Nombre inválido.[/yellow]")
        return

    amount = IntPrompt.ask("Monto (CRC)", default=int(target["amount"]))
    if amount <= 0:
        console.print("[yellow]Monto inválido.[/yellow]")
        return

    c = pick_from_list("Categoría", CATEGORIES, default_index=_index_in_list(CATEGORIES, target["category"]))
    d = pick_from_list("Destino", DESTINATIONS, default_index=_index_in_list(DESTINATIONS, target["destination"]))
    accounts = db.list_accounts(con, user_id)
    a = pick_from_list("Cuenta", accounts, default_index=_index_in_list(accounts, target["account"]))
    f = pick_from_list("Frecuencia", ["Mensual", "Cada N meses"], default_index=1 if target["frequency"] == "MONTHLY" else 2)

    if f == 1:
        freq = "MONTHLY"
        every_n = None
    else:
        freq = "EVERY_N_MONTHS"
        every_n = IntPrompt.ask("Cada cuántos meses (N)", default=target["every_n_months"] or 2)
        if every_n < 2:
            every_n = 2

    db.update_fixed_expense(
        con,
        fx_id,
        name=name,
        amount=amount,
        category=CATEGORIES[c - 1],
        destination=DESTINATIONS[d - 1],
        account=accounts[a - 1],
        frequency=freq,
        every_n_months=every_n,
        user_id=user_id,
    )
    console.print("[green]Gasto fijo actualizado.[/green]")


def add_movement(con, user_id: int, y: int, m: int) -> None:
    console.print("\n[bold]Agregar movimiento (mes actual)[/bold]")
    kind = pick_from_list("Tipo", ["Ingreso extra", "Gasto variable"], default_index=2)

    amount = IntPrompt.ask("Monto (CRC)", default=0)
    if amount <= 0:
        console.print("[yellow]Monto inválido.[/yellow]")
        return

    c = pick_from_list("Categoría", CATEGORIES, default_index=len(CATEGORIES))
    d = pick_from_list("Destino", DESTINATIONS, default_index=1)
    accounts = db.list_accounts(con, user_id)
    a = pick_from_list("Cuenta", accounts, default_index=1)

    today = date.today()
    tx_date = Prompt.ask("Fecha (YYYY-MM-DD)", default=today.isoformat()).strip()
    note = Prompt.ask("Nota (opcional)", default="").strip()

    db.add_transaction(
        con,
        tx_date=tx_date,
        year=y,
        month=m,
        kind="INCOME" if kind == 1 else "EXPENSE",
        amount=amount,
        category=CATEGORIES[c - 1],
        destination=DESTINATIONS[d - 1],
        account=accounts[a - 1],
        note=note if note else None,
        user_id=user_id,
    )
    console.print("[green]Movimiento guardado.[/green]")


def edit_movement(con, user_id: int, y: int, m: int) -> None:
    totals = db.month_totals(con, y, m, user_id)
    rows = totals["tx_rows"]
    if not rows:
        console.print("[yellow]No hay movimientos en el mes para editar.[/yellow]")
        return

    from ui import build_tx_table
    console.print()
    console.print(build_tx_table(rows))

    tx_id = IntPrompt.ask("ID del movimiento a editar (0 para salir)", default=0)
    if tx_id == 0:
        return

    target = next((r for r in rows if r["id"] == tx_id), None)
    if not target:
        console.print("[red]ID no encontrado.[/red]")
        return

    console.print("\n[bold]Editar movimiento[/bold]")
    kind = pick_from_list("Tipo", ["Ingreso extra", "Gasto variable"], default_index=1 if target["kind"] == "INCOME" else 2)
    amount = IntPrompt.ask("Monto (CRC)", default=int(target["amount"]))
    if amount <= 0:
        console.print("[yellow]Monto inválido.[/yellow]")
        return

    c = pick_from_list("Categoría", CATEGORIES, default_index=_index_in_list(CATEGORIES, target["category"]))
    d = pick_from_list("Destino", DESTINATIONS, default_index=_index_in_list(DESTINATIONS, target["destination"]))
    accounts = db.list_accounts(con, user_id)
    a = pick_from_list("Cuenta", accounts, default_index=_index_in_list(accounts, target["account"]))
    tx_date = Prompt.ask("Fecha (YYYY-MM-DD)", default=target["tx_date"]).strip()
    note = Prompt.ask("Nota (opcional)", default=target["note"] or "").strip()

    db.update_transaction(
        con,
        tx_id,
        tx_date=tx_date,
        kind="INCOME" if kind == 1 else "EXPENSE",
        amount=amount,
        category=CATEGORIES[c - 1],
        destination=DESTINATIONS[d - 1],
        account=accounts[a - 1],
        note=note if note else None,
        user_id=user_id,
    )
    console.print("[green]Movimiento actualizado.[/green]")


def show_detail(con, user_id: int, y: int, m: int) -> None:
    totals = db.month_totals(con, y, m, user_id)
    from ui import build_tx_table
    console.print()
    console.print(build_tx_table(totals["tx_rows"]))
    action = pick_from_list("Acción", ["Editar movimiento", "Volver"], default_index=2)
    if action == 2:
        return
    tx_id = IntPrompt.ask("ID del movimiento a editar (0 para cancelar)", default=0)
    if tx_id == 0:
        return
    target = next((r for r in totals["tx_rows"] if r["id"] == tx_id), None)
    if not target:
        console.print("[red]ID no encontrado.[/red]")
        Prompt.ask("\nEnter para volver", default="")
        return

    console.print("\n[bold]Editar movimiento[/bold]")
    kind = pick_from_list("Tipo", ["Ingreso extra", "Gasto variable"], default_index=1 if target["kind"] == "INCOME" else 2)
    amount = IntPrompt.ask("Monto (CRC)", default=int(target["amount"]))
    if amount <= 0:
        console.print("[yellow]Monto inválido.[/yellow]")
        return

    c = pick_from_list("Categoría", CATEGORIES, default_index=_index_in_list(CATEGORIES, target["category"]))
    d = pick_from_list("Destino", DESTINATIONS, default_index=_index_in_list(DESTINATIONS, target["destination"]))
    accounts = db.list_accounts(con, user_id)
    a = pick_from_list("Cuenta", accounts, default_index=_index_in_list(accounts, target["account"]))
    tx_date = Prompt.ask("Fecha (YYYY-MM-DD)", default=target["tx_date"]).strip()
    note = Prompt.ask("Nota (opcional)", default=target["note"] or "").strip()

    db.update_transaction(
        con,
        tx_id,
        tx_date=tx_date,
        kind="INCOME" if kind == 1 else "EXPENSE",
        amount=amount,
        category=CATEGORIES[c - 1],
        destination=DESTINATIONS[d - 1],
        account=accounts[a - 1],
        note=note if note else None,
        user_id=user_id,
    )
    console.print("[green]Movimiento actualizado.[/green]")
    Prompt.ask("\nEnter para volver", default="")


def export_excel(con, user_id: int) -> None:
    months = db.list_months(con, user_id, limit=60)
    months = sorted(months, key=lambda r: (r.year, r.month))  # cronológico

    n = IntPrompt.ask("Exportar últimos N meses", default=6)
    if n < 1:
        n = 1

    months = months[-n:]
    data = []
    for r in months:
        t = db.month_totals(con, r.year, r.month, user_id)
        data.append((r.year, r.month, t))

    fixed_rows = db.list_fixed_expenses(con, user_id, active_only=False)

    filename = Prompt.ask("Nombre del archivo", default="reporte_finanzas.xlsx")
    export_excel_premium(filename, data, fixed_expenses_rows=fixed_rows)
    console.print(f"[green]Excel creado:[/green] {filename}")
    Prompt.ask("Enter para volver", default="")


def main() -> None:
    con = db.connect("finanzas.db")
    db.init_schema(con)
    
    # Login
    current_user = login_screen(con)
    
    # Mes actual automático por FECHA PC
    y, m = ensure_current_month(con, current_user.id)

    while True:
        now = datetime.now()  # hora real PC
        y_now, m_now = ensure_current_month(con, current_user.id)
        # si cambió el mes en la PC, cambiamos automáticamente la vista al mes actual
        if (y_now, m_now) != (y, m):
            y, m = y_now, m_now

        totals = db.month_totals(con, y, m, current_user.id)
        hint = f"Todo en CRC. El mes se crea solo con la fecha de tu PC. Usuario: {current_user.username} ({current_user.role})"
        dashboard(
            app_title="FINANZAS (CRC)",
            now=now,
            selected_year=y,
            selected_month=m,
            totals=totals,
            hint=hint,
        )

        # Construir menú dinámico según rol
        menu_options = [
            "1) Configurar salario",
            "2) Agregar gasto/ingreso",
            "3) Editar gastos fijos",
            "4) Editar movimientos",
            "5) Gestionar gastos fijos",
            "6) Gestionar cuentas",
            "7) Ver detalle del mes",
            "8) Exportar a Excel",
            "9) Cambiar mes",
        ]
        
        # Opciones adicionales para admin
        if current_user.role == "admin":
            menu_options.extend([
                "10) Gestionar usuarios",
                "11) Cambiar mi contraseña",
                "0) Salir"
            ])
        else:
            menu_options.extend([
                "10) Cambiar mi contraseña",
                "0) Salir"
            ])

        console.print("\n[bold]Menú de Opciones[/bold]")
        for option in menu_options:
            console.print(option)

        op = IntPrompt.ask("Opción", default=0)

        if op == 0:
            break
        elif op == 1:
            config_salary(con, current_user.id)
        elif op == 2:
            add_expense(con, current_user.id, y, m)
        elif op == 3:
            edit_fixed_expense(con, current_user.id)
        elif op == 4:
            edit_movement(con, current_user.id, y, m)
        elif op == 5:
            manage_fixed(con, current_user.id)
        elif op == 6:
            manage_accounts(con, current_user.id)
        elif op == 7:
            show_detail(con, current_user.id, y, m)
        elif op == 8:
            export_excel(con, current_user.id)
        elif op == 9:
            y, m = pick_month(con, current_user.id, y, m)
        elif op == 10:
            if current_user.role == "admin":
                manage_users_screen(con, current_user)
            else:
                change_password_screen(con, current_user)
        elif op == 11:
            if current_user.role == "admin":
                change_password_screen(con, current_user)
        else:
            console.print("[red]Opción inválida.[/red]")


if __name__ == "__main__":
    main()
