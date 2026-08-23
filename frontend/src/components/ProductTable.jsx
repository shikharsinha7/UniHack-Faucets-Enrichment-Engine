const CONFIDENCE_COLORS = { high: "#1e7e34", medium: "#b8860b", low: "#c0392b" };
const CONFIDENCE_BG = { high: "#e6f4ea", medium: "#fdf3d9", low: "#fbeae9" };

function Badge({ confidence }) {
  return (
    <span style={{
      color: CONFIDENCE_COLORS[confidence], background: CONFIDENCE_BG[confidence],
      padding: "2px 8px", borderRadius: 12, fontSize: 11, fontWeight: 600, textTransform: "uppercase",
    }}>
      {confidence}
    </span>
  );
}

function Field({ field }) {
  if (!field) return <span>-</span>;
  return (
    <div>
      <div>{field.value}</div>
      <div style={{ marginTop: 4 }}><Badge confidence={field.confidence} /></div>
    </div>
  );
}

function AttributeChips({ attributes }) {
  if (!attributes || attributes.length === 0) return <span style={{ color: "#999" }}>none extracted</span>;
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
      {attributes.map((a, i) => (
        <span key={i} title={`Source: ${a.value.source || "inferred, unverified"}`} style={{
          fontSize: 12, padding: "3px 8px", borderRadius: 6,
          background: a.value.lov_compliant ? "#e6f4ea" : "#fbeae9",
          color: a.value.lov_compliant ? "#1e7e34" : "#c0392b",
          border: `1px solid ${a.value.lov_compliant ? "#b7dfc2" : "#f3c5c0"}`,
        }}>
          {a.label}: {a.value.value}{a.uom ? ` ${a.uom}` : ""}{!a.value.lov_compliant && " ⚠"}
        </span>
      ))}
    </div>
  );
}

export default function ProductTable({ products }) {
  if (!products || products.length === 0) {
    return <p style={{ color: "#888" }}>No enriched products yet. Submit one above.</p>;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {products.map((p, index) => (
        <div key={`${p.mfg_part_num || "product"}-${index}`} style={{
          background: "#fff", borderRadius: 8, padding: 18,
          borderLeft: `4px solid ${p.needs_human_review ? CONFIDENCE_COLORS.low : CONFIDENCE_COLORS.high}`,
          boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 10 }}>
            <div>
              <strong style={{ fontSize: 16 }}>{p.mfg_part_num}</strong>
              <span style={{ color: "#888", marginLeft: 10, fontSize: 13 }}>{p.part_desc}</span>
            </div>
            <span style={{
              fontWeight: 700,
              color: p.needs_human_review ? CONFIDENCE_COLORS.low : CONFIDENCE_COLORS.high,
            }}>
              {p.needs_human_review ? "⚠ Needs Review" : "✓ Verified"}
            </span>
          </div>

          <div style={{ fontSize: 12, color: "#666", marginBottom: 12 }}>{p.classpath}</div>

          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
            <tbody>
              <tr><td style={{ padding: "6px 8px", width: 160, color: "#666" }}>Manufacturer</td><td style={{ padding: "6px 8px" }}><Field field={p.manufacturer_name} /></td></tr>
              <tr><td style={{ padding: "6px 8px", color: "#666" }}>Brand</td><td style={{ padding: "6px 8px" }}><Field field={p.brand_name} /></td></tr>
              <tr><td style={{ padding: "6px 8px", color: "#666" }}>Invoice Desc (≤40, CAPS)</td><td style={{ padding: "6px 8px" }}><Field field={p.invoice_desc} /></td></tr>
              <tr><td style={{ padding: "6px 8px", color: "#666" }}>Mobile Desc (60-80)</td><td style={{ padding: "6px 8px" }}><Field field={p.mobile_desc} /></td></tr>
              <tr><td style={{ padding: "6px 8px", color: "#666" }}>Short Desc / Title</td><td style={{ padding: "6px 8px" }}><Field field={p.short_desc} /></td></tr>
              <tr><td style={{ padding: "6px 8px", color: "#666" }}>Long Desc</td><td style={{ padding: "6px 8px" }}><Field field={p.long_desc} /></td></tr>
              <tr>
                <td style={{ padding: "6px 8px", color: "#666", verticalAlign: "top" }}>Attributes</td>
                <td style={{ padding: "6px 8px" }}><AttributeChips attributes={p.attributes} /></td>
              </tr>
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );
}
