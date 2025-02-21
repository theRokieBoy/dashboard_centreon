import re
import base64
import io
import seaborn as sns
import matplotlib.pyplot as plt
import json
import pandas as pd
from flask import Flask
from utils import extraer_data
import matplotlib
from apscheduler.schedulers.background import BackgroundScheduler

matplotlib.use('Agg')  # Usa un backend no interactivo

app = Flask(__name__)

pattern_disco = r"Storage '([A-Z]:\\) .*? Usage Total: ([\d\.]+ \w+) Used: ([\d\.]+ \w+) \(([\d\.]+)%\) Free: ([\d\.]+ \w+) \(([\d\.]+)%\)"
pattern_filesystem = r"Storage '(.*?)' Usage Total: ([\d.]+ \w+) Used: ([\d.]+ \w+) \(([\d.]+)%\) Free: ([\d.]+ \w+) \(([\d.]+)%\)"


def mi_funcion():
    print("Ejecutando tarea cada 5 minutos...")
    extraer_data()


# # Configurar el scheduler
# scheduler = BackgroundScheduler()
# scheduler.add_job(mi_funcion, 'interval', minutes=5)
# scheduler.start()


def extract_percentage(output, label):
    """Extrae el porcentaje de uso de CPU o RAM desde diferentes formatos de output."""
    match = re.search(r'(\d+\.\d+)\s*%', output)
    if match:
        return float(match.group(1))
    return None

# Función para formatear el eje Y con porcentajes y centrar el texto en la barra


def format_yticks(ax, y_labels, percentages):
    ax.set_yticklabels([f"{perc:.2f}%" for perc,
                       label in zip(percentages, y_labels)], fontsize=11, color="#FAFAFA")


def add_labels(ax, y_labels, percentages, ip_address):
    for i, (label, perc, ip_address) in enumerate(zip(y_labels, percentages, ip_address)):
        ax.text(2, i, label+" ["+ip_address+"]", ha="left", va="center",
                color="#FAFAFA", fontsize=10, fontweight="normal")


def add_labels_disco(ax, y_labels, percentages, ip_address, disco, free):
    for i, (label, perc, ip_address, disco, free) in enumerate(zip(y_labels, percentages, ip_address, disco, free)):
        ax.text(2, i, label+" ["+ip_address+"]  " + disco + " que tiene "+free + " libres", ha="left", va="center",
                color="#FAFAFA", fontsize=10, fontweight="normal")


