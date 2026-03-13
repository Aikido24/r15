import { useEffect, useMemo, useState } from "react";

const DEFAULT_API_URL = "http://127.0.0.1:8001";
const POLLING_INTERVAL_MS = 1200;

function formatJson(value) {
  return JSON.stringify(value, null, 2);
}

function getConfidenceLabel(confidence) {
  switch (confidence) {
    case "high":
      return "Alta";
    case "medium":
      return "Media";
    default:
      return "Baja";
  }
}

function getLegibilityLabel(legibility) {
  switch (legibility) {
    case "clear":
      return "Claro";
    case "illegible":
      return "Ilegible";
    default:
      return "Dudoso";
  }
}

function getStageLabel(stage, currentPage, totalPages) {
  const pageSuffix =
    currentPage && totalPages ? ` (pagina ${currentPage} de ${totalPages})` : "";

  switch (stage) {
    case "queued":
      return "En cola";
    case "downloading_document":
      return "Descargando documento";
    case "saving_upload":
      return "Subiendo archivo";
    case "normalizing_pages":
      return `Normalizando paginas${pageSuffix}`;
    case "reading_document":
      return `Leyendo documento con IA${pageSuffix}`;
    case "parsing_fields":
      return "Consolidando campos";
    case "evaluating_rules":
      return "Validando reglas";
    case "building_report":
      return "Consolidando reporte";
    case "completed":
      return "Completado";
    case "failed":
      return "Fallido";
    default:
      return "Procesando";
  }
}

function StatusBadge({ ok }) {
  return (
    <span className={ok ? "badge badge-success" : "badge badge-danger"}>
      {ok ? "Aprobado" : "Rechazado"}
    </span>
  );
}

function ProgressPanel({
  jobStatus,
  jobStage,
  progressPercent,
  progressMessage,
  currentPage,
  totalPages,
  jobId,
}) {
  const title =
    jobStatus === "failed"
      ? "Error durante el analisis"
      : jobStatus === "completed"
        ? "Analisis completado"
        : "Procesando documento";

  return (
    <section className={`card progress-card status-${jobStatus || "queued"}`}>
      <div className="progress-header">
        <div>
          <p className="eyebrow">estado del job</p>
          <h2>{title}</h2>
        </div>
        <span className={`badge status-pill status-pill-${jobStatus || "queued"}`}>
          {jobStatus || "queued"}
        </span>
      </div>

      <p className="progress-stage">
        {getStageLabel(jobStage, currentPage, totalPages)}
      </p>
      <p className="progress-message">{progressMessage || "Esperando actualizacion..."}</p>

      <div className="progress-bar-shell" aria-hidden="true">
        <div
          className="progress-bar-fill"
          style={{ width: `${Math.max(0, Math.min(progressPercent, 100))}%` }}
        />
      </div>

      <div className="progress-meta">
        <span>{progressPercent}%</span>
        {jobId ? <code>{jobId}</code> : null}
      </div>
    </section>
  );
}

function SectionCard({ title, children }) {
  return (
    <section className="card">
      <h2>{title}</h2>
      {children}
    </section>
  );
}

function HandwrittenNumberList({ items }) {
  if (!items?.length) {
    return <p>No se detectaron numeros manuscritos.</p>;
  }

  return (
    <div className="stack">
      {items.map((item, index) => (
        <article
          key={`${item.page_number || "global"}-${item.region_description || "region"}-${index}`}
          className="list-item"
        >
          <div className="finding-header">
            <strong>{item.value || "Sin lectura confiable"}</strong>
            <span className={`tag severity-${item.legibility === "clear" ? "medium" : "high"}`}>
              {getLegibilityLabel(item.legibility)}
            </span>
          </div>
          <p>
            {item.page_number ? `Pagina ${item.page_number}. ` : ""}
            {item.region_description || "Region no especificada."}
          </p>
          <p>Confianza: {getConfidenceLabel(item.confidence)}</p>
          {item.reasoning ? <p>{item.reasoning}</p> : null}
        </article>
      ))}
    </div>
  );
}

