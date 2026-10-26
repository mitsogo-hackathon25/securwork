import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  fetchAdminSupportTicket,
  fetchAdminSupportTickets,
  replyAdminSupportTicket,
  updateAdminSupportTicketStatus,
  type SupportTicketStatus,
} from '../../api/support'
import { formatApiError } from '../../utils/formatApiError'
import '../TicketsPage.css'
import './Admin.css'

const STATUSES: SupportTicketStatus[] = ['open', 'in_progress', 'resolved', 'closed']

export default function AdminSupportPage() {
  const { t } = useTranslation()
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const ticketId = id ? Number(id) : null

  const [reply, setReply] = useState('')
  const [error, setError] = useState('')

  const { data: tickets = [], isLoading: listLoading } = useQuery({
    queryKey: ['admin-support-tickets'],
    queryFn: fetchAdminSupportTickets,
    enabled: !ticketId,
  })

  const { data: ticket, isLoading: detailLoading } = useQuery({
    queryKey: ['admin-support-ticket', ticketId],
    queryFn: () => fetchAdminSupportTicket(ticketId!),
    enabled: !!ticketId,
  })

  useEffect(() => {
    if (ticket) {
      queryClient.invalidateQueries({ queryKey: ['admin-support-unread'] })
    }
  }, [ticket, queryClient])

  const replyMutation = useMutation({
    mutationFn: () => replyAdminSupportTicket(ticketId!, reply),
    onSuccess: () => {
      setReply('')
      queryClient.invalidateQueries({ queryKey: ['admin-support-ticket', ticketId] })
      queryClient.invalidateQueries({ queryKey: ['admin-support-tickets'] })
      queryClient.invalidateQueries({ queryKey: ['admin-support-unread'] })
    },
    onError: (err: unknown) => setError(formatApiError(err, t('tickets.replyError'))),
  })

  const statusMutation = useMutation({
    mutationFn: (status: SupportTicketStatus) => updateAdminSupportTicketStatus(ticketId!, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-support-ticket', ticketId] })
      queryClient.invalidateQueries({ queryKey: ['admin-support-tickets'] })
    },
  })

  if (ticketId) {
    if (detailLoading || !ticket) {
      return <div className="admin-page"><p>{t('common.loading')}</p></div>
    }
    return (
      <div className="admin-page">
        <button type="button" className="btn btn-secondary" onClick={() => navigate('/admin/tickets')}>
          ← {t('tickets.backToList')}
        </button>
        <h1>{ticket.subject}</h1>
        <p className="admin-muted">
          {ticket.user_display} · {t(`tickets.status.${ticket.status}`)}
        </p>
        <label className="admin-field">
          {t('tickets.changeStatus')}
          <select
            value={ticket.status}
            onChange={(e) => statusMutation.mutate(e.target.value as SupportTicketStatus)}
          >
            {STATUSES.map((s) => (
              <option key={s} value={s}>{t(`tickets.status.${s}`)}</option>
            ))}
          </select>
        </label>
        <div className="ticket-thread admin-ticket-thread">
          {ticket.messages.map((msg) => (
            <article key={msg.id} className={`ticket-message ${msg.is_staff_reply ? 'staff' : 'user'}`}>
              <header>
                <strong>{msg.author_name}</strong>
                <time dateTime={msg.created_at}>{new Date(msg.created_at).toLocaleString()}</time>
              </header>
              <p>{msg.body}</p>
            </article>
          ))}
        </div>
        {error && <p className="admin-alert admin-alert-error">{error}</p>}
        <form
          className="admin-form"
          onSubmit={(e) => {
            e.preventDefault()
            setError('')
            if (!reply.trim()) return
            replyMutation.mutate()
          }}
        >
          <label>
            {t('tickets.staffReply')}
            <textarea value={reply} onChange={(e) => setReply(e.target.value)} rows={4} required />
          </label>
          <button type="submit" className="btn btn-primary" disabled={replyMutation.isPending}>
            {replyMutation.isPending ? t('common.loading') : t('tickets.sendReply')}
          </button>
        </form>
      </div>
    )
  }

  return (
    <div className="admin-page">
      <h1>{t('adminNav.tickets')}</h1>
      {listLoading ? (
        <p>{t('common.loading')}</p>
      ) : tickets.length === 0 ? (
        <p>{t('tickets.adminEmpty')}</p>
      ) : (
        <table className="admin-table">
          <thead>
            <tr>
              <th>{t('tickets.subject')}</th>
              <th>{t('tickets.statusLabel')}</th>
              <th>{t('tickets.updatedCol')}</th>
            </tr>
          </thead>
          <tbody>
            {tickets.map((item) => (
              <tr key={item.id}>
                <td>
                  <Link to={`/admin/tickets/${item.id}`} className="admin-link-with-dot">
                    {item.needs_staff_attention && <span className="nav-unread-dot" aria-hidden />}
                    #{item.id} {item.subject}
                  </Link>
                </td>
                <td>{t(`tickets.status.${item.status}`)}</td>
                <td>{new Date(item.updated_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
