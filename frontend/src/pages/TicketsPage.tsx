import { useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Helmet } from 'react-helmet-async'
import {
  createSupportTicket,
  fetchSupportTicket,
  fetchSupportTickets,
  replySupportTicket,
  type SupportTicketListItem,
} from '../api/support'
import { isLoggedIn, accountUrlWithNext } from '../utils/auth'
import { formatApiError } from '../utils/formatApiError'
import './TicketsPage.css'

const POLL_MS = 15_000
const ACTIVE_STATUSES = new Set(['open', 'in_progress'])

function parseTicketId(raw: string | undefined): number | null {
  if (!raw || !/^\d+$/.test(raw)) return null
  const id = Number(raw)
  return Number.isFinite(id) ? id : null
}

function TicketHistoryList({
  tickets,
  currentId,
  title,
  onSelect,
}: {
  tickets: SupportTicketListItem[]
  currentId?: number | null
  title: string
  onSelect: (id: number) => void
}) {
  const { t } = useTranslation()

  if (tickets.length === 0) return null

  return (
    <section className="ticket-history-block">
      <h2 className="ticket-history-heading">{title}</h2>
      <ul className="ticket-list">
        {tickets.map((item) => (
          <li key={item.id}>
            <button
              type="button"
              className={`ticket-list-item${currentId === item.id ? ' active' : ''}`}
              onClick={() => onSelect(item.id)}
            >
              <span className="ticket-list-subject">
                {item.needs_user_attention && <span className="nav-unread-dot" aria-hidden />}
                {item.subject}
              </span>
              <span className="ticket-list-meta">
                {t(`tickets.status.${item.status}`)} · {new Date(item.updated_at).toLocaleString()}
                {item.message_count > 0 && (
                  <> · {t('tickets.messageCount', { count: item.message_count })}</>
                )}
              </span>
              {item.last_message_is_staff && (
                <span className="ticket-list-badge">{t('tickets.supportReplied')}</span>
              )}
              {item.last_message_preview && (
                <span className="ticket-list-preview">{item.last_message_preview}</span>
              )}
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}

export default function TicketsPage() {
  const { t } = useTranslation()
  const { id } = useParams<{ id: string }>()
  const location = useLocation()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const ticketId = parseTicketId(id)
  const [loggedIn, setLoggedIn] = useState(isLoggedIn())

  const [subject, setSubject] = useState('')
  const [message, setMessage] = useState('')
  const [reply, setReply] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    setLoggedIn(isLoggedIn())
  }, [location.pathname])

  const { data: tickets = [], isLoading: listLoading } = useQuery({
    queryKey: ['support-tickets'],
    queryFn: fetchSupportTickets,
    enabled: loggedIn,
    refetchInterval: POLL_MS,
  })

  const {
    data: ticket,
    isPending: detailPending,
    isError: detailError,
    error: detailLoadError,
    refetch: refetchTicket,
  } = useQuery({
    queryKey: ['support-ticket', ticketId],
    queryFn: () => fetchSupportTicket(ticketId!),
    enabled: loggedIn && ticketId !== null,
    refetchInterval: POLL_MS,
    retry: 1,
  })

  const sortedTickets = useMemo(
    () => [...tickets].sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()),
    [tickets],
  )

  const { activeTickets, closedTickets } = useMemo(() => {
    const active: SupportTicketListItem[] = []
    const closed: SupportTicketListItem[] = []
    for (const item of sortedTickets) {
      if (ACTIVE_STATUSES.has(item.status)) active.push(item)
      else closed.push(item)
    }
    return { activeTickets: active, closedTickets: closed }
  }, [sortedTickets])

  useEffect(() => {
    if (ticket) {
      queryClient.invalidateQueries({ queryKey: ['support-unread'] })
    }
  }, [ticket, queryClient])

  const openTicket = (pk: number) => {
    navigate(`/tickets/${pk}`)
  }

  const createMutation = useMutation({
    mutationFn: () => createSupportTicket(subject, message),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['support-tickets'] })
      queryClient.invalidateQueries({ queryKey: ['support-unread'] })
      navigate(`/tickets/${data.id}`)
    },
    onError: (err: unknown) => setError(formatApiError(err, t('tickets.createError'))),
  })

  const replyMutation = useMutation({
    mutationFn: () => replySupportTicket(ticketId!, reply),
    onSuccess: () => {
      setReply('')
      queryClient.invalidateQueries({ queryKey: ['support-ticket', ticketId] })
      queryClient.invalidateQueries({ queryKey: ['support-tickets'] })
      queryClient.invalidateQueries({ queryKey: ['support-unread'] })
    },
    onError: (err: unknown) => setError(formatApiError(err, t('tickets.replyError'))),
  })

  if (!loggedIn) {
    return (
      <div className="container section tickets-page">
        <Helmet><title>{t('tickets.title')} — SecurWork</title></Helmet>
        <h1 className="section-title">{t('tickets.title')}</h1>
        <p>{t('tickets.loginRequired')}</p>
        <Link to={accountUrlWithNext(location.pathname)} className="btn btn-primary">{t('account.login')}</Link>
      </div>
    )
  }

  const historyPanel = listLoading ? (
    <p>{t('common.loading')}</p>
  ) : sortedTickets.length === 0 ? (
    <p className="tickets-empty-hint">{t('tickets.empty')}</p>
  ) : (
    <>
      <TicketHistoryList
        tickets={activeTickets}
        currentId={ticketId}
        title={t('tickets.activeHistory')}
        onSelect={openTicket}
      />
      <TicketHistoryList
        tickets={closedTickets}
        currentId={ticketId}
        title={t('tickets.closedHistory')}
        onSelect={openTicket}
      />
    </>
  )

  if (id && ticketId === null) {
    return (
      <div className="container section tickets-page">
        <p className="tickets-error">{t('tickets.notFound')}</p>
        <Link to="/tickets" className="btn btn-secondary">{t('tickets.backToList')}</Link>
      </div>
    )
  }

  if (ticketId !== null) {
    if (detailPending) {
      return <div className="container section"><p>{t('common.loading')}</p></div>
    }
    if (detailError || !ticket) {
      return (
        <div className="container section tickets-page">
          <p className="tickets-error">
            {formatApiError(detailLoadError, t('tickets.loadError'))}
          </p>
          <button type="button" className="btn btn-secondary" onClick={() => refetchTicket()}>
            {t('tickets.retry')}
          </button>
          <Link to="/tickets" className="btn btn-primary tickets-retry-back">{t('tickets.backToList')}</Link>
        </div>
      )
    }

    const messages = ticket.messages ?? []

    return (
      <div className="container section tickets-page">
        <Helmet><title>{ticket.subject} — SecurWork</title></Helmet>
        <Link to="/tickets" className="tickets-back">← {t('tickets.backToList')}</Link>
        <div className="tickets-layout">
          <aside className="tickets-history-aside" aria-label={t('tickets.yourTickets')}>
            <h2 className="ticket-history-aside-title">{t('tickets.conversationHistory')}</h2>
            {historyPanel}
          </aside>
          <div className="tickets-conversation">
            <h1 className="section-title">{ticket.subject}</h1>
            <p className="tickets-status">{t(`tickets.status.${ticket.status}`)}</p>
            <p className="tickets-history-hint">{t('tickets.threadHint')}</p>
            <div className="ticket-thread">
              {messages.length === 0 ? (
                <p className="tickets-empty-hint">{t('tickets.noMessages')}</p>
              ) : (
                messages.map((msg) => (
                  <article
                    key={msg.id}
                    className={`ticket-message ${msg.is_staff_reply ? 'staff' : 'user'}`}
                  >
                    <header>
                      <strong>
                        {msg.is_staff_reply ? t('tickets.supportTeam') : msg.author_name}
                      </strong>
                      <time dateTime={msg.created_at}>{new Date(msg.created_at).toLocaleString()}</time>
                    </header>
                    <p>{msg.body}</p>
                  </article>
                ))
              )}
            </div>
            {error && <p className="tickets-error">{error}</p>}
            <form
              className="ticket-reply-form"
              onSubmit={(e) => {
                e.preventDefault()
                setError('')
                if (!reply.trim()) return
                replyMutation.mutate()
              }}
            >
              <label>
                {t('tickets.yourReply')}
                <textarea value={reply} onChange={(e) => setReply(e.target.value)} rows={4} required />
              </label>
              <button type="submit" className="btn btn-primary" disabled={replyMutation.isPending}>
                {replyMutation.isPending ? t('common.loading') : t('tickets.sendReply')}
              </button>
            </form>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="container section tickets-page">
      <Helmet><title>{t('tickets.title')} — SecurWork</title></Helmet>
      <h1 className="section-title">{t('tickets.title')}</h1>
      <p className="tickets-intro">{t('tickets.intro')}</p>

      <section className="ticket-list-section ticket-list-section-primary">
        <h2>{t('tickets.yourTickets')}</h2>
        <p className="tickets-open-hint">{t('tickets.openTicketHint')}</p>
        {historyPanel}
      </section>

      <section className="ticket-create">
        <h2>{t('tickets.newTicket')}</h2>
        {error && <p className="tickets-error">{error}</p>}
        <form
          onSubmit={(e) => {
            e.preventDefault()
            setError('')
            createMutation.mutate()
          }}
        >
          <label>
            {t('tickets.subject')}
            <input value={subject} onChange={(e) => setSubject(e.target.value)} required maxLength={200} />
          </label>
          <label>
            {t('tickets.message')}
            <textarea value={message} onChange={(e) => setMessage(e.target.value)} rows={5} required />
          </label>
          <button type="submit" className="btn btn-primary" disabled={createMutation.isPending}>
            {createMutation.isPending ? t('common.loading') : t('tickets.submit')}
          </button>
        </form>
      </section>
    </div>
  )
}
