# weekly-pulse

Deux routines Claude Code hebdomadaires pour celles et ceux qui maintiennent plus de dépôts qu'ils n'ont le temps d'en surveiller.

🇬🇧 [Read in English](README.md)

| Routine | Chaque semaine, pour chaque dépôt listé | Résultat |
|---|---|---|
| 🔐 **security-pulse** | Dépendances vulnérables, secrets dans l'arborescence, workflows GitHub Actions risqués, réglages faibles, et lecture du diff de la semaine | Une issue dans ce dépôt, mise à jour si la routine repasse |
| 📚 **docs-pulse** | Les changements mergés ou poussés, des entrées de changelog écrites pour l'utilisateur, la doc qui ne correspond plus au code | Une pull request dans ce dépôt, à relire et merger |

Sur les projets annexes, les alertes de sécurité s'accumulent sans tri et les README décrivent des options supprimées depuis des mois. Avec weekly-pulse, le propriétaire lit une issue et une PR par dépôt chaque semaine, et il tranche.

Rien n'est mergé, supprimé ni poussé sur une branche par défaut. Claude propose, vous décidez.

## Comment ça marche

```
pulse.config.yml ──► scripts/pulse_*.py ──► faits (JSON) ──► skill : tri et rédaction ──► scripts/verify_report.py ──► issue / PR
                     testés, déterministes                   le jugement de l'agent          contrôle bloquant
```

Les scripts font tout ce dont on peut écrire le résultat attendu à l'avance : appels à l'API REST de GitHub, detect-secrets, zizmor, pip-audit et npm audit, liste des PR mergées et des commits directs. Chaque vérification rend un statut, si bien qu'un outil qui n'a pas tourné apparaît comme un trou de couverture et jamais comme un résultat propre.

L'agent fait le reste. Il distingue une donnée de test d'une clé valide, regroupe des dizaines d'alertes npm transitives sous les quelques dépendances directes qui les tirent, vérifie si un paquet vulnérable est réellement atteint, lit le diff de la semaine à la recherche d'un contrôle d'accès oublié, rédige le changelog pour un lecteur et repère le README qui documente encore une option retirée.

Chaque corps de message passe par `verify_report.py` avant publication. Le script refuse tout texte sans le marqueur de la semaine (c'est lui qui permet de mettre à jour au lieu de dupliquer) et tout texte qui ressemble à la valeur d'un secret.

## Outils existants et place du projet

GitHub propose déjà Dependabot, le secret scanning et CodeQL. Sur un dépôt public, activez-les : ils couvrent l'essentiel de la détection. Sur les dépôts privés d'un compte personnel, le secret scanning et le code scanning ne sont pas disponibles, et une session cloud ne peut de toute façon pas lire ces API d'alertes. weekly-pulse lit ce que GitHub fournit, comble les manques avec des outils locaux et ajoute le tri hebdomadaire par-dessus.

Pour le changelog, [release-please](https://github.com/googleapis/release-please), [changesets](https://github.com/changesets/changesets) et [git-cliff](https://git-cliff.org) font le travail de façon déterministe. Si un dépôt en utilise un, docs-pulse laisse son changelog tranquille et ne corrige que la doc. Des agents de mise à jour de la doc existent aussi, par exemple dans [githubnext/agentics](https://github.com/githubnext/agentics).

Je n'ai pas trouvé les deux tâches réunies sous forme de skills pour routines planifiées, avec une couche de collecte testée et un contrôle qui bloque une fuite avant publication.

## Organisation du dépôt

```
CLAUDE.md                 règles appliquées par l'agent à chaque passage
DECISIONS.md              décisions de conception datées, et ce qui ferait rouvrir chacune
pulse.config.yml          dépôts à surveiller et quelques options
scripts/                  collecteurs, vérificateur de rapport, installation
tests/                    tests unitaires des scripts
.claude/skills/           security-pulse et docs-pulse, chacun avec son modèle de rapport
routines/                 réglages et prompt de chaque routine
docs/setup.fr.md          guide d'installation (aussi en anglais)
```

Les skills et les scripts sont en anglais pour rester réutilisables ; la langue des rapports se règle dans `pulse.config.yml` (`language: fr`).

## Démarrer

Forkez, listez vos dépôts dans `pulse.config.yml`, créez deux routines à partir de `routines/`. Le [guide d'installation](docs/setup.fr.md) détaille les points qui comptent : rattacher chaque dépôt surveillé à la routine, passer par `gh api` puisque GraphQL est bloqué en session cloud, installer les outils depuis PyPI.

## État du projet

v0.1, octobre 2026. Les deux collecteurs ont tourné sur un vrai dépôt ; collecteurs et vérificateur sont couverts par des tests unitaires. Les routines n'ont pas encore tourné de bout en bout sur planning ; les premiers passages seront consignés dans `DECISIONS.md`.

## Licence

[MIT](LICENSE)
