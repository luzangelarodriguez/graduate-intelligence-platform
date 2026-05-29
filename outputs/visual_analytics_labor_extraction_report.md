# Visual Analytics Labor Extraction Report

- Run ID: `visual-analytics-20260526152121-0825c11c`
- Fuentes configuradas: 9
- Empleos extraidos: 0
- Empleos descartados: 4
- Duplicados suprimidos: 0
- Gold jobs validos: 0
- Quality score: 0.1500
- Publicable a Gold: no

## Fuentes
- LinkedIn: alta, restricted_manual_api_fallback, enabled=True
- Computrabajo: alta, scraping_controlado, enabled=True
- Elempleo: alta, api_first_or_scraping_controlado, enabled=True
- Ticjob: alta, scraping_controlado, enabled=True
- Hireline: media-alta, scraping_controlado, enabled=True
- Servicio Publico de Empleo: alta, fuente_oficial, enabled=True
- Agencia Publica de Empleo SENA: alta, fuente_oficial, enabled=True
- Mi Futuro Empleo: media, scraping_controlado, enabled=True
- FindJobIT: media, scraping_controlado, enabled=True

## Skills Mas Frecuentes
- Sin corrida de red o sin empleos aceptados.

## Errores Por Fuente
- LinkedIn: restricted_manual - Puede requerir autenticacion y aplica restricciones anti-scraping.
- Servicio Publico de Empleo: SSLError - HTTPSConnectionPool(host='www.serviciodeempleo.gov.co', port=443): Max retries exceeded with url: / (Caused by SSLError(SSLCertVerificationError(1, '[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1032)')))
- Servicio Publico de Empleo: SSLError - HTTPSConnectionPool(host='www.serviciodeempleo.gov.co', port=443): Max retries exceeded with url: / (Caused by SSLError(SSLCertVerificationError(1, '[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1032)')))
