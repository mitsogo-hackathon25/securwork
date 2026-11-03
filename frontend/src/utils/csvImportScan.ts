/**
 * Browser-side CSV column/value scan for admin import (no server upload — avoids nginx body limits).
 * Header keys align with backend store/csv_import.py for filter matching on import.
 */

export type CsvScanColumn = { key: string; label: string }

export type CsvScanValue = {
  key: string
  name: string
  product_count: number
  row_count: number
}

const BRAND_FILTER_NONE = '__none__'

const HEADER_ALIASES: Record<string, string> = {
  codice_padre: 'sku_prodotto',
  codicepadre: 'sku_prodotto',
  sku: 'sku_variante',
  arrivo: 'in_arrivo',
  in_arrivo: 'in_arrivo',
  descrizione: 'descrizione_it',
  foto: 'url_immagini',
  prezzo_unico: 'prezzo_unico',
  prezzo_confezione: 'prezzo_confezione',
  prezzo_imballo: 'prezzo_imballo',
  scategoria: 'scategoria',
  merceologica: 'merceologica',
  categoria: 'categoria',
  colore: 'colore',
  taglia: 'taglia',
  ean: 'ean',
  prezzo: 'prezzo',
  marca: 'marca',
}

const SUPPLIER_MARKERS = new Set([
  'sku_prodotto',
  'sku_variante',
  'prezzo',
  'prezzo_unico',
  'merceologica',
  'scategoria',
  'in_arrivo',
  'descrizione_it',
])

function headerKey(value: string): string {
  let text = (value || '').trim().toLowerCase()
  text = text.normalize('NFD').replace(/[\u0300-\u036f]/g, '')
  text = text.replace(/[\s-]+/g, '_').replace(/[^a-z0-9_]/g, '')
  return text
}

function normalizeHeader(value: string): string {
  const k = headerKey(value)
  return HEADER_ALIASES[k] ?? k
}

function canonicalFilterKey(raw: string): string {
  if (!raw?.trim()) return BRAND_FILTER_NONE
  let text = raw.trim().toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '')
  text = text.replace(/\s+/g, '')
  return text || BRAND_FILTER_NONE
}

function prepareCsvText(text: string): string {
  let t = text.replace(/^\ufeff/, '')
  const lines = t.split(/\r\n|\n|\r/)
  while (lines.length && !lines[0].trim()) lines.shift()
  return lines.join('\n')
}

function countFields(line: string, delimiter: string): number {
  return parseCsvLine(line, delimiter).length
}

function pickDelimiter(text: string): string {
  const lines = text.split(/\r\n|\n|\r/).filter((l) => l.trim())
  if (!lines.length) return ','
  const header = lines[0]
  let best = ','
  let bestCount = 0
  for (const d of ['\t', ';', ',', '|']) {
    const n = countFields(header, d)
    if (n > bestCount) {
      bestCount = n
      best = d
    }
  }
  return bestCount > 1 ? best : ','
}

function parseCsvLine(line: string, delimiter: string): string[] {
  const out: string[] = []
  let cur = ''
  let inQuotes = false
  for (let i = 0; i < line.length; i += 1) {
    const c = line[i]
    if (c === '"') {
      if (inQuotes && line[i + 1] === '"') {
        cur += '"'
        i += 1
      } else {
        inQuotes = !inQuotes
      }
      continue
    }
    if (!inQuotes && c === delimiter) {
      out.push(cur.trim())
      cur = ''
      continue
    }
    cur += c
  }
  out.push(cur.trim())
  return out
}

async function fileToCsvText(file: File): Promise<string> {
  const buf = new Uint8Array(await file.arrayBuffer())
  if (buf.length >= 2 && buf[0] === 0xff && buf[1] === 0xfe) {
    return prepareCsvText(new TextDecoder('utf-16le').decode(buf))
  }
  if (buf.length >= 2 && buf[0] === 0xfe && buf[1] === 0xff) {
    return prepareCsvText(new TextDecoder('utf-16be').decode(buf))
  }
  let text = new TextDecoder('utf-8').decode(buf)
  if (text.includes('\ufffd')) {
    text = new TextDecoder('iso-8859-1').decode(buf)
  }
  return prepareCsvText(text)
}

function parseCsvTable(text: string): { rawHeaders: string[]; normHeaders: string[]; rows: string[][] } {
  const prepared = prepareCsvText(text)
  const lines = prepared.split(/\n/).filter((l) => l.length > 0)
  if (!lines.length) {
    return { rawHeaders: [], normHeaders: [], rows: [] }
  }
  const delimiter = pickDelimiter(prepared)
  const rawHeaders = parseCsvLine(lines[0], delimiter)
  const normHeaders = rawHeaders.map(normalizeHeader)
  const rows = lines.slice(1).map((line) => parseCsvLine(line, delimiter))
  return { rawHeaders, normHeaders, rows }
}

