from __future__ import annotations

import html
import shutil
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

from money_manager import FinanceManager

manager = FinanceManager()


def _render_page(message: str = "") -> str:
    rows = manager.list_movements()
    saldo_actual = manager.current_balance()
    msg_html = f'<p style="color:#0a7">{html.escape(message)}</p>' if message else ""

    table_rows = ""
    for m in rows:
        sign = "+" if m.tipo == "ingreso" else "-"
        color = "#1a7f37" if m.tipo == "ingreso" else "#cf222e"
        table_rows += (
            "<tr>"
            f"<td>{html.escape(m.concepto)}</td>"
            f"<td style='color:{color}'>{sign}${m.valor:.2f}</td>"
            f"<td><b>${m.saldo_acumulado:.2f}</b></td>"
            f"<td>{m.fecha}</td>"
            f"<td>{m.tipo}</td>"
            f"<td>{html.escape(m.categoria)}</td>"
            f"<td>{html.escape(m.detalle)}</td>"
            "</tr>"
        )

    if not table_rows:
        table_rows = "<tr><td colspan='7'>Aún no hay movimientos.</td></tr>"

    return f"""
<!doctype html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Mi bolsillo</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 1rem; }}
    .grid {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap:1rem; }}
    section {{ border:1px solid #ddd; border-radius:8px; padding:1rem; }}
    input, select, textarea, button {{ width:100%; padding:0.5rem; margin:0.25rem 0 0.75rem; }}
    table {{ width:100%; border-collapse: collapse; font-size: 0.92rem; }}
    th, td {{ border:1px solid #ddd; padding:0.4rem; text-align:left; }}
  </style>
</head>
<body>
  <h1>Gestión de dinero de bolsillo</h1>
  <p>Saldo actual: <b>${saldo_actual:.2f}</b></p>
  {msg_html}

  <div class="grid">
    <section>
      <h3>Nuevo movimiento</h3>
      <form method="post" action="/movimientos">
        <label>Concepto</label>
        <input name="concepto" required placeholder="Ej: Almuerzo, Sueldo" />
        <label>Tipo</label>
        <select name="tipo" required>
          <option value="ingreso">Ingreso</option>
          <option value="gasto">Gasto</option>
        </select>
        <label>Valor</label>
        <input name="valor" type="number" step="0.01" min="0.01" required />
        <label>Fecha</label>
        <input name="fecha" type="date" required />
        <label>Categoría</label>
        <input name="categoria" />
        <label>Detalle</label>
        <input name="detalle" />
        <button type="submit">Guardar</button>
      </form>
    </section>

    <section>
      <h3>Importar desde Excel (pegando CSV)</h3>
      <p>Encabezados: <code>concepto,tipo,valor,fecha,categoria,detalle</code></p>
      <form method="post" action="/importar-texto">
        <textarea name="csv_text" rows="10" placeholder="concepto,tipo,valor,fecha,categoria,detalle"></textarea>
        <button type="submit">Importar</button>
      </form>
      <a href="/backup">Descargar backup de datos</a>
    </section>
  </div>

  <h3>Histórico (estilo Excel)</h3>
  <table>
    <thead>
      <tr><th>Concepto</th><th>Valor</th><th>Saldo acumulado</th><th>Fecha</th><th>Tipo</th><th>Categoría</th><th>Detalle</th></tr>
    </thead>
    <tbody>{table_rows}</tbody>
  </table>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/":
            msg = parse_qs(parsed.query).get("msg", [""])[0]
            content = _render_page(msg)
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(content.encode("utf-8"))
            return

        if parsed.path == "/backup":
            backup_path = manager.create_backup()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header(
                "Content-Disposition", f"attachment; filename={backup_path.name}"
            )
            self.end_headers()
            with backup_path.open("rb") as f:
                shutil.copyfileobj(f, self.wfile)
            return

        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        data = {k: v[0] for k, v in parse_qs(raw).items()}

        try:
            if self.path == "/movimientos":
                manager.add_movement(
                    concepto=data.get("concepto", ""),
                    tipo=data.get("tipo", ""),
                    valor=float(data.get("valor", "0")),
                    fecha=data.get("fecha", ""),
                    categoria=data.get("categoria", ""),
                    detalle=data.get("detalle", ""),
                )
                msg = "Movimiento registrado"
            elif self.path == "/importar-texto":
                text = data.get("csv_text", "").strip()
                if not text:
                    raise ValueError("Debes pegar contenido CSV")
                tmp = Path("_import_tmp.csv")
                tmp.write_text(text, encoding="utf-8")
                inserted = manager.import_from_csv(tmp)
                tmp.unlink(missing_ok=True)
                msg = f"Importación completada: {inserted} movimientos"
            else:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
        except Exception as exc:
            msg = f"Error: {exc}"

        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", f"/?{urlencode({'msg': msg})}")
        self.end_headers()


def run() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", 8000), Handler)
    print("Servidor iniciado en http://0.0.0.0:8000")
    server.serve_forever()


if __name__ == "__main__":
    run()
