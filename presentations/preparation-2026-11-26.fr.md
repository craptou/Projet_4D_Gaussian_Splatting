# Préparer l'oral de 5 à 7 minutes

Pour comprendre les méthodes avant la répétition : [parcours détaillé, exemples et questions](understand-the-project.fr.md).

Support : [PowerPoint en anglais](progress-2026-11-26.en.pptx) · [PDF](progress-2026-11-26.en.pdf) · [Texte anglais et notes orales](progress-2026-11-26.en.md).

Les huit premières diapositives constituent l'exposé, pour environ six minutes. Les deux suivantes servent à discuter du code après l'exposé ou pendant les questions. Les notes en anglais sont aussi intégrées au PowerPoint. Lis-les à voix haute et reformule les phrases qui ne te ressemblent pas.

## Ce que tu dois savoir expliquer

1. **Le but.** Plusieurs enregistrements d'un même replay doivent permettre de reconstruire une scène 3D qui évolue dans le temps. « 4D » signifie ici trois dimensions spatiales et le temps. L'objectif final n'est pas encore entièrement atteint.
2. **Les données.** Il s'agit d'un replay rejoué depuis plusieurs points de vue, pas de caméras physiques filmant simultanément. L'alignement par événement de score est approximatif. Le dernier comparatif emploie onze caméras d'entraînement et dix instants ; view20 est réservée à la validation.
3. **Les notions du cours.** Les matrices changent de repère ; la perspective transforme la 3D en pixels ; le clipping retire ce qui est hors du volume visible ; l'échantillonnage choisit des images à des instants donnés. Le moteur de splatting projette puis combine les contributions des Gaussiennes. Tu n'as pas réimplémenté tous ces algorithmes depuis zéro.
4. **Le problème de clipping.** Des points de la planche se trouvaient trop près des caméras dans nos unités normalisées pour le seuil CUDA. Multiplier les points et les translations des caméras par le même facteur conserve la projection en pixels et change les profondeurs par rapport à ce seuil. Cela a réparé un problème statique, pas tout le mouvement.
5. **Les résultats.** La référence DyNeRF fonctionne sur un petit extrait. Trois reconstructions statiques de la planche sont reconnaissables. Trois modèles statiques affichés en séquence ne constituent pas un suivi temporel appris.
6. **Le comparatif temporel.** Les deux méthodes ont les mêmes images et graines initiales, mais des pertes et procédures d'entraînement différentes. Les dix instants sont supervisés : ce test ne démontre pas une interpolation vers des instants non appris. La qualité doit être examinée sur la planche, pas seulement sur le décor.

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
