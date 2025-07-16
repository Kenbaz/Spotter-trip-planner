interface SEOProps {
  title?: string;
  description?: string;
  keywords?: string;
  ogTitle?: string;
  ogDescription?: string;
  ogImage?: string;
  canonical?: string;
  noIndex?: boolean;
}

const DEFAULT_TITLE = 'Spotter HOS Trip Planner';
const DEFAULT_DESCRIPTION =
  "Plan HOS-compliant truck trips with automatic compliance checking. Manage your driving hours, routes, and trip planning efficiently.";
const DEFAULT_KEYWORDS =
  "truck driving, HOS compliance, trip planner, hours of service, trucking, logistics, route planning";


export function SEO({
  title,
  description = DEFAULT_DESCRIPTION,
  keywords = DEFAULT_KEYWORDS,
  ogTitle,
  ogDescription,
  ogImage,
  canonical,
  noIndex = false,
}: SEOProps) {
    const fullTitle = title ? `${title} | ${DEFAULT_TITLE}` : DEFAULT_TITLE;
    const finalOgTitle = ogTitle || fullTitle || DEFAULT_TITLE;
    const finalOgDescription = ogDescription || description;
    const finalCanonical = canonical || window.location.href;

    return (
      <>
        <title>{fullTitle}</title>
        <meta name="description" content={description} />
        <meta name="keywords" content={keywords} />

        {noIndex && <meta name="robots" content="noindex,nofollow" />}

        {/* Open Graph */}
        <meta property="og:title" content={finalOgTitle} />
        <meta property="og:description" content={finalOgDescription} />
        <meta property="og:type" content="website" />
        <meta property="og:url" content={finalCanonical} />
        {ogImage && <meta property="og:image" content={ogImage} />}

        {/* Twitter Card */}
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content={finalOgTitle} />
        <meta name="twitter:description" content={finalOgDescription} />
        {ogImage && <meta name="twitter:image" content={ogImage} />}

        {/* Canonical URL */}
        <link rel="canonical" href={finalCanonical} />

        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <meta name="format-detection" content="telephone=no" />
      </>
    );
}