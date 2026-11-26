# Préparer l'oral de 5 à 7 minutes

Pour comprendre les méthodes avant la répétition : [parcours détaillé, exemples et questions](understand-the-project.fr.md).

Support : [PowerPoint en anglais](progress-2026-11-26.en.pptx) · [PDF](progress-2026-11-26.en.pdf) · [Texte anglais et notes orales](progress-2026-11-26.en.md).

Les huit premières diapositives constituent l'exposé, pour environ six minutes. Les deux suivantes servent à discuter du code après l'exposé ou pendant les questions. Les notes en anglais sont aussi intégrées au PowerPoint. Lis-les à voix haute et reformule les phrases qui ne te ressemblent pas.

Le nouveau plan présente **d'abord le fonctionnement, puis l'acquisition et les résultats**. Diapositive7 : cliquer sur l'image du modèle dans PowerPoint pour lancer la vidéo intégrée de trois secondes. Dans le PDF, l'image reste fixe et le lien « 3-second model clip » ouvre la vidéo publiée.

## Ce que tu dois savoir expliquer

1. **Le but et le plan.** Reconstruire une scène évoluant dans le temps pour choisir une nouvelle vue. Annoncer les deux parties : fonctionnement, puis acquisition et résultats.
2. **Préparer les images.** Extraire des images, aligner les instants, conserver la cohérence entre résolution et paramètres caméra. Cela met en pratique les notions d'échantillonnage et de coordonnées image.
3. **Retrouver les caméras.** COLMAP associe des détails du décor, estime les poses et triangule des points ; il affine ensuite la reconstruction. Les intrinsèques décrivent la projection, la pose décrit la position et l'orientation. Les caméras de la référence sont fournies ; celles de True Skate sont estimées.
4. **Apprendre la scène.** Des Gaussiennes possèdent des paramètres de position, taille, orientation, opacité et apparence. On rend une image, on la compare à l'image cible, puis on modifie les paramètres grâce aux gradients. Les projections, la visibilité et la rasterisation interviennent ici.
5. **Ajouter le temps et vérifier.** 4DGS apprend un réseau de déformation ; Dynamic ajuste des états successifs avec des contraintes locales. On vérifie les rendus depuis une vue réservée. Rendu temporel et suivi matériel validé sont deux affirmations différentes.
6. **Acquérir les données.** Cuisine : base téléchargée, caméras calibrées et vidéos synchronisées. True Skate : même replay rejoué depuis des points de vue successifs ; passage de caméras suivies à des vues fixes ; découpage et alignement approximatif par événement de score.
7. **Montrer la référence.** La vidéo intégrée montre un véritable rendu du modèle sur le petit extrait DyNeRF. La scène et le mouvement sont reconnaissables ; des erreurs de couleur et du flou persistent. Ce n'est pas la preuve d'une reconstruction complète ou d'un suivi physique exact.
8. **Montrer les limites des données personnelles.** Comparer la planche originale au rendu temporel dégradé. Des ajustements statiques séparés sont meilleurs. Le timing, les masques et les surfaces initialement cachées sont des pistes à vérifier ; les résultats ne prouvent pas que la seule qualité des données explique toutes les différences entre les expériences.

## Code 1 : passer de la 3D aux pixels

Ouvre [static_board_geometry.py](../scripts/static_board_geometry.py) et la fonction `project`. C'est le code présenté dans l'annexe, avec des espaces ajoutés pour le rendre lisible.

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

**Quelles notions du cours ont été utilisées ?** Transformations et géométrie projective, viewing/perspective, clipping/visibilité, échantillonnage et rasterisation. Les pages précises sont indiquées dans le support. Ne revendique pas une implémentation de Fourier, de ray tracing ou de SLERP dans ce projet.

## Répétition conseillée

Une première fois avec les notes, une deuxième en regardant seulement les images. Pour le code, explique chaque ligne sans lire un paragraphe appris par cœur. Si une question dépasse ce que tu maîtrises, distingue le rôle que tu comprends de la partie interne de la bibliothèque que tu dois encore étudier.
