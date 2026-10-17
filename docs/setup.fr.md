# Installation

🇬🇧 [English version](setup.md)

Une dizaine de minutes, du fork au premier passage.

## Avant de commencer

- [Claude Code sur le web](https://code.claude.com/docs/en/claude-code-on-the-web) avec les [routines](https://code.claude.com/docs/en/routines) (en préversion au moment où ces lignes sont écrites).
- GitHub connecté à Claude, avec accès à chaque dépôt à surveiller. Pour un dépôt privé, il faut que l'application GitHub de Claude y soit installée, ou que votre jeton `gh` ait été transmis avec `/web-setup`.

## 1. Forker et configurer

Forkez ce dépôt (ou **Use this template**), puis modifiez [`pulse.config.yml`](../pulse.config.yml) :

```yaml
language: fr        # ou en
repos:
  - vous/api
  - vous/web-app
```

Vérifiez que les scripts fonctionnent avec votre compte avant de planifier quoi que ce soit :

```bash
bash scripts/setup.sh
python3 -m unittest discover tests
python3 scripts/pulse_security.py vous/api | head -40
```

## 2. Créer les deux routines

Pour chaque fichier de [`routines/`](../routines/), créez une routine avec les réglages et le prompt qu'il indique. Trois points comptent :

1. **Rattachez weekly-pulse en premier, puis chaque dépôt surveillé.** Une session ne peut appeler l'API GitHub que pour les dépôts qui lui sont rattachés ; les autres répondent 403. Le fichier de config ne suffit pas.
2. **Collez [`scripts/setup.sh`](../scripts/setup.sh) comme script de setup de l'environnement** pour la routine sécurité : les outils s'installent une fois, puis restent en cache.
3. **Gardez le réseau par défaut.** PyPI, npm et l'API GitHub font partie de sa liste autorisée, et rien d'autre n'est nécessaire.

Puis **lancez chaque routine une fois à la main** et relisez la session.

## 3. Un bon premier passage

- [ ] Chaque dépôt surveillé a une issue `🔐 Security pulse — <semaine>`.
- [ ] Chaque dépôt modifié dans la semaine a une PR `📚 Docs pulse — <semaine>` sur une branche `claude/weekly-pulse-docs-<semaine>`, ou le résumé indique « quiet week » ou « docs in sync ».
- [ ] Relancer une routine la même semaine met à jour l'issue ou la PR au lieu d'en créer une autre.
- [ ] La section « Not checked » de l'issue explique chaque vérification manquante.

## Dépannage

| Ce que vous voyez | Pourquoi, et quoi faire |
|---|---|
| `not reachable` / 403 « access … not enabled for this session » | Le dépôt n'est pas rattaché à la routine. Rattachez-le. |
| `gh pr create` ou `gh issue create` échoue | GraphQL est bloqué depuis les sessions cloud. Les skills passent par `gh api` (REST) ; n'y revenez pas. |
| Secret scanning / code scanning dans « Not checked » | Ces API ne sont pas joignables depuis une session, et GitHub ne les propose pas sur les dépôts privés d'un compte personnel. `detect-secrets` couvre l'arborescence à la place. |
| `detect-secrets: not installed` | Le script de setup n'a pas tourné. Vérifiez les réglages de l'environnement. |
| Deux issues pour la même semaine | Le commentaire marqueur (première ligne du corps) a été supprimé. Restaurez-le sur l'une et fermez l'autre. |
| La routine ne semble pas charger les skills | Vérifiez que weekly-pulse est le **premier** dépôt rattaché ; le prompt demande aussi à l'agent de s'y placer avec `cd`. |

## Ajouter un pulse

1. Un collecteur dans `scripts/` pour tout ce dont on connaît le résultat attendu, avec ses tests.
2. Un skill dans `.claude/skills/<nom>-pulse/SKILL.md` pour la part de jugement : entrées, procédure, rapport avec le marqueur de la semaine, interdits.
3. Ses options sous une nouvelle clé de `pulse.config.yml`, un prompt dans `routines/` et une entrée dans `DECISIONS.md`.
