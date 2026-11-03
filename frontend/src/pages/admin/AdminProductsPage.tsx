import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  bulkDeleteAdminProducts,
  deleteAllAdminProducts,
  deleteAdminProduct,
  downloadProductCsvTemplate,
  exportProductsCsv,
  restoreDemoCatalog,
  fetchAdminProducts,
  importProductsCsvWithProgress,
  rollbackCsvImportBatch,
  updateAdminProduct,
  type CsvImportColumnFilter,
  type CsvImportColumnOption,
  type CsvImportError,
  type CsvImportProgressEvent,
  type CsvImportResult,
  type CsvImportValueOption,
} from '../../api/admin'
import {
  CSV_IMPORT_ALL,
  CSV_FILTER_NONE,
  countSelectedImportProducts,
  scanCsvColumnValuesFromFile,
  scanCsvImportPreview,
} from '../../utils/csvImportScan'
import { formatPrice } from '../../utils/format'
import { formatApiError, formatClientError } from '../../utils/formatApiError'
import './Admin.css'

export default function AdminProductsPage() {
  const { t, i18n } = useTranslation()
  const queryClient = useQueryClient()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [page, setPage] = useState(1)
  const [importing, setImporting] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [restoringDemo, setRestoringDemo] = useState(false)
  const [importSuccess, setImportSuccess] = useState('')
  const [importErrors, setImportErrors] = useState<CsvImportError[]>([])
  const [importDetail, setImportDetail] = useState('')
  const [importProgress, setImportProgress] = useState<CsvImportProgressEvent | null>(null)
  const [importBatchId, setImportBatchId] = useState<string | null>(null)
  const [importBatchCreated, setImportBatchCreated] = useState(0)
  const [rollbackImportBusy, setRollbackImportBusy] = useState(false)
  const [selectedIds, setSelectedIds] = useState<number[]>([])
  const [bulkDeleting, setBulkDeleting] = useState(false)
  const [deleteAllBusy, setDeleteAllBusy] = useState(false)
  const [scanningCsv, setScanningCsv] = useState(false)
  const [loadingColumnValues, setLoadingColumnValues] = useState(false)
  const [importModalOpen, setImportModalOpen] = useState(false)
  const [importModalStep, setImportModalStep] = useState<'column' | 'values'>('column')
  const [importColumnOptions, setImportColumnOptions] = useState<CsvImportColumnOption[]>([])
  const [importColumnSelected, setImportColumnSelected] = useState<string | null>(null)
  const [importValueOptions, setImportValueOptions] = useState<CsvImportValueOption[]>([])
  const [importValueSelected, setImportValueSelected] = useState<string[]>([])
  const [pendingImportFile, setPendingImportFile] = useState<File | null>(null)
  const [importCsvStats, setImportCsvStats] = useState<{
    totalDataRows: number
    importableRows: number
  } | null>(null)
  const [selectedImportStats, setSelectedImportStats] = useState<{
    productCount: number
    rowCount: number
  } | null>(null)
  const [selectedImportStatsLoading, setSelectedImportStatsLoading] = useState(false)

  const resetImportModalState = () => {
    setImportModalStep('column')
    setImportColumnOptions([])
    setImportColumnSelected(null)
    setImportValueOptions([])
    setImportValueSelected([])
    setImportCsvStats(null)
    setSelectedImportStats(null)
  }

  useEffect(() => {
    if (
      importModalStep !== 'values'
      || !pendingImportFile
      || !importColumnSelected
      || importColumnSelected === CSV_IMPORT_ALL
    ) {
      setSelectedImportStats(null)
      return
    }
    if (importValueSelected.length === 0) {
      setSelectedImportStats({ productCount: 0, rowCount: 0 })
      return
    }
    let cancelled = false
    setSelectedImportStatsLoading(true)
    void countSelectedImportProducts(
      pendingImportFile,
      importColumnSelected,
      importValueSelected,
    )
      .then((stats) => {
        if (!cancelled) setSelectedImportStats(stats)
      })
      .finally(() => {
        if (!cancelled) setSelectedImportStatsLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [
    importModalStep,
    pendingImportFile,
    importColumnSelected,
    importValueSelected,
  ])

  useEffect(() => {
    const onLanguageChanged = () => {
      setImportModalOpen(false)
      setPendingImportFile(null)
      resetImportModalState()
    }
    i18n.on('languageChanged', onLanguageChanged)
    return () => {
      i18n.off('languageChanged', onLanguageChanged)
    }
  }, [i18n])

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
    if (!importProgress) return 0
    if (importProgress.phase === 'done') return 100
    if (!importProgress.total || importProgress.total <= 0) return 0
    const current = importProgress.current ?? 0
    const pct = Math.round((current / importProgress.total) * 100)
    if (current <= 0) return 0
    return Math.min(100, Math.max(2, pct))
  })()

  const importProgressMeta = (() => {
    if (!importProgress) return ''
    const current = importProgress.current ?? 0
    if (importProgress.phase === 'uploading' && importProgress.total === 100) {
      return `${current}%`
    }
    if (importProgress.total && importProgress.total > 0) {
      const suffix =
        importProgress.phase === 'validating'
          ? t('adminProducts.progressRows')
          : importProgress.phase === 'importing' || importProgress.phase === 'skipped'
            ? t('adminProducts.progressProducts')
            : ''
      return `${current.toLocaleString()} / ${importProgress.total.toLocaleString()}${suffix}`
    }
    return ''
  })()

  const deactivateProduct = async (id: number, name: string) => {
    setImportDetail('')
    setImportSuccess('')
    await deactivateMutation.mutateAsync(id)
    setImportSuccess(`"${name}" disattivato.`)
  }

  const handleDeactivate = async (id: number, name: string) => {
    if (!window.confirm(t('adminProducts.confirmDeactivate', { name }))) return
    try {
      await deactivateProduct(id, name)
    } catch (err: unknown) {
      setImportDetail(formatApiError(err, 'Impossibile disattivare il prodotto.'))
    }
  }

  const handleDelete = async (id: number, name: string) => {
    if (!window.confirm(t('adminProducts.confirmDelete', { name }))) return
    setImportDetail('')
    setImportSuccess('')
    try {
      await deleteMutation.mutateAsync(id)
      queryClient.invalidateQueries({ queryKey: ['admin-products'] })
    } catch (err: unknown) {
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

  const productCount = data?.count ?? 0
  const catalogEmpty = !isLoading && productCount === 0

  const handleRestoreDemoCatalog = async () => {
    setImportDetail('')
    setImportSuccess('')
    setImportErrors([])
    setRestoringDemo(true)
    try {
      const result = await restoreDemoCatalog()
      setImportSuccess(result.detail)
      queryClient.invalidateQueries({ queryKey: ['admin-products'] })
    } catch (err: unknown) {
      setImportDetail(formatClientError(err, t('adminProducts.restoreDemoError')))
    } finally {
      setRestoringDemo(false)
    }
  }

  const handleExportCsv = async () => {
    setImportDetail('')
    setImportErrors([])
    setImportSuccess('')
    setExporting(true)
    try {
      const fresh = await queryClient.fetchQuery({
        queryKey: ['admin-products', params],
        queryFn: () => fetchAdminProducts(params),
      })
      if ((fresh?.count ?? 0) === 0) {
        setImportDetail(t('adminProducts.exportNeedsProducts'))
        return
      }
      await exportProductsCsv()
    } catch (err: unknown) {
      setImportDetail(formatClientError(err, 'Impossibile esportare i prodotti in CSV.'))
    } finally {
      setExporting(false)
    }
  }

  const runCsvImport = async (file: File, columnFilter?: CsvImportColumnFilter) => {
    setImporting(true)
    setImportSuccess('')
    setImportErrors([])
    setImportDetail('')
    setImportBatchId(null)
    setImportBatchCreated(0)
    setImportProgress({ phase: 'uploading', current: 0, total: 100, message: 'Caricamento file…' })
    try {
      const result = await importProductsCsvWithProgress(
        file,
        (event) => {
          setImportProgress(event)
          if (event.batch_id) setImportBatchId(event.batch_id)
          if (event.phase === 'done' || event.phase === 'failed') {
            setImportBatchCreated(event.created_products ?? 0)
          } else if (event.phase === 'importing' && event.batch_id) {
            setImportBatchId(event.batch_id)
          }
        },
        (percent) => setImportProgress({
          phase: 'uploading',
          current: percent,
          total: 100,
          message: `Caricamento file… ${percent}%`,
        }),
        columnFilter,
      )
      setImportSuccess(result.detail)
      if (result.batch_id) setImportBatchId(result.batch_id)
      setImportBatchCreated(result.created_products)
      if (result.errors?.length) {
        setImportErrors(result.errors)
        if (result.import_partial) {
          setImportDetail(result.detail)
        }
      }
      setImportProgress({ phase: 'done', current: 100, total: 100, message: result.detail })
      queryClient.invalidateQueries({ queryKey: ['admin-products'] })
    } catch (err: unknown) {
      const responseData = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: CsvImportResult & { errors?: CsvImportError[] } } }).response?.data
        : undefined
      if (responseData?.batch_id) {
        setImportBatchId(responseData.batch_id)
        setImportBatchCreated(responseData.created_products ?? 0)
      }
      if (responseData?.errors?.length) {
        setImportDetail(responseData.detail || 'Validazione CSV non riuscita.')
        setImportErrors(responseData.errors)
      } else if (responseData?.detail) {
        setImportDetail(responseData.detail)
      } else if (err instanceof Error && err.message) {
        setImportDetail(err.message)
      } else {
        setImportDetail(formatApiError(err, 'Impossibile importare il CSV.'))
      }
    } finally {
      setImporting(false)
      setPendingImportFile(null)
    }
  }

  const handleImportFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return

    setScanningCsv(true)
    setImportSuccess('')
    setImportErrors([])
    setImportDetail('')
    setPendingImportFile(file)
    resetImportModalState()
    try {
      const preview = await scanCsvImportPreview(file)
      setImportColumnOptions(preview.columns)
      setImportCsvStats({
        totalDataRows: preview.totalDataRows,
        importableRows: preview.importableRows,
      })
      setImportColumnSelected(CSV_IMPORT_ALL)
      setImportModalStep('column')
      setImportModalOpen(true)
    } catch (err: unknown) {
      setImportDetail(formatClientError(err, t('adminProducts.readColumnsError')))
      setPendingImportFile(null)
    } finally {
      setScanningCsv(false)
    }
  }

  const closeImportModal = () => {
    setImportModalOpen(false)
    setPendingImportFile(null)
    resetImportModalState()
  }

  const goToValueStep = async () => {
    if (!pendingImportFile || !importColumnSelected) {
      setImportDetail(t('adminProducts.selectOneColumn'))
      return
    }
    if (importColumnSelected === CSV_IMPORT_ALL) {
      setImportDetail(t('adminProducts.useImportAllButton'))
      return
    }
    setLoadingColumnValues(true)
    setImportDetail('')
    try {
      const values = await scanCsvColumnValuesFromFile(pendingImportFile, importColumnSelected)
      setImportValueOptions(values)
      setImportValueSelected(values.map((v) => v.key))
      setImportModalStep('values')
    } catch (err: unknown) {
      setImportDetail(formatClientError(err, t('adminProducts.readColumnValuesError')))
    } finally {
      setLoadingColumnValues(false)
    }
  }

  const toggleImportValue = (key: string) => {
    setImportValueSelected((prev) => (
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]
    ))
  }

  const confirmImportAll = async () => {
    if (!pendingImportFile) return
    const file = pendingImportFile
    setImportModalOpen(false)
    resetImportModalState()
    await runCsvImport(file)
  }

  const confirmColumnImport = async () => {
    if (!pendingImportFile || !importColumnSelected) return
    if (importValueSelected.length === 0) {
      setImportDetail(t('adminProducts.selectOneValue'))
      return
    }
    const file = pendingImportFile
    const column = importColumnSelected
    const values = importValueOptions
      .filter((v) => importValueSelected.includes(v.key))
      .flatMap((v) => [v.key, v.name])
    setImportModalOpen(false)
    resetImportModalState()
    await runCsvImport(file, { column, values })
  }

  const handleRollbackLastImport = async () => {
    if (!importBatchId || importBatchCreated <= 0) return
    if (!window.confirm(t('adminProducts.confirmRollbackImport', { count: importBatchCreated }))) return
    setRollbackImportBusy(true)
    setImportDetail('')
    try {
      const result = await rollbackCsvImportBatch(importBatchId)
      setImportSuccess(result.detail)
      setImportBatchId(null)
      setImportBatchCreated(0)
      setImportErrors([])
      queryClient.invalidateQueries({ queryKey: ['admin-products'] })
    } catch (err: unknown) {
      setImportDetail(formatApiError(err, t('adminProducts.rollbackImportError')))
    } finally {
      setRollbackImportBusy(false)
    }
  }

  const handleDeleteAll = async () => {
    const total = data?.count ?? 0
    const countLabel = total > 0 ? t('adminProducts.inCatalog', { count: total }) : ''
    if (!window.confirm(t('adminProducts.confirmDeleteAll', { countLabel }))) return
    const typed = window.prompt(t('adminProducts.confirmDeleteAllPrompt'))
    if (typed !== t('adminProducts.confirmDeleteAllToken')) {
      if (typed !== null) {
        setImportDetail(t('adminProducts.confirmDeleteAllWrong'))
      }
      return
    }

    setDeleteAllBusy(true)
    setImportDetail('')
    setImportSuccess('')
    setSelectedIds([])
    try {
      const result = await deleteAllAdminProducts()
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
      setPage(1)
      queryClient.invalidateQueries({ queryKey: ['admin-products'] })
    } catch (err: unknown) {
      setImportDetail(formatApiError(err, 'Impossibile eliminare tutti i prodotti.'))
    } finally {
      setDeleteAllBusy(false)
    }
  }

  const handleBulkDelete = async () => {
    if (selectedIds.length === 0) return
    const count = selectedIds.length
    if (!window.confirm(t('adminProducts.confirmBulkDelete', { count }))) return

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
          <h1>{t('adminProducts.title')}</h1>
          <p>{t('adminProducts.subtitle')}</p>
        </div>
        <div className="admin-header-actions">
          <button type="button" className="btn btn-secondary" onClick={handleDownloadTemplate}>
            {t('adminProducts.downloadTemplate')}
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            disabled={exporting || catalogEmpty}
            title={catalogEmpty ? t('adminProducts.exportNeedsProducts') : undefined}
            onClick={handleExportCsv}
          >
            {exporting ? t('adminProducts.exporting') : t('adminProducts.exportCsv')}
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            disabled={importing || scanningCsv}
            onClick={() => fileInputRef.current?.click()}
          >
            {scanningCsv ? t('adminProducts.scanningCsv') : importing ? t('adminProducts.importing') : t('adminProducts.importCsv')}
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,text/csv"
            className="admin-file-input"
            onChange={handleImportFile}
          />
          <Link to="/admin/products/new" className="btn btn-primary">{t('adminProducts.addProduct')}</Link>
        </div>
      </div>

      <section className="admin-card admin-import-panel">
        <h2>{t('adminProducts.importExportTitle')}</h2>
        <p className="admin-hint">{t('adminProducts.importHint')}</p>
        <p className="admin-hint">{t('adminProducts.skipExistingHint')}</p>
        {catalogEmpty && (
          <div className="admin-alert admin-alert-warning">
            <p>{t('adminProducts.emptyCatalog')}</p>
            <div className="admin-empty-catalog-actions">
              <button
                type="button"
                className="btn btn-secondary"
                disabled={importing || scanningCsv}
                onClick={() => fileInputRef.current?.click()}
              >
                {t('adminProducts.importCsv')}
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                disabled={restoringDemo}
                onClick={handleRestoreDemoCatalog}
              >
                {restoringDemo ? t('common.loading') : t('adminProducts.restoreDemoCatalog')}
              </button>
            </div>
          </div>
        )}
        {importing && importProgress && (
          <div className="admin-import-progress" aria-live="polite">
            <div className="admin-import-progress-label">
              {importProgress.message || t('adminProducts.importInProgress')}
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
            {importProgressMeta ? (
              <span className="admin-import-progress-meta">{importProgressMeta}</span>
            ) : null}
          </div>
        )}
        {!importing && importProgress?.phase === 'done' && importProgress && (
          <div className="admin-import-progress admin-import-progress--done" aria-live="polite">
            <div className="admin-import-progress-label">{importProgress.message}</div>
          </div>
        )}
        {importSuccess && <p className="admin-alert admin-alert-success">{importSuccess}</p>}
        {importBatchId && importBatchCreated > 0 && !importing && (
          <div className="admin-import-rollback">
            <p className="admin-hint">{t('adminProducts.rollbackImportHint', { count: importBatchCreated })}</p>
            <button
              type="button"
              className="btn btn-secondary"
              disabled={rollbackImportBusy}
              onClick={handleRollbackLastImport}
            >
              {rollbackImportBusy ? t('adminProducts.rollbackImportBusy') : t('adminProducts.rollbackImport')}
            </button>
          </div>
        )}
        {importDetail && !importSuccess && (
          <p className="admin-alert admin-alert-error">{importDetail}</p>
        )}
        {importErrors.length > 0 && (
          <div className="admin-import-errors">
            <strong>{t('adminProducts.errorsFound', { count: importErrors.length })}</strong>
            <ul>
              {importErrors.map((error, index) => (
                <li key={`${error.row}-${error.field}-${index}`}>
                  {error.row > 0 ? (
                    t('adminProducts.rowError', {
                      row: error.row,
                      field: error.field ? ` · ${error.field}` : '',
                      message: error.message,
                    })
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
          placeholder={t('adminProducts.searchPlaceholder')}
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1) }}
        />
        <select value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1) }}>
          <option value="all">{t('adminProducts.filterAll')}</option>
          <option value="active">{t('adminProducts.filterActive')}</option>
          <option value="inactive">{t('adminProducts.filterInactive')}</option>
        </select>
      </div>

      <div className="admin-bulk-bar">
        <p className="admin-bulk-hint">
          <strong>{t('adminProducts.bulkDeleteHint')}</strong>
        </p>
        <div className="admin-bulk-actions">
          <span className="admin-bulk-count">
            {t('adminProducts.selectedCount', { count: selectedIds.length })}
          </span>
          <button
            type="button"
            className="btn btn-secondary"
            disabled={selectedIds.length === 0}
            onClick={() => setSelectedIds([])}
          >
            {t('adminProducts.deselectAll')}
          </button>
          <button
            type="button"
            className="btn btn-secondary admin-bulk-delete-btn"
            disabled={selectedIds.length === 0 || bulkDeleting || deleteAllBusy}
            onClick={handleBulkDelete}
          >
            {bulkDeleting ? t('adminProducts.bulkDeleting') : t('adminProducts.bulkDelete')}
          </button>
          <button
            type="button"
            className="btn btn-secondary admin-bulk-delete-btn"
            disabled={bulkDeleting || deleteAllBusy || (data?.count ?? 0) === 0}
            onClick={handleDeleteAll}
            title={t('adminProducts.deleteAllTitle')}
          >
            {deleteAllBusy ? t('adminProducts.bulkDeleting') : t('adminProducts.deleteAll')}
          </button>
        </div>
      </div>

      {isLoading ? (
        <p>{t('adminProducts.loadingProducts')}</p>
      ) : (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th className="admin-table-check" scope="col">
                  <span className="admin-table-check-label">{t('adminProducts.colSelect')}</span>
                  <input
                    type="checkbox"
                    className="admin-table-checkbox"
                    aria-label="Seleziona tutti i prodotti in questa pagina"
                    checked={allOnPageSelected}
                    onChange={toggleSelectAllOnPage}
                  />
                </th>
                <th>{t('adminProducts.colProduct')}</th>
                <th>{t('adminProducts.colSku')}</th>
                <th>{t('adminProducts.colPrice')}</th>
                <th>{t('adminProducts.colStock')}</th>
                <th>{t('adminProducts.colStatus')}</th>
                <th>{t('adminProducts.colFlags')}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {products.length === 0 ? (
                <tr>
                  <td colSpan={8} className="admin-empty">{t('adminProducts.empty')}</td>
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
                      {product.is_active ? t('adminCommon.active') : t('adminCommon.inactive')}
                    </span>
                  </td>
                  <td>
                    <div className="admin-flags">
                      {product.is_featured && <span className="admin-flag">{t('adminProducts.flagFeatured')}</span>}
                      {product.is_new_arrival && <span className="admin-flag">{t('adminProducts.flagNew')}</span>}
                      {product.is_bestseller && <span className="admin-flag">{t('adminProducts.flagBest')}</span>}
                    </div>
                  </td>
                  <td className="admin-actions">
                    <Link to={`/admin/products/${product.id}`} className="admin-link">{t('adminCommon.edit')}</Link>
                    {product.is_active && (
                      <button
                        type="button"
                        className="admin-link"
                        onClick={() => handleDeactivate(product.id, product.name)}
                      >
                        {t('adminCommon.deactivate')}
                      </button>
                    )}
                    <button
                      type="button"
                      className="admin-link admin-link-danger"
                      onClick={() => handleDelete(product.id, product.name)}
                    >
                      {t('adminCommon.delete')}
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
          <button type="button" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>{t('adminCommon.prev')}</button>
          <span>{t('adminCommon.pageOf', { page, total: totalPages })}</span>
          <button type="button" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>{t('adminCommon.next')}</button>
        </div>
      )}

      {importModalOpen && createPortal(
        <div className="admin-import-brand-overlay" role="dialog" aria-modal="true" aria-labelledby="import-filter-title">
          <div className="admin-import-brand-dialog admin-card">
            <h3 id="import-filter-title">
              {importModalStep === 'column'
                ? t('adminProducts.columnModalTitle')
                : t('adminProducts.valueModalTitle')}
            </h3>
            <p className="admin-hint">
              {importModalStep === 'column'
                ? t('adminProducts.columnModalHint', { file: pendingImportFile?.name ?? '' })
                : t('adminProducts.valueModalHint', {
                  file: pendingImportFile?.name ?? '',
                  column: importColumnOptions.find((c) => c.key === importColumnSelected)?.label
                    ?? importColumnSelected
                    ?? '',
                })}
            </p>
            {importModalStep === 'column' && importCsvStats && (
              <p className="admin-import-row-stats">
                {t('adminProducts.csvRowsDetected', {
                  total: importCsvStats.totalDataRows.toLocaleString(),
                  importable: importCsvStats.importableRows.toLocaleString(),
                })}
              </p>
            )}
            {importModalStep === 'column' ? (
              <ul className="admin-import-brand-list">
                <li key={CSV_IMPORT_ALL}>
                  <label className="admin-import-brand-option admin-import-brand-option--all">
                    <input
                      type="radio"
                      name="csv-import-column"
                      checked={importColumnSelected === CSV_IMPORT_ALL}
                      onChange={() => setImportColumnSelected(CSV_IMPORT_ALL)}
                    />
                    <span className="admin-import-brand-name">{t('adminProducts.importAllProducts')}</span>
                    <span className="admin-import-brand-meta">
                      {t('adminProducts.importAllProductsHint')}
                    </span>
                  </label>
                </li>
                <li className="admin-import-list-divider" aria-hidden="true">
                  {t('adminProducts.orFilterByColumn')}
                </li>
                {importColumnOptions.map((col) => (
                  <li key={col.key}>
                    <label className="admin-import-brand-option">
                      <input
                        type="radio"
                        name="csv-import-column"
                        checked={importColumnSelected === col.key}
                        onChange={() => setImportColumnSelected(col.key)}
                      />
                      <span className="admin-import-brand-name">{col.label}</span>
                      <span className="admin-import-brand-meta">{col.key}</span>
                    </label>
                  </li>
                ))}
              </ul>
            ) : (
              <>
                <div className="admin-import-brand-toolbar">
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => setImportValueSelected(importValueOptions.map((v) => v.key))}
                  >
                    {t('adminProducts.selectAllValues')}
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => setImportValueSelected([])}
                  >
                    {t('adminProducts.deselectAllValues')}
                  </button>
                </div>
                <p className="admin-import-selected-summary" aria-live="polite">
                  {selectedImportStatsLoading
                    ? t('adminProducts.selectedImportCounting')
                    : t('adminProducts.selectedImportSummary', {
                      products: (selectedImportStats?.productCount ?? 0).toLocaleString(),
                      rows: (selectedImportStats?.rowCount ?? 0).toLocaleString(),
                    })}
                </p>
                <ul className="admin-import-brand-list">
                  {importValueOptions.map((value) => (
                    <li key={value.key}>
                      <label className="admin-import-brand-option">
                        <input
                          type="checkbox"
                          checked={importValueSelected.includes(value.key)}
                          onChange={() => toggleImportValue(value.key)}
                        />
                        <span className="admin-import-brand-name">
                          {value.key === CSV_FILTER_NONE
                            ? t('adminProducts.filterValueNull')
                            : value.name}
                        </span>
                        <span className="admin-import-brand-meta">
                          {t('adminProducts.brandProducts', { count: value.product_count })}
                          {' · '}
                          {t('adminProducts.brandRows', { count: value.row_count })}
                        </span>
                      </label>
                    </li>
                  ))}
                </ul>
              </>
            )}
            <div className="admin-import-brand-actions">
              <button type="button" className="btn btn-secondary" onClick={closeImportModal}>
                {t('adminCommon.cancel')}
              </button>
              {importModalStep === 'column' ? (
                importColumnSelected === CSV_IMPORT_ALL ? (
                  <button
                    type="button"
                    className="btn btn-primary"
                    disabled={importing}
                    onClick={() => void confirmImportAll()}
                  >
                    {importing ? t('adminProducts.importInProgress') : t('adminProducts.startImportAll')}
                  </button>
                ) : (
                  <button
                    type="button"
                    className="btn btn-primary"
                    disabled={!importColumnSelected || loadingColumnValues}
                    onClick={() => void goToValueStep()}
                  >
                    {loadingColumnValues ? t('adminProducts.loadingValues') : t('adminProducts.nextSelectValues')}
                  </button>
                )
              ) : (
                <>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    disabled={loadingColumnValues}
                    onClick={() => setImportModalStep('column')}
                  >
                    {t('adminProducts.backToColumns')}
                  </button>
                  <button
                    type="button"
                    className="btn btn-primary"
                    disabled={importValueSelected.length === 0 || importing}
                    onClick={() => void confirmColumnImport()}
                  >
                    {t('adminProducts.importSelectedValues')}
                  </button>
                </>
              )}
            </div>
          </div>
        </div>,
        document.body,
      )}
    </div>
  )
}
