from __future__ import annotations

import csv
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Optional

DB_PATH = Path("finanzas.db")
BACKUP_DIR = Path("backups")


@dataclass
class Movement:
    id: int
    concepto: str
    tipo: str
    valor: float
    fecha: str
    categoria: str
    detalle: str
    saldo_acumulado: float


class FinanceManager:
    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = db_path
        self._ensure_db()
        self._configure_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _configure_db(self) -> None:
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA foreign_keys=ON;")

    def _ensure_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS movimientos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    concepto TEXT NOT NULL,
                    tipo TEXT NOT NULL CHECK (tipo IN ('ingreso', 'gasto')),
                    valor REAL NOT NULL CHECK (valor > 0),
                    fecha TEXT NOT NULL,
                    categoria TEXT NOT NULL DEFAULT '',
                    detalle TEXT NOT NULL DEFAULT '',
                    creado_en TEXT NOT NULL DEFAULT (datetime('now'))
                )
                """
            )

    def add_movement(
        self,
        concepto: str,
        tipo: str,
        valor: float,
        fecha: Optional[str],
        categoria: str = "",
        detalle: str = "",
    ) -> int:
        concepto = concepto.strip()
        if not concepto:
            raise ValueError("El concepto es obligatorio.")

        tipo = tipo.strip().lower()
        if tipo not in {"ingreso", "gasto"}:
            raise ValueError("El tipo debe ser ingreso o gasto.")

        if valor <= 0:
            raise ValueError("El valor debe ser mayor a cero.")

        fecha_normalizada = self._normalize_date(fecha)

        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO movimientos (concepto, tipo, valor, fecha, categoria, detalle)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    concepto,
                    tipo,
                    float(valor),
                    fecha_normalizada,
                    categoria.strip(),
                    detalle.strip(),
                ),
            )
            return int(cursor.lastrowid)

    def list_movements(self) -> list[Movement]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, concepto, tipo, valor, fecha, categoria, detalle
                FROM movimientos
                ORDER BY fecha ASC, id ASC
                """
            ).fetchall()

        saldo = 0.0
        movimientos: list[Movement] = []
        for row in rows:
            delta = row["valor"] if row["tipo"] == "ingreso" else -row["valor"]
            saldo += float(delta)
            movimientos.append(
                Movement(
                    id=row["id"],
                    concepto=row["concepto"],
                    tipo=row["tipo"],
                    valor=float(row["valor"]),
                    fecha=row["fecha"],
                    categoria=row["categoria"],
                    detalle=row["detalle"],
                    saldo_acumulado=saldo,
                )
            )
        return movimientos

    def current_balance(self) -> float:
        with self._connect() as conn:
            ingresos = conn.execute(
                "SELECT COALESCE(SUM(valor), 0) FROM movimientos WHERE tipo='ingreso'"
            ).fetchone()[0]
            gastos = conn.execute(
                "SELECT COALESCE(SUM(valor), 0) FROM movimientos WHERE tipo='gasto'"
            ).fetchone()[0]
        return float(ingresos - gastos)

    def import_from_csv(self, csv_path: Path) -> int:
        inserted = 0
        with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            required = {"concepto", "tipo", "valor", "fecha"}
            if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
                raise ValueError(
                    "El CSV debe incluir columnas: concepto,tipo,valor,fecha"
                )
            for row in reader:
                self.add_movement(
                    concepto=row.get("concepto", ""),
                    tipo=row.get("tipo", ""),
                    valor=float(row.get("valor", 0)),
                    fecha=row.get("fecha", ""),
                    categoria=row.get("categoria", ""),
                    detalle=row.get("detalle", ""),
                )
                inserted += 1
        return inserted

    def create_backup(self) -> Path:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = BACKUP_DIR / f"finanzas_{ts}.db"
        shutil.copy2(self.db_path, backup_path)
        return backup_path

    @staticmethod
    def _normalize_date(fecha: Optional[str]) -> str:
        if not fecha:
            return date.today().isoformat()
        try:
            return datetime.strptime(fecha, "%Y-%m-%d").date().isoformat()
        except ValueError as exc:
            raise ValueError("La fecha debe usar formato YYYY-MM-DD") from exc
