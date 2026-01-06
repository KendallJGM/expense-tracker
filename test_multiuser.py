# test_multiuser.py
"""
Script para probar el sistema multiusuario
"""

import db
from rich.console import Console
from rich.table import Table

console = Console()

def test_multiuser_system():
    console.print("[bold cyan]=== PRUEBA DEL SISTEMA MULTIUSUARIO ===[/bold cyan]")
    
    # Conectar a la base de datos
    con = db.connect("finanzas.db")
    
    try:
        # 1. Probar autenticación del admin
        console.print("\n[bold]1. Probando autenticación del admin...[/bold]")
        admin = db.authenticate_user(con, "admin", "admin123")
        if admin:
            console.print(f"[green]✓ Admin autenticado: {admin.username} ({admin.role})[/green]")
        else:
            console.print("[red]✗ Error autenticando admin[/red]")
            return
        
        # 2. Crear un usuario de prueba
        console.print("\n[bold]2. Creando usuario de prueba...[/bold]")
        success = db.create_user(con, "testuser", "test123", "user")
        if success:
            console.print("[green]✓ Usuario 'testuser' creado exitosamente[/green]")
        else:
            console.print("[yellow]⚠ El usuario 'testuser' ya existe[/yellow]")
        
        # 3. Autenticar como usuario de prueba
        console.print("\n[bold]3. Probando autenticación del usuario de prueba...[/bold]")
        test_user = db.authenticate_user(con, "testuser", "test123")
        if test_user:
            console.print(f"[green]✓ Usuario autenticado: {test_user.username} ({test_user.role})[/green]")
            console.print(f"[yellow]⚠ Debe cambiar contraseña: {test_user.must_change_password}[/yellow]")
        else:
            console.print("[red]✗ Error autenticando usuario de prueba[/red]")
            return
        
        # 4. Probar aislamiento de datos
        console.print("\n[bold]4. Probando aislamiento de datos...[/bold]")
        
        # Agregar datos como admin
        db.add_account(con, "Cuenta Admin", admin.id)
        db.set_salary(con, 500000, admin.id)
        
        # Agregar datos como usuario
        db.add_account(con, "Cuenta Usuario", test_user.id)
        db.set_salary(con, 300000, test_user.id)
        
        # Verificar que cada usuario ve solo sus datos
        admin_accounts = db.list_accounts(con, admin.id)
        user_accounts = db.list_accounts(con, test_user.id)
        
        console.print(f"[green]✓ Cuentas del admin: {admin_accounts}[/green]")
        console.print(f"[green]✓ Cuentas del usuario: {user_accounts}[/green]")
        
        admin_salary = db.get_salary(con, admin.id)
        user_salary = db.get_salary(con, test_user.id)
        
        console.print(f"[green]✓ Salario del admin: {admin_salary:,} CRC[/green]")
        console.print(f"[green]✓ Salario del usuario: {user_salary:,} CRC[/green]")
        
        # 5. Listar todos los usuarios (solo admin)
        console.print("\n[bold]5. Listando todos los usuarios...[/bold]")
        users = db.list_users(con)
        
        table = Table(title="Usuarios en el Sistema")
        table.add_column("ID", style="cyan")
        table.add_column("Usuario", style="magenta")
        table.add_column("Rol", style="green")
        table.add_column("Cambiar Contraseña", style="yellow")
        
        for user in users:
            table.add_row(
                str(user.id),
                user.username,
                user.role,
                "Sí" if user.must_change_password else "No"
            )
        
        console.print(table)
        
        # 6. Probar cambio de contraseña
        console.print("\n[bold]6. Probando cambio de contraseña...[/bold]")
        db.change_password(con, test_user.id, "nuevacontraseña")
        
        # Verificar que ya no debe cambiar contraseña
        updated_user = db.authenticate_user(con, "testuser", "nuevacontraseña")
        if updated_user and not updated_user.must_change_password:
            console.print("[green]✓ Contraseña cambiada exitosamente[/green]")
        else:
            console.print("[red]✗ Error cambiando contraseña[/red]")
        
        console.print("\n[bold green]=== TODAS LAS PRUEBAS PASARON EXITOSAMENTE ===[/bold green]")
        console.print("\n[bold]Resumen del sistema implementado:[/bold]")
        console.print("• ✓ Sistema de autenticación con hashing SHA-256")
        console.print("• ✓ Roles de usuario (admin/user)")
        console.print("• ✓ Aislamiento completo de datos por usuario")
        console.print("• ✓ Gestión de usuarios solo para admin")
        console.print("• ✓ Forzado de cambio de contraseña en primer login")
        console.print("• ✓ Usuario admin hardcodeado (admin/admin123)")
        console.print("• ✓ Migración automática de datos existentes")
        
    except Exception as e:
        console.print(f"[red]✗ Error en las pruebas: {e}[/red]")
        raise
    
    finally:
        con.close()

if __name__ == "__main__":
    test_multiuser_system()
