import math


def mackay97_bcf(polluant: dict, vegetal: dict, sol: dict) -> dict:
    """
    Modèle Hung & Mackay (1997) — fugacité 3 compartiments
    Calcule BCF pour racine et feuille

    Sortie : BCF en mg/kg_vegsec / (mg/kg_sol)
    """

    # --- Paramètres de base ---
    Kow = 10 ** polluant["log_kow"]
    Koc = 10 ** polluant["log_koc"]
    H = polluant["H"]
    Corg = sol["matiere_organique"] / 1.72
    Kd = Koc * Corg

    # --- Concentration dans l'eau du sol ---
    # Bilan de masse : C_eau [mg/L] = C_sol [mg/kg] × ρb / (ρb×Kd + θw + H×θa)
    denominateur = (sol["densite"] * Kd
                    + sol["fraction_eau"]
                    + H * sol["fraction_air"])
    Ceau_sur_Csol = sol["densite"] / denominateur  # (mg/L_eau) / (mg/kg_sol) = kg/L

    # --- TSCF : Briggs 1982 uniquement ---
    # Hsu 1991 non retenu — les deux formules divergent d'~1 ordre de grandeur
    # pour 0 < log Kow < 5 (McKone & Maddalena, LBNL-60273, 2007, p.13).
    # Approche max(Briggs, Hsu) possible mais non retenue faute de consensus.
    TSCF = 0.784 * math.exp(
        -((polluant["log_kow"] - 1.78) ** 2) / 2.44
    )

    # --- Partition lipide/eau ---
    lipide = vegetal["lipide"]
    Krw_racine = lipide * Kow  # partition racine/eau
    Kfw_feuille = lipide * Kow  # partition feuille/eau

    # --- BCF racine ---
    # Cracine/Csol = TSCF * Ceau/Csol * Krw
    BCF_racine = TSCF * Ceau_sur_Csol * Krw_racine

    # --- BCF feuille ---
    Q = vegetal["evapotranspiration"]  # L/jour
    g = 1e-3  # conductance feuille m/jour (Trapp & Matthies 1995)
    A = vegetal["surface_feuille"]  # m²
    gA = g * A * 1000  # m/jour × m² × 1000 L/m³ → L/jour (même unité que Q)
    Cair = sol["conc_air"][polluant["nom"]]  # µg/m³ → converti en mg/L
    Cair_mgl = Cair * 1e-6  # µg/m³ → mg/L  (÷1e3 pour µg→mg, ÷1e3 pour m³→L)

    # Cfeuille/Csol — les deux termes déjà normalisés par Csol (implicite Csol=1 mg/kg)
    numerateur = (TSCF * Ceau_sur_Csol * Q
                  + Cair_mgl * gA / H)
    denominateur_f = (Q / Kfw_feuille + gA)
    BCF_feuille = numerateur / denominateur_f

    return {
        "BCF_racine": BCF_racine,
        "BCF_feuille": BCF_feuille,
    }