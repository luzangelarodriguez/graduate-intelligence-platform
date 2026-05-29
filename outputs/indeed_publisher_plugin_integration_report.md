# Indeed Publisher Plugin Integration Report

La documentacion oficial describe un widget frontend de busqueda laboral, no una API de extraccion.
El pipeline usa estos criterios del plugin como contrato de busqueda y mantiene la extraccion estructurada en Partner API.

- Source status: credentials_missing
- Plugin type: job-search
- Search limit: 10
- Search what: Data Analyst OR Business Intelligence OR Power BI OR SQL OR Analytics
- Search where: Colombia
- Validation errors: missing_partner_app_id, missing_placement_id

## Embed HTML sugerido

```html
<script src="https://plugins.indeed.com/publisher-plugin/main.js" crossorigin defer></script>
<div id="indeed-plugin-root"
    data-indeed-plugin-type="job-search"
    data-indeed-search-limit="10"
    data-indeed-search-what="Data Analyst OR Business Intelligence OR Power BI OR SQL OR Analytics"
    data-indeed-search-where="Colombia"></div>
<script>
  document.getElementById("indeed-plugin-root")?.addEventListener("indeed-plugin-event", (event) => {
    const detail = event.detail || {};
    if (detail.type === "load") {
      console.info("Indeed publisher plugin load", { success: Boolean(detail.payload && detail.payload.success) });
    }
  });
</script>
```

## JSON

```json
{
  "plugin_type": "job-search",
  "partner_app_id": "",
  "placement_id": "",
  "search_limit": 10,
  "search_what": "Data Analyst OR Business Intelligence OR Power BI OR SQL OR Analytics",
  "search_where": "Colombia",
  "search_job_types": "",
  "search_occupations": "",
  "source_status": "credentials_missing",
  "validation_errors": [
    "missing_partner_app_id",
    "missing_placement_id"
  ],
  "plugin_script_url": "https://plugins.indeed.com/publisher-plugin/main.js",
  "query_used_for_api_extraction": "Data Analyst OR Business Intelligence OR Power BI OR SQL OR Analytics"
}
```
