import type { CustomizationDesign } from '../api/types'

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.onload = () => resolve(img)
    img.onerror = reject
    img.src = src
  })
}

function loadImageFromFile(file: File): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => resolve(img)
    img.onerror = reject
    img.src = URL.createObjectURL(file)
  })
}

export async function renderCustomizationPreview(
  mockupUrl: string,
  logoFile: File,
  design: CustomizationDesign,
): Promise<Blob> {
  const [mockup, logo] = await Promise.all([
    loadImage(mockupUrl),
    loadImageFromFile(logoFile),
  ])

  const canvas = document.createElement('canvas')
  canvas.width = mockup.naturalWidth
  canvas.height = mockup.naturalHeight
  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error('Canvas not supported')

  ctx.drawImage(mockup, 0, 0, canvas.width, canvas.height)

  const x = design.x_pct * canvas.width
  const y = design.y_pct * canvas.height
  const w = design.width_pct * canvas.width
  const h = design.height_pct * canvas.height

  if (design.rotation) {
    ctx.save()
    ctx.translate(x + w / 2, y + h / 2)
    ctx.rotate((design.rotation * Math.PI) / 180)
    ctx.drawImage(logo, -w / 2, -h / 2, w, h)
    ctx.restore()
  } else {
    ctx.drawImage(logo, x, y, w, h)
  }

  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (blob) resolve(blob)
      else reject(new Error('Could not create preview image'))
    }, 'image/png')
  })
}
