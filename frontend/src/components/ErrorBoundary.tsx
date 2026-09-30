import { Component, type ErrorInfo, type ReactNode } from 'react'

interface Props {
  children: ReactNode
}

interface State {
  error: Error | null
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('SecurWork render error:', error, info)
  }

  render() {
    if (this.state.error) {
      return (
        <div style={{ padding: '2rem', fontFamily: 'system-ui, sans-serif', maxWidth: 600, margin: '2rem auto' }}>
          <h1 style={{ color: '#c62828' }}>Something went wrong</h1>
          <p>The page failed to load. Try refreshing or restarting the dev servers.</p>
          <pre style={{ background: '#f5f5f5', padding: '1rem', overflow: 'auto', fontSize: '0.85rem' }}>
            {this.state.error.message}
          </pre>
          <button
            type="button"
            onClick={() => window.location.reload()}
            style={{ marginTop: '1rem', padding: '0.5rem 1rem', cursor: 'pointer' }}
          >
            Reload page
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
