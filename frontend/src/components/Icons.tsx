interface IconProps {
  size?: number
  className?: string
}

export function IconShield({ size = 24, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" className={className} aria-hidden="true">
      <path d="M12 2l8 4v6c0 5-3.5 9.5-8 10-4.5-.5-8-5-8-10V6l8-4z" />
    </svg>
  )
}

export function IconQuality({ size = 24, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" className={className} aria-hidden="true">
      <path d="M12 2l2.4 4.8 5.4.8-3.9 3.8.9 5.4L12 14.8 7.2 17.8l.9-5.4L4.2 7.6l5.4-.8L12 2z" />
    </svg>
  )
}

export function IconService({ size = 24, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" className={className} aria-hidden="true">
      <path d="M4 6h16v12H4z" /><path d="M4 10h16" /><path d="M8 14h4" />
    </svg>
  )
}

export function IconTruck({ size = 24, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" className={className} aria-hidden="true">
      <path d="M3 6h11v9H3z" /><path d="M14 9h4l3 3v3h-7V9z" /><circle cx="7" cy="18" r="2" /><circle cx="17" cy="18" r="2" />
    </svg>
  )
}

export function IconReturn({ size = 24, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" className={className} aria-hidden="true">
      <path d="M3 7v6h6" /><path d="M21 17a8 8 0 0 0-14-5.3L3 13" />
    </svg>
  )
}

export function IconSupport({ size = 24, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" className={className} aria-hidden="true">
      <path d="M12 3a7 7 0 0 0-7 7v3a3 3 0 0 0 3 3h1v-6H7a5 5 0 1 1 10 0h-2v6h1a3 3 0 0 0 3-3v-3a7 7 0 0 0-7-7z" />
    </svg>
  )
}

export function IconPayment({ size = 24, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" className={className} aria-hidden="true">
      <rect x="2" y="5" width="20" height="14" rx="2" /><path d="M2 10h20" />
    </svg>
  )
}
