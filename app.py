
import streamlit as st
import pandas as pd

import matplotlib
matplotlib.use('Agg')   # Usa il backend Agg per Streamlit su server
import matplotlib.pyplot as plt

# Titolo dell'app
st.title("Relazione Tecnica Batterie")

# ===========================
# Sidebar per input utente
# ===========================
st.sidebar.header("Parametri Cliente e Batteria")
cliente = st.sidebar.text_input("Nome Cliente", "")
targa_batteria = st.sidebar.number_input("Ah nominali batteria", min_value=1, value=500, step=1)
carrello_id = st.sidebar.text_input("Tipo/Matricola Carrello", "")

st.sidebar.markdown("---")
st.sidebar.header("Caricamento Dati")
uploaded_file = st.sidebar.file_uploader(
    "Carica file Excel cicli batteria", 
    type=["xlsx", "xls"]
)

# ===========================
# Funzione di elaborazione
# ===========================
def processa_file(df, C_nom):
    # Rinomina colonne
    df = df.rename(columns={
        "Ah Discharged": "Ah_Disb",
        "Ah Charged In Charge Phase": "Ah_Chg",
        "Max. Temperature At Cycle (℃)": "Tmax_C",
        "Min. Temperature At Cycle (℃)": "Tmin_C",
        "Full Charge In Cycle [True/False]": "FullCharge_Flag"
    })
    # Converti in numerico
    df["Ah_Disb"] = pd.to_numeric(df["Ah_Disb"], errors="coerce")
    df["Ah_Chg"] = pd.to_numeric(df["Ah_Chg"], errors="coerce")
    df["Tmax_C"] = pd.to_numeric(df["Tmax_C"], errors="coerce")

    n_cicli = df.shape[0]
    soglia_scarica_prof = 0.8 * C_nom

    # Scariche profonde
    mask_scarica_prof = df["Ah_Disb"] >= soglia_scarica_prof
    n_scariche_prof = mask_scarica_prof.sum()
    perc_scariche_prof = n_scariche_prof / n_cicli * 100

    # Cariche complete/parziali
    df["FullCharge"] = df["FullCharge_Flag"].map({"T": True, "F": False})
    n_cariche_comp = int(df["FullCharge"].sum())
    perc_cariche_comp = n_cariche_comp / n_cicli * 100
    n_cariche_parz = n_cicli - n_cariche_comp
    perc_cariche_parz = 100 - perc_cariche_comp

    # Ah medi scaricati e DoD medio
    ah_medi_scaricati = df["Ah_Disb"].mean()
    df["DoD_pct"] = df["Ah_Disb"] / C_nom * 100
    dod_medio = df["DoD_pct"].mean()

    # Efficienza Ah media
    df["Eff_Ah"] = df["Ah_Disb"] / df["Ah_Chg"]
    eff_ah_media = df["Eff_Ah"].mean()

    # Cicli con Tmax > 45 °C e Tmax medio
    mask_Tmax_45 = df["Tmax_C"] > 45
    n_Tmax_gt45 = mask_Tmax_45.sum()
    tmax_medio = df["Tmax_C"].mean()

    # Output testuale
    report = {
        "Capacità nominale (Ah)": C_nom,
        "Cicli totali": n_cicli,
        "Scariche profonde (≥80%)": f"{n_scariche_prof} ({perc_scariche_prof:.1f} %)",
        "Cariche complete": f"{n_cariche_comp} ({perc_cariche_comp:.1f} %)",
        "Cariche parziali": f"{n_cariche_parz} ({perc_cariche_parz:.1f} %)",
        "Ah medi scaricati": f"{ah_medi_scaricati:.1f} Ah",
        "DoD medio": f"{dod_medio:.1f} %",
        "Efficienza Ah media": f"{eff_ah_media:.2f}",
        "Cicli con Tmax > 45 °C": n_Tmax_gt45,
        "Tmax medio": f"{tmax_medio:.1f} °C"
    }

    return df, report

# ===========================
# Main: se è stato caricato un file, processa i dati
# ===========================
if uploaded_file is not None:
    # Provo a leggere con header multilivello
    try:
        df_multi = pd.read_excel(uploaded_file, header=[0, 1])
        # Appiattisco le colonne al secondo livello
        df_multi.columns = [col[1] for col in df_multi.columns]
        df = df_multi.copy()
    except Exception as e:
        st.error(f"Errore nella lettura del file: {e}")
    else:
        # Elaborazione
        df_elab, report = processa_file(df, targa_batteria)

        # Mostro le informazioni di intestazione
        st.subheader("Dati Cliente e Carrello")
        st.write(f"**Cliente:** {cliente}")
        st.write(f"**Tipo/Matricola Carrello:** {carrello_id}")
        st.write(f"**Ah nominali batteria:** {targa_batteria} Ah")
        st.markdown("---")

        # Report testuale
        st.subheader("1. Indici Chiave")
        for key, val in report.items():
            st.write(f"- **{key}:** {val}")
        st.markdown("---")

        # Consigli operativi
        st.subheader("2. Consigli Operativi")
        st.write("• Verificare le cariche incomplete per ridurre la solfatazione.")
        st.write("• Monitorare attentamente i cicli in cui la temperatura si avvicina a 45 °C.")
        st.markdown("---")

        # Grafico 1: Ah caricati vs Ah scaricati
        st.subheader("Grafico Ah caricati vs Ah scaricati per ciclo")
        fig1, ax1 = plt.subplots(figsize=(10, 5))
        ax1.plot(
            df_elab.index + 1,
            df_elab["Ah_Chg"],
            label="Ah caricati",
            color="gold",
            marker="o",
            linestyle="-",
            markersize=5
        )
        ax1.plot(
            df_elab.index + 1,
            df_elab["Ah_Disb"],
            label="Ah scaricati",
            color="orange",
            marker="s",
            linestyle="--",
            markersize=5
        )
        ax1.set_xlabel("Numero Ciclo")
        ax1.set_ylabel("Ah")
        ax1.grid(True, linestyle="--", linewidth=0.5, alpha=0.7)
        ax1.legend(loc="upper right")
        st.pyplot(fig1)

        # Grafico 2: Temperatura massima per ciclo
        st.subheader("Grafico Temperatura massima per ciclo")
        fig2, ax2 = plt.subplots(figsize=(10, 5))
        ax2.plot(
            df_elab.index + 1,
            df_elab["Tmax_C"],
            label="Tmax (°C)",
            color="orange",
            marker="^",
            linestyle="-",
            markersize=5
        )
        ax2.axhline(
            45,
            color="red",
            linestyle="--",
            linewidth=1.2,
            label="Soglia 45 °C"
        )
        ax2.set_xlabel("Numero Ciclo")
        ax2.set_ylabel("Temperatura (°C)")
        ax2.grid(True, linestyle="--", linewidth=0.5, alpha=0.7)
        ax2.legend(loc="upper right")
        st.pyplot(fig2)
else:
    st.info("Carica un file Excel per avviare l'elaborazione.")
