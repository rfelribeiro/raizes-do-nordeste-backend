"""Converte .docx em PDF com o LibreOffice headless, atualizando o sumário antes de exportar.

Roda no contêiner do LibreOffice (python3-uno). Uso: converter_pdf.py <entrada.docx> <saida.pdf>
"""
import os
import subprocess
import sys
import time

import uno
from com.sun.star.beans import PropertyValue


def prop(nome, valor):
    p = PropertyValue()
    p.Name, p.Value = nome, valor
    return p


def conectar():
    ctx = uno.getComponentContext()
    resolver = ctx.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", ctx)
    for _ in range(60):
        try:
            return resolver.resolve("uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext")
        except Exception:
            time.sleep(1)
    sys.exit("LibreOffice não respondeu.")


def main(entrada, saida):
    soffice = subprocess.Popen(
        ["soffice", "--headless", "--norestore", "--nologo", "-env:UserInstallation=file:///tmp/lo-perfil",
         "--accept=socket,host=localhost,port=2002;urp;"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        ctx = conectar()
        desktop = ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
        doc = desktop.loadComponentFromURL(uno.systemPathToFileUrl(os.path.abspath(entrada)), "_blank", 0, (prop("Hidden", True),))
        # duas passadas: o sumário muda a paginação, então os números só estabilizam na segunda
        for _ in range(2):
            indices = doc.getDocumentIndexes()
            for i in range(indices.getCount()):
                indices.getByIndex(i).update()
            doc.refresh()
        doc.storeToURL(uno.systemPathToFileUrl(os.path.abspath(saida)), (prop("FilterName", "writer_pdf_Export"),))
        doc.close(True)
        try:
            desktop.terminate()
        except Exception:
            pass
    finally:
        time.sleep(1)
        soffice.terminate()


if __name__ == "__main__":
    main(*sys.argv[1:3])
