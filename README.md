# CloudSense

Monitor de infraestructura AWS con analisis narrativo generado por IA. Recolecta metricas de CPU, RAM y red cada minuto, las almacena en SQLite y produce diagnosticos en lenguaje natural usando un LLM local (Ollama) o cualquier proveedor compatible con la API de OpenAI.

## Funcionalidades principales

- **Dashboard en tiempo real** - graficas de CPU/RAM y trafico de red con umbrales configurables, actualizado cada 30 segundos.
- **Narrativas automaticas** - el LLM analiza el periodo seleccionado (1h, 3h o 24h) y genera un diagnostico en espanol con contexto de negocio, descripcion de red y recomendaciones de servicios AWS cuando los umbrales lo justifican.
- **Simulador de carga** - cuatro modos (Normal, Alta carga, Critico, Nocturno) para demostrar el sistema sin necesidad de una instancia real.
- **Panel de configuracion** - ajuste de umbrales, ventana de analisis, descripcion de la instancia y generacion manual de narrativas.

## Arquitectura

```
compose.yml
├── backend/          FastAPI + APScheduler (Python)
│   ├── api/          Endpoints REST (metricas, narrativas, simulacion, umbrales)
│   ├── collector/    Recoleccion de metricas (Strategy: fuente sintetica o real)
│   ├── db/           Acceso a SQLite (metricas, narrativas, configuracion)
│   └── llm/          Construccion de prompt y generacion de narrativas
└── ollama/           Servidor LLM local (llama3.2 por defecto)
```

La narrativa sigue un pipeline hibrido: el LLM escribe la oracion descriptiva de CPU/RAM, Python construye deterministicamente la oracion de red y las recomendaciones de AWS.

## Requisitos

- [Podman](https://podman.io/) (o Docker) con `podman-compose` / `docker compose`
- 4 GB de RAM libres para el modelo llama3.2

## Inicio rapido

```bash
# 1. Clonar y entrar al repositorio
git clone <url-del-repo>
cd proyecto-sic-software-i

# 2. Copiar y ajustar variables de entorno
cp .env.example .env

# 3. Levantar los servicios (la primera vez descarga el modelo, tarda ~5 min)
podman compose up -d

# 4. Abrir el navegador
open http://localhost:8000
```

> La primera narrativa se genera automaticamente despues de que el scheduler completa el primer ciclo (~60 minutos). Para generarla de inmediato, usa el boton **Generar narrativa** en el panel de simulacion.

## Variables de entorno

| Variable | Defecto | Descripcion |
|---|---|---|
| `DATA_SOURCE` | `synthetic` | Fuente de metricas. `synthetic` usa el simulador; `real` lee el sistema operativo host. |
| `THRESHOLD_CPU` | `85` | Umbral de CPU (%) para alertas y recomendaciones. |
| `THRESHOLD_RAM` | `85` | Umbral de RAM (%) para alertas y recomendaciones. |
| `COLLECT_INTERVAL_MINUTES` | `1` | Frecuencia de recoleccion de metricas. |
| `NARRATIVE_INTERVAL_MINUTES` | `60` | Frecuencia de generacion automatica de narrativas. |
| `LLM_PROVIDER` | `ollama` | Proveedor LLM. Opciones: `ollama`, `openai`, `anthropic`, `openrouter`. |
| `LLM_BASE_URL` | `http://ollama:11434` | URL base del proveedor LLM. |
| `LLM_MODEL` | `llama3.2` | Modelo a usar. |
| `LLM_API_KEY` | _(vacio)_ | API key para proveedores externos. No requerida con Ollama. |
| `INSTANCE_DESCRIPTION` | _(vacio)_ | Descripcion del negocio que el LLM usa para contextualizar picos. |

## Endpoints principales

| Metodo | Ruta | Descripcion |
|---|---|---|
| `GET` | `/` | Landing page |
| `GET` | `/dashboard` | Monitor en tiempo real |
| `GET` | `/simulacion-panel` | Panel de simulacion y configuracion |
| `GET` | `/metricas/actuales` | Ultima lectura de metricas |
| `GET` | `/metricas/historial?horas=1` | Historial de metricas (1, 3 o 24 horas) |
| `GET` | `/narrativa/ultima` | Narrativa mas reciente |
| `GET` | `/narrativa/historial` | Historial de narrativas |
| `POST` | `/simulacion/modo/{mode}` | Cambiar modo del simulador |
| `POST` | `/simulacion/narrativa` | Generar narrativa manualmente |
| `POST` | `/simulacion/reset` | Limpiar datos y reiniciar escenario |
| `GET` | `/config/umbrales` | Leer umbrales actuales |
| `POST` | `/config/umbrales` | Actualizar umbrales |

## Patrones de diseno aplicados

- **Factory Method** - `collector/sources/` define una clase base `MetricSource`; la fuente concreta (sintetica o real) se instancia segun `DATA_SOURCE`.
- **Strategy** - el modo del simulador (normal, alta\_carga, critico, nocturno) encapsula rangos de metricas intercambiables en tiempo de ejecucion.
- **Singleton** - `db/database.py` expone una instancia unica de conexion a SQLite reutilizada en toda la aplicacion.

## Modos del simulador

| Modo | CPU | RAM | Caso tipico |
|---|---|---|---|
| Normal | 30-65% | 35-60% | Operacion diaria estandar |
| Alta carga | 70-88% | 65-82% | Pico de trafico o proceso batch |
| Critico | 88-99% | 82-97% | Sobrecarga o posible DDoS |
| Nocturno | 8-22% | 18-32% | Minima actividad, solo healthchecks |