function DetectedNumberList({ items }) {
  if (!items?.length) {
    return <p>No se detectaron numeros estructurados en esta seccion.</p>;
  }

  return (
    <div className="stack">
      {items.map((item, index) => (
        <article
          key={`${item.page_number || "global"}-${item.field_name || "field"}-${item.region_description || "region"}-${index}`}
          className="list-item"
        >
          <div className="finding-header">
            <strong>{item.value || "Sin lectura confiable"}</strong>
            <span className={`tag severity-${item.legibility === "clear" ? "medium" : "high"}`}>
              {item.number_kind === "handwritten" ? "Manuscrito" : item.number_kind === "printed" ? "Impreso" : "Desconocido"}
            </span>
          </div>
          <p>Campo: {item.field_name || "other"}</p>
          <p>{item.region_description || "Region no especificada."}</p>
          <p>
            Legibilidad: {getLegibilityLabel(item.legibility)}. Confianza: {getConfidenceLabel(item.confidence)}.
          </p>
          {item.reasoning ? <p>{item.reasoning}</p> : null}
        </article>
      ))}
    </div>
  );
}

function App() {
  const [apiBaseUrl, setApiBaseUrl] = useState(DEFAULT_API_URL);
  const [inputMode, setInputMode] = useState("url");
  const [documentUrl, setDocumentUrl] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [jobId, setJobId] = useState("");
  const [jobStatus, setJobStatus] = useState("");
  const [jobStage, setJobStage] = useState("queued");
  const [progressPercent, setProgressPercent] = useState(0);
  const [progressMessage, setProgressMessage] = useState("");
  const [currentPage, setCurrentPage] = useState(null);
  const [totalPages, setTotalPages] = useState(null);

  useEffect(() => {
    if (!jobId || jobStatus === "completed" || jobStatus === "failed") {
      return undefined;
    }

    const endpointBase = apiBaseUrl.replace(/\/$/, "");
    let timeoutId;
    let cancelled = false;

    async function pollJob() {
      try {
        const response = await fetch(`${endpointBase}/analysis-jobs/${jobId}`);
        const responseData = await response.json();
        if (!response.ok) {
          throw new Error(responseData.detail || "No se pudo consultar el progreso.");
        }

        if (cancelled) {
          return;
        }

        setJobStatus(responseData.status || "");
        setJobStage(responseData.stage || "queued");
        setProgressPercent(responseData.progress_percent ?? 0);
        setProgressMessage(responseData.message || "");
        setCurrentPage(responseData.current_page ?? null);
        setTotalPages(responseData.total_pages ?? null);

        if (responseData.status === "completed") {
          setResult(responseData.result || null);
          setSubmitting(false);
          return;
        }

        if (responseData.status === "failed") {
          setSubmitting(false);
          setError(responseData.error || responseData.message || "El analisis fallo.");
          return;
        }

        timeoutId = window.setTimeout(pollJob, POLLING_INTERVAL_MS);
      } catch (requestError) {
        if (cancelled) {
          return;
        }

        setSubmitting(false);
        setJobStatus("failed");
        setJobStage("failed");
        setError(
          requestError instanceof Error
            ? requestError.message
            : "No se pudo consultar el progreso.",
        );
      }
    }

    pollJob();

    return () => {
      cancelled = true;
      if (timeoutId) {
        window.clearTimeout(timeoutId);
      }
    };
  }, [apiBaseUrl, jobId]);

  function startFileJob(endpointBase, file) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      const formData = new FormData();
      formData.append("file", file);

      xhr.open("POST", `${endpointBase}/analysis-jobs/file`);
      xhr.responseType = "json";

      xhr.upload.onprogress = (event) => {
        if (!event.lengthComputable) {
          return;
        }

        const uploadPercent = Math.round((event.loaded / event.total) * 100);
        setJobStatus("running");
        setJobStage("saving_upload");
        setProgressPercent(uploadPercent);
        setProgressMessage(`Subiendo archivo local (${uploadPercent}%).`);
        setCurrentPage(null);
        setTotalPages(null);
      };

      xhr.onerror = () => reject(new Error("No se pudo subir el archivo al backend."));
      xhr.onload = () => {
        const responseData =
          xhr.response && typeof xhr.response === "object"
            ? xhr.response
            : JSON.parse(xhr.responseText || "{}");

        if (xhr.status < 200 || xhr.status >= 300) {
          reject(
            new Error(responseData.detail || "No se pudo crear el job para el archivo."),
          );
          return;
        }

        resolve(responseData);
      };

      xhr.send(formData);
    });
  }

  const requestPreview = useMemo(
    () =>
      inputMode === "url"
        ? {
            document_url: documentUrl || "<url-del-documento>",
          }
        : {
            file: selectedFile?.name || "<archivo-local.pdf>",
          },
    [documentUrl, inputMode, selectedFile],
  );

  async function handleSubmit(event) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    setJobId("");
    setJobStatus("queued");
    setJobStage(inputMode === "file" ? "saving_upload" : "queued");
    setProgressPercent(0);
    setProgressMessage(
      inputMode === "file"
        ? "Preparando subida del archivo local."
        : "Creando trabajo de analisis.",
    );
    setCurrentPage(null);
    setTotalPages(null);

    try {
      const endpointBase = apiBaseUrl.replace(/\/$/, "");
      const response =
        inputMode === "url"
          ? await fetch(`${endpointBase}/analysis-jobs`, {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
              },
              body: JSON.stringify({
                document_url: documentUrl,
              }),
            })
          : await startFileJob(endpointBase, selectedFile);

      const responseData =
        inputMode === "url" ? await response.json() : response;
      if (inputMode === "url" && !response.ok) {
        throw new Error(responseData.detail || "No se pudo crear el job.");
      }

      setJobId(responseData.job_id || "");
      setJobStatus(responseData.status || "queued");
      setJobStage(responseData.stage || "queued");
      setProgressPercent(responseData.progress_percent ?? 0);
      setProgressMessage(responseData.message || "Trabajo creado.");
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Ocurrio un error inesperado.",
      );
      setJobStatus("failed");
      setJobStage("failed");
      setSubmitting(false);
    }
  }

  const shouldShowProgress =
    submitting || jobId || jobStatus === "completed" || jobStatus === "failed";
  const handwrittenNumbers = result?.visual_checks?.handwritten_numbers || [];
  const rejectedByStrikeout = result?.findings?.some((finding) => finding.type === "visual_strikeout");

  return (
    <main className="layout">
      <header className="hero">
        <div>
          <p className="eyebrow">cliente_web</p>
          <h1>Document Analyzer</h1>
          <p className="hero-copy">
            Cliente React para enviar imagenes o PDFs por URL al backend y revisar
            lectura visual con IA, validaciones, hallazgos y detalle por pagina.
          </p>
        </div>
      </header>

      <SectionCard title="Enviar documento">
        <form className="form-grid" onSubmit={handleSubmit}>
          <label>
            API base URL
            <input
              type="url"
              value={apiBaseUrl}
              onChange={(event) => setApiBaseUrl(event.target.value)}
              placeholder="http://127.0.0.1:8001"
              required
            />
          </label>

          <div className="input-mode-group">
            <span>Origen del documento</span>
            <div className="mode-buttons">
              <button
                type="button"
                className={inputMode === "url" ? "mode-button active" : "mode-button"}
                onClick={() => setInputMode("url")}
                disabled={submitting}
              >
                URL
              </button>
              <button
                type="button"
                className={inputMode === "file" ? "mode-button active" : "mode-button"}
                onClick={() => setInputMode("file")}
                disabled={submitting}
              >
                Archivo local
              </button>
            </div>
          </div>

          {inputMode === "url" ? (
            <label key="document-url-input">
              URL del documento
              <input
                type="url"
                value={documentUrl}
                onChange={(event) => setDocumentUrl(event.target.value)}
                placeholder="https://sitio.com/documento.pdf"
                required
                disabled={submitting}
              />
            </label>
          ) : (
            <label key="document-file-input">
              Archivo PDF o imagen
              <input
                type="file"
                accept=".pdf,image/*"
                onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
                required
                disabled={submitting}
              />
            </label>
          )}

          <div className="actions">
            <button
              type="submit"
              disabled={
                submitting ||
                (inputMode === "url" ? !documentUrl.trim() : !selectedFile)
              }
            >
              {submitting ? "Procesando..." : "Analizar documento"}
            </button>
          </div>
        </form>

        <div className="request-preview">
          <h3>Payload</h3>
          <pre>{formatJson(requestPreview)}</pre>
        </div>

        {error ? <p className="error-box">{error}</p> : null}
      </SectionCard>

      {shouldShowProgress ? (
        <ProgressPanel
          jobStatus={jobStatus}
          jobStage={jobStage}
          progressPercent={progressPercent}
          progressMessage={progressMessage}
          currentPage={currentPage}
          totalPages={totalPages}
          jobId={jobId}
        />
      ) : null}

      {result ? (
        <>
          <SectionCard title="Resultado general">
            <div className="summary-row">
              <StatusBadge ok={result.ok} />
              <p>{result.summary || result.message}</p>
            </div>
            {!result.ok && rejectedByStrikeout ? (
              <p className="error-box">
                Documento rechazado automaticamente porque se detectaron tachones.
              </p>
            ) : null}
            <dl className="meta-grid">
              <div>
                <dt>Tipo</dt>
                <dd>{result.document_kind}</dd>
              </div>
              <div>
                <dt>Paginas</dt>
                <dd>{result.page_count}</dd>
              </div>
              <div>
                <dt>Archivo</dt>
                <dd>{result.file_name}</dd>
              </div>
              <div>
                <dt>Contenido</dt>
                <dd>{result.content_type}</dd>
              </div>
            </dl>
          </SectionCard>

          <SectionCard title="Numeros manuscritos detectados">
            <HandwrittenNumberList items={handwrittenNumbers} />
          </SectionCard>

          <SectionCard title="Lectura visual por IA">
            <DetectedNumberList items={result.visual_checks?.detected_numbers || []} />
          </SectionCard>

          <SectionCard title="Campos parseados">
            <pre>{formatJson(result.parsed_fields || {})}</pre>
          </SectionCard>

          <SectionCard title="Reglas matematicas">
            <div className="stack">
              {result.rule_checks?.map((check) => (
                <article key={check.rule} className="list-item">
                  <strong>{check.rule}</strong>
                  <span className={check.passed ? "tag ok" : "tag fail"}>
                    {check.passed ? "OK" : "Fallo"}
                  </span>
                  <p>{check.message}</p>
                </article>
              ))}
            </div>
          </SectionCard>

          <SectionCard title="Analisis visual global">
            <pre>{formatJson(result.visual_checks || {})}</pre>
          </SectionCard>

          <SectionCard title="Hallazgos globales">
            {result.findings?.length ? (
              <div className="stack">
                {result.findings.map((finding, index) => (
                  <article key={`${finding.type}-${index}`} className="list-item">
                    <div className="finding-header">
                      <strong>{finding.type}</strong>
                      <span className={`tag severity-${finding.severity}`}>
                        {finding.severity}
                      </span>
                    </div>
                    <p>{finding.message}</p>
                  </article>
                ))}
              </div>
            ) : (
              <p>No se registraron hallazgos globales.</p>
            )}
          </SectionCard>

          <SectionCard title="Paginas procesadas">
            <div className="stack">
              {result.pages?.map((page) => (
                <article key={page.page_number} className="page-card">
                  <div className="page-header">
                    <h3>Pagina {page.page_number}</h3>
                    <code>{page.image_path}</code>
                  </div>
                  <div className="page-grid">
                    <div>
                    <h4>Lectura visual por IA</h4>
                    <DetectedNumberList items={page.visual_checks?.detected_numbers || []} />
                    </div>
                    <div>
                      <h4>Analisis visual</h4>
                      <pre>{formatJson(page.visual_checks || {})}</pre>
                    </div>
                  </div>

                  <div>
                    <h4>Hallazgos de pagina</h4>
                    {page.findings?.length ? (
                      <div className="stack">
                        {page.findings.map((finding, index) => (
                          <article
                            key={`${page.page_number}-${finding.type}-${index}`}
                            className="list-item"
                          >
                            <div className="finding-header">
                              <strong>{finding.type}</strong>
                              <span className={`tag severity-${finding.severity}`}>
                                {finding.severity}
                              </span>
                            </div>
                            <p>{finding.message}</p>
                          </article>
                        ))}
                      </div>
                    ) : (
                      <p>No hay hallazgos para esta pagina.</p>
                    )}
                  </div>

                  <div>
                    <h4>Numeros manuscritos</h4>
                    <HandwrittenNumberList items={page.visual_checks?.handwritten_numbers || []} />
                  </div>
                </article>
              ))}
            </div>
          </SectionCard>

          <SectionCard title="Respuesta completa">
            <pre>{formatJson(result)}</pre>
          </SectionCard>
        </>
      ) : null}
    </main>
  );
}

export default App;
