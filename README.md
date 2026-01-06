# 🏥 TriageIA — Plateforme intelligente de Triage Médical par IA avec Chatbot

## 📌 Contexte
Le triage médical est une étape clé dans les services d’urgences. Il permet de prioriser la prise en charge des patients selon la gravité de leur état. Cependant, le triage manuel peut être long, subjectif et sujet à erreurs, notamment en situation d’affluence.

Ce projet propose une **plateforme web de triage médical assisté par IA**, intégrant un **chatbot interactif** permettant de guider la saisie des informations cliniques et de déclencher une **prédiction automatique** du niveau d’urgence.

---

## ❓ Problématique
Le triage manuel peut être **chronophage**, **non standardisé** et dépend fortement de l’expérience de l’agent. Une mauvaise classification peut soit **retarder la prise en charge d’un patient critique**, soit **surcharger le service** en priorisant un cas non urgent.

**Question centrale :**  
> Comment mettre en place un système intelligent capable d’assister efficacement le triage médical afin de réduire l’engorgement des urgences et d’améliorer la priorisation des patients ?

---

## 🎯 Objectifs du projet
- Collecter les informations du patient de manière **structurée** via un chatbot.
- Prédire automatiquement la catégorie de triage parmi :
  - **Emergent**
  - **Urgent**
  - **Semi-urgent**
- Intégrer le modèle IA via une **API REST** (requête JSON → réponse JSON).
- Enregistrer les données et les résultats en base de données pour assurer :
  - **traçabilité**
  - **historique**
  - **export PDF/CSV**
- Réduire l’engorgement et améliorer la priorisation, dans une logique **d’aide à la décision**.

---

## 👥 Équipe
**Réalisé par :**
- BEN-LAGHFIRI Majeda  
- ZHIRI Rania  
- HASSAOUI Aya  
- JARDI Siham  

**Encadré par :**
- Mme. STITINI Oumaima  
- Mr. NAIT MALEK Yousef  

**Master :** MDSIE–TEE (ENS Marrakech, Université Cadi Ayyad) 

**Module :** Intelligence artificielle avancée

**Année universitaire :** 2025–2026  

---

## 🧠 Approche IA (Modélisation)
Le problème est formulé comme une **classification supervisée multi-classes**.

### ✅ Modèles testés
Trois algorithmes ont été entraînés et comparés :
- **SVM (SVC)**
- **Random Forest**
- **XGBoost**

### 📊 Résultats (Test)
| Modèle | Accuracy | F1-macro |
|-------|----------|----------|
| XGBoost | 0.73 | 0.73 |
| SVM (SVC) | 0.71 | 0.72 |
| ✅ Random Forest | **0.74** | **0.74** |

➡️ **Random Forest** a été retenu comme modèle final pour sa robustesse et sa stabilité.

---

## 🧼 Prétraitement des données
Le dataset contient **1629 enregistrements** et environ **50 variables** (démographie, signes vitaux, antécédents).

Le pipeline inclut :
- Nettoyage et suppression des colonnes non pertinentes / fuite de données
- Gestion des valeurs manquantes :
  - Numériques : **médiane**
  - Catégorielles : **mode**
- Encodage des variables catégorielles : **One-Hot Encoding**
- Standardisation des variables numériques
- Split : **80% entraînement / 20% test** (stratifié)

---

## 🧩 Architecture du système
La plateforme suit une architecture **client–serveur** :

- **Frontend Web** : interface + chatbot (assistant médical)
- **Backend API REST** : prétraitement + modèle IA + logique applicative
- **Base de données** : persistance des patients + analyses + horodatage
- **Exports** : historique exportable (PDF / CSV)

📌 Endpoint principal :
- `POST /api/triage/predict`

Entrée : JSON (données patient)  
Sortie : JSON (classe prédite + scores éventuels)

<img width="623" height="375" alt="image" src="https://github.com/user-attachments/assets/9a3d78b3-8849-4243-aafa-8d217495dfe3" />

---

## 🤖 Chatbot (Interface conversationnelle)
Le chatbot guide l’assistante médicale pas à pas :
- Pose les questions nécessaires (âge, sexe, signes vitaux, antécédents…)
- Valide les champs en temps réel (types, plages physiologiques, champs requis)
- Déclenche automatiquement la prédiction via l’API
- Affiche clairement le résultat : **Emergent / Urgent / Semi-urgent**
- Enregistre la prédiction + données en base pour l’historique

---

## 🗃️ Traçabilité & Historique
Chaque analyse est enregistrée avec :
- Identifiant patient
- Données saisies
- Date et heure (horodatage)
- Classe prédite
- Export possible en **PDF** ou **CSV**

---

## 🖥️ Interfaces de la plateforme (Screens)
La plateforme TriageIA propose plusieurs pages principales :

1. **Page d’accueil**  
   - Présentation générale de l’application et accès rapide aux modules.
   <img width="1238" height="698" alt="image" src="https://github.com/user-attachments/assets/1482a927-085f-4f20-93d8-7604794fcd30" />


2. **Gestion des patients**  
   - Liste des patients, recherche, accès au dossier.
   <img width="1341" height="744" alt="image" src="https://github.com/user-attachments/assets/2f98a7b3-dac3-418e-b537-2c1a151a354a" />


3. **Ajout d’un patient**  
   - Formulaire d’ajout avec champs structurés.
   <img width="1203" height="654" alt="image" src="https://github.com/user-attachments/assets/a1645c81-9e59-4870-bda5-a34502b6c1b9" />


4. **Interface du chatbot de triage**  
   - Dialogue guidé + validation des champs + prédiction affichée.
   <img width="1388" height="741" alt="image" src="https://github.com/user-attachments/assets/8a940fce-3820-44f6-babe-1324ae7e7b38" />


5. **Historique des analyses**  
   - Tableau d’historique + export **PDF/CSV**.
   <img width="1419" height="761" alt="image" src="https://github.com/user-attachments/assets/73cd7fd0-4fbb-4e7c-b52b-ac70d9a93024" />

   




---

## 🔐 Sécurité (Bonnes pratiques)
Mesures intégrées :
- Validation des champs (format, valeurs manquantes, cohérence)
- Minimisation des données transmises (seulement les variables utiles)

Perspectives recommandées :
- Authentification + gestion des rôles (assistante / médecin / admin)
- HTTPS/TLS
- Chiffrement des données au repos
- Journalisation (logs) + audit

---


