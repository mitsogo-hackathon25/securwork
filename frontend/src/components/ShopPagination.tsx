import { useTranslation } from 'react-i18next'
import './ShopPagination.css'

const PAGE_SIZE = 12

interface Props {
  page: number
  totalCount: number
  onPageChange: (page: number) => void
}

function buildPageItems(current: number, total: number): (number | 'ellipsis')[] {
  if (total <= 7) {
    return Array.from({ length: total }, (_, i) => i + 1)
  }
  const items: (number | 'ellipsis')[] = [1]
  const start = Math.max(2, current - 1)
  const end = Math.min(total - 1, current + 1)

  if (start > 2) items.push('ellipsis')
  for (let p = start; p <= end; p += 1) items.push(p)
  if (end < total - 1) items.push('ellipsis')
  items.push(total)
  return items
}

export default function ShopPagination({ page, totalCount, onPageChange }: Props) {
  const { t } = useTranslation()
  const totalPages = Math.max(1, Math.ceil(totalCount / PAGE_SIZE))

  if (totalPages <= 1) return null

  const pageItems = buildPageItems(page, totalPages)
  const from = (page - 1) * PAGE_SIZE + 1
  const to = Math.min(page * PAGE_SIZE, totalCount)

  return (
    <nav className="shop-pagination" aria-label={t('shop.pagination')}>
      <p className="shop-pagination-summary">
        {t('shop.showingRange', { from, to, total: totalCount })}
      </p>

      <div className="shop-pagination-controls">
        <button
          type="button"
          className="shop-pagination-btn shop-pagination-prev"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
          aria-label={t('shop.previousPage')}
        >
          <span aria-hidden="true">←</span>
          <span className="shop-pagination-btn-text">{t('shop.previous')}</span>
        </button>

        <ol className="shop-pagination-pages">
          {pageItems.map((item, index) =>
            item === 'ellipsis' ? (
              <li key={`ellipsis-${index}`} className="shop-pagination-ellipsis" aria-hidden="true">…</li>
            ) : (
              <li key={item}>
                <button
                  type="button"
                  className={`shop-pagination-page${item === page ? ' active' : ''}`}
                  onClick={() => onPageChange(item)}
                  aria-label={t('shop.goToPage', { page: item })}
                  aria-current={item === page ? 'page' : undefined}
                >
                  {item}
                </button>
              </li>
            )
          )}
        </ol>

        <button
          type="button"
          className="shop-pagination-btn shop-pagination-next"
          disabled={page >= totalPages}
          onClick={() => onPageChange(page + 1)}
          aria-label={t('shop.nextPage')}
        >
          <span className="shop-pagination-btn-text">{t('shop.next')}</span>
          <span aria-hidden="true">→</span>
        </button>
      </div>

      <p className="shop-pagination-mobile-label">
        {t('shop.pageOf', { page, total: totalPages })}
      </p>
    </nav>
  )
}
