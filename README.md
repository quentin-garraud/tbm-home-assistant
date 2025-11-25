# TBM - Transports Bordeaux Métropole pour Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

Cette intégration permet de récupérer les horaires en temps réel des trams, bus et bateaux du réseau TBM (Transports Bordeaux Métropole) dans Home Assistant.

## Fonctionnalités

- 🚃 Horaires en temps réel des trams
- 🚌 Horaires en temps réel des bus
- ⛴️ Horaires en temps réel des BatCub (bateaux)
- 🔄 Mise à jour automatique toutes les 60 secondes
- 📱 Configuration via l'interface utilisateur
- 🇫🇷 Interface en français et anglais

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
3. Entrez l'identifiant de l'arrêt ou son nom
4. Sélectionnez une ligne spécifique ou "Toutes les lignes"

### Trouver l'identifiant d'un arrêt

L'identifiant d'un arrêt suit le format : `stop_area:TBM:SA:XXXX`

Exemples d'arrêts populaires :

- **Quinconces** : `stop_area:TBM:SA:QUIN`
- **Victoire** : `stop_area:TBM:SA:VICT`
- **Pey Berland** : `stop_area:TBM:SA:PEYB`
- **Hôtel de Ville** : `stop_area:TBM:SA:HDVI`
- **Gare Saint-Jean** : `stop_area:TBM:SA:SAJE`

Vous pouvez aussi simplement entrer le nom de l'arrêt (ex: "Quinconces") et l'intégration le recherchera automatiquement.

## Capteurs créés

### Capteur principal : Prochain départ

Affiche le temps d'attente avant le prochain départ (toutes lignes confondues).

**État** : Temps d'attente (ex: "3 min", "Imminent", "Aucun")

**Attributs** :

- `stop_name` : Nom de l'arrêt
- `line` : Numéro de la ligne
- `destination` : Direction/terminus
- `departure_time` : Heure de départ prévue
- `waiting_time` : Temps d'attente en minutes
- `vehicle_type` : Type de véhicule (tram, bus, bateau)
- `realtime` : Données en temps réel (true/false)
- `next_departures` : Liste des 5 prochains départs

### Capteurs par ligne

Un capteur est créé pour chaque ligne/direction desservant l'arrêt, affichant le prochain départ pour cette ligne spécifique.

## Exemple d'utilisation dans une carte Lovelace

```yaml
type: entities
title: Horaires TBM - Quinconces
entities:
  - entity: sensor.tbm_quinconces_prochain_depart
    name: Prochain passage
  - entity: sensor.tbm_quinconces_ligne_a_floirac_dravemont
    name: Ligne A → Floirac
  - entity: sensor.tbm_quinconces_ligne_b_pessac_centre
    name: Ligne B → Pessac
```

### Carte plus avancée avec les attributs

```yaml
type: markdown
title: 🚃 Prochains trams
content: |
  {% set sensor = states.sensor.tbm_quinconces_prochain_depart %}
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
        entity_id: sensor.tbm_quinconces_prochain_depart
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
            Le tram {{ state_attr('sensor.tbm_quinconces_prochain_depart', 'line') }} 
            arrive dans {{ state_attr('sensor.tbm_quinconces_prochain_depart', 'waiting_time') }} minutes
```

## API utilisée

Cette intégration utilise l'API publique de TBM disponible sur `ws.infotbm.com`. Les données sont fournies par Bordeaux Métropole.

## Contribuer

Les contributions sont les bienvenues ! N'hésitez pas à ouvrir une issue ou une pull request.

## Licence

Ce projet est sous licence MIT.
