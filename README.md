# CAN2SAV — Déploiement admin privé

Ce projet est un site statique GitHub Pages pour afficher le tournoi, plus un backend Python pour protéger les modifications.

## Objectif

- `index.html`, `style.css`, `script.js` sont hébergés sur GitHub Pages.
- `server.py` est hébergé ailleurs (Render, Railway, PythonAnywhere, VPS...).
- Seul un admin connecté peut sauvegarder les modifications.

## Étape 1 — Tester en local

1. Installer Python et créer un environnement virtuel :

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Lancer le serveur local :

```bash
python3 server.py
```

3. Ouvrir `index.html` avec un serveur local ou `Live Server`.

4. Dans `script.js`, laisser `REMOTE_API_BASE = ''` pour utiliser le serveur local.

## Étape 2 — Déployer le serveur Python

### Option simple : Render / Railway

1. Crée un nouveau service Web Python.
2. Pousse ces fichiers : `server.py`, `requirements.txt`, `data.json`, `style.css`, `script.js`, `index.html`.
3. Configure une variable d'environnement :

- `ADMIN_PASSWORD` → ton mot de passe admin
- Optionnel : `MYSQL_HOST`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`

4. Le service doit exposer `server.py` sur le port fourni par le service.

> Si le service ne supporte pas le port custom, ajuste `server.py` pour utiliser la variable d'environnement `PORT`.

### Option simple : PythonAnywhere

1. Crée un compte PythonAnywhere.
2. Déplace `server.py` et `requirements.txt` dans un répertoire PythonAnywhere.
3. Installe `mysql-connector-python` si besoin.
4. Lance `server.py` via `bash` ou en tant qu'application Web.

## Étape 3 — Configurer le front-end GitHub Pages

1. Sur GitHub Pages, laisse `index.html`, `style.css`, `script.js` publics.
2. Ouvre `script.js`.
3. Remplace la ligne :

```js
const REMOTE_API_BASE = '';
```

par :

```js
const REMOTE_API_BASE = 'https://MON_SERVEUR_DEPRODIGNE';
```

4. Publie le site sur GitHub Pages.

## Étape 4 — Utilisation

- Ouvre ta page GitHub Pages.
- Clique sur `Admin`.
- Entre le mot de passe.
- Tu pourras maintenant ajouter, modifier et sauvegarder.

## Remarques importantes

- GitHub Pages ne peut pas exécuter `server.py`.
- Le backend doit être déployé sur un service distinct.
- Les données sont sauvegardées sur le serveur via `/api/save`.
- Les utilisateurs normaux peuvent toujours voir le site, mais ne peuvent pas sauvegarder sans admin.

## Si tu veux que je t'aide à héberger

Je peux te guider sur :
- Render ou Railway pour déployer `server.py`.
- configurer `ADMIN_PASSWORD`.
- ajuster le front-end pour l’URL publique.
