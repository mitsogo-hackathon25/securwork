import { forwardRef, useCallback, useEffect, useImperativeHandle, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { CustomizationDesign, CustomizationOption } from '../api/types'
import { uploadCustomization } from '../api/store'
import { renderCustomizationPreview } from '../utils/customizationPreview'
import './ProductCustomizer.css'

export interface ProductCustomizerHandle {
  upload: () => Promise<number>
  hasLogo: () => boolean
}

interface Props {
  mockupUrl: string
  variantId: number
  options: CustomizationOption[]
  onReadyChange?: (ready: boolean) => void
}

const DEFAULT_DESIGN: CustomizationDesign = {
  view: 'front',
  x_pct: 0.35,
  y_pct: 0.28,
  width_pct: 0.3,
  height_pct: 0.22,
  rotation: 0,
}

const formatFee = (fee: string) =>
  `€ ${parseFloat(fee || '0').toFixed(2).replace('.', ',')}`

const ProductCustomizer = forwardRef<ProductCustomizerHandle, Props>(function ProductCustomizer({
  mockupUrl,
  variantId,
  options,
  onReadyChange,
}, ref) {
  const { t } = useTranslation()
  const stageRef = useRef<HTMLDivElement>(null)
  const [method, setMethod] = useState<string>(options[0]?.code || '')
  const [logoFile, setLogoFile] = useState<File | null>(null)
  const [logoPreview, setLogoPreview] = useState<string | null>(null)
  const [design, setDesign] = useState<CustomizationDesign>(DEFAULT_DESIGN)
  const [dragging, setDragging] = useState(false)
  const dragOffset = useRef({ x: 0, y: 0 })

  useEffect(() => {
    if (!options.length) {
      setMethod('')
      return
    }
    if (!options.some((option) => option.code === method)) {
      setMethod(options[0].code)
    }
  }, [options, method])

  const selectedOption = options.find((option) => option.code === method) || options[0]
  const customizationFee = selectedOption?.fee

  useEffect(() => {
    onReadyChange?.(Boolean(logoFile && method))
  }, [logoFile, method, onReadyChange])

  useEffect(() => {
    return () => {
      if (logoPreview) URL.revokeObjectURL(logoPreview)
    }
  }, [logoPreview])

  const handleLogoUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    if (logoPreview) URL.revokeObjectURL(logoPreview)
    setLogoFile(file)
    setLogoPreview(URL.createObjectURL(file))
  }

  const onPointerDown = (e: React.PointerEvent<HTMLImageElement>) => {
    if (!stageRef.current) return
    const rect = stageRef.current.getBoundingClientRect()
    dragOffset.current = {
      x: e.clientX - rect.left - design.x_pct * rect.width,
      y: e.clientY - rect.top - design.y_pct * rect.height,
    }
    setDragging(true)
    e.currentTarget.setPointerCapture(e.pointerId)
  }

  const onPointerMove = (e: React.PointerEvent<HTMLImageElement>) => {
    if (!dragging || !stageRef.current) return
    const rect = stageRef.current.getBoundingClientRect()
    const x = (e.clientX - rect.left - dragOffset.current.x) / rect.width
    const y = (e.clientY - rect.top - dragOffset.current.y) / rect.height
    setDesign((prev) => ({
      ...prev,
      x_pct: Math.min(Math.max(x, 0), 1 - prev.width_pct),
      y_pct: Math.min(Math.max(y, 0), 1 - prev.height_pct),
    }))
  }

  const onPointerUp = (e: React.PointerEvent<HTMLImageElement>) => {
    setDragging(false)
    e.currentTarget.releasePointerCapture(e.pointerId)
  }

  const upload = useCallback(async (): Promise<number> => {
    if (!logoFile || !method) throw new Error('No logo')
    const previewBlob = await renderCustomizationPreview(mockupUrl, logoFile, design)
    const previewFile = new File([previewBlob], 'preview.png', { type: 'image/png' })
    const result = await uploadCustomization({
      variantId,
      logo: logoFile,
      preview: previewFile,
      designData: design,
      method,
    })
    return result.id
  }, [logoFile, mockupUrl, design, variantId, method])

  useImperativeHandle(ref, () => ({
    upload,
    hasLogo: () => Boolean(logoFile && method),
  }), [upload, logoFile, method])

  return (
    <div className="product-customizer">
      <h3>{t('customizer.title')}</h3>
      <p className="product-customizer-desc">{t('customizer.subtitle')}</p>

      <label className="product-customizer-method">
        {t('customizer.method')}
        <select value={method} onChange={(e) => setMethod(e.target.value)}>
          {options.map((option) => (
            <option key={option.code} value={option.code}>
              {option.label} — {formatFee(option.fee)}
            </option>
          ))}
        </select>
      </label>

      {customizationFee && parseFloat(customizationFee) > 0 && (
        <p className="product-customizer-fee">
          {t('customizer.fee', { price: formatFee(customizationFee) })}
        </p>
      )}

      <label className="product-customizer-upload">
        <span className="btn btn-secondary">{t('customizer.uploadLogo')}</span>
        <input type="file" accept="image/png,image/jpeg,image/webp,image/svg+xml" onChange={handleLogoUpload} />
      </label>

      <div className="product-customizer-stage" ref={stageRef}>
        <img src={mockupUrl} alt="" className="product-customizer-mockup" draggable={false} />
        {logoPreview && (
          <img
            src={logoPreview}
            alt=""
            className="product-customizer-logo"
            style={{
              left: `${design.x_pct * 100}%`,
              top: `${design.y_pct * 100}%`,
              width: `${design.width_pct * 100}%`,
              height: `${design.height_pct * 100}%`,
              transform: `rotate(${design.rotation}deg)`,
            }}
            onPointerDown={onPointerDown}
            onPointerMove={onPointerMove}
            onPointerUp={onPointerUp}
            draggable={false}
          />
        )}
        <div className="product-customizer-zone" aria-hidden="true" />
      </div>

      {logoPreview && (
        <div className="product-customizer-controls">
          <label>
            {t('customizer.size')}
            <input
              type="range"
              min={10}
              max={50}
              value={Math.round(design.width_pct * 100)}
              onChange={(e) => {
                const width = parseInt(e.target.value, 10) / 100
                const aspect = design.height_pct / design.width_pct
                setDesign((prev) => ({
                  ...prev,
                  width_pct: width,
                  height_pct: width * aspect,
                  x_pct: Math.min(prev.x_pct, 1 - width),
                  y_pct: Math.min(prev.y_pct, 1 - width * aspect),
                }))
              }}
            />
          </label>
          <label>
            {t('customizer.rotation')}
            <input
              type="range"
              min={-45}
              max={45}
              value={design.rotation}
              onChange={(e) => setDesign((prev) => ({ ...prev, rotation: parseInt(e.target.value, 10) }))}
            />
          </label>
          <p className="product-customizer-hint">{t('customizer.dragHint')}</p>
        </div>
      )}
    </div>
  )
})

export default ProductCustomizer
