import streamlit as st
import mido
import music21
import tempfile
import os

# --- IMPOSTAZIONI PAGINA ---
st.set_page_config(page_title="Music Utility Pro", page_icon="🎵")
st.title("🎵 Transposer & Folder Web Pro")
st.write("Carica il tuo file MIDI o MusicXML, modificalo e scarica il risultato!")

# Mappatura Note
mappa_note = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}
lista_note = list(mappa_note.keys())

# --- FUNZIONI DI ANALISI (Identiche a prima) ---
def analizza_tonalita(percorso):
    try:
        score = music21.converter.parse(percorso)
        chiavi_esplicite = score.flat.getElementsByClass(music21.key.KeySignature)
        if chiavi_esplicite:
            chiave_reale = chiavi_esplicite[0].asKey() if hasattr(chiavi_esplicite[0], 'asKey') else chiavi_esplicite[0]
            return chiave_reale.tonic.name, chiave_reale.mode, chiave_reale.tonic.pitchClass
        key = score.analyze('key')
        return key.tonic.name, key.mode, key.tonic.pitchClass 
    except Exception:
        return "C", "major", 0

# --- INTERFACCIA WEB ---
# 1. Caricamento File
uploaded_file = st.file_uploader("1. Seleziona il tuo file musicale", type=['mid', 'midi', 'xml', 'musicxml', 'mxl'])

if uploaded_file is not None:
    # Salviamo il file caricato in un file temporaneo per farlo leggere a mido/music21
    estensione = os.path.splitext(uploaded_file.name)[1].lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=estensione) as tmp_originale:
        tmp_originale.write(uploaded_file.getvalue())
        percorso_orig = tmp_originale.name

    st.success(f"File '{uploaded_file.name}' caricato con successo!")

    # Creiamo due "Tab" (schede) per separare Trasposizione e Folding
    tab1, tab2 = st.tabs(["🔄 Trasposizione", "📏 Folding Melodico"])

    # --- TAB 1: TRASPOSIZIONE ---
    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            tonalita_dest = st.selectbox("Tonalità di destinazione:", lista_note)
        with col2:
            direzione = st.radio("Direzione:", ["Distanza Minima", "Sempre in Su", "Sempre in Giù"])

        if st.button("Esegui Trasposizione"):
            with st.spinner("Analisi ed elaborazione in corso..."):
                ton_orig_nome, modo, val_orig = analizza_tonalita(percorso_orig)
                
                distanza = mappa_note[tonalita_dest] - val_orig
                if direzione == "Distanza Minima":
                    if distanza > 6: distanza -= 12
                    if distanza < -6: distanza += 12
                elif direzione == "Sempre in Su" and distanza < 0: distanza += 12
                elif direzione == "Sempre in Giù" and distanza > 0: distanza -= 12

                # Generiamo il file di output temporaneo
                with tempfile.NamedTemporaryFile(delete=False, suffix=estensione) as tmp_out:
                    percorso_out = tmp_out.name

                if estensione in ['.mid', '.midi']:
                    mid = mido.MidiFile(percorso_orig)
                    for track in mid.tracks:
                        for msg in track:
                            if msg.type in ('note_on', 'note_off'):
                                n_nota = msg.note + distanza
                                if 0 <= n_nota <= 127: msg.note = n_nota
                    mid.save(percorso_out)
                else:
                    score = music21.converter.parse(percorso_orig)
                    score_trasposto = score.transpose(distanza)
                    score_trasposto.write('musicxml', percorso_out)

                st.success(f"Trasposizione completata! (Spostamento: {distanza} semitoni)")
                
                # Bottone per il download
                with open(percorso_out, "rb") as file_out:
                    st.download_button(label="📥 Scarica File Trasposto", data=file_out, file_name=f"trasposto_{uploaded_file.name}", mime="audio/midi")

    # --- TAB 2: FOLDING ---
    with tab2:
        col3, col4 = st.columns(2)
        with col3:
            lim_inf = st.number_input("Minimo (Es. Fa3=53):", value=53)
        with col4:
            lim_sup = st.number_input("Massimo (Es. Do5=72):", value=72)

        if st.button("Esegui Folding"):
            with st.spinner("Compressione della melodia in corso..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix=estensione) as tmp_out:
                    percorso_out = tmp_out.name
                
                note_modificate = 0

                if estensione in ['.mid', '.midi']:
                    mid = mido.MidiFile(percorso_orig)
                    for track in mid.tracks:
                        for msg in track:
                            if msg.type in ('note_on', 'note_off'):
                                n_nota = msg.note
                                nota_orig = msg.note
                                while n_nota < lim_inf: n_nota += 12
                                while n_nota > lim_sup: n_nota -= 12
                                if 0 <= n_nota <= 127:
                                    msg.note = n_nota
                                    if n_nota != nota_orig and msg.type == 'note_on': note_modificate += 1
                    mid.save(percorso_out)
                else:
                    score = music21.converter.parse(percorso_orig)
                    for element in score.recurse().notes:
                        if element.isNote:
                            while element.pitch.midi < lim_inf: element.pitch.octave += 1; note_modificate += 1
                            while element.pitch.midi > lim_sup: element.pitch.octave -= 1; note_modificate += 1
                    score.write('musicxml', percorso_out)

                st.success(f"Folding completato! Note modificate: {note_modificate}")
                
                with open(percorso_out, "rb") as file_out:
                    st.download_button(label="📥 Scarica File Foldato", data=file_out, file_name=f"folded_{uploaded_file.name}", mime="audio/midi")