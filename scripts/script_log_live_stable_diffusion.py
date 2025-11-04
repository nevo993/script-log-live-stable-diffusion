import gradio as gr
import sys
import threading
import time
import io

# Bufor logów
_log_buffer = io.StringIO()
_log_lock = threading.Lock()
MAX_LOG_SIZE = 150000

# --- Interceptor dla stdout/stderr ---
class LogInterceptor:
    def __init__(self, stream):
        self.stream = stream

    def write(self, data):
        try:
            self.stream.write(data)
            self.stream.flush()
        except Exception:
            pass

        with _log_lock:
            _log_buffer.write(data)
            value = _log_buffer.getvalue()
            if len(value) > MAX_LOG_SIZE:
                _log_buffer.seek(0)
                _log_buffer.truncate(0)
                _log_buffer.write(value[-MAX_LOG_SIZE:])

    def flush(self):
        try:
            self.stream.flush()
        except Exception:
            pass

    def isatty(self):
        # Umożliwia Uvicornowi i loggerom działać normalnie
        return hasattr(self.stream, "isatty") and self.stream.isatty()

# Zamiana stdout/stderr tylko raz
if not isinstance(sys.stdout, LogInterceptor):
    sys.stdout = LogInterceptor(sys.stdout)
if not isinstance(sys.stderr, LogInterceptor):
    sys.stderr = LogInterceptor(sys.stderr)

def read_live_log():
    with _log_lock:
        content = _log_buffer.getvalue()
    return content or "(brak logów — uruchom generowanie lub działanie w konsoli)"

def on_ui_tabs():
    """Tworzy zakładkę Live Logs"""
    with gr.Blocks(analytics_enabled=False) as log_tab:
        gr.Markdown("### 🧠 Live Logs — console WebUI")
        log_box = gr.Textbox(
            value=read_live_log(),
            label="Log output",
            lines=25,
            interactive=False
        )
        refresh_btn = gr.Button("⟳ Refresh log")

        def manual_refresh():
            return read_live_log()

        refresh_btn.click(fn=manual_refresh, outputs=log_box)

        # Auto-refresh co sekundę (kompatybilny z gradio 3.41)
        def refresh_loop():
            while True:
                time.sleep(1)
                try:
                    log_box.update(value=read_live_log())
                except Exception:
                    break

        threading.Thread(target=refresh_loop, daemon=True).start()

    return [(log_tab, "Live Logs", "live_logs_tab")]

try:
    import modules.script_callbacks as script_callbacks
    script_callbacks.on_ui_tabs(on_ui_tabs)
    print("[Live Logs] Extension aktywny — logi widoczne w zakładce Live Logs.")
except Exception as e:
    print("[Live Logs] Błąd inicjalizacji:", e)
