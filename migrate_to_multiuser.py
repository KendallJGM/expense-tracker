# migrate_to_multiuser.py
"""
Script para migrar la base de datos existente a un sistema multiusuario.
Crea una copia de seguridad y agrega las columnas necesarias.
"""

import sqlite3
import os
import shutil
from datetime import datetime

def migrate_database():
    db_path = "finanzas.db"
    backup_path = f"finanzas_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    
    # Crear copia de seguridad solo si existe la base de datos
    if os.path.exists(db_path):
        shutil.copy2(db_path, backup_path)
        print(f"✓ Copia de seguridad creada: {backup_path}")
        
        # Leer datos existentes antes de eliminar
        con_old = sqlite3.connect(db_path)
        con_old.row_factory = sqlite3.Row
        
        # Extraer datos existentes
        old_months = con_old.execute("SELECT * FROM months").fetchall()
        old_settings = con_old.execute("SELECT * FROM settings").fetchall()
        old_fixed = con_old.execute("SELECT * FROM fixed_expenses").fetchall()
        old_accounts = con_old.execute("SELECT * FROM accounts").fetchall()
        old_transactions = con_old.execute("SELECT * FROM transactions").fetchall()
        
        con_old.close()
        
        # Eliminar base de datos vieja
        os.remove(db_path)
    
    # Crear nueva base de datos con esquema multiusuario
    con = sqlite3.connect(db_path)
    con.execute("PRAGMA foreign_keys = ON;")
    
    try:
        # Importar y ejecutar init_schema
        import db
        db.init_schema(con)
        
        # Si había datos existentes, migrarlos
        if os.path.exists(backup_path):
            admin_id = con.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()[0]
            
            # Migrar datos
            for month in old_months:
                con.execute("""
                    INSERT OR IGNORE INTO months(year, month, start_date, user_id)
                    VALUES (?, ?, ?, ?)
                """, (month['year'], month['month'], month['start_date'], admin_id))
            
            # Migrar settings
            if old_settings:
                for setting in old_settings:
                    con.execute("""
                        INSERT OR IGNORE INTO settings(salary_amount, user_id)
                        VALUES (?, ?)
                    """, (setting['salary_amount'], admin_id))
            
            # Migrar gastos fijos
            for fixed in old_fixed:
                con.execute("""
                    INSERT OR IGNORE INTO fixed_expenses(
                        name, amount, category, destination, account, 
                        frequency, every_n_months, start_year, start_month, active, user_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    fixed['name'], fixed['amount'], fixed['category'], fixed['destination'],
                    fixed['account'], fixed['frequency'], fixed['every_n_months'],
                    fixed['start_year'], fixed['start_month'], fixed['active'], admin_id
                ))
            
            # Migrar cuentas
            for account in old_accounts:
                con.execute("""
                    INSERT OR IGNORE INTO accounts(name, user_id)
                    VALUES (?, ?)
                """, (account['name'], admin_id))
            
            # Migrar transacciones
            for tx in old_transactions:
                con.execute("""
                    INSERT OR IGNORE INTO transactions(
                        tx_date, year, month, kind, amount, category, 
                        destination, account, note, user_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    tx['tx_date'], tx['year'], tx['month'], tx['kind'],
                    tx['amount'], tx['category'], tx['destination'],
                    tx['account'], tx['note'], admin_id
                ))
            
            con.commit()
            print(f"✓ {len(old_months)} meses migrados")
            print(f"✓ {len(old_settings)} configuraciones migradas")
            print(f"✓ {len(old_fixed)} gastos fijos migrados")
            print(f"✓ {len(old_accounts)} cuentas migradas")
            print(f"✓ {len(old_transactions)} transacciones migradas")
        
        print("✓ Migración completada exitosamente")
        print(f"✓ Usuario admin creado: admin/admin123")
        print(f"✓ Todos los datos existentes fueron asignados al usuario admin")
        
    except Exception as e:
        print(f"✗ Error durante la migración: {e}")
        con.rollback()
        raise
    
    finally:
        con.close()

if __name__ == "__main__":
    migrate_database()
