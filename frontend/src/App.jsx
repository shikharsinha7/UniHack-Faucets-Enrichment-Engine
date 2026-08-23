import { useState, useRef } from "react";
import ProductTable from "./components/ProductTable.jsx";

export default function App() {
  // Single-item form state
  const [mfgPartNum, setMfgPartNum] = useState("");
  const [partDesc, setPartDesc] = useState("");
  const [partManuf, setPartManuf] = useState("");
  const [singleLoading, setSingleLoading] = useState(false);

  // Batch CSV upload state
  const [selectedFile, setSelectedFile] = useState(null);
  const [csvLoading, setCsvLoading] = useState(false);
  const fileInputRef = useRef(null);

  // Products and status state
  const [products, setProducts] = useState([]);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);
  const [activeFilter, setActiveFilter] = useState("all"); // 'all' | 'flagged' | 'verified'

  const isBusy = singleLoading || csvLoading;

  async function handleSingleEnrich(e) {
    e.preventDefault();
    if (!mfgPartNum.trim() || !partDesc.trim()) return;

    setSingleLoading(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const res = await fetch("/enrich", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mfg_part_num: mfgPartNum.trim(),
          part_desc: partDesc.trim(),
          e1_brand: "-- Unbranded --",
          unilog_brand: "-- No Unilog Brand --",
          dib_brand: "-- No DIB Brand --",
          part_manuf: partManuf.trim() || null,
        }),
      });
      if (!res.ok) {
        const errJson = await res.json().catch(() => null);
        throw new Error(errJson?.detail || `Request failed: ${res.status}`);
      }
      const enriched = await res.json();
      setProducts((prev) => [enriched, ...prev]);
      setMfgPartNum("");
      setPartDesc("");
      setPartManuf("");
      setSuccessMsg(`Successfully enriched item: ${enriched.mfg_part_num}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setSingleLoading(false);
    }
  }

  async function handleCsvUpload(e) {
    e.preventDefault();
    if (!selectedFile) {
      setError("Please choose a CSV file to upload.");
      return;
    }

    setCsvLoading(true);
    setError(null);
    setSuccessMsg(null);

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const res = await fetch("/enrich/upload-csv", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => null);
        throw new Error(errJson?.detail || `CSV upload failed with status ${res.status}`);
      }

      const data = await res.json();
      // data: { results: EnrichedProduct[], total: number, flagged_for_review: number }
      setProducts((prev) => [...data.results, ...prev]);
      setSuccessMsg(
        `Enriched ${data.total} item(s) from CSV: ${data.total - data.flagged_for_review} verified, ${data.flagged_for_review} flagged for review.`
      );
      setSelectedFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setCsvLoading(false);
    }
  }

  function handleFileChange(e) {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setError(null);
    }
  }

  function downloadSampleCsv() {
    const csvContent =
      "Mfg_Part_Num,Part_Desc,E1_Brand,Unilog_Brand,DIB_Brand,Part_Manuf\n" +
      "7594,Moen 7594 Arbor Pulldown Kitchen Faucet,-- Unbranded --,-- No Unilog Brand --,-- No DIB Brand --,Moen Inc\n" +
      "9178-AR-DST,Delta 9178-AR-DST Trinsic Single Handle Pull-Down,-- Unbranded --,-- No Unilog Brand --,-- No DIB Brand --,Delta Faucet Co\n" +
      "K-596-VS,Kohler K-596-VS Simplice Pull-Down Kitchen Faucet,-- Unbranded --,-- No Unilog Brand --,-- No DIB Brand --,Kohler Co\n" +
      "UNKNOWN-100,Generic Replacement Plastic Faucet Cartridge,-- Unbranded --,-- No Unilog Brand --,-- No DIB Brand --,Unknown Generic";

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "sample_faucets_upload.csv";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  // Summary counts
  const totalCount = products.length;
  const flaggedCount = products.filter((p) => p.needs_human_review).length;
  const verifiedCount = totalCount - flaggedCount;

  // Filtered view
  const displayedProducts = products.filter((p) => {
    if (activeFilter === "flagged") return p.needs_human_review;
    if (activeFilter === "verified") return !p.needs_human_review;
    return true;
  });

  return (
    <div style={{ maxWidth: 1080, margin: "0 auto", padding: "40px 20px" }}>
      {/* Header */}
      <header style={{ marginBottom: 28 }}>
        <h1 style={{ margin: "0 0 6px 0", fontSize: 28, color: "#0f172a", fontWeight: 700 }}>
          Faucets Enrichment &amp; Trust Engine
        </h1>
        <p style={{ color: "#64748b", margin: 0, fontSize: 15 }}>
          UniHack x Unilog — sparse distributor rows in, trust-scored Faucets catalog records out.
        </p>
      </header>

      {/* Action Controls Grid */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
        gap: 20,
        marginBottom: 28,
      }}>
        {/* CSV Batch Upload Card */}
        <div style={{
          background: "#ffffff",
          borderRadius: 10,
          padding: 22,
          boxShadow: "0 1px 4px rgba(0,0,0,0.06), 0 4px 12px rgba(0,0,0,0.03)",
          border: "1px solid #e2e8f0",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
        }}>
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
              <h2 style={{ fontSize: 16, margin: 0, color: "#1e293b", fontWeight: 600 }}>
                📁 Batch CSV Upload
              </h2>
              <button
                type="button"
                onClick={downloadSampleCsv}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "#2563eb",
                  fontSize: 12,
                  fontWeight: 500,
                  cursor: "pointer",
                  padding: "4px 6px",
                  textDecoration: "underline",
                }}
                title="Download 6-column sample CSV"
              >
                Download Sample CSV
              </button>
            </div>

            <p style={{ fontSize: 13, color: "#64748b", margin: "0 0 14px 0", lineHeight: 1.4 }}>
              Upload CSV with the 6 standard columns: <code style={{ background: "#f1f5f9", padding: "2px 4px", borderRadius: 4, fontSize: 11 }}>Mfg_Part_Num</code>, <code style={{ background: "#f1f5f9", padding: "2px 4px", borderRadius: 4, fontSize: 11 }}>Part_Desc</code>, <code style={{ background: "#f1f5f9", padding: "2px 4px", borderRadius: 4, fontSize: 11 }}>Part_Manuf</code>, etc.
            </p>

            <form onSubmit={handleCsvUpload}>
              <div
                onClick={() => fileInputRef.current?.click()}
                style={{
                  border: "2px dashed #cbd5e1",
                  borderRadius: 8,
                  padding: "16px 14px",
                  textAlign: "center",
                  background: selectedFile ? "#f0fdf4" : "#f8fafc",
                  cursor: isBusy ? "not-allowed" : "pointer",
                  marginBottom: 14,
                  borderColor: selectedFile ? "#86efac" : "#cbd5e1",
                  transition: "all 0.2s ease",
                }}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv,text/csv"
                  onChange={handleFileChange}
                  disabled={isBusy}
                  style={{ display: "none" }}
                />
                {selectedFile ? (
                  <div>
                    <span style={{ fontSize: 14, fontWeight: 600, color: "#15803d" }}>
                      📄 {selectedFile.name}
                    </span>
                    <div style={{ fontSize: 12, color: "#64748b", marginTop: 2 }}>
                      ({(selectedFile.size / 1024).toFixed(1)} KB) — Click to change
                    </div>
                  </div>
                ) : (
                  <div>
                    <span style={{ fontSize: 13, color: "#475569", fontWeight: 500 }}>
                      Click to choose CSV file
                    </span>
                    <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 2 }}>
                      Accepts .csv format
                    </div>
                  </div>
                )}
              </div>

              <button
                type="submit"
                disabled={isBusy || !selectedFile}
                style={{
                  width: "100%",
                  padding: "10px 16px",
                  background: isBusy || !selectedFile ? "#94a3b8" : "#2563eb",
                  color: "#ffffff",
                  border: "none",
                  borderRadius: 6,
                  fontWeight: 600,
                  fontSize: 14,
                  cursor: isBusy || !selectedFile ? "not-allowed" : "pointer",
                  boxShadow: isBusy || !selectedFile ? "none" : "0 1px 3px rgba(37,99,235,0.3)",
                  transition: "background 0.2s ease",
                }}
              >
                {csvLoading ? (
                  <span><span className="spinner"></span>Processing Batch CSV...</span>
                ) : (
                  "Upload & Enrich CSV"
                )}
              </button>
            </form>
          </div>
        </div>

        {/* Single Item Form Card */}
        <div style={{
          background: "#ffffff",
          borderRadius: 10,
          padding: 22,
          boxShadow: "0 1px 4px rgba(0,0,0,0.06), 0 4px 12px rgba(0,0,0,0.03)",
          border: "1px solid #e2e8f0",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
        }}>
          <div>
            <h2 style={{ fontSize: 16, margin: "0 0 12px 0", color: "#1e293b", fontWeight: 600 }}>
              ⚡ Single Item Quick Enrich
            </h2>
            <form onSubmit={handleSingleEnrich} style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <input
                placeholder="Mfg_Part_Num (e.g. 7594, 9178-AR-DST)"
                value={mfgPartNum}
                onChange={(e) => setMfgPartNum(e.target.value)}
                required
                disabled={isBusy}
                style={{
                  padding: "9px 12px",
                  borderRadius: 6,
                  border: "1px solid #cbd5e1",
                  fontSize: 13,
                  outline: "none",
                }}
              />
              <input
                placeholder="Part_Desc (e.g. Moen 7594 Arbor Pulldown Faucet)"
                value={partDesc}
                onChange={(e) => setPartDesc(e.target.value)}
                required
                disabled={isBusy}
                style={{
                  padding: "9px 12px",
                  borderRadius: 6,
                  border: "1px solid #cbd5e1",
                  fontSize: 13,
                  outline: "none",
                }}
              />
              <input
                placeholder="Part_Manuf (optional, e.g. Moen Inc, Delta)"
                value={partManuf}
                onChange={(e) => setPartManuf(e.target.value)}
                disabled={isBusy}
                style={{
                  padding: "9px 12px",
                  borderRadius: 6,
                  border: "1px solid #cbd5e1",
                  fontSize: 13,
                  outline: "none",
                }}
              />
              <button
                type="submit"
                disabled={isBusy || !mfgPartNum.trim() || !partDesc.trim()}
                style={{
                  marginTop: 4,
                  padding: "10px 16px",
                  background: isBusy || !mfgPartNum.trim() || !partDesc.trim() ? "#94a3b8" : "#0f172a",
                  color: "#ffffff",
                  border: "none",
                  borderRadius: 6,
                  fontWeight: 600,
                  fontSize: 14,
                  cursor: isBusy || !mfgPartNum.trim() || !partDesc.trim() ? "not-allowed" : "pointer",
                  transition: "background 0.2s ease",
                }}
              >
                {singleLoading ? (
                  <span><span className="spinner"></span>Enriching Item...</span>
                ) : (
                  "Enrich Item"
                )}
              </button>
            </form>
          </div>
        </div>
      </div>

      {/* Notifications */}
      {error && (
        <div style={{
          padding: "12px 16px",
          background: "#fef2f2",
          color: "#991b1b",
          borderRadius: 8,
          border: "1px solid #fecaca",
          marginBottom: 24,
          fontSize: 14,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}>
          <span><strong>Error:</strong> {error}</span>
          <button
            onClick={() => setError(null)}
            style={{ background: "none", border: "none", color: "#991b1b", cursor: "pointer", fontSize: 16 }}
          >
            ×
          </button>
        </div>
      )}

      {successMsg && (
        <div style={{
          padding: "12px 16px",
          background: "#f0fdf4",
          color: "#166534",
          borderRadius: 8,
          border: "1px solid #bbf7d0",
          marginBottom: 24,
          fontSize: 14,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}>
          <span><strong>Success:</strong> {successMsg}</span>
          <button
            onClick={() => setSuccessMsg(null)}
            style={{ background: "none", border: "none", color: "#166534", cursor: "pointer", fontSize: 16 }}
          >
            ×
          </button>
        </div>
      )}

      {/* Loading Banner for Long Batches */}
      {csvLoading && (
        <div style={{
          padding: "16px 20px",
          background: "#eff6ff",
          borderRadius: 8,
          border: "1px solid #bfdbfe",
          marginBottom: 24,
          display: "flex",
          alignItems: "center",
          gap: 12,
          color: "#1e40af",
        }}>
          <span className="spinner" style={{ borderColor: "rgba(30,64,175,0.3)", borderTopColor: "#1e40af", width: 18, height: 18 }}></span>
          <div>
            <div style={{ fontWeight: 600, fontSize: 14 }}>Batch Enrichment in Progress...</div>
            <div style={{ fontSize: 12, color: "#3b82f6", marginTop: 2 }}>
              Parsing CSV rows, fetching manufacturer specs, validating attributes against LOV, and assembling compliance descriptions.
            </div>
          </div>
        </div>
      )}

      {/* Prominent Results Summary & Dashboard Counters */}
      <section style={{ marginBottom: 20 }}>
        <div style={{
          background: "#ffffff",
          borderRadius: 10,
          padding: "18px 22px",
          border: "1px solid #e2e8f0",
          boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 16,
        }}>
          {/* Metrics Badges / Cards */}
          <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 14 }}>
            {/* Total Count */}
            <div style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              padding: "8px 16px",
              background: "#f8fafc",
              borderRadius: 8,
              border: "1px solid #e2e8f0",
            }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                Total Products
              </span>
              <span style={{ fontSize: 22, fontWeight: 800, color: "#0f172a" }}>
                {totalCount}
              </span>
            </div>

            {/* Flagged For Review Count */}
            <div style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              padding: "8px 16px",
              background: flaggedCount > 0 ? "#fef2f2" : "#f8fafc",
              borderRadius: 8,
              border: `1px solid ${flaggedCount > 0 ? "#fecaca" : "#e2e8f0"}`,
            }}>
              <span style={{
                fontSize: 12,
                fontWeight: 600,
                color: flaggedCount > 0 ? "#b91c1c" : "#64748b",
                textTransform: "uppercase",
                letterSpacing: "0.5px",
                display: "flex",
                alignItems: "center",
                gap: 4,
              }}>
                ⚠ Flagged for Review
              </span>
              <span style={{
                fontSize: 22,
                fontWeight: 800,
                color: flaggedCount > 0 ? "#dc2626" : "#475569",
              }}>
                {flaggedCount}
              </span>
            </div>

            {/* Verified Count */}
            <div style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              padding: "8px 16px",
              background: verifiedCount > 0 ? "#f0fdf4" : "#f8fafc",
              borderRadius: 8,
              border: `1px solid ${verifiedCount > 0 ? "#bbf7d0" : "#e2e8f0"}`,
            }}>
              <span style={{
                fontSize: 12,
                fontWeight: 600,
                color: verifiedCount > 0 ? "#15803d" : "#64748b",
                textTransform: "uppercase",
                letterSpacing: "0.5px",
                display: "flex",
                alignItems: "center",
                gap: 4,
              }}>
                ✓ Auto-Verified
              </span>
              <span style={{
                fontSize: 22,
                fontWeight: 800,
                color: verifiedCount > 0 ? "#16a34a" : "#475569",
              }}>
                {verifiedCount}
              </span>
            </div>
          </div>

          {/* Action / Filter Controls */}
          {totalCount > 0 && (
            <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
              <div style={{
                display: "inline-flex",
                background: "#f1f5f9",
                borderRadius: 6,
                padding: 2,
              }}>
                <button
                  type="button"
                  onClick={() => setActiveFilter("all")}
                  style={{
                    padding: "6px 12px",
                    borderRadius: 5,
                    border: "none",
                    fontSize: 12,
                    fontWeight: 600,
                    cursor: "pointer",
                    background: activeFilter === "all" ? "#ffffff" : "transparent",
                    color: activeFilter === "all" ? "#0f172a" : "#64748b",
                    boxShadow: activeFilter === "all" ? "0 1px 2px rgba(0,0,0,0.08)" : "none",
                  }}
                >
                  All ({totalCount})
                </button>
                <button
                  type="button"
                  onClick={() => setActiveFilter("flagged")}
                  style={{
                    padding: "6px 12px",
                    borderRadius: 5,
                    border: "none",
                    fontSize: 12,
                    fontWeight: 600,
                    cursor: "pointer",
                    background: activeFilter === "flagged" ? "#ffffff" : "transparent",
                    color: activeFilter === "flagged" ? "#dc2626" : "#64748b",
                    boxShadow: activeFilter === "flagged" ? "0 1px 2px rgba(0,0,0,0.08)" : "none",
                  }}
                >
                  Needs Review ({flaggedCount})
                </button>
                <button
                  type="button"
                  onClick={() => setActiveFilter("verified")}
                  style={{
                    padding: "6px 12px",
                    borderRadius: 5,
                    border: "none",
                    fontSize: 12,
                    fontWeight: 600,
                    cursor: "pointer",
                    background: activeFilter === "verified" ? "#ffffff" : "transparent",
                    color: activeFilter === "verified" ? "#16a34a" : "#64748b",
                    boxShadow: activeFilter === "verified" ? "0 1px 2px rgba(0,0,0,0.08)" : "none",
                  }}
                >
                  Verified ({verifiedCount})
                </button>
              </div>

              <button
                type="button"
                onClick={() => setProducts([])}
                style={{
                  padding: "6px 12px",
                  borderRadius: 6,
                  border: "1px solid #e2e8f0",
                  background: "#ffffff",
                  color: "#64748b",
                  fontSize: 12,
                  fontWeight: 500,
                  cursor: "pointer",
                }}
                title="Clear all enriched results from view"
              >
                Clear All
              </button>
            </div>
          )}
        </div>
      </section>

      {/* Render Product Results via ProductTable */}
      <ProductTable products={displayedProducts} />
    </div>
  );
}

