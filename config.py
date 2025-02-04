LANGUAGE_CONFIGS = {
    "fr": {
        "name": "French",
        "section_marker": "section",
        "section_format": "both",
        "sections": {
            "1": ["un", "1", "a"],
            "2": ["deux", "2", "b"],
            "3": ["trois", "3", "c"],
            "4": ["quatre", "4", "d"],
            "5": ["cinq", "5", "e"],
        },
    },
    "de": {
        "name": "German",
        "section_marker": "fragen zu teil",
        "section_format": "number",
        "sections": {
            "1": ["eins", "1"],
            "2": ["zwei", "2"],
            "3": ["drei", "3"],
            "4": ["vier", "4"],
            "5": ["fünf", "5"],
        },
    },
    "es": {
        "name": "Spanish",
        "section_marker": [
            "sección",
            "seccion",
        ],  # Both accented and non-accented versions
        "section_format": "number",
        "sections": {
            "1": ["uno", "1", "primera"],
            "2": ["dos", "2", "segunda"],
            "3": ["tres", "3", "tercera"],
            "4": ["cuatro", "4", "cuarta"],
            "5": ["cinco", "5", "quinta"],
        },
    },
}
