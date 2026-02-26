import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from playwright.sync_api import sync_playwright


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = PROJECT_ROOT / "Frontend" / "app"
BACKEND_DIR = PROJECT_ROOT
REPORT_PATH = PROJECT_ROOT / "tmp" / "ui_audit_report.json"
TEST_PDF = PROJECT_ROOT / "Backend" / "tests" / "test_assets" / "scanned.pdf"

BASE_URL = "http://127.0.0.1:5173"
API_URL = "http://127.0.0.1:8000"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "adminpassword"


results = []
console_errors = []
page_errors = []
network_errors = []
background_logs = []
spawned = []


def record(name: str, ok: bool, details: str = ""):
    results.append({"name": name, "ok": ok, "details": details})


def wait_http(url: str, timeout_sec: int = 120) -> bool:
    start = time.time()
    while time.time() - start < timeout_sec:
        try:
            with urlopen(url, timeout=5) as resp:
                status = getattr(resp, "status", 200)
                if status < 500:
                    return True
        except URLError:
            pass
        except Exception:
            pass
        time.sleep(1)
    return False


def server_up(url: str) -> bool:
    try:
        with urlopen(url, timeout=5) as resp:
            status = getattr(resp, "status", 200)
            return status < 500
    except Exception:
        return False


def spawn_logged(command: str, cwd: Path, label: str, env_extra=None):
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    proc = subprocess.Popen(
        command,
        cwd=str(cwd),
        env=env,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    spawned.append((proc, label))
    return proc


def collect_process_output(proc: subprocess.Popen, label: str, max_lines: int = 120):
    try:
        if proc.stdout:
            lines = proc.stdout.read().splitlines()[-max_lines:]
            for line in lines:
                background_logs.append(f"[{label}:stdout] {line}")
        if proc.stderr:
            lines = proc.stderr.read().splitlines()[-max_lines:]
            for line in lines:
                background_logs.append(f"[{label}:stderr] {line}")
    except Exception as exc:
        background_logs.append(f"[{label}] falha ao coletar output: {exc}")


def ensure_servers():
    backend_ready = server_up(f"{API_URL}/api/v1/auth/social/config")
    if not backend_ready:
        spawn_logged(
            "..\\.venv\\Scripts\\python run_backend.py --reload false --host 127.0.0.1 --port 8000",
            BACKEND_DIR,
            "backend",
            {"BACKEND_RELOAD": "False"},
        )

    frontend_ready = server_up(f"{BASE_URL}/login")
    if not frontend_ready:
        spawn_logged(
            "npm run dev -- --host 127.0.0.1 --port 5173",
            FRONTEND_DIR,
            "frontend",
        )

    backend_up = wait_http(f"{API_URL}/api/v1/auth/social/config", 120)
    frontend_up = wait_http(f"{BASE_URL}/login", 120)
    record("Backend online", backend_up, "API respondeu" if backend_up else "Timeout aguardando API")
    record(
        "Frontend online",
        frontend_up,
        "Vite respondeu" if frontend_up else "Timeout aguardando frontend",
    )
    if not backend_up or not frontend_up:
        raise RuntimeError("Servidores não iniciaram a tempo.")


def safe_step(name, fn):
    try:
        fn()
        record(name, True, "OK")
    except Exception as exc:
        record(name, False, str(exc))


def close_modals_if_any(page):
    selectors = [
        'button[aria-label="Fechar"]',
        ".modal-close-button",
        ".modal-close",
    ]
    for sel in selectors:
        loc = page.locator(sel)
        if loc.count() > 0:
            try:
                if loc.first.is_visible():
                    loc.first.click()
                    time.sleep(0.2)
            except Exception:
                pass
    close_btn = page.get_by_role("button", name=re.compile(r"^fechar$", re.I))
    if close_btn.count() > 0:
        try:
            close_btn.first.click()
        except Exception:
            pass


def run_ui_audit():
    ensure_servers()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1600, "height": 900})
        page = context.new_page()
        page.set_default_timeout(15000)

        page.on(
            "console",
            lambda msg: console_errors.append(msg.text) if msg.type == "error" else None,
        )
        page.on("pageerror", lambda err: page_errors.append(str(err)))

        def on_response(response):
            req = response.request
            if req.resource_type in ("xhr", "fetch") and response.status >= 400:
                network_errors.append(
                    {
                        "url": response.url,
                        "status": response.status,
                        "method": req.method,
                    }
                )

        page.on("response", on_response)

        safe_step(
            "Login com admin",
            lambda: (
                page.goto(f"{BASE_URL}/login", wait_until="domcontentloaded"),
                page.locator("#email").fill(ADMIN_EMAIL),
                page.locator("#password").fill(ADMIN_PASSWORD),
                page.get_by_role("button", name=re.compile(r"^entrar$", re.I)).click(),
                page.wait_for_url(re.compile(r"/dashboard"), timeout=20000),
            ),
        )

        safe_step(
            "Dashboard carregou",
            lambda: page.get_by_role("heading", name=re.compile(r"dashboard", re.I))
            .first.wait_for(state="visible"),
        )

        def step_theme_toggle():
            body = page.locator("body")
            before_dark = body.evaluate("el => el.classList.contains('dark')")
            page.get_by_role("button", name=re.compile(r"alternar tema", re.I)).click()
            time.sleep(0.3)
            after_dark = body.evaluate("el => el.classList.contains('dark')")
            if before_dark == after_dark:
                raise RuntimeError("Tema não alternou no primeiro clique")
            page.get_by_role("button", name=re.compile(r"alternar tema", re.I)).click()
            time.sleep(0.3)
            final_dark = body.evaluate("el => el.classList.contains('dark')")
            if final_dark != before_dark:
                raise RuntimeError("Tema não voltou ao estado original")

        safe_step("Theme toggle alterna claro/escuro", step_theme_toggle)

        def step_user_menu_config():
            page.locator(".user-avatar").click()
            page.get_by_role("button", name=re.compile(r"configura", re.I)).click()
            page.wait_for_url(re.compile(r"/configuracoes"), timeout=15000)

        safe_step("Abrir menu usuário e ir para Configurações", step_user_menu_config)

        safe_step(
            "Salvar perfil em Configurações",
            lambda: (
                page.get_by_role("button", name=re.compile(r"salvar alterações do perfil", re.I)).click(),
                time.sleep(1.5),
            ),
        )

        def step_change_password_modal():
            page.get_by_role("button", name=re.compile(r"alterar senha", re.I)).click()
            time.sleep(0.5)
            close_modals_if_any(page)

        safe_step("Abrir modal alterar senha e fechar", step_change_password_modal)

        nav_targets = [
            ("Dashboard", re.compile(r"/dashboard")),
            ("Produtos", re.compile(r"/produtos")),
            ("Fornecedores", re.compile(r"/fornecedores")),
            ("Tipos de Produto", re.compile(r"/tipos-de-produto")),
            ("Enriquecimento", re.compile(r"/enriquecimento")),
            ("Histórico", re.compile(r"/historico")),
            ("Meu Plano", re.compile(r"/plano")),
            ("Configurações", re.compile(r"/configuracoes")),
        ]

        for name, url_pattern in nav_targets:
            def make_step(target_name=name, pattern=url_pattern):
                def _inner():
                    page.locator("aside").get_by_role(
                        "link", name=re.compile(target_name, re.I)
                    ).click()
                    page.wait_for_url(pattern, timeout=15000)

                return _inner

            safe_step(f"Navegação sidebar: {name}", make_step())

        safe_step(
            "Produtos: atualizar lista",
            lambda: (
                page.goto(f"{BASE_URL}/produtos", wait_until="domcontentloaded"),
                page.get_by_role("button", name=re.compile(r"atualizar lista", re.I)).click(),
                time.sleep(1),
            ),
        )

        def step_new_product_modal():
            page.get_by_role("button", name=re.compile(r"\+ novo produto", re.I)).click()
            time.sleep(0.5)
            close_modals_if_any(page)

        safe_step("Produtos: abrir novo produto e fechar", step_new_product_modal)

        def step_edit_product_modal():
            edit_btn = page.locator('button[title="Editar produto"]').first
            edit_btn.wait_for(state="visible")
            edit_btn.click()
            time.sleep(0.6)
            close_modals_if_any(page)

        safe_step("Produtos: abrir edição do primeiro item e fechar", step_edit_product_modal)

        def step_products_enrich_batch():
            first_checkbox = page.locator("table tbody tr input[type='checkbox']").first
            first_checkbox.wait_for(state="visible")
            first_checkbox.click()
            page.get_by_role("button", name=re.compile(r"enriquecer web", re.I)).first.click()
            time.sleep(2)

        safe_step("Produtos: iniciar enriquecimento em lote (1 item)", step_products_enrich_batch)

        def step_enriquecimento_page():
            page.goto(f"{BASE_URL}/enriquecimento", wait_until="domcontentloaded")
            first_checkbox = page.locator("table tbody tr input[type='checkbox']").first
            first_checkbox.wait_for(state="visible")
            first_checkbox.click()
            page.get_by_role("button", name=re.compile(r"enriquecer web", re.I)).first.click()
            time.sleep(2)

        safe_step("Enriquecimento: selecionar e iniciar enriquecimento", step_enriquecimento_page)

        def step_open_fornecedor_modal():
            page.goto(f"{BASE_URL}/fornecedores", wait_until="domcontentloaded")
            first_row = page.locator("#forn-table tbody tr").first
            first_row.wait_for(state="visible")
            first_row.click()
            page.get_by_role("heading", name=re.compile(r"editar fornecedor", re.I)).wait_for(
                state="visible"
            )

        safe_step("Fornecedores: abrir modal edição primeira linha", step_open_fornecedor_modal)

        safe_step(
            "Fornecedor info: salvar alterações",
            lambda: (
                page.get_by_role("button", name=re.compile(r"salvar alterações", re.I)).click(),
                time.sleep(1.5),
            ),
        )

        def step_open_import_wizard():
            page.get_by_role("button", name=re.compile(r"importar cat", re.I)).first.click()
            page.get_by_role("button", name=re.compile(r"^importar catálogo$", re.I)).first.click()
            page.get_by_role("heading", name=re.compile(r"passo 1", re.I)).wait_for(state="visible")

        safe_step("Fornecedor importação: abrir wizard", step_open_import_wizard)

        def step_wizard_preview():
            page.locator("#wizard-file-input").set_input_files(str(TEST_PDF))
            page.get_by_role("button", name=re.compile(r"gerar preview", re.I)).click()
            page.get_by_role("heading", name=re.compile(r"passo 2", re.I)).wait_for(
                state="visible", timeout=60000
            )

        safe_step("Wizard passo 1->2: upload + gerar preview", step_wizard_preview)

        def step_wizard_mapping():
            page.get_by_role("button", name=re.compile(r"definir mapeamento", re.I)).click()
            page.get_by_role("heading", name=re.compile(r"mapear colunas", re.I)).wait_for(
                state="visible"
            )

            product_type_select = page.locator("#column-mapping-product-type-select")
            if product_type_select.count() > 0 and product_type_select.first.is_visible():
                values = product_type_select.first.locator("option").all_inner_texts()
                if len(values) > 1:
                    product_type_select.first.select_option(index=1)

            mapping_selects = page.locator(".mapping-table tbody tr td select")
            count = mapping_selects.count()
            if count > 0:
                try:
                    mapping_selects.nth(0).select_option("auto:sku_nome")
                except Exception:
                    mapping_selects.nth(0).select_option("nome_base")
            if count > 1:
                try:
                    mapping_selects.nth(1).select_option("descricao_original")
                except Exception:
                    pass

            page.get_by_role("button", name=re.compile(r"confirmar mapeamento", re.I)).click()
            time.sleep(0.5)

        safe_step("Wizard passo 2: mapear e confirmar", step_wizard_mapping)

        def step_wizard_start_processing():
            type_select = page.locator("#wizard-product-type")
            if type_select.count() > 0 and type_select.first.is_visible():
                options = type_select.first.locator("option").all_inner_texts()
                if len(options) > 1:
                    type_select.first.select_option(index=1)
            page.get_by_role("button", name=re.compile(r"iniciar processamento", re.I)).click()
            page.get_by_role("heading", name=re.compile(r"passo 3", re.I)).wait_for(
                state="visible", timeout=30000
            )

        safe_step("Wizard passo 2->3: iniciar processamento", step_wizard_start_processing)

        def step_wizard_wait_terminal():
            header = page.locator(".wizard-processing-header")
            header.wait_for(state="visible", timeout=10000)
            start = time.time()
            terminal = False
            while time.time() - start < 90:
                text = header.inner_text().upper()
                if any(x in text for x in ["IMPORTED", "FAILED", "PARTIAL", "DONE"]):
                    terminal = True
                    break
                time.sleep(2)
            if not terminal:
                raise RuntimeError("Status terminal não alcançado em 90s")

        safe_step("Wizard processamento: aguardar status terminal", step_wizard_wait_terminal)

        def step_close_wizard_modal():
            close_btns = page.get_by_role("button", name=re.compile(r"^fechar$", re.I))
            if close_btns.count() > 0:
                try:
                    close_btns.first.click()
                    time.sleep(0.5)
                except Exception:
                    pass
            close_modals_if_any(page)

        safe_step("Fechar wizard e modal de fornecedor", step_close_wizard_modal)

        def step_tipos_new_modal():
            page.goto(f"{BASE_URL}/tipos-de-produto", wait_until="domcontentloaded")
            page.get_by_role("button", name=re.compile(r"\+ novo tipo de produto", re.I)).click()
            time.sleep(0.5)
            close_modals_if_any(page)

        safe_step("Tipos de Produto: abrir novo tipo e fechar", step_tipos_new_modal)

        def step_tipos_attr_modal():
            first_type = page.locator(".type-list-panel ul li").first
            first_type.wait_for(state="visible")
            first_type.click()
            page.get_by_role("button", name=re.compile(r"\+ novo atributo", re.I)).click()
            time.sleep(0.5)
            close_modals_if_any(page)

        safe_step("Tipos de Produto: abrir modal novo atributo", step_tipos_attr_modal)

        safe_step(
            "Meu Plano: clicar ações de assinatura",
            lambda: (
                page.goto(f"{BASE_URL}/plano", wait_until="domcontentloaded"),
                page.get_by_role("button", name=re.compile(r"upgrade de plano", re.I)).click(),
                time.sleep(0.3),
                page.get_by_role("button", name=re.compile(r"cancelar assinatura", re.I)).click(),
                time.sleep(0.3),
            ),
        )

        safe_step(
            "Logout pelo botão Sair",
            lambda: (
                page.get_by_role("button", name=re.compile(r"sair", re.I)).first.click(),
                page.wait_for_url(re.compile(r"/login"), timeout=15000),
            ),
        )

        browser.close()


def cleanup():
    for proc, label in reversed(spawned):
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
        collect_process_output(proc, label)
        background_logs.append(f"[{label}] finalizado")



class FullUiAuditWorkflow:
    def run_ui_audit(self):
        run_ui_audit()

    def cleanup(self):
        cleanup()


full_ui_audit_workflow = FullUiAuditWorkflow()


def main():
    try:
        full_ui_audit_workflow.run_ui_audit()
    except Exception as exc:
        record("Execucao geral do auditor", False, str(exc))
    finally:
        full_ui_audit_workflow.cleanup()


    passed = len([r for r in results if r["ok"]])
    failed = len([r for r in results if not r["ok"]])
    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "totals": {"passed": passed, "failed": failed, "steps": len(results)},
        "steps": results,
        "console_errors": console_errors,
        "page_errors": page_errors,
        "network_errors": network_errors,
        "background_logs_tail": background_logs[-200:],
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"REPORT_PATH={REPORT_PATH}")
    print(f"PASSED={passed}")
    print(f"FAILED={failed}")


if __name__ == "__main__":
    main()
