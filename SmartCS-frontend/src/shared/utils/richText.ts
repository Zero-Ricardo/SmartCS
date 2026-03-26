const escapeHtml = (value: string) =>
  value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");

const linkify = (value: string) =>
  value.replace(
    /(https?:\/\/[^\s]+)/g,
    '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>'
  );

export const toRichHtml = (raw: string) => {
  const escaped = escapeHtml(raw);
  const lines = escaped.split("\n");
  const hasList = lines.some((line) => /^\s*-\s+/.test(line));
  if (!hasList) {
    return linkify(escaped).replaceAll("\n", "<br/>");
  }
  const transformed = lines
    .map((line) => {
      if (/^\s*-\s+/.test(line)) {
        return `<li>${linkify(line.replace(/^\s*-\s+/, ""))}</li>`;
      }
      return `<p>${linkify(line)}</p>`;
    })
    .join("");
  return transformed.replace(/(<li>.*?<\/li>)+/g, "<ul>$&</ul>");
};
