import threading
import io
import contextlib
import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox

# Import the processing function from the existing script
try:
    from color_change2 import reestruturar_desenho_final
except Exception:
    # If import fails, we still want the GUI file to be importable for checks; show friendly error on run.
    reestruturar_desenho_final = None


class App:
    def __init__(self, root):
        self.root = root
        root.title('DXF Reestruturador - GUI')

        frm = tk.Frame(root, padx=8, pady=8)
        frm.pack(fill='both', expand=True)

        tk.Label(frm, text='Arquivo DXF entrada:').grid(row=0, column=0, sticky='w')
        self.entry_in = tk.Entry(frm, width=60)
        self.entry_in.grid(row=0, column=1, sticky='we', padx=4)
        tk.Button(frm, text='Procurar...', command=self.browse_input).grid(row=0, column=2)
        tk.Button(frm, text='Selecionar vários...', command=self.browse_input_multiple).grid(row=0, column=3, padx=(6,0))

        tk.Label(frm, text='Arquivo DXF saída:').grid(row=1, column=0, sticky='w')
        self.entry_out = tk.Entry(frm, width=60)
        self.entry_out.grid(row=1, column=1, sticky='we', padx=4)
        tk.Button(frm, text='Procurar...', command=self.browse_output).grid(row=1, column=2)

        self.run_btn = tk.Button(frm, text='Executar reestruturação', command=self.on_run)
        self.run_btn.grid(row=2, column=0, columnspan=3, pady=8)

        tk.Label(frm, text='Log:').grid(row=3, column=0, sticky='nw')
        self.text = tk.Text(frm, height=18, width=90)
        self.text.grid(row=3, column=1, columnspan=2, sticky='nsew')
        frm.rowconfigure(3, weight=1)
        frm.columnconfigure(1, weight=1)

        btn_frame = tk.Frame(frm)
        btn_frame.grid(row=4, column=0, columnspan=3, sticky='we', pady=(8,0))
        tk.Button(btn_frame, text='Abrir pasta de saída', command=self.open_output_folder).pack(side='left')
        tk.Button(btn_frame, text='Limpar log', command=lambda: self.text.delete('1.0', 'end')).pack(side='left', padx=6)
        tk.Button(btn_frame, text='Abrir relatório de handles', command=self.open_handles_report).pack(side='left', padx=6)

        # Settings area
        settings = tk.Frame(frm, pady=6)
        settings.grid(row=5, column=0, columnspan=4, sticky='we')
        self.chk_var = tk.IntVar(value=0)
        tk.Checkbutton(settings, text='Proteger setas por proximidade de cotas', variable=self.chk_var).pack(side='left')
        tk.Label(settings, text='ARROW_PROXIMITY').pack(side='left', padx=(12,0))
        self.entry_arrow_prox = tk.Entry(settings, width=6)
        self.entry_arrow_prox.insert(0, str(20.0))
        self.entry_arrow_prox.pack(side='left')
        tk.Label(settings, text='(min 0.1, max 1000)').pack(side='left', padx=(6,0))
        tk.Label(settings, text='RAIO_DE_BUSCA').pack(side='left', padx=(12,0))
        self.entry_raio = tk.Entry(settings, width=6)
        self.entry_raio.insert(0, str(800.0))
        self.entry_raio.pack(side='left')
        tk.Label(settings, text='(min 1, max 10000)').pack(side='left', padx=(6,0))

        # Keep last outputs per file
        self._last_outputs = {}

    def browse_input(self):
        path = filedialog.askopenfilename(filetypes=[('DXF files', '*.dxf'), ('All files', '*.*')])
        if path:
            self.entry_in.delete(0, 'end')
            self.entry_in.insert(0, path)

    def browse_output(self):
        path = filedialog.asksaveasfilename(defaultextension='.dxf', filetypes=[('DXF files', '*.dxf'), ('All files', '*.*')])
        if path:
            self.entry_out.delete(0, 'end')
            self.entry_out.insert(0, path)

    def browse_input_multiple(self):
        paths = filedialog.askopenfilenames(filetypes=[('DXF files', '*.dxf'), ('All files', '*.*')])
        if paths:
            # join with os.pathsep for storage but show first
            first = paths[0]
            self.entry_in.delete(0, 'end')
            self.entry_in.insert(0, first)
            self._multi_inputs = list(paths)
        else:
            self._multi_inputs = []

    def append_log(self, text):
        self.text.insert('end', text)
        self.text.see('end')

    def on_run(self):
        infile = self.entry_in.get().strip()
        outfile = self.entry_out.get().strip()
        inputs = getattr(self, '_multi_inputs', None)
        if inputs:
            input_list = inputs
        else:
            input_list = [infile]
        if not infile or not os.path.exists(infile):
            messagebox.showerror('Erro', 'Arquivo de entrada inválido ou não encontrado.')
            return
        # If no output specified, default to app folder: outputs will be auto-named per input
        if not outfile:
            app_folder = os.getcwd()
            # use a default base name if single-file
            default_base = os.path.splitext(os.path.basename(infile))[0]
            outfile = os.path.join(app_folder, f"{default_base}_pro_v3.dxf")
            # show in UI so user sees where output will go
            self.entry_out.delete(0, 'end')
            self.entry_out.insert(0, outfile)
        if reestruturar_desenho_final is None:
            messagebox.showerror('Erro', 'Não foi possível importar a função de processamento (veja consola).')
            return

        self.run_btn.config(state='disabled')
        self.append_log(f"Iniciando processamento de {len(input_list)} arquivo(s)\n")

        # gather settings
        protect = bool(self.chk_var.get())
        # validate and clamp numeric settings
        try:
            arrow_prox = float(self.entry_arrow_prox.get())
        except Exception:
            arrow_prox = 20.0
        arrow_prox = max(0.1, min(1000.0, arrow_prox))
        if float(self.entry_arrow_prox.get() or 0) != arrow_prox:
            self.append_log(f"ARROW_PROXIMITY adjusted to {arrow_prox}\n")
        try:
            raio = float(self.entry_raio.get())
        except Exception:
            raio = 800.0
        raio = max(1.0, min(10000.0, raio))
        if float(self.entry_raio.get() or 0) != raio:
            self.append_log(f"RAIO_DE_BUSCA adjusted to {raio}\n")

        thread = threading.Thread(target=self._run_multiple_files_thread, args=(input_list, outfile, protect, arrow_prox, raio), daemon=True)
        thread.start()

    def _run_thread(self, infile, outfile):
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                reestruturar_desenho_final(infile, outfile)
        except Exception as e:
            buf.write(f"Erro ao executar: {e}\n")
        output = buf.getvalue()
        # Append to text widget in main thread
        self.root.after(0, lambda: self._on_done(output, outfile))

    def _run_multiple_files_thread(self, input_list, base_outfile, protect, arrow_prox, raio):
        buf = io.StringIO()
        results = []
        try:
            for idx, infile in enumerate(input_list):
                # choose outfile per input
                if len(input_list) == 1:
                    outfile = base_outfile
                else:
                    base, ext = os.path.splitext(base_outfile)
                    outfile = f"{base}_{idx+1}{ext}" if base_outfile else infile.replace('.dxf', f'_out_{idx+1}.dxf')
                with contextlib.redirect_stdout(buf):
                    try:
                        summary = reestruturar_desenho_final(infile, outfile, protect_by_dimension=protect, arrow_proximity=arrow_prox, raio_de_busca=raio)
                        results.append((infile, outfile, summary))
                    except Exception as e:
                        buf.write(f"Erro processando {infile}: {e}\n")
        except Exception as e:
            buf.write(f"Erro ao executar processamento: {e}\n")
        output = buf.getvalue()
        # Append results in main thread
        self.root.after(0, lambda: self._on_done_multiple(output, results))

    def _on_done_multiple(self, output, results):
        self.append_log(output)
        for infile, outfile, summary in results:
            self.append_log(f"Arquivo: {infile} -> {outfile}\n")
            if summary and isinstance(summary, dict):
                self.append_log(f"Handles report: {summary.get('handles_report_path')}\n")
                # store last handles path
                self._last_outputs[infile] = summary.get('handles_report_path')
        self.append_log('\nProcessamento finalizado.\n')
        self.run_btn.config(state='normal')

    def _on_done(self, output, outfile):
        self.append_log(output)
        self.append_log('\nProcessamento finalizado.\n')
        self.run_btn.config(state='normal')
        self._last_output = outfile
        # single-run summary may have written handles report next to outfile
        # attempt to set the last handles path
        handles_csv = os.path.splitext(outfile)[0] + '_handles_report.csv'
        if os.path.exists(handles_csv):
            self._last_outputs[outfile] = handles_csv

    def open_output_folder(self):
        try:
            out = getattr(self, '_last_output', None)
            if out and os.path.exists(out):
                folder = os.path.dirname(os.path.abspath(out))
                if sys.platform == 'win32':
                    os.startfile(folder)
                else:
                    # cross-platform fallback
                    import subprocess
                    subprocess.run(['xdg-open', folder])
            else:
                messagebox.showinfo('Info', 'Nenhum arquivo de saída disponível ainda.')
        except Exception as e:
            messagebox.showerror('Erro', f'Não foi possível abrir a pasta: {e}')

    def open_handles_report(self):
        try:
            # prefer most recent: if multiple, pick any
            if not self._last_outputs:
                messagebox.showinfo('Info', 'Nenhum relatório de handles disponível ainda.')
                return
            # pick last value
            last = list(self._last_outputs.values())[-1]
            if last and os.path.exists(last):
                if sys.platform == 'win32':
                    os.startfile(last)
                else:
                    import subprocess
                    subprocess.run(['xdg-open', last])
            else:
                messagebox.showinfo('Info', 'Relatório de handles não encontrado.')
        except Exception as e:
            messagebox.showerror('Erro', f'Não foi possível abrir o relatório: {e}')


def main():
    root = tk.Tk()
    app = App(root)
    root.mainloop()


if __name__ == '__main__':
    main()
