# TBM - Transports Bordeaux Métropole pour Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

Cette intégration permet de récupérer les horaires en temps réel des trams, bus et BatCub du réseau TBM (Transports Bordeaux Métropole) dans Home Assistant.

## Fonctionnalités

- 🚃 Horaires en temps réel des trams (lignes A, B, C, D)
- 🚌 Horaires en temps réel des bus
- ⛴️ Horaires en temps réel des BatCub (navettes fluviales)
- 🔄 Mise à jour automatique toutes les 60 secondes
- 📱 Configuration via l'interface utilisateur
- 🇫🇷 Interface en français et anglais
- ✅ Utilise l'API officielle SIRI Lite de Bordeaux Métropole

## Installation

### Installation manuelle

1. Téléchargez ce dépôt
2. Copiez le dossier `custom_components/tbm` dans le dossier `custom_components` de votre installation Home Assistant
3. Redémarrez Home Assistant

### Installation via HACS (recommandé)

1. Ouvrez HACS dans Home Assistant
2. Cliquez sur "Intégrations"
3. Cliquez sur les 3 points en haut à droite → "Dépôts personnalisés"
4. Ajoutez l'URL de ce dépôt avec la catégorie "Intégration"
5. Recherchez "TBM" et installez l'intégration
6. Redémarrez Home Assistant

## Configuration

1. Allez dans **Paramètres** → **Appareils et services** → **Ajouter une intégration**
2. Recherchez "TBM"
3. Entrez le nom de l'arrêt à rechercher (ex: "Berges du Lac", "Quinconces", "Victoire")
4. Sélectionnez l'arrêt souhaité dans la liste des résultats

### Exemples d'arrêts

- **Berges du Lac** (Tram C)
- **Quinconces** (Trams B, C)
- **Victoire** (Trams A, B)
- **Pey Berland** (Tram A)
- **Gare Saint-Jean** (Trams A, C)
- **Place de la Bourse**

## Capteurs créés

### Capteur principal : Prochain départ

Affiche le temps d'attente avant le prochain départ (toutes lignes confondues).

**État** : Temps d'attente (ex: "3 min", "Imminent", "Aucun")

**Attributs** :

- `stop_name` : Nom de l'arrêt
- `line` : Numéro/lettre de la ligne
- `destination` : Direction/terminus
- `waiting_time` : Temps d'attente en minutes
- `realtime` : Données en temps réel (true/false)
- `aimed_time` : Heure de passage théorique
- `expected_time` : Heure de passage estimée (temps réel)
- `next_departures` : Liste des 5 prochains départs

### Capteurs par ligne/direction

Un capteur est créé pour chaque ligne/direction desservant l'arrêt, affichant le prochain départ pour cette ligne spécifique.

## Exemple d'utilisation dans une carte Lovelace

```yaml
type: entities
title: 🚃 Horaires TBM - Berges du Lac
entities:
  - entity: sensor.tbm_berges_du_lac_prochain_depart
    name: Prochain passage
  - entity: sensor.tbm_berges_du_lac_ligne_c_blanquefort
    name: Ligne C → Blanquefort
  - entity: sensor.tbm_berges_du_lac_ligne_c_gare_de_blanquefort
    name: Ligne C → Gare de Blanquefort
```

### Carte avec les prochains départs

```yaml
type: markdown
title: 🚃 Prochains trams - Berges du Lac
content: |
  {% set sensor = states.sensor.tbm_berges_du_lac_prochain_depart %}
  {% if sensor.attributes.next_departures %}
  | Ligne | Direction | Temps |
  |-------|-----------|-------|
  {% for dep in sensor.attributes.next_departures[:5] %}
  | {{ dep.line }} | {{ dep.destination }} | {{ dep.waiting_time }} min |
  {% endfor %}
  {% else %}
  Aucun départ prévu
  {% endif %}
```

## Automatisations

### Notification avant de partir

```yaml
automation:
  - alias: "Notification tram proche"
    trigger:
      - platform: numeric_state
        entity_id: sensor.tbm_berges_du_lac_prochain_depart
        attribute: waiting_time
        below: 5
    condition:
      - condition: time
        after: "07:00:00"
        before: "09:00:00"
        weekday:
          - mon
          - tue
          - wed
          - thu
          - fri
    action:
      - service: notify.mobile_app
        data:
          title: "🚃 Tram proche !"
          message: >
            Le tram {{ state_attr('sensor.tbm_berges_du_lac_prochain_depart', 'line') }} 
            arrive dans {{ state_attr('sensor.tbm_berges_du_lac_prochain_depart', 'waiting_time') }} minutes
            direction {{ state_attr('sensor.tbm_berges_du_lac_prochain_depart', 'destination') }}
```

## API utilisée

Cette intégration utilise l'API officielle **SIRI Lite** de Bordeaux Métropole, fournie par Mecatran.

- **Documentation** : [transport.data.gouv.fr](https://transport.data.gouv.fr/datasets/67f5bad303325228295b7dff)
- **Données** : Temps réel (GTFS-RT / SIRI Lite)
- **Fournisseur** : Bordeaux Métropole

## Contribuer

Les contributions sont les bienvenues ! N'hésitez pas à ouvrir une issue ou une pull request.

## Licence

Ce projet est sous licence MIT.
