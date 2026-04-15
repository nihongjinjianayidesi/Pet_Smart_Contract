function toHex(buffer: ArrayBuffer) {
  const bytes = new Uint8Array(buffer)
  return Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('')
}

export async function sha256HexFromArrayBuffer(buffer: ArrayBuffer) {
  const digest = await crypto.subtle.digest('SHA-256', buffer)
  return toHex(digest)
}

export async function sha256HexFromText(text: string) {
  const enc = new TextEncoder()
  return sha256HexFromArrayBuffer(enc.encode(text).buffer)
}

export async function sha256HexFromFile(file: File) {
  const buffer = await file.arrayBuffer()
  return sha256HexFromArrayBuffer(buffer)
}

