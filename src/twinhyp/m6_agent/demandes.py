"""Traitement des demandes de modification : plan (LLM) -> delta -> veto SHACL -> adaptations -> décision.

1. Le LLM traduit la demande en PLAN structuré (sortie JSON contrainte par un schéma).
2. Le moteur de règles calcule le delta Δ = (triplets ajoutés, triplets retirés) de l'action demandée.
3. Δ est appliqué sur une COPIE du graphe, validée par SHACL (formes publiques + maison) : c'est le
   veto symbolique, dans le code ; le LLM ne peut pas le contourner.
4. Si l'action viole une forme, des adaptations sont générées par règles, validées de la même façon,
   puis classées par l'ordre lexicographique sécurité des personnes > accessibilité > sobriété
   (puis, à égalité, satisfaction de la demande).
5. Le candidat retenu est appliqué au graphe (commit) ; les suivants voient ce graphe (effet cumulatif).
6. Le LLM rédige la justification à partir des faits calculés ; il ne peut pas changer la décision.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from rdflib import RDF, Graph, Literal, URIRef
from rdflib.namespace import SOSA

from twinhyp.io_schemas import formes_violees_graphe
from twinhyp.m2_graphe import requetes as R
from twinhyp.m2_graphe.construction import SSI, dec, iri
from twinhyp.m6_agent import outils as O

PLAN = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["changer_type_detecteur", "deplacer_equipement", "retirer_detecteurs",
                                               "diriger_evacuation", "autre"]},
        "espace": {"type": ["string", "null"], "description": "espace concerné (source), nom court"},
        "espace_cible": {"type": ["string", "null"], "description": "espace de destination, nom court"},
        "niveau": {"type": ["string", "null"]},
        "logement": {"type": ["string", "null"]},
        "nouveau_type": {"type": ["string", "null"], "enum": ["HeatDetector", "SmokeDetector", None]},
        "t_s": {"type": ["number", "null"]},
        "destination": {"type": ["string", "null"], "description": "ex. escalier, sortie"},
        "route": {"type": ["string", "null"], "enum": ["habituelle", "sure", None]},
        "motif": {"type": ["string", "null"], "description": "raison invoquée par le demandeur"},
    },
    "required": ["action", "espace", "espace_cible", "niveau", "logement", "nouveau_type", "t_s", "destination",
                 "route", "motif"],
}

SYSTEME_PLAN = """Tu traduis une demande de modification d'un système de sécurité incendie en plan JSON.
Actions : changer_type_detecteur (requalifier les détecteurs d'un espace, nouveau_type HeatDetector ou SmokeDetector),
deplacer_equipement (de `espace` vers `espace_cible`), retirer_detecteurs (d'un `niveau`),
diriger_evacuation (occupants d'un `niveau` et d'un `logement` vers une `destination` à l'instant t_s, `route`
habituelle ou sure), autre. Utilise les noms courts du résumé. Mets null pour les champs sans objet.

Résumé du bâtiment :
{resume}"""

SYSTEME_JUSTIF = """Tu rédiges, en français et en 2 à 4 phrases, la justification d'une décision d'un agent de sécurité
incendie. La décision est DÉJÀ prise par le moteur symbolique : ne la change pas, explique-la à partir des faits
fournis (formes SHACL violées, adaptation retenue). Ordre de priorité imposé, du plus au moins important :
1) la sécurité des personnes (détection, conformité SHACL), 2) l'accessibilité (routes sûres et praticables),
3) la sobriété (nombre d'équipements). La satisfaction de la demande ne vient qu'après ces trois critères."""

JUSTIF = {"type": "object", "properties": {"justification": {"type": "string"}}, "required": ["justification"]}

DETECTEURS = (SSI.SmokeDetector, SSI.HeatDetector)


@dataclass
class Candidat:
    nom: str
    description: str
    ajouts: set = field(default_factory=set)
    retraits: set = field(default_factory=set)
    satisfaction: float = 0.0          # part de la demande satisfaite (départage final)
    formes_violees: list[str] = field(default_factory=list)
    criteres: tuple = ()


# Validation symbolique -------------------------------------------------------------------------
class Validateur:
    """SHACL sur une copie. Les observations SOSA (≈ 20 000 triplets) sont retirées de la copie : aucun
    delta de l'agent ne les touche, et leur forme (M10) est vérifiée une fois sur le graphe initial."""

    def __init__(self, formes: list[Path], ontologie: Path):
        self.formes, self.ontologie, self.appels = formes, ontologie, 0

    def __call__(self, g: Graph, c: Candidat) -> list[str]:
        copie = Graph()
        obs = set(g.subjects(RDF.type, SOSA.Observation))
        for t in g:
            if t[0] not in obs and t not in c.retraits:
                copie.add(t)
        for t in c.ajouts:
            copie.add(t)
        self.appels += 1
        c.formes_violees = formes_violees_graphe(copie, self.formes, self.ontologie)[0]
        return c.formes_violees


# Lecture du graphe ------------------------------------------------------------------------------
def _triplets(g: Graph, s) -> set:
    return set(g.triples((s, None, None))) | set(g.triples((None, None, s)))


def detecteurs(g: Graph, espace: URIRef | None = None, niveau: URIRef | None = None) -> list[URIRef]:
    res = []
    for cls in DETECTEURS:
        for d in g.subjects(RDF.type, cls):
            if espace is not None and (d, SSI.coversSpace, espace) not in g:
                continue
            if niveau is not None and (d, SSI.onStorey, niveau) not in g:
                continue
            res.append(d)
    return sorted(set(res))


def couverture_detection(g: Graph, c: Candidat) -> float:
    """Part des espaces occupables couverts par un détecteur automatique après application du candidat."""
    ajoutes = {(s, o) for s, p, o in c.ajouts if p == SSI.coversSpace}
    retires = {(s, o) for s, p, o in c.retraits if p == SSI.coversSpace}
    couvre = {(s, o) for s, o in g.subject_objects(SSI.coversSpace)} - retires | ajoutes
    occupables = {s for s in g.subjects(SSI.occupiable, Literal(True))} or set(g.subjects(RDF.type, URIRef("https://w3id.org/bot#Space")))
    couverts = {o for _, o in couvre} & occupables
    return round(len(couverts) / max(len(occupables), 1), 4)


def nb_equipements(g: Graph, c: Candidat) -> int:
    ajout = {s for s, p, o in c.ajouts if p == RDF.type}
    retrait = {s for s, p, o in c.retraits if p == RDF.type} - ajout
    tous = {s for s, _, _ in g.triples((None, SSI.isLocatedIn, None))}
    return len((tous - retrait) | ajout)


def evaluer(g: Graph, c: Candidat, valider: Validateur) -> tuple:
    """Clé lexicographique (plus grand = meilleur) : sécurité, accessibilité, sobriété, satisfaction."""
    valider(g, c)
    securite = (not c.formes_violees, couverture_detection(g, c))
    accessibilite = (not any(f.startswith(("F4", "F8")) for f in c.formes_violees),)
    sobriete = (-nb_equipements(g, c),)
    c.criteres = (securite, accessibilite, sobriete, c.satisfaction)
    return c.criteres


# Actions ---------------------------------------------------------------------------------------
def _espace(g: Graph, nom: str | None) -> URIRef:
    if not nom:
        raise O.ErreurOutil("plan incomplet : espace manquant")
    return iri("space", O.resoudre_espace(g, nom))


def _niveau(g: Graph, nom: str | None) -> URIRef:
    nom = O._niveau(g, nom or "")
    return next(n for n in g.subjects(URIRef("http://www.w3.org/2000/01/rdf-schema#label"), Literal(nom))
                if (n, RDF.type, URIRef("https://w3id.org/bot#Storey")) in g)


def changer_type(g: Graph, plan: dict) -> list[Candidat]:
    esp = _espace(g, plan["espace"])
    nouveau = SSI[plan["nouveau_type"] or "HeatDetector"]
    cibles = detecteurs(g, esp)
    c = Candidat("demande", f"{len(cibles)} détecteur(s) couvrant {plan['espace']} -> {nouveau.split('#')[-1]}",
                 satisfaction=1.0)
    for d in cibles:
        for cls in DETECTEURS:
            if (d, RDF.type, cls) in g and cls != nouveau:
                c.retraits.add((d, RDF.type, cls))
        c.ajouts.add((d, RDF.type, nouveau))
    # un détecteur qui couvrirait aussi un autre espace : dédoubler (adaptation) — détecteurs mono-espace ici
    multi = [d for d in cibles if len(set(g.objects(d, SSI.coversSpace))) > 1]
    return [c] if not multi else [c, Candidat("refus", "aucune modification", satisfaction=0.0)]


def deplacer(g: Graph, plan: dict, boite: O.Boite) -> list[Candidat]:
    src, dst = _espace(g, plan["espace"]), _espace(g, plan["espace_cible"])
    eq = detecteurs(g, src) or sorted(d for d in g.subjects(SSI.isLocatedIn, src) if (d, RDF.type, SSI.Camera) not in g)
    if not eq:
        raise O.ErreurOutil(f"aucun équipement ne couvre {plan['espace']}")
    d = eq[0]
    niveau_dst = g.value(dst, SSI.onStorey) or next(g.subjects(URIRef("https://w3id.org/bot#hasSpace"), dst))
    demande = Candidat("demande", f"déplacer {g.value(d, URIRef('http://www.w3.org/2000/01/rdf-schema#label'))} de "
                       f"{plan['espace']} vers {plan['espace_cible']}", satisfaction=1.0)
    for p in (SSI.isLocatedIn, SSI.coversSpace):
        if (d, p, src) in g:
            demande.retraits.add((d, p, src))
            demande.ajouts.add((d, p, dst))
    for o in g.objects(d, SSI.onStorey):
        demande.retraits.add((d, SSI.onStorey, o))
    demande.ajouts.add((d, SSI.onStorey, niveau_dst))
    candidats = [demande, Candidat("refus", "aucune modification (l'équipement reste en place)")]
    # adaptation : servir l'objectif invoqué (connectivité) sans découvrir l'espace source -> relais en plus
    reseau = _reseau(boite)
    if reseau is not None:
        relais = iri("device", "RELAIS-M6-01")
        c = Candidat("relais", f"conserver l'équipement et ajouter un relais IoT dans {plan['espace_cible']}",
                     satisfaction=0.0 if reseau["composantes"] == 1 else 0.8)
        c.ajouts |= {(relais, RDF.type, SSI.SafetyDevice), (relais, SSI.isLocatedIn, dst),
                     (relais, SSI.onStorey, niveau_dst), (relais, URIRef("http://www.w3.org/2000/01/rdf-schema#label"),
                                                          Literal("RELAIS-M6-01"))}
        candidats.append(c)
    return candidats


def _reseau(boite: O.Boite) -> dict | None:
    if boite.devices is None or not boite.devices.is_file():
        return None
    return json.loads(boite.devices.read_text(encoding="utf-8"))["sous_problemes"]["reseau"]["principal"]


def retirer(g: Graph, plan: dict, boite: O.Boite) -> list[Candidat]:
    niv = _niveau(g, plan["niveau"])
    cibles = detecteurs(g, niveau=niv)
    demande = Candidat("demande", f"retirer les {len(cibles)} détecteurs automatiques du niveau {plan['niveau']}",
                       satisfaction=1.0)
    for d in cibles:
        demande.retraits |= _triplets(g, d)
    refus = Candidat("refus", "aucune modification (détection maintenue pendant les travaux)")
    # adaptation : détection temporaire par détecteurs de CHALEUR (insensibles aux poussières de chantier),
    # placés par l'optimiseur de M4 (MILP de couverture) sur les espaces du niveau
    temp = Candidat("chaleur_temporaire", "remplacer pendant les travaux les détecteurs de fumée du niveau par des "
                    "détecteurs de chaleur temporaires (placement recalculé par le MILP de M4)", satisfaction=0.5)
    temp.retraits = set(demande.retraits)
    for k, (espace, x, y, z, zone) in enumerate(placer_detecteurs_niveau(g, boite, niv, cibles), start=1):
        d = iri("device", f"DC-T{k:02d}")
        temp.ajouts |= {(d, RDF.type, SSI.HeatDetector), (d, URIRef("http://www.w3.org/2000/01/rdf-schema#label"), Literal(f"DC-T{k:02d}")),
                        (d, SSI.isLocatedIn, espace), (d, SSI.coversSpace, espace), (d, SSI.onStorey, niv),
                        (d, SSI.posX, dec(x)), (d, SSI.posY, dec(y)), (d, SSI.posZ, dec(z))}
        if zone is not None:
            temp.ajouts.add((d, SSI.inDetectionZone, zone))
    return [demande, refus, temp]


def placer_detecteurs_niveau(g: Graph, boite: O.Boite, niveau: URIRef, anciens: list[URIRef]) -> list[tuple]:
    """Outil « optimiseur » : MILP de couverture de M4 restreint aux espaces du niveau."""
    from twinhyp.m4_deploiement import placement

    geo = json.loads(boite.geometrie.read_text(encoding="utf-8"))
    gid_niveau = str(g.value(niveau, SSI.ifcGlobalId))
    sous = {**geo, "espaces": [e for e in geo["espaces"] if e["niveau_globalId"] == gid_niveau],
            "positions_autorisees": [p for p in geo["positions_autorisees"] if p["niveau_globalId"] == gid_niveau]}
    rayon = boite.params.get("detecteur_chaleur_rayon_m", boite.params["detecteur_rayon_m"])
    eqs, _ = placement.detecteurs(sous, {**boite.params, "detecteur_rayon_m": rayon}, geo["voxels"]["origine_m"][:2])
    zone_de = {g.value(d, SSI.coversSpace): g.value(d, SSI.inDetectionZone) for d in anciens}
    return [(iri("space", e["espace_globalId"]), e["x"], e["y"], e["z"], zone_de.get(iri("space", e["espace_globalId"])))
            for e in eqs]


# Évacuation dirigée (D4) : F8 évaluée à l'instant t -------------------------------------------
def etat_a(g: Graph, t: int) -> Graph:
    """Copie de g où le statut Dangerous reflète l'instant t (ssi:dangerSince ≤ t) ; routes courantes retirées."""
    from twinhyp.m5_evacuation import dangereux_a

    danger, _ = dangereux_a(g, t)
    h = Graph()
    obs = set(g.subjects(RDF.type, SOSA.Observation))
    routes = set(g.subjects(RDF.type, SSI.EvacuationRoute))
    for s, p, o in g:
        if s in obs or s in routes or p == SSI.hasStatus:
            continue
        h.add((s, p, o))
    for s, gid in g.subject_objects(SSI.ifcGlobalId):
        if (s, RDF.type, URIRef("https://w3id.org/bot#Space")) in g:
            h.add((s, SSI.hasStatus, SSI.Dangerous if str(gid) in danger else SSI.Normal))
    return h


def horodatage_a(g: Graph, t: int):
    """Horodatage (xsd:dateTime) des observations de l'instant t du scénario."""
    return next((h for o in g.subjects(SSI.scenarioTime, Literal(t)) for h in g.objects(o, SOSA.resultTime)), None)


def triplets_route(nom: str, depart: str, route: dict, quand=None) -> set:
    r = iri("route", nom)
    t = {(r, RDF.type, SSI.EvacuationRoute), (r, SSI.routeFor, iri("space", depart)),
         (r, SSI.routeTo, iri("door", route["sortie_globalId"]))}
    if quand is not None:
        t.add((r, SSI.validAt, quand))
    t |= {(r, SSI.passesThrough, iri("space", e)) for e in route["route"][1:]}
    return t


def diriger(g: Graph, plan: dict, valider: Validateur) -> list[dict]:
    """Une décision par espace du niveau et du logement visés."""
    from twinhyp.m5_evacuation import EXTERIEUR, dangereux_a, graphe_routage, occupes, route_sure

    t = int(plan["t_s"] if plan["t_s"] is not None else 0)
    esp = [e for e in O._espaces(g) if _norm_eq(e["niveau"], O._niveau(g, plan["niveau"] or ""))
           and (not plan["logement"] or e["logement"] == O._logement(g, plan["logement"]))]
    G = graphe_routage(g)
    danger, req_danger = dangereux_a(g, t)
    escaliers = set(O.liaisons_verticales(O.Boite(g, {})).valeur)
    occupation = _occupation_a(g, t)
    h = etat_a(g, t)
    quand = horodatage_a(g, t)
    decisions = []
    for e in sorted(esp, key=lambda e: e["nom"]):
        gid = e["gid"]
        habituelle = route_sure(G, gid, set())  # stratégie 1 : route statique, sans tenir compte du danger
        cand_h = Candidat("route_habituelle", "", satisfaction=1.0)
        occ = occupation.get(gid)
        faits = {"espace": f"{e['nom']} ({e['nom_long']})", "t_s": t,
                 "occupants": occ if occ is not None else "inconnu (aucun comptage dans cet espace)",
                 "espaces_dangereux": sorted(O.libelles(g).get(x, x) for x in danger)}
        if habituelle is None:
            decisions.append({"espace": e, "decision": "refusee", "candidat": None, "formes": [], "faits": faits})
            continue
        cand_h.ajouts = triplets_route(f"M6_{gid}_{t}_habituelle", gid, habituelle, quand)
        cand_h.description = "route habituelle : " + " → ".join(O.libelles(g).get(x, x) for x in habituelle["route"])
        valider(h, cand_h)
        faits["route_habituelle"] = cand_h.description
        faits["passe_par_escalier"] = bool(set(habituelle["route"]) & escaliers)
        if not cand_h.formes_violees:
            decisions.append({"espace": e, "decision": "acceptee", "candidat": cand_h, "formes": [], "faits": faits,
                              "route": habituelle})
            continue
        sure = route_sure(G, gid, danger)  # stratégie 2 : contrainte dure
        if sure is None:
            faits["route_sure"] = None
            decisions.append({"espace": e, "decision": "refusee", "candidat": None, "formes": cand_h.formes_violees,
                              "faits": faits, "adaptation": "aucune route sûre : mise à l'abri sur place (porte "
                              "fermée), position signalée aux secours"})
            continue
        cand_s = Candidat("route_sure", "route sûre : " + " → ".join(O.libelles(g).get(x, x) for x in sure["route"]),
                          triplets_route(f"M6_{gid}_{t}_sure", gid, sure, quand), satisfaction=0.5)
        valider(h, cand_s)
        faits["route_sure"] = cand_s.description
        decisions.append({"espace": e, "decision": "acceptee_avec_adaptation" if not cand_s.formes_violees else "refusee",
                          "candidat": cand_s, "formes": cand_h.formes_violees, "faits": faits, "route": sure})
    return decisions


def _norm_eq(a: str, b: str) -> bool:
    return O._norm(a) == O._norm(b)


def _occupation_a(g: Graph, t: int) -> dict[str, int]:
    gids = O.espaces_occupes(O.Boite(g, {}), t).valeur
    texte = R.PREFIXES + """SELECT ?gid ?n WHERE { ?o sosa:hasFeatureOfInterest ?s ; sosa:observedProperty ssi:Occupancy ;
        sosa:hasSimpleResult ?n ; ssi:scenarioTime %d . ?s ssi:ifcGlobalId ?gid }""" % t
    occ = {str(a): int(round(float(b))) for a, b in R.executer(g, texte)}
    return {k: occ.get(k, 0) for k in set(gids) | set(occ)}


# Orchestration ---------------------------------------------------------------------------------
def planifier(llm, demande: dict, resume: str) -> tuple[dict, dict]:
    e = llm.chat([{"role": "system", "content": SYSTEME_PLAN.format(resume=resume)},
                  {"role": "user", "content": f"Demande {demande['id']} : {demande['demande']}"}],
                 format_=PLAN, tache=f"{demande['id']}:plan")
    return json.loads(e["reponse"].get("content") or "{}"), e


def justifier(llm, demande: dict, faits: dict, secours: str) -> str:
    try:
        e = llm.chat([{"role": "system", "content": SYSTEME_JUSTIF},
                      {"role": "user", "content": json.dumps({"demande": demande["demande"], **faits}, ensure_ascii=False)}],
                     format_=JUSTIF, tache=f"{demande['id']}:justification")
        texte = json.loads(e["reponse"].get("content") or "{}").get("justification", "").strip()
        return texte or secours
    except Exception:  # la justification rédigée est un confort : la décision et les faits sont déjà établis
        return secours


def _maintenant() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def traiter(llm, g: Graph, demandes: list[dict], boite: O.Boite, valider: Validateur, resume: str) -> list[dict]:
    lignes = []
    for dem in demandes:
        plan, _ = planifier(llm, dem, resume)
        if plan.get("action") == "diriger_evacuation":
            lignes += _traiter_evacuation(llm, g, dem, plan, valider)
            continue
        try:
            if plan.get("action") == "changer_type_detecteur":
                candidats = changer_type(g, plan)
            elif plan.get("action") == "deplacer_equipement":
                candidats = deplacer(g, plan, boite)
            elif plan.get("action") == "retirer_detecteurs":
                candidats = retirer(g, plan, boite)
            else:
                raise O.ErreurOutil(f"action « {plan.get('action')} » non prise en charge")
        except O.ErreurOutil as exc:
            lignes.append({"horodatage": _maintenant(), "demande_id": dem["id"], "action": "aucune",
                           "decision": "refusee", "justification": f"Plan inexploitable : {exc}", "formes_violees": [],
                           "triplets_ajoutes": 0, "triplets_retires": 0, "source": "regle", "plan": plan})
            continue
        for c in candidats:
            evaluer(g, c, valider)
        demande = candidats[0]
        valides = [c for c in candidats if not c.formes_violees]
        retenu = max(valides, key=lambda c: c.criteres) if valides else None
        if retenu is demande:
            decision, source = "acceptee", "llm"
        elif retenu is None or retenu.nom == "refus":
            decision, source = "refusee", "veto_symbolique" if demande.formes_violees else "regle"
        else:
            decision, source = "acceptee_avec_adaptation", "veto_symbolique" if demande.formes_violees else "regle"
        if retenu is not None and retenu.nom != "refus":  # commit
            for t in retenu.retraits:
                g.remove(t)
            for t in retenu.ajouts:
                g.add(t)
        faits = {"decision": decision, "action_demandee": demande.description,
                 "formes_violees_par_la_demande": demande.formes_violees,
                 "candidats": [{"nom": c.nom, "description": c.description, "formes_violees": c.formes_violees,
                                "couverture_detection": c.criteres[0][1], "equipements": -c.criteres[2][0]}
                               for c in candidats],
                 "retenu": retenu.description if retenu else "aucun", "contexte_reseau": _reseau(boite)}
        secours = (f"Décision : {decision}. Demande : {demande.description} ; formes violées : "
                   f"{', '.join(demande.formes_violees) or 'aucune'}. Retenu : {faits['retenu']}.")
        lignes.append({"horodatage": _maintenant(), "demande_id": dem["id"],
                       "action": retenu.description if retenu and retenu.nom != "refus" else f"aucune ({demande.description} refusée)",
                       "decision": decision, "justification": justifier(llm, dem, faits, secours),
                       "formes_violees": demande.formes_violees,
                       "triplets_ajoutes": len(retenu.ajouts) if retenu and retenu.nom != "refus" else 0,
                       "triplets_retires": len(retenu.retraits) if retenu and retenu.nom != "refus" else 0,
                       "source": source, "plan": plan, "candidats": faits["candidats"]})
    return lignes


def _traiter_evacuation(llm, g: Graph, dem: dict, plan: dict, valider: Validateur) -> list[dict]:
    decisions = diriger(g, plan, valider)
    faits_communs = {"t_s": plan["t_s"], "par_espace": [{**d["faits"], "decision": d["decision"],
                                                         "formes_violees_route_habituelle": d["formes"],
                                                         **({"adaptation": d["adaptation"]} if "adaptation" in d else {})}
                                                        for d in decisions]}
    texte = justifier(llm, dem, faits_communs, "")
    lignes = []
    for d in decisions:
        e, c = d["espace"], d["candidat"]
        if d["decision"] == "acceptee":
            action, source = c.description, "llm"
        elif d["decision"] == "acceptee_avec_adaptation":
            action, source = c.description, "veto_symbolique"
        else:
            action, source = d.get("adaptation", "aucune route"), "veto_symbolique" if d["formes"] else "regle"
        f = d["faits"]
        fait = (f"{f['espace']} à t = {f['t_s']} s (occupants : {f['occupants']}) : {f.get('route_habituelle', 'pas de route habituelle')}"
                f" ; formes violées : {', '.join(d['formes']) or 'aucune'}"
                + (f" ; {f['route_sure']}" if f.get("route_sure") else "") + ".")
        lignes.append({"horodatage": _maintenant(), "demande_id": dem["id"], "action": action, "decision": d["decision"],
                       "justification": (fait + " " + texte).strip(), "formes_violees": d["formes"],
                       "triplets_ajoutes": 0, "triplets_retires": 0, "source": source, "plan": plan,
                       "espace_globalId": e["gid"], "t_s": f["t_s"],
                       "route": d.get("route", {}).get("route") if d.get("route") else None})
    return lignes
