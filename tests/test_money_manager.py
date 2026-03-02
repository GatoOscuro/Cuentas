import tempfile
import unittest
from pathlib import Path

from money_manager import FinanceManager


class FinanceManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db_path = Path("test_finanzas.db")
        if self.db_path.exists():
            self.db_path.unlink()
        self.manager = FinanceManager(self.db_path)

    def tearDown(self) -> None:
        if self.db_path.exists():
            self.db_path.unlink()

    def test_running_balance_column(self) -> None:
        self.manager.add_movement("Sueldo", "ingreso", 1500, "2026-01-01")
        self.manager.add_movement("Comida", "gasto", 120, "2026-01-02")
        self.manager.add_movement("Freelance", "ingreso", 300, "2026-01-03")

        movimientos = self.manager.list_movements()

        self.assertEqual([m.saldo_acumulado for m in movimientos], [1500.0, 1380.0, 1680.0])

    def test_current_balance(self) -> None:
        self.manager.add_movement("Sueldo", "ingreso", 1000, "2026-01-02")
        self.manager.add_movement("Transporte", "gasto", 250, "2026-01-03")
        self.assertEqual(self.manager.current_balance(), 750)

    def test_import_from_csv(self) -> None:
        csv_data = (
            "concepto,tipo,valor,fecha,categoria,detalle\n"
            "Salario,ingreso,2000,2026-02-01,Trabajo,Pago mensual\n"
            "Mercado,gasto,450,2026-02-02,Comida,Supermercado\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "movimientos.csv"
            csv_path.write_text(csv_data, encoding="utf-8")
            inserted = self.manager.import_from_csv(csv_path)

        self.assertEqual(inserted, 2)
        self.assertEqual(len(self.manager.list_movements()), 2)


if __name__ == "__main__":
    unittest.main()
