
import streamlit as st
import pandas as pd

import matplotlib
matplotlib.use('Agg')
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
    df = df.rename(columns={
        "Ah Discharged": "Ah_Disb",
        "Ah Charged In Charge Phase": "Ah_Chg",
        "Max. Temperature At Cycle (℃)": "Tmax_C",
        "Min. Temperature At Cycle (℃)": "Tmin_C",
        "Full Charge In Cycle [True/False]": "FullCharge_Flag"
    })
    df["Ah_Disb"] = pd.to_numeric(df["Ah_Disb"], errors="coerce")
    df["Ah_Chg"] = pd.to_numeric(df["Ah_Chg"], errors="coerce")
    df["Tmax_C"] = pd.to_numeric(df["Tmax_C"], errors="coerce")
    df["FullCharge"] = df["FullCharge_Flag"].map({"T": True, "F": False})

    n_cicli = df.shape[0]
    soglia_scarica_prof = 0.8 * C_nom
    n_scariche_prof = (df["Ah_Disb"] >= soglia_scarica_prof).sum()
    perc_scariche_prof = n_scariche_prof / n_cicli * 100

    n_cariche_comp = df["FullCharge"].sum()
    perc_cariche_comp = n_cariche_comp / n_cicli * 100
    n_cariche_parz = n_cicli - n_cariche_comp
    perc_cariche_parz = 100 - perc_cariche_comp

    ah_medi_scaricati = df["Ah_Disb"].mean()
    df["DoD_pct"] = df["Ah_Disb"] / C_nom * 100
    dod_medio = df["DoD_pct"].mean()

    tot_ah_disch = df["Ah_Disb"].sum()
    tot_ah_chg = df["Ah_Chg"].sum()
    tot_ah_chg_adj = tot_ah_chg + C_nom
    eff_ah_media = tot_ah_disch / tot_ah_chg_adj if tot_ah_chg_adj != 0 else None

    n_Tmax_gt55 = (df["Tmax_C"] > 55).sum()
    tmax_medio = df["Tmax_C"].mean()

    report = {
        "Capacità nominale (Ah)": C_nom,
        "Cicli totali": n_cicli,
        "Scariche profonde (≥80%)": f"{n_scariche_prof} ({perc_scariche_prof:.1f} %)",
        "Cariche complete": f"{int(n_cariche_comp)} ({perc_cariche_comp:.1f} %)",
        "Cariche parziali": f"{int(n_cariche_parz)} ({perc_cariche_parz:.1f} %)",
        "Ah medi scaricati": f"{ah_medi_scaricati:.1f} Ah",
        "DoD medio": f"{dod_medio:.1f} %",
        "Efficienza Ah media": f"{eff_ah_media:.3f}",
        "Cicli con Tmax > 55 °C": f"{n_Tmax_gt55} ({(n_Tmax_gt55/n_cicli*100):.1f} %)",
        "Tmax medio": f"{tmax_medio:.1f} °C"
    }
    return df, report, perc_scariche_prof

# ===========================
# Main
# ===========================
if uploaded_file is not None:
    try:
        df_multi = pd.read_excel(uploaded_file, header=[0, 1])
        df_multi.columns = [col[1] for col in df_multi.columns]
        df = df_multi.copy()
    except Exception as e:
        st.error(f"Errore nella lettura del file: {e}")
    else:
        df_elab, report, perc_scariche = processa_file(df, targa_batteria)

        # Info header
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
        st.write("• Monitorare attentamente i cicli in cui la temperatura si avvicina alla soglia.")
        if perc_scariche > 5:
            st.write("• Limitare le scariche profonde (>80% DoD) riprogrammando i turni o installando limitatori di scarica, per preservare la durata della batteria.")
        st.markdown("---")

        # Grafico 1: barre con spunte
        st.subheader("Grafico Ah caricati / scaricati per ciclo")
        indices = df_elab.index + 1
        ah_chg = df_elab["Ah_Chg"].tolist()
        ah_disb = df_elab["Ah_Disb"].tolist()
        flags = df_elab["FullCharge"].tolist()

        fig1, ax1 = plt.subplots(figsize=(10, 5))
        width = 0.4
        # Due colori distinti per le barre
        ax1.bar(indices - width/2, ah_chg, width=width, label="Ah caricati", color="#1f77b4")
        ax1.bar(indices + width/2, ah_disb, width=width, label="Ah scaricati", color="#d62728")

        # Spunte ✓/✗ in alto
        ymax = max(max(ah_chg), max(ah_disb)) * 1.05
        for x, ok in zip(indices, flags):
            symbol = "✓" if ok else "✗"
            color = "green" if ok else "red"
            ax1.text(x, ymax, symbol, ha='center', va='bottom',
                     fontsize=12, fontweight='bold', color=color)

        # Imposta i ticks dei cicli ogni 20
        step = 20
        ticks = list(range(1, len(indices)+1, step))
        if len(indices) not in ticks:
            ticks.append(len(indices))
        ax1.set_xticks(ticks)
        ax1.set_xticklabels([str(t) for t in ticks])
        ax1.set_xlabel("Numero Ciclo")
        ax1.set_ylabel("Ah")
        ax1.set_ylim(0, ymax * 1.1)
        ax1.grid(True, linestyle="--", linewidth=0.5, alpha=0.7)
        ax1.legend(loc="upper right")
        st.pyplot(fig1)

        # Grafico 2: temperatura
        st.subheader("Grafico Temperatura massima per ciclo")
        fig2, ax2 = plt.subplots(figsize=(10, 5))
        ax2.plot(indices, df_elab["Tmax_C"], label="Tmax (°C)",
                 color="orange", marker="^", linestyle="-", markersize=5)
        # Ticks ogni 20 per coerenza
        ax2.set_xticks(ticks)
        ax2.set_xticklabels([str(t) for t in ticks])
        ax2.axhline(55, color="red", linestyle="--", linewidth=1.2, label="Soglia 55 °C")
        ax2.set_xlabel("Numero Ciclo")
        ax2.set_ylabel("Temperatura (°C)")
        ax2.grid(True, linestyle="--", linewidth=0.5, alpha=0.7)
        ax2.legend(loc="upper right")
        st.pyplot(fig2)

else:
    st.info("Carica un file Excel per avviare l'elaborazione.")
