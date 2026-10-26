import api from './client'

export type SupportTicketStatus = 'open' | 'in_progress' | 'resolved' | 'closed'

export type SupportMessage = {
  id: number
  body: string
  is_staff_reply: boolean
  author_name: string
  created_at: string
}

export type SupportTicketListItem = {
  id: number
  subject: string
  status: SupportTicketStatus
  needs_user_attention: boolean
  needs_staff_attention?: boolean
  created_at: string
  updated_at: string
  last_message_preview: string
  last_message_is_staff: boolean
  message_count: number
}

export type SupportTicketDetail = SupportTicketListItem & {
  messages: SupportMessage[]
  user_display?: string
}

export const fetchSupportTickets = () =>
  api.get<SupportTicketListItem[]>('/support/tickets/').then((r) => r.data)

export const fetchSupportTicket = (id: number) =>
  api.get<SupportTicketDetail>(`/support/tickets/${id}/`).then((r) => r.data)

export const createSupportTicket = (subject: string, message: string) =>
  api.post<SupportTicketDetail>('/support/tickets/', { subject, message }).then((r) => r.data)

export const replySupportTicket = (id: number, message: string) =>
  api.post<SupportTicketDetail>(`/support/tickets/${id}/reply/`, { message }).then((r) => r.data)

export const fetchSupportUnreadCount = () =>
  api.get<{ count: number }>('/support/tickets/unread-count/').then((r) => r.data)

export const fetchAdminSupportTickets = () =>
  api.get<SupportTicketListItem[]>('/admin/support/tickets/').then((r) => r.data)

export const fetchAdminSupportTicket = (id: number) =>
  api.get<SupportTicketDetail>(`/admin/support/tickets/${id}/`).then((r) => r.data)

export const replyAdminSupportTicket = (id: number, message: string) =>
  api.post<SupportTicketDetail>(`/admin/support/tickets/${id}/reply/`, { message }).then((r) => r.data)

export const updateAdminSupportTicketStatus = (id: number, status: SupportTicketStatus) =>
  api.patch<SupportTicketDetail>(`/admin/support/tickets/${id}/status/`, { status }).then((r) => r.data)

export const fetchAdminSupportUnreadCount = () =>
  api.get<{ count: number }>('/admin/support/tickets/unread-count/').then((r) => r.data)
