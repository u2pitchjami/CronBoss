# 📘 TUTORIEL : Utilisation de cronboss (Python + YAML)

## 🎯 Objectif

Automatiser facilement des scripts Python ou Bash à des horaires précis avec gestion des logs et nettoyage automatique.

---

## 🧱 Structure d’un fichier `cronboss.yaml`

Chaque tâche est une entrée dans une liste YAML :

```yaml
- type: python  # ou "bash"
  script: chemin/vers/le_script.py
  args: "--option valeur"  # (facultatif)
  hours: [6, 14, 22]  # ou "any"
  minutes: [0, 30]    # ou "any"
  days: any           # ou [0, 1, 2] → jours de semaine
  enabled: true       # ou false pour désactiver temporairement

  cleanup:            # (optionnel)
    paths:
      - /chemin/vers/les/logs
    rule:
      keep_days: 14
      extensions: ["all"]  # ou [".log", ".sql.gz"]
      recursive: true
```

---

## 🕒 Planification simplifiée

* `hours`, `minutes`, `days` peuvent être :

  * un tableau `[8, 12, 20]`
  * la valeur `any` → s’exécute à toute heure ou tout jour

### 🧪 Exemples :

* `"hours": [6, 12]` et `"minutes": [0, 30]` → script lancé à 6h00, 6h30, 12h00, 12h30
* `"days": [0, 6]` → uniquement lundi et dimanche

---

## 🔁 Nettoyage automatique (`cleanup`)

Chaque tâche peut inclure un bloc `cleanup` pour supprimer les fichiers anciens.

### 🧼 Exemples :

```yaml
cleanup:
  paths:
    - /home/user/data/logs
  rule:
    keep_days: 7
    extensions: [".log"]  # ou ["all"] pour tout supprimer
    recursive: true
```

### 💡 Astuce :

`extensions: ["all"]` → supprime tous les fichiers sans filtrage sur l’extension.

---

## 🐍 Détection d’environnement Python

Si aucun `interpreter` n’est précisé dans la tâche, cronboss :

1. Cherche le nom du projet via le chemin du script
2. Le compare avec une **carte des interpréteurs** (`venvs.yaml`)
3. Et sinon, utilise une valeur par défaut définie dans `.env`

### Exemple de `venvs.yaml`

```yaml
brain_ops_activity: /home/pipo/envs/bo_activity/bin/python3
mixonaut_beets: /home/pipo/envs/vmix/bin/python3
mixonaut_essentia: /home/pipo/envs/vmix/bin/python3
```

### Extrait de `.env`

```env
# Interpréteur fallback si aucun projet trouvé
ENV_PYTHON=/home/pipo/envs/vrun
```

---

## ⏳ Tolérance temporelle avec CRON\_INTERVAL\_MINUTES

Pour permettre le rattrapage des tâches entre deux exécutions du script principal (géré via `crontab`), une variable spéciale est utilisée :

```env
CRON_INTERVAL_MINUTES=10
```

### 🔎 Fonctionnement :

* Si `cronboss.py` est appelé toutes les **15 minutes** via `crontab`, il vérifie **quelles tâches auraient dû s’exécuter dans les 10 dernières minutes**.
* Cela évite de **rater des exécutions** à cause d’un décalage de minute.

### ⚠️ Important :

Si cette variable n’est **pas** définie, cronboss considère un intervalle de 0 minute → toutes les tâches doivent alors matcher **exactement l’heure ET la minute**, ce qui est très contraignant.

### ✅ Recommandation :

Toujours définir `CRON_INTERVAL_MINUTES` dans `.env`, idéalement entre `5` et `15` selon la fréquence d’appel du script principal.

---

## 🚀 Fonctionnement général (`main()`)

1. Lit tous les fichiers `*.yaml` dans `tasks/`
2. Évalue chaque tâche avec `should_run()` en tenant compte de l’intervalle de tolérance
3. Exécute le script avec l’interpréteur associé
4. Applique la règle de nettoyage si définie

---

## ✅ Bonnes pratiques

* Toujours mettre `enabled: false` pour désactiver une tâche proprement
* Utiliser `extensions: ["all"]` pour gérer les fichiers tournés (`log.2024-06-04`, etc.)
* Centraliser les interpréteurs Python dans `venvs.yaml`
* Définir un fallback dans `.env` via `ENV_PYTHON`
* Logger chaque exécution (déjà fait dans `main()`)
* Faire tourner `main()` chaque minute ou 5-15 min via `crontab`

---

## 🧠 Exemple complet de tâche cronboss

```yaml
- type: python
  script: dev/brain_ops/activity/machines/activity_tracker.py
  hours: any
  minutes: any
  days: any
  enabled: true
  cleanup:
    paths:
      - /home/pipo/data/logs/brainops/activity/
    rule:
      keep_days: 14
      extensions: ["all"]
      recursive: true
```
