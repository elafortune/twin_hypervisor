"""Outils symboliques de l'agent M6 (le LLM choisit l'outil et ses arguments ; l'outil CALCULE).

Familles (au moins 4 exigées par l'énoncé) :
- requête SPARQL : gabarits paramétrés (un par intention) + `sparql` libre en lecture seule ;
- planificateur d'évacuation : `itineraire`, `route_evacuation`, `instant_sans_route_sure` (M1/M5) ;
- optimiseur : `front_pareto_iwcmc` (résultat de PREP-NSGA, M3) ; `placer_detecteurs` (MILP de M4) ;
- validation SHACL : `valider_shacl` (delta appliqué sur une COPIE du graphe, cf. demandes.py).

Chaque outil renvoie un `Resultat` : la valeur exacte (GlobalId IFC ou nombre) qui part dans
answers.jsonl, les requêtes SPARQL réellement exécutées et un texte court lisible par le LLM.
Aucun nom propre au duplex : niveaux, espaces, logements et seuils sont des ARGUMENTS.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from rdflib import Graph

from twinhyp.m2_graphe import requetes as R


class ErreurOutil(ValueError):
    """Erreur renvoyée au LLM (message exploitable pour qu'il corrige son appel)."""


@dataclass
class Resultat:
    valeur: Any
    requetes: list[str] = field(default_factory=list)
    texte: str = ""


@dataclass
class Boite:
    """Ce que les outils voient : le graphe et les sorties des modules précédents."""
    g: Graph
    params: dict
    pareto: Path | None = None
    devices: Path | None = None
    geometrie: Path | None = None
    ontologie: Path | None = None
    formes: list[Path] = field(default_factory=list)


# Résolution des noms ---------------------------------------------------------------------
ESPACES = R.PREFIXES + """SELECT ?gid ?nom ?nl ?niv ?log WHERE {
    ?s a bot:Space ; rdfs:label ?nom ; ssi:ifcGlobalId ?gid .
    OPTIONAL { ?s ssi:longName ?nl } OPTIONAL { ?n bot:hasSpace ?s ; rdfs:label ?niv }
    OPTIONAL { ?s ssi:inDwelling ?d . ?d rdfs:label ?log } }"""
NIVEAUX = R.PREFIXES + """SELECT ?nom WHERE { ?n a bot:Storey ; rdfs:label ?nom }"""
LOGEMENTS = R.PREFIXES + """SELECT ?nom WHERE { ?d a ssi:Dwelling ; rdfs:label ?nom }"""


def _espaces(g: Graph) -> list[dict]:
    return [{"gid": str(a), "nom": str(b), "nom_long": str(c) if c else "", "niveau": str(d) if d else "",
             "logement": str(e) if e else ""} for a, b, c, d, e in R.executer(g, ESPACES)]


def libelles(g: Graph) -> dict[str, str]:
    lib = {e["gid"]: f"{e['nom']} ({e['nom_long']})" if e["nom_long"] else e["nom"] for e in _espaces(g)}
    for gid, nom in R.executer(g, R.PREFIXES + "SELECT ?gid ?l WHERE { ?p a ssi:Door ; ssi:ifcGlobalId ?gid ; rdfs:label ?l }"):
        lib[str(gid)] = f"porte {nom}"
    return lib


def _norm(x: str) -> str:
    return re.sub(r"\s+", " ", str(x)).strip().casefold()


def resoudre_espace(g: Graph, nom: str, nom_long: str | None = None, logement: str | None = None) -> str:
    """Nom (« A202 »), nom long (« Bedroom 2 ») et/ou logement -> GlobalId unique, sinon ErreurOutil."""
    tous = _espaces(g)
    c = [e for e in tous if _norm(e["nom"]) == _norm(nom) or _norm(e["nom_long"]) == _norm(nom)]
    if nom_long:
        c = [e for e in c if _norm(e["nom_long"]) == _norm(nom_long)] or c
    if logement and len(c) > 1:
        lg = _norm(logement)
        c = [e for e in c if lg == _norm(e["logement"]) or _norm(e["logement"]).endswith(" " + lg)
             or _norm(e["nom"]).startswith(lg)] or c
    if len(c) == 1:
        return c[0]["gid"]
    if not c:
        raise ErreurOutil(f"aucun espace nommé « {nom} » ; espaces connus : " + ", ".join(sorted({e['nom'] for e in tous})))
    raise ErreurOutil(f"« {nom} » est ambigu ({len(c)} espaces : " + "; ".join(
        f"{e['nom']} / {e['nom_long']} / {e['logement']}" for e in c) + ") : préciser nom_long ou logement")


def _niveau(g: Graph, niveau: str) -> str:
    noms = [str(l[0]) for l in R.executer(g, NIVEAUX)]
    for n in noms:
        if _norm(n) == _norm(niveau) or _norm(n).replace(" ", "") == _norm(niveau).replace(" ", ""):
            return n
    raise ErreurOutil(f"niveau « {niveau} » inconnu ; niveaux : {', '.join(sorted(noms))}")


def _logement(g: Graph, logement: str) -> str:
    noms = [str(l[0]) for l in R.executer(g, LOGEMENTS)]
    for n in noms:
        if _norm(n) == _norm(logement) or _norm(n).endswith(" " + _norm(logement)):
            return n
    raise ErreurOutil(f"logement « {logement} » inconnu ; logements : {', '.join(sorted(noms))}")


def _ensemble(b: Boite, gids, requetes) -> Resultat:
    gids = sorted({str(x) for x in gids})
    lib = libelles(b.g)
    return Resultat(gids, list(requetes), f"{len(gids)} élément(s) : " + (", ".join(lib.get(x, x) for x in gids) or "aucun"))


def _gabarit(b: Boite, cle: str, **p) -> Resultat:
    texte = R.requete(cle, **p)
    lignes = R.executer(b.g, texte)
    return _ensemble(b, [l[0] for l in lignes if l[0] is not None], [texte])


def _somme(b: Boite, cle: str, **p) -> Resultat:
    texte = R.requete(cle, **p)
    v = round(float(R.executer(b.g, texte)[0][0] or 0), 2)
    return Resultat(v, [texte], f"{v}")


# Types d'espaces : le LLM nomme un type, l'outil le traduit en motif sur le nom long (FR/EN)
TYPES_ESPACE = {
    "salle_de_bain": "bath|salle de bain|salle d'eau|sdb|shower|douche",
    "toilettes": "toilet|wc|water|restroom|lavatory|(^| )rr( |$)",  # « MENS RR » : bureaux NIBS (étape 10)
    "chambre": "bed|chambre",
    "cuisine": "kitchen|cuisine",
    "sejour": "living|séjour|salon",
    "couloir": "hall|corridor|couloir|dégagement",
    "entree": "foyer|entrée|entry|lobby",
    "escalier": "stair|escalier",
    "buanderie": "utility|buanderie|cellier|laundry",
    "bureau": "office|bureau",
    "salle_de_reunion": "conference|meeting|réunion",
    "local_technique": "mech|elec|server|tele|ups|technique",
}


# Outils « requête » --------------------------------------------------------------------------
def espaces_du_niveau(b: Boite, niveau: str) -> Resultat:
    return _gabarit(b, "Q01", niveau=_niveau(b.g, niveau))


def portes_exterieures(b: Boite) -> Resultat:
    return _gabarit(b, "Q02")


def espaces_avec_sortie_directe(b: Boite) -> Resultat:
    return _gabarit(b, "Q03")


def espaces_ouverts_vers(b: Boite, espace: str) -> Resultat:
    resoudre_espace(b.g, espace)
    return _gabarit(b, "Q04", espace=espace)


def surface_totale(b: Boite, prefixe: str | None = None, niveau: str | None = None) -> Resultat:
    if bool(prefixe) == bool(niveau):
        raise ErreurOutil("donner soit `prefixe` (préfixe des noms d'espaces, ex. logement), soit `niveau`")
    return _somme(b, "Q05", prefixe=prefixe) if prefixe else _somme(b, "Q10", niveau=_niveau(b.g, niveau))


def espaces_a_porte_unique(b: Boite, niveau: str) -> Resultat:
    return _gabarit(b, "Q06", niveau=_niveau(b.g, niveau))


def liaisons_verticales(b: Boite) -> Resultat:
    return _gabarit(b, "Q09")


def plus_grand_espace_par_logement(b: Boite) -> Resultat:
    return _gabarit(b, "Q11")


def espaces_du_niveau_par_type(b: Boite, niveau: str, type_espace: str) -> Resultat:
    if type_espace not in TYPES_ESPACE:
        raise ErreurOutil(f"type_espace inconnu ; valeurs : {', '.join(TYPES_ESPACE)}")
    return _gabarit(b, "Q12", niveau=_niveau(b.g, niveau), motif=TYPES_ESPACE[type_espace])


def passages_entre_logements(b: Boite, logement_a: str, logement_b: str) -> Resultat:
    return _gabarit(b, "Q13", logement_a=_logement(b.g, logement_a), logement_b=_logement(b.g, logement_b))


def portes_plus_etroites_que(b: Boite, seuil_m: float) -> Resultat:
    return _gabarit(b, "Q14", seuil=float(seuil_m))


def sparql(b: Boite, requete: str) -> Resultat:
    """Lecture seule : toute mise à jour est refusée (le graphe n'est modifié que par le moteur de règles)."""
    if re.search(r"\b(INSERT|DELETE|LOAD|CLEAR|DROP|CREATE|ADD|MOVE|COPY)\b", requete, re.I):
        raise ErreurOutil("requête de mise à jour refusée : l'outil sparql est en lecture seule")
    texte = requete if "PREFIX ssi:" in requete else R.PREFIXES + requete
    try:
        lignes = R.executer(b.g, texte)
    except Exception as exc:  # erreur de syntaxe : renvoyée au LLM pour auto-correction
        raise ErreurOutil(f"requête invalide : {exc}") from exc
    if lignes and len(lignes[0]) == 1 and isinstance(lignes[0][0], (int, float)) and len(lignes) == 1:
        return Resultat(float(lignes[0][0]), [texte], str(lignes[0][0]))
    return _ensemble(b, [l[0] for l in lignes if l and l[0] is not None], [texte])


# Outils « planificateur » ---------------------------------------------------------------------
def itineraire(b: Boite, depart: str, arrivee: str, mesure: str, depart_nom_long: str | None = None,
               logement: str | None = None, inclure_depart: bool = False) -> Resultat:
    """Plus court chemin (distances de M1, Dijkstra) de l'espace `depart` jusqu'à la sortie de l'espace `arrivee`."""
    d = resoudre_espace(b.g, depart, depart_nom_long, logement)
    a = resoudre_espace(b.g, arrivee, None, logement)
    try:
        c = R.chemin(b.g, d, a)
    except ValueError as exc:
        raise ErreurOutil(f"pas de sortie depuis l'espace « {arrivee} » : {exc}") from exc
    if mesure == "largeur_min_portes":
        return Resultat(c["largeur_min_porte_m"], c["requetes"], f"{c['largeur_min_porte_m']} m")
    if mesure == "espaces_traverses":
        res = _ensemble(b, c["espaces"] if inclure_depart else c["espaces"][1:], c["requetes"])
        res.valeur = c["espaces"] if inclure_depart else c["espaces"][1:]  # ordre du parcours conservé
        return res
    if mesure == "distance_m":
        return Resultat(c["distance_m"], c["requetes"], f"{c['distance_m']} m")
    raise ErreurOutil("mesure : largeur_min_portes, espaces_traverses ou distance_m")


def _instant(b: Boite, t_s) -> int:
    from twinhyp.m5_evacuation import instant_alarme

    if isinstance(t_s, str) and _norm(t_s) in ("alarme", "alarm", "instant de l'alarme"):
        t = instant_alarme(b.g)
        if t is None:
            raise ErreurOutil("aucune alarme dans le scénario")
        return t
    try:
        return int(float(t_s))
    except (TypeError, ValueError) as exc:
        raise ErreurOutil("t_s : un nombre de secondes ou \"alarme\"") from exc


def route_evacuation(b: Boite, espace: str, t_s, inclure_depart: bool = True, nom_long: str | None = None) -> Resultat:
    """Stratégie 2 : plus court chemin évitant tout espace Dangerous à l'instant t (contrainte dure F8)."""
    from twinhyp.m5_evacuation import route_a

    gid = resoudre_espace(b.g, espace, nom_long)
    t = _instant(b, t_s)
    route, req = route_a(b.g, gid, t)
    if route is None:
        return Resultat([], req, f"t = {t} s : aucune route sûre depuis {espace}")
    pts = route["route"] if inclure_depart else route["route"][1:]
    res = _ensemble(b, pts, req)
    res.valeur = pts
    res.texte = f"t = {t} s, sortie {route['sortie_globalId']}, {route['distance_m']} m : {res.texte}"
    return res


def instant_sans_route_sure(b: Boite, espace: str, nom_long: str | None = None) -> Resultat:
    from twinhyp.m5_evacuation import plus_de_route_sure

    t, req = plus_de_route_sure(b.g, resoudre_espace(b.g, espace, nom_long))
    if t is None:
        raise ErreurOutil(f"{espace} garde une route sûre pendant tout le scénario")
    return Resultat(t, req, f"{t} s")


def premiere_alarme_fumee(b: Boite, seuil_par_m: float) -> Resultat:
    texte = R.requete("Q15", seuil=float(seuil_par_m))
    lignes = R.executer(b.g, texte)
    if not lignes or lignes[0][0] is None:
        raise ErreurOutil("aucune observation au-dessus du seuil")
    return Resultat(int(lignes[0][0]), [texte], f"{int(lignes[0][0])} s")


def espaces_dangereux(b: Boite, t_s: float) -> Resultat:
    return _gabarit(b, "Q16", t=int(_instant(b, t_s)))


def espaces_occupes(b: Boite, t_s: float) -> Resultat:
    return _gabarit(b, "Q19", t=int(_instant(b, t_s)))


# Outil « optimiseur » -------------------------------------------------------------------------
def front_pareto_iwcmc(b: Boite, couverture_min: float, avec_jumeau: bool = True, mu: int = 0) -> Resultat:
    """Plus petit nombre de nœuds du front de Pareto (PREP-NSGA, M3) atteignant `couverture_min`."""
    from twinhyp.m3_iwcmc import nom_scenario

    if b.pareto is None or not b.pareto.is_file():
        raise ErreurOutil("pareto.json absent : lancer M3")
    seuil = float(couverture_min)
    seuil = seuil / 100 if seuil > 1 else seuil
    nom = nom_scenario(bool(avec_jumeau), int(mu))
    scen = next((s for s in json.loads(b.pareto.read_text(encoding="utf-8")) if s["scenario"] == nom), None)
    if scen is None:
        raise ErreurOutil(f"scénario {nom} absent de pareto.json")
    n = min((p["n_equipements"] for p in scen["front"] if p["couverture"] >= seuil), default=None)
    if n is None:
        raise ErreurOutil(f"aucune solution du front {nom} n'atteint {seuil:.0%}")
    return Resultat(n, [], f"{n} nœud(s) (front « {nom} », couverture ≥ {seuil:.0%})")


# Registre : nom -> (fonction, description, schéma des paramètres) ------------------------------
S, N, B_ = {"type": "string"}, {"type": "number"}, {"type": "boolean"}


def _p(props: dict, requis: list[str]) -> dict:
    return {"type": "object", "properties": props, "required": requis}


OUTILS: dict[str, tuple[Callable, str, dict]] = {
    "espaces_du_niveau": (espaces_du_niveau, "Espaces situés à un niveau (étage).", _p({"niveau": S}, ["niveau"])),
    "portes_exterieures": (portes_exterieures, "Portes qui donnent directement sur l'extérieur (sorties).", _p({}, [])),
    "espaces_avec_sortie_directe": (espaces_avec_sortie_directe,
                                    "Espaces ayant une porte de sortie vers l'extérieur (accès direct).", _p({}, [])),
    "espaces_ouverts_vers": (espaces_ouverts_vers, "Espaces communiquant avec un espace donné par une ouverture libre (sans porte).",
                             _p({"espace": S}, ["espace"])),
    "surface_totale": (surface_totale, "Somme des surfaces (propriété GSA BIM Area) des espaces dont le nom commence par "
                       "`prefixe`, OU des espaces d'un `niveau` (donner un seul des deux).",
                       _p({"prefixe": S, "niveau": S}, [])),
    "espaces_a_porte_unique": (espaces_a_porte_unique, "Espaces d'un niveau qui n'ont qu'une seule porte.",
                               _p({"niveau": S}, ["niveau"])),
    "itineraire": (itineraire, "Plus court chemin d'évacuation (sans danger) d'un espace de départ jusqu'à la porte de "
                   "sortie de l'espace `arrivee`. mesure : largeur_min_portes (m, portes franchies), espaces_traverses "
                   "(liste), distance_m. Si le nom de départ est ambigu, préciser depart_nom_long et/ou logement.",
                   _p({"depart": S, "arrivee": S, "mesure": {"type": "string", "enum": ["largeur_min_portes", "espaces_traverses", "distance_m"]},
                       "depart_nom_long": S, "logement": S, "inclure_depart": B_}, ["depart", "arrivee", "mesure"])),
    "liaisons_verticales": (liaisons_verticales, "Espaces assurant la liaison verticale entre niveaux (escaliers).", _p({}, [])),
    "plus_grand_espace_par_logement": (plus_grand_espace_par_logement, "Pour chaque logement, l'espace de plus grande surface.", _p({}, [])),
    "espaces_du_niveau_par_type": (espaces_du_niveau_par_type, "Espaces d'un niveau d'un type donné.",
                                   _p({"niveau": S, "type_espace": {"type": "string", "enum": list(TYPES_ESPACE)}},
                                      ["niveau", "type_espace"])),
    "passages_entre_logements": (passages_entre_logements, "Portes ou ouvertures reliant directement deux logements.",
                                 _p({"logement_a": S, "logement_b": S}, ["logement_a", "logement_b"])),
    "portes_plus_etroites_que": (portes_plus_etroites_que, "Portes de largeur strictement inférieure à un seuil (m).",
                                 _p({"seuil_m": N}, ["seuil_m"])),
    "premiere_alarme_fumee": (premiere_alarme_fumee, "Scénario : premier instant (s) où l'obscurcissement dépasse un seuil (/m).",
                              _p({"seuil_par_m": N}, ["seuil_par_m"])),
    "espaces_dangereux": (espaces_dangereux, "Scénario : espaces dans l'état Dangerous à l'instant t_s (s).", _p({"t_s": N}, ["t_s"])),
    "espaces_occupes": (espaces_occupes, "Scénario : espaces comptant encore des personnes à l'instant t_s (s).", _p({"t_s": N}, ["t_s"])),
    "route_evacuation": (route_evacuation, "Scénario, stratégie 2 (graphe dynamique, aucun espace dangereux traversé) : "
                         "espaces traversés par la route recommandée depuis `espace` à l'instant t_s (nombre de secondes, "
                         "ou \"alarme\" pour l'instant de l'alarme).",
                         _p({"espace": S, "t_s": {"type": ["number", "string"]}, "inclure_depart": B_, "nom_long": S}, ["espace", "t_s"])),
    "instant_sans_route_sure": (instant_sans_route_sure, "Scénario : premier instant (s) à partir duquel les occupants "
                                "d'un espace n'ont plus aucune route sûre.", _p({"espace": S, "nom_long": S}, ["espace"])),
    "front_pareto_iwcmc": (front_pareto_iwcmc, "Optimiseur PREP-NSGA (reproduction IWCMC) : plus petit nombre de nœuds "
                           "d'une solution du front de Pareto atteignant une couverture minimale (0–1).",
                           _p({"couverture_min": N, "avec_jumeau": B_, "mu": {"type": "integer"}}, ["couverture_min"])),
    "sparql": (sparql, "Requête SPARQL SELECT libre (lecture seule) sur le graphe, si aucun autre outil ne convient. "
               "Préfixes ssi:, bot:, rdfs:, sosa: déjà déclarés. Renvoyer ?gid (ssi:ifcGlobalId) ou un nombre.",
               _p({"requete": S}, ["requete"])),
}


def schemas_ollama() -> list[dict]:
    return [{"type": "function", "function": {"name": n, "description": d, "parameters": p}}
            for n, (_, d, p) in OUTILS.items()]


def appeler(b: Boite, nom: str, arguments: dict) -> Resultat:
    if nom not in OUTILS:
        raise ErreurOutil(f"outil inconnu « {nom} » ; outils : {', '.join(OUTILS)}")
    f, _, schema = OUTILS[nom]
    args = {k: v for k, v in (arguments or {}).items() if k in schema["properties"] and v not in (None, "")}
    for k, v in list(args.items()):  # petits modèles : booléens envoyés en texte (« False » serait vrai en Python)
        if schema["properties"][k].get("type") == "boolean" and isinstance(v, str):
            if v.strip().lower() not in ("true", "false", "vrai", "faux", "1", "0"):
                raise ErreurOutil(f"{k} doit être true ou false")
            args[k] = v.strip().lower() in ("true", "vrai", "1")
    manquants = [k for k in schema["required"] if k not in args]
    if manquants:
        raise ErreurOutil(f"arguments manquants : {', '.join(manquants)}")
    try:
        return f(b, **args)
    except ErreurOutil:
        raise
    except (TypeError, ValueError, KeyError) as exc:
        raise ErreurOutil(f"{type(exc).__name__} : {exc}") from exc