def generate_chart():

    # Cargar datos desde el archivo JSON
    with open("resultados.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    # Extraer datos de RAM y CPU
    ram_data = data.get("RAM", [])
    cpu_data = data.get("CPU", [])
    disco_data = []
    for host in data.get("Disco", []):
        host_name = host["host_name"]
        host_address = host["host_address"]
        matches = re.findall(pattern_disco, host["output"])
        for match in matches:
            disco_data.append([host_name, host_address, *match])

    filesystem_data = []
    for host in data.get("Filesystem", []):
        host_name = host["host_name"]
        host_address = host["host_address"]
        matches = re.findall(pattern_filesystem, host["output"])
        for match in matches:
            filesystem_data.append([host_name, host_address, *match])

    if ram_data and cpu_data and disco_data and filesystem_data:
        df_ram = pd.DataFrame(ram_data)[
            ["host_name", "output", "host_address"]]
        df_cpu = pd.DataFrame(cpu_data)[["host_name", "output"]]
        df_disco = pd.DataFrame(disco_data, columns=[
                                "Host", "host_address", "Disk", "Total", "Used", "Used %", "Free", "Free %"])
        # Convertir columnas numéricas a tipo float
        df_disco["Used %"] = df_disco["Used %"].astype(float)
        df_disco["Free %"] = df_disco["Free %"].astype(float)

        df_filesystem = pd.DataFrame(filesystem_data, columns=[
            "Host", "host_address", "Disk", "Total", "Used", "Used %", "Free", "Free %"])
        # Convertir columnas numéricas a tipo float
        df_filesystem["Used %"] = df_filesystem["Used %"].astype(float)
        df_filesystem["Free %"] = df_filesystem["Free %"].astype(float)
        # Extraer porcentajes
        df_ram["Memory Usage %"] = df_ram["output"].apply(
            lambda x: extract_percentage(x, "RAM"))

        df_cpu["CPU Usage %"] = df_cpu["CPU Usage %"] = df_cpu["output"].apply(
            lambda x: extract_percentage(x, "CPU"))

        # Combinar datos por host
        df = pd.merge(df_ram, df_cpu, on="host_name", how="outer")

        # ordenar y fltrar
        df_ram = df.sort_values(by="Memory Usage %", ascending=False)
        df_ram = df_ram.drop_duplicates(
            subset=["host_name"], keep="first").head(30)
        df_cpu = df.sort_values(by="CPU Usage %", ascending=False)
        df_cpu = df_cpu.drop_duplicates(
            subset=["host_name"], keep="first").head(30)
        df_disco = df_disco.sort_values(by="Used %", ascending=False).drop_duplicates(
            subset=["Host", "Disk"], keep="first").head(30)
        df_filesystem = df_filesystem.sort_values(by="Used %", ascending=False).drop_duplicates(
            subset=["Host", "Disk"], keep="first").head(30)

        df_espacio_free = pd.concat(
            [df_disco, df_filesystem], ignore_index=True)
        print(df_espacio_free)

        # Crear el gráfico
        plt.style.use('dark_background')
        fig, axes = plt.subplots(2, 2, figsize=(15, 20))

        # Colores
        colors_ram = ["#aa202d" if x > 95 else "#bba41a" if x >
                      85 else "#679a3d" for x in df_ram["Memory Usage %"]]
        colors_cpu = ["#aa202d" if x > 90 else "#bba41a" if x >
                      65 else "#679a3d" for x in df_cpu["CPU Usage %"]]

        colors_disco = ["#aa202d" if x > 93 else "#bba41a" if x >
                        90 else "#679a3d" for x in df_disco["Used %"]]

        colors_filesystem = ["#aa202d" if x > 93 else "#bba41a" if x >
                             90 else "#679a3d" for x in df_filesystem["Used %"]]

        # Gráfico de RAM
        sns.barplot(y=df_ram["host_name"], x=df_ram["Memory Usage %"],
                    palette=colors_ram, ax=axes[0, 0])
        axes[0, 0].set_xlabel("")
        axes[0, 0].set_ylabel("")
        axes[0, 0].set_title("Memory usage %", loc="left",
                             pad=10, fontsize=12)
        axes[0, 0].set_xlim(0, 100)  # Establecer límites del eje X
        axes[0, 0].grid(axis="x", linestyle="", alpha=0.7)

        format_yticks(axes[0, 0], df_ram["host_name"],
                      df_ram["Memory Usage %"])
        add_labels(axes[0, 0], df_ram["host_name"],
                   df_ram["Memory Usage %"], df_ram["host_address"])
        axes[0, 0].tick_params(axis="y", length=0)

        # Gráfico de CPU
        sns.barplot(y=df_cpu["host_name"], x=df_cpu["CPU Usage %"],
                    palette=colors_cpu, ax=axes[0, 1])
        axes[0, 1].set_xlabel("")
        axes[0, 1].set_ylabel("")
        axes[0, 1].set_title("CPU usage %", loc="left",
                             pad=10, fontsize=12)
        axes[0, 1].set_xlim(0, 100)  # Establecer límites del eje X
        axes[0, 1].grid(axis="x", linestyle="", alpha=0.7)
        format_yticks(axes[0, 1], df_cpu["host_name"],
                      df_cpu["CPU Usage %"])
        add_labels(axes[0, 1], df_cpu["host_name"],
                   df_cpu["CPU Usage %"], df_cpu["host_address"])
        axes[0, 1].tick_params(axis="y", length=0)

        # Gráfico de disco
        sns.barplot(y=df_disco["Disk"] + " (" + df_disco["Host"] + ")", x=df_disco["Used %"],
                    palette=colors_disco, ax=axes[1, 0])
        axes[1, 0].set_xlabel("")
        axes[1, 0].set_ylabel("")
        axes[1, 0].set_title("Disco usage %", loc="left",
                             pad=10, fontsize=12)
        axes[1, 0].set_xlim(0, 100)  # Establecer límites del eje X
        axes[1, 0].grid(axis="x", linestyle="", alpha=0.7)
        format_yticks(axes[1, 0], df_disco["Host"],
                      df_disco["Used %"])
        add_labels_disco(axes[1, 0], df_disco["Host"],
                         df_disco["Used %"], df_disco["host_address"], df_disco["Disk"], df_disco["Free"])
        axes[1, 0].tick_params(axis="y", length=0)

        # Gráfico de filesystem
        sns.barplot(y=df_filesystem["Disk"] + " (" + df_filesystem["Host"] + ")", x=df_filesystem["Used %"],
                    palette=colors_filesystem, ax=axes[1, 1])
        axes[1, 1].set_xlabel("")
        axes[1, 1].set_ylabel("")
        axes[1, 1].set_title("Filesystem usage %", loc="left",
                             pad=10, fontsize=12)
        axes[1, 1].set_xlim(0, 100)  # Establecer límites del eje X
        axes[1, 1].grid(axis="x", linestyle="", alpha=0.7)
        format_yticks(axes[1, 1], df_filesystem["Host"],
                      df_filesystem["Used %"])
        add_labels_disco(axes[1, 1], df_filesystem["Host"],
                         df_filesystem["Used %"], df_filesystem["host_address"], df_filesystem["Disk"], df_filesystem["Free"])
        axes[1, 1].tick_params(axis="y", length=0)

        # Agregar bordes alrededor de cada subplot
        for ax in axes.flat:
            ax.set_facecolor('#393939')
            for spine in ax.spines.values():
                # Color del borde (puedes cambiarlo)
                spine.set_edgecolor('white')
                spine.set_linewidth(1.5)      # Grosor del borde

        plt.tight_layout()

        # Convertir gráfico a imagen en base64
        img = io.BytesIO()
        plt.savefig(img, format='png', bbox_inches='tight')
        img.seek(0)
        plot_url = base64.b64encode(img.getvalue()).decode()
        return plot_url
    return None


@app.route('/')
def home():
    plot_url = generate_chart()
    # return f'<img src="data:image/png;base64,{plot_url}" alt="Memory and CPU Usage Chart">' if plot_url else "No data available"
    return f"""
    <html>
    <head>
        <meta http-equiv="refresh" content="300"> <!-- Refresca cada 5 minutos -->
        <title>Uso de Memoria y CPU</title>
    </head>
    <body>
        <img src="data:image/png;base64,{plot_url}" alt="Memory and CPU Usage Chart">
    </body>
    </html>
    """ if plot_url else "No data available"


if __name__ == "__main__":
    # app.run(debug=True)
    app.run(port=4000, host="0.0.0.0", debug=True)
