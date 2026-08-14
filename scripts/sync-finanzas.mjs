#!/usr/bin/env node
/**
 * Sincroniza la contabilidad desde Google Sheets hacia src/data/movimientos.json.
 *
 *   pnpm sync:finanzas                      # baja el CSV publicado (FINANZAS_CSV_URL)
 *   pnpm sync:finanzas --archivo ruta.csv   # usa un CSV local (migración / pruebas)
 *   pnpm sync:finanzas --permitir-descartes # no falla aunque haya filas ilegibles
 *
 * Para obtener la URL: en el Sheet, Archivo -> Compartir -> Publicar en la web
 * -> elegir la hoja «Movimientos» -> formato CSV. Copiar el enlace resultante a
 * la variable de entorno FINANZAS_CSV_URL (o a .env.local).
 *
 * El script falla con código 1 si encuentra filas que no puede leer. Es
 * deliberado: es preferible una sincronización rota y visible a un dashboard
 * que grafica datos incompletos en silencio.
 */
import { writeFileSync, readFileSync, mkdirSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { normalizar } from './lib/normalizar.mjs'

const RAIZ = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const DESTINO = resolve(RAIZ, 'src/data/movimientos.json')

function leerArgumentos(argv) {
  const args = { archivo: null, permitirDescartes: false }
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--archivo') args.archivo = argv[++i]
    else if (argv[i] === '--permitir-descartes') args.permitirDescartes = true
  }
  return args
}

async function obtenerCSV({ archivo }) {
  if (archivo) {
    const ruta = resolve(process.cwd(), archivo)
    return { csv: readFileSync(ruta, 'utf-8'), fuente: `archivo local: ${archivo}` }
  }

  const url = process.env.FINANZAS_CSV_URL
  if (!url) {
    throw new Error(
      'Falta FINANZAS_CSV_URL.\n\n' +
        'Publicá la hoja «Movimientos» del Sheet como CSV\n' +
        '(Archivo -> Compartir -> Publicar en la web -> CSV) y exportá la URL:\n\n' +
        '  export FINANZAS_CSV_URL="https://docs.google.com/spreadsheets/d/e/.../pub?output=csv"\n\n' +
        'O pasá un CSV local con --archivo ruta.csv',
    )
  }

  const respuesta = await fetch(url, { redirect: 'follow' })
  if (!respuesta.ok) {
    throw new Error(`El Sheet respondió ${respuesta.status} ${respuesta.statusText}. ¿Sigue publicado?`)
  }
  const csv = await respuesta.text()
  if (csv.trimStart().startsWith('<')) {
    throw new Error(
      'La URL devolvió HTML en lugar de CSV. Suele pasar cuando se copia el enlace\n' +
        'de edición en vez del de publicación. Verificá que termine en «output=csv».',
    )
  }
  return { csv, fuente: 'Google Sheets (publicado como CSV)' }
}

async function main() {
  const args = leerArgumentos(process.argv.slice(2))
  const { csv, fuente } = await obtenerCSV(args)
  const { saldoInicial, movimientos, avisos, descartadas } = normalizar(csv, { fuente })

  if (!movimientos.length) throw new Error('No se pudo leer ningún movimiento del CSV.')

  const ingresos = movimientos.filter((m) => m.flujo === 'Ingreso').reduce((s, m) => s + m.montoUSD, 0)
  const egresos = movimientos.filter((m) => m.flujo === 'Egreso').reduce((s, m) => s + m.montoUSD, 0)
  const aRevisar = movimientos.filter((m) => m.revisar)

  const salida = {
    generado: new Date().toISOString(),
    fuente,
    saldoInicial,
    totales: {
      ingresos: Number(ingresos.toFixed(2)),
      egresos: Number(egresos.toFixed(2)),
      saldoActual: Number((saldoInicial + ingresos - egresos).toFixed(2)),
      movimientos: movimientos.length,
      porRevisar: aRevisar.length,
    },
    movimientos,
    avisos,
  }

  mkdirSync(dirname(DESTINO), { recursive: true })
  writeFileSync(DESTINO, `${JSON.stringify(salida, null, 2)}\n`, 'utf-8')

  const fmt = (n) => `$${n.toFixed(2)}`
  console.log(`\n  Fuente:            ${fuente}`)
  console.log(`  Movimientos:       ${movimientos.length}`)
  console.log(`  Rango:             ${movimientos[0].fecha} → ${movimientos.at(-1).fecha}`)
  console.log(`  Saldo inicial:     ${fmt(saldoInicial)}`)
  console.log(`  Ingresos:          ${fmt(ingresos)}`)
  console.log(`  Egresos:           ${fmt(egresos)}`)
  console.log(`  Saldo actual:      ${fmt(salida.totales.saldoActual)}`)
  console.log(`  Escrito en:        ${DESTINO.replace(RAIZ + '/', '')}\n`)

  if (avisos.length) {
    console.log(`  ${avisos.length} aviso(s):`)
    for (const a of avisos.slice(0, 10)) console.log(`    · línea ${a.linea}: ${a.mensaje}`)
    if (avisos.length > 10) console.log(`    · … y ${avisos.length - 10} más`)
    console.log('')
  }

  if (aRevisar.length) {
    const porMotivo = new Map()
    for (const m of aRevisar) porMotivo.set(m.motivoRevision, (porMotivo.get(m.motivoRevision) ?? 0) + 1)
    console.log(`  ${aRevisar.length} movimiento(s) sin clasificar, por grupo:`)
    for (const [motivo, n] of [...porMotivo].sort((a, b) => b[1] - a[1])) {
      console.log(`    · ${n.toString().padStart(3)} — ${motivo}`)
    }
    console.log('')
  }

  if (descartadas.length) {
    console.error(`  ${descartadas.length} fila(s) DESCARTADAS por ilegibles:`)
    for (const d of descartadas) console.error(`    · línea ${d.linea}: ${d.razon} → ${JSON.stringify(d.fila)}`)
    if (!args.permitirDescartes) {
      console.error(
        '\n  Sincronización abortada. Corregí esas filas en el Sheet y volvé a correr,\n' +
          '  o usá --permitir-descartes si querés generar el JSON igual.\n',
      )
      process.exit(1)
    }
    console.error('  (--permitir-descartes activo: el JSON se generó sin esas filas)\n')
  }
}

main().catch((e) => {
  console.error(`\n  Error: ${e.message}\n`)
  process.exit(1)
})
