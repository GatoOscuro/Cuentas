# App visual para gestión de dinero de bolsillo

Esta aplicación reemplaza una hoja de Excel por una interfaz web simple para registrar ingresos y gastos, ver el saldo acumulado por movimiento y conservar los datos localmente.

## Objetivos cubiertos

- **Sencilla de usar:** formulario único + tabla histórica.
- **Visual tipo Excel:** columnas de concepto, valor, saldo acumulado, fecha, tipo, categoría y detalle.
- **Persistencia real:** SQLite (`finanzas.db`) en disco.
- **Portable y multidispositivo:** app web accesible desde PC o celular en la misma red.
- **Seguridad de datos:** consultas parametrizadas en SQLite, modo WAL y backup descargable.
- **Sin dependencias externas:** solo Python estándar.

## Ejecución

```bash
python app.py
```

Abre: `http://localhost:8000`

Para usarla desde otro dispositivo en la misma red: `http://IP_DE_TU_PC:8000`.

## Importar cuentas desde Excel

1. Exporta tu archivo Excel a CSV.
2. Copia el contenido y pégalo en la sección **Importar desde Excel (pegando CSV)**.
3. Encabezados requeridos:

```text
concepto,tipo,valor,fecha,categoria,detalle
```

- `tipo`: `ingreso` o `gasto`
- `fecha`: formato `YYYY-MM-DD`

## Estructura principal

- `app.py`: interfaz web HTTP.
- `money_manager.py`: lógica de negocio + persistencia SQLite.
- `tests/test_money_manager.py`: pruebas de saldo acumulado, balance e importación CSV.
