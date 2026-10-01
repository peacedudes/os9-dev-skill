# Anleitung: Wie KIs diese Wissensbasis nutzen können (Deutsch)

Empfohlene Vorgehensweise für KI-Integration:
1. Dokumenten-Indexierung: Alle Markdown-Dateien in ein Vektorindex-System (z. B. FAISS, Milvus) einspeisen, mit Metadaten (Titel, Pfad, Sprache, Themen).
2. Chunking: Texte in semantische Abschnitte (ca. 500 Wörter) teilen und mit Quelldatei/Merkmalen versehen.
3. Retrieval-Pipeline: Bei einer Anfrage zuerst relevante Chunks abrufen, dann eine Zusammenfassung / Antwort mit Kontext generieren.
4. Übersetzungs-Workflow: Für nicht-deutsche Originale automatische Übersetzung + menschliche Korrektur; Übersetzungen versionieren.
5. Prompt-Design: Verwende System-Prompts, die die Zielumgebung (OS-9, 68k) und gewünschte Ausgabeform (Codebeispiele, Schritt-für-Schritt-Anleitung) spezifizieren.

Beispiel-Workflows:
- Frage an KI: "Wie funktioniert das Dateisystem-Modul X unter OS-9?" → Retrieval relevante Kapitel → Synthese + Code-Snippets.
- Automatische Code-Generierung: Nutze Beispiele aus dem Repo als Referenz-Korpus und generiere Manager/Treiber-Stubs.

