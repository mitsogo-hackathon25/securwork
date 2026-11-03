/** Gzip-compress CSV uploads so they pass nginx limits (e.g. 1MB) when the server is not yet reconfigured. */

export async function compressCsvFileForUpload(
  file: File,
): Promise<{ blob: Blob; filename: string }> {
  const baseName = file.name?.trim() || 'import.csv'
  if (typeof CompressionStream === 'undefined') {
    return { blob: file, filename: baseName }
  }
  try {
    const stream = file.stream().pipeThrough(new CompressionStream('gzip'))
    const ab = await new Response(stream).arrayBuffer()
    const gz = new Blob([ab], { type: 'application/gzip' })
    if (gz.size < file.size) {
      const filename = baseName.toLowerCase().endsWith('.gz') ? baseName : `${baseName}.gz`
      return { blob: gz, filename }
    }
  } catch {
    /* fall back to raw file */
  }
  return { blob: file, filename: baseName }
}

export async function buildCsvUploadForm(
  file: File,
  extraFields?: Record<string, string>,
): Promise<FormData> {
  const { blob, filename } = await compressCsvFileForUpload(file)
  const form = new FormData()
  form.append('file', blob, filename)
  if (extraFields) {
    for (const [key, value] of Object.entries(extraFields)) {
      form.append(key, value)
    }
  }
  return form
}
