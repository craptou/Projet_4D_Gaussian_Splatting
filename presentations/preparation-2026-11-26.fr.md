# Préparer l'oral d'environ dix minutes

Pour comprendre les méthodes avant la répétition : [parcours détaillé, exemples et questions](understand-the-project.fr.md).

Support : [PowerPoint en anglais](progress-2026-11-26.en.pptx) · [PDF des diapositives](progress-2026-11-26.en.pdf) · [Script oral clair en PDF](progress-2026-11-26.script.en.pdf) · [Texte anglais et liens de fonctions](progress-2026-11-26.en.md).

Les douze diapositives constituent un exposé d'environ dix minutes. Il n'y a plus d'annexe de code : chaque concept renvoie aux fonctions qui le mettent en œuvre. Les noms des fonctions sont cliquables et ouvrent le code à la ligne correspondante. Les notes anglaises sont intégrées au PowerPoint et au PDF du script, avec une page par diapositive. Lis à voix haute la rubrique « What to say » ; la rubrique « Functions to open » sert à la discussion du code et n'est pas à réciter.

Le plan présente **d'abord le fonctionnement, puis l'acquisition et les résultats**. Diapositive10 : cliquer sur l'image du modèle dans PowerPoint pour lancer la vidéo intégrée de trois secondes. Dans le PDF, l'image reste fixe. La vidéo est aussi accessible dans les sources du script Markdown.

## Ce que tu dois savoir expliquer

1. **Le but et le plan.** Reconstruire une scène évoluant dans le temps pour choisir une nouvelle vue. Annoncer les deux parties : fonctionnement, puis acquisition et résultats.
2. **Préparer les images.** Extraire des images, aligner les instants, conserver la cohérence entre résolution et paramètres caméra. Cela met en pratique les notions d'échantillonnage et de coordonnées image.
3. **Retrouver les caméras.** COLMAP associe des détails du décor, estime les poses et triangule des points ; il affine ensuite la reconstruction. Les intrinsèques décrivent la projection, la pose décrit la position et l'orientation. Les caméras de la référence sont fournies ; celles de True Skate sont estimées.
4. **Projeter et vérifier la visibilité.** La fonction `project()` transforme un point du monde en pixel. `require_board_visibility()` vérifie les profondeurs des graines initiales. Une bonne projection ne suffit pas si le moteur supprime le point au clipping.
5. **Représenter la scène.** Une Gaussienne est un ellipsoïde 3D à influence progressive, plus forte près de son centre. Sa projection produit une contribution en forme d'ellipse douce. Position, taille, orientation, opacité et apparence sont des paramètres. `create_from_pcd()` initialise la représentation ; `densify_and_split()` peut ajouter du détail pendant l'optimisation.
6. **Rendre puis apprendre.** `render()` produit les pixels depuis une caméra. L'apprentissage compare ce rendu à une image cible, calcule des gradients et modifie les paramètres. `scene_reconstruction()` gère cette boucle. Rendre une image et améliorer le modèle sont deux opérations distinctes.
7. **Ajouter le temps.** 4DGS prédit des déformations avec `forward_dynamic()` ; l'adaptateur `dynamic_replay_engine.train()` ajuste des états successifs via les fonctions des auteurs. Les caméras restent des entrées pour les deux méthodes.
8. **Valider.** `probe()` contrôle notamment les caméras et les projections ; `evaluate()` compare les rendus et les régions d'objet. View20 est une vue de validation réutilisée. Les dix instants du dernier essai sont supervisés : ce n'est pas un test d'interpolation temporelle.
9. **Acquérir les données.** Cuisine : base téléchargée, caméras calibrées et vidéos synchronisées. True Skate : même replay rejoué depuis des points de vue successifs ; passage de caméras suivies à des vues fixes ; découpage et alignement approximatif par événement de score.
10. **Montrer la référence.** La vidéo intégrée montre un véritable rendu du modèle sur le petit extrait DyNeRF. La scène et le mouvement sont reconnaissables ; du flou et des erreurs de couleur persistent.
11. **Montrer les limites des données personnelles.** Comparer la planche originale au rendu temporel dégradé. Des ajustements statiques séparés sont meilleurs. Les configurations et les scènes diffèrent aussi de la référence : on n'a pas isolé une cause unique.
12. **Expliquer les masques déjà testés.** Le premier contrôle pondéré améliore le PSNR des pixels d'entraînement sélectionnés,11,79→25,18dB, mais produit une tache sombre. Les essais récents utilisent également des masques multi-vues. `action_masks()` construit des candidats ; `foreground_l1()` donne du poids à leur erreur RGB. La suite consiste à améliorer et vérifier les masques existants, pas à prétendre qu'ils n'ont jamais été essayés.

