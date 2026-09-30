import { Helmet } from 'react-helmet-async'

interface OrganizationSchemaProps {
  url?: string
}

export function OrganizationSchema({ url = 'https://www.securwork.it' }: OrganizationSchemaProps) {
  const schema = {
    '@context': 'https://schema.org',
    '@type': 'Organization',
    name: 'SecurWork',
    url,
    description: 'Professional workwear and occupational clothing in Italy.',
    address: {
      '@type': 'PostalAddress',
      addressCountry: 'IT',
    },
  }

  return (
    <Helmet>
      <script type="application/ld+json">{JSON.stringify(schema)}</script>
    </Helmet>
  )
}

interface ProductSchemaProps {
  name: string
  description?: string
  sku: string
  image?: string | null
  price?: string | null
  inStock: boolean
  url: string
}

export function ProductSchema({ name, description, sku, image, price, inStock, url }: ProductSchemaProps) {
  const schema = {
    '@context': 'https://schema.org',
    '@type': 'Product',
    name,
    description: description || name,
    sku,
    image: image || undefined,
    offers: {
      '@type': 'Offer',
      url,
      priceCurrency: 'EUR',
      price: price || undefined,
      availability: inStock
        ? 'https://schema.org/InStock'
        : 'https://schema.org/OutOfStock',
    },
  }

  return (
    <Helmet>
      <script type="application/ld+json">{JSON.stringify(schema)}</script>
    </Helmet>
  )
}

interface BreadcrumbSchemaProps {
  items: { name: string; url: string }[]
}

export function BreadcrumbSchema({ items }: BreadcrumbSchemaProps) {
  const schema = {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: items.map((item, i) => ({
      '@type': 'ListItem',
      position: i + 1,
      name: item.name,
      item: item.url,
    })),
  }

  return (
    <Helmet>
      <script type="application/ld+json">{JSON.stringify(schema)}</script>
    </Helmet>
  )
}
