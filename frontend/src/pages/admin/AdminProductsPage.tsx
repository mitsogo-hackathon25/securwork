import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  bulkDeleteAdminProducts,
  deleteAdminProduct,
  downloadProductCsvTemplate,
  exportProductsCsv,
  fetchAdminProducts,
  importProductsCsvWithProgress,
  updateAdminProduct,
  type CsvImportError,
  type CsvImportProgressEvent,
} from '../../api/admin'
import { formatPrice } from '../../utils/format'
import { formatApiError } from '../../utils/formatApiError'
import './Admin.css'

export default function AdminProductsPage() {
  const queryClient = useQueryClient()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [page, setPage] = useState(1)
  const [importing, setImporting] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [importSuccess, setImportSuccess] = useState('')
  const [importErrors, setImportErrors] = useState<CsvImportError[]>([])
  const [importDetail, setImportDetail] = useState('')
  const [importProgress, setImportProgress] = useState<CsvImportProgressEvent | null>(null)
  const [selectedIds, setSelectedIds] = useState<number[]>([])
  const [bulkDeleting, setBulkDeleting] = useState(false)

  const params: Record<string, string | number | boolean> = { page, ordering: '-updated_at' }
  if (search) params.search = search
  if (statusFilter === 'active') params.is_active = true
  if (statusFilter === 'inactive') params.is_active = false

  const { data, isLoading } = useQuery({
    queryKey: ['admin-products', params],
    queryFn: () => fetchAdminProducts(params),
  })

  const deleteMutation = useMutation({
    mutationFn: deleteAdminProduct,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-products'] }),
  })

  const deactivateMutation = useMutation({
    mutationFn: (id: number) => updateAdminProduct(id, { is_active: false }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-products'] }),
  })

  const products = data?.results ?? []
  const totalPages = data ? Math.ceil(data.count / 12) : 1
  const pageIds = products.map((p) => p.id)
  const allOnPageSelected = pageIds.length > 0 && pageIds.every((id) => selectedIds.includes(id))

  const toggleSelectAllOnPage = () => {
    if (allOnPageSelected) {
      setSelectedIds((prev) => prev.filter((id) => !pageIds.includes(id)))
      return
    }
    setSelectedIds((prev) => [...new Set([...prev, ...pageIds])])
  }

  const toggleSelectProduct = (id: number) => {
    setSelectedIds((prev) => (
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    ))
  }

  const importProgressPercent = (() => {
    if (!importProgress?.total || importProgress.total <= 0) return 0
    const current = importProgress.current ?? 0
    return Math.min(100, Math.round((current / importProgress.total) * 100))
  })()

  const deactivateProduct = async (id: number, name: string) => {
    setImportDetail('')
    setImportSuccess('')
    await deactivateMutation.mutateAsync(id)
    setImportSuccess(`"${name}" disattivato.`)
  }

  const handleDeactivate = async (id: number, name: string) => {
    if (!window.confirm(`Disattivare "${name}"? Non sarà più visibile nel negozio.`)) return
    try {
      await deactivateProduct(id, name)
    } catch (err: unknown) {
      setImportDetail(formatApiError(err, 'Impossibile disattivare il prodotto.'))
    }
  }

  const handleDelete = async (id: number, name: string) => {
    if (!window.confirm(`Eliminare "${name}"? L'operazione non può essere annullata.`)) return
    setImportDetail('')
    setImportSuccess('')
    try {
      await deleteMutation.mutateAsync(id)
    } catch (err: unknown) {
      const responseData = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string; code?: string } } }).response?.data
        : undefined
      if (responseData?.code === 'product_has_orders') {
        const deactivate = window.confirm(
          `${responseData.detail || 'Prodotto collegato a ordini.'}\n\nVuoi disattivarlo ora?`,
        )
        if (deactivate) {
          try {
            await deactivateProduct(id, name)
          } catch (deactivateErr: unknown) {
            setImportDetail(formatApiError(deactivateErr, 'Impossibile disattivare il prodotto.'))
          }
        }
        return
      }
      setImportDetail(formatApiError(err, 'Impossibile eliminare il prodotto.'))
    }
  }

  const handleDownloadTemplate = async () => {
    setImportDetail('')
    setImportErrors([])
    setImportSuccess('')
    try {
      await downloadProductCsvTemplate()
    } catch (err: unknown) {
      setImportDetail(formatApiError(err, 'Impossibile scaricare il modello CSV.'))
    }
  }

  const handleExportCsv = async () => {
    setImportDetail('')
    setImportErrors([])
    setImportSuccess('')
    setExporting(true)
    try {
      await exportProductsCsv()
    } catch (err: unknown) {
      setImportDetail(formatApiError(err, 'Impossibile esportare i prodotti in CSV.'))
    } finally {
      setExporting(false)
    }
  }

  const handleImportFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return

    setImporting(true)
    setImportSuccess('')
    setImportErrors([])
    setImportDetail('')
    setImportProgress({ phase: 'uploading', current: 0, total: 100, message: 'Caricamento file…' })
    try {
      const result = await importProductsCsvWithProgress(
        file,
        (event) => setImportProgress(event),
        (percent) => setImportProgress({
          phase: 'uploading',
          current: percent,
          total: 100,
          message: `Caricamento file… ${percent}%`,
        }),
      )
      setImportSuccess(result.detail)
      setImportProgress({ phase: 'done', current: 100, total: 100, message: result.detail })
      queryClient.invalidateQueries({ queryKey: ['admin-products'] })
    } catch (err: unknown) {
      const responseData = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string; errors?: CsvImportError[] } } }).response?.data
        : undefined
      if (responseData?.errors?.length) {
        setImportDetail(responseData.detail || 'Validazione CSV non riuscita.')
        setImportErrors(responseData.errors)
      } else {
        setImportDetail(formatApiError(err, 'Impossibile importare il CSV.'))
      }
    } finally {
      setImporting(false)
    }
  }

  const handleBulkDelete = async () => {
    if (selectedIds.length === 0) return
    const count = selectedIds.length
    if (!window.confirm(
      `Eliminare ${count} prodott${count === 1 ? 'o' : 'i'} selezionat${count === 1 ? 'o' : 'i'}? L'operazione non può essere annullata.`,
    )) return

    setBulkDeleting(true)
    setImportDetail('')
    setImportSuccess('')
    try {
      const result = await bulkDeleteAdminProducts(selectedIds)
      setSelectedIds((prev) => prev.filter((id) => !result.deleted.includes(id)))
      if (result.blocked.length > 0) {
        const names = result.blocked.slice(0, 5).map((b) => b.name).join(', ')
        const more = result.blocked.length > 5 ? ` (+${result.blocked.length - 5} altri)` : ''
        setImportDetail(
          `${result.detail} Non eliminati (ordini collegati): ${names}${more}.`,
        )
      }
      if (result.deleted.length > 0) {
        setImportSuccess(result.detail)
      } else if (!result.blocked.length) {
        setImportDetail(result.detail)
      }
      queryClient.invalidateQueries({ queryKey: ['admin-products'] })
    } catch (err: unknown) {
      setImportDetail(formatApiError(err, 'Impossibile eliminare i prodotti selezionati.'))
    } finally {
      setBulkDeleting(false)
    }
  }

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <h1>Prodotti</h1>
          <p>Gestisci catalogo, magazzino, prezzi e descrizioni.</p>
        </div>
        <div className="admin-header-actions">
          <button type="button" className="btn btn-secondary" onClick={handleDownloadTemplate}>
            Scarica modello CSV
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            disabled={exporting}
            onClick={handleExportCsv}
          >
            {exporting ? 'Esportazione…' : 'Esporta CSV'}
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            disabled={importing}
            onClick={() => fileInputRef.current?.click()}
          >
            {importing ? 'Importazione…' : 'Importa CSV'}
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,text/csv"
            className="admin-file-input"
            onChange={handleImportFile}
          />
          <Link to="/admin/products/new" className="btn btn-primary">Aggiungi prodotto</Link>
        </div>
      </div>

      <section className="admin-card admin-import-panel">
        <h2>Import / export massivo</h2>
        <p className="admin-hint">
          L&apos;export scarica tutti i prodotti attuali (una riga per taglia/colore). Scarica il modello
          per iniziare da zero, oppure modifica un export e reimporta nuovi prodotti. Colonne obbligatorie
          principali: <strong>marca</strong> (brand), <strong>categoria</strong> (slug o nome, es. polo o
          T-shirt; anche <code>slug_categorie</code> nel vecchio modello), <strong>colore</strong>, taglia e
          prezzo. Opzionali: <strong>descrizione_breve_it/en</strong>, <strong>bestseller</strong> (si/no),{' '}
          <strong>costo_personalizzazione</strong> (costo base logo sul prodotto). Marche e colori non presenti
          nel catalogo vengono creati automaticamente. Nel modello standard il nome italiano (nome_it)
          deve essere univoco; nel listino fornitore il prodotto è identificato dal{' '}
          <strong>Codice Padre</strong> (più righe = taglie/colori, descrizioni uguali o diverse).
          Per la personalizzazione logo usa: ricamo_petto, costo_ricamo_petto, ricamo_grande,
          costo_ricamo_grande, dtf_petto, costo_dtf_petto, dtf_grande, costo_dtf_grande (si/no + prezzo).
          Per le immagini usa url_immagini (URL pubblici separati da virgola; il primo è principale)
          e opzionalmente url_mockup. È supportato anche il listino fornitore con colonne Codice Padre,
          Merceologica, Categoria, SCategoria, SKU, Colore, Taglia, Descrizione, Foto, Prezzo Unico
          (Confezione/Imballo usati solo se manca il prezzo unitario; scorte = In Arrivo se numerico,
          altrimenti 0). Righe senza prezzo nel listino fornitore vengono saltate. Righe duplicate con lo
          stesso SKU variante vengono unite (resta l&apos;ultima).
        </p>
        {(importing || importProgress?.phase === 'done') && importProgress && (
          <div className="admin-import-progress" aria-live="polite">
            <div className="admin-import-progress-label">
              {importProgress.message || 'Import in corso…'}
              {importProgress.phase === 'importing' && importProgress.product_sku && (
                <span className="admin-import-progress-sku"> ({importProgress.product_sku})</span>
              )}
            </div>
            <div className="admin-import-progress-track">
              <div
                className="admin-import-progress-bar"
                style={{ width: `${importProgressPercent}%` }}
              />
            </div>
            {importProgress.total ? (
              <span className="admin-import-progress-meta">
                {importProgress.current ?? 0} / {importProgress.total}
                {importProgress.phase === 'validating' ? ' righe' : ''}
                {importProgress.phase === 'importing' ? ' prodotti' : ''}
              </span>
            ) : null}
          </div>
        )}
        {importSuccess && <p className="admin-alert admin-alert-success">{importSuccess}</p>}
        {importDetail && !importSuccess && (
          <p className="admin-alert admin-alert-error">{importDetail}</p>
        )}
        {importErrors.length > 0 && (
          <div className="admin-import-errors">
            <strong>{importErrors.length} error{importErrors.length === 1 ? 'e' : 'i'} trovat{importErrors.length === 1 ? 'o' : 'i'}</strong>
            <ul>
              {importErrors.map((error, index) => (
                <li key={`${error.row}-${error.field}-${index}`}>
                  {error.row > 0 ? (
                    <>
                      Riga {error.row}
                      {error.field ? ` · ${error.field}` : ''}: {error.message}
                    </>
                  ) : (
                    error.message
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}
      </section>

      <div className="admin-toolbar">
        <input
          type="search"
          placeholder="Cerca per nome, SKU o slug…"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1) }}
        />
        <select value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1) }}>
          <option value="all">Tutti gli stati</option>
          <option value="active">Solo attivi</option>
          <option value="inactive">Solo inattivi</option>
        </select>
      </div>

      <div className="admin-bulk-bar">
        <p className="admin-bulk-hint">
          <strong>Eliminazione multipla:</strong> seleziona i prodotti con le caselle nella prima colonna
          della tabella (intestazione = tutta la pagina). Se la tabella è larga, scorri leggermente a sinistra.
        </p>
        <div className="admin-bulk-actions">
          <span className="admin-bulk-count">
            {selectedIds.length} selezionat{selectedIds.length === 1 ? 'o' : 'i'}
          </span>
          <button
            type="button"
            className="btn btn-secondary"
            disabled={selectedIds.length === 0}
            onClick={() => setSelectedIds([])}
          >
            Deseleziona tutto
          </button>
          <button
            type="button"
            className="btn btn-secondary admin-bulk-delete-btn"
            disabled={selectedIds.length === 0 || bulkDeleting}
            onClick={handleBulkDelete}
          >
            {bulkDeleting ? 'Eliminazione…' : 'Elimina selezionati'}
          </button>
        </div>
      </div>

      {isLoading ? (
        <p>Caricamento prodotti…</p>
      ) : (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th className="admin-table-check" scope="col">
                  <span className="admin-table-check-label">Sel.</span>
                  <input
                    type="checkbox"
                    className="admin-table-checkbox"
                    aria-label="Seleziona tutti i prodotti in questa pagina"
                    checked={allOnPageSelected}
                    onChange={toggleSelectAllOnPage}
                  />
                </th>
                <th>Prodotto</th>
                <th>SKU</th>
                <th>Prezzo</th>
                <th>Scorte</th>
                <th>Stato</th>
                <th>Flag</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {products.length === 0 ? (
                <tr>
                  <td colSpan={8} className="admin-empty">Nessun prodotto trovato.</td>
                </tr>
              ) : products.map((product) => (
                <tr key={product.id}>
                  <td className="admin-table-check">
                    <input
                      type="checkbox"
                      className="admin-table-checkbox"
                      aria-label={`Seleziona ${product.name}`}
                      checked={selectedIds.includes(product.id)}
                      onChange={() => toggleSelectProduct(product.id)}
                    />
                  </td>
                  <td>
                    <div className="admin-product-cell">
                      {product.primary_image ? (
                        <img src={product.primary_image} alt="" />
                      ) : (
                        <div className="admin-product-thumb-placeholder" />
                      )}
                      <div>
                        <strong>{product.name}</strong>
                        <span>{product.slug}</span>
                      </div>
                    </div>
                  </td>
                  <td>{product.sku}</td>
                  <td>{product.min_price ? formatPrice(product.min_price) : '—'}</td>
                  <td>
                    <span className={product.in_stock ? 'admin-stock-ok' : 'admin-stock-out'}>
                      {product.total_stock}
                    </span>
                  </td>
                  <td>
                    <span className={`admin-badge ${product.is_active ? 'admin-badge-success' : 'admin-badge-muted'}`}>
                      {product.is_active ? 'Attivo' : 'Inattivo'}
                    </span>
                  </td>
                  <td>
                    <div className="admin-flags">
                      {product.is_featured && <span className="admin-flag">In evidenza</span>}
                      {product.is_new_arrival && <span className="admin-flag">Nuovo</span>}
                      {product.is_bestseller && <span className="admin-flag">Best</span>}
                    </div>
                  </td>
                  <td className="admin-actions">
                    <Link to={`/admin/products/${product.id}`} className="admin-link">Modifica</Link>
                    {product.is_active && (
                      <button
                        type="button"
                        className="admin-link"
                        onClick={() => handleDeactivate(product.id, product.name)}
                      >
                        Disattiva
                      </button>
                    )}
                    <button
                      type="button"
                      className="admin-link admin-link-danger"
                      onClick={() => handleDelete(product.id, product.name)}
                    >
                      Elimina
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {totalPages > 1 && (
        <div className="admin-pagination">
          <button type="button" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Precedente</button>
          <span>Pagina {page} di {totalPages}</span>
          <button type="button" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>Successiva</button>
        </div>
      )}
    </div>
  )
}