function rowFromRecord(rawHeaders: string[], normHeaders: string[], cells: string[]): Record<string, string> {
  const row: Record<string, string> = {}
  for (let i = 0; i < rawHeaders.length; i += 1) {
    const nk = normHeaders[i]
    if (!nk) continue
    const val = (cells[i] ?? '').trim()
    row[nk] = row[nk] ? row[nk] : val
  }
  if (!row.sku_prodotto && row.sku_variante) row.sku_prodotto = row.sku_variante
  if (!row.nome_it && row.descrizione_it) row.nome_it = row.descrizione_it
  if (!row.scorte && row.in_arrivo && /^\d+$/.test(row.in_arrivo)) row.scorte = row.in_arrivo
  return row
}

function isSupplierFormat(normHeaders: string[]): boolean {
  const set = new Set(normHeaders)
  for (const m of SUPPLIER_MARKERS) {
    if (set.has(m)) return true
  }
  return set.has('sku_variante') && set.has('descrizione_it')
}

function rowBrandRaw(row: Record<string, string>): string {
  if (row.marca?.trim()) return row.marca.trim()
  const mer = row.merceologica?.trim() ?? ''
  if (mer && mer.length < 40 && !mer.toLowerCase().includes('abbigliamento')) return mer
  return ''
}

function columnCellRaw(row: Record<string, string>, columnKey: string): string {
  if (columnKey === 'marca') {
    return (row.marca?.trim() || rowBrandRaw(row)).trim()
  }
  return (row[columnKey] ?? '').trim()
}

function rowHasIdentity(row: Record<string, string>): boolean {
  if (row.sku_prodotto || row.sku_variante) return true
  if (row.ean) return true
  const name = row.nome_it || row.descrizione_it
  return Boolean(name && row.prezzo)
}

function filterDisplayName(raw: string): string {
  const cleaned = raw.trim()
  return cleaned || '(vuoto)'
}

export async function scanCsvColumnsFromFile(file: File): Promise<CsvScanColumn[]> {
  const text = await fileToCsvText(file)
  const { rawHeaders, normHeaders } = parseCsvTable(text)
  if (!rawHeaders.length) {
    throw new Error('Il CSV non ha una riga di intestazione.')
  }

  const columns: CsvScanColumn[] = []
  const seen = new Set<string>()
  for (let i = 0; i < rawHeaders.length; i += 1) {
    const norm = normHeaders[i]
    if (!norm || seen.has(norm)) continue
    seen.add(norm)
    const label = (rawHeaders[i] || '').trim() || norm
    columns.push({ key: norm, label })
  }

  if (isSupplierFormat(normHeaders) && !seen.has('marca')) {
    columns.push({ key: 'marca', label: 'marca (ricavata dal listino)' })
  }

  columns.sort((a, b) => a.label.localeCompare(b.label, undefined, { sensitivity: 'base' }))
  if (!columns.length) {
    throw new Error('Nessuna colonna riconosciuta nella prima riga del CSV.')
  }
  return columns
}

export async function scanCsvColumnValuesFromFile(
  file: File,
  columnKey: string,
): Promise<CsvScanValue[]> {
  const text = await fileToCsvText(file)
  const { rawHeaders, normHeaders, rows } = parseCsvTable(text)
  if (!normHeaders.includes(columnKey) && columnKey !== 'marca') {
    throw new Error(`Colonna '${columnKey}' non trovata nel CSV.`)
  }

  const productIds: Record<string, Set<string>> = {}
  const rowCounts: Record<string, number> = {}
  const labels: Record<string, string> = {}

  for (const cells of rows) {
    const row = rowFromRecord(rawHeaders, normHeaders, cells)
    if (!rowHasIdentity(row)) continue
    const rawVal = columnCellRaw(row, columnKey)
    const key = rawVal ? canonicalFilterKey(rawVal) : BRAND_FILTER_NONE
    if (!(key in labels)) labels[key] = filterDisplayName(rawVal)
    const productSku = (row.sku_prodotto || row.sku_variante || '').toLowerCase()
    if (!productIds[key]) productIds[key] = new Set()
    if (productSku) productIds[key].add(productSku)
    rowCounts[key] = (rowCounts[key] ?? 0) + 1
  }

  const keys = Object.keys(labels)
  if (!keys.length) {
    throw new Error('Nessuna riga prodotto trovata nel CSV.')
  }

  return keys
    .sort((a, b) => labels[a].localeCompare(labels[b], undefined, { sensitivity: 'base' }))
    .map((key) => ({
      key,
      name: labels[key],
      product_count: productIds[key]?.size ?? 0,
      row_count: rowCounts[key] ?? 0,
    }))
}
