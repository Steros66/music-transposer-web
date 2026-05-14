import streamlit as st
import mido
import music21
import tempfile
import os

# --- PAGE SETTINGS ---
st.set_page_config(page_title="Music Utility Pro", page_icon="🎵")
st.title("🎵 Transposer & Folder Web Pro")
st.write("Upload your MIDI or MusicXML file, modify it, and download the result!")

# Note Mapping
mappa_note = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}
lista_note = list(mappa_note.keys())

# --- ANALYSIS FUNCTIONS ---
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

# --- WEB INTERFACE ---
# 1. File Upload
uploaded_file = st.file_uploader("1. Select your music file", type=['mid', 'midi', 'xml', 'musicxml', 'mxl'])

if uploaded_file is not None:
    # Save uploaded file to a temporary file for mido/music21 to read
    estensione = os.path.splitext(uploaded_file.name)[1].lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=estensione) as tmp_originale:
        tmp_originale.write(uploaded_file.getvalue())
        percorso_orig = tmp_originale.name

    st.success(f"File '{uploaded_file.name}' successfully uploaded!")

    # Create two Tabs for Transposition and Folding
    tab1, tab2 = st.tabs(["🔄 Transposition", "📏 Melodic Folding"])

    # --- TAB 1: TRANSPOSITION ---
    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            tonalita_dest = st.selectbox("Target Key:", lista_note)
        with col2:
            direzione = st.radio("Direction:", ["Shortest Distance", "Always Up", "Always Down"])

        if st.button("Execute Transposition"):
            with st.spinner("Analyzing and processing..."):
                ton_orig_nome, modo, val_orig = analizza_tonalita(percorso_orig)
                
                distanza = mappa_note[tonalita_dest] - val_orig
                if direzione == "Shortest Distance":
                    if distanza > 6: distanza -= 12
                    if distanza < -6: distanza += 12
                elif direzione == "Always Up" and distanza < 0: distanza += 12
                elif direzione == "Always Down" and distanza > 0: distanza -= 12

                # Generate temporary output file
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

                st.success(f"Transposition complete! (Shift: {distanza} semitones)")
                
                # Download button
                with open(percorso_out, "rb") as file_out:
                    st.download_button(label="📥 Download Transposed File", data=file_out, file_name=f"transposed_{uploaded_file.name}", mime="audio/midi")

    # --- TAB 2: FOLDING ---
    with tab2:
        col3, col4 = st.columns(2)
        with col3:
            lim_inf = st.number_input("Minimum (e.g. F3=53):", value=53)
        with col4:
            lim_sup = st.number_input("Maximum (e.g. C5=72):", value=72)

        if st.button("Execute Folding"):
            with st.spinner("Compressing melody..."):
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

                st.success(f"Folding complete! Modified notes: {note_modificate}")
                
                with open(percorso_out, "rb") as file_out:
                    st.download_button(label="📥 Download Folded File", data=file_out, file_name=f"folded_{uploaded_file.name}", mime="audio/midi")
