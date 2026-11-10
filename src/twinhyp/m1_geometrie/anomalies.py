"""Détection des incohérences de la maquette par règles génériques (invariants).

Chaque règle exprime un invariant qu'une maquette saine respecte ; chaque
violation devient une anomalie {element_globalId, description, traitement}.
Aucune règle ne connaît les GlobalId ou les noms du duplex.

Étape 1 : règles sur les attributs et propriétés. Les règles de connectivité
(porte bordant plus de 2 espaces, désaccord entre sources…) arrivent à l'étape 2.
"""

from __future__ import annotations

import re
from collections import defaultdict

from twinhyp.m1_geometrie import ifc_outils as io

# Plages plausibles d'un escalier (m) ; hors plage -> anomalie.
HAUTEUR_MARCHE_M = (0.10, 0.25)
GIRON_M = (0.20, 0.40)
PIED_M = 0.3048
TOLERANCE_NIVEAU_M = 0.30


def anomalie(gid: str, description: str, traitement: str, regle: str, **extra) -> dict:
    return {"element_globalId": gid, "description": description, "traitement": traitement,
            "regle": regle, **extra}


# ------------------------------------------------------------------------------
def noms_dupliques(espaces: list[dict]) -> list[dict]:
    """Invariant : le nom (numéro) d'un espace est unique dans le bâtiment."""
    par_nom = defaultdict(list)
    for e in espaces:
        par_nom[e["nom"]].append(e)
    sortie = []
    for nom, groupe in sorted(par_nom.items()):
        if len(groupe) < 2:
            continue
        details = ", ".join(f"{e['globalId']} « {e['nom_long']} »" for e in groupe)
        for e in groupe:
            sortie.append(anomalie(
                e["globalId"], f"Nom d'espace « {nom} » porté par {len(groupe)} espaces : {details}.",
                "Identification par GlobalId uniquement ; nom conservé ; libellé affiché « nom (nom long) ».",
                "nom_unique"))
    return sortie


def nom_contredit_proprietes(f, espaces: list[dict]) -> list[dict]:
    """Invariant : le nom IFC d'un espace égale les copies redondantes de ce nom
    dans ses propriétés (ex. `Number` ou `Reference` des psets d'identité)."""
    sortie = []
    for e in espaces:
        el = f.by_guid(e["globalId"])
        for cle in ("Number", "Reference"):
            for pset, valeur in io.chercher_propriete(el, cle):
                if isinstance(valeur, str) and valeur and valeur != e["nom"]:
                    sortie.append(anomalie(
                        e["globalId"],
                        f"Nom IFC « {e['nom']} » différent de {pset}.{cle} = « {valeur} ».",
                        f"Nom IFC conservé (attribut normatif) ; la valeur « {valeur} » est signalée comme "
                        "nom probable d'origine.", "nom_coherent_proprietes", valeur_propriete=valeur))
    return sortie


def _base(nom_long: str | None) -> str:
    return re.sub(r"[\d\s]+$", "", (nom_long or "").strip().lower())


def jumeaux_noms_differents(f, espaces: list[dict]) -> list[dict]:
    """Invariant : deux espaces de géométrie identique (logements symétriques) et
    de même catégorie ont la même fonction (nom long sans numéro)."""
    sortie = []
    cle = lambda e: (e["niveau_globalId"], round(e["surface_geometrique_m2"], 1), round(e["hauteur_m"], 2))
    groupes = defaultdict(list)
    for e in espaces:
        groupes[cle(e)].append(e)
    for groupe in groupes.values():
        bases = {_base(e["nom_long"]) for e in groupe}
        if len(groupe) < 2 or len(bases) < 2:
            continue
        categories = {}
        for e in groupe:
            cats = [v for _, v in io.chercher_propriete(f.by_guid(e["globalId"]), "OmniClass Table 13 Category")]
            categories[e["globalId"]] = cats[0] if cats else None
        # l'espace minoritaire est suspect ; à égalité, celui dont le nom ne figure pas dans sa catégorie
        for e in groupe:
            cat = categories[e["globalId"]] or ""
            if _base(e["nom_long"]) and _base(e["nom_long"]) not in cat.lower():
                autres = [o for o in groupe if o is not e]
                sortie.append(anomalie(
                    e["globalId"],
                    f"Espace « {e['nom']} » nommé « {e['nom_long']} » alors que son jumeau géométrique "
                    f"{autres[0]['nom']} s'appelle « {autres[0]['nom_long']} » et que sa catégorie est « {cat} ».",
                    "Fonction déduite de la catégorie (ex. escalier) ; nom long conservé mais non utilisé "
                    "pour qualifier l'espace.", "fonction_coherente"))
    return sortie


