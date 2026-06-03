import math


def plantx_bcf(polluant: dict, vegetal: dict, sol: dict) -> dict:
    """
    Modèle PlantX — Trapp & Matthies (1995)
    Bilan de masse à l'état pseudo-stationnaire

    Sortie : BCF en mg/kg_vegsec / (mg/kg_sol)
    """

    # --- Paramètres de base ---
    Koc = 10 ** polluant["log_koc"]
    H = polluant["H"]
    Corg = sol["matiere_organique"] / 1.72
    Kd = Koc * Corg

    # --- Concentration eau du sol ---
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

    # --- Taux de perte (métabolisme + croissance) ---
    lambda_r  = 0.01   # /jour — taux métabolisme racine (défaut)
    lambda_f  = 0.01   # /jour — taux métabolisme feuille (défaut)
    lambda_fr = 0.005  # /jour — taux métabolisme fruit (défaut)

    # --- Volumes compartiments ---
    V_racine  = 0.1  # L (défaut)
    V_feuille = 1.0  # L (défaut)
    V_fruit   = 0.5  # L (défaut)

    # --- Flux transpiration ---
    Q = vegetal["evapotranspiration"]  # L/jour

    # --- BCF racine — toujours calculé (TSCF requis) ---
    # État stationnaire : Cracine = Q * TSCF * Ceau / (Q + lambda_r * V_r)
    BCF_racine = (Q * TSCF * Ceau_sur_Csol) / (Q + lambda_r * V_racine)

    result = {"BCF_racine": BCF_racine}

    # --- BCF feuille — uniquement si feuille ou fruit ---
    if vegetal["organe"] in ("feuille", "fruit"):
        Kxw = 0.8  # partition xylème/eau (défaut Trapp)
        F_feuille_sur_Csol = Q * BCF_racine / Kxw

        g  = 1e-3                          # conductance feuille m/jour (Trapp & Matthies 1995)
        A  = vegetal["surface_feuille"]    # m²
        gA = g * A * 1000                  # L/jour
        Cair     = sol["conc_air"][polluant["nom"]]  # µg/m³
        Cair_mgl = Cair * 1e-6             # µg/m³ → mg/L

        # Terme sol [kg/j] + terme air [mg/j → kg/j via ×1e-6]
        BCF_feuille = (
            (F_feuille_sur_Csol + Cair_mgl * gA / H * 1e-6)
            / (gA / (H * V_feuille) + lambda_f)
        )
        result["BCF_feuille"] = BCF_feuille

    # --- BCF fruit — uniquement si fruit ---
    if vegetal["organe"] == "fruit":
        Kphloem = 0.1  # L/jour — conductance phloème (défaut)
        BCF_fruit = (
            (Kphloem * BCF_feuille + Cair_mgl * gA / (H * V_fruit) * 1e-6)
            / (Kphloem / V_fruit + lambda_fr)
        )
        result["BCF_fruit"] = BCF_fruit

    return result
