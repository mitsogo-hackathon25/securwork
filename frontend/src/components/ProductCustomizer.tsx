import { forwardRef, useCallback, useEffect, useImperativeHandle, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { CustomizationDesign } from '../api/types'
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
  customizationFee?: string | null
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

const ProductCustomizer = forwardRef<ProductCustomizerHandle, Props>(function ProductCustomizer({
  mockupUrl,
  variantId,
  customizationFee,
  onReadyChange,
}, ref) {
  const { t } = useTranslation()
  const stageRef = useRef<HTMLDivElement>(null)
  const [logoFile, setLogoFile] = useState<File | null>(null)
  const [logoPreview, setLogoPreview] = useState<string | null>(null)
  const [design, setDesign] = useState<CustomizationDesign>(DEFAULT_DESIGN)
  const [dragging, setDragging] = useState(false)
  const dragOffset = useRef({ x: 0, y: 0 })

  useEffect(() => {
    onReadyChange?.(Boolean(logoFile))
  }, [logoFile, onReadyChange])

  useEffect(() => {
    return () => {
      if (logoPreview) URL.revokeObjectURL(logoPreview)
    }
  }, [logoPreview])

  const handleLogoUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (!file.type.startsWith('image/')) return
    setLogoFile(file)
    setLogoPreview(URL.createObjectURL(file))
    e.target.value = ''
  }

  const onPointerDown = (e: React.PointerEvent) => {
    if (!stageRef.current) return
    const rect = stageRef.current.getBoundingClientRect()
    const pointerX = (e.clientX - rect.left) / rect.width
    const pointerY = (e.clientY - rect.top) / rect.height
    dragOffset.current = {
      x: pointerX - design.x_pct,
      y: pointerY - design.y_pct,
    }
    setDragging(true)
    ;(e.target as HTMLElement).setPointerCapture(e.pointerId)
  }

  const onPointerMove = (e: React.PointerEvent) => {
    if (!dragging || !stageRef.current) return
    const rect = stageRef.current.getBoundingClientRect()
    const x = (e.clientX - rect.left) / rect.width - dragOffset.current.x
    const y = (e.clientY - rect.top) / rect.height - dragOffset.current.y
    setDesign((prev) => ({
      ...prev,
      x_pct: Math.min(Math.max(x, 0), 1 - prev.width_pct),
      y_pct: Math.min(Math.max(y, 0), 1 - prev.height_pct),
    }))
  }

  const onPointerUp = (e: React.PointerEvent) => {
    setDragging(false)
    ;(e.target as HTMLElement).releasePointerCapture(e.pointerId)
  }

  const upload = useCallback(async (): Promise<number> => {
    if (!logoFile) throw new Error('No logo')
    const previewBlob = await renderCustomizationPreview(mockupUrl, logoFile, design)
    const previewFile = new File([previewBlob], 'preview.png', { type: 'image/png' })
    const result = await uploadCustomization({
      variantId,
      logo: logoFile,
      preview: previewFile,
      designData: design,
    })
    return result.id
  }, [logoFile, mockupUrl, design, variantId])

  useImperativeHandle(ref, () => ({
    upload,
    hasLogo: () => Boolean(logoFile),
  }), [upload, logoFile])

  return (
    <div className="product-customizer">
      <h3>{t('customizer.title')}</h3>
      <p className="product-customizer-desc">{t('customizer.subtitle')}</p>
      {customizationFee && parseFloat(customizationFee) > 0 && (
        <p className="product-customizer-fee">
          {t('customizer.fee', { price: `€ ${parseFloat(customizationFee).toFixed(2).replace('.', ',')}` })}
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