def booleens_mal_types(f) -> list[dict]:
    """Invariant : une propriété booléenne (préfixe Is/Has) a une valeur booléenne."""
    par_valeur = defaultdict(list)
    for el in f.by_type("IfcElement") + f.by_type("IfcSpace"):
        for pset, valeurs in io.proprietes(el).items():
            for nom, v in valeurs.items():
                if re.match(r"^(Is|Has)[A-Z]", nom) and not isinstance(v, bool) and v is not None:
                    par_valeur[(nom, pset, str(v))].append(el.GlobalId)
    sortie = []
    for (nom, pset, v), gids in sorted(par_valeur.items()):
        gids = sorted(set(gids))
        sortie.append(anomalie(
            gids[0], f"Propriété {pset}.{nom} = « {v} » (texte au lieu d'un booléen) sur {len(gids)} élément(s).",
            f"Propriété ignorée : les sorties sont déterminées par la géométrie et Pset_DoorCommon.IsExternal "
            "(recoupement à l'étape 2).", "booleen_type", elements_concernes=gids))
    return sortie


def niveau_attendu(z_bas: float, niveaux: list[dict]) -> dict | None:
    candidats = [n for n in niveaux if n["altitude_m"] <= z_bas + TOLERANCE_NIVEAU_M]
    return max(candidats, key=lambda n: n["altitude_m"]) if candidats else None


def rattachement_niveau(espaces: list[dict], escaliers: list[dict], niveaux: list[dict]) -> list[dict]:
    """Invariant : un élément est rattaché au niveau sur lequel il repose."""
    nom_niveau = {n["globalId"]: n["nom"] for n in niveaux}
    sortie = []
    for el, genre in [(e, "Espace") for e in espaces] + [(s, "Escalier") for s in escaliers]:
        attendu = niveau_attendu(el["z_bas_m"], niveaux)
        if attendu and el["niveau_globalId"] != attendu["globalId"]:
            sortie.append(anomalie(
                el["globalId"],
                f"{genre} « {el['nom']} » rattaché au niveau « {nom_niveau.get(el['niveau_globalId'])} » "
                f"alors que sa base est à z = {el['z_bas_m']} m (niveau « {attendu['nom']} », "
                f"altitude {attendu['altitude_m']} m).",
                f"Niveau corrigé en « {attendu['nom']} » pour la connectivité ; rattachement IFC signalé.",
                "rattachement_niveau", niveau_corrige_globalId=attendu["globalId"]))
    return sortie


def rattachement_spatial(f) -> list[dict]:
    """Invariant : tout élément physique est rattaché à la structure spatiale
    (IfcRelContainedInSpatialStructure), directement ou via l'assemblage dont il fait partie.
    Un élément orphelin n'apparaît sous aucun niveau dans les visionneuses (arbre du projet)."""
    sortie = []
    for el in sorted(f.by_type("IfcElement"), key=lambda e: e.GlobalId):
        if el.is_a("IfcFeatureElement"):  # ouvertures : rattachées à leur hôte
            continue
        parent, rattache = el, False
        while parent is not None and not rattache:
            rattache = bool(getattr(parent, "ContainedInStructure", None))
            parent = io.ue.get_aggregate(parent)
        if rattache:
            continue
        deduit = io.niveau_de(el)
        sortie.append(anomalie(
            el.GlobalId,
            f"{el.is_a()} « {el.Name} » n'est rattaché à aucun niveau (absent de IfcRelContainedInSpatialStructure) : "
            "il n'apparaît sous aucun niveau dans l'arborescence d'une visionneuse.",
            f"Niveau déduit du placement / de l'élément hôte : « {deduit.Name if deduit else '?'} » ; "
            "élément conservé dans la connectivité.", "rattachement_spatial"))
    return sortie


def dimensions_escalier(escaliers: list[dict]) -> list[dict]:
    """Invariant : hauteur de marche et giron déclarés dans des plages plausibles,
    et cohérents avec la géométrie (hauteur de la volée / nombre de contremarches)."""
    sortie = []
    for s in escaliers:
        for v in s["volees"]:
            n = v["contremarches"]
            geo = (s["z_haut_m"] - s["z_bas_m"]) / n if n else None
            for cle, plage, libelle in [("hauteur_marche_declaree", HAUTEUR_MARCHE_M, "hauteur de marche"),
                                        ("giron_declare", GIRON_M, "giron")]:
                x = v[cle]
                if x is None or plage[0] <= x <= plage[1]:
                    continue
                en_pieds = plage[0] <= x * PIED_M <= plage[1]
                msg = (f"Volée {v['globalId']} : {libelle} déclaré(e) = {x:.4f} m, hors plage {plage} m"
                       + (f" ; {x:.4f} pied = {x * PIED_M:.3f} m : valeur probablement en pieds" if en_pieds else "")
                       + (f" ; hauteur géométrique par marche = {geo:.3f} m." if geo and cle.startswith("hauteur") else "."))
                sortie.append(anomalie(
                    s["globalId"], msg,
                    "Valeur déclarée ignorée ; la longueur de la volée est calculée sur la géométrie.",
                    "dimensions_escalier"))
    return sortie


def detecter(f, niveaux: list[dict], espaces: list[dict], escaliers: list[dict]) -> list[dict]:
    regles = [
        noms_dupliques(espaces),
        nom_contredit_proprietes(f, espaces),
        jumeaux_noms_differents(f, espaces),
        booleens_mal_types(f),
        rattachement_niveau(espaces, escaliers, niveaux),
        rattachement_spatial(f),
        dimensions_escalier(escaliers),
    ]
    return [a for r in regles for a in r]
