import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  deleteAdminProduct,
  downloadProductCsvTemplate,
  exportProductsCsv,
  fetchAdminProducts,
  importProductsCsv,
  type CsvImportError,
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

  const products = data?.results ?? []
  const totalPages = data ? Math.ceil(data.count / 12) : 1

  const handleDelete = async (id: number, name: string) => {
    if (!window.confirm(`Eliminare "${name}"? L'operazione non può essere annullata.`)) return
    await deleteMutation.mutateAsync(id)
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
    try {
      const result = await importProductsCsv(file)
      setImportSuccess(result.detail)
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
          per iniziare da zero, oppure modifica un export e reimporta solo nuovi SKU. Marche e colori
          devono corrispondere esattamente al Catalogo. Taglie ammesse: XS, S, M, L, XL, XXL, XXXL, 4XL.
          Per la personalizzazione logo usa: ricamo_petto, costo_ricamo_petto, ricamo_grande,
          costo_ricamo_grande, dtf_petto, costo_dtf_petto, dtf_grande, costo_dtf_grande (si/no + prezzo).
          Per le immagini usa url_immagini (URL pubblici separati da virgola; il primo è principale)
          e opzionalmente url_mockup.
        </p>
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

      {isLoading ? (
        <p>Caricamento prodotti…</p>
      ) : (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
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
                  <td colSpan={7} className="admin-empty">Nessun prodotto trovato.</td>
                </tr>
              ) : products.map((product) => (
                <tr key={product.id}>
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
