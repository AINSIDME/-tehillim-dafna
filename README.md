# תהילים יומי — לעילוי נשמת דפנה בת רבקה ע״ה

Generador de videos diarios con lectura de Tehilim y explicación en hebreo, dedicado a la memoria de Dafna.

**Estado:** código inicial instalado. La publicación NO está activada hasta que se configure OAuth de YouTube y se revise un video de prueba. Los videos son **privados** por defecto.

## Configuración de YouTube
1. En https://console.cloud.google.com/ crea proyecto y habilita **YouTube Data API v3**.
2. Configura **Google Auth Platform / OAuth consent screen**. Crea un cliente OAuth tipo **Desktop** y descarga su JSON.
3. En tu PC instala Python 3.11+ y dependencias con `pip install -r requirements.txt`. Guarda el JSON como `client_secret.json` y ejecuta `python authorize_youtube.py`.
4. El script crea `youtube_token.json`. **No subas el archivo, ni compartas su contenido aquí.**
5. En GitHub, en este repositorio: **Settings → Secrets and variables → Actions → New repository secret**. Crea `YOUTUBE_TOKEN_JSON` con el contenido completo del token.
6. Desde **Actions → Tehillim diario → Run workflow** inicia una prueba privada. Revisa audio, escritura hebrea, capítulo y explicación.
7. Tras verificar el resultado, en **Settings → Secrets and variables → Actions → Variables** puedes configurar `YOUTUBE_PRIVACY=public`.

La ejecución se programa hacia las 10:15, hora de Israel. Los horarios de GitHub Actions no están garantizados al minuto, y se deben revisar posibles restricciones de publicación de YouTube para nuevos proyectos API.

## Contenido
- Los capítulos se descargan de Sefaria. **Verifica los términos de reutilización de la edición antes de la publicación pública.**
- Voz sintética masculina hebrea; la pronunciación de los nombres sagrados necesita revisión antes de publicar.
- Los capítulos con explicaciones disponibles se definen en `explanations.json`. El sistema detiene la publicación si un capítulo no tiene explicación, para evitar generar contenido atribuido falsamente a comentaristas.
- Los textos explicativos son resúmenes originales, no citas directas de comentaristas.
- Los primeros 10 capítulos están preparados. Agrega explicaciones revisadas para capítulos 11–150 antes de llegar a ellos.
- 1 video por día; progreso en `state.json`.

## Probar localmente
```bash
pip install -r requirements.txt
python agent.py --chapter 1
```
Requiere ffmpeg y una fuente compatible con hebreo (DejaVu Sans). El vídeo aparecerá en `output/`.

No subas contraseñas, credenciales, OAuth tokens ni llaves a GitHub.