## Code 1 : passer de la 3D aux pixels

Ouvre [static_board_geometry.py](../scripts/static_board_geometry.py) et la fonction `project`, référencée sur la diapositive4. L'explication détaillée ci-dessous sert à comprendre ce code, sans ajouter d'annexe au diaporama.

```python
camera = points @ pose[:, :3].T + pose[:, 3]
```

`points` contient des positions 3D. La rotation puis la translation de la caméra donnent ces positions dans le repère de la caméra. Le `@` représente une multiplication matricielle. Le `.T` tient à la convention utilisée pour ranger les points en lignes dans NumPy.

```python
pixels = camera[:, :2] / camera[:, 2, None]
```

On divise les coordonnées horizontale et verticale par la profondeur. À taille égale, un objet plus éloigné occupe moins de place dans l'image. On utilise cette formule sur des points de profondeur valide ; la visibilité est contrôlée séparément.

```python
return pixels * f + [cx, cy], camera[:, 2]
```

La focale `f` exprime le résultat en pixels ; `(cx, cy)` est le point principal de la caméra dans l'image. La fonction renvoie aussi la profondeur. Elle applique une caméra connue : elle n'estime pas elle-même sa pose.

Phrase simple en anglais : **“This function uses the camera pose to transform 3D points, applies perspective, and returns image coordinates.”**

## Code 2 : protéger la validation

Ouvre [fixed_dataset_adapter.py](../scripts/fixed_dataset_adapter.py), dans la partie qui charge `foreground_mask_path`.

Le masque indique quels pixels appartiennent probablement à l'objet mobile. Un masque d'entraînement peut aider à ajuster le modèle. Un masque de validation doit seulement servir à évaluer le résultat. Le code déclenche donc une erreur si un masque de validation est fourni comme information d'entraînement.

Phrase simple en anglais : **“This check prevents validation masks from guiding training.”**

View20 a déjà été regardée plusieurs fois pour prendre des décisions : c'est une vue de validation, pas un test final jamais consulté.

## Questions probables

**Pourquoi des caméras fixes ?** Elles simplifient le problème : on conserve une pose par vue au lieu d'en estimer une pour chaque image. Une caméra mobile n'est pas impossible à utiliser ; elle demande davantage d'estimation de poses.

**As-tu développé Gaussian Splatting toi-même ?** Non. Les algorithmes de recherche et COLMAP sont réutilisés et cités. Le projet réalise la préparation des données, l'adaptation des chargeurs, les contrôles et les expériences, avec une assistance IA pour le développement. Présente les éléments dont tu comprends réellement le rôle.

**Pourquoi ne pas entraîner plus longtemps ?** Les essais ont montré qu'améliorer le décor ou le score global ne garantit pas une meilleure planche. Il faut identifier les erreurs de données, de géométrie ou de mouvement avant de prolonger le calcul.

**Peux-tu déjà mesurer les rotations du skateboard ?** Pas de façon validée. Une Gaussienne qui possède une rotation n'est pas automatiquement un point matériel correctement suivi. Il faut d'abord valider la reconstruction et le suivi.

**Quelles notions du cours ont été utilisées ?** Transformations et géométrie projective, viewing/perspective, clipping/visibilité, échantillonnage et rasterisation. Ces notions sont reliées aux étapes du projet dans le support. Ne revendique pas une implémentation de Fourier, de ray tracing ou de SLERP dans ce projet.

## Répétition conseillée

Une première fois avec les notes, une deuxième en regardant seulement les images. Pour le code, explique chaque ligne sans lire un paragraphe appris par cœur. Si une question dépasse ce que tu maîtrises, distingue le rôle que tu comprends de la partie interne de la bibliothèque que tu dois encore étudier.
