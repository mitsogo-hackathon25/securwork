import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import { useTranslation } from 'react-i18next'
import { SESSION_EXPIRED_EVENT } from '../../utils/auth'
import './Toast.css'

type ToastVariant = 'success' | 'error'

type ToastContextValue = {
  showToast: (message: string, variant?: ToastVariant, durationMs?: number) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

const TOAST_DURATION_MS = 2000

export function ToastProvider({ children }: { children: ReactNode }) {
  const { t } = useTranslation()
  const [toast, setToast] = useState<{ message: string; variant: ToastVariant } | null>(null)
  const [visible, setVisible] = useState(false)
  const hideTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const showToast = useCallback((message: string, variant: ToastVariant = 'success', durationMs = TOAST_DURATION_MS) => {
    if (hideTimerRef.current) {
      clearTimeout(hideTimerRef.current)
      hideTimerRef.current = null
    }
    setToast({ message, variant })
    setVisible(true)
    hideTimerRef.current = setTimeout(() => {
      setVisible(false)
      hideTimerRef.current = setTimeout(() => {
        setToast(null)
        hideTimerRef.current = null
      }, 280)
    }, durationMs)
  }, [])

  useEffect(() => {
    const onSessionExpired = () => {
      showToast(t('common.sessionExpired'), 'error', 3200)
    }
    window.addEventListener(SESSION_EXPIRED_EVENT, onSessionExpired)
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, onSessionExpired)
  }, [showToast, t])

  const value = useMemo(() => ({ showToast }), [showToast])

  return (
    <ToastContext.Provider value={value}>
      {children}
      {toast && (
        <div
          className={`app-toast app-toast--${toast.variant}${visible ? ' app-toast--visible' : ''}`}
          role="status"
          aria-live="polite"
        >
          {toast.message}
        </div>
      )}
    </ToastContext.Provider>
  )
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext)
  if (!ctx) {
    throw new Error('useToast must be used within ToastProvider')
  }
  return ctx
}
